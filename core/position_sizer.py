"""
Volatility-Based Position Sizing.
Implementasi Kelly Criterion dan ATR-based sizing untuk manajemen risiko yang lebih cerdas.

FIX: Perbaikan fundamental pada rumus Kelly dan Volatility.
- Kelly: fraction → risk_amount → lot (bukan fraction * equity langsung)
- Volatility: lot = risk_amount / (sl_pips * pip_value_per_lot)
"""
import math
from typing import Dict, Any


class PositionSizer:
    """
    Calculate optimal lot size based on:
    - Kelly Criterion (edge-based sizing)
    - Volatility (ATR-based)
    - Risk percentage per trade

    pip_value_per_lot: nilai USD per pip per 1.0 standard lot.
    Contoh XAUUSD: 1 pip = 0.01, 1 standard lot = 100 oz → $10 per pip per lot.
    """

    def __init__(self, config: dict):
        self.base_lot = config.get("lot", 0.01)
        self.risk_per_trade_pct = config.get("risk_per_trade_pct", 1.0)  # 1% per trade
        self.kelly_fraction = config.get("kelly_fraction", 0.25)  # Use 1/4 Kelly for safety
        self.max_lot = config.get("max_lot", 0.5)
        self.min_lot = config.get("min_lot", 0.01)
        self.sl_multiplier = config.get("sl_multiplier", 1.5)
        self.pip_value_per_lot = config.get("pip_value_per_lot", 10.0)  # $10/pip for XAUUSD

    def calculate_kelly_lot(
        self,
        win_rate: float,  # 0-1
        avg_win: float,   # In USD
        avg_loss: float,  # In USD (positive number)
        equity: float,
        atr: float = 0,
        pip_value_per_lot: float = 0,
    ) -> float:
        """
        Kelly Criterion: f* = (p*b - q) / b
        where:
          p = win rate
          q = 1 - p
          b = avg_win / avg_loss

        FIX: Convert Kelly fraction to lot via risk_amount / (sl_pips * pip_value_per_lot)
        instead of the incorrect `fraction * equity` which produces dollar amounts, not lots.
        """
        if avg_loss <= 0 or win_rate <= 0:
            return self.base_lot

        b = avg_win / avg_loss
        kelly_pct = (win_rate * b - (1 - win_rate)) / b
        kelly_pct = max(0, kelly_pct)  # No negative sizing

        # Apply safety fraction
        safe_kelly = kelly_pct * self.kelly_fraction

        # FIX: Convert Kelly fraction → risk amount → lot size
        risk_amount = safe_kelly * equity

        # Use provided pip_value_per_lot or instance default
        pvpl = pip_value_per_lot if pip_value_per_lot > 0 else self.pip_value_per_lot

        if atr <= 0 or pvpl <= 0:
            # Without ATR info, fallback to base_lot
            return self.base_lot

        sl_pips = atr * self.sl_multiplier
        lot = risk_amount / (sl_pips * pvpl)

        return max(self.min_lot, min(self.max_lot, round(lot, 2)))

    def calculate_volatility_lot(
        self,
        equity: float,
        atr: float,
        pip_value_per_lot: float = 0,
        instrument: str = "USD"
    ) -> float:
        """
        ATR-based sizing: lot inversely proportional to volatility.
        Higher ATR = smaller lot (to keep risk constant).

        FIX: Corrected formula from `(risk * pip) / (sl * 10000)` to
        `risk_amount / (sl_pips * pip_value_per_lot)`.
        """
        if atr <= 0:
            return self.base_lot

        # Use provided pip_value_per_lot or instance default
        pvpl = pip_value_per_lot if pip_value_per_lot > 0 else self.pip_value_per_lot

        if pvpl <= 0:
            return self.base_lot

        risk_amount = equity * (self.risk_per_trade_pct / 100)
        sl_pips = atr * self.sl_multiplier

        # FIX: lot = risk_amount / (sl_pips * pip_value_per_lot)
        lot = risk_amount / (sl_pips * pvpl)

        return max(self.min_lot, min(self.max_lot, round(lot, 2)))

    def calculate_optimal_lot(
        self,
        equity: float,
        atr: float,
        win_rate: float = 0.5,
        avg_win: float = 50,
        avg_loss: float = 30,
        pip_value_per_lot: float = 0,
        instrument: str = "USD"
    ) -> float:
        """
        Combine Kelly + Volatility methods, take conservative.
        """
        kelly_lot = self.calculate_kelly_lot(
            win_rate, avg_win, avg_loss, equity,
            atr=atr, pip_value_per_lot=pip_value_per_lot
        )
        vol_lot = self.calculate_volatility_lot(
            equity, atr, pip_value_per_lot, instrument
        )

        # Use the smaller (more conservative) lot
        return min(kelly_lot, vol_lot)

    def get_sizing_info(
        self,
        equity: float,
        atr: float,
        win_rate: float = 0.5,
        avg_win: float = 50,
        avg_loss: float = 30,
        pip_value_per_lot: float = 0,
        instrument: str = "USD"
    ) -> Dict[str, Any]:
        """
        Return detailed sizing information for logging/debugging.
        """
        kelly_lot = self.calculate_kelly_lot(
            win_rate, avg_win, avg_loss, equity,
            atr=atr, pip_value_per_lot=pip_value_per_lot
        )
        vol_lot = self.calculate_volatility_lot(
            equity, atr, pip_value_per_lot, instrument
        )
        optimal = self.calculate_optimal_lot(
            equity, atr, win_rate, avg_win,
            avg_loss, pip_value_per_lot, instrument
        )

        return {
            "base_lot": self.base_lot,
            "kelly_suggested": kelly_lot,
            "volatility_suggested": vol_lot,
            "optimal_lot": optimal,
            "risk_per_trade_pct": self.risk_per_trade_pct,
            "kelly_fraction": self.kelly_fraction,
            "sl_multiplier": self.sl_multiplier,
            "pip_value_per_lot": pip_value_per_lot if pip_value_per_lot > 0 else self.pip_value_per_lot,
        }