"""
CLI command: trade report
Menampilkan detail statistik Win/Loss, PnL, dan alasan AI berdasarkan riwayat trading.
"""
import sqlite3
import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.align import Align

console = Console()

def run_report(limit: int = 3):
    try:
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        console.print("[bold red]❌ File config.yaml tidak ditemukan. Jalankan setup terlebih dahulu.[/bold red]")
        return
        
    db_path = config.get("db_path", "db/sqlite.db")
    
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Hitung Win/Loss dari trade_history
        c.execute("SELECT profit FROM trade_history")
        trades = c.fetchall()
        
        if not trades:
            console.print(Panel(Align.center("[bold yellow]Belum ada riwayat trading.[/bold yellow]"), border_style="yellow"))
            return
            
        total_trades = len(trades)
        wins = [t[0] for t in trades if t[0] > 0]
        losses = [t[0] for t in trades if t[0] <= 0]
        
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0
        total_profit = sum(wins)
        total_loss = sum(losses)
        net_pnl = total_profit + total_loss
        
        # Summary Table
        summary_table = Table(title="[bold cyan]📊 TRADING PERFORMANCE SUMMARY[/bold cyan]", show_header=False)
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="green")
        
        summary_table.add_row("Total Trades", str(total_trades))
        summary_table.add_row("Win Rate", f"{win_rate:.1f}%")
        summary_table.add_row("Wins / Losses", f"{win_count} Wins / {loss_count} Losses")
        summary_table.add_row("Gross Profit", f"+{total_profit:.2f}")
        summary_table.add_row("Gross Loss", f"{total_loss:.2f}")
        
        pnl_color = "green" if net_pnl >= 0 else "red"
        summary_table.add_row("Net PnL", f"[{pnl_color}]{net_pnl:.2f}[/{pnl_color}]")
        
        console.print("\n")
        console.print(Panel(Align.center(summary_table), border_style="cyan"))
        
        # Last Trades Table
        console.print(f"\n[bold yellow]📝 RECENT TRADES (LAST {limit})[/bold yellow]")
        
        c.execute("""
            SELECT ticket, type, profit, ai_reason, close_time 
            FROM trade_history 
            ORDER BY close_time DESC LIMIT ?
        """, (limit,))
        recent_trades = c.fetchall()
        
        if recent_trades:
            for trade in recent_trades:
                ticket, action, profit, reason, close_time = trade
                p_color = "green" if profit > 0 else "red"
                sign = "+" if profit > 0 else ""
                
                # Coba ambil lesson learned dari DB memory (opsional)
                lesson = ""
                try:
                    c.execute("SELECT lesson FROM learning_memory WHERE date(date) = date(?) ORDER BY id DESC LIMIT 1", (close_time,))
                    res = c.fetchone()
                    if res:
                        lesson = res[0]
                except Exception:
                    pass
                
                t_table = Table(show_header=False, box=None, padding=(0, 2))
                t_table.add_column("Key", style="dim cyan", width=15)
                t_table.add_column("Value")
                
                t_table.add_row("Ticket", str(ticket))
                t_table.add_row("Action", action)
                t_table.add_row("Profit", f"[{p_color}]{sign}{profit:.2f}[/{p_color}]")
                t_table.add_row("AI Reason", reason)
                if lesson:
                    t_table.add_row("Lesson Learned", f"[italic yellow]{lesson}[/italic yellow]")
                
                console.print(Panel(t_table, title=f"Trade {close_time}", title_align="left", border_style="dim"))
        
        conn.close()
        
    except sqlite3.Error as e:
        console.print(f"[bold red]❌ Error database: {e}[/bold red]")

if __name__ == "__main__":
    import sys
    limit = 3
    if len(sys.argv) > 2 and sys.argv[1] == "--limit":
        try:
            limit = int(sys.argv[2])
        except ValueError:
            pass
    run_report(limit)
