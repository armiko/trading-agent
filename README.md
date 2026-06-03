# 🤖 Xerynq — AI Trading Agent

AI-powered trading agent for MetaTrader 5 with advanced risk management, self-learning memory, and real-time terminal dashboard.

> **Stack:** Python · MetaTrader 5 · 9Router (60+ AI providers) · SQLite · Textual/Rich TUI
> **Runtime:** VM Proxmox Windows (akses via SSH dari MacBook)

---

## 🚀 Quick Start

```bash
# 1. Clone & install
git clone https://github.com/armiko/trading-agent.git
cd trading-agent
pip install -r requirements.txt

# 2. Setup 9Router (AI provider)
npm install -g 9router
9router  # Configure providers in browser dashboard

# 3. Configure
# Setup interaktif
python trade.py setup

# Cek koneksi
python trade.py status

# Cek riwayat performa & alasan AI
python trade.py report --limit 5

# Jalankan dalam mode assisted (membutuhkan konfirmasi)
python trade.py start

# Jalankan dalam auto mode
python trade.py run
```

---

## 🏗️ Architecture

```
CLI / TUI (Textual/Rich)  →  Core Engine  →  9Router & MT5  →  SQLite
                                  ↓
                    DXY Correlation, Position Sizer,
                    Trailing Stop, Performance Tracker, AI Ensemble
```

### 7-Phase Trading Loop

1. **Booting** — MT5 initialize, load config & tracked positions
2. **Data Gathering** — Fetch M5/M15 candles, calculate indicators, check spread
3. **AI Decision** — Build prompt with context + learning memory, call AI
4. **Risk Engine**: Memvalidasi eksekusi dengan Drawdown harian, Kelly Criterion (dinamis), ADX Regime Filter, dan korelasi DXY.
5. **Execution Engine**: Manajemen order ke MT5 dengan *tight breakeven* dan *trailing stop*.
6. **Position Monitoring** — Trailing stop, breakeven, time-based exit
7. **Post-Trade Learning** — Save to DB, AI self-reflection, lesson learned

---

## ⚡ Key Features

| Feature | Description |
|---------|-------------|
| **AI Decision Making** | 9Router dengan 60+ AI providers & auto-fallback |
| **Dynamic Position Sizing** | Kelly Criterion + ATR-based volatility sizing |
| **DXY Correlation** | Gold vs Dollar Index divergence detection |
| **Trailing Stop** | ATR-based adaptive stop loss with breakeven automation |
| **Risk Management** | Daily drawdown protection, circuit breaker, RSI filter |
| **Learning System** | Self-reflection AI & memory of past trades |
| **Global Telemetry** | Sync trades & lessons to SaaS backend to build Collective Intelligence |
| **Performance Tracker** | Live vs backtest deviation monitoring |
| **AI Ensemble** | Multiple models voting to reduce hallucination |
| **Market Regime** | ADX-based trending/ranging classification |
| **News Filter** | Economic calendar filter with buffer time |
| **Web Dashboard** | Real-time monitoring of metrics, equity curve, and live logs |
| **Terminal UI** | Real-time CLI dashboard with approval workflow |

---

## 📁 Project Structure

```
trading-agent/
├── trade.py                  # Main CLI entry point
├── setup_wizard.py           # Interactive configuration wizard
├── config.template.yaml      # Configuration template
├── config.yaml               # User configuration (gitignored)
├── requirements.txt
│
├── cli/
│   ├── start.py              # TUI entry point (assisted mode)
│   ├── status.py             # MT5 connection & account status
│   ├── models.py             # List available AI models
│   └── tui/
│       └── widgets.py        # Textual TUI widgets
│
├── core/
│   ├── agent.py              # Main orchestrator (7-phase loop)
│   ├── market.py             # Data gathering, spread check, session
│   ├── indicators.py         # RSI, EMA, ATR, MACD, S/R, price action
│   ├── ai.py                 # AI prompt building & response parsing
│   ├── ai_ensemble.py        # Multi-model voting system
│   ├── risk.py               # Drawdown, confidence, circuit breaker
│   ├── execution.py          # Order execution with ATR-based SL/TP
│   ├── learning.py           # Trade history & self-reflection memory
│   ├── database.py           # SQLite initialization
│   ├── correlation.py        # DXY correlation tracking
│   ├── position_sizer.py     # Kelly + Volatility lot sizing
│   ├── trailing_stop.py      # Adaptive trailing stop management
│   ├── performance_tracker.py # Live vs backtest monitoring
│   ├── regime.py             # Market regime classification
│   ├── news_filter.py        # Economic calendar filter
│   └── backtest.py           # Historical backtesting engine
│
├── providers/
│   └── ninerouter.py         # 9Router AI provider integration
│
├── db/                       # SQLite database (gitignored)
│   ├── sqlite.db
│   ├── tracked_positions.json
│   └── performance_state.json
│
└── docs/                     # Documentation
    ├── 01-overview.md
    ├── 02-architecture.md
    ├── 03-modules.md
    ├── 04-cli_commands.md
    ├── 05-configuration.md
    ├── 06-development.md
    ├── 07-maintenance.md
    └── 08-ai_context.md
```

---

## ⚙️ Configuration

Jalankan `python trade.py setup` atau edit `config.yaml`:

```yaml
# Basic
symbol: XAUUSD
lot: 0.01                       # Base lot (overridden by dynamic sizing)
mode: assisted                  # assisted / auto

# AI Provider (9Router)
model: auto                     # Model name or 'auto' for smart routing
ninerouter_url: http://localhost:20128/v1
ninerouter_api_key: null

# Risk Management
max_trades_per_day: 3
confidence_threshold: 80        # Minimum AI confidence (0-100)
max_drawdown_percent: 5         # Daily drawdown limit → HIBERNATE
spread_multiplier_limit: 0.3    # Max spread > 30% ATR → skip
circuit_breaker_max_errors: 3   # Consecutive errors → exponential backoff

# ATR-Based Exits
atr_sl_multiplier: 1.5          # SL = ATR × 1.5
atr_tp_multiplier: 2.5          # TP = ATR × 2.5
atr_trailing_multiplier: 1.0    # Trailing stop distance
breakeven_after_atr: 1.0        # Move SL to breakeven after 1× ATR profit
time_exit_minutes: 20           # Force close if low profit after 20min

# Dynamic Position Sizing
risk_per_trade_pct: 1.0         # Risk 1% equity per trade
kelly_fraction: 0.25            # Use 1/4 Kelly (conservative)
pip_value_per_lot: 10.0         # USD per pip per standard lot (XAUUSD = $10)
max_lot: 0.5
min_lot: 0.01

# Optional Features
dxy_correlation_enabled: false  # DXY divergence detection
ai_ensemble_enabled: false      # Multi-model voting
regime_adaptive: false          # ADX-based regime classification
news_filter_enabled: false      # Economic calendar filter
session_filter_enabled: false   # Session-based trading filter

# SaaS Integration
saas_api_key: ""                # Get from your Web Dashboard
saas_backend_url: "http://127.0.0.1:8000/api/v1" # Telemetry endpoint
```

Lihat `docs/05-configuration.md` untuk referensi lengkap semua parameter.

---

## 💻 CLI Commands

| Command | Description |
|---------|-------------|
| `python trade.py setup` | Interactive configuration wizard |
| `python trade.py config` | View current settings + validation |
| `python trade.py status` | Check MT5 connection & account |
| `python trade.py models` | List available AI models |
| `python trade.py start` | Start TUI dashboard (assisted mode) |
| `python trade.py run` | Run headless (auto mode) |

---

## 🖥️ Terminal UI

```
┌────────────────────────────────────────────────────────┐
│ [LIVE] AI TRADING TERMINAL  |  Model: auto             │
├────────────────────────────────────────────────────────┤
│ ACCOUNT (CENT)            │ MARKET ANALYSIS            │
│ Balance : 2000.00 USC     │ Trend M15 : Bullish        │
│ Equity  : 2015.00 USC     │ Trend M5  : Bullish        │
│ PnL Day : +15.00 USC      │ Session   : London         │
├───────────────────────────┴────────────────────────────┤
│ CURRENT SIGNAL                                         │
│ Action     : BUY XAUUSD                                │
│ Confidence : 87%                                       │
│ Lot        : 0.02 (dynamic)                            │
│ Status     : [PENDING] Press 'a' to approve            │
├────────────────────────────────────────────────────────┤
│ OPEN POSITIONS                                         │
│ BUY XAUUSD | Lot: 0.02 | Entry: 2320.10 | PnL: +0.42  │
├────────────────────────────────────────────────────────┤
│ LOG                                                    │
│ [INFO] Agent initialized successfully                  │
│ [INFO] NEW SIGNAL: BUY | Conf: 87% | Lot: 0.02        │
└────────────────────────────────────────────────────────┘
```

**Keyboard Shortcuts:** `a` approve signal · `r` refresh · `q` quit

---

## 🧠 Position Sizing

Sistem menggunakan **conservative blend** dari dua metode:

### Kelly Criterion (Edge-based)
```
f* = (p × b − q) / b
lot = (f* × kelly_fraction × equity) / (SL_pips × pip_value_per_lot)
```

### Volatility-based (ATR)
```
risk_amount = equity × risk_per_trade_pct / 100
lot = risk_amount / (ATR × SL_multiplier × pip_value_per_lot)
```

**Final lot = min(kelly_lot, volatility_lot)** — selalu ambil yang lebih konservatif.

---

## 🛡️ Risk Management

| Layer | Mechanism |
|-------|-----------|
| **Confidence Gate** | Block trade jika AI confidence < threshold |
| **Daily Trade Limit** | Max N trades per day (reset midnight) |
| **Drawdown Protection** | Hibernate 60 menit jika drawdown ≥ limit |
| **Directional Filter** | Block BUY vs M15 Bearish, SELL vs M15 Bullish |
| **RSI Filter** | Block BUY jika RSI > 68, SELL jika RSI < 32 |
| **DXY Divergence** | Block trade jika Gold/DXY diverge (opsional) |
| **Circuit Breaker** | Exponential backoff: 1min → 5min → 15min → 60min |
| **Spread Check** | Skip jika spread > 30% ATR |
| **ATR Minimum** | Skip jika market terlalu quiet (ATR < threshold) |

---

## 🗄️ Database Schema

### trade_history
| Column | Type | Description |
|--------|------|-------------|
| ticket | INT (PK) | MT5 order ID |
| type | VARCHAR | BUY / SELL |
| entry_price | FLOAT | Entry price |
| close_price | FLOAT | Close price |
| profit | FLOAT | P&L in USD |
| open_time | DATETIME | Open timestamp |
| close_time | DATETIME | Close timestamp |
| ai_confidence | INT | AI confidence (0-100) |
| ai_reason | TEXT | AI reasoning |

### learning_memory
| Column | Type | Description |
|--------|------|-------------|
| id | INT (Auto) | Primary key |
| date | DATETIME | Timestamp |
| market_context | TEXT | JSON market conditions |
| result | VARCHAR | WIN / LOSS |
| lesson | TEXT | AI self-reflection lesson |

---

## 📦 Requirements

- Python 3.8+
- MetaTrader 5 (Windows VM)
- Node.js (for 9Router)
- 9Router (`npm install -g 9router`)
- Cent account for testing (**jangan gunakan akun real**)

```bash
pip install MetaTrader5 pandas pandas_ta textual rich pyyaml aiohttp
```

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| MT5 not connected | Pastikan MT5 running, "Allow automated trading" di Tools → Options |
| 9Router not available | Jalankan `9router`, buka dashboard di browser untuk connect providers |
| Spread too high | Bot otomatis skip, tunggu spread menurun |
| Drawdown limit reached | Bot hibernate 60 menit, reset otomatis besok |
| Circuit breaker active | Exponential backoff, tunggu atau restart manual |
| Market closed | Bot otomatis skip cycle saat weekend |

---

## 📚 Documentation

Dokumentasi lengkap tersedia di folder `docs/`:

- `docs/01-overview.md` — Arsitektur & komponen utama
- `docs/02-architecture.md` — Data flow & dependencies detail
- `docs/03-modules.md` — Dokumentasi setiap modul
- `docs/04-cli_commands.md` — Panduan CLI lengkap
- `docs/05-configuration.md` — Referensi semua parameter
- `docs/06-development.md` — Panduan pengembang
- `docs/07-maintenance.md` — Maintenance checklist
- `docs/08-ai_context.md` — Context untuk AI prompt

---

## 📝 Changelog

### v2.5.0 (Global Telemetry & Web Dashboard Integration)
* **Added** Web Dashboard Integration: Sync trades and AI reasoning to a centralized SaaS backend using `saas_api_key`.
* **Added** Global Telemetry: Async background thread safely pushes `telemetry/trade` and `telemetry/lesson` payloads without blocking trading execution.
* **Enhanced** `setup_wizard.py` now prompts for SaaS Authentication (API Key & Backend URL) seamlessly.

### v2.4.0 (Architecture Fixes & Generalization)
* Bebas menggunakan instrumen apapun (Tidak terkunci hanya XAUUSD).
* Kalkulasi lot dinamis menggunakan *pip value* langsung dari MT5.
* **Kelly Fraction** kini bisa diatur lewat `trade.py setup`.
* Filter *Overbought/Oversold* RSI akan dinonaktifkan secara pintar jika kekuatan tren (ADX > 25) sangat kuat.
* *Tight Breakeven*: Pengganti time-based exit. Jika posisi lebih dari 20 menit namun profit lambat, SL akan digeser ke breakeven.
* Command baru `python trade.py report` untuk melihat metrik Win Rate dan *Reasoning* AI secara rapi dengan parameter opsional `--limit N`.

### v2.3.0 — MT5 Integration & CLI UI Enhancement
- **Added** `MT5Provider` to directly connect and fetch OHLCV data from MetaTrader 5 locally.
- **Enhanced** `setup_wizard.py` and `trade.py` UI using the `rich` library for beautiful terminal tables, panels, and automatic type validations.

### v2.2.1 — Interactive Mode Feature Parity
- **Fixed** Assisted Mode (TUI): AI Ensemble voting is now correctly triggered in interactive mode.
- **Fixed** Assisted Mode (TUI): Support/Resistance Sanity Checks are now applied before prompting the user for approval.
- **Fixed** Assisted Mode (TUI): Dynamic Position Sizing (Kelly/Volatility) is now correctly injected into the user's manual approval flow instead of defaulting to static lot sizes.

### v2.2.0 — Final Logic & Mathematical Fixes
- **Fixed** News Filter Timezone: Converted all local `datetime.now()` to `datetime.utcnow()` to prevent missing GMT-based RSS news events in non-UTC timezones.
- **Fixed** DXY Correlation Math: Changed correlation timeframe alignment from M5 vs H1 (producing `NaN` due to index mismatch) to H1 vs H1 for robust divergence detection.
- **Fixed** Confluence S/R Sanity Check: Corrected dictionary key mismatch that previously disabled Support/Resistance AI override protections.
- **Fixed** Position Sizer: Migrated to explicit `point` value calculation to prevent massive over-leveraging.
- **Fixed** Time-based Auto Exit: Synchronized exit timer duration strictly with MT5 `tick.time` to prevent premature forced closes caused by PC vs Broker timezone differences.
- **Fixed** Market Session Detection: Migrated Asia/London/NY detection to strict UTC hours so the bot behaves correctly regardless of VPS local time.
- **Fixed** Partial Close Detection: Properly maps continuation tickets so AI doesn't lose track of remaining open positions.
- **Changed** AI context prompt enriched with R:R distance, H1 Trend, and BB Width expansion logic.

### v2.1.0 — System Stability Update
- **Added** Drawdown limit triggers 60-minute hibernation.
- **Fixed** Market closed early returns.

---

## 📞 Support

Jika menemukan bug atau punya saran:
1. Check log di TUI panel
2. Review `db/sqlite.db` untuk detail error
3. Open issue di [GitHub](https://github.com/armiko/trading-agent/issues)

Happy Trading! 🚀
