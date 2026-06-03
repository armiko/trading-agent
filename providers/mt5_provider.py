"""
MetaTrader 5 Provider untuk eksekusi trading dan pengambilan data.
Catatan: Library MetaTrader5 hanya berjalan di OS Windows.
"""
import pandas as pd
from datetime import datetime
import time
from typing import Optional, Dict, Any, List

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    print("[WARNING] MetaTrader5 library tidak tersedia. Fitur MT5 hanya berjalan di Windows.")


class MT5Provider:
    def __init__(self, magic_number: int = 99999):
        self.magic_number = magic_number
        self.connected = False

    def connect(self) -> bool:
        """Inisialisasi koneksi ke terminal MT5 lokal."""
        if not MT5_AVAILABLE:
            print("MetaTrader5 tidak terinstall atau tidak berjalan di Windows.")
            return False
            
        if not mt5.initialize():
            print(f"MT5 initialize() failed, error code = {mt5.last_error()}")
            return False
            
        self.connected = True
        return True

    def disconnect(self):
        """Tutup koneksi MT5."""
        if MT5_AVAILABLE and self.connected:
            mt5.shutdown()
            self.connected = False

    def get_account_info(self) -> Optional[Dict[str, float]]:
        """Mendapatkan informasi akun (balance, equity, margin)."""
        if not self.connected:
            return None
            
        account_info = mt5.account_info()
        if account_info is None:
            return None
            
        return {
            "balance": account_info.balance,
            "equity": account_info.equity,
            "margin": account_info.margin,
            "free_margin": account_info.margin_free,
            "leverage": account_info.leverage
        }

    def get_historical_data(self, symbol: str, timeframe: int, count: int = 100) -> Optional[pd.DataFrame]:
        """
        Mendapatkan historical candlestick data.
        timeframe: misalnya mt5.TIMEFRAME_M15, mt5.TIMEFRAME_H1
        """
        if not self.connected:
            return None
            
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
        if rates is None or len(rates) == 0:
            return None
            
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        # Rename columns untuk disesuaikan dengan core/indicators.py kita
        # indicators.py butuh: open, high, low, close, volume (tick_volume)
        df = df.rename(columns={'tick_volume': 'volume'})
        
        return df

    def execute_market_order(self, symbol: str, order_type: int, lot_size: float, 
                             sl: float = 0.0, tp: float = 0.0, comment: str = "") -> Optional[Dict[str, Any]]:
        """
        Mengeksekusi market order (Buy/Sell).
        order_type: mt5.ORDER_TYPE_BUY atau mt5.ORDER_TYPE_SELL
        """
        if not self.connected:
            return None
            
        # Dapatkan harga saat ini berdasarkan tipe order
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            print(f"Gagal mendapatkan data tick untuk {symbol}")
            return None
            
        price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(lot_size),
            "type": order_type,
            "price": price,
            "sl": float(sl),
            "tp": float(tp),
            "deviation": 10,
            "magic": self.magic_number,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            error = result.retcode if result else mt5.last_error()
            print(f"Order failed, retcode={error}")
            return None
            
        return {
            "order_ticket": result.order,
            "price": result.price,
            "volume": result.volume
        }

    def close_position(self, ticket: int) -> bool:
        """Menutup posisi berdasarkan ticket id."""
        if not self.connected:
            return False
            
        position = mt5.positions_get(ticket=ticket)
        if position is None or len(position) == 0:
            return False
            
        pos = position[0]
        tick = mt5.symbol_info_tick(pos.symbol)
        
        # Kebalikan dari posisi saat ini
        if pos.type == mt5.ORDER_TYPE_BUY:
            close_type = mt5.ORDER_TYPE_SELL
            price = tick.bid
        else:
            close_type = mt5.ORDER_TYPE_BUY
            price = tick.ask
            
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": close_type,
            "position": ticket,
            "price": price,
            "deviation": 10,
            "magic": self.magic_number,
            "comment": "Close Position",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            return False
            
        return True
