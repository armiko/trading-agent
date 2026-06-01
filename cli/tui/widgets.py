"""
Custom widgets untuk TUI trading agent.
"""
from textual.widgets import Static, DataTable, Label
from textual.reactive import reactive
from typing import Optional


class StatusLabel(Static):
    """Label dengan status dinamis"""
    status = reactive("idle")

    def __init__(self, text: str = "", status: str = "idle"):
        super().__init__(text)
        self.status = status

    def watch_status(self, new_status: str):
        if new_status == "active":
            self.update(f"[green]● {self.text}")
        elif new_status == "standby":
            self.update(f"[yellow]● {self.text}")
        elif new_status == "error":
            self.update(f"[red]● {self.text}")
        else:
            self.update(f"[grey]● {self.text}")


class AccountPanel(Static):
    """Panel informasi akun"""
    balance = reactive(0.0)
    equity = reactive(0.0)
    pnl = reactive(0.0)

    def __init__(self):
        super().__init__("Account Panel")
        self.balance = 0.0
        self.equity = 0.0
        self.pnl = 0.0

    def update_values(self, balance: float, equity: float, pnl: float):
        self.balance = balance
        self.equity = equity
        self.pnl = pnl
        self.refresh()

    def render(self):
        pnl_color = "green" if self.pnl >= 0 else "red"
        return f"""[bold]ACCOUNT (CENT)[/bold]
Balance: [white]{self.balance:.2f} USC[/white]
Equity:  [white]{self.equity:.2f} USC[/white]
PnL Day: [{pnl_color}]{self.pnl:+.2f} USC[/{pnl_color}]
"""


class MarketPanel(Static):
    """Panel informasi pasar"""
    trend_m15 = reactive("NEUTRAL")
    trend_m5 = reactive("NEUTRAL")
    rsi = reactive(50.0)
    atr = reactive(0.0)
    spread = reactive(0)
    session = reactive("Unknown")

    def __init__(self):
        super().__init__("Market Panel")

    def update_values(
        self,
        trend_m15: str,
        trend_m5: str,
        rsi: float,
        atr: float,
        spread: int,
        session: str,
    ):
        self.trend_m15 = trend_m15
        self.trend_m5 = trend_m5
        self.rsi = rsi
        self.atr = atr
        self.spread = spread
        self.session = session
        self.refresh()

    def render(self):
        trend_m15_color = "green" if self.trend_m15 == "BULLISH" else "red" if self.trend_m15 == "BEARISH" else "grey"
        trend_m5_color = "green" if self.trend_m5 == "BULLISH" else "red" if self.trend_m5 == "BEARISH" else "grey"
        spread_color = "green" if self.spread < 15 else "yellow" if self.spread < 30 else "red"

        return f"""[bold]MARKET ANALYSIS[/bold]
Trend M15: [{trend_m15_color}]{self.trend_m15}[/{trend_m15_color}]
Trend M5:  [{trend_m5_color}]{self.trend_m5}[/{trend_m5_color}]
RSI (14):  [white]{self.rsi:.1f}[/white]
ATR:       [white]{self.atr:.1f}[/white]
Spread:    [{spread_color}]{self.spread} points[/{spread_color}]
Session:   [white]{self.session}[/white]
"""
