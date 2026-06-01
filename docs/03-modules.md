# Module Documentation

## Core Modules

### 1. agent.py - Main Orchestrator

**Fungsi Utama:** Menggabungkan semua komponen dalam satu event loop async.

**Method Penting:**
- `__init__()` - Initialize semua komponen (market, ai, risk, execution, dll)
- `initialize()` - Fase 1: MT5 connect, load config, load tracked positions
- `run_cycle()` - Satu siklus trading loop (Fase 2-7)
- `data_gathering()` - Fetch M5/M15 candles, calculate indicators
- `detect_closed_positions()` - Detect posisi yang sudah close
- `process_closed_positions()` - Fase 7: Save to DB, self-reflection, learn
- `run()` - Main loop dengan dynamic sleep interval

**State Management:**
```python
self.tracked_positions: Dict[int, Dict]  # ticket -> position data
self.last_decision: Optional[Dict]       # Last AI decision
self.last_context: Optional[Dict]        # Last market context
self.current_equity: float               # Current account equity
self.daily_pnl: float                    # Today's P&L
```

**Integration Points:**
- DXY Correlation (optional)
- Position Sizer (dynamic lot)
- Trailing Stop Manager
- Performance Tracker
- AI Ensemble (optional)

---

### 2. market.py - Data Gathering

**Fungsi Utama:** Fetch data dari MT5 dan kalkulasi indikator teknikal.

**Method Penting:**
- `update_m5()` - Fetch M5 candles (tiap 1 menit)
- `update_m15()` - Fetch M15 candles (cached, tiap 15 menit)
- `fetch_spread()` - Real-time spread check
- `is_spread_acceptable()` - Validate spread < 30% ATR
- `get_context()` - Build comprehensive market context untuk AI

**Context Output:**
```json
{
  "trend_m15": "BULLISH",
  "trend_m5": "BULLISH",
  "rsi": 62.5,
  "atr": 15.2,
  "ema_diff": 2.3,
  "spread": 10,
  "session": "London",
  "market_structure": {...},
  "price_action": {...},
  "support_resistance": {...}
}
```

---

### 3. ai.py - AI Decision Engine

**Fungsi Utama:** Build prompt, call AI provider, parse response.

**Method Penting:**
- `build_prompt()` - Build comprehensive prompt dengan context + learning memory
- `call_provider()` - API call ke 9Router
- `_parse_json_response()` - Parse JSON dari AI response
- `decide()` - Main decision loop dengan retry logic
- `self_reflect()` - Post-trade reflection untuk learning

**Prompt Structure:**
```
[SYSTEM INSTRUCTION]
Kamu adalah AI Trading Quantitative...

[MARKET CONTEXT]
- Trend M15: Bullish
- RSI: 62
- ATR: 15
...

[LEARNING MEMORY]
- Hindari BUY saat RSI > 70
...

[ANALYSIS RULES]
1. Harga dekat Resistance + RSI > 70 = SELL
...

[OUTPUT FORMAT]
{"action": "BUY/SELL/HOLD", "confidence": 0-100, "reason": "..."}
```

---

### 4. risk.py - Risk Manager

**Fungsi Utama:** Validasi apakah sinyal boleh dieksekusi.

**Validation Checks:**
1. Action bukan BUY/SELL → Block
2. Confidence < threshold (80%) → Block
3. Today trades >= max (3) → Block
4. Drawdown >= 5% → Block (HIBERNATE)
5. Directional conflict (BUY vs M15 Bearish) → Block
6. RSI > 68 untuk BUY / RSI < 32 untuk SELL → Block
7. Circuit breaker aktif → Block

**Circuit Breaker:**
```
3 errors → Hibernate 1 minute
4 errors → Hibernate 5 minutes
5 errors → Hibernate 15 minutes
6+ errors → Hibernate 1 hour
```

---

### 5. execution.py - Order Execution

**Fungsi Utama:** Kirim order ke MT5 dengan TP/SL dinamis.

**Method Penting:**
- `send_order()` - Kirim order dengan SL/TP (ATR-based)
- `modify_position()` - Update SL/TP posisi
- `close_position()` - Force close posisi
- `monitor_positions()` - Trailing stop, breakeven, time-based exit

**SL/TP Calculation:**
```python
# BUY
SL = Entry - (ATR × 1.5)
TP = Entry + (ATR × 2.5)

# SELL
SL = Entry + (ATR × 1.5)
TP = Entry - (ATR × 2.5)
```

---

### 6. learning.py - Learning Memory

**Fungsi Utama:** Trade history & self-reflection.

**Method Penting:**
- `save_trade()` - Save trade ke `trade_history`
- `save_lesson()` - Save lesson ke `learning_memory`
- `get_weighted_memory()` - Ambil 3 loss + 2 win terakhir

**Self-Reflection Prompt:**
```
Kamu baru saja eksekusi BUY dengan alasan Trend alignment.
Hasilnya LOSS -15 USC. Kondisi: RSI 72, ATR 8.
Buat 1 kalimat lesson learned.
```

---

### 7. indicators.py - Technical Indicators

**Fungsi Utama:** Kalkulasi indikator teknikal menggunakan pandas_ta.

**Indicators:**
- **Trend:** EMA_20, EMA_50, EMA_200, MACD
- **Momentum:** RSI_14, Stochastic, ROC, MOM
- **Volatility:** ATR_14, Bollinger Bands, BB Width
- **Volume:** Volume SMA, Volume Ratio
- **Market Structure:** Support/Resistance, Price Action, Market Structure

**Method Penting:**
- `compute_indicators()` - Kalkulasi semua indikator
- `get_trend_label()` - Tentukan trend berdasarkan EMA
- `get_latest_values()` - Ambil RSI, ATR, EMA_diff terakhir
- `get_enhanced_context()` - Build comprehensive context untuk AI

---

### 8. correlation.py - DXY Correlation

**Fungsi Utama:** Track korelasi XAUUSD dengan Dollar Index.

**Method Penting:**
- `fetch_dxy_data()` - Ambil data DXY (atau proxy EURUSD/GBPUSD)
- `get_correlation_signal()` - Calculate correlation & generate signal

**Signal Output:**
```json
{
  "correlation": -0.85,
  "dxy_trend": "BULLISH",
  "dxy_change_pct": 0.5,
  "divergence": "NONE",
  "signal_bias": "CONFIRM_BUY"
}
```

**Divergence Detection:**
- `BULLISH_DIVERGENCE` - Gold up + DXY up → AVOID_BUY
- `BEARISH_DIVERGENCE` - Gold down + DXY down → AVOID_SELL

---

### 9. position_sizer.py - Dynamic Position Sizing

**Fungsi Utama:** Calculate optimal lot size berdasarkan Kelly Criterion & Volatility.

**Method Penting:**
- `calculate_kelly_lot()` - Kelly Criterion sizing
- `calculate_volatility_lot()` - ATR-based sizing
- `calculate_optimal_lot()` - Conservative blend (minimum of both)

**Kelly Formula:**
```
f* = (p × b - q) / b
di mana:
  p = win rate
  q = 1 - p
  b = avg_win / avg_loss
```

---

### 10. trailing_stop.py - Trailing Stop Manager

**Fungsi Utama:** Manage trailing stop loss secara adaptif.

**Method Penting:**
- `update_trailing_stop()` - Update SL berdasarkan profit & ATR
- `should_breakeven()` - Check apakah layak di-breakeven

**Trailing Logic:**
1. **Breakeven (Profit ≥ 1R):** SL → Entry + (ATR × 0.2)
2. **Lock Profit (Profit ≥ 2R):** SL → Current - (ATR × 1.5)
3. **Aggressive Trail (Profit ≥ 3R):** SL → Current - (ATR × 0.5)

---

### 11. performance_tracker.py - Live Performance Monitor

**Fungsi Utama:** Track live performance vs backtest expectations.

**Method Penting:**
- `start_tracking()` - Initialize dengan starting equity
- `record_trade()` - Record hasil trade
- `get_metrics()` - Get current performance metrics
- `check_deviation()` - Compare live vs backtest

**Metrics Tracked:**
- Win rate
- Profit factor
- Max drawdown
- Sample size (statistical significance)

**Alert Conditions:**
- Win rate deviation > 15%
- Profit factor < 70% dari backtest
- Drawdown > 130% dari backtest

---

### 12. ai_ensemble.py - AI Ensemble Voting

**Fungsi Utama:** Multiple AI models dengan majority voting.

**Method Penting:**
- `decide_ensemble()` - Run multiple models & vote
- `get_ensemble_stats()` - Get voting statistics

**Voting Logic:**
1. Run 2-3 models secara parallel
2. Count votes untuk setiap action
3. Majority action → Final decision
4. Average confidence dari majority models
5. Require minimum agreement (default: 2 models)

---

### 13. regime.py - Market Regime Classifier

**Fungsi Utama:** Classify market condition (Trending/Ranging/Volatile).

**Regime Types:**
- `TRENDING` - Strong directional movement (ADX > 25)
- `RANGING` - Sideways/consolidation (ADX < 20)
- `VOLATILE` - High volatility without clear direction

**Method Penting:**
- `classify()` - Classify current market regime
- `get_adaptive_params()` - Get recommended params berdasarkan regime

---

### 14. news_filter.py - Economic Calendar Filter

**Fungsi Utama:** Filter trading berdasarkan economic news.

**Method Penting:**
- `get_high_impact_news()` - Ambil high impact news
- `is_news_around()` - Check apakah ada news dalam buffer time

**Buffer Time:** Default 30 menit sebelum/after news

---

### 15. backtest.py - Historical Backtesting

**Fungsi Utama:** Backtest strategy dengan historical data.

**Method Penting:**
- `run_backtest()` - Run backtest simulation
- `calculate_metrics()` - Calculate performance metrics

**Metrics:**
- Total trades
- Win rate
- Profit factor
- Max drawdown
- Sharpe ratio
- Profit factor
- Walk-forward analysis
