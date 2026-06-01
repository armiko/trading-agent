"""
Base Ollama API caller.
Komunikasi dengan Ollama server di localhost:11434
"""
import aiohttp
import asyncio
from typing import Optional


class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.generate_url = f"{base_url}/api/generate"
        self.models_url = f"{base_url}/api/tags"

    async def generate(
        self, model: str, prompt: str, timeout: int = 30, temperature: float = 0.1
    ) -> Optional[str]:
        """Kirim prompt dan dapatkan response"""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": 128},
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.generate_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        print(f"[OLLAMA] HTTP {resp.status}: {text[:150]}")
                        return None
                    data = await resp.json()
                    return data.get("response", "")
        except asyncio.TimeoutError:
            print(f"[OLLAMA] Timeout after {timeout}s")
            return None
        except Exception as e:
            print(f"[OLLAMA] Error: {e}")
            return None

    async def list_models(self) -> list:
        """Dapatkan daftar model yang tersedia di Ollama"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.models_url, timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
                    return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    async def is_available(self) -> bool:
        """Cek apakah Ollama server hidup"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.base_url, timeout=aiohttp.ClientTimeout(total=3)
                ) as resp:
                    return resp.status == 200
        except Exception:
            return False
