"""
Market Regime Classifier.
Mengklasifikasikan kondisi market menjadi:
- TRENDING: Strong directional movement (ADX > 25, ATR high)
- RANGING: Sideways/consolidation (ADX < 20, ATR low, BB width narrow)
- VOLATILE: High volatility without clear direction (ATR very high, ADX mixed)

Digunakan untuk adaptive strategy dan learning memory clustering.
"""
import pandas as pd
import pandas_ta as ta
from typing import Dict, Any, Optional
from enum import Enum


class MarketRegime(Enum):
    """Market regime types"""
    TRENDING = "TRENDING"
    RANGING = "RANGING"
    VOLATILE = "VOLATILE"
    UNKNOWN = "UNKNOWN"


class RegimeClassifier:
    """
    Classifier untuk menentukan market regime berdasarkan multiple indicators.
    """
    
    def __init__(
        self,
        adx_trending_threshold: float = 25.0,
        adx_ranging_threshold: float = 20.0,
        atr_percentile_high: float = 75.0,
        atr_percentile_low: float = 25.0,
        bb_width_percentile_narrow: float = 30.0,
    ):
        """
        Args:
            adx_trending_threshold: ADX > threshold = trending
            adx_ranging_threshold: ADX < threshold = ranging
            atr_percentile_high: ATR above this percentile = high volatility
            atr_percentile_low: ATR below this percentile = low volatility
            bb_width_percentile_narrow: BB width below this percentile = narrow range
        """
        self.adx_trending = adx_trending_threshold
        self.adx_ranging = adx_ranging_threshold
        self.atr_pct_high = atr_percentile_high
        self.atr_pct_low = atr_percentile_low
        self.bb_width_pct_narrow = bb_width_percentile_narrow
        
        # Cache for regime history
        self.regime_history: list[MarketRegime] = []
        self.max_history = 100

    def _calculate_adx(self, df: pd.DataFrame, length: int = 14) -> Optional[float]:
        """Calculate ADX (Average Directional Index)"""
        if df is None or len(df) < length + 1:
            return None
        
        try:
            adx = ta.adx(df["high"], df["low"], df["close"], length=length)
            if adx is None or len(adx) == 0:
                return None
            
            # ADX returns a DataFrame with columns: ADX_14, DMP_14, DMN_14
            if isinstance(adx, pd.DataFrame) and f"ADX_{length}" in adx.columns:
                return float(adx[f"ADX_{length}"].iloc[-1])
            
            return None
        except Exception as e:
            print(f"[REGIME] ADX calculation error: {e}")
            return None

    def _calculate_bb_width(self, df: pd.DataFrame, length: int = 20, std: float = 2.0) -> Optional[float]:
        """Calculate Bollinger Bands width as percentage of price"""
        if df is None or len(df) < length:
            return None
        
        try:
            bb = ta.bbands(df["close"], length=length, std=std)
            if bb is None or len(bb) == 0:
                return None
            
            # BB returns DataFrame with columns: BBL_20_2.0, BBM_20_2.0, BBU_20_2.0, BBB_20_2.0, BBP_20_2.0
            upper_col = f"BBU_{length}_{std}"
            lower_col = f"BBL_{length}_{std}"
            middle_col = f"BBM_{length}_{std}"
            
            if upper_col not in bb.columns or lower_col not in bb.columns or middle_col not in bb.columns:
                return None
            
            upper = bb[upper_col].iloc[-1]
            lower = bb[lower_col].iloc[-1]
            middle = bb[middle_col].iloc[-1]
            
            # Width as percentage of middle band
            width_pct = ((upper - lower) / middle) * 100 if middle > 0 else 0
            return float(width_pct)
        
        except Exception as e:
            print(f"[REGIME] BB width calculation error: {e}")
            return None

    def _get_atr_percentile(self, df: pd.DataFrame, current_atr: float) -> Optional[float]:
        """Get percentile rank of current ATR vs historical ATR"""
        if df is None or "ATR_14" not in df.columns or len(df) < 50:
            return None
        
        try:
            atr_series = df["ATR_14"].dropna()
            if len(atr_series) < 20:
                return None
            
            # Calculate percentile rank
            percentile = (atr_series < current_atr).sum() / len(atr_series) * 100
            return float(percentile)
        
        except Exception as e:
            print(f"[REGIME] ATR percentile error: {e}")
            return None

    def _get_bb_width_percentile(self, df: pd.DataFrame, current_width: float) -> Optional[float]:
        """Get percentile rank of current BB width vs historical"""
        if df is None or len(df) < 50:
            return None
        
        try:
            # Calculate BB width for all historical data
            bb = ta.bbands(df["close"], length=20, std=2.0)
            if bb is None:
                return None
            
            upper_col = "BBU_20_2.0"
            lower_col = "BBL_20_2.0"
            middle_col = "BBM_20_2.0"
            
            if upper_col not in bb.columns or lower_col not in bb.columns or middle_col not in bb.columns:
                return None
            
            width_series = ((bb[upper_col] - bb[lower_col]) / bb[middle_col] * 100).dropna()
            
            if len(width_series) < 20:
                return None
            
            # Calculate percentile rank
            percentile = (width_series < current_width).sum() / len(width_series) * 100
            return float(percentile)
        
        except Exception as e:
            print(f"[REGIME] BB width percentile error: {e}")
            return None

    def classify(self, df: pd.DataFrame, current_atr: float) -> Dict[str, Any]:
        """
        Classify current market regime.
        
        Returns:
            {
                "regime": MarketRegime,
                "confidence": float (0-100),
                "metrics": {
                    "adx": float,
                    "atr_percentile": float,
                    "bb_width": float,
                    "bb_width_percentile": float,
                },
                "reasoning": str
            }
        """
        if df is None or len(df) < 50:
            return {
                "regime": MarketRegime.UNKNOWN,
                "confidence": 0,
                "metrics": {},
                "reasoning": "Insufficient data for regime classification"
            }
        
        # Calculate indicators
        adx = self._calculate_adx(df)
        bb_width = self._calculate_bb_width(df)
        atr_percentile = self._get_atr_percentile(df, current_atr)
        bb_width_percentile = self._get_bb_width_percentile(df, bb_width) if bb_width else None
        
        metrics = {
            "adx": adx,
            "atr_percentile": atr_percentile,
            "bb_width": bb_width,
            "bb_width_percentile": bb_width_percentile,
        }
        
        # Classification logic
        regime = MarketRegime.UNKNOWN
        confidence = 0
        reasoning = ""
        
        # Check if we have enough data
        if adx is None or atr_percentile is None:
            return {
                "regime": MarketRegime.UNKNOWN,
                "confidence": 0,
                "metrics": metrics,
                "reasoning": "Missing key indicators (ADX or ATR)"
            }
        
        # TRENDING: Strong ADX + moderate to high ATR
        if adx >= self.adx_trending:
            if atr_percentile >= self.atr_pct_high:
                regime = MarketRegime.VOLATILE
                confidence = min(100, adx + (atr_percentile - self.atr_pct_high))
                reasoning = f"High volatility with strong trend (ADX: {adx:.1f}, ATR: {atr_percentile:.0f}th percentile)"
            else:
                regime = MarketRegime.TRENDING
                confidence = min(100, adx + 20)
                reasoning = f"Strong trending market (ADX: {adx:.1f})"
        
        # RANGING: Low ADX + low ATR + narrow BB
        elif adx < self.adx_ranging:
            if atr_percentile < self.atr_pct_low:
                if bb_width_percentile and bb_width_percentile < self.bb_width_pct_narrow:
                    regime = MarketRegime.RANGING
                    confidence = min(100, (self.adx_ranging - adx) * 3 + (self.atr_pct_low - atr_percentile))
                    reasoning = f"Tight ranging market (ADX: {adx:.1f}, ATR: {atr_percentile:.0f}th pct, BB: {bb_width_percentile:.0f}th pct)"
                else:
                    regime = MarketRegime.RANGING
                    confidence = min(100, (self.adx_ranging - adx) * 3)
                    reasoning = f"Ranging market (ADX: {adx:.1f}, low ATR)"
            else:
                # Low ADX but high ATR = choppy/volatile
                regime = MarketRegime.VOLATILE
                confidence = min(100, atr_percentile - self.atr_pct_low)
                reasoning = f"Choppy/volatile market (low ADX: {adx:.1f}, high ATR: {atr_percentile:.0f}th pct)"
        
        # MIXED: Medium ADX
        else:
            if atr_percentile >= self.atr_pct_high:
                regime = MarketRegime.VOLATILE
                confidence = min(100, atr_percentile - 50)
                reasoning = f"Volatile market (medium ADX: {adx:.1f}, high ATR: {atr_percentile:.0f}th pct)"
            else:
                regime = MarketRegime.TRENDING
                confidence = min(100, adx)
                reasoning = f"Weak trending market (ADX: {adx:.1f})"
        
        # Update history
        self.regime_history.append(regime)
        if len(self.regime_history) > self.max_history:
            self.regime_history.pop(0)
        
        return {
            "regime": regime,
            "confidence": round(confidence, 1),
            "metrics": metrics,
            "reasoning": reasoning
        }

    def get_regime_stability(self, lookback: int = 10) -> float:
        """
        Calculate regime stability (0-100).
        100 = same regime for all lookback periods.
        0 = regime changes every period.
        """
        if len(self.regime_history) < lookback:
            return 0.0
        
        recent = self.regime_history[-lookback:]
        most_common = max(set(recent), key=recent.count)
        stability = (recent.count(most_common) / lookback) * 100
        
        return round(stability, 1)

    def get_adaptive_params(self, regime: MarketRegime) -> Dict[str, Any]:
        """
        Get recommended trading parameters based on regime.
        
        Returns adaptive parameters for:
        - confidence_threshold
        - max_trades_per_day
        - atr_sl_multiplier
        - atr_tp_multiplier
        - time_exit_minutes
        """
        if regime == MarketRegime.TRENDING:
            return {
                "confidence_threshold": 75,  # Lower threshold for trending
                "max_trades_per_day": 5,     # More trades in trending
                "atr_sl_multiplier": 1.5,
                "atr_tp_multiplier": 3.0,    # Wider TP for trends
                "time_exit_minutes": 30,     # Let trends run longer
                "description": "Trending market: wider TP, more trades"
            }
        
        elif regime == MarketRegime.RANGING:
            return {
                "confidence_threshold": 85,  # Higher threshold for ranging
                "max_trades_per_day": 2,     # Fewer trades in ranging
                "atr_sl_multiplier": 1.0,    # Tighter SL
                "atr_tp_multiplier": 1.5,    # Tighter TP
                "time_exit_minutes": 15,     # Quick exits
                "description": "Ranging market: tight SL/TP, fewer trades"
            }
        
        elif regime == MarketRegime.VOLATILE:
            return {
                "confidence_threshold": 90,  # Very high threshold
                "max_trades_per_day": 1,     # Very few trades
                "atr_sl_multiplier": 2.0,    # Wider SL for volatility
                "atr_tp_multiplier": 2.0,
                "time_exit_minutes": 20,
                "description": "Volatile market: wide SL, minimal trades"
            }
        
        else:  # UNKNOWN
            return {
                "confidence_threshold": 80,
                "max_trades_per_day": 3,
                "atr_sl_multiplier": 1.5,
                "atr_tp_multiplier": 2.5,
                "time_exit_minutes": 20,
                "description": "Unknown regime: default parameters"
            }


# Singleton instance
_classifier_instance: Optional[RegimeClassifier] = None


def get_classifier(
    adx_trending_threshold: float = 25.0,
    adx_ranging_threshold: float = 20.0,
) -> RegimeClassifier:
    """Get or create singleton classifier instance"""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = RegimeClassifier(
            adx_trending_threshold=adx_trending_threshold,
            adx_ranging_threshold=adx_ranging_threshold,
        )
    return _classifier_instance
"""