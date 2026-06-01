"""
9Router Provider: Smart AI router dengan 3-tier fallback.
OpenAI-compatible endpoint ke 60+ AI providers.
https://9router.com
"""
import aiohttp
import asyncio
from typing import Optional, Dict, Any


class NineRouterClient:
    def __init__(
        self,
        base_url: str = "http://localhost:20128/v1",
        model: str = "auto",
        api_key: Optional[str] = None,
    ):
        self.base_url = base_url
        self.model = model
        self.api_key = api_key or "9router-local"
        self.chat_url = f"{base_url}/chat/completions"

    async def generate(
        self, prompt: str, timeout: int = 30, temperature: float = 0.1
    ) -> Optional[str]:
        """
        Kirim prompt ke 9router dengan OpenAI-compatible format.
        9router akan auto-route ke provider terbaik dengan fallback.
        """
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": 128,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.chat_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        print(f"[9ROUTER] HTTP {resp.status}: {text[:150]}")
                        return None
                    data = await resp.json()
                    return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except asyncio.TimeoutError:
            print(f"[9ROUTER] Timeout after {timeout}s")
            return None
        except Exception as e:
            print(f"[9ROUTER] Error: {e}")
            return None

    async def is_available(self) -> bool:
        """Cek apakah 9router server hidup"""
        try:
            async with aiohttp.ClientSession() as session:
                # Try /v1/models endpoint (OpenAI-compatible)
                async with session.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=aiohttp.ClientTimeout(total=3),
                ) as resp:
                    return resp.status == 200
        except Exception:
            return False

    async def list_models(self) -> list:
        """Dapatkan daftar model yang tersedia di 9router"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
                    return [m["id"] for m in data.get("data", [])]
        except Exception:
            return []
