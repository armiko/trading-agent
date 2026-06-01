"""
CLI command: trade models
Tampilkan model AI yang tersedia dari 9Router
(termasuk Ollama yang terhubung via 9Router)
"""
import sys
import asyncio


async def check_ninerouter():
    """Cek 9Router models (termasuk local Ollama via 9Router)"""
    try:
        from providers.ninerouter import NineRouterClient
        client = NineRouterClient()
        if await client.is_available():
            models = await client.list_models()
            return models
    except Exception:
        pass
    return None


async def run_models():
    """Entry point untuk 'trade models'"""
    print("\n=== AI PROVIDER (9Router) ===\n")

    print("9Router (http://localhost:20128/v1):")
    models = await check_ninerouter()
    if models:
        for m in models[:15]:
            print(f"   ✓ {m}")
        if len(models) > 15:
            print(f"   ... and {len(models) - 15} more")
        print(f"\n   Total: {len(models)} models available")
        print("\n   (termasuk local Ollama jika terhubung ke 9Router)")
    else:
        print("   ✗ 9Router not available")
        print("   Install: npm install -g 9router && 9router")

    print()
    print("Tips:")
    print("   - model: auto       → 9Router auto-routes ke best provider")
    print("   - model: ollama     → Use local Ollama via 9Router")
    print("   - model: kiro       → Use Kiro AI (free)")
    print("   - model: qwen       → Use Qwen (free)")
    print()
    print("   Config: python trade.py setup")
    print()


if __name__ == "__main__":
    asyncio.run(run_models())
