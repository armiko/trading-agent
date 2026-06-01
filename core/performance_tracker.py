"""
Live Performance Tracker.
Monitor live trading performance dan compare dengan backtest expectations.
Alert jika deviation > threshold.
"""
import json
import os
from typing import Dict, Any, Optional
from datetime import datetime


class LivePerformanceTracker:
    """
    Track live performance dan compare dengan backtest expectations.
    Alert jika live performance deviates > 30% dari backtest.
    """

    def __init__(self, db_path: str = "db/sqlite.db"):
        self.db_path = db_path
        self.starting_equity: Optional[float] = None
        self.peak_equity: float = 0
        self.trade_count: int = 0
        self.wins: int = 0
        self.losses: int = 0
        self.total_profit: float = 0
        self.total_loss: float = 0
        self.trades_history: list = []
        self.state_file = "db/performance_state.json"

    def start_tracking(self, starting_equity: float):
        """Initialize tracking dengan starting equity."""
        self.starting_equity = starting_equity
        self.peak_equity = starting_equity
        self.save_state()

    def record_trade(self, profit_usc: float, current_equity: float):
        """Record hasil trade."""
        self.trade_count += 1
        if profit_usc > 0:
            self.wins += 1
            self.total_profit += profit_usc
        else:
            self.losses += 1
            self.total_loss += abs(profit_usc)

        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

        self.trades_history.append({
            "timestamp": datetime.now().isoformat(),
            "profit": profit_usc,
            "equity": current_equity,
        })

        self.save_state()

    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        if self.trade_count == 0:
            return {
                "trade_count": 0,
                "win_rate": 0,
                "wins": 0,
                "losses": 0,
                "profit_factor": 0,
                "current_drawdown_pct": 0,
                "sample_size_warning": True,
            }

        win_rate = (self.wins / self.trade_count) * 100
        profit_factor = (self.total_profit / self.total_loss) if self.total_loss > 0 else 0

        # Calculate current drawdown
        current_equity = self.trades_history[-1]["equity"] if self.trades_history else self.starting_equity
        current_dd = self.peak_equity - current_equity
        current_dd_pct = (current_dd / self.peak_equity * 100) if self.peak_equity > 0 else 0

        return {
            "trade_count": self.trade_count,
            "win_rate": round(win_rate, 2),
            "wins": self.wins,
            "losses": self.losses,
            "profit_factor": round(profit_factor, 2),
            "total_profit": round(self.total_profit, 2),
            "total_loss": round(self.total_loss, 2),
            "net_profit": round(self.total_profit - self.total_loss, 2),
            "current_drawdown_pct": round(current_dd_pct, 2),
            "peak_equity": round(self.peak_equity, 2),
            "sample_size_warning": self.trade_count < 30,
        }

    def check_deviation(self, backtest_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare live vs backtest. Alert jika deviation > 30%.
        """
        live = self.get_metrics()
        if not live or not backtest_metrics or live["trade_count"] < 10:
            return {"status": "insufficient_data", "warnings": []}

        warnings = []

        # Win rate deviation
        live_wr = live["win_rate"]
        bt_wr = backtest_metrics.get("win_rate", 50)
        wr_diff = abs(live_wr - bt_wr)
        if wr_diff > 15 and live["trade_count"] >= 20:
            warnings.append(f"⚠️ Win rate deviation: live {live_wr}% vs backtest {bt_wr}%")

        # Profit factor deviation
        live_pf = live["profit_factor"]
        bt_pf = backtest_metrics.get("profit_factor", 1.5)
        if live_pf < bt_pf * 0.7 and live["trade_count"] >= 20:
            warnings.append(f"⚠️ Profit factor below backtest: live {live_pf} vs backtest {bt_pf}")

        # Drawdown deviation
        live_dd = abs(live["current_drawdown_pct"])
        bt_dd = backtest_metrics.get("max_drawdown_pct", 10)
        if live_dd > bt_dd * 1.3:
            warnings.append(f"🚨 Drawdown exceeded backtest: {live_dd}% vs {bt_dd}%")

        # Sample size warning
        if live["sample_size_warning"]:
            warnings.append(f"ℹ️ Sample size too small ({live['trade_count']} trades). Need 30+ for statistical significance.")

        return {
            "status": "WARNING" if warnings else "OK",
            "warnings": warnings,
            "live_metrics": live,
            "backtest_metrics": backtest_metrics,
        }

    def save_state(self):
        """Save current state to file."""
        try:
            os.makedirs("db", exist_ok=True)
            state = {
                "starting_equity": self.starting_equity,
                "peak_equity": self.peak_equity,
                "trade_count": self.trade_count,
                "wins": self.wins,
                "losses": self.losses,
                "total_profit": self.total_profit,
                "total_loss": self.total_loss,
                "trades_history": self.trades_history[-100:],  # Keep last 100 trades
            }
            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"[PERF_TRACKER] Failed to save state: {e}")

    def load_state(self):
        """Load state from file."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, "r") as f:
                    state = json.load(f)
                self.starting_equity = state.get("starting_equity")
                self.peak_equity = state.get("peak_equity", 0)
                self.trade_count = state.get("trade_count", 0)
                self.wins = state.get("wins", 0)
                self.losses = state.get("losses", 0)
                self.total_profit = state.get("total_profit", 0)
                self.total_loss = state.get("total_loss", 0)
                self.trades_history = state.get("trades_history", [])
                print(f"[PERF_TRACKER] Loaded state: {self.trade_count} trades")
        except Exception as e:
            print(f"[PERF_TRACKER] Failed to load state: {e}")

    def reset(self):
        """Reset all tracking data."""
        self.starting_equity = None
        self.peak_equity = 0
        self.trade_count = 0
        self.wins = 0
        self.losses = 0
        self.total_profit = 0
        self.total_loss = 0
        self.trades_history = []
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
        print("[PERF_TRACKER] Reset complete")