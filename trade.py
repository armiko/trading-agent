"""
Main CLI entry point untuk trading agent.
Usage:
  python trade.py setup     - Interactive setup wizard
  python trade.py config    - Lihat/edit config saat ini
  python trade.py status    - Cek koneksi MT5
  python trade.py models    - List available AI models
  python trade.py start     - Start TUI trading agent
  python trade.py run       - Run headless (auto mode)
"""
import sys
import asyncio
import yaml


def print_usage():
    print("Usage: python trade.py [setup|config|status|models|start|run]")
    print("")
    print("Commands:")
    print("  setup        Interactive setup wizard")
    print("  config       Tampilkan/edit konfigurasi saat ini")
    print("  status       Cek koneksi MT5 & balance")
    print("  models       List AI providers (9Router & Ollama)")
    print("  start        Start TUI (assisted mode)")
    print("  run          Run headless (auto mode)")


def show_config():
    """Tampilkan konfigurasi saat ini"""
    try:
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
        
        print("\n=== CURRENT CONFIGURATION ===\n")
        print(f"Symbol:              {config.get('symbol', 'N/A')}")
        print(f"Lot Size:            {config.get('lot', 'N/A')}")
        print(f"Capital/Equity:      - (dari MT5)")
        print(f"Max Trades/Day:      {config.get('max_trades_per_day', 'N/A')}")
        print(f"Confidence:          {config.get('confidence_threshold', 'N/A')}%")
        print(f"Max Drawdown:        {config.get('max_drawdown_percent', 'N/A')}%")
        print(f"AI Provider:         {config.get('provider', 'N/A')}")
        print(f"Model:               {config.get('model', 'N/A')}")
        print(f"Mode:                {config.get('mode', 'N/A')}")
        print()
        print("To edit, run: python trade.py setup")
        print()
    except FileNotFoundError:
        print("\n❌ config.yaml tidak ditemukan.")
        print("Run: python trade.py setup")
        print()


def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1]

    if command == "setup":
        # Setup wizard
        exec(open("setup_wizard.py").read())

    elif command == "config":
        show_config()

    elif command == "status":
        from cli.status import run_status
        run_status()

    elif command == "models":
        from cli.models import run_models
        asyncio.run(run_models())

    elif command == "start":
        from cli.start import run_tui
        asyncio.run(run_tui())

    elif command == "run":
        from core.agent import TradingAgent
        agent = TradingAgent()
        asyncio.run(agent.run())

    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
