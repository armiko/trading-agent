"""
Kalkulasi indikator teknikal menggunakan pandas_ta.
ENHANCED VERSION:
- EMA_20, EMA_50, EMA_200 untuk trend
- RSI_14, Stochastic untuk momentum
- ATR_14 untuk volatility
- MACD untuk trend confirmation
- Support/Resistance levels (pivot points, swing highs/lows)
- Price Action patterns (HH, LL, breakouts)
- Volume analysis
- Market structure detection
"""
import pandas as pd
import pandas_ta as ta
import numpy as np
from typing import Tuple, Optional, Dict, Any, List
from dataclasses import dataclass


@dataclass
class SupportResistance:
    """Support and Resistance levels"""
    support_levels: List[float]
    resistance_levels: List[float]
    nearest_support: float
    nearest_resistance: float
    distance_to_support_pct: float
    distance_to_resistance_pct: float


@dataclass
class PriceAction:
    """Price Action analysis"""
    pattern: str  # HH, LL, HL, LH, CONSOLIDATION
    trend_strength: float  # 0-100
    breakout_signal: str  # BULLISH_BREAKOUT, BEARISH_BREAKOUT, NONE
    swing_high: float
    swing_low: float
    price_position: str  # NEAR_HIGH, NEAR_LOW, MIDDLE


@dataclass
class MarketStructure:
    """Market structure analysis"""
    structure: str  # BULLISH, BEARISH, NEUTRAL
    momentum: str  # STRONG, WEAK, NEUTRAL
    volatility: str  # HIGH, NORMAL, LOW
    volume_trend: str  # INCREASING, DECREASING, STABLE


def compute_indicators(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    Menambahkan kolom indikator ke dataframe.
    Membutuhkan kolom: open, high, low, close, volume
    """
    if df is None or len(df) < 50:
        return df

    try:
        # EMA - Multiple timeframes
        df["EMA_20"] = ta.ema(df["close"], length=20)
        df["EMA_50"] = ta.ema(df["close"], length=50)
        df["EMA_200"] = ta.ema(df["close"], length=200)

        # RSI
        df["RSI_14"] = ta.rsi(df["close"], length=14)

        # ATR
        df["ATR_14"] = ta.atr(df["high"], df["low"], df["close"], length=14)

        # MACD
        macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
        if macd is not None:
            df["MACD"] = macd["MACD_12_26_9"]
            df["MACD_signal"] = macd["MACDs_12_26_9"]
            df["MACD_hist"] = macd["MACDh_12_26_9"]

        # Stochastic
        stoch = ta.stoch(df["high"], df["low"], df["close"], k=14, d=3)
        if stoch is not None:
            df["STOCH_K"] = stoch["STOCHk_14_3_3"]
            df["STOCH_D"] = stoch["STOCHd_14_3_3"]

        # Bollinger Bands
        bb = ta.bbands(df["close"], length=20, std=2)
        if bb is not None:
            df["BB_upper"] = bb["BBU_20_2.0"]
            df["BB_middle"] = bb["BBM_20_2.0"]
            df["BB_lower"] = bb["BBL_20_2.0"]
            df["BB_width"] = bb["BBB_20_2.0"]

        # ADX for trend strength
        adx = ta.adx(df["high"], df["low"], df["close"], length=14)
        if adx is not None:
            df["ADX"] = adx["ADX_14"]
            df["DI_plus"] = adx["DMP_14"]
            df["DI_minus"] = adx["DMN_14"]

        # Volume indicators
        df["Volume_SMA"] = ta.sma(df["tick_volume"], length=20)
        df["Volume_ratio"] = df["tick_volume"] / df["Volume_SMA"]

        # Price momentum
        df["ROC"] = ta.roc(df["close"], length=10)  # Rate of Change
        df["MOM"] = ta.mom(df["close"], length=10)  # Momentum

    except Exception as e:
        print(f"[INDICATORS] Error computing: {e}")
        return None

    return df


def detect_support_resistance(df: pd.DataFrame, lookback: int = 50) -> SupportResistance:
    """
    Detect support and resistance levels using pivot points and swing highs/lows.
    """
    if df is None or len(df) < lookback:
        current_price = df["close"].iloc[-1] if len(df) > 0 else 0
        return SupportResistance(
            support_levels=[],
            resistance_levels=[],
            nearest_support=current_price * 0.99,
            nearest_resistance=current_price * 1.01,
            distance_to_support_pct=1.0,
            distance_to_resistance_pct=1.0,
        )

    recent_df = df.tail(lookback)
    current_price = recent_df["close"].iloc[-1]

    # Find swing highs and lows
    swing_highs = []
    swing_lows = []

    for i in range(2, len(recent_df) - 2):
        # Swing high: higher than 2 candles before and after
        if (recent_df["high"].iloc[i] > recent_df["high"].iloc[i-1] and
            recent_df["high"].iloc[i] > recent_df["high"].iloc[i-2] and
            recent_df["high"].iloc[i] > recent_df["high"].iloc[i+1] and
            recent_df["high"].iloc[i] > recent_df["high"].iloc[i+2]):
            swing_highs.append(recent_df["high"].iloc[i])

        # Swing low: lower than 2 candles before and after
        if (recent_df["low"].iloc[i] < recent_df["low"].iloc[i-1] and
            recent_df["low"].iloc[i] < recent_df["low"].iloc[i-2] and
            recent_df["low"].iloc[i] < recent_df["low"].iloc[i+1] and
            recent_df["low"].iloc[i] < recent_df["low"].iloc[i+2]):
            swing_lows.append(recent_df["low"].iloc[i])

    # Cluster nearby levels (within 0.1% of each other)
    def cluster_levels(levels: List[float], tolerance: float = 0.001) -> List[float]:
        if not levels:
            return []
        levels = sorted(levels)
        clustered = []
        current_cluster = [levels[0]]

        for level in levels[1:]:
            if abs(level - current_cluster[-1]) / current_cluster[-1] < tolerance:
                current_cluster.append(level)
            else:
                clustered.append(sum(current_cluster) / len(current_cluster))
                current_cluster = [level]

        clustered.append(sum(current_cluster) / len(current_cluster))
        return clustered

    resistance_levels = cluster_levels(swing_highs)
    support_levels = cluster_levels(swing_lows)

    # Filter levels: resistance above price, support below price
    resistance_levels = [r for r in resistance_levels if r > current_price]
    support_levels = [s for s in support_levels if s < current_price]

    # Find nearest levels
    nearest_resistance = min(resistance_levels) if resistance_levels else current_price * 1.01
    nearest_support = max(support_levels) if support_levels else current_price * 0.99

    # Calculate distances
    dist_to_resistance = ((nearest_resistance - current_price) / current_price) * 100
    dist_to_support = ((current_price - nearest_support) / current_price) * 100

    return SupportResistance(
        support_levels=support_levels[:3],  # Top 3 support levels
        resistance_levels=resistance_levels[:3],  # Top 3 resistance levels
        nearest_support=nearest_support,
        nearest_resistance=nearest_resistance,
        distance_to_support_pct=round(dist_to_support, 2),
        distance_to_resistance_pct=round(dist_to_resistance, 2),
    )


def analyze_price_action(df: pd.DataFrame, lookback: int = 20) -> PriceAction:
    """
    Analyze price action patterns: HH, LL, HL, LH, breakouts.
    """
    if df is None or len(df) < lookback:
        return PriceAction(
            pattern="UNKNOWN",
            trend_strength=0,
            breakout_signal="NONE",
            swing_high=0,
            swing_low=0,
            price_position="MIDDLE",
        )

    recent_df = df.tail(lookback)
    current_price = recent_df["close"].iloc[-1]

    # Find recent swing points
    highs = recent_df["high"].values
    lows = recent_df["low"].values

    swing_high = np.max(highs)
    swing_low = np.min(lows)

    # Detect pattern
    mid_point = len(recent_df) // 2
    first_half_high = np.max(highs[:mid_point])
    second_half_high = np.max(highs[mid_point:])
    first_half_low = np.min(lows[:mid_point])
    second_half_low = np.min(lows[mid_point:])

    pattern = "CONSOLIDATION"
    if second_half_high > first_half_high and second_half_low > first_half_low:
        pattern = "HH_HL"  # Higher Highs, Higher Lows (Bullish)
    elif second_half_high < first_half_high and second_half_low < first_half_low:
        pattern = "LH_LL"  # Lower Highs, Lower Lows (Bearish)
    elif second_half_high > first_half_high and second_half_low < first_half_low:
        pattern = "EXPANSION"  # Expanding range
    elif second_half_high < first_half_high and second_half_low > first_half_low:
        pattern = "CONTRACTION"  # Contracting range

    # Calculate trend strength (0-100)
    price_range = swing_high - swing_low
    if price_range > 0:
        position_in_range = (current_price - swing_low) / price_range
        if pattern == "HH_HL":
            trend_strength = min(100, position_in_range * 100 + 20)
        elif pattern == "LH_LL":
            trend_strength = min(100, (1 - position_in_range) * 100 + 20)
        else:
            trend_strength = 50
    else:
        trend_strength = 50

    # Detect breakouts
    breakout_signal = "NONE"
    recent_high = np.max(highs[-5:])
    recent_low = np.min(lows[-5:])
    prev_high = np.max(highs[-10:-5])
    prev_low = np.min(lows[-10:-5])

    if recent_high > prev_high * 1.001:  # 0.1% breakout threshold
        breakout_signal = "BULLISH_BREAKOUT"
    elif recent_low < prev_low * 0.999:
        breakout_signal = "BEARISH_BREAKOUT"

    # Price position
    range_third = price_range / 3
    if current_price > swing_high - range_third:
        price_position = "NEAR_HIGH"
    elif current_price < swing_low + range_third:
        price_position = "NEAR_LOW"
    else:
        price_position = "MIDDLE"

    return PriceAction(
        pattern=pattern,
        trend_strength=round(trend_strength, 1),
        breakout_signal=breakout_signal,
        swing_high=round(swing_high, 5),
        swing_low=round(swing_low, 5),
        price_position=price_position,
    )


def analyze_market_structure(df: pd.DataFrame) -> MarketStructure:
    """
    Analyze overall market structure: trend, momentum, volatility, volume.
    """
    if df is None or len(df) < 50:
        return MarketStructure(
            structure="NEUTRAL",
            momentum="NEUTRAL",
            volatility="NORMAL",
            volume_trend="STABLE",
        )

    latest = df.iloc[-1]

    # Structure: based on EMA alignment
    ema20 = latest.get("EMA_20", 0)
    ema50 = latest.get("EMA_50", 0)
    ema200 = latest.get("EMA_200", 0)
    close = latest["close"]

    if ema20 > ema50 > ema200 and close > ema20:
        structure = "BULLISH"
    elif ema20 < ema50 < ema200 and close < ema20:
        structure = "BEARISH"
    else:
        structure = "NEUTRAL"

    # Momentum: based on MACD and RSI
    macd_hist = latest.get("MACD_hist", 0)
    rsi = latest.get("RSI_14", 50)

    if abs(macd_hist) > 5 and (rsi > 60 or rsi < 40):
        momentum = "STRONG"
    elif abs(macd_hist) < 2 and 45 < rsi < 55:
        momentum = "WEAK"
    else:
        momentum = "NEUTRAL"

    # Volatility: based on ATR percentile
    atr = latest.get("ATR_14", 0)
    atr_series = df["ATR_14"].tail(50).dropna()
    if len(atr_series) > 20:
        atr_percentile = (atr_series < atr).sum() / len(atr_series) * 100
        if atr_percentile > 75:
            volatility = "HIGH"
        elif atr_percentile < 25:
            volatility = "LOW"
        else:
            volatility = "NORMAL"
    else:
        volatility = "NORMAL"

    # Volume trend
    volume_ratio = latest.get("Volume_ratio", 1.0)
    recent_volume_ratios = df["Volume_ratio"].tail(10).mean() if "Volume_ratio" in df.columns else 1.0

    if recent_volume_ratios > 1.2:
        volume_trend = "INCREASING"
    elif recent_volume_ratios < 0.8:
        volume_trend = "DECREASING"
    else:
        volume_trend = "STABLE"

    return MarketStructure(
        structure=structure,
        momentum=momentum,
        volatility=volatility,
        volume_trend=volume_trend,
    )


def get_trend_label(df: pd.DataFrame) -> str:
    """Tentukan tren berdasarkan EMA"""
    if df is None or len(df) < 2:
        return "NEUTRAL"

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    ema20 = latest.get("EMA_20", None)
    ema50 = latest.get("EMA_50", None)

    if ema20 is None or ema50 is None:
        return "NEUTRAL"

    if ema20 > ema50:
        if prev.get("EMA_20", 0) > prev.get("EMA_50", 0):
            return "BULLISH"
        else:
            return "BULLISH_CROSS"
    elif ema20 < ema50:
        if prev.get("EMA_20", 0) < prev.get("EMA_50", 0):
            return "BEARISH"
        else:
            return "BEARISH_CROSS"
    else:
        return "NEUTRAL"


def get_latest_values(df: pd.DataFrame) -> Tuple[float, float, float]:
    """
    Kembalikan (RSI, ATR, EMA_diff) dari baris terakhir
    EMA_diff = EMA20 - EMA50 (positif = bullish)
    """
    if df is None or len(df) == 0:
        return (50.0, 0.0, 0.0)

    latest = df.iloc[-1]
    rsi = latest.get("RSI_14", 50.0)
    atr = latest.get("ATR_14", 0.0)
    ema20 = latest.get("EMA_20", 0.0)
    ema50 = latest.get("EMA_50", 0.0)

    if pd.isna(rsi):
        rsi = 50.0
    if pd.isna(atr):
        atr = 0.0
    if pd.isna(ema20) or pd.isna(ema50):
        ema_diff = 0.0
    else:
        ema_diff = ema20 - ema50

    return (rsi, atr, ema_diff)


def get_enhanced_context(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Get comprehensive market context with all indicators.
    """
    if df is None or len(df) < 50:
        return {}

    latest = df.iloc[-1]
    rsi, atr, ema_diff = get_latest_values(df)

    # Support/Resistance
    sr = detect_support_resistance(df)

    # Price Action
    pa = analyze_price_action(df)

    # Market Structure
    ms = analyze_market_structure(df)

    # Additional indicators
    macd_hist = latest.get("MACD_hist", 0)
    stoch_k = latest.get("STOCH_K", 50)
    adx = latest.get("ADX", 0)
    bb_width = latest.get("BB_width", 0)

    return {
        "rsi": round(rsi, 1),
        "atr": round(atr, 1),
        "ema_diff": round(ema_diff, 2),
        "macd_hist": round(macd_hist, 2),
        "stoch_k": round(stoch_k, 1),
        "adx": round(adx, 1),
        "bb_width": round(bb_width, 2),
        "support_resistance": {
            "nearest_support": round(sr.nearest_support, 2),
            "nearest_resistance": round(sr.nearest_resistance, 2),
            "dist_to_support_pct": sr.distance_to_support_pct,
            "dist_to_resistance_pct": sr.distance_to_resistance_pct,
        },
        "price_action": {
            "pattern": pa.pattern,
            "trend_strength": pa.trend_strength,
            "breakout_signal": pa.breakout_signal,
            "price_position": pa.price_position,
        },
        "market_structure": {
            "structure": ms.structure,
            "momentum": ms.momentum,
            "volatility": ms.volatility,
            "volume_trend": ms.volume_trend,
        },
    }
