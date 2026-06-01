"""
Main Agent Orchestration.
Menggabungkan Market, AI, Risk, Execution dalam satu event loop async.
FIXED: Fase 7 (Learning), Daily Reset, Position Tracking, Context Staleness, Counter Timing
"""
import asyncio
import yaml
import MetaTrader5 as mt5
from datetime import datetime, date
from typing import Optional, Dict, Any

from core.market import MarketData
from core.indicators import compute_indicators, get_trend_label, get_latest_values
from core.ai import AIDecisionEngine
from core.risk import RiskManager
from core.execution import ExecutionEngine
from core.learning import LearningMemory
from core.database import init_database


class TradingAgent:
    """
    Orchestrator utama untuk trading agent.
    Menjalankan 7 fase alur sistem dengan fixes:
    - Fase 7 (Learning) implemented
    - Auto daily reset
    - Position tracking
    - Context always fresh
    - Counter timing fixed
    """

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        # Init database
        init_database(self.config.get("db_path", "db/sqlite.db"))

        # Init komponen
        self.market = MarketData(
            symbol=self.config.get("symbol", "XAUUSD"),
            atr_multiplier_limit=self.config.get("spread_multiplier_limit", 0.3),
        )
        self.ai = AIDecisionEngine(
            provider=self.config.get("provider", "ninerouter"),
            model=self.config.get("model", "auto"),
            db_path=self.config.get("db_path", "db/sqlite.db"),
            ninerouter_url=self.config.get("ninerouter_url", "http://localhost:20128/v1"),
            ninerouter_api_key=self.config.get("ninerouter_api_key", None),
        )
        self.risk = RiskManager(self.config)
        self.executor = ExecutionEngine(self.config)
        self.learning = LearningMemory(self.config.get("db_path", "db/sqlite.db"))

        # State
        self.running = False
        self.mode = self.config.get("mode", "assisted")
        self.last_decision: Optional[Dict[str, Any]] = None
        self.last_context: Optional[Dict[str, Any]] = None
        self.current_equity: float = 0.0
        self.daily_pnl: float = 0.0
        self.current_date: date = date.today()
        
        # FIX 3: Position tracking - map ticket → {decision, context, open_time}
        self.tracked_positions: Dict[int, Dict[str, Any]] = {}

    async def initialize(self) -> bool:
        """Fase 1: Booting & Inisialisasi"""
        for attempt in range(3):
            if mt5.initialize():
                print("[AGENT] MT5 initialized successfully")
                account = mt5.account_info()
                if account:
                    self.current_equity = account.equity
                    self.daily_pnl = account.profit
                    self.current_date = date.today()
                    self.risk.reset_daily_state(account.equity)
                    print(f"[AGENT] Account: {account.login} | Balance: {account.balance}")
                    return True
            print(f"[AGENT] MT5 init attempt {attempt+1} failed, retrying...")
            await asyncio.sleep(2)

        print("[AGENT] FATAL: MT5 initialization failed after 3 attempts")
        return False

    async def check_daily_reset(self):
        """FIX 2: Auto daily reset - cek date change"""
        today = date.today()
        if today != self.current_date:
            print(f"[AGENT] Date changed: {self.current_date} → {today}. Resetting daily state...")
            self.current_date = today
            account = mt5.account_info()
            if account:
                self.risk.reset_daily_state(account.equity)
                self.current_equity = account.equity
                print(f"[AGENT] Daily reset complete. New equity baseline: {account.equity}")

    async def data_gathering(self):
        """Fase 2: Data Gathering & Feature Engineering"""
        df_m5 = await self.market.update_m5()
        if df_m5 is not None and len(df_m5) > 50:
            df_m5 = compute_indicators(df_m5)
            if df_m5 is not None:
                self.market.trend_m5 = get_trend_label(df_m5)
                rsi, atr, _ = get_latest_values(df_m5)
                self.market.current_rsi = rsi
                self.market.current_atr = atr

        df_m15 = await self.market.update_m15()
        if df_m15 is not None and len(df_m15) > 50:
            df_m15 = compute_indicators(df_m15)
            if df_m15 is not None:
                self.market.trend_m15 = get_trend_label(df_m15)

    async def detect_closed_positions(self) -> list:
        """
        FIX 1: Deteksi posisi yang sudah close.
        Return list of closed position details.
        """
        if not self.tracked_positions:
            return []

        closed = []
        current_open_tickets = {p.ticket for p in await self.executor.get_open_positions()}
        
        for ticket, tracking_data in list(self.tracked_positions.items()):
            if ticket not in current_open_tickets:
                # Position sudah close, ambil detail dari history
                deals = mt5.history_deals_get(position=ticket)
                if deals and len(deals) >= 2:
                    # deals[0] = open, deals[-1] = close
                    open_deal = deals[0]
                    close_deal = deals[-1]
                    
                    closed_info = {
                        "ticket": ticket,
                        "type": "BUY" if open_deal.type == mt5.ORDER_TYPE_BUY else "SELL",
                        "entry_price": open_deal.price,
                        "close_price": close_deal.price,
                        "profit": close_deal.profit,
                        "open_time": datetime.fromtimestamp(open_deal.time),
                        "close_time": datetime.fromtimestamp(close_deal.time),
                        "decision": tracking_data["decision"],
                        "context": tracking_data["context"],
                    }
                    closed.append(closed_info)
                    
                # Remove dari tracking
                del self.tracked_positions[ticket]
                
        return closed

    async def process_closed_positions(self, closed_positions: list):
        """
        FIX 1: Fase 7 - Learning Engine.
        Process closed positions: save to DB, self-reflect, save lesson.
        """
        for pos in closed_positions:
            # Save trade to database
            self.learning.save_trade(
                ticket=pos["ticket"],
                order_type=pos["type"],
                entry_price=pos["entry_price"],
                close_price=pos["close_price"],
                profit=pos["profit"],
                open_time=pos["open_time"],
                close_time=pos["close_time"],
                ai_confidence=pos["decision"]["confidence"],
                ai_reason=pos["decision"]["reason"],
            )
            
            # AI self-reflection
            trade_result = {
                "action": pos["type"],
                "reason": pos["decision"]["reason"],
                "profit": pos["profit"],
                "context": pos["context"],
            }
            lesson = await self.ai.self_reflect(trade_result)
            
            # Save lesson to learning_memory
            result = "WIN" if pos["profit"] > 0 else "LOSS"
            self.learning.save_lesson(
                market_context=pos["context"],
                result=result,
                lesson=lesson,
            )
            
            # FIX 5: Increment counter saat position close, bukan saat open
            self.risk.today_trades += 1
            
            print(f"[AGENT] Fase 7 complete for ticket {pos['ticket']}: {result} {pos['profit']:.2f} USC")
            print(f"[AGENT] Lesson learned: {lesson}")

    async def run_cycle(self):
        """
        Satu siklus lengkap trading loop.
        FIXED: Context always fresh, Fase 7 implemented, counter timing fixed.
        """
        # FIX 2: Check daily reset
        await self.check_daily_reset()
        
        # Fase 2: Data gathering
        await self.data_gathering()

        # Update equity
        if mt5.terminal_info():
            account = mt5.account_info()
            if account:
                self.current_equity = account.equity
                self.daily_pnl = account.profit

        # FIX 4: Always get context (tidak skip meskipun ada posisi)
        context = await self.market.get_context()
        self.last_context = context

        # Cek spread
        spread_ok = await self.market.is_spread_acceptable()
        if not spread_ok:
            print("[AGENT] STANDBY: Spread too high")
            return

        # FIX 1: Fase 7 - Detect & process closed positions
        closed_positions = await self.detect_closed_positions()
        if closed_positions:
            await self.process_closed_positions(closed_positions)

        # Fase 6: Monitor existing positions
        positions = await self.executor.get_open_positions()
        if positions:
            await self.executor.monitor_positions(self.market.current_atr)
            return  # Skip AI decision jika masih ada posisi

        # Fase 3: AI Decision
        decision = await self.ai.decide(context)
        self.last_decision = decision

        print(f"[AGENT] AI Decision: {decision['action']} (conf: {decision['confidence']}%) - {decision['reason']}")

        if decision["action"] == "HOLD":
            self.risk.register_success()
            return

        # Fase 4: Risk validation
        validation = self.risk.validate(
            action=decision["action"],
            confidence=decision["confidence"],
            current_equity=self.current_equity,
            context=context,
        )

        if not validation["allowed"]:
            print(f"[AGENT] Risk blocked: {validation['reason']}")
            return

        # Fase 5: Execution
        if self.mode == "assisted":
            print(f"[AGENT] SIGNAL: {decision['action']} | Conf: {decision['confidence']}% | Reason: {decision['reason']}")
            return  # TUI akan handle konfirmasi

        # Auto mode: langsung eksekusi
        ticket = await self.executor.send_order(
            action=decision["action"],
            atr=self.market.current_atr,
            reason=decision["reason"],
        )

        if ticket:
            # FIX 3: Track position dengan decision & context
            self.tracked_positions[ticket] = {
                "decision": decision,
                "context": context.copy(),
                "open_time": datetime.now(),
            }
            # FIX 5: TIDAK increment counter di sini, tunggu sampai close
            self.risk.register_success()
            print(f"[AGENT] Position {ticket} tracked. Waiting for close to complete Fase 7...")
        else:
            self.risk.register_error()

    async def execute_signal_assisted(self, decision: Dict[str, Any], context: Dict[str, Any]) -> Optional[int]:
        """
        Helper untuk TUI: eksekusi sinyal yang sudah di-approve user.
        Return ticket number jika sukses.
        """
        ticket = await self.executor.send_order(
            action=decision["action"],
            atr=self.market.current_atr,
            reason=decision["reason"],
        )

        if ticket:
            # FIX 3: Track position
            self.tracked_positions[ticket] = {
                "decision": decision,
                "context": context.copy(),
                "open_time": datetime.now(),
            }
            self.risk.register_success()
            print(f"[AGENT] Position {ticket} tracked (assisted mode)")
            return ticket
        else:
            self.risk.register_error()
            return None

    async def run(self):
        """
        Main loop: Fase 2-7 berulang setiap 60 detik.
        Fase 6 (position monitoring) berjalan di setiap cycle.
        Fase 7 (learning) berjalan setelah posisi tertutup.
        """
        if not await self.initialize():
            return

        self.running = True
        print("[AGENT] Starting trading loop (60s interval)...")
        print("[AGENT] All 5 fixes applied: Fase 7, Daily Reset, Position Tracking, Context Fresh, Counter Timing")

        while self.running:
            try:
                await self.run_cycle()
            except Exception as e:
                print(f"[AGENT] Cycle error: {e}")
                import traceback
                traceback.print_exc()
                self.risk.register_error()

            await asyncio.sleep(60)

    def stop(self):
        """Hentikan trading loop"""
        self.running = False
        print("[AGENT] Stopping...")


async def main():
    agent = TradingAgent()
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
