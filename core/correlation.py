"""
Currency Correlation Tracker.
Tracking korelasi XAUUSD dengan DXY (Dollar Index) dan proxy EURUSD/GBPUSD.
Gold berkorelasi negatif kuat dengan USD, ini fundamental penting!
"""
import MetaTrader5 as mt5
import pandas as pd
from typing import Dict, Any, Optional
import asyncio


class CurrencyCorrelation:
    """
    Track korelasi XAUUSD dengan DXY, EURUSD (proxy USD).
    Gold berkorelasi negatif kuat dengan USD.
    """

    def __init__(self, symbol: str = "XAUUSD"):
        self.symbol = symbol
        self.dxy_symbol = "USDX"  # atau "DXY" tergantung broker
        self.proxy_symbols = ["EURUSD", "GBPUSD"]
        self._cache_dxy: Optional[pd.DataFrame] = None
        self._last_update: Optional[float] = None

    async def _ensure_mt5_connected(self) -> bool:
        if not mt5.terminal_info():
            return mt5.initialize()
        return True

    async def fetch_dxy_data(self, count: int = 100) -> Optional[pd.DataFrame]:
        """Ambil data DXY (Dollar Index) atau gunakan proxy"""
        if not await self._ensure_mt5_connected():
            return None

        import time
        now = time.time()
        if self._cache_dxy is not None and self._last_update is not None:
            if now - self._last_update < 60:  # Cache 1 minute
                return self._cache_dxy

        for symbol in [self.dxy_symbol] + self.proxy_symbols:
            try:
                rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, count)
                if rates is not None and len(rates) > 50:
                    df = pd.DataFrame(rates)
                    df["time"] = pd.to_datetime(df["time"], unit="s")
                    df.set_index("time", inplace=True)

                    # EURUSD proxy: inverse untuk mensimulasikan DXY
                    if symbol in self.proxy_symbols:
                        df["close"] = 1.0 / df["close"]

                    self._cache_dxy = df
                    self._last_update = now
                    return df
            except Exception:
                continue

        return None

    def get_correlation_signal(
        self,
        df_gold: pd.DataFrame,
        df_dxy: pd.DataFrame,
        lookback: int = 20
    ) -> Dict[str, Any]:
        """
        Calculate correlation dan generate signal.
        Normal: Gold up + DXY down = konfirmasi bullish
        Anomali: Gold up + DXY up = divergence (warning)
        """
        if df_dxy is None or len(df_dxy) < lookback:
            return {
                "correlation": 0,
                "dxy_trend": "UNKNOWN",
                "dxy_change_pct": 0,
                "divergence": "NONE",
                "signal_bias": "NEUTRAL",
                "warning": "DXY data unavailable"
            }

        try:
            gold_returns = df_gold["close"].pct_change().tail(lookback)
            dxy_returns = df_dxy["close"].pct_change().tail(lookback)
            correlation = gold_returns.corr(dxy_returns)

            dxy_ema20 = df_dxy["close"].ewm(span=20).mean().iloc[-1]
            dxy_current = df_dxy["close"].iloc[-1]
            dxy_trend = "BULLISH" if dxy_current > dxy_ema20 else "BEARISH"

            # Detect divergence
            gold_change = (df_gold["close"].iloc[-1] - df_gold["close"].iloc[-lookback]) / df_gold["close"].iloc[-lookback]
            dxy_change = (df_dxy["close"].iloc[-1] - df_dxy["close"].iloc[-lookback]) / df_dxy["close"].iloc[-lookback]

            divergence = "NONE"
            signal_bias = "NEUTRAL"

            if gold_change > 0 and dxy_change > 0:
                divergence = "BULLISH_DIVERGENCE"
                signal_bias = "AVOID_BUY"
            elif gold_change < 0 and dxy_change < 0:
                divergence = "BEARISH_DIVERGENCE"
                signal_bias = "AVOID_SELL"
            elif gold_change > 0 and dxy_change < 0:
                signal_bias = "CONFIRM_BUY"
            elif gold_change < 0 and dxy_change > 0:
                signal_bias = "CONFIRM_SELL"

            return {
                "correlation": round(float(correlation), 2),
                "dxy_trend": dxy_trend,
                "dxy_change_pct": round(float(dxy_change * 100), 2),
                "divergence": divergence,
                "signal_bias": signal_bias,
                "warning": None
            }
        except Exception as e:
            return {
                "correlation": 0,
                "dxy_trend": "ERROR",
                "dxy_change_pct": 0,
                "divergence": "NONE",
                "signal_bias": "NEUTRAL",
                "warning": f"Correlation error: {e}"
            }