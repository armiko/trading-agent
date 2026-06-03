"""
Risk Engine: Memvalidasi apakah sinyal boleh dieksekusi.
- Drawdown harian > max_drawdown_percent -> HIBERNATE
- Max trades per day (customizable)
- Confidence threshold
- Directional conflict dengan M15
- Circuit breaker untuk error bertubi-tubi
"""
import sqlite3
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional


class RiskManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.db_path = config.get("db_path", "db/sqlite.db")
        self.max_trades = config.get("max_trades_per_day", 3)  # Bisa diganti kapan saja
        self.confidence_threshold = config.get("confidence_threshold", 80)
        self.max_drawdown_pct = config.get("max_drawdown_percent", 5)

        # State runtime
        self.consecutive_errors = 0
        self.hibernate_until: Optional[datetime] = None
        self.is_hibernating = False
        self.daily_initial_equity: Optional[float] = None
        self.today_trades = 0
        
        # Error tracking
        self.error_counts = {
            "ai": 0, "mt5": 0, "db": 0, "network": 0, "other": 0
        }
        
        # Exponential backoff
        self.backoff_level = 0
        self.last_error_time: Optional[datetime] = None
        
        # FIX: Default circuit breaker di 3 errors, lalu backoff 1min -> 5min -> 15min -> 60min
        self.max_errors_before_breaker = config.get("circuit_breaker_max_errors", 3)

    def set_max_trades(self, n: int):
        """Override batas trade harian, misal: 1, 3, 5, 10, 999 (unlimited)"""
        self.max_trades = n
        print(f"[RISK] Max trades per day updated to: {n}")

    def reset_daily_state(self, equity: float):
        """Reset state untuk hari baru"""
        self.daily_initial_equity = equity
        self.today_trades = self._count_today_trades()
        self.hibernate_until = None
        self.is_hibernating = False

    def _count_today_trades(self) -> int:
        """Hitung trade hari ini dari DB menggunakan SERVER TIME dari MT5 jika ada"""
        try:
            import MetaTrader5 as mt5
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Gunakan server time dari MT5 jika tersedia (broker timezone)
            server_time = None
            try:
                if mt5.terminal_info():
                    tick = mt5.symbol_info_tick(self.config.get("symbol", "XAUUSD"))
                    if tick and hasattr(tick, 'time') and tick.time:
                        server_time = datetime.fromtimestamp(tick.time)
            except Exception:
                pass
            
            if server_time:
                today = server_time.strftime("%Y-%m-%d")
            else:
                today = date.today().isoformat()
            
            c.execute(
                "SELECT COUNT(*) FROM trade_history WHERE DATE(open_time) = ?",
                (today,),
            )
            count = c.fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0

    def _get_daily_drawdown(self, current_equity: float) -> float:
        """Hitung drawdown harian dalam USC"""
        if self.daily_initial_equity is None:
            return 0.0
        dd = self.daily_initial_equity - current_equity
        return max(0.0, dd)

    def register_error(self, error_type: str = "other"):
        if error_type in self.error_counts:
            self.error_counts[error_type] += 1
        else:
            self.error_counts["other"] += 1
        
        self.consecutive_errors += 1
        self.last_error_time = datetime.now()
        
        if self.consecutive_errors >= self.max_errors_before_breaker:
            self._activate_circuit_breaker()

    def register_success(self):
        """Reset counter error setelah sukses"""
        self.consecutive_errors = 0
        self.error_counts = {k: 0 for k in self.error_counts}
        self.backoff_level = 0

    def _activate_circuit_breaker(self):
        """Exponential backoff: 1min -> 5min -> 15min -> 60min"""
        backoff_minutes = [1, 5, 15, 60]
        self.backoff_level = min(self.backoff_level, len(backoff_minutes) - 1)
        sleep_minutes = backoff_minutes[self.backoff_level]
        
        self.hibernate_until = datetime.now() + timedelta(minutes=sleep_minutes)
        self.is_hibernating = True
        
        error_summary = ", ".join([f"{k}: {v}" for k, v in self.error_counts.items() if v > 0])
        print(f"[RISK] CIRCUIT BREAKER: Hibernate for {sleep_minutes} min (level {self.backoff_level + 1})")
        print(f"[RISK] Error summary: {error_summary}")
        print(f"[RISK] Resume at: {self.hibernate_until}")
        
        self.backoff_level += 1

    def check_circuit_breaker(self) -> bool:
        if not self.is_hibernating:
            return True
        if self.hibernate_until and datetime.now() >= self.hibernate_until:
            self.is_hibernating = False
            self.consecutive_errors = 0
            self.hibernate_until = None
            print("[RISK] Circuit breaker reset. Resuming normal operation.")
            return True
        return False

    def validate(
        self,
        action: str,
        confidence: int,
        current_equity: float,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validasi komprehensif sebelum eksekusi."""
        if not self.check_circuit_breaker():
            return {
                "allowed": False,
                "reason": f"CIRCUIT BREAKER: Hibernate until {self.hibernate_until}",
            }

        if action not in ("BUY", "SELL"):
            return {"allowed": False, "reason": f"Action must be BUY/SELL, got {action}"}

        if confidence < self.confidence_threshold:
            return {
                "allowed": False,
                "reason": f"Confidence {confidence}% < threshold {self.confidence_threshold}%",
            }

        if self.today_trades >= self.max_trades:
            return {
                "allowed": False,
                "reason": f"Max trades today ({self.max_trades}) reached",
            }

        dd = self._get_daily_drawdown(current_equity)
        if self.daily_initial_equity and self.daily_initial_equity > 0:
            dd_pct = (dd / self.daily_initial_equity) * 100
            if dd_pct >= self.max_drawdown_pct:
                # FIX 5: Activate hibernation to prevent log spam and wasted cycles
                if not self.is_hibernating:
                    self.hibernate_until = datetime.now() + timedelta(minutes=60)
                    self.is_hibernating = True
                    print(f"[RISK] DRAWDOWN HIBERNATE: {dd_pct:.1f}% drawdown. Sleeping until {self.hibernate_until}")
                return {
                    "allowed": False,
                    "reason": f"Daily drawdown {dd_pct:.1f}% >= {self.max_drawdown_pct}% -> HIBERNATE",
                }

        trend_m15 = context.get("trend_m15", "NEUTRAL")
        if action == "BUY" and trend_m15 == "BEARISH":
            return {
                "allowed": False,
                "reason": f"BUY signal but M15 trend is {trend_m15} (directional conflict)",
            }
        if action == "SELL" and trend_m15 == "BULLISH":
            return {
                "allowed": False,
                "reason": f"SELL signal but M15 trend is {trend_m15} (directional conflict)",
            }

        rsi = context.get("rsi", 50)
        if action == "BUY" and rsi > 68:
            return {
                "allowed": False,
                "reason": f"RSI {rsi} > 68 overbought, avoid BUY at peak",
            }
        if action == "SELL" and rsi < 32:
            return {
                "allowed": False,
                "reason": f"RSI {rsi} < 32 oversold, avoid SELL at bottom",
            }

        return {"allowed": True, "reason": "All checks passed"}
