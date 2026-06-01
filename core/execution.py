"""
Execution Engine: Mengirim order ke MT5 dengan TP/SL dinamis berbasis ATR.
- Trailing stop & breakeven logic
- Time-based exit
- Position monitoring
"""
import MetaTrader5 as mt5
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta


class ExecutionEngine:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.symbol = config.get("symbol", "XAUUSD")
        self.lot = config.get("lot", 0.01)
        self.magic = config.get("magic_number", 99999)
        self.deviation = config.get("max_deviation", 10)
        self.atr_sl_mult = config.get("atr_sl_multiplier", 1.5)
        self.atr_tp_mult = config.get("atr_tp_multiplier", 2.5)
        self.atr_trail_mult = config.get("atr_trailing_multiplier", 1.0)
        self.breakeven_atr = config.get("breakeven_after_atr", 1.0)
        self.time_exit_min = config.get("time_exit_minutes", 20)
        self.time_exit_profit_atr = config.get("time_exit_min_profit_atr", 0.5)

    def _get_point_value(self) -> float:
        """Dapatkan nilai 1 point untuk symbol"""
        info = mt5.symbol_info(self.symbol)
        if info is None:
            return 0.01
        return info.point

    def _calculate_sl_tp(
        self, action: str, entry_price: float, atr: float
    ) -> tuple[float, float]:
        """Hitung SL dan TP berdasarkan ATR"""
        point = self._get_point_value()
        atr_points = atr / point

        if action == "BUY":
            sl = entry_price - (atr_points * self.atr_sl_mult * point)
            tp = entry_price + (atr_points * self.atr_tp_mult * point)
        else:  # SELL
            sl = entry_price + (atr_points * self.atr_sl_mult * point)
            tp = entry_price - (atr_points * self.atr_tp_mult * point)

        return (round(sl, 5), round(tp, 5))

    async def send_order(
        self, action: str, atr: float, reason: str = ""
    ) -> Optional[int]:
        """
        Kirim order ke MT5.
        Return ticket number jika sukses, None jika gagal.
        """
        if not mt5.terminal_info():
            print("[EXEC] MT5 not connected")
            return None

        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            print(f"[EXEC] Failed to get tick for {self.symbol}")
            return None

        order_type = mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL
        price = tick.ask if action == "BUY" else tick.bid

        sl, tp = self._calculate_sl_tp(action, price, atr)

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": self.lot,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": self.deviation,
            "magic": self.magic,
            "comment": f"AI:{reason[:20]}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result is None:
            print("[EXEC] order_send returned None")
            return None

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"[EXEC] Order failed: {result.retcode} - {result.comment}")
            return None

        print(
            f"[EXEC] Order sent: {action} {self.symbol} @ {price} | SL: {sl} | TP: {tp} | Ticket: {result.order}"
        )
        return result.order

    async def get_open_positions(self) -> list:
        """Ambil semua posisi terbuka dengan magic number ini"""
        if not mt5.terminal_info():
            return []
        positions = mt5.positions_get(symbol=self.symbol)
        if positions is None:
            return []
        return [p for p in positions if p.magic == self.magic]

    async def modify_position(
        self, ticket: int, new_sl: float, new_tp: float
    ) -> bool:
        """Modifikasi SL/TP posisi yang sudah ada"""
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl": new_sl,
            "tp": new_tp,
        }
        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            return True
        return False

    async def close_position(self, ticket: int) -> bool:
        """Force close posisi"""
        positions = await self.get_open_positions()
        pos = next((p for p in positions if p.ticket == ticket), None)
        if not pos:
            return False

        tick = mt5.symbol_info_tick(self.symbol)
        if not tick:
            return False

        order_type = (
            mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        )
        price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol": self.symbol,
            "volume": pos.volume,
            "type": order_type,
            "price": price,
            "deviation": self.deviation,
            "magic": self.magic,
            "comment": "AI:TimeExit",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"[EXEC] Position {ticket} closed")
            return True
        return False

    async def monitor_positions(self, atr: float):
        """
        Monitor posisi terbuka:
        - Trailing stop jika profit > 1x ATR
        - Breakeven jika profit > 1x ATR
        - Time-based exit jika > 20 menit & profit < 0.5 ATR
        """
        positions = await self.get_open_positions()
        if not positions:
            return

        point = self._get_point_value()
        atr_points = atr / point

        for pos in positions:
            # Hitung profit dalam points
            if pos.type == mt5.ORDER_TYPE_BUY:
                current_price = mt5.symbol_info_tick(self.symbol).bid
                profit_points = (current_price - pos.price_open) / point
            else:
                current_price = mt5.symbol_info_tick(self.symbol).ask
                profit_points = (pos.price_open - current_price) / point

            # Breakeven logic
            if profit_points >= (atr_points * self.breakeven_atr):
                if pos.type == mt5.ORDER_TYPE_BUY:
                    new_sl = pos.price_open + (2 * point)
                    if new_sl > pos.sl:
                        await self.modify_position(pos.ticket, new_sl, pos.tp)
                        print(f"[EXEC] Breakeven activated for {pos.ticket}")
                else:
                    new_sl = pos.price_open - (2 * point)
                    if new_sl < pos.sl:
                        await self.modify_position(pos.ticket, new_sl, pos.tp)
                        print(f"[EXEC] Breakeven activated for {pos.ticket}")

            # Time-based exit
            open_time = datetime.fromtimestamp(pos.time)
            duration = (datetime.now() - open_time).total_seconds() / 60
            if duration >= self.time_exit_min:
                if profit_points < (atr_points * self.time_exit_profit_atr):
                    await self.close_position(pos.ticket)
                    print(
                        f"[EXEC] Time-based exit for {pos.ticket} after {duration:.1f} min"
                    )
