"""
Trailing Stop Loss Manager.
Implementasi trailing stop adaptif berbasis ATR.
Fitur: breakeven move, profit locking, dynamic trailing.
"""
from typing import Dict, Any, Optional


class TrailingStopManager:
    """
    Implement trailing stop loss yang adaptif:
    - ATR-based trailing
    - Breakeven move saat profit > 1R
    - Lock profit saat profit > 2R
    """

    def __init__(self, atr_multiplier: float = 1.5, breakeven_buffer: float = 0.2):
        """
        Args:
            atr_multiplier: Multiplier ATR untuk trailing distance
            breakeven_buffer: ATR buffer di atas/bawah entry untuk breakeven
        """
        self.atr_mult = atr_multiplier
        self.be_buffer = breakeven_buffer

    def update_trailing_stop(
        self,
        position: Dict[str, Any],
        current_price: float,
        current_atr: float,
    ) -> Optional[float]:
        """
        Returns new SL price or None if no update needed.

        Args:
            position: {
                "entry_price": float,
                "sl": float,
                "tp": float,
                "direction": "BUY" or "SELL"
            }
            current_price: Harga saat ini
            current_atr: Nilai ATR saat ini

        Returns:
            float: Harga SL baru, atau None jika tidak perlu update
        """
        entry = position["entry_price"]
        sl = position["sl"]
        direction = position["direction"]
        tp = position.get("tp", None)

        if direction == "BUY":
            profit = current_price - entry
            risk = entry - sl

            if risk <= 0:
                return None

            # Breakeven move: profit > 1R
            if profit >= risk * 1.0 and sl < entry:
                new_sl = entry + (current_atr * self.be_buffer)
                if new_sl > sl:
                    return round(new_sl, 5)

            # Lock profit: profit > 2R
            if profit >= risk * 2.0:
                trail_sl = current_price - (current_atr * self.atr_mult)
                if trail_sl > sl and trail_sl < current_price:
                    return round(trail_sl, 5)

            # Aggressive trail: profit > 3R
            if profit >= risk * 3.0:
                tight_trail = current_price - (current_atr * 0.5)
                if tight_trail > sl and tight_trail < current_price:
                    return round(tight_trail, 5)

        else:  # SELL
            profit = entry - current_price
            risk = sl - entry

            if risk <= 0:
                return None

            # Breakeven move
            if profit >= risk * 1.0 and sl > entry:
                new_sl = entry - (current_atr * self.be_buffer)
                if new_sl < sl:
                    return round(new_sl, 5)

            # Lock profit
            if profit >= risk * 2.0:
                trail_sl = current_price + (current_atr * self.atr_mult)
                if trail_sl < sl and trail_sl > current_price:
                    return round(trail_sl, 5)

            # Aggressive trail
            if profit >= risk * 3.0:
                tight_trail = current_price + (current_atr * 0.5)
                if tight_trail < sl and tight_trail > current_price:
                    return round(tight_trail, 5)

        return None

    def should_breakeven(
        self,
        entry_price: float,
        current_price: float,
        sl_price: float,
        direction: str,
    ) -> bool:
        """
        Check apakah posisi sudah layak di-breakeven.
        """
        if direction == "BUY":
            profit = current_price - entry_price
            risk = entry_price - sl_price
        else:
            profit = entry_price - current_price
            risk = sl_price - entry_price

        if risk <= 0:
            return False

        return profit >= risk  # Profit >= 1R

    def get_next_target(
        self,
        entry_price: float,
        sl_price: float,
        tp_price: float,
        direction: str,
    ) -> Dict[str, Any]:
        """
        Calculate next target for partial profit taking.
        Returns target dan alasan.
        """
        risk = abs(entry_price - sl_price)

        if direction == "BUY":
            targets = [
                (1.0, entry_price + risk, "First target (1R) - Breakeven"),
                (1.5, entry_price + risk * 1.5, "Second target (1.5R) - Partial take"),
                (2.0, entry_price + risk * 2.0, "Third target (2R) - Full take"),
            ]
        else:
            targets = [
                (1.0, entry_price - risk, "First target (1R) - Breakeven"),
                (1.5, entry_price - risk * 1.5, "Second target (1.5R) - Partial take"),
                (2.0, entry_price - risk * 2.0, "Third target (2R) - Full take"),
            ]

        for r_mult, price, desc in targets:
            if abs(tp_price - price) / max(abs(tp_price), 0.01) < 0.01:
                return {"target_price": price, "description": desc, "risk_multiple": r_mult}

        return {"target_price": tp_price, "description": "Original TP", "risk_multiple": None}