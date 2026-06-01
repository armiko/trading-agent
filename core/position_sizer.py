"""
Volatility-Based Position Sizing.
Implementasi Kelly Criterion dan ATR-based sizing untuk manajemen risiko yang lebih cerdas.
"""
import math
from typing import Dict, Any


class PositionSizer:
    """
    Calculate optimal lot size based on:
    - Kelly Criterion (edge-based sizing)
    - Volatility (ATR-based)
    - Risk percentage per trade
    """

    def __init__(self, config: dict):
        self.base_lot = config.get("lot", 0.01)
        self.risk_per_trade_pct = config.get("risk_per_trade_pct", 1.0)  # 1% per trade
        self.kelly_fraction = config.get("kelly_fraction", 0.25)  # Use 1/4 Kelly for safety
        self.max_lot = config.get("max_lot", 0.5)
        self.min_lot = config.get("min_lot", 0.01)

    def calculate_kelly_lot(
        self,
        win_rate: float,  # 0-1
        avg_win: float,   # In USC
        avg_loss: float,  # In USC (positive number)
        equity: float,
    ) -> float:
        """
        Kelly Criterion: f* = (p*b - q) / b
        where:
          p = win rate
          q = 1 - p
          b = avg_win / avg_loss
        """
        if avg_loss <= 0 or win_rate <= 0:
            return self.base_lot

        b = avg_win / avg_loss
        kelly_pct = (win_rate * b - (1 - win_rate)) / b
        kelly_pct = max(0, kelly_pct)  # No negative sizing

        # Apply safety fraction
        safe_kelly = kelly_pct * self.kelly_fraction

        # Convert to lot
        lot = safe_kelly * equity / 100  # Simplified conversion

        return max(self.min_lot, min(self.max_lot, round(lot, 2)))

    def calculate_volatility_lot(
        self,
        equity: float,
        atr: float,
        sl_multiplier: float = 1.5,
    ) -> float:
        """
        ATR-based sizing: lot inversely proportional to volatility.
        Higher ATR = smaller lot (to keep risk constant).
        """
        risk_amount = equity * (self.risk_per_trade_pct / 100)

        # SL distance in points
        sl_points = atr * sl_multiplier * 100  # Convert to points

        # Value per point for XAUUSD: ~$0.01 per point per 0.01 lot
        # Risk = sl_points * lot * 0.01
        # Solve for lot: lot = risk / (sl_points * 0.01)
        if sl_points <= 0:
            return self.base_lot

        lot = risk_amount / (sl_points * 0.01)

        return max(self.min_lot, min(self.max_lot, round(lot, 2)))

    def calculate_optimal_lot(
        self,
        equity: float,
        atr: float,
        win_rate: float = 0.5,
        avg_win: float = 50,
        avg_loss: float = 30,
    ) -> float:
        """
        Combine Kelly + Volatility methods, take conservative.
        """
        kelly_lot = self.calculate_kelly_lot(win_rate, avg_win, avg_loss, equity)
        vol_lot = self.calculate_volatility_lot(equity, atr)

        # Use the smaller (more conservative) lot
        return min(kelly_lot, vol_lot)

    def get_sizing_info(
        self,
        equity: float,
        atr: float,
        win_rate: float = 0.5,
        avg_win: float = 50,
        avg_loss: float = 30,
    ) -> Dict[str, Any]:
        """
        Return detailed sizing information for logging/debugging.
        """
        kelly_lot = self.calculate_kelly_lot(win_rate, avg_win, avg_loss, equity)
        vol_lot = self.calculate_volatility_lot(equity, atr)
        optimal = self.calculate_optimal_lot(equity, atr, win_rate, avg_win, avg_loss)

        return {
            "base_lot": self.base_lot,
            "kelly_suggested": kelly_lot,
            "volatility_suggested": vol_lot,
            "optimal_lot": optimal,
            "risk_per_trade_pct": self.risk_per_trade_pct,
            "kelly_fraction": self.kelly_fraction,
        }