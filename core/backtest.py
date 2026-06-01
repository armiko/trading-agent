"""
Backtesting Framework untuk validasi strategy sebelum live trading.
- Historical simulation dengan real spread & slippage
- Walk-forward optimization
- Performance metrics (Sharpe, max DD, win rate, etc.)
- Support multiple timeframes
"""
import asyncio
import pandas as pd
import MetaTrader5 as mt5
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import json
import os
from dataclasses import dataclass, asdict

from core.indicators import compute_indicators, get_trend_label, get_latest_values
from core.regime import RegimeClassifier, MarketRegime


@dataclass
class BacktestTrade:
    """Single trade result in backtest"""
    entry_time: datetime
    exit_time: datetime
    direction: str  # BUY or SELL
    entry_price: float
    exit_price: float
    sl_price: float
    tp_price: float
    exit_reason: str  # TP, SL, TIME, MANUAL
    profit_points: float
    profit_usc: float
    ai_confidence: int
    ai_reason: str
    regime: str
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['entry_time'] = self.entry_time.isoformat()
        d['exit_time'] = self.exit_time.isoformat()
        return d


@dataclass
class BacktestMetrics:
    """Performance metrics dari backtest"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_profit: float
    total_loss: float
    net_profit: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    max_consecutive_wins: int
    max_consecutive_losses: int
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    avg_trade_duration_minutes: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def print_summary(self):
        """Print formatted summary"""
        print("\n" + "="*60)
        print("BACKTEST PERFORMANCE SUMMARY")
        print("="*60)
        print(f"Total Trades: {self.total_trades}")
        print(f"Win Rate: {self.win_rate:.1f}% ({self.winning_trades}W / {self.losing_trades}L)")
        print(f"Net Profit: {self.net_profit:.2f} USC")
        print(f"Profit Factor: {self.profit_factor:.2f}")
        print(f"Avg Win: {self.avg_win:.2f} USC | Avg Loss: {self.avg_loss:.2f} USC")
        print(f"Largest Win: {self.largest_win:.2f} USC | Largest Loss: {self.largest_loss:.2f} USC")
        print(f"Max Drawdown: {self.max_drawdown:.2f} USC ({self.max_drawdown_pct:.1f}%)")
        print(f"Sharpe Ratio: {self.sharpe_ratio:.2f}")
        print(f"Avg Trade Duration: {self.avg_trade_duration_minutes:.1f} minutes")
        print("="*60 + "\n")


class BacktestEngine:
    """
    Main backtesting engine.
    Simulate trading strategy pada historical data.
    """
    
    def __init__(
        self,
        symbol: str = "XAUUSD",
        lot_size: float = 0.01,
        initial_balance: float = 2000.0,
        spread_points: int = 10,
        slippage_points: int = 2,
        commission_per_lot: float = 0.0,
    ):
        self.symbol = symbol
        self.lot_size = lot_size
        self.initial_balance = initial_balance
        self.spread_points = spread_points
        self.slippage_points = slippage_points
        self.commission_per_lot = commission_per_lot
        
        # State
        self.trades: List[BacktestTrade] = []
        self.current_position: Optional[Dict[str, Any]] = None
        self.balance = initial_balance
        self.equity = initial_balance
        self.peak_equity = initial_balance
        
        # Regime classifier
        self.regime_classifier = RegimeClassifier()
    
    def _get_point_value(self) -> float:
        """Get point value for symbol"""
        info = mt5.symbol_info(self.symbol)
        if info is None:
            return 0.01  # Default for XAUUSD
        return info.point
    
    def _calculate_profit(
        self,
        direction: str,
        entry_price: float,
        exit_price: float,
        lot_size: float,
    ) -> float:
        """Calculate profit in USC"""
        point = self._get_point_value()
        
        if direction == "BUY":
            profit_points = (exit_price - entry_price) / point
        else:  # SELL
            profit_points = (entry_price - exit_price) / point
        
        # XAUUSD: 1 lot = 100 oz, 1 point = $0.01
        # Cent account: 1 cent lot = 0.01 lot = 1 oz
        # Profit = profit_points * lot_size * 100 (for standard lot)
        # For cent lot: profit_points * lot_size * 1
        profit_usc = profit_points * lot_size * 1.0
        
        # Subtract commission
        profit_usc -= self.commission_per_lot * lot_size * 2  # Entry + exit
        
        return profit_usc
    
    def _apply_spread_slippage(self, price: float, direction: str, is_entry: bool) -> float:
        """Apply spread and slippage to price"""
        point = self._get_point_value()
        
        if is_entry:
            if direction == "BUY":
                # Buy at ask (higher)
                price += (self.spread_points + self.slippage_points) * point
            else:  # SELL
                # Sell at bid (lower)
                price -= self.slippage_points * point
        else:  # Exit
            if direction == "BUY":
                # Close buy at bid (lower)
                price -= self.slippage_points * point
            else:  # SELL
                # Close sell at ask (higher)
                price += (self.spread_points + self.slippage_points) * point
        
        return price
    
    def _check_sl_tp_hit(
        self,
        candle: pd.Series,
        position: Dict[str, Any],
    ) -> Optional[Tuple[str, float]]:
        """
        Check if SL or TP was hit in this candle.
        Returns: (exit_reason, exit_price) or None
        """
        direction = position["direction"]
        sl = position["sl"]
        tp = position["tp"]
        
        if direction == "BUY":
            # Check SL hit (low <= sl)
            if candle["low"] <= sl:
                exit_price = self._apply_spread_slippage(sl, direction, is_entry=False)
                return ("SL", exit_price)
            # Check TP hit (high >= tp)
            if candle["high"] >= tp:
                exit_price = self._apply_spread_slippage(tp, direction, is_entry=False)
                return ("TP", exit_price)
        
        else:  # SELL
            # Check SL hit (high >= sl)
            if candle["high"] >= sl:
                exit_price = self._apply_spread_slippage(sl, direction, is_entry=False)
                return ("SL", exit_price)
            # Check TP hit (low <= tp)
            if candle["low"] <= tp:
                exit_price = self._apply_spread_slippage(tp, direction, is_entry=False)
                return ("TP", exit_price)
        
        return None
    
    def _calculate_sl_tp(
        self,
        direction: str,
        entry_price: float,
        atr: float,
        atr_sl_mult: float = 1.5,
        atr_tp_mult: float = 2.5,
    ) -> Tuple[float, float]:
        """Calculate SL and TP based on ATR"""
        point = self._get_point_value()
        atr_points = atr / point
        
        if direction == "BUY":
            sl = entry_price - (atr_points * atr_sl_mult * point)
            tp = entry_price + (atr_points * atr_tp_mult * point)
        else:  # SELL
            sl = entry_price + (atr_points * atr_sl_mult * point)
            tp = entry_price - (atr_points * atr_tp_mult * point)
        
        return (round(sl, 5), round(tp, 5))
    
    async def simulate_decision(
        self,
        df_m5: pd.DataFrame,
        df_m15: pd.DataFrame,
        current_idx: int,
        ai_decision_func,
        risk_validate_func,
        config: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Simulate AI decision at given candle index.
        Returns decision dict or None if no action.
        """
        # Get current market context
        current_candle = df_m5.iloc[current_idx]
        rsi, atr, _ = get_latest_values(df_m5.iloc[:current_idx+1])
        trend_m5 = get_trend_label(df_m5.iloc[:current_idx+1])
        trend_m15 = get_trend_label(df_m15.iloc[:current_idx+1])
        
        # Classify regime
        regime_info = self.regime_classifier.classify(df_m5.iloc[:current_idx+1], atr)
        
        context = {
            "trend_m15": trend_m15,
            "trend_m5": trend_m5,
            "rsi": round(rsi, 1),
            "atr": round(atr, 1),
            "spread": self.spread_points,
            "session": "London",  # Simplified for backtest
            "regime": regime_info["regime"].value,
        }
        
        # Call AI decision function
        decision = await ai_decision_func(context)
        
        if decision["action"] == "HOLD":
            return None
        
        # Validate with risk manager
        validation = risk_validate_func(
            action=decision["action"],
            confidence=decision["confidence"],
            current_equity=self.equity,
            context=context,
        )
        
        if not validation["allowed"]:
            return None
        
        # Add regime info to decision
        decision["regime"] = regime_info["regime"].value
        decision["context"] = context
        
        return decision
    
    def open_position(
        self,
        candle: pd.Series,
        decision: Dict[str, Any],
        atr: float,
        config: Dict[str, Any],
    ):
        """Open a new position"""
        direction = decision["action"]
        entry_price = self._apply_spread_slippage(
            candle["close"],
            direction,
            is_entry=True
        )
        
        sl, tp = self._calculate_sl_tp(
            direction,
            entry_price,
            atr,
            atr_sl_mult=config.get("atr_sl_multiplier", 1.5),
            atr_tp_mult=config.get("atr_tp_multiplier", 2.5),
        )
        
        self.current_position = {
            "direction": direction,
            "entry_time": candle.name,
            "entry_price": entry_price,
            "sl": sl,
            "tp": tp,
            "ai_confidence": decision["confidence"],
            "ai_reason": decision["reason"],
            "regime": decision.get("regime", "UNKNOWN"),
        }    
    def close_position(
        self,
        candle: pd.Series,
        exit_reason: str,
        exit_price: Optional[float] = None,
    ):
        """Close current position"""
        if not self.current_position:
            return
        
        if exit_price is None:
            exit_price = self._apply_spread_slippage(
                candle["close"],
                self.current_position["direction"],
                is_entry=False
            )
        
        # Calculate profit
        profit_usc = self._calculate_profit(
            self.current_position["direction"],
            self.current_position["entry_price"],
            exit_price,
            self.lot_size,
        )
        
        point = self._get_point_value()
        if self.current_position["direction"] == "BUY":
            profit_points = (exit_price - self.current_position["entry_price"]) / point
        else:
            profit_points = (self.current_position["entry_price"] - exit_price) / point
        
        # Create trade record
        trade = BacktestTrade(
            entry_time=self.current_position["entry_time"],
            exit_time=candle.name,
            direction=self.current_position["direction"],
            entry_price=self.current_position["entry_price"],
            exit_price=exit_price,
            sl_price=self.current_position["sl"],
            tp_price=self.current_position["tp"],
            exit_reason=exit_reason,
            profit_points=profit_points,
            profit_usc=profit_usc,
            ai_confidence=self.current_position["ai_confidence"],
            ai_reason=self.current_position["ai_reason"],
            regime=self.current_position["regime"],
        )
        
        self.trades.append(trade)
        
        # Update balance and equity
        self.balance += profit_usc
        self.equity = self.balance
        
        # Track peak equity for drawdown calculation
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity
        
        # Clear position
        self.current_position = None
    
    def calculate_metrics(self) -> BacktestMetrics:
        """Calculate performance metrics from trades"""
        if not self.trades:
            return BacktestMetrics(
                total_trades=0, winning_trades=0, losing_trades=0,
                win_rate=0, total_profit=0, total_loss=0, net_profit=0,
                profit_factor=0, avg_win=0, avg_loss=0,
                largest_win=0, largest_loss=0,
                max_consecutive_wins=0, max_consecutive_losses=0,
                max_drawdown=0, max_drawdown_pct=0,
                sharpe_ratio=0, sortino_ratio=0, calmar_ratio=0,
                avg_trade_duration_minutes=0,
            )
        
        # Basic stats
        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t.profit_usc > 0]
        losing_trades = [t for t in self.trades if t.profit_usc <= 0]
        
        num_wins = len(winning_trades)
        num_losses = len(losing_trades)
        win_rate = (num_wins / total_trades * 100) if total_trades > 0 else 0
        
        total_profit = sum(t.profit_usc for t in winning_trades)
        total_loss = abs(sum(t.profit_usc for t in losing_trades))
        net_profit = total_profit - total_loss
        
        profit_factor = (total_profit / total_loss) if total_loss > 0 else 0
        
        avg_win = (total_profit / num_wins) if num_wins > 0 else 0
        avg_loss = (total_loss / num_losses) if num_losses > 0 else 0
        
        largest_win = max((t.profit_usc for t in winning_trades), default=0)
        largest_loss = min((t.profit_usc for t in losing_trades), default=0)
        
        # Consecutive wins/losses
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        current_streak = 0
        last_result = None
        
        for trade in self.trades:
            is_win = trade.profit_usc > 0
            if is_win == last_result:
                current_streak += 1
            else:
                current_streak = 1
                last_result = is_win
            
            if is_win:
                max_consecutive_wins = max(max_consecutive_wins, current_streak)
            else:
                max_consecutive_losses = max(max_consecutive_losses, current_streak)
        
        # Drawdown calculation
        equity_curve = [self.initial_balance]
        for trade in self.trades:
            equity_curve.append(equity_curve[-1] + trade.profit_usc)
        
        max_dd = 0
        peak = equity_curve[0]
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            dd = peak - equity
            if dd > max_dd:
                max_dd = dd
        
        max_dd_pct = (max_dd / self.initial_balance * 100) if self.initial_balance > 0 else 0
        
        # Sharpe ratio (simplified: assumes risk-free rate = 0)
        returns = [t.profit_usc for t in self.trades]
        avg_return = sum(returns) / len(returns) if returns else 0
        std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5 if len(returns) > 1 else 0
        sharpe = (avg_return / std_return) if std_return > 0 else 0
        
        # Sortino ratio (only downside deviation)
        downside_returns = [r for r in returns if r < 0]
        downside_std = (sum(r ** 2 for r in downside_returns) / len(downside_returns)) ** 0.5 if downside_returns else 0
        sortino = (avg_return / downside_std) if downside_std > 0 else 0
        
        # Calmar ratio (return / max drawdown)
        calmar = (net_profit / max_dd) if max_dd > 0 else 0
        
        # Average trade duration
        durations = [(t.exit_time - t.entry_time).total_seconds() / 60 for t in self.trades]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        return BacktestMetrics(
            total_trades=total_trades,
            winning_trades=num_wins,
            losing_trades=num_losses,
            win_rate=round(win_rate, 2),
            total_profit=round(total_profit, 2),
            total_loss=round(total_loss, 2),
            net_profit=round(net_profit, 2),
            profit_factor=round(profit_factor, 2),
            avg_win=round(avg_win, 2),
            avg_loss=round(avg_loss, 2),
            largest_win=round(largest_win, 2),
            largest_loss=round(largest_loss, 2),
            max_consecutive_wins=max_consecutive_wins,
            max_consecutive_losses=max_consecutive_losses,
            max_drawdown=round(max_dd, 2),
            max_drawdown_pct=round(max_dd_pct, 2),
            sharpe_ratio=round(sharpe, 2),
            sortino_ratio=round(sortino, 2),
            calmar_ratio=round(calmar, 2),
            avg_trade_duration_minutes=round(avg_duration, 1),
        )
    
    async def run(
        self,
        start_date: datetime,
        end_date: datetime,
        ai_decision_func,
        risk_validate_func,
        config: Dict[str, Any],
        timeframe: int = mt5.TIMEFRAME_M5,
    ) -> BacktestMetrics:
        """
        Run backtest simulation.
        
        Args:
            start_date: Start date for backtest
            end_date: End date for backtest
            ai_decision_func: Async function that takes context and returns decision
            risk_validate_func: Function that validates decision
            config: Trading config dict
            timeframe: MT5 timeframe constant
        
        Returns:
            BacktestMetrics with performance results
        """
        print(f"\n[BACKTEST] Starting simulation: {start_date} to {end_date}")
        
        # Fetch historical data
        if not mt5.initialize():
            print("[BACKTEST] Failed to initialize MT5")
            return self.calculate_metrics()
        
        # Fetch M5 data
        rates_m5 = mt5.copy_rates_range(self.symbol, mt5.TIMEFRAME_M5, start_date, end_date)
        if rates_m5 is None or len(rates_m5) == 0:
            print("[BACKTEST] Failed to fetch M5 data")
            return self.calculate_metrics()
        
        df_m5 = pd.DataFrame(rates_m5)
        df_m5["time"] = pd.to_datetime(df_m5["time"], unit="s")
        df_m5.set_index("time", inplace=True)
        df_m5 = compute_indicators(df_m5)
        
        # Fetch M15 data
        rates_m15 = mt5.copy_rates_range(self.symbol, mt5.TIMEFRAME_M15, start_date, end_date)
        if rates_m15 is None or len(rates_m15) == 0:
            print("[BACKTEST] Failed to fetch M15 data")
            return self.calculate_metrics()
        
        df_m15 = pd.DataFrame(rates_m15)
        df_m15["time"] = pd.to_datetime(df_m15["time"], unit="s")
        df_m15.set_index("time", inplace=True)
        df_m15 = compute_indicators(df_m15)
        
        print(f"[BACKTEST] Loaded {len(df_m5)} M5 candles, {len(df_m15)} M15 candles")
        
        # Simulate trading
        time_exit_minutes = config.get("time_exit_minutes", 20)
        
        for idx in range(50, len(df_m5)):  # Start after 50 candles for indicators
            current_candle = df_m5.iloc[idx]
            
            # Check if position exists
            if self.current_position:
                # Check SL/TP hit
                sl_tp_result = self._check_sl_tp_hit(current_candle, self.current_position)
                if sl_tp_result:
                    exit_reason, exit_price = sl_tp_result
                    self.close_position(current_candle, exit_reason, exit_price)
                    continue
                
                # Check time-based exit
                duration = (current_candle.name - self.current_position["entry_time"]).total_seconds() / 60
                if duration >= time_exit_minutes:
                    self.close_position(current_candle, "TIME")
                    continue
            
            else:
                # No position, check for entry signal
                decision = await self.simulate_decision(
                    df_m5, df_m15, idx, ai_decision_func, risk_validate_func, config
                )
                
                if decision:
                    rsi, atr, _ = get_latest_values(df_m5.iloc[:idx+1])
                    self.open_position(current_candle, decision, atr, config)
        
        # Close any remaining position
        if self.current_position:
            self.close_position(df_m5.iloc[-1], "END")
        
        # Calculate and return metrics
        metrics = self.calculate_metrics()
        metrics.print_summary()
        
        return metrics
    
    def save_results(self, output_dir: str = "db/backtest_results"):
        """Save backtest results to JSON files"""
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save trades
        trades_file = os.path.join(output_dir, f"trades_{timestamp}.json")
        with open(trades_file, "w") as f:
            json.dump([t.to_dict() for t in self.trades], f, indent=2)
        
        # Save metrics
        metrics = self.calculate_metrics()
        metrics_file = os.path.join(output_dir, f"metrics_{timestamp}.json")
        with open(metrics_file, "w") as f:
            json.dump(metrics.to_dict(), f, indent=2)
        
        print(f"[BACKTEST] Results saved to {output_dir}")
