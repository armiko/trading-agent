#!/usr/bin/env python3
"""
Setup Wizard untuk Xerynq.
Interactive configuration untuk parameter trading.
"""
import yaml
import os
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, FloatPrompt, Confirm
from rich.table import Table
from rich.align import Align
from rich import print as rprint

console = Console()

def print_header():
    header_text = "[bold cyan]🤖 XERYNQ - SETUP WIZARD[/bold cyan]\nInteractive Trading Agent Configuration"
    panel = Panel(Align.center(header_text), border_style="cyan", padding=(1, 2))
    console.print(panel)
    console.print("\n[dim]Setup wizard akan membantu Anda mengkonfigurasi trading agent.[/dim]")
    console.print("[dim]Tekan Enter untuk menggunakan nilai default.[/dim]\n")


def validate_symbol(value):
    """Validate trading symbol (accept any non-empty string)"""
    if not value or len(value) < 2:
        return False, "Symbol tidak boleh kosong dan minimal 2 karakter"
    return True, None


def main():
    print_header()
    
    # Trading Parameters
    console.print("[bold yellow]📊 TRADING PARAMETERS[/bold yellow]")
    console.print("[dim]" + "-" * 60 + "[/dim]")
    
    while True:
        symbol = Prompt.ask(
            "[cyan]Instrument/Symbol[/cyan]",
            default="XAUUSD"
        ).upper()
        valid, err = validate_symbol(symbol)
        if valid:
            break
        console.print(f"[bold red]❌ {err}[/bold red]")
    
    capital = FloatPrompt.ask(
        "[cyan]Modal/Capital (USC)[/cyan]",
        default=2000.0
    )
    
    lot = FloatPrompt.ask(
        "[cyan]Lot Size[/cyan]",
        default=0.01
    )
    
    max_trades = IntPrompt.ask(
        "[cyan]Max Trades Per Day[/cyan]",
        default=3
    )
    
    # Risk Parameters
    console.print("\n[bold yellow]⚠️  RISK MANAGEMENT[/bold yellow]")
    console.print("[dim]" + "-" * 60 + "[/dim]")
    
    confidence = FloatPrompt.ask(
        "[cyan]Confidence Threshold (%)[/cyan]",
        default=80.0
    )
    
    max_drawdown = FloatPrompt.ask(
        "[cyan]Max Drawdown Per Day (%)[/cyan]",
        default=5.0
    )
    
    kelly_fraction = FloatPrompt.ask(
        "[cyan]Kelly Fraction (0.1 - 1.0)[/cyan]",
        default=0.25
    )
    
    # AI Provider
    console.print("\n[bold yellow]🤖 AI PROVIDER[/bold yellow]")
    console.print("[dim]" + "-" * 60 + "[/dim]")
    
    provider = Prompt.ask(
        "[cyan]Provider[/cyan]",
        default="ninerouter",
        choices=["ninerouter"]
    ).lower()
    
    model = Prompt.ask(
        "[cyan]Model[/cyan]",
        default="auto"
    )
    
    # Trading Mode
    console.print("\n[bold yellow]🎮 TRADING MODE[/bold yellow]")
    console.print("[dim]" + "-" * 60 + "[/dim]")
    
    mode = Prompt.ask(
        "[cyan]Mode[/cyan]",
        default="assisted",
        choices=["assisted", "auto"]
    ).lower()
    
    # SaaS Auth
    console.print("\n[bold yellow]🔐 SAAS AUTHENTICATION[/bold yellow]")
    console.print("[dim]" + "-" * 60 + "[/dim]")
    
    saas_api_key = Prompt.ask(
        "[cyan]SaaS API Key (Dapatkan dari Web Dashboard)[/cyan]",
        default=""
    )
    
    saas_backend_url = Prompt.ask(
        "[cyan]SaaS Backend URL[/cyan]",
        default="http://127.0.0.1:8000/api/v1"
    )
    
    console.print("\n[bold green]✅ Setup Complete![/bold green]")
    
    # Summary Table
    table = Table(title="[bold]📋 CONFIGURATION SUMMARY[/bold]", show_header=False, box=None)
    table.add_column("Parameter", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Symbol", symbol)
    table.add_row("Capital", f"{capital} USC")
    table.add_row("Lot Size", str(lot))
    table.add_row("Max Trades/Day", str(max_trades))
    table.add_row("Confidence", f"{confidence}%")
    table.add_row("Max Drawdown", f"{max_drawdown}%")
    table.add_row("Kelly Fraction", str(kelly_fraction))
    table.add_row("SaaS API Key", saas_api_key[:10] + "..." if saas_api_key else "")
    table.add_row("AI Provider", provider)
    table.add_row("Model", model)
    table.add_row("Mode", mode)
    
    console.print("\n")
    console.print(Panel(Align.center(table), border_style="green"))
    console.print("\n")
    
    if not Confirm.ask("[bold]Simpan konfigurasi ini?[/bold]", default=True):
        console.print("\n[bold red]❌ Setup dibatalkan.[/bold red]")
        return
    
    # Build config
    config = {
        'symbol': symbol,
        'lot': float(lot),
        'provider': provider,
        'model': model,
        'mode': mode,
        'max_trades_per_day': int(max_trades),
        'confidence_threshold': int(confidence),
        'max_drawdown_percent': float(max_drawdown),
        'spread_multiplier_limit': 0.3,
        'circuit_breaker_max_errors': 3,
        'circuit_breaker_sleep_hours': 1,
        'atr_sl_multiplier': 1.5,
        'atr_tp_multiplier': 2.5,
        'atr_trailing_multiplier': 1.0,
        'breakeven_after_atr': 1.0,
        'kelly_fraction': float(kelly_fraction),
        'magic_number': 99999,
        'max_deviation': 10,
        'db_path': 'db/sqlite.db',
        'saas_api_key': saas_api_key,
        'saas_backend_url': saas_backend_url
    }
    
    if provider == 'ninerouter':
        config['ninerouter_url'] = 'http://localhost:20128/v1'
        config['ninerouter_api_key'] = None
    
    # Save config
    with open('config.yaml', 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    console.print("\n[bold green]✅ Konfigurasi berhasil disimpan ke config.yaml[/bold green]")
    console.print("\n[bold cyan]🚀 Next steps:[/bold cyan]")
    console.print("   1. Pastikan MT5 sudah running")
    console.print("   2. Jalankan: [green]9router[/green]")
    console.print("   3. Jalankan: [green]python trade.py start[/green]")
    console.print("\n[bold magenta]Happy Trading! 🎯[/bold magenta]\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[bold red]❌ Setup dibatalkan oleh user.[/bold red]")
    except Exception as e:
        console.print(f"\n\n[bold red]❌ Error: {e}[/bold red]")
