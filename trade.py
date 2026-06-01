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


def validate_config(config: dict) -> list:
    """FIX #14: Validasi konfigurasi, return list of warnings"""
    warnings = []
    
    # Required fields
    required = ["symbol", "lot", "provider", "mode"]
    for field in required:
        if field not in config:
            warnings.append(f"Missing required field: {field}")
    
    # Symbol validation
    valid_symbols = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD"]
    if config.get("symbol") not in valid_symbols:
        warnings.append(f"Invalid symbol: {config.get('symbol')}. Valid: {valid_symbols}")
    
    # Numeric validations
    if config.get("lot", 0) <= 0:
        warnings.append("Lot must be > 0")
    if config.get("max_trades_per_day", 1) < 1:
        warnings.append("max_trades_per_day must be >= 1")
    conf = config.get("confidence_threshold", 80)
    if conf < 0 or conf > 100:
        warnings.append(f"confidence_threshold must be 0-100, got {conf}")
    dd = config.get("max_drawdown_percent", 5)
    if dd <= 0 or dd > 100:
        warnings.append(f"max_drawdown_percent must be 1-100, got {dd}")
    
    # Provider validation
    if config.get("provider") not in ["ninerouter"]:
        warnings.append(f"provider must be 'ninerouter', got {config.get('provider')}")
    
    return warnings


def show_config():
    """FIX #14: Tampilkan konfigurasi saat ini dengan validasi"""
    try:
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
        
        # Validate
        warnings = validate_config(config)
        if warnings:
            print("\n⚠️  CONFIG WARNINGS:")
            for w in warnings:
                print(f"   ❌ {w}")
            print()
        
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
        print(f"Learning Loss/ Win:  {config.get('learning_loss_count', 3)} loss + {config.get('learning_win_count', 2)} win")
        print()
        print("To edit, run: python trade.py setup")
        print()
    except FileNotFoundError:
        print("\n❌ config.yaml tidak ditemukan.")
        print("Run: python trade.py setup")
        print()
    except yaml.YAMLError:
        print("\n❌ config.yaml invalid YAML format.")
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
        # FIX #14: Validate config before starting
        try:
            with open("config.yaml", "r") as f:
                config = yaml.safe_load(f)
            warnings = validate_config(config)
            if warnings:
                print("\n⚠️  CONFIG VALIDATION WARNINGS:")
                for w in warnings:
                    print(f"   ❌ {w}")
                confirm = input("\nContinue anyway? (y/n): ").strip().lower()
                if confirm != 'y':
                    print("Aborted. Fix config with: python trade.py setup")
                    sys.exit(1)
        except Exception as e:
            print(f"\n❌ Config validation failed: {e}")
            sys.exit(1)
        
        from cli.start import run_tui
        asyncio.run(run_tui())

    elif command == "run":
        # FIX #14: Validate config before running
        try:
            with open("config.yaml", "r") as f:
                config = yaml.safe_load(f)
            warnings = validate_config(config)
            if warnings:
                print("\n❌ CONFIG VALIDATION FAILED:")
                for w in warnings:
                    print(f"   ❌ {w}")
                print("\nFix config with: python trade.py setup")
                sys.exit(1)
        except Exception as e:
            print(f"\n❌ Config validation failed: {e}")
            sys.exit(1)
        
        from core.agent import TradingAgent
        agent = TradingAgent()
        asyncio.run(agent.run())

    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
