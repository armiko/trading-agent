"""
Main TUI application untuk trading agent.
Menggunakan Textual untuk interface terminal yang interaktif.
"""
import asyncio
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Button, Label, RichLog
from textual.reactive import reactive
from rich.text import Text

from core.agent import TradingAgent
from cli.tui.widgets import AccountPanel, MarketPanel


class SignalPanel(Static):
    """Panel untuk menampilkan sinyal AI"""
    action = reactive("HOLD")
    confidence = reactive(0)
    reason = reactive("")
    status = reactive("idle")

    def __init__(self):
        super().__init__()

    def update_signal(self, action: str, confidence: int, reason: str, status: str = "pending"):
        self.action = action
        self.confidence = confidence
        self.reason = reason
        self.status = status
        self.refresh()

    def render(self):
        action_color = "green" if self.action == "BUY" else "red" if self.action == "SELL" else "grey"
        status_color = "green" if self.status == "approved" else "yellow" if self.status == "pending" else "grey"
        
        return f"""[bold]CURRENT SIGNAL[/bold]
Action:     [{action_color}]{self.action}[/{action_color}]
Confidence: [white]{self.confidence}%[/white]
Reason:     [white]{self.reason}[/white]
Status:     [{status_color}]{self.status.upper()}[/{status_color}]
"""


class PositionsPanel(Static):
    """Panel untuk menampilkan posisi terbuka"""
    positions = reactive([])

    def __init__(self):
        super().__init__()
        self.positions = []

    def update_positions(self, positions: list):
        self.positions = positions
        self.refresh()

    def render(self):
        if not self.positions:
            return "[bold]OPEN POSITIONS[/bold]\n[grey]No open positions[/grey]"
        
        lines = ["[bold]OPEN POSITIONS[/bold]"]
        for pos in self.positions:
            pnl_color = "green" if pos.profit >= 0 else "red"
            pos_type = "BUY" if pos.type == 0 else "SELL"
            lines.append(
                f"{pos_type} {pos.symbol} | Lot: {pos.volume} | Entry: {pos.price_open} | PnL: [{pnl_color}]{pos.profit:+.2f}[/{pnl_color}]"
            )
        return "\n".join(lines)


class TradingTUI(App):
    """Main TUI application"""
    CSS = """
    Screen {
        layout: grid;
        grid-size: 2 3;
        grid-gutter: 1;
    }
    
    #account {
        column-span: 1;
        row-span: 1;
    }
    
    #market {
        column-span: 1;
        row-span: 1;
    }
    
    #signal {
        column-span: 2;
        row-span: 1;
    }
    
    #positions {
        column-span: 2;
        row-span: 1;
    }
    
    #log {
        column-span: 2;
        row-span: 1;
        height: 10;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("a", "approve", "Approve Signal"),
    ]

    def __init__(self):
        super().__init__()
        self.agent = TradingAgent()
        self.account_panel = AccountPanel()
        self.market_panel = MarketPanel()
        self.signal_panel = SignalPanel()
        self.positions_panel = PositionsPanel()
        self.log = RichLog(highlight=True, markup=True)
        self.running = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield self.account_panel.add_class("panel").set_id("account")
        yield self.market_panel.add_class("panel").set_id("market")
        yield self.signal_panel.add_class("panel").set_id("signal")
        yield self.positions_panel.add_class("panel").set_id("positions")
        yield self.log.set_id("log")
        yield Footer()

    async def on_mount(self) -> None:
        """FIX #19: Initialize agent saat TUI dimount dengan interval lebih cepat"""
        self.log.write("[bold green]Initializing trading agent...[/bold green]")
        
        if not await self.agent.initialize():
            self.log.write("[bold red]Failed to initialize MT5[/bold red]")
            return
        
        self.log.write("[bold green]Agent initialized successfully[/bold green]")
        self.running = True
        
        # FIX #19: Background workers dengan interval lebih cepat
        self.set_interval(60, self.update_market_data)     # Market: 60s
        self.set_interval(30, self.update_account_info)    # Account: 30s
        self.set_interval(10, self.update_positions)       # Positions: 10s (FIX #19)
        self.set_interval(60, self.check_signals)          # Signals: 60s (FIX #19: from 300s)
        
        self.log.write("[dim]Intervals: Market=60s, Account=30s, Positions=10s, Signals=60s[/dim]")

    async def update_market_data(self) -> None:
        """Update market data panel"""
        if not self.running:
            return
        
        try:
            await self.agent.data_gathering()
            context = await self.agent.market.get_context()
            
            self.market_panel.update_values(
                trend_m15=context.get("trend_m15", "NEUTRAL"),
                trend_m5=context.get("trend_m5", "NEUTRAL"),
                rsi=context.get("rsi", 50.0),
                atr=context.get("atr", 0.0),
                spread=context.get("spread", 0),
                session=context.get("session", "Unknown"),
            )
        except Exception as e:
            self.log.write(f"[red]Market data error: {e}[/red]")

    async def update_account_info(self) -> None:
        """Update account info panel"""
        if not self.running:
            return
        
        try:
            import MetaTrader5 as mt5
            if mt5.terminal_info():
                account = mt5.account_info()
                if account:
                    self.account_panel.update_values(
                        balance=account.balance,
                        equity=account.equity,
                        pnl=account.profit,
                    )
                    self.agent.current_equity = account.equity
        except Exception as e:
            self.log.write(f"[red]Account info error: {e}[/red]")

    async def update_positions(self) -> None:
        """Update positions panel"""
        if not self.running:
            return
        
        try:
            positions = await self.agent.executor.get_open_positions()
            self.positions_panel.update_positions(positions)
            
            # Monitor positions
            if positions:
                await self.agent.executor.monitor_positions(self.agent.market.current_atr)
        except Exception as e:
            self.log.write(f"[red]Positions error: {e}[/red]")

    async def check_signals(self) -> None:
        """Check for AI signals"""
        if not self.running:
            return
        
        try:
            # Skip jika ada posisi terbuka
            positions = await self.agent.executor.get_open_positions()
            if positions:
                return
            
            # Get AI decision
            context = await self.agent.market.get_context()
            decision = await self.agent.get_ai_decision(context)
            
            # Post-AI Sanity Check (S/R filter)
            decision = self.agent.validate_ai_sanity(decision, context)
            
            # Calculate optimal lot size
            optimal_lot = self.agent.position_sizer.calculate_lot_size(
                current_equity=self.agent.current_equity,
                sl_distance=self.agent.market.current_atr * self.agent.config.get("atr_sl_multiplier", 1.5)
            )
            decision["optimal_lot"] = optimal_lot
            self.agent.last_decision = decision
            
            if decision["action"] == "HOLD":
                return
            
            # Validate dengan risk manager
            validation = self.agent.risk.validate(
                action=decision["action"],
                confidence=decision["confidence"],
                current_equity=self.agent.current_equity,
                context=context,
            )
            
            if not validation["allowed"]:
                self.log.write(f"[yellow]Signal blocked: {validation['reason']}[/yellow]")
                return
            
            # Update signal panel
            self.signal_panel.update_signal(
                action=decision["action"],
                confidence=decision["confidence"],
                reason=decision["reason"],
                status="pending",
            )
            
            self.log.write(
                f"[bold cyan]NEW SIGNAL: {decision['action']} | Conf: {decision['confidence']}% | {decision['reason']}[/bold cyan]"
            )
            self.log.write("[yellow]Press 'a' to approve or wait for next cycle[/yellow]")
            
        except Exception as e:
            self.log.write(f"[red]Signal check error: {e}[/red]")

    async def action_approve(self) -> None:
        """Approve dan eksekusi sinyal"""
        if self.signal_panel.status != "pending":
            self.log.write("[yellow]No pending signal to approve[/yellow]")
            return
        
        try:
            # Use agent's execute_signal_assisted method (includes position tracking)
            decision = self.agent.last_decision if self.agent.last_decision else {
                "action": self.signal_panel.action,
                "confidence": self.signal_panel.confidence,
                "reason": self.signal_panel.reason,
            }
            context = self.agent.last_context or {}
            
            ticket = await self.agent.execute_signal_assisted(decision, context)
            
            if ticket:
                self.signal_panel.update_signal(
                    action=self.signal_panel.action,
                    confidence=self.signal_panel.confidence,
                    reason=self.signal_panel.reason,
                    status="approved",
                )
                self.log.write(f"[bold green]Order executed: Ticket #{ticket}[/bold green]")
            else:
                self.log.write("[bold red]Order execution failed[/bold red]")
        except Exception as e:
            self.log.write(f"[red]Execution error: {e}[/red]")

    async def action_refresh(self) -> None:
        """Manual refresh semua data"""
        self.log.write("[cyan]Refreshing all data...[/cyan]")
        await self.update_market_data()
        await self.update_account_info()
        await self.update_positions()

    async def action_quit(self) -> None:
        """Quit aplikasi"""
        self.running = False
        self.log.write("[bold yellow]Shutting down...[/bold yellow]")
        import MetaTrader5 as mt5
        mt5.shutdown()
        self.exit()


async def run_tui():
    """Entry point untuk TUI"""
    app = TradingTUI()
    await app.run_async()


if __name__ == "__main__":
    asyncio.run(run_tui())
