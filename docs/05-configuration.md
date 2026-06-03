# Configuration Reference

## config.yaml Structure

Semua konfigurasi sistem ada di `config.yaml`. File ini di-generate dari `config.template.yaml` saat pertama kali run `python trade.py setup`.

## Basic Settings

### symbol
**Type:** `string`  
**Default:** `XAUUSD`  
**Valid Values:** `XAUUSD`, `EURUSD`, `GBPUSD`, `USDJPY`, `BTCUSD`

**Deskripsi:** Trading pair yang akan di-trade.

```yaml
symbol: XAUUSD
```

---

### lot
**Type:** `float`  
**Default:** `0.01`  
**Range:** `0.01` - `1.0`

**Deskripsi:** Fixed lot size untuk setiap trade. Akan di-override jika `dynamic_position_sizing` enabled.

```yaml
lot: 0.01
```

---

### mode
**Type:** `string`  
**Default:** `assisted`  
**Valid Values:** `assisted`, `auto`

**Deskripsi:**
- `assisted` - Manual approval via TUI (press 'a' untuk approve signal)
- `auto` - Fully automated (langsung eksekusi tanpa konfirmasi)

```yaml
mode: assisted
```

---

## Risk Management

### max_trades_per_day
**Type:** `integer`  
**Default:** `3`  
**Range:** `1` - `10`

**Deskripsi:** Maksimum trade yang boleh dieksekusi per hari. Reset otomatis setiap midnight.

```yaml
max_trades_per_day: 3
```

---

### confidence_threshold
**Type:** `integer`  
**Default:** `80`  
**Range:** `0` - `100`

**Deskripsi:** Minimum AI confidence untuk eksekusi trade. Jika confidence < threshold, trade di-block.

```yaml
confidence_threshold: 80
```

**Rekomendasi:**
- `70-75` - Lebih banyak signal, tapi lebih banyak false positive
- `80-85` - Balanced (recommended)
- `90-95` - Sangat konservatif, signal jarang

---

### max_drawdown_percent
**Type:** `float`  
**Default:** `5.0`  
**Range:** `1.0` - `20.0`

**Deskripsi:** Maximum daily drawdown dalam persen dari equity awal. Jika tercapai, bot masuk mode HIBERNATE.

```yaml
max_drawdown_percent: 5.0
```

**Contoh:**
- Starting equity: 2000 USC
- Max drawdown 5% = 100 USC
- Jika equity turun ke 1900 USC → HIBERNATE

---

### spread_multiplier_limit
**Type:** `float`  
**Default:** `0.3`  
**Range:** `0.1` - `1.0`

**Deskripsi:** Maximum spread sebagai persentase dari ATR. Jika spread > limit, skip trading.

```yaml
spread_multiplier_limit: 0.3
```

**Contoh:**
- ATR = 15 points
- Limit = 0.3 (30%)
- Max spread = 15 × 0.3 = 4.5 points
- Jika spread > 4.5 → Skip

---

## Dynamic Position Sizing

Position sizing is always active. Lot size is dynamically calculated using Kelly Criterion + ATR-based volatility method, taking the more conservative result.

---

### risk_per_trade_pct
**Type:** `float`  
**Default:** `1.0`  
**Range:** `0.5` - `5.0`

**Deskripsi:** Risk per trade dalam persen dari equity.

```yaml
risk_per_trade_pct: 1.0
```

---

### pip_value_per_lot
**Type:** `float`  
**Default:** `10.0`

**Deskripsi:** Nilai USD per pip per 1.0 standard lot. Untuk XAUUSD = $10/pip/lot.

```yaml
pip_value_per_lot: 10.0
```

### max_lot
**Type:** `float`  
**Default:** `0.5`

**Deskripsi:** Maximum lot size cap.

```yaml
max_lot: 0.5
```

---

### min_lot
**Type:** `float`  
**Default:** `0.01`

**Deskripsi:** Minimum lot size floor.

```yaml
min_lot: 0.01
```

---

## ATR-Based Exits

### atr_sl_multiplier
**Type:** `float`  
**Default:** `1.5`  
**Range:** `1.0` - `3.0`

**Deskripsi:** Stop Loss distance sebagai multiplier dari ATR.

```yaml
atr_sl_multiplier: 1.5
```

**Contoh:**
- ATR = 15 points
- Multiplier = 1.5
- SL distance = 15 × 1.5 = 22.5 points

---

### atr_tp_multiplier
**Type:** `float`  
**Default:** `2.5`  
**Range:** `1.5` - `5.0`

**Deskripsi:** Take Profit distance sebagai multiplier dari ATR.

```yaml
atr_tp_multiplier: 2.5
```

---

### atr_trailing_multiplier
**Type:** `float`  
**Default:** `1.0`  
**Range:** `0.5` - `2.0`

**Deskripsi:** Trailing stop distance sebagai multiplier dari ATR.

```yaml
atr_trailing_multiplier: 1.0
```

---

### breakeven_after_atr
**Type:** `float`  
**Default:** `1.0`  
**Range:** `0.5` - `2.0`

**Deskripsi:** Move SL ke breakeven setelah profit > ATR × multiplier.

```yaml
breakeven_after_atr: 1.0
```

---

### atr_minimum_points
**Type:** `integer`  
**Default:** `8`

**Deskripsi:** Minimum ATR dalam points untuk allow trading. Jika ATR < minimum, skip (market terlalu quiet).

```yaml
atr_minimum_points: 8
```

---

## Time-Based Exits

### time_exit_minutes
**Type:** `integer`  
**Default:** `20`  
**Range:** `10` - `60`

**Deskripsi:** Force close position setelah N menit jika profit < threshold.

```yaml
time_exit_minutes: 20
```

---

### time_exit_min_profit_atr
**Type:** `float`  
**Default:** `0.5`  
**Range:** `0.3` - `1.0`

**Deskripsi:** Minimum profit (sebagai ATR multiplier) untuk avoid time-based exit.

```yaml
time_exit_min_profit_atr: 0.5
```

**Contoh:**
- ATR = 15 points
- Multiplier = 0.5
- Min profit = 15 × 0.5 = 7.5 points
- Jika profit < 7.5 points setelah 20 menit → Force close

---

## Circuit Breaker

### circuit_breaker_max_errors
**Type:** `integer`  
**Default:** `3`  
**Range:** `2` - `10`

**Deskripsi:** Maximum consecutive errors sebelum activate circuit breaker.

```yaml
circuit_breaker_max_errors: 3
```

---

### circuit_breaker_sleep_hours
**Type:** `float`  
**Default:** `1.0`  
**Range:** `0.5` - `24.0`

**Deskripsi:** Hibernate duration dalam jam setelah circuit breaker activated.

```yaml
circuit_breaker_sleep_hours: 1.0
```

---

## Session Filter (NEW)

### session_filter_enabled
**Type:** `boolean`  
**Default:** `true`

**Deskripsi:** Enable session-based trading filter.

```yaml
session_filter_enabled: true
```

---

## SaaS Integration (NEW)

### saas_api_key
**Type:** `string`  
**Default:** `""`

**Deskripsi:** API Key dari Xerynq Web Dashboard untuk mengirim Global Telemetry (Trades & Lessons).

```yaml
saas_api_key: "ta_live_..."
```

---

### saas_backend_url
**Type:** `string`  
**Default:** `"http://127.0.0.1:8000/api/v1"`

**Deskripsi:** Endpoint tujuan untuk Web Dashboard backend.

```yaml
saas_backend_url: "http://127.0.0.1:8000/api/v1"
```

---

### allowed_sessions
**Type:** `list[string]`  
**Default:** `["London", "New York"]`

**Deskripsi:** List sesi yang diizinkan untuk trading.

```yaml
allowed_sessions:
  - London      # 09:00-17:00 UTC
  - "New York"  # 17:00-21:00 UTC
```

---

### avoid_sessions
**Type:** `list[string]`  
**Default:** `["Asia"]`

**Deskripsi:** List sesi yang dihindari untuk trading.

```yaml
avoid_sessions:
  - Asia        # 00:00-09:00 UTC (low volume)
```

---

## News Filter (NEW)

### news_filter_enabled
**Type:** `boolean`  
**Default:** `true`

**Deskripsi:** Enable economic calendar filter.

```yaml
news_filter_enabled: true
```

---

### news_buffer_minutes
**Type:** `integer`  
**Default:** `30`  
**Range:** `15` - `60`

**Deskripsi:** Avoid trading N minutes sebelum/sesudah high-impact news.

```yaml
news_buffer_minutes: 30
```

---

### news_currencies
**Type:** `list[string]`  
**Default:** `["USD", "EUR"]`

**Deskripsi:** List currencies untuk monitor news.

```yaml
news_currencies:
  - USD
  - EUR
```

---

## Market Regime (NEW)

### regime_adaptive
**Type:** `boolean`  
**Default:** `true`

**Deskripsi:** Adjust parameters berdasarkan market regime.

```yaml
regime_adaptive: true
```

---

### regime_adx_trending
**Type:** `float`  
**Default:** `25.0`  
**Range:** `20.0` - `30.0`

**Deskripsi:** ADX threshold untuk trending market.

```yaml
regime_adx_trending: 25.0
```

---

### regime_adx_ranging
**Type:** `float`  
**Default:** `20.0`  
**Range:** `15.0` - `25.0`

**Deskripsi:** ADX threshold untuk ranging market.

```yaml
regime_adx_ranging: 20.0
```

---

## Learning Memory

### learning_loss_count
**Type:** `integer`  
**Default:** `3`  
**Range:** `1` - `10`

**Deskripsi:** Number of recent losses untuk include dalam AI memory.

```yaml
learning_loss_count: 3
```

---

### learning_win_count
**Type:** `integer`  
**Default:** `2`  
**Range:** `1` - `10`

**Deskripsi:** Number of recent wins untuk include dalam AI memory.

```yaml
learning_win_count: 2
```

---

## MT5 Execution

### magic_number
**Type:** `integer`  
**Default:** `99999`

**Deskripsi:** Unique identifier untuk bot. Auto-generated jika masih default.

```yaml
magic_number: 99999
```

---

### max_deviation
**Type:** `integer`  
**Default:** `10`  
**Range:** `5` - `50`

**Deskripsi:** Maximum slippage dalam points. Order dibatalkan jika slippage > deviation.

```yaml
max_deviation: 10
```

---

## Database

### db_path
**Type:** `string`  
**Default:** `db/sqlite.db`

**Deskripsi:** Path ke SQLite database.

```yaml
db_path: db/sqlite.db
```

---

## AI Provider (9Router)

### provider (DEPRECATED)
**Type:** `string`  
**Status:** ⚠️ Deprecated — field ini tidak lagi digunakan.

**Deskripsi:** Field ini tidak berpengaruh pada routing AI. AI routing menggunakan `ninerouter_url` secara langsung. Field ini bisa dihapus dari config.

### model
**Type:** `string`  
**Default:** `auto`  
**Examples:** `auto`, `gpt-4`, `claude-3-opus`, `qwen3:8b`

**Deskripsi:** Model name atau `auto` untuk auto-routing.

```yaml
model: auto
```

---

### ninerouter_url
**Type:** `string`  
**Default:** `http://localhost:20128/v1`

**Deskripsi:** 9Router API endpoint.

```yaml
ninerouter_url: http://localhost:20128/v1
```

---

### ninerouter_api_key
**Type:** `string` or `null`  
**Default:** `null`

**Deskripsi:** Optional API key untuk 9Router paid tier.

```yaml
ninerouter_api_key: null
```

---

## DXY Correlation (NEW)

### dxy_correlation_enabled
**Type:** `boolean`  
**Default:** `false`

**Deskripsi:** Enable DXY correlation tracking untuk XAUUSD.

```yaml
dxy_correlation_enabled: true
```

---

## AI Ensemble (NEW)

### ai_ensemble_enabled
**Type:** `boolean`  
**Default:** `false`

**Deskripsi:** Enable multiple AI models voting.

```yaml
ai_ensemble_enabled: false
```

---

### ai_ensemble_models
**Type:** `list[string]`  
**Default:** `[]`

**Deskripsi:** List models untuk voting.

```yaml
ai_ensemble_models:
  - gpt-4
  - claude-3-opus
```

---

### ai_ensemble_min_agreement
**Type:** `integer`  
**Default:** `2`  
**Range:** `2` - `3`

**Deskripsi:** Minimum models yang harus setuju untuk eksekusi.

```yaml
ai_ensemble_min_agreement: 2
```
