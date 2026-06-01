"""
AI Decision Engine: Menyusun prompt, komunikasi dengan AI provider (Ollama/9Router), parsing response.
- Support provider switching via config
- Retry 2x jika parsing gagal
- Fallback ke HOLD jika semua retry gagal
- Memory: ambil 3 loss + 2 win terbaru
"""
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from .learning import LearningMemory


SYSTEM_INSTRUCTION = (
    "Kamu adalah AI Trading Quantitative murni. Tugasmu mengevaluasi data teknikal XAUUSD "
    "dan mengeluarkan 1 keputusan trading. "
    "OUTPUT HARUS BERUPA JSON VALID, TANPA TEKS TAMBAHAN. "
    'Format: {"action": "BUY/SELL/HOLD", "confidence": <0-100>, "reason": "<maksimal 10 kata>"}'
)


class AIDecisionEngine:
    def __init__(
        self,
        provider: str = "ollama",
        model: str = "qwen3:8b",
        db_path: str = "db/sqlite.db",
        ninerouter_url: str = "http://localhost:20128/v1",
        ninerouter_api_key: Optional[str] = None,
    ):
        self.provider = provider
        self.db_path = db_path
        self.learning = LearningMemory(db_path)
        self.last_decision: Optional[Dict[str, Any]] = None

        # Setup provider client
        if provider == "ninerouter":
            from providers.ninerouter import NineRouterClient
            self.client = NineRouterClient(
                base_url=ninerouter_url,
                model=model if model != "auto" else "auto",
                api_key=ninerouter_api_key,
            )
            self.model_display = f"9router/{ninerouter_url}"
        else:
            from providers.ollama import OllamaClient
            self.client = OllamaClient(base_url="http://localhost:11434")
            self.model_display = model

        self.model = model

        # Fallback handler
        self.fallback_provider = None
        self._setup_fallback()
        
        # FIX #17: Provider performance tracking
        self.provider_stats = {
            "calls": 0,
            "successes": 0,
            "failures": 0,
            "fallback_used": 0,
            "avg_latency_ms": 0,
            "last_used": None
        }

    def _setup_fallback(self):
        """
        Setup fallback: jika provider utama gagal terus,
        coba provider lain.
        """
        if self.provider == "ollama":
            # Ollama -> 9Router fallback
            try:
                from providers.ninerouter import NineRouterClient
                self.fallback_provider = NineRouterClient(
                    base_url="http://localhost:20128/v1",
                    model="auto",
                )
            except Exception:
                self.fallback_provider = None
        elif self.provider == "ninerouter":
            # 9Router -> Ollama fallback
            try:
                from providers.ollama import OllamaClient
                self.fallback_provider = OllamaClient()
            except Exception:
                self.fallback_provider = None

    async def call_provider(self, prompt: str) -> Optional[str]:
        """
        FIX #12: Panggil AI provider dengan fallback dan logging.
        Return None jika semua provider gagal.
        """
        # Coba provider utama
        if self.provider == "ninerouter":
            result = await self.client.generate(prompt)
            if result:
                return result
            # Fallback ke Ollama
            print("[AI] 9Router failed, falling back to Ollama...")
            if self.fallback_provider:
                from providers.ollama import OllamaClient
                if isinstance(self.fallback_provider, OllamaClient):
                    return await self.fallback_provider.generate(self.model, prompt)
        else:
            # Ollama -> panggil dengan model
            result = await self.client.generate(self.model, prompt)
            if result:
                return result
            # Fallback ke 9Router
            print("[AI] Ollama failed, falling back to 9Router...")
            if self.fallback_provider:
                return await self.fallback_provider.generate(prompt)

        # FIX #12: Semua provider gagal
        print("[AI] CRITICAL: All AI providers failed (9Router + Ollama)")
        return None

    async def build_prompt(self, context: Dict[str, Any]) -> str:
        """FIX #6: Bangun prompt dengan market context + learning memory (with fallback)"""
        lessons = self.learning.get_weighted_memory(limit_loss=3, limit_win=2)

        memory_section = ""
        if lessons:
            memory_lines = []
            for l in lessons:
                memory_lines.append(f"- {l['lesson']}")
            memory_section = "\n".join(memory_lines)
        else:
            # FIX #6: Fallback untuk bot baru (no history)
            memory_section = """- Hindari entry saat RSI > 70 (overbought) atau < 30 (oversold)
- Perhatikan trend M15 untuk konfirmasi arah
- ATR rendah (<10) menandakan market sideways, hindari entry
- Spread tinggi mengurangi profit potential"""

        trend_m15 = context.get("trend_m15", "NEUTRAL")
        trend_m5 = context.get("trend_m5", "NEUTRAL")
        rsi = context.get("rsi", 50)
        atr = context.get("atr", 0)
        spread = context.get("spread", 0)
        session = context.get("session", "Unknown")

        prompt = f"""[SYSTEM INSTRUCTION]
{SYSTEM_INSTRUCTION}

[MARKET CONTEXT]
- Timeframe M15 Trend: {trend_m15}
- Timeframe M5 Trend: {trend_m5}
- RSI (14): {rsi}
- ATR: {atr}
- Spread: {spread} points
- Session: {session}

[LEARNING MEMORY]
{memory_section if memory_section else 'Belum ada memori trading.'}

[OUTPUT FORMAT]
{{"action": "BUY/SELL/HOLD", "confidence": <0-100>, "reason": "<maksimal 10 kata>"}}
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
        """
        FIX #17: Loop utama dengan provider performance tracking.
        """
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
                # FIX #17: Track success
                latency = (datetime.now() - start_time).total_seconds() * 1000
                self.provider_stats["successes"] += 1
                self.provider_stats["last_used"] = datetime.now().isoformat()
                # Update rolling average latency
                prev_avg = self.provider_stats["avg_latency_ms"]
                n = self.provider_stats["successes"]
                self.provider_stats["avg_latency_ms"] = ((prev_avg * (n-1)) + latency) / n
                
                self.last_decision = parsed
                return parsed

            print(f"[AI] Attempt {attempt+1}: failed to parse: {raw[:80]}...")

        # FIX #17: Track failure
        self.provider_stats["failures"] += 1
        
        fallback = {
            "action": "HOLD",
            "confidence": 0,
            "reason": "parsing error after retries",
        }
        self.last_decision = fallback
        return fallback

    async def self_reflect(self, trade_result: Dict[str, Any]) -> str:
        """
        Post-trade reflection: kirim prompt ke AI untuk self-reflection.
        """
        action = trade_result.get("action", "UNKNOWN")
        reason = trade_result.get("reason", "none")
        profit = trade_result.get("profit", 0)
        context = trade_result.get("context", {})
        result = "WIN" if profit > 0 else "LOSS"

        reflection_prompt = f"""
[SYSTEM INSTRUCTION]
Kamu adalah AI Trading yang mengevaluasi ulang keputusan trading sendiri.
Buat 1 kalimat lesson learned dalam Bahasa Indonesia, maksimal 20 kata.

[DETAIL TRADE]
- Action: {action}
- Alasan: {reason}
- Hasil: {result} ({profit} USC)
- RSI saat entry: {context.get('rsi', 'N/A')}
- ATR saat entry: {context.get('atr', 'N/A')}

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
