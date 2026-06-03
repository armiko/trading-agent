# CLI Commands Reference

## Overview

Semua command dijalankan melalui `trade.py`:

```bash
python trade.py [command]
```

## Commands

### 1. setup - Interactive Setup Wizard

**Fungsi:** Konfigurasi interaktif untuk first-time setup.

**Usage:**
```bash
python trade.py setup
```

*(Terminal UI akan menggunakan `rich` dengan validasi input otomatis dan tabel ringkasan).*

**Prompt yang ditanyakan:**
1. Symbol (XAUUSD, EURUSD, GBPUSD, dll)
2. Lot size (0.01, 0.02, dll)
3. Max trades per day (1-10)
4. Confidence threshold (0-100)
5. Max drawdown percent (1-20)
6. AI Provider (ninerouter)
7. Model name (auto, gpt-4, claude-3, dll)

**Output:** Generate `config.yaml` dari template.

---

### 2. config - View Configuration

**Fungsi:** Tampilkan konfigurasi saat ini dengan validasi.

**Usage:**
```bash
python trade.py config
```

**Output:**
*(Ditampilkan dalam format Tabel berwarna menggunakan library `rich`)*
```
┌──────────────────────────────────────┐
│ CURRENT CONFIGURATION                │
├───────────────┬──────────────────────┤
│ Parameter     │ Value                │
├───────────────┼──────────────────────┤
│ Symbol        │ XAUUSD               │
│ Lot Size      │ 0.01                 │
│ Max Trades/Day│ 3                    │
│ Confidence    │ 80%                  │
│ AI Provider   │ ninerouter           │
└───────────────┴──────────────────────┘

⚠️  CONFIG WARNINGS:
   ❌ provider 'ollama' is deprecated. Please update to 'ninerouter'.
```

**Validasi:**
- Required fields (symbol, lot, provider, mode)
- Symbol validation (XAUUSD, EURUSD, dll)
- Numeric validations (lot > 0, confidence 0-100, dll)
- Provider validation (ninerouter)

---

### 3. status - Check MT5 Connection

**Fungsi:** Cek koneksi MT5 dan tampilkan account info.

**Usage:**
```bash
python trade.py status
```

**Output (Success):**
```
=== MT5 CONNECTION STATUS ===

Account Login: 12345678
Currency: USD
Balance: 2000.00
Equity: 2015.50
Profit: +15.50

Open Positions: 1
  BUY XAUUSD | Lot: 0.01 | Entry: 2320.50 | PnL: +0.50

[OK] MT5 connected successfully
```

**Output (Error):**
```
=== MT5 CONNECTION STATUS ===

[ERROR] MT5 not connected

Troubleshooting:
1. Make sure MT5 is running
2. Check 'Allow automated trading' in Tools → Options → Expert Advisors
3. Restart MT5 and try again
```

---

### 4. models - List Available AI Models

**Fungsi:** Tampilkan AI models yang tersedia via 9Router.

**Usage:**
```bash
python trade.py models
```

**Output:**
```
=== AVAILABLE AI MODELS (9Router) ===

Connected Providers:
  ✓ OpenAI (gpt-4, gpt-3.5-turbo)
  ✓ Anthropic (claude-3-opus, claude-3-sonnet)
  ✓ Google (gemini-pro)
  ✓ Ollama (qwen3:8b, mimo:latest)

Recommended for Trading:
  - gpt-4 (best reasoning)
  - claude-3-opus (best analysis)
  - qwen3:8b (fast, local)

Current Model: auto (9Router will auto-route)

To change model, edit config.yaml:
  model: gpt-4
```

---

### 5. start - Start TUI (Assisted Mode)

**Fungsi:** Jalankan trading agent dengan TUI dashboard (manual approval).

**Usage:**
```bash
python trade.py start
```

**Features:**
- Real-time dashboard dengan 5 panels
- Manual approval untuk setiap signal (press 'a')
- Live position monitoring
- Event log

**Keyboard Shortcuts:**
- `a` - Approve signal
- `r` - Refresh data
- `q` - Quit

**TUI Layout:**
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
│ Reason     : Trend alignment & RSI normal              │
│ Status     : [PENDING] Press 'a' to approve            │
├────────────────────────────────────────────────────────┤
│ OPEN POSITIONS                                         │
│ BUY XAUUSD | Lot: 0.01 | Entry: 2320.10 | PnL: +0.42  │
├────────────────────────────────────────────────────────┤
│ LOG                                                    │
│ [INFO] Agent initialized successfully                  │
│ [INFO] NEW SIGNAL: BUY | Conf: 87%                    │
└────────────────────────────────────────────────────────┘
```

**Validation:**
- Config validation sebelum start
- Warning jika ada config issues
- Confirm untuk continue jika ada warnings

---

### 6. run - Run Headless (Auto Mode)

**Fungsi:** Jalankan trading agent tanpa TUI (fully automated).

**Usage:**
```bash
python trade.py run
```

**Features:**
- No UI, hanya log ke console
- Auto-execute semua signals (no manual approval)
- Suitable untuk production/VPS

**Output:**
```
[AGENT] MT5 initialized successfully
[AGENT] Account: 12345678 | Balance: 2000.00
[AGENT] Starting trading loop...
[AGENT] AI Decision: BUY (conf: 87%) - Trend alignment
[AGENT] Position sizing: lot=0.02 (from base=0.01)
[EXEC] Order sent: BUY XAUUSD @ 2320.50 | SL: 2302.25 | TP: 2358.25 | Ticket: 123456
[AGENT] Position 123456 tracked. Waiting for close to complete Fase 7...
```

**Validation:**
- Config validation sebelum run
- Exit jika ada validation errors
- No warnings allowed (must fix config first)

---

## Command Flow

### First Time Setup
```bash
# 1. Setup wizard
python trade.py setup

# 2. Check config
python trade.py config

# 3. Check MT5 connection
python trade.py status

# 4. Check available models
python trade.py models

# 5. Start trading (assisted mode)
python trade.py start
```

### Daily Usage
```bash
# Morning: Check status
python trade.py status

# Start trading
python trade.py start

# Or run headless
python trade.py run
```

### Troubleshooting
```bash
# Check config
python trade.py config

# Check MT5 connection
python trade.py status

# Check AI models
python trade.py models

# Re-run setup if needed
python trade.py setup
```

---

## Exit Codes

| Code | Meaning |
|------|----------|
| 0 | Success |
| 1 | Invalid command / Config error |
| 2 | MT5 connection failed |
| 3 | AI provider not available |

---

## Environment Variables

**Optional:**
```bash
export NINEROUTER_API_KEY="your-api-key"  # For 9Router paid tier
```

---

## Logs

**Console Output:**
- `[AGENT]` - Agent events
- `[EXEC]` - Execution events
- `[RISK]` - Risk manager events
- `[AI]` - AI decision events
- `[PERF_TRACKER]` - Performance tracking events

**Database Logs:**
- `db/sqlite.db` - Trade history & learning memory
- `db/tracked_positions.json` - Open positions
- `db/performance_state.json` - Performance metrics
