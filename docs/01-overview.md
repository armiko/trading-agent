# AI Trading Agent - Overview

## 🎯 Tujuan Proyek

AI Trading Agent adalah sistem trading otomatis berbasis terminal yang menggunakan AI (Large Language Model) untuk menganalisis pasar XAUUSD (Gold) dan menghasilkan sinyal trading. Sistem ini dirancang untuk berjalan **lokal** di VM Proxmox Windows dengan akses ke MetaTrader 5.

## 🏗️ Arsitektur Utama

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI / TUI Interface                       │
│  (trade.py, cli/start.py, cli/status.py, cli/models.py)    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Core Engine                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │  Market     │  │   AI        │  │   Risk      │          │
│  │  Data       │  │   Decision  │  │   Manager   │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ Execution   │  │ Learning    │  │ Regime      │          │
│  │ Engine      │  │ Memory      │  │ Classifier  │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    External Services                         │
│  MetaTrader 5 ←→ 9Router (AI) ←→ SQLite Database           │
└─────────────────────────────────────────────────────────────┘
```

## 📦 Komponen Utama

### 1. Core Modules (`core/`)
| File | Fungsi |
|------|--------|
| `agent.py` | Main orchestrator - menggabungkan semua komponen |
| `market.py` | Data gathering M5/M15, spread check, session filter |
| `ai.py` | AI decision engine - prompt building & response parsing |
| `ai_ensemble.py` | Multiple AI models voting system |
| `risk.py` | Risk validation - drawdown, confidence, circuit breaker |
| `execution.py` | Order execution dengan TP/SL dinamis |
| `learning.py` | Trade history & self-reflection memory |
| `indicators.py` | Technical indicators (RSI, EMA, ATR, MACD, dll) |
| `correlation.py` | DXY correlation tracking |
| `position_sizer.py` | Dynamic lot sizing (Kelly + ATR) |
| `trailing_stop.py` | Adaptive trailing stop management |
| `performance_tracker.py` | Live vs backtest performance monitoring |
| `regime.py` | Market regime classification |
| `news_filter.py` | Economic calendar filter |
| `backtest.py` | Historical backtesting engine |

### 2. CLI Modules (`cli/`)
| File | Fungsi |
|------|--------|
| `start.py` | TUI entry point (assisted mode) |
| `status.py` | MT5 connection & account status |
| `models.py` | List available AI models |
| `tui/widgets.py` | Textual widgets untuk dashboard |

### 3. Providers (`providers/`)
| File | Fungsi |
|------|--------|
| `ninerouter.py` | 9Router AI provider integration |

## 🔄 Alur Trading (7 Fase)

1. **Booting** - MT5 initialize, load config, load tracked positions
2. **Data Gathering** - Fetch M5/M15 candles, calculate indicators
3. **AI Decision** - Build prompt, call AI, parse response
4. **Risk Validation** - Check drawdown, confidence, circuit breaker
5. **Execution** - Send order dengan SL/TP dinamis
6. **Position Monitoring** - Trailing stop, breakeven, time-based exit
7. **Post-Trade** - Save to DB, self-reflection, learn from result

## 🚀 Quick Start

```bash
# Setup
python trade.py setup

# Cek status
python trade.py status

# Start TUI (assisted mode)
python trade.py start

# Run headless (auto mode)
python trade.py run
```

## 📊 Fitur Advanced

- **DXY Correlation** - Konfirmasi fundamental USD strength
- **Dynamic Position Sizing** - Kelly Criterion + Volatility-based
- **Trailing Stop** - ATR-based adaptive stop loss
- **Performance Tracker** - Real-time deviation monitoring
- **AI Ensemble** - Multiple models voting system
- **Enhanced Indicators** - Support/Resistance, Price Action, Market Structure

## 🔧 Konfigurasi

Semua konfigurasi ada di `config.yaml`:

```yaml
symbol: XAUUSD
lot: 0.01
mode: assisted  # assisted / auto
max_trades_per_day: 3
confidence_threshold: 80
max_drawdown_percent: 5
```

Lihat `docs/configuration.md` untuk detail lengkap.

## 📚 Dokumentasi Lengkap

- `docs/02-architecture.md` - Arsitektur detail
- `docs/03-modules.md` - Dokumentasi setiap modul
- `docs/04-cli_commands.md` - Panduan CLI
- `docs/05-configuration.md` - Konfigurasi lengkap
- `docs/06-development.md` - Panduan pengembang
- `docs/07-maintenance.md` - Maintenance checklist
- `docs/08-ai_context.md` - Context khusus untuk AI
