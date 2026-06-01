"""
Kalkulasi indikator teknikal menggunakan pandas_ta.
- EMA_20, EMA_50 untuk M15 dan M5
- RSI_14
- ATR_14
"""
import pandas as pd
import pandas_ta as ta
from typing import Tuple, Optional


def compute_indicators(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    Menambahkan kolom indikator ke dataframe.
    Membutuhkan kolom: open, high, low, close, volume
    """
    if df is None or len(df) < 50:
        return df

    try:
        # EMA
        df["EMA_20"] = ta.ema(df["close"], length=20)
        df["EMA_50"] = ta.ema(df["close"], length=50)

        # RSI
        rsi = ta.rsi(df["close"], length=14)
        df["RSI_14"] = rsi

        # ATR
        atr = ta.atr(df["high"], df["low"], df["close"], length=14)
        df["ATR_14"] = atr

    except Exception as e:
        print(f"[INDICATORS] Error computing: {e}")
        return None

    return df


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
