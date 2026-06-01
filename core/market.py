"""
Market data gathering dengan multi-timeframe caching.
ENHANCED VERSION:
- Richer context dengan Support/Resistance, Price Action, Market Structure
- Dynamic spread check berdasarkan ATR
- Session filter integration
"""
import asyncio
import MetaTrader5 as mt5
import pandas as pd
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from core.indicators import (
    compute_indicators, get_trend_label, get_latest_values,
    get_enhanced_context, detect_support_resistance, analyze_price_action, analyze_market_structure
)


class MarketData:
    def __init__(self, symbol: str = "XAUUSD", atr_multiplier_limit: float = 0.3):
        self.symbol = symbol
        self.atr_multiplier_limit = atr_multiplier_limit
        self._cache_m5: Optional[pd.DataFrame] = None
        self._cache_m15: Optional[pd.DataFrame] = None
        self._last_m5_update: Optional[datetime] = None
        self._last_m15_update: Optional[datetime] = None
        self._spread_cache: Optional[int] = None
        self._last_spread_update: Optional[datetime] = None

        # Running values
        self.current_atr: float = 0.0
        self.current_rsi: float = 50.0
        self.current_spread: int = 0
        self.trend_m15: str = "NEUTRAL"
        self.trend_m5: str = "NEUTRAL"
        self.session: str = ""
        self.is_market_open: bool = False

        # Enhanced context storage
        self.enhanced_context: Dict[str, Any] = {}
        self.support_resistance: Dict[str, Any] = {}
        self.price_action: Dict[str, Any] = {}
        self.market_structure: Dict[str, Any] = {}

    async def _ensure_mt5_connected(self) -> bool:
        if not mt5.terminal_info():
            return mt5.initialize()
        return True

    def _get_session(self) -> str:
        now = datetime.now()
        hour = now.hour
        if 0 <= hour < 9:
            return "Asia"
        elif 9 <= hour < 12:
            return "Transition"
        elif 12 <= hour < 17:
            return "London"
        elif 17 <= hour < 21:
            return "New York"
        else:
            return "Asia"

    def _check_market_hours(self) -> bool:
        now = datetime.now()
        # Forex 24/5: skip Sabtu & Minggu
        return now.weekday() < 5

    async def fetch_spread(self) -> int:
        """Cek spread real-time dari MT5"""
        if not await self._ensure_mt5_connected():
            return 999
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            return 999
        spread = int((tick.ask - tick.bid) / mt5.symbol_info(self.symbol).point)
        self._spread_cache = spread
        self._last_spread_update = datetime.now()
        self.current_spread = spread
        return spread

    async def is_spread_acceptable(self) -> bool:
        """Spread dikatakan aman jika < 30% ATR"""
        spread = await self.fetch_spread()
        if self.current_atr <= 0:
            return spread < 50  # fallback safe
        max_allowed = max(1, int(self.current_atr * self.atr_multiplier_limit))
        return spread <= max_allowed

    async def fetch_rates(
        self, timeframe: int, count: int = 100
    ) -> Optional[pd.DataFrame]:
        """Ambil data candle dari MT5"""
        if not await self._ensure_mt5_connected():
            return None
        rates = mt5.copy_rates_from_pos(self.symbol, timeframe, 0, count)
        if rates is None or len(rates) == 0:
            return None
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df.set_index("time", inplace=True)
        return df

    async def update_m5(self) -> Optional[pd.DataFrame]:
        """Update M5 (boleh tiap 1 menit)"""
        self._cache_m5 = await self.fetch_rates(mt5.TIMEFRAME_M5, 100)
        if self._cache_m5 is not None:
            self._cache_m5 = compute_indicators(self._cache_m5)
        self._last_m5_update = datetime.now()
        return self._cache_m5

    async def update_m15(self) -> Optional[pd.DataFrame]:
        """Update M15 (hanya sekali tiap 15 menit)"""
        now = datetime.now()
        if (
            self._last_m15_update
            and (now - self._last_m15_update).total_seconds() < 120
        ):
            return self._cache_m15  # cached, kurang dari 2 menit

        self._cache_m15 = await self.fetch_rates(mt5.TIMEFRAME_M15, 100)
        if self._cache_m15 is not None:
            self._cache_m15 = compute_indicators(self._cache_m15)
        self._last_m15_update = now
        return self._cache_m15

    async def get_context(self) -> Dict[str, Any]:
        """Kembalikan dictionary market context untuk prompt AI"""
        self.session = self._get_session()
        self.is_market_open = self._check_market_hours()

        if not self.is_market_open:
            return {
                "action": "HOLD",
                "reason": "Market closed (weekend)",
                "session": self.session,
            }

        await self.update_m5()
        await self.update_m15()
        await self.fetch_spread()

        # Get enhanced context
        if self._cache_m5 is not None:
            self.enhanced_context = get_enhanced_context(self._cache_m5)
            self.support_resistance = self.enhanced_context.get("support_resistance", {})
            self.price_action = self.enhanced_context.get("price_action", {})
            self.market_structure = self.enhanced_context.get("market_structure", {})

        # Get latest values
        if self._cache_m5 is not None:
            rsi, atr, ema_diff = get_latest_values(self._cache_m5)
            self.current_rsi = rsi
            self.current_atr = atr

        # Build comprehensive context
        context = {
            "trend_m15": self.trend_m15,
            "trend_m5": self.trend_m5,
            "rsi": round(self.current_rsi, 1),
            "atr": round(self.current_atr, 1),
            "ema_diff": round(ema_diff, 2) if self._cache_m5 is not None else 0,
            "spread": self.current_spread,
            "session": self.session,
            "market_structure": self.market_structure,
            "price_action": self.price_action,
            "support_resistance": self.support_resistance,
        }

        return context
