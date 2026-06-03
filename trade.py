"""
Main CLI entry point untuk trading agent.
Usage:
  python trade.py setup     - Interactive setup wizard
  python trade.py config    - Lihat/edit config saat ini
  python trade.py status    - Cek koneksi MT5
  python trade.py report    - Lihat ringkasan performa dan riwayat trading
  python trade.py models    - List available AI models
  python trade.py start     - Start TUI trading agent
  python trade.py run       - Run headless (auto mode)
"""
import sys
import asyncio
import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.align import Align

console = Console()

def print_usage():
    console.print("\n[bold cyan]Usage:[/bold cyan] python trade.py [command]")
    console.print("\n[bold]Commands:[/bold]")
    console.print("  [green]setup[/green]        Interactive setup wizard")
    console.print("  [green]config[/green]       Tampilkan/edit konfigurasi saat ini")
    console.print("  [green]status[/green]       Cek koneksi MT5 & balance")
    console.print("  [green]report[/green]       Lihat laporan performa (Win/Loss, PnL, AI Reason)")
    console.print("  [green]models[/green]       List AI provider (9Router)")
    console.print("  [green]start[/green]        Start TUI (assisted mode)")
    console.print("  [green]run[/green]          Run headless (auto mode)\n")


def validate_config(config: dict) -> list:
    """Validasi konfigurasi, return list of warnings"""
    warnings = []
    
    # Required fields
    required = ["symbol", "lot", "mode"]
    for field in required:
        if field not in config:
            warnings.append(f"Missing required field: [bold]{field}[/bold]")
    
    # Symbol validation
    valid_symbols = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD"]
    if config.get("symbol") not in valid_symbols:
        warnings.append(f"Invalid symbol: [bold]{config.get('symbol')}[/bold]. Valid: {', '.join(valid_symbols)}")
    
    # Numeric validations
    if "lot" in config:
        lot_val = config["lot"]
        try:
            lot_val = float(lot_val)
            if lot_val <= 0:
                warnings.append("Lot must be > 0")
        except (ValueError, TypeError):
            warnings.append("Lot must be a number")
    
    max_trades_val = config.get("max_trades_per_day", 1)
    try:
        max_trades_val = int(max_trades_val)
        if max_trades_val < 1:
            warnings.append("max_trades_per_day must be >= 1")
    except (ValueError, TypeError):
        warnings.append("max_trades_per_day must be an integer")
    
    conf_val = config.get("confidence_threshold", 80)
    try:
        conf_val = float(conf_val)
        if conf_val < 0 or conf_val > 100:
            warnings.append(f"confidence_threshold must be 0-100, got {conf_val}")
    except (ValueError, TypeError):
        warnings.append("confidence_threshold must be a number")
    
    dd_val = config.get("max_drawdown_percent", 5)
    try:
        dd_val = float(dd_val)
        if dd_val <= 0 or dd_val > 100:
            warnings.append(f"max_drawdown_percent must be 1-100, got {dd_val}")
    except (ValueError, TypeError):
        warnings.append("max_drawdown_percent must be a number")
    
    provider = config.get("provider")
    if provider:
        warnings.append("ℹ️  'provider' field is deprecated and unused. AI routing uses 'ninerouter_url' config directly.")
    
    return warnings


def show_config():
    """Tampilkan konfigurasi saat ini dengan validasi"""
    try:
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
        
        # Validate
        warnings = validate_config(config)
        if warnings:
            console.print("\n[bold yellow]⚠️  CONFIG WARNINGS:[/bold yellow]")
            for w in warnings:
                console.print(f"   ❌ {w}")
            console.print()
        
        table = Table(title="[bold cyan]CURRENT CONFIGURATION[/bold cyan]", show_header=True, header_style="bold magenta")
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Symbol", str(config.get('symbol', 'N/A')))
        table.add_row("Lot Size", str(config.get('lot', 'N/A')))
        table.add_row("Capital/Equity", "- (dari MT5)")
        table.add_row("Max Trades/Day", str(config.get('max_trades_per_day', 'N/A')))
        table.add_row("Confidence", f"{config.get('confidence_threshold', 'N/A')}%")
        table.add_row("Max Drawdown", f"{config.get('max_drawdown_percent', 'N/A')}%")
        table.add_row("AI Provider", str(config.get('provider', 'N/A')))
        table.add_row("Model", str(config.get('model', 'N/A')))
        table.add_row("Mode", str(config.get('mode', 'N/A')))
        
        learning_str = f"{config.get('learning_loss_count', 3)} loss + {config.get('learning_win_count', 2)} win"
        table.add_row("Learning Loss/Win", learning_str)
        
        console.print("\n")
        console.print(Panel(Align.center(table), border_style="cyan"))
        console.print("\n[dim]To edit, run: python trade.py setup[/dim]\n")
        
    except FileNotFoundError:
        console.print("\n[bold red]❌ File config.yaml tidak ditemukan.[/bold red]")
        console.print("Jalankan [green]python trade.py setup[/green] terlebih dahulu.\n")
    except Exception as e:
        console.print(f"\n[bold red]❌ Error membaca/validasi config: {e}[/bold red]\n")


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

    elif command == "report":
        limit = 3
        if "--limit" in sys.argv:
            try:
                idx = sys.argv.index("--limit")
                limit = int(sys.argv[idx + 1])
            except (ValueError, IndexError):
                pass
        from cli.report import run_report
        run_report(limit)

    elif command == "models":
        from cli.models import run_models
        asyncio.run(run_models())

    elif command == "start":
        try:
            with open("config.yaml", "r") as f:
                config = yaml.safe_load(f)
            warnings = validate_config(config)
            if warnings:
                console.print("\n[bold yellow]⚠️  CONFIG VALIDATION WARNINGS:[/bold yellow]")
                for w in warnings:
                    console.print(f"   ❌ {w}")
                
                from rich.prompt import Confirm
                if not Confirm.ask("\n[bold]Continue anyway?[/bold]", default=False):
                    console.print("[red]Aborted.[/red] Fix config with: [green]python trade.py setup[/green]")
                    sys.exit(1)
        except FileNotFoundError:
            console.print("\n[bold red]❌ File config.yaml tidak ditemukan.[/bold red]")
            sys.exit(1)
        except Exception as e:
            console.print(f"\n[bold red]❌ Config validation failed: {e}[/bold red]")
            sys.exit(1)
        
        from cli.start import run_tui
        asyncio.run(run_tui())

    elif command == "run":
        try:
            with open("config.yaml", "r") as f:
                config = yaml.safe_load(f)
            warnings = validate_config(config)
            if warnings:
                console.print("\n[bold red]❌ CONFIG VALIDATION FAILED:[/bold red]")
                for w in warnings:
                    console.print(f"   ❌ {w}")
                console.print("\nFix config with: [green]python trade.py setup[/green]")
                sys.exit(1)
        except FileNotFoundError:
            console.print("\n[bold red]❌ File config.yaml tidak ditemukan.[/bold red]")
            sys.exit(1)
        except Exception as e:
            console.print(f"\n[bold red]❌ Config validation failed: {e}[/bold red]")
            sys.exit(1)
        
        from core.agent import TradingAgent
        agent = TradingAgent()
        asyncio.run(agent.run())

    else:
        console.print(f"[bold red]Unknown command: {command}[/bold red]")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
