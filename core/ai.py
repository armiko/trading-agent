"""
AI Decision Engine: Menyusun prompt, komunikasi dengan 9Router AI provider, parsing response.
ENHANCED VERSION:
- Richer context dengan Support/Resistance, Price Action, Market Structure, Regime
- Adaptive prompt based on market regime
- Better learning memory integration
"""
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from .learning import LearningMemory
from providers.ninerouter import NineRouterClient


SYSTEM_INSTRUCTION = (
    "Kamu adalah AI Trading Quantitative murni yang menganalisis data teknikal XAUUSD. "
    "Tugasmu mengevaluasi MULTIPLE INDIKATOR secara komprehensif dan mengeluarkan "
    "1 keputusan trading berdasarkan konfirmasi dari banyak indikator. "
    "OUTPUT HARUS BERUPA JSON VALID, TANPA TEKS TAMBAHAN. "
    "Format: {"action": "BUY/SELL/HOLD", "confidence": <0-100>, "reason": "<maksimal 15 kata>"}"
)


class AIDecisionEngine:
    def __init__(
        self,
        model: str = "auto",
        db_path: str = "db/sqlite.db",
        ninerouter_url: str = "http://localhost:20128/v1",
        ninerouter_api_key: Optional[str] = None,
    ):
        self.db_path = db_path
        self.learning = LearningMemory(db_path)
        self.last_decision: Optional[Dict[str, Any]] = None

        # Setup 9Router client
        self.client = NineRouterClient(
            base_url=ninerouter_url,
            model=model if model != "auto" else "auto",
            api_key=ninerouter_api_key,
        )
        self.model = model
        self.model_display = f"9router/{model}"

        # Provider performance tracking
        self.provider_stats = {
            "calls": 0,
            "successes": 0,
            "failures": 0,
            "avg_latency_ms": 0,
            "last_used": None
        }

    async def call_provider(self, prompt: str) -> Optional[str]:
        """Panggil 9Router (single provider). Handle semua model termasuk Ollama via 9Router."""
        result = await self.client.generate(prompt)
        if not result:
            print("[AI] CRITICAL: 9Router failed to respond")
        return result

    async def build_prompt(self, context: Dict[str, Any]) -> str:
        """Build enriched prompt with comprehensive market analysis."""
        lessons = self.learning.get_weighted_memory(limit_loss=3, limit_win=2)

        memory_section = ""
        if lessons:
            memory_lines = []
            for l in lessons:
                memory_lines.append(f"- {l['lesson']}")
            memory_section = "\n".join(memory_lines)
        else:
            memory_section = """- Hindari entry saat RSI > 70 (overbought) atau < 30 (oversold)
- Harga mendekati Resistance = sinyal SELL, mendekati Support = sinyal BUY
- ATR rendah (<10) menandakan market sideways, hindari entry
- Spread tinggi (>50) mengurangi profit potential, hindari entry
- Volume meningkat + breakout = validasi trend kuat"""

        # Extract market structure
        ms = context.get("market_structure", {})
        support_res = context.get("support_resistance", {})
        price_action = context.get("price_action", {})
        regime = context.get("regime", "UNKNOWN")

        trend_m15 = context.get("trend_m15", "NEUTRAL")
        trend_m5 = context.get("trend_m5", "NEUTRAL")
        rsi = context.get("rsi", 50)
        atr = context.get("atr", 0)
        ema_diff = context.get("ema_diff", 0)
        spread = context.get("spread", 0)
        session = context.get("session", "Unknown")

        prompt = f"""[SYSTEM INSTRUCTION]
{SYSTEM_INSTRUCTION}

[MARKET CONTEXT]
- Timeframe M15 Trend: {trend_m15}
- Timeframe M5 Trend: {trend_m5}
- RSI (14): {rsi}
- ATR (14): {atr}
- EMA20-EMA50 spread: {ema_diff}
- Spread: {spread} points
- Session: {session}

[MARKET STRUCTURE]
- Structure: {ms.get('structure', 'NEUTRAL')}
- Momentum: {ms.get('momentum', 'NEUTRAL')}
- Volatility: {ms.get('volatility', 'NORMAL')}
- Volume: {ms.get('volume_trend', 'STABLE')}

[SUPPORT & RESISTANCE]
- Nearest Support: {support_res.get('nearest_support', 'N/A')}
- Nearest Resistance: {support_res.get('nearest_resistance', 'N/A')}
- Distance to Support: {support_res.get('dist_to_support_pct', 0)}%
- Distance to Resistance: {support_res.get('dist_to_resistance_pct', 0)}%

[PRICE ACTION]
- Pattern: {price_action.get('pattern', 'UNKNOWN')}
- Trend Strength: {price_action.get('trend_strength', 50)}%
- Breakout Signal: {price_action.get('breakout_signal', 'NONE')}
- Price Position: {price_action.get('price_position', 'MIDDLE')}

[MARKET REGIME]
- Regime: {regime}

[LEARNING MEMORY]
{memory_section if memory_section else 'Belum ada memori trading.'}

[ANALYSIS RULES]
1. Harga dekat Resistance + RSI > 70 = prioritaskan SELL
2. Harga dekat Support + RSI < 30 = prioritaskan BUY
3. Trend M15 BULLISH + HH/HL pattern = konfirmasi BUY
4. Trend M15 BEARISH + LH/LL pattern = konfirmasi SELL
5. Volume meningkat + breakout valid = tren kuat
6. ATR tinggi + market VOLATILE = prioritaskan HOLD

[OUTPUT FORMAT]
{{"action": "BUY/SELL/HOLD", "confidence": <0-100>, "reason": "<maksimal 15 kata>"}}
"""
        return prompt

    def _parse_json_response(self, raw: str) -> Optional[Dict[str, Any]]:
        """Parse JSON dari response AI. Handle markdown code block."""
        if not raw:
            return None
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1:
                cleaned = cleaned[start : end + 1]
        try:
            result = json.loads(cleaned)
            if "action" not in result or "confidence" not in result:
                return None
            result["action"] = result["action"].upper()
            if result["action"] not in ("BUY", "SELL", "HOLD"):
                return None
            result["confidence"] = int(result["confidence"])
            result["confidence"] = max(0, min(100, result["confidence"]))
            return result
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            print(f"[AI] JSON parse error: {e}")
            return None

    async def decide(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Loop utama dengan rich context dan provider performance tracking."""
        prompt = await self.build_prompt(context)
        start_time = datetime.now()
        self.provider_stats["calls"] += 1

        max_retries = 2
        for attempt in range(max_retries + 1):
            raw = await self.call_provider(prompt)
            if not raw:
                print(f"[AI] Attempt {attempt+1}: no response")
                continue

            parsed = self._parse_json_response(raw)
            if parsed:
                latency = (datetime.now() - start_time).total_seconds() * 1000
                self.provider_stats["successes"] += 1
                self.provider_stats["last_used"] = datetime.now().isoformat()
                prev_avg = self.provider_stats["avg_latency_ms"]
                n = self.provider_stats["successes"]
                self.provider_stats["avg_latency_ms"] = ((prev_avg * (n-1)) + latency) / n
                
                self.last_decision = parsed
                return parsed

            print(f"[AI] Attempt {attempt+1}: failed to parse: {raw[:80]}...")

        self.provider_stats["failures"] += 1
        
        fallback = {
            "action": "HOLD",
            "confidence": 0,
            "reason": "parsing error after retries",
        }
        self.last_decision = fallback
        return fallback

    async def self_reflect(self, trade_result: Dict[str, Any]) -> str:
        """Post-trade reflection dengan context lengkap."""
        action = trade_result.get("action", "UNKNOWN")
        reason = trade_result.get("reason", "none")
        profit = trade_result.get("profit", 0)
        context = trade_result.get("context", {})
        result = "WIN" if profit > 0 else "LOSS"

        ms = context.get("market_structure", {})
        sr = context.get("support_resistance", {})
        pa = context.get("price_action", {})

        reflection_prompt = f"""
[SYSTEM INSTRUCTION]
Kamu adalah AI Trading yang mengevaluasi ulang keputusan trading sendiri.
Analisa mengapa trade ini {result} dan buat 1 kalimat lesson learned dalam Bahasa Indonesia, maksimal 20 kata.

[DETAIL TRADE]
- Action: {action}
- Alasan: {reason}
- Hasil: {result} ({profit} USC)
- RSI saat entry: {context.get('rsi', 'N/A')}
- ATR saat entry: {context.get('atr', 'N/A')}
- Market Structure: {ms.get('structure', 'N/A')}
- Jarak ke Support: {sr.get('dist_to_support_pct', 'N/A')}%
- Jarak ke Resistance: {sr.get('dist_to_resistance_pct', 'N/A')}%
- Price Pattern: {pa.get('pattern', 'N/A')}

[OUTPUT]
Hanya 1 kalimat, tanpa format khusus.
"""

        raw = await self.call_provider(reflection_prompt)
        if raw:
            lesson = raw.strip().strip('"').strip("'")
            if len(lesson) > 150:
                lesson = lesson[:147] + "..."
            return lesson
        return f"{action} at RSI {context.get('rsi', '?')} resulted in {result}"
