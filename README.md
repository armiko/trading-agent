# 🤖 AI Trading Agent — MVP (TUI & CLI Edition)

Dokumen ini merangkum arsitektur **Minimum Viable Product (MVP)** untuk AI Trading Agent berbasis terminal. Fokus utama fase ini adalah membangun integrasi Core Engine, manajemen risiko, dan sistem pembelajaran (Learning Memory) melalui Terminal UI (TUI) yang ringan namun interaktif.

> **Stack:** Python · MetaTrader 5 · 9Router (60+ AI providers) · SQLite · Textual/Rich TUI  
> **Server:** VM Proxmox Windows (akses via SSH dari MacBook)

---

## 🏗️ Arsitektur & Konsep MVP

```
CLI / TUI (Textual/Rich)  →  Core Engine (Market, Risk, Flow)  →  9Router & MT5  →  SQLite
                                      ↓
                    Advanced Features: DXY Correlation, Position Sizer,
                    Trailing Stop, Performance Tracker, AI Ensemble
```

Semua komponen berjalan **murni lokal** di VM Proxmox Windows untuk meminimalisir latensi.

### 🚀 Fitur Advanced (NEW)

1. **DXY Correlation Tracking** - Monitor korelasi XAUUSD dengan Dollar Index untuk konfirmasi fundamental
2. **Dynamic Position Sizing** - Kelly Criterion + Volatility-based lot sizing untuk risk management optimal
3. **Trailing Stop Manager** - ATR-based trailing stop dengan breakeven automation
4. **Live Performance Tracker** - Real-time monitoring dengan deviation alert vs backtest
5. **AI Ensemble Voting** - Multiple AI models dengan majority voting untuk mengurangi hallucination
6. **Enhanced Technical Analysis** - Support/Resistance detection, Price Action patterns, Market Structure analysis

---

## ⚙️ Spesifikasi Teknis (Configurable via Setup Wizard)

> **Jalankan `python trade.py setup` untuk konfigurasi interaktif.**

| Parameter | Nilai Default | Keterangan |
|---|---|---|
| **Pair Target** | XAUUSD | Bisa diganti via setup wizard |
| **Tipe Akun** | Cent Account | Untuk testing (jangan pakai real) |
| **Base Equity** | 2000 USC | Dari MT5, bisa di-reset via daily reset |
| **Lot Eksekusi** | 0.01 Cent lot | Fixed, no martingale |
| **Max Drawdown** | 5% per hari | Mode HIBERNATE jika tercapai |
| **Max Open Position** | 1 | Bot hanya 1 posisi aktif |
| **Max Trades Per Day** | 3 | Reset otomatis setiap midnight |

**Note:** Semua parameter di atas bisa diubah via `python trade.py setup` atau edit `config.yaml`.

---

## 📁 Struktur Direktori

```
trading-agent/
├── cli/
│   ├── start.py          # Entry point aplikasi TUI
│   ├── status.py         # Cek koneksi & balance
│   └── models.py         # Handler ganti model AI
│
├── core/
│   ├── market.py         # Tarik data M5 & Multi-Timeframe
│   ├── indicators.py     # Kalkulasi EMA, RSI, ATR via pandas_ta
│   ├── ai.py             # Pengirim prompt ke 9Router AI
│   ├── risk.py           # Validasi Drawdown & Rules
│   ├── execution.py      # Trigger mt5.order_send()
│   ├── learning.py       # Update & baca SQLite trades
│   ├── database.py       # Database initialization
│   └── agent.py          # Main orchestration
│
├── providers/            # AI Provider
│   └── ninerouter.py     # 9Router (60+ providers, fallback)
│
├── db/
│   └── sqlite.db         # WAL mode enabled
│
└── config.yaml
```

---

## 🔧 Konfigurasi Global (`config.yaml`)

```yaml
symbol: XAUUSD
lot: 0.01
model: qwen3:8b           # Bisa diganti via CLI
mode: assisted            # Opsi: assisted / auto
max_trades_per_day: 3
confidence_threshold: 80
max_drawdown_percent: 5   # Dihitung dari ekuitas awal harian (100 USC)
spread_multiplier_limit: 0.3  # max spread > 30% ATR → skip
circuit_breaker_max_errors: 3  # setelah N error berturut-turut → sleep 1 jam
circuit_breaker_sleep_hours: 1
atr_sl_multiplier: 1.5
atr_tp_multiplier: 2.5
atr_trailing_multiplier: 1.0
breakeven_after_atr: 1.0
time_exit_minutes: 20
time_exit_min_profit_atr: 0.5
magic_number: 99999
max_deviation: 10
db_path: db/sqlite.db

# ADVANCED FEATURES

## DXY Correlation (NEW)
dxy_correlation_enabled: true  # Enable DXY tracking untuk XAUUSD

## Position Sizing (NEW)
risk_per_trade_pct: 1.0        # Risk 1% per trade
kelly_fraction: 0.25          # Use 1/4 Kelly (conservative)
max_lot: 0.5                  # Maximum lot cap
min_lot: 0.01                 # Minimum lot floor

## Trailing Stop (NEW)
atr_trailing_multiplier: 1.5  # Trailing distance
breakeven_buffer_atr: 0.2     # Buffer above/below entry

## AI Ensemble (NEW)
ai_ensemble_enabled: false    # Enable multiple AI models voting
ai_ensemble_models:           # Models untuk voting
  - "gpt-4"
  - "claude-3"
ai_ensemble_min_agreement: 2  # Minimal 2 models setuju

## Performance Tracker (NEW)
# Otomatis aktif, tidak perlu konfigurasi

## Enhanced Indicators (NEW)
# Otomatis aktif, tidak perlu konfigurasi
```

---

## 🗄️ Skema Database (SQLite — WAL Mode)

### Tabel `trade_history`
| Kolom | Tipe | Keterangan |
|---|---|---|
| `ticket` | INT (PK) | ID order dari MT5 |
| `type` | VARCHAR | BUY / SELL |
| `entry_price` | FLOAT | |
| `close_price` | FLOAT | |
| `profit` | FLOAT | PnL dalam USC |
| `open_time` | DATETIME | |
| `close_time` | DATETIME | |
| `ai_confidence` | INT | Keyakinan AI saat buka posisi |
| `ai_reason` | TEXT | Alasan singkat dari JSON AI |

### Tabel `learning_memory`
| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | INT (Auto) | |
| `date` | DATETIME | |
| `market_context` | TEXT | JSON kondisi teknikal |
| `result` | VARCHAR | WIN / LOSS |
| `lesson` | TEXT | Kesimpulan AI, contoh: *"RSI 70 di sesi London sering false breakout"* |

---

## 🎯 Advanced Features Documentation

### 1. DXY Correlation Tracking

**Mengapa Penting?**
Gold (XAUUSD) memiliki korelasi negatif kuat (-0.85) dengan US Dollar Index (DXY). Trading gold tanpa mempertimbangkan DXY seperti trading buta.

**Cara Kerja:**
- Fetch data DXY dari MT5 (atau gunakan proxy EURUSD/GBPUSD jika DXY tidak tersedia)
- Hitung korelasi 20-period antara Gold dan DXY
- Deteksi divergence: Gold naik + DXY naik = anomali (AVOID_BUY)
- Konfirmasi normal: Gold naik + DXY turun = CONFIRM_BUY

**Konfigurasi:**
```yaml
dxy_correlation_enabled: true  # Enable DXY tracking
```

**Output di Log:**
```
[AGENT] DXY Divergence: BULLISH_DIVERGENCE - AVOID_BUY
[AGENT] DXY Correlation blocked BUY: BULLISH_DIVERGENCE
```

### 2. Dynamic Position Sizing

**Mengapa Penting?**
Fixed lot size (0.01) tidak optimal. Saat volatilitas tinggi, risiko meningkat. Saat win rate bagus, kita bisa size up.

**Metode:**

**A. Kelly Criterion (Edge-based)**
```
f* = (p × b - q) / b
di mana:
  p = win rate
  q = 1 - p
  b = avg_win / avg_loss
```

**B. Volatility-based (ATR)**
```
Lot = Risk Amount / (SL Points × Point Value)
SL Points = ATR × SL Multiplier
```

**C. Conservative Blend**
Sistem menggunakan **lot terkecil** antara Kelly dan Volatility untuk keamanan maksimal.

**Konfigurasi:**
```yaml
risk_per_trade_pct: 1.0      # 1% equity per trade
kelly_fraction: 0.25          # Use 1/4 Kelly (conservative)
max_lot: 0.5                  # Maximum lot cap
min_lot: 0.01                 # Minimum lot floor
```

**Output di Log:**
```
[AGENT] Position sizing: lot=0.02 (from base=0.01)
```

### 3. Trailing Stop Manager

**Mengapa Penting?**
Fixed SL/TP tidak optimal. Trailing stop melindungi profit saat trend berlanjut.

**Fitur:**

**A. Breakeven Move (Profit ≥ 1R)**
```
Jika profit ≥ 1× Risk:
  SL → Entry + (ATR × 0.2)
```

**B. Profit Locking (Profit ≥ 2R)**
```
Jika profit ≥ 2× Risk:
  SL → Current Price - (ATR × 1.5)
```

**C. Aggressive Trail (Profit ≥ 3R)**
```
Jika profit ≥ 3× Risk:
  SL → Current Price - (ATR × 0.5)
```

**Konfigurasi:**
```yaml
atr_trailing_multiplier: 1.5   # Trailing distance
breakeven_buffer_atr: 0.2      # Buffer above/below entry
```

**Output di Log:**
```
[EXEC] Breakeven activated for 12345 (offset: 5.0 points)
[AGENT] Trailing stop updated to 2325.50
```

### 4. Live Performance Tracker

**Mengapa Penting?**
Backtest bisa bagus, tapi live trading bisa berbeda. Performance tracker mendeteksi deviation dan alert jika performa menyimpang.

**Metrik yang Ditrack:**
- Win rate (live vs backtest)
- Profit factor (live vs backtest)
- Maximum drawdown (live vs backtest)
- Sample size (statistical significance)

**Alert Conditions:**
- Win rate deviation > 15% (dengan min 20 trades)
- Profit factor < 70% dari backtest
- Drawdown > 130% dari backtest max DD
- Sample size < 30 trades (warning: insufficient data)

**Konfigurasi:**
Otomatis aktif, tidak perlu konfigurasi tambahan.

**Output di Log:**
```
⚠️ Win rate deviation: live 45% vs backtest 60%
🚨 Drawdown exceeded backtest: 8% vs 5%
ℹ️ Sample size too small (15 trades). Need 30+ for statistical significance.
```

### 5. AI Ensemble Voting

**Mengapa Penting?**
Single AI model bisa hallucinate atau bias. Ensemble dengan voting mengurangi error rate.

**Cara Kerja:**
- Jalankan 2-3 AI models secara parallel
- Hitung majority vote untuk action (BUY/SELL/HOLD)
- Average confidence dari models yang setuju
- Require minimum agreement (default: 2 models)

**Konfigurasi:**
```yaml
ai_ensemble_enabled: true
ai_ensemble_models:
  - "gpt-4"
  - "claude-3"
ai_ensemble_min_agreement: 2  # Minimal 2 models setuju
```

**Output di Log:**
```
[AGENT] Ensemble Decision: BUY (67% agreement)
[AGENT] Ensemble votes: {'BUY': 2, 'HOLD': 1}
```

### 6. Enhanced Technical Analysis

**A. Support & Resistance Detection**
- Deteksi swing highs/lows menggunakan pivot points
- Clustering levels yang berdekatan (tolerance 0.1%)
- Hitung jarak ke nearest support/resistance

**B. Price Action Patterns**
- HH/HL (Higher Highs, Higher Lows) = Bullish
- LH/LL (Lower Highs, Lower Lows) = Bearish
- Breakout detection (bullish/bearish)
- Price position (NEAR_HIGH, NEAR_LOW, MIDDLE)

**C. Market Structure Analysis**
- Structure: BULLISH/BEARISH/NEUTRAL (based on EMA alignment)
- Momentum: STRONG/WEAK/NEUTRAL (based on MACD + RSI)
- Volatility: HIGH/NORMAL/LOW (based on ATR percentile)
- Volume: INCREASING/DECREASING/STABLE

**Konfigurasi:**
Otomatis aktif, tidak perlu konfigurasi tambahan.

**Output di Context AI:**
```json
{
  "support_resistance": {
    "nearest_support": 2315.50,
    "nearest_resistance": 2325.80,
    "dist_to_support_pct": 0.5,
    "dist_to_resistance_pct": 0.3
  },
  "price_action": {
    "pattern": "HH_HL",
    "trend_strength": 75.0,
    "breakout_signal": "BULLISH_BREAKOUT",
    "price_position": "NEAR_HIGH"
  },
  "market_structure": {
    "structure": "BULLISH",
    "momentum": "STRONG",
    "volatility": "NORMAL",
    "volume_trend": "INCREASING"
  }
}
```

---

## 🔄 Alur Sistem (7 Fase)

Sistem berjalan menggunakan **Asynchronous Event Loop** (`asyncio`) agar TUI tidak freeze saat menunggu respons 9Router atau MT5.

### Fase 1 — Booting & Inisialisasi
1. Jalankan `trade start`, baca `config.yaml`
2. `mt5.initialize()` → retry 3x dengan sleep, baru exit jika gagal total
3. Cek login akun & pastikan Auto Trading diizinkan di MT5
4. Render TUI ke layar

### Fase 2 — Data Gathering & Feature Engineering *(tiap 1 menit)*
- **Spread Check:** Jika `Spread > 30% ATR` → status `[STANDBY: SPREAD HIGH]`, skip AI
- **Tarik Candle** M5 tiap 1 menit, M15 tiap 15 menit (cache-aware)
- **Kalkulasi `pandas_ta`:**
  - EMA_20 & EMA_50 di M15 → Tren Makro
  - EMA_20 & EMA_50 di M5 → Tren Mikro
  - RSI_14 di M5 → Momentum
  - ATR_14 di M5 → Volatilitas

### Fase 3 — Penyusunan Prompt & AI Decision *(tiap tutup candle M5)*
1. Jika `positions_total() == 0`, ambil **3 lesson LOSS + 2 lesson WIN terakhir** dari `learning_memory`
2. Build prompt dinamis (Market Context + Memori weighted)
3. API call ke `http://localhost:20128/v1` (9Router endpoint)
4. Parse JSON dari respons; jika gagal → retry max 2x → fallback: `{"action": "HOLD", "confidence": 0, "reason": "parsing error"}`

### Fase 4 — Risk Engine (Validasi)
`core/risk.py` memblokir eksekusi jika:
- [ ] Action bukan BUY/SELL
- [ ] Confidence < 80%
- [ ] Total trade hari ini ≥ 3
- [ ] Drawdown harian sudah ≥ 5%
- [ ] AI melawan tren M15 (directional conflict)
- [ ] RSI > 68 untuk BUY / RSI < 32 untuk SELL (overbought/oversold filter)
- [ ] Circuit breaker aktif (error bertubi-tubi)

### Fase 5 — Order Execution (TP/SL Dinamis via ATR)
```
Contoh ATR = 12 poin:

BUY:
  SL = Entry - (1.5 × ATR) = Entry - 18 poin
  TP = Entry + (2.5 × ATR) = Entry + 30 poin

Parameter Wajib:
  deviation = 10   → batalkan jika slippage > 10 poin
  magic    = 99999 → bot hanya manage order sendiri
```

### Fase 6 — Position Monitoring & Exit *(tiap 1 menit)*
- **Trailing / Breakeven:** Jika profit > 1× ATR → geser SL ke Entry + 2 poin
- **Time-Based Exit:** Jika posisi sudah > 20 menit & profit < 0.5× ATR → Force Close (anti-nyangkut)

### Fase 7 — Post-Trade & Learning Engine *(FIXED: otomatis tiap posisi close)*
1. **Deteksi closed position** — `detect_closed_positions()` cek tiap cycle
2. **Ambil detail dari MT5** — `mt5.history_deals_get(position=ticket)` → entry, close, profit
3. **Simpan ke `trade_history`** — dengan AI confidence & reason
4. **Self-reflection AI** — Kirim prompt ke AI:
   > *"Kamu baru saja eksekusi {BUY} dengan alasan {reason}. Hasilnya {LOSS -15 USC}. Kondisi: RSI 72, ATR 8. Buat 1 kalimat lesson learned."*
5. **Simpan lesson** — ke `learning_memory`
6. **Increment counter** — `today_trades += 1` **hanya saat posisi close** (tidak saat open)
7. **Reset state** → kembali ke Fase 2

---

## 🧠 Template Prompt AI

```
[SYSTEM INSTRUCTION]
Kamu adalah AI Trading Quantitative murni. Tugasmu mengevaluasi data teknikal XAUUSD
dan mengeluarkan 1 keputusan trading.
OUTPUT HARUS BERUPA JSON VALID, TANPA TEKS TAMBAHAN.

[MARKET CONTEXT]
- Timeframe M15 Trend : Bullish (EMA20 > EMA50)
- Timeframe M5 Trend  : Bullish (EMA20 > EMA50)
- RSI (14)            : 62 (Netral)
- ATR                 : 15 (Volatilitas Tinggi)
- Spread              : 10 points (Aman)

[LEARNING MEMORY]
- Jangan entry BUY jika ATR di bawah 10 (market sideways).
- Hindari BUY di pucuk jika RSI > 68.

[OUTPUT FORMAT]
{"action": "BUY/SELL/HOLD", "confidence": <0-100>, "reason": "<maksimal 10 kata>"}
```

---

## 💻 Perintah CLI

| Perintah | Fungsi |
|---|---|
| `trade setup` | **Interactive wizard** untuk input symbol, capital, lot, max trades |
| `trade config` | Lihat konfigurasi saat ini |
| `trade status` | Cek koneksi MT5, tampilkan Balance & Equity |
| `trade models` | Tampilkan AI provider tersedia (9Router & 9Router) |
| `trade start` | Mulai loop trading + render TUI dasbor live |
| `trade run` | Jalankan headless (auto mode, tanpa TUI) |

---

## 🖥️ Layout Terminal UI (TUI)

```
┌────────────────────────────────────────────────────────┐
│ [LIVE] AI TRADING TERMINAL  |  Model: qwen3:8b         │
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
│ [INFO] NEW SIGNAL: BUY | Conf: 87% | Trend alignment  │
└────────────────────────────────────────────────────────┘
```

Panel dibagi 5 area dan di-refresh secara async (tidak spam ke bawah):
- **Top Left** — Account Info: Balance, Equity, PnL hari ini, Drawdown tersisa
- **Top Right** — Market Data: Tren M15/M5, RSI, ATR, Status Spread
- **Middle** — AI Terminal: Live log pemikiran AI + sinyal pending
- **Bottom Left** — Active Trades: Tabel posisi floating real-time
- **Bottom Right** — System Log: Event log dan error messages

---

## 📦 Dependencies

Untuk Python packages:
```bash
pip install MetaTrader5 pandas pandas_ta textual rich pyyaml aiohttp
```

Untuk AI Providers (pilih salah satu atau keduanya):

### A. 9Router (Recommended - 60+ AI providers & auto-fallback)
- Install Node.js jika belum ada
- Install 9Router CLI global:
```bash
npm install -g 9router
9router # Jalankan dan konfigurasi provider di browser
```

**B. 9Router (Single Provider - mendukung 60+ providers termasuk Ollama lokal)**
- Install 9Router dari [https://9router.com](https://9router.com)
- Jalankan 9Router server & pull model:
```bash
9router
# Model akan di-route otomatis oleh 9Router   # atau model lain sesuai config
```

---

## 🔧 Perbaikan Logika & Flow (dari Blueprint)

| No | Masalah | Perbaikan |
|---|---|---|
| 1 | MT5 Initialize tidak ada retry logic | Tambah retry 3x dengan sleep, baru exit jika gagal total |
| 2 | Spread check 15 poin hardcoded | Gunakan ATR untuk menentukan batas spread (>30% ATR → skip) |
| 3 | Candle M15 & M5 setiap 1 menit | Bedakan interval: M5 tiap 1 menit, M15 tiap 15 menit (cache-aware) |
| 4 | Fase 3 "tiap tutup candle M5" tidak jelas | Tambah event-based trigger via asyncio |
| 5 | ATR contoh fixed 12 poin | ATR adalah nilai hasil kalkulasi, bukan fixed |
| 6 | Directional conflict tidak jelas | Definisikan: BUY vs M15 Bearish, SELL vs M15 Bullish |
| 7 | Mode auto vs assisted tidak dijelaskan | Assisted: user konfirmasi lewat TUI. Auto: langsung eksekusi |
| 8 | Learning memory cuma ambil 3 loss | Ambil 3 loss + 2 win terbaru, weighted memory |
| 9 | Tidak ada circuit breaker | Jika AI gagal parsing >3x berturut-turut → mode SAFE, sleep 1 jam |
| 10 | Time-Based Exit (30 menit) kaku | Gunakan ATR-based: jika profit <0.5 ATR setelah 20 menit → force close |
| 11 | **Fase 7 tidak berjalan** → learning memory kosong | `detect_closed_positions()` + `process_closed_positions()` di setiap cycle |
| 12 | **Daily reset manual** → drawdown limit kacau | `check_daily_reset()` otomatis cek tanggal tiap cycle |
| 13 | **Tidak track posisi** → bingung posisi mana milik bot | `tracked_positions: Dict[int, Dict]` map ticket → decision + context |
| 14 | **Context stale saat posisi terbuka** | `get_context()` **selalu** dipanggil, tidak pernah di-skip |
| 15 | **Counter today_trades increment** saat order open | Increment **saat position close**, bukan saat open |
| 16 | **AI Decision Timing Inconsistent** (doc vs code) | Diperjelas: AI decision setiap 60s, bukan M5 candle close |
| 17 | **Position Monitoring Terlalu Lambat** (60s) | Monitoring 10s saat ada posisi, 60s saat idle |
| 18 | **Position Tracking Tidak Persisten** | `tracked_positions` disimpan ke `db/tracked_positions.json` |
| 19 | **Daily Reset Timezone Issues** | Gunakan broker server time dari MT5, bukan system time |
| 20 | **Circuit Breaker Scope Terbatas** | Track error by category (AI, MT5, DB, Network) + exponential backoff |

---

## 🚀 Quick Start

1. **Setup Environment**
   ```bash
   cd trading-agent
   pip install -r requirements.txt
   ```

2. **Setup 9Router (Recommended) atau 9Router**
   ```bash
   # Option A: 9Router (60+ providers, auto-fallback)
   npm install -g 9router
   9router
   
   # Option B: 9Router (local LLM)
   9router
   # Model akan di-route otomatis oleh 9Router
   ```

3. **Interactive Setup Wizard**
   ```bash
   python trade.py setup
   ```
   Anda akan diminta input:
   - Symbol (XAUUSD, EURUSD, dll)
   - Capital/Equity
   - Lot size
   - Max trades per day
   - Confidence threshold
   - AI Provider (9Router/9Router)

4. **Cek Koneksi MT5**
   ```bash
   python trade.py status
   ```

5. **Mulai Trading (Assisted Mode)**
   ```bash
   python trade.py start
   ```

6. **Atau Jalankan Headless (Auto Mode)**
   ```bash
   python trade.py run
   ```

---

## 📝 Catatan Keamanan

- Jangan gunakan akun real untuk testing
- Selalu cek spread sebelum trading
- Monitor drawdown harian
- Gunakan circuit breaker untuk mencegah error beruntun
- Backup database secara berkala
---

## 📚 Tutorial Lengkap

### 1. Setup Awal

#### A. Install Dependencies
```bash
cd trading-agent
pip install -r requirements.txt
```

#### B. Setup 9Router (Local LLM)
```bash
# Cek apakah 9Router sudah terinstall
9router --version

# Jika belum, install dari https://9router.com

# Pull model yang akan digunakan
# Model akan di-route otomatis oleh 9Router
ollama pull mimo:latest
```

#### C. Setup MetaTrader 5
1. Install MT5 di VM Proxmox Windows
2. Buka MT5 dan login ke akun Cent (2000 USC)
3. Buka Tools → Options → Expert Advisors
4. Centang **"Allow automated trading"**
5. Pastikan ikon Expert Advisor (robot) di toolbar berwarna hijau

---

### 2. Konfigurasi (Menggunakan Setup Wizard)

**Rekomendasi:** Gunakan interactive setup wizard untuk konfigurasi pertama kali:

```bash
python trade.py setup
```

Anda akan diminta input:
- **Symbol** (XAUUSD, EURUSD, GBPUSD, dll)
- **Capital/Equity** (dari akun MT5)
- **Lot Size** (0.01, 0.02, dll)
- **Max Trades Per Day** (3, 5, dll)
- **Confidence Threshold** (80%)
- **AI Provider** (9Router atau 9Router)

**Atau edit manual** `config.yaml`:

```yaml
# Konfigurasi Dasar
symbol: XAUUSD
lot: 0.01
mode: assisted            # assisted / auto
max_trades_per_day: 3
confidence_threshold: 80

# Risk Management
max_drawdown_percent: 5   # 5% dari equity awal
spread_multiplier_limit: 0.3  # max spread > 30% ATR → skip
circuit_breaker_max_errors: 3
circuit_breaker_sleep_hours: 1

# Dynamic Exit (ATR-based)
atr_sl_multiplier: 1.5
atr_tp_multiplier: 2.5
atr_trailing_multiplier: 1.0
breakeven_after_atr: 1.0
time_exit_minutes: 20
time_exit_min_profit_atr: 0.5

# Execution
magic_number: 99999     # Auto-generate jika masih default
max_deviation: 10
db_path: db/sqlite.db

# AI Provider
provider: ninerouter    # single provider (9Router)
model: auto              # model spesifik atau auto-route
ninerouter_url: http://localhost:20128/v1
# ollama_url: http://localhost:11434   # (deprecated, use 9Router)
```

**Penjelasan Parameter Penting:**
- `mode: assisted` → Anda harus tekan 'a' di TUI untuk approve sinyal
- `mode: auto` → Bot langsung eksekusi tanpa konfirmasi
- `max_drawdown_percent: 5` → Bot berhenti otomatis jika drawdown ≥5%
- `provider: ninerouter` → Gunakan 9Router dengan 60+ providers dan auto-fallback
- `magic_number: 99999` → Auto-generate unique number jika masih default
- `circuit_breaker_max_errors: 3` → Bot sleep 1 jam jika error bertubi-tubi

---

### 3. Menjalankan Bot

#### A. Cek Koneksi MT5
```bash
python trade.py status
```

Output yang benar:
```
=== MT5 CONNECTION STATUS ===

Account Login: 12345678
Currency: USD
Balance: 2000.00
Equity: 2000.00
Profit: 0.00

Open Positions: 0

[OK] MT5 connected successfully
```

#### B. Cek Model AI
```bash
python trade.py models
```

Output:
```
=== AVAILABLE AI MODELS (9Router) ===

Installed models:
  - qwen3:8b
  - mimo:latest
```

#### C. Jalankan TUI (Assisted Mode)
```bash
python trade.py start
```

**Interaksi TUI:**
- `a` → Approve sinyal BUY/SELL
- `r` → Refresh data manual
- `q` → Quit aplikasi

**Panel TUI:**
1. **Account Panel** (kiri atas): Balance, Equity, PnL hari ini
2. **Market Panel** (kanan atas): Trend M15/M5, RSI, ATR, Spread
3. **Signal Panel** (tengah): Sinyal AI + status (PENDING/APPROVED)
4. **Positions Panel** (bawah kiri): Posisi terbuka real-time
5. **Log Panel** (bawah kanan): Event log dan error messages

#### D. Jalankan Headless (Auto Mode)
```bash
python trade.py run
```

Bot akan:
- Setiap 60 detik: update market data
- Setiap 5 menit: cek sinyal AI
- Langsung eksekusi jika validasi lulus
- Monitor posisi setiap 60 detik

---

### 4. Monitoring & Troubleshooting

#### A. Cek Log
Lihat file `db/sqlite.db` untuk:
- Trade history: `SELECT * FROM trade_history ORDER BY open_time DESC LIMIT 10;`
- Learning memory: `SELECT * FROM learning_memory ORDER BY date DESC LIMIT 5;`

#### B. Cek Statistik Harian
```python
# Quick stats via Python
python -c "
import sqlite3
conn = sqlite3.connect('db/sqlite.db')
c = conn.cursor()
c.execute('SELECT COUNT(*), SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END), SUM(profit) FROM trade_history WHERE DATE(open_time) = date("now")')
row = c.fetchone()
print(f'Trades today: {row[0]}')
print(f'Wins: {row[1]}')
print(f'Total PnL: {row[2]:.2f} USC')
conn.close()
"
```

#### C. Troubleshooting

| Masalah | Solusi |
|---|---|
| MT5 not connected | 1. Pastikan MT5 terbuka dan login<br>2. Cek "Allow automated trading" di Tools → Options<br>3. Restart MT5 |
| 9Router not available | 1. Install: `npm install -g 9router`<br>2. Jalankan: `9router`<br>3. Buka dashboard di browser untuk connect providers |
| Spread too high | Bot otomatis skip. Tunggu spread menurun atau cek broker |
| Drawdown limit reached | Bot masuk mode HIBERNATE. Tunggu besok atau reset equity awal |
| Circuit breaker active | Bot sleep 1 jam. Tunggu atau restart manual |

---

### 5. Optimasi & Best Practices

#### A. Adjust Confidence Threshold
Jika terlalu banyak false signal:
```yaml
confidence_threshold: 85  # naikkan dari 80
```

Jika terlalu jarang signal:
```yaml
confidence_threshold: 70  # turunkan dari 80
```

#### B. Adjust ATR Multiplier
Jika SL terlalu dekat (sering stop loss):
```yaml
atr_sl_multiplier: 2.0  # naikkan dari 1.5
```

Jika TP terlalu jauh (sulit dapat profit):
```yaml
atr_tp_multiplier: 1.5  # turunkan dari 2.5
```

#### C. Reset Daily State
Jika ingin reset drawdown counter (misal setelah weekend):
1. Stop bot
2. Edit `config.yaml`, ganti `model: qwen3:8b` dengan `model: qwen3:8b_temp`
3. Start bot (bot akan reset daily state)
4. Ganti kembali ke `model: qwen3:8b`

---

### 6. Contoh Workflow Lengkap

**Hari Senin, Pagi:**
```bash
# 1. Cek koneksi
python trade.py status

# 2. Cek model
python trade.py models

# 3. Start TUI
python trade.py start
```

**Saat TUI Running:**
1. Bot update market data tiap 60 detik
2. Setiap 5 menit, cek sinyal AI
3. Jika ada sinyal BUY/SELL:
   - Panel Signal berubah jadi PENDING
   - Log menampilkan: `[INFO] NEW SIGNAL: BUY | Conf: 87%`
4. Tekan `a` untuk approve
5. Bot eksekusi order dengan SL/TP dinamis
6. Bot monitor posisi tiap 60 detik

**Hari Jumat, Sore:**
```bash
# Stop bot
q  # di TUI

# Cek hasil hari ini
python -c "import sqlite3; conn = sqlite3.connect('db/sqlite.db'); c = conn.cursor(); c.execute('SELECT COUNT(*), SUM(profit) FROM trade_history WHERE DATE(open_time) = date("now")'); print(c.fetchone()); conn.close()"
```

---

### 7. Maintenance

#### A. Backup Database
```bash
cp db/sqlite.db db/sqlite.db.backup.$(date +%Y%m%d)
```

#### B. Clear Old Data
```bash
# Hapus trade history > 30 hari
python -c "
import sqlite3
from datetime import datetime, timedelta
conn = sqlite3.connect('db/sqlite.db')
c = conn.cursor()
cutoff = (datetime.now() - timedelta(days=30)).isoformat()
c.execute('DELETE FROM trade_history WHERE open_time < ?', (cutoff,))
conn.commit()
print(f'Deleted trades older than 30 days')
conn.close()
"
```

#### C. Reset Learning Memory
```bash
# Hapus semua learning memory
python -c "
import sqlite3
conn = sqlite3.connect('db/sqlite.db')
c = conn.cursor()
c.execute('DELETE FROM learning_memory')
conn.commit()
print('Learning memory reset')
conn.close()
"
```

---

## 🌐 Setup 9Router (Recommended)

### Apa itu 9Router?

[9Router](https://9router.com) adalah **smart AI router** yang menghubungkan tool Anda ke **60+ AI providers** dengan fitur:

- ✅ **3-tier fallback** (Subscription → Cheap → Free)
- ✅ **OpenAI-compatible** API
- ✅ **Built-in token optimization** (RTK & Caveman mode)
- ✅ **Zero downtime** - auto-switch saat quota habis
- ✅ **Free tier tersedia** - Kiro, iFlow, Qwen, OpenCode


### Setup 9Router (2 Command)

#### 1. Install 9Router
```bash
npm install -g 9router
```

#### 2. Connect Providers
```bash
9router
```

Dashboard akan terbuka di browser. Pilih provider yang ingin digunakan:

**Tier 1 - Subscription** (Claude, Copilot, dll)
**Tier 2 - Cheap** (GLM $0.60, MiniMax $0.20)
**Tier 3 - FREE** (Kiro, iFlow, Qwen, OpenCode)

### Konfigurasi Trading Agent

Edit `config.yaml`:

```yaml
provider: ninerouter
model: auto
ninerouter_url: http://localhost:20128/v1
ninerouter_api_key: null
```

**Penjelasan:**
- `provider: ninerouter` → Gunakan 9Router sebagai AI provider
- `model: auto` → 9Router auto-route ke provider terbaik
- `ninerouter_url` → Default 9Router endpoint
- `ninerouter_api_key` → Kosongkan jika menggunakan free tier

### Cara Kerja 9Router dengan Trading Agent

1. **Bot memanggil AI** → Kirim prompt ke `http://localhost:20128/v1`
2. **9Router route** → Auto-select provider terbaik
3. **Fallback otomatis** → Jika provider utama habis quota, auto-switch ke tier berikutnya
4. **Response** → Hasil AI dikirim kembali ke bot

### Contoh Workflow

**Skenario 1: Free Tier (Kiro)**
```yaml
provider: ninerouter
model: kiro
```
Bot akan menggunakan Kiro AI (free) untuk semua decision.

**Skenario 2: Auto Fallback**
```yaml
provider: ninerouter
model: auto
```
- Tier 1: Claude (subscription Anda)
- Tier 2: GLM (cheap)
- Tier 3: Kiro (free)

Jika Claude quota habis → otomatis pakai GLM → jika habis → pakai Kiro.

**Skenario 3: Multi-Account**
9Router support multiple accounts per provider dengan round-robin load balancing.

### Monitoring 9Router

Buka dashboard 9Router:
```
http://localhost:20128/dashboard
```

Dashboard menampilkan:
- Real-time quota tracking
- Provider usage statistics
- Token savings (RTK & Caveman)
- Fallback events

### Troubleshooting 9Router

| Masalah | Solusi |
|---|---|
| 9Router not running | Jalankan `9router` di terminal |
| Connection refused | Pastikan 9router berjalan di `localhost:20128` |
| No providers connected | Buka dashboard dan connect providers |
| Model not found | Gunakan `model: auto` atau cek model tersedia di dashboard |

### Tips Optimization

#### A. Enable RTK & Caveman Mode
9Router built-in token optimization:
- **RTK**: −20–40% token savings untuk tool_result
- **Caveman**: −65% token savings dengan prompt lebih compact

Keduanya default ON, tidak perlu konfigurasi.

#### B. Prioritize Free Tier
Jika ingin hemat biaya:
```yaml
provider: ninerouter
model: kiro  # atau iFlow, qwen, opencode
```

#### C. Setup Fallback Priority
9Router auto-fallback, tapi Anda bisa control via provider selection:
- Subscription providers → Tier 1
- Paid API keys → Tier 2
- Free providers → Tier 3

---

## 📞 Support & Feedback

Jika menemukan bug atau punya saran:
1. Cek log di TUI panel
2. Cek `db/sqlite.db` untuk detail error
3. Review `config.yaml` untuk konfigurasi

Happy Trading! 🚀
