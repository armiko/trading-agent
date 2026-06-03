"""
Main Agent Orchestration.
Menggabungkan Market, AI, Risk, Execution dalam satu event loop async.
FIXES: Fase 7, Daily Reset, Position Tracking, Context Staleness, Counter Timing
"""
import asyncio
import yaml
import json
import os
import MetaTrader5 as mt5
from datetime import datetime, date
from typing import Optional, Dict, Any
import random

from core.market import MarketData
from core.indicators import compute_indicators, get_trend_label, get_latest_values
from core.ai import AIDecisionEngine
from core.risk import RiskManager
from core.execution import ExecutionEngine
from core.learning import LearningMemory
from core.database import init_database
from core.regime import RegimeClassifier, MarketRegime
from core.news_filter import EconomicCalendar

# NEW INTEGRATIONS
from core.correlation import CurrencyCorrelation
from core.position_sizer import PositionSizer
from core.trailing_stop import TrailingStopManager
from core.performance_tracker import LivePerformanceTracker
from core.ai_ensemble import AIEnsemble
from core.confluence import calculate_confluence


class TradingAgent:
    """
    Orchestrator utama untuk trading agent.
    Menjalankan 7 fase alur sistem.
    FIXES: Fase 7, Daily Reset, Position Tracking, Context Fresh, Counter Timing
    """

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        # Init database
        init_database(self.config.get("db_path", "db/sqlite.db"))

        # FIX #16: Generate unique magic number jika masih default
        default_magic = 99999
        if self.config.get("magic_number", default_magic) == default_magic:
            self.config["magic_number"] = int(f"999{random.randint(1000, 9999)}")
            print(f"[AGENT] Generated unique magic number: {self.config['magic_number']}")

        # Init komponen
        self.market = MarketData(
            symbol=self.config.get("symbol", "XAUUSD"),
            atr_multiplier_limit=self.config.get("spread_multiplier_limit", 0.3),
        )
        # FIX: Single 9Router provider (tidak perlu param provider= lagi)
        self.ai = AIDecisionEngine(
            model=self.config.get("model", "auto"),
            db_path=self.config.get("db_path", "db/sqlite.db"),
            ninerouter_url=self.config.get("ninerouter_url", "http://localhost:20128/v1"),
            ninerouter_api_key=self.config.get("ninerouter_api_key"),
        )
        self.risk = RiskManager(self.config)
        self.executor = ExecutionEngine(self.config)
        self.learning = LearningMemory(
            self.config.get("db_path", "db/sqlite.db"),
            loss_count=self.config.get("learning_loss_count", 3),
            win_count=self.config.get("learning_win_count", 2)
        )

        # State
        self.running = False
        self.mode = self.config.get("mode", "assisted")
        self.last_decision: Optional[Dict[str, Any]] = None
        self.last_context: Optional[Dict[str, Any]] = None
        self.current_equity: float = 0.0
        self.daily_pnl: float = 0.0
        self.current_date: date = date.today()

        # FIX 3: Position tracking - map ticket -> {decision, context, open_time}
        self.tracked_positions: Dict[int, Dict[str, Any]] = {}
        self.tracked_positions_file = "db/tracked_positions.json"

        # FIX #13: Signal expiry for assisted mode
        self.signal_timestamp: Optional[datetime] = None
        self.signal_expiry_minutes = 5

        # ENHANCEMENT: Regime classifier
        self.regime_enabled = self.config.get("regime_adaptive", False)
        if self.regime_enabled:
            self.regime_classifier = RegimeClassifier(
                adx_trending_threshold=self.config.get("regime_adx_trending", 25.0),
                adx_ranging_threshold=self.config.get("regime_adx_ranging", 20.0),
            )
            print("[AGENT] Regime classifier enabled")
        else:
            self.regime_classifier = None

        # ENHANCEMENT: News filter
        self.news_filter_enabled = self.config.get("news_filter_enabled", False)
        if self.news_filter_enabled:
            self.news_calendar = EconomicCalendar(
                buffer_minutes=self.config.get("news_buffer_minutes", 30),
                currencies=self.config.get("news_currencies", ["USD", "EUR"]),
            )
            print("[AGENT] News filter enabled")
        else:
            self.news_calendar = None

        # ENHANCEMENT: Session filter
        self.session_filter_enabled = self.config.get("session_filter_enabled", False)
        self.allowed_sessions = self.config.get("allowed_sessions", ["London", "New York"])
        self.avoid_sessions = self.config.get("avoid_sessions", ["Asia"])

        # NEW INTEGRATIONS
        # DXY Correlation tracker
        self.dxy_enabled = self.config.get("dxy_correlation_enabled", False)
        if self.dxy_enabled:
            self.dxy_correlation = CurrencyCorrelation(symbol=self.config.get("symbol", "XAUUSD"))
            print("[AGENT] DXY correlation tracking enabled")
        else:
            self.dxy_correlation = None

        # Position Sizer
        self.position_sizer = PositionSizer(self.config)
        print("[AGENT] Position sizer initialized")

        # Trailing Stop Manager
        self.trailing_stop = TrailingStopManager(
            atr_multiplier=self.config.get("atr_trailing_multiplier", 1.5),
            breakeven_buffer=self.config.get("breakeven_buffer_atr", 0.2)
        )
        print("[AGENT] Trailing stop manager initialized")
        
        # Connect trailing stop to executor
        self.executor.set_trailing_stop_manager(self.trailing_stop)

        # Performance Tracker
        self.performance_tracker = LivePerformanceTracker(
            db_path=self.config.get("db_path", "db/sqlite.db")
        )
        self.performance_tracker.load_state()
        print("[AGENT] Performance tracker initialized")

        # AI Ensemble (optional - use multiple models)
        self.ensemble_enabled = self.config.get("ai_ensemble_enabled", False)
        if self.ensemble_enabled:
            secondary_models = self.config.get("ai_ensemble_models", [])
            self.ai_ensemble = AIEnsemble(
                primary_model=self.config.get("model", "auto"),
                secondary_models=secondary_models,
                db_path=self.config.get("db_path", "db/sqlite.db"),
                ninerouter_url=self.config.get("ninerouter_url", "http://localhost:20128/v1"),
                ninerouter_api_key=self.config.get("ninerouter_api_key"),
                min_agreement=self.config.get("ai_ensemble_min_agreement", 2)
            )
            print("[AGENT] AI Ensemble enabled")
        else:
            self.ai_ensemble = None

    def save_tracked_positions(self):
        """FIX #4: Persist tracked positions to file"""
        try:
            os.makedirs("db", exist_ok=True)
            serializable = {}
            for ticket, data in self.tracked_positions.items():
                serializable[str(ticket)] = {
                    "decision": data["decision"],
                    "context": data["context"],
                    "open_time": data["open_time"].isoformat() if isinstance(data["open_time"], datetime) else data["open_time"]
                }
            with open(self.tracked_positions_file, "w") as f:
                json.dump(serializable, f, indent=2)
        except Exception as e:
            print(f"[AGENT] Warning: Failed to save tracked positions: {e}")

    def load_tracked_positions(self):
        """FIX #4: Load tracked positions from file"""
        try:
            if os.path.exists(self.tracked_positions_file):
                with open(self.tracked_positions_file, "r") as f:
                    data = json.load(f)
                for ticket_str, pos_data in data.items():
                    ticket = int(ticket_str)
                    pos_data["open_time"] = datetime.fromisoformat(pos_data["open_time"])
                    self.tracked_positions[ticket] = pos_data
                print(f"[AGENT] Loaded {len(self.tracked_positions)} tracked positions from file")
        except Exception as e:
            print(f"[AGENT] Warning: Failed to load tracked positions: {e}")

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
                    # FIX #4: Load tracked positions from file
                    self.load_tracked_positions()
                    return True
            print(f"[AGENT] MT5 init attempt {attempt+1} failed, retrying...")
            await asyncio.sleep(2)

        print("[AGENT] FATAL: MT5 initialization failed after 3 attempts")
        return False

    async def check_daily_reset(self):
        """FIX #7: Auto daily reset"""
        today = date.today()
        if today != self.current_date:
            print(f"[AGENT] Date changed: {self.current_date} -> {today}. Resetting daily state...")
            self.current_date = today
            account = mt5.account_info()
            if account:
                self.risk.reset_daily_state(account.equity)
                self.current_equity = account.equity

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
        FIX 3: Handle partial close dengan volume comparison.
        Return list of closed position details.
        """
        if not self.tracked_positions:
            return []

        closed = []
        modified = False
        current_open_tickets = {p.ticket for p in await self.executor.get_open_positions()}

        for ticket, tracking_data in list(self.tracked_positions.items()):
            if ticket not in current_open_tickets:
                deals = mt5.history_deals_get(position=ticket)
                if deals and len(deals) >= 2:
                    open_deal = deals[0]

                    # FIX 3: Check if fully closed by comparing entry vs exit volume
                    entry_volume = sum(
                        d.volume for d in deals
                        if d.entry == mt5.DEAL_ENTRY_IN
                    )
                    exit_volume = sum(
                        d.volume for d in deals
                        if d.entry == mt5.DEAL_ENTRY_OUT
                    )

                    if exit_volume < entry_volume * 0.999:
                        # Partial close detected — find continuation ticket
                        new_positions = mt5.positions_get(symbol=self.executor.symbol)
                        if new_positions:
                            for p in new_positions:
                                if (
                                    p.magic == self.executor.magic
                                    and p.ticket not in self.tracked_positions
                                ):
                                    self.tracked_positions[p.ticket] = tracking_data
                                    print(
                                        f"[AGENT] Partial close detected: {ticket} → "
                                        f"remainder at {p.ticket} "
                                        f"(exit {exit_volume:.2f}/{entry_volume:.2f})"
                                    )
                                    break
                        del self.tracked_positions[ticket]
                        modified = True
                        continue

                    # Fully closed — sum all exit deal profits
                    total_profit = sum(
                        d.profit for d in deals
                        if d.entry == mt5.DEAL_ENTRY_OUT
                    )
                    close_deal = deals[-1]

                    closed_info = {
                        "ticket": ticket,
                        "type": "BUY" if open_deal.type == mt5.ORDER_TYPE_BUY else "SELL",
                        "entry_price": open_deal.price,
                        "close_price": close_deal.price,
                        "profit": total_profit,
                        "open_time": datetime.fromtimestamp(open_deal.time),
                        "close_time": datetime.fromtimestamp(close_deal.time),
                        "decision": tracking_data["decision"],
                        "context": tracking_data["context"],
                    }
                    closed.append(closed_info)

                del self.tracked_positions[ticket]
                modified = True

        # Save after any tracked position changes
        if closed or modified:
            self.save_tracked_positions()

        return closed

    async def process_closed_positions(self, closed_positions: list):
        """
        FIX 1: Fase 7 - Learning Engine.
        Process closed positions: save to DB, self-reflect, save lesson.
        """
        for pos in closed_positions:
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

            trade_result = {
                "action": pos["type"],
                "reason": pos["decision"]["reason"],
                "profit": pos["profit"],
                "context": pos["context"],
            }
            lesson = await self.ai.self_reflect(trade_result)

            result = "WIN" if pos["profit"] > 0 else "LOSS"
            self.learning.save_lesson(
                market_context=pos["context"],
                result=result,
                lesson=lesson,
            )

            # FIX 5: Increment counter saat position close, bukan saat open
            self.risk.today_trades += 1
            
            # NEW: Update performance tracker
            self.performance_tracker.record_trade(pos["profit"], self.current_equity)

            print(f"[AGENT] Fase 7 complete for ticket {pos['ticket']}: {result} {pos['profit']:.2f} USC")
            print(f"[AGENT] Lesson learned: {lesson}")

    def validate_ai_sanity(self, decision: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Hard overrides for AI hallucinations."""
        action = decision.get("action", "HOLD")
        if action == "HOLD":
            return decision
            
        rsi = context.get("rsi", 50)
        
        # Hard override: Extreme RSI
        if action == "BUY" and rsi > 80:
            return {"action": "HOLD", "confidence": 0, "reason": "Override: RSI extreme overbought"}
        if action == "SELL" and rsi < 20:
            return {"action": "HOLD", "confidence": 0, "reason": "Override: RSI extreme oversold"}
            
        # Hard override: Trading directly into S/R
        current_price = context.get("current_price", 0)
        sr = context.get("support_resistance", {})
        
        if current_price > 0:
            if action == "BUY":
                dist = sr.get("dist_to_resistance_pct", 1.0)
                if dist < 0.1:
                    return {"action": "HOLD", "confidence": 0, "reason": "Override: Too close to resistance"}
            elif action == "SELL":
                dist = sr.get("dist_to_support_pct", 1.0)
                if dist < 0.1:
                    return {"action": "HOLD", "confidence": 0, "reason": "Override: Too close to support"}
                    
        return decision

    async def get_ai_decision(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Dapatkan keputusan dari AI (Single atau Ensemble)."""
        if self.ensemble_enabled and self.ai_ensemble:
            return await self.ai_ensemble.decide_ensemble(context)
        return await self.ai.decide(context)

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
                # Initialize performance tracker if needed
                if self.performance_tracker.starting_equity is None:
                    self.performance_tracker.start_tracking(account.equity)

        # FIX 4: Always get context (tidak skip meskipun ada posisi)
        context = await self.market.get_context()
        self.last_context = context

        # FIX 4b: Early return if market is closed
        if context.get("reason") == "Market closed (weekend)":
            print("[AGENT] Market closed (weekend). Skipping cycle.")
            return

        # NEW: Apply Regime Classification
        if self.regime_enabled and self.regime_classifier and self.market._cache_m5 is not None:
            regime_info = self.regime_classifier.classify(self.market._cache_m5, self.market.current_atr)
            context["regime"] = regime_info["regime"].value
            context["regime_confidence"] = regime_info["confidence"]
            context["regime_reasoning"] = regime_info["reasoning"]

        # NEW: Session Filter
        if self.session_filter_enabled:
            current_session = self.market.session
            if current_session in self.avoid_sessions:
                print(f"[AGENT] Avoiding {current_session} session. Skipping.")
                return
        
        # NEW: Enhance context with DXY correlation data
        if self.dxy_enabled and self.dxy_correlation:
            df_dxy = await self.dxy_correlation.fetch_dxy_data()
            df_gold = self.market._cache_h1  # Gunakan H1 agar sama dengan df_dxy (menghindari error NaN correlation)
            if df_dxy is not None and df_gold is not None:
                dxy_signal = self.dxy_correlation.get_correlation_signal(df_gold, df_dxy)
                context["dxy_signal"] = dxy_signal
                # Print DXY warning for divergence
                if dxy_signal.get("divergence", "NONE") != "NONE":
                    print(f"[AGENT] DXY Divergence: {dxy_signal['divergence']} - {dxy_signal['signal_bias']}")

        # Cek spread
        spread_ok = await self.market.is_spread_acceptable()
        if not spread_ok:
            print("[AGENT] STANDBY: Spread too high")
            return

        # NEW: News Filter
        if self.news_filter_enabled and self.news_calendar:
            if self.news_calendar.is_news_around():
                print("[AGENT] High-impact news nearby. Skipping trade.")
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

        # Fase 3: AI Decision (dengan opsi Ensemble)
        decision = await self.get_ai_decision(context)
        if self.ensemble_enabled and self.ai_ensemble:
            print(f"[AGENT] Ensemble Decision: {decision['action']} ({decision.get('ensemble_agreement', 100)}% agreement)")
            
        # Post-AI Sanity Check
        decision = self.validate_ai_sanity(decision, context)
        self.last_decision = decision

        print(f"[AGENT] AI Decision: {decision['action']} (conf: {decision['confidence']}%) - {decision['reason']}")

        if decision["action"] == "HOLD":
            return
            
        # Confluence Scoring
        confluence_score = calculate_confluence(decision["action"], context)
        print(f"[AGENT] Confluence Score: {confluence_score}/7")
        if confluence_score < 3:
            print(f"[AGENT] Blocked by low confluence ({confluence_score} < 3)")
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
        
        # NEW: DXY correlation risk check
        # FIX 2: Do NOT call register_success() on block — consistent with risk validation
        dxy_signal = context.get("dxy_signal", {})
        if dxy_signal.get("signal_bias") == "AVOID_BUY" and decision["action"] == "BUY":
            print(f"[AGENT] DXY Correlation blocked BUY: {dxy_signal.get('divergence', 'NONE')}")
            return
        if dxy_signal.get("signal_bias") == "AVOID_SELL" and decision["action"] == "SELL":
            print(f"[AGENT] DXY Correlation blocked SELL: {dxy_signal.get('divergence', 'NONE')}")
            return
        
        # NEW: Calculate optimal lot size using position sizer
        optimal_lot = self.position_sizer.calculate_optimal_lot(
            equity=self.current_equity,
            atr=self.market.current_atr,
            win_rate=self.performance_tracker.get_metrics().get("win_rate", 50) / 100,
            avg_win=self.performance_tracker.get_metrics().get("total_profit", 50) / max(self.performance_tracker.get_metrics().get("wins", 1), 1),
            avg_loss=self.performance_tracker.get_metrics().get("total_loss", 30) / max(self.performance_tracker.get_metrics().get("losses", 1), 1),
            point=self.executor._get_point_value()
        )
        print(f"[AGENT] Position sizing: lot={optimal_lot} (from base={self.config.get('lot', 0.01)})")
        
        # Update config lot untuk digunakan oleh executor
        self.config["lot"] = optimal_lot

        # Fase 5: Execution
        if self.mode == "assisted":
            print(f"[AGENT] SIGNAL: {decision['action']} | Conf: {decision['confidence']}% | Lot: {optimal_lot} | Reason: {decision['reason']}")
            # FIX #13: Simpan timestamp untuk signal expiry
            self.signal_timestamp = datetime.now()
            # Simpan optimal_lot di decision untuk digunakan saat approve
            decision["optimal_lot"] = optimal_lot
            self.last_decision = decision
            return  # TUI akan handle konfirmasi

        # Auto mode: langsung eksekusi (gunakan optimal_lot)
        ticket = await self.executor.send_order(
            action=decision["action"],
            atr=self.market.current_atr,
            reason=decision["reason"],
            lot=optimal_lot
        )

        if ticket:
            # FIX 3: Track position dengan decision & context
            self.tracked_positions[ticket] = {
                "decision": decision,
                "context": context.copy(),
                "open_time": datetime.now(),
            }
            # FIX #4: Save tracked positions to file
            self.save_tracked_positions()
            # FIX 5: TIDAK increment counter di sini, tunggu sampai close
            self.risk.register_success()
            print(f"[AGENT] Position {ticket} tracked. Waiting for close to complete Fase 7...")
        else:
            self.risk.register_error()

    async def execute_signal_assisted(self, decision: Dict[str, Any], context: Dict[str, Any]) -> Optional[int]:
        """
        FIX #13: Helper untuk TUI dengan signal expiry check.
        """
        # FIX #13: Check signal expiry
        if self.signal_timestamp:
            elapsed = (datetime.now() - self.signal_timestamp).total_seconds() / 60
            if elapsed > self.signal_expiry_minutes:
                print(f"[AGENT] Signal expired ({elapsed:.1f} min > {self.signal_expiry_minutes} min). Re-validating...")
                fresh_context = await self.market.get_context()
                validation = self.risk.validate(
                    action=decision["action"],
                    confidence=decision["confidence"],
                    current_equity=self.current_equity,
                    context=fresh_context,
                )
                if not validation["allowed"]:
                    print(f"[AGENT] Re-validation failed: {validation['reason']}")
                    return None
                context = fresh_context

        # Gunakan optimal_lot dari decision jika ada
        lot_to_use = decision.get("optimal_lot", self.config.get("lot", 0.01))
        ticket = await self.executor.send_order(
            action=decision["action"],
            atr=self.market.current_atr,
            reason=decision["reason"],
            lot=lot_to_use
        )

        if ticket:
            self.tracked_positions[ticket] = {
                "decision": decision,
                "context": context.copy(),
                "open_time": datetime.now(),
            }
            self.save_tracked_positions()
            self.risk.register_success()
            print(f"[AGENT] Position {ticket} tracked (assisted mode)")
            return ticket
        else:
            self.risk.register_error("mt5")
            return None

    async def run(self):
        """
        Main loop: Fase 2-7 berulang.
        FIX #2: Monitoring 10s saat ada posisi, 60s saat idle.
        """
        if not await self.initialize():
            return

        self.running = True
        print("[AGENT] Starting trading loop...")

        while self.running:
            try:
                await self.run_cycle()
            except Exception as e:
                print(f"[AGENT] Cycle error: {e}")
                import traceback
                traceback.print_exc()
                self.risk.register_error()

            # FIX #2: Dynamic sleep interval
            positions = await self.executor.get_open_positions()
            sleep_interval = 10 if positions else 60
            await asyncio.sleep(sleep_interval)

    def stop(self):
        """Hentikan trading loop"""
        self.running = False
        print("[AGENT] Stopping...")


async def main():
    agent = TradingAgent()
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())