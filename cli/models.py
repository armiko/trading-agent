"""
CLI command: trade models
Tampilkan model AI yang tersedia dari Ollama dan 9Router
"""
import sys
import asyncio


async def check_ollama():
    """Cek Ollama models"""
    try:
        from providers.ollama import OllamaClient
        client = OllamaClient()
        if await client.is_available():
            models = await client.list_models()
            return models
    except Exception:
        pass
    return None


async def check_ninerouter():
    """Cek 9Router models"""
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
    print("\n=== AVAILABLE AI PROVIDERS ===\n")

    # Cek Ollama
    print("1. Ollama (http://localhost:11434):")
    ollama_models = await check_ollama()
    if ollama_models:
        for m in ollama_models:
            print(f"   ✓ {m}")
    else:
        print("   ✗ Not available")
        print("   Run: ollama serve")

    print()

    # Cek 9Router
    print("2. 9Router (http://localhost:20128/v1):")
    ninerouter_models = await check_ninerouter()
    if ninerouter_models:
        for m in ninerouter_models[:10]:  # show top 10
            print(f"   ✓ {m}")
        if len(ninerouter_models) > 10:
            print(f"   ... and {len(ninerouter_models) - 10} more")
    else:
        print("   ✗ Not available")
        print("   Run: npm install -g 9router && 9router")

    print()

    # Recommendations
    print("3. Recommendations:")
    print("   - Use 9Router for auto-fallback to 60+ providers")
    print("   - Use Ollama for local privacy (requires GPU)")
    print()
    print("   Edit config.yaml to switch:")
    print('     provider: ninerouter  # or ollama')
    print('     model: auto           # or specific model name')
    print()


if __name__ == "__main__":
    asyncio.run(run_models())
