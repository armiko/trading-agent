from typing import Dict, Any

def calculate_confluence(action: str, context: Dict[str, Any]) -> int:
    """
    Calculate confluence score for a given action (BUY/SELL).
    Returns a score from 0-7 indicating how many factors support the action.
    """
    score = 0
    if action not in ("BUY", "SELL"):
        return 0

    trend_h1 = context.get("trend_h1", "NEUTRAL")
    trend_m15 = context.get("trend_m15", "NEUTRAL")
    trend_m5 = context.get("trend_m5", "NEUTRAL")
    rsi = context.get("rsi", 50)
    
    # 1. H1 Trend alignment
    if (action == "BUY" and trend_h1 == "BULLISH") or \
       (action == "SELL" and trend_h1 == "BEARISH"):
        score += 1
        
    # 2. M15 Trend alignment
    if (action == "BUY" and trend_m15 in ("BULLISH", "BULLISH_CROSS")) or \
       (action == "SELL" and trend_m15 in ("BEARISH", "BEARISH_CROSS")):
        score += 1
        
    # 3. M5 Trend alignment
    if (action == "BUY" and trend_m5 in ("BULLISH", "BULLISH_CROSS")) or \
       (action == "SELL" and trend_m5 in ("BEARISH", "BEARISH_CROSS")):
        score += 1
        
    # 4. RSI Room to grow (not overbought for BUY, not oversold for SELL)
    if (action == "BUY" and rsi < 65) or \
       (action == "SELL" and rsi > 35):
        score += 1
        
    # 5. Price Position (buying near low, selling near high)
    pa = context.get("price_action", {})
    pos = pa.get("price_position", "MIDDLE")
    if (action == "BUY" and pos == "NEAR_LOW") or \
       (action == "SELL" and pos == "NEAR_HIGH"):
        score += 1
        
    # 6. Momentum alignment
    ms = context.get("market_structure", {})
    if ms.get("momentum") == "STRONG":
        score += 1
        
    # 7. Regime alignment (Trending is generally better for directional trades)
    regime = context.get("regime", "UNKNOWN")
    if regime == "TRENDING":
        score += 1
        
    return score
