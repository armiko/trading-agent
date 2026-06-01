"""
Risk Engine: Memvalidasi apakah sinyal boleh dieksekusi.
- Drawdown harian > max_drawdown_percent → HIBERNATE
- Max trades per day
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
        self.max_trades = config.get("max_trades_per_day", 3)
        self.confidence_threshold = config.get("confidence_threshold", 80)
        self.max_drawdown_pct = config.get("max_drawdown_percent", 5)
        self.circuit_breaker_max = config.get("circuit_breaker_max_errors", 3)
        self.circuit_breaker_sleep = config.get("circuit_breaker_sleep_hours", 1)

        # State runtime
        self.consecutive_errors = 0
        self.hibernate_until: Optional[datetime] = None
        self.is_hibernating = False
        self.daily_initial_equity: Optional[float] = None
        self.today_trades = 0

    def reset_daily_state(self, equity: float):
        """Reset state untuk hari baru"""
        self.daily_initial_equity = equity
        self.today_trades = self._count_today_trades()
        self.hibernate_until = None
        self.is_hibernating = False

    def _count_today_trades(self) -> int:
        """Hitung trade hari ini dari DB"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
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

    def register_error(self):
        """Tambah counter error bertubi-tubi"""
        self.consecutive_errors += 1
        if self.consecutive_errors >= self.circuit_breaker_max:
            self._activate_circuit_breaker()

    def register_success(self):
        """Reset counter error setelah sukses"""
        self.consecutive_errors = 0

    def _activate_circuit_breaker(self):
        """Aktifkan mode hibernasi karena terlalu banyak error"""
        self.hibernate_until = datetime.now() + timedelta(
            hours=self.circuit_breaker_sleep
        )
        self.is_hibernating = True
        print(
            f"[RISK] CIRCUIT BREAKER: Hibernate until {self.hibernate_until}"
        )

    def check_circuit_breaker(self) -> bool:
        """Cek apakah circuit breaker masih aktif"""
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
        """
        Validasi komprehensif sebelum eksekusi.
        Return dict: {"allowed": bool, "reason": str}
        """
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
                return {
                    "allowed": False,
                    "reason": f"Daily drawdown {dd_pct:.1f}% >= {self.max_drawdown_pct}% → HIBERNATE",
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
