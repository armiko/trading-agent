# AI Context - Quick Understanding Guide

> **Untuk AI/LLM:** File ini berisi ringkasan cepat agar AI dapat memahami project ini dalam 2 menit.

## 🎯 Apa Ini?

**AI Trading Agent** = Bot trading otomatis yang menggunakan AI (LLM) untuk analisis teknikal XAUUSD (Gold) dan generate sinyal BUY/SELL/HOLD.

## 🏗️ Struktur Project (Simplified)

```
trading-agent/
├── trade.py              # Entry point CLI
├── config.yaml           # Konfigurasi utama
├── core/                 # Business logic
│   ├── agent.py         # Main orchestrator (7 fase trading loop)
│   ├── market.py        # Data gathering M5/M15 + indicators
│   ├── ai.py            # AI decision engine (prompt + parse)
│   ├── risk.py          # Risk validation (drawdown, confidence)
│   ├── execution.py     # Order execution ke MT5
│   ├── learning.py      # Trade history + self-reflection
│   └── [8 advanced modules]
├── cli/                  # CLI interface
│   ├── start.py         # TUI dashboard
│   └── status.py        # MT5 status check
└── providers/
    └── ninerouter.py    # 9Router AI integration
```

## 🔄 Trading Loop (7 Fase)

1. **Initialize** → Connect MT5, load config
2. **Data Gathering** → Fetch candles, calculate indicators (RSI, EMA, ATR)
3. **AI Decision** → Build prompt → Call AI → Parse JSON response
4. **Risk Validation** → Check drawdown, confidence, circuit breaker
5. **Execution** → Send order dengan SL/TP dinamis
6. **Position Monitoring** → Trailing stop, breakeven, time-based exit
7. **Post-Trade Learning** → Save to DB, self-reflection, update memory

## 🧠 AI Integration

### Input ke AI (Prompt)
```json
{
  "market_context": {
    "trend_m15": "BULLISH",
    "trend_m5": "BULLISH",
    "rsi": 62,
    "atr": 15,
    "spread": 10,
    "session": "London",
    "support_resistance": {...},
    "price_action": {...},
    "market_structure": {...}
  },
  "learning_memory": [
    "Hindari BUY saat RSI > 70",
    "ATR < 10 = market sideways"
  ]
}
```

### Output dari AI (Expected)
```json
{
  "action": "BUY",
  "confidence": 87,
  "reason": "Trend alignment + RSI normal"
}
```

## 🚀 Advanced Features

| Feature | File | Fungsi |
|---------|------|--------|
| **DXY Correlation** | `correlation.py` | Track korelasi Gold ↔ USD Index |
| **Position Sizer** | `position_sizer.py` | Kelly + ATR-based lot sizing |
| **Trailing Stop** | `trailing_stop.py` | ATR-based adaptive SL |
| **Performance Tracker** | `performance_tracker.py` | Live vs backtest monitoring |
| **AI Ensemble** | `ai_ensemble.py` | Multiple models voting |
| **Enhanced Indicators** | `indicators.py` | S/R, Price Action, Market Structure |

## 📝 Konfigurasi Penting

```yaml
# config.yaml
symbol: XAUUSD
lot: 0.01
mode: assisted              # assisted = manual approval, auto = fully automated
max_trades_per_day: 3
confidence_threshold: 80    # Minimum AI confidence
max_drawdown_percent: 5     # Daily drawdown limit

# Advanced
dxy_correlation_enabled: true
risk_per_trade_pct: 1.0
ai_ensemble_enabled: false
```

## 🔧 CLI Commands

```bash
python trade.py setup    # Interactive setup wizard
python trade.py status   # Check MT5 connection
python trade.py start    # Start TUI (assisted mode)
python trade.py run      # Run headless (auto mode)
```

## 🗄️ Database

**SQLite** (`db/sqlite.db`):
- `trade_history` - Semua trade yang pernah dieksekusi
- `learning_memory` - Lesson learned dari AI self-reflection

## 🎨 Tech Stack

- **Python 3.10+** - Main language
- **MetaTrader 5** - Trading platform
- **9Router** - AI provider (60+ models, auto-fallback)
- **SQLite** - Database
- **Textual** - TUI framework
- **pandas_ta** - Technical indicators
- **asyncio** - Async event loop

## 🔍 Cara Kerja AI Decision

### 1. Build Prompt (`ai.py:build_prompt()`)
```python
prompt = f"""
[SYSTEM INSTRUCTION]
Kamu adalah AI Trading Quantitative.
OUTPUT: JSON {"action": "BUY/SELL/HOLD", "confidence": 0-100, "reason": "..."}

[MARKET CONTEXT]
- Trend M15: {trend_m15}
- RSI: {rsi}
- ATR: {atr}
...

[LEARNING MEMORY]
{lessons from database}

[ANALYSIS RULES]
1. Harga dekat Resistance + RSI > 70 = SELL
2. Harga dekat Support + RSI < 30 = BUY
...
"""
```

### 2. Call AI (`ai.py:call_provider()`)
```python
response = await ninerouter_client.generate(prompt)
```

### 3. Parse Response (`ai.py:_parse_json_response()`)
```python
result = json.loads(response)
if result["action"] not in ["BUY", "SELL", "HOLD"]:
    return None  # Invalid
return result
```

### 4. Validate (`risk.py:validate()`)
```python
if confidence < 80:
    return {"allowed": False, "reason": "Low confidence"}
if today_trades >= 3:
    return {"allowed": False, "reason": "Max trades reached"}
# ... more checks
return {"allowed": True}
```

## 🛡️ Safety Features

1. **Circuit Breaker** - Auto-hibernate setelah 3 error berturut-turut
2. **Drawdown Limit** - Stop trading jika loss > 5% per hari
3. **Confidence Threshold** - Hanya eksekusi jika AI confidence ≥ 80%
4. **Directional Conflict** - Block BUY jika trend M15 bearish
5. **Spread Check** - Skip jika spread > 30% ATR
6. **DXY Divergence** - Block jika Gold & DXY bergerak anomali

## 📊 Performance Monitoring

**Performance Tracker** (`performance_tracker.py`) monitor:
- Win rate (live vs backtest)
- Profit factor (live vs backtest)
- Max drawdown (live vs backtest)
- Sample size (statistical significance)

**Alert jika:**
- Win rate deviation > 15%
- Profit factor < 70% dari backtest
- Drawdown > 130% dari backtest

## 🔄 State Management

### Runtime State
```python
self.tracked_positions = {}  # ticket -> {decision, context, open_time}
self.last_decision = None    # Last AI decision
self.last_context = None     # Last market context
self.current_equity = 0.0    # Current account equity
```

### Persistent State
```
db/sqlite.db                 # Trade history & learning
db/tracked_positions.json    # Open positions
db/performance_state.json    # Performance metrics
config.yaml                  # Configuration
```

## 🐛 Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| MT5 not connected | Check MT5 running + "Allow automated trading" enabled |
| 9Router not available | Run `9router` in terminal |
| Spread too high | Bot auto-skip, wait for spread to decrease |
| Drawdown limit reached | Bot hibernate, reset tomorrow |
| Circuit breaker active | Bot sleep 1 hour, auto-resume |

## 📚 Dokumentasi Lengkap

- `docs/01-overview.md` - Project overview
- `docs/02-architecture.md` - System architecture
- `docs/03-modules.md` - Module documentation
- `docs/04-cli_commands.md` - CLI guide
- `docs/05-configuration.md` - Configuration reference
- `docs/06-development.md` - Development guide
- `docs/07-maintenance.md` - Maintenance checklist

## 🎯 Quick Mental Model

```
User runs: python trade.py start
    ↓
Agent starts trading loop (every 60s):
    ↓
1. Fetch market data (M5/M15 candles)
    ↓
2. Calculate indicators (RSI, EMA, ATR, S/R, Price Action)
    ↓
3. Build prompt with context + learning memory
    ↓
4. Call AI → Get decision (BUY/SELL/HOLD)
    ↓
5. Validate with risk manager
    ↓
6. If allowed → Execute order to MT5
    ↓
7. Monitor position → Trailing stop → Close
    ↓
8. Save to DB → AI self-reflection → Learn
    ↓
(repeat)
```

## 🚀 Untuk AI Developer

Jika Anda adalah AI yang sedang membantu develop project ini:

1. **Main entry point:** `trade.py`
2. **Core logic:** `core/agent.py` (method `run_cycle()`)
3. **AI integration:** `core/ai.py` (method `decide()`)
4. **Risk rules:** `core/risk.py` (method `validate()`)
5. **Konfigurasi:** `config.yaml` atau `config.template.yaml`

**Untuk menambah fitur baru:**
1. Buat module di `core/` (misal: `core/new_feature.py`)
2. Import di `core/agent.py`
3. Initialize di `agent.__init__()`
4. Integrate di `agent.run_cycle()`
5. Update `config.template.yaml` jika perlu config baru
6. Update dokumentasi di `docs/`

**Untuk debugging:**
1. Cek log di TUI panel
2. Cek `db/sqlite.db` untuk trade history
3. Cek `db/tracked_positions.json` untuk open positions
4. Run `python trade.py status` untuk cek MT5 connection

---

**Selamat coding! 🚀**
