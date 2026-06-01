# Arsitektur Sistem

## 🏗️ Layer Architecture

Sistem ini menggunakan **3-layer architecture**:

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│  - CLI Commands (trade.py)                                  │
│  - TUI Interface (cli/start.py)                             │
│  - Status & Models Display                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    BUSINESS LOGIC LAYER                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Core Agent (agent.py)                               │   │
│  │  - Orchestrates all components                       │   │
│  │  - Manages trading loop                              │   │
│  │  - Handles state & position tracking                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Market   │  │   AI     │  │   Risk   │  │Execution │   │
│  │ Data     │  │ Decision │  │ Manager  │  │  Engine  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Learning  │  │ Regime   │  │  News    │  │Indicators│   │
│  │ Memory   │  │Classifier│  │  Filter  │  │          │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │   DXY    │  │ Position │  │ Trailing │  │Performance│  │
│  │Correlation│ │  Sizer   │  │   Stop   │  │  Tracker │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    DATA ACCESS LAYER                         │
│  - MetaTrader 5 API (mt5.*)                                 │
│  - SQLite Database (trade_history, learning_memory)         │
│  - 9Router HTTP API (AI providers)                          │
│  - File System (config.yaml, tracked_positions.json)        │
└─────────────────────────────────────────────────────────────┘
```

## 🔄 Data Flow

### 1. Trading Loop Flow

```
┌─────────────┐
│   START     │
└──────┬──────┘
       │
       ↓
┌─────────────────────────────────────────┐
│  1. Initialize                          │
│  - MT5 connect                          │
│  - Load config                          │
│  - Load tracked positions               │
│  - Initialize all modules               │
└──────┬──────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────┐
│  2. Data Gathering (every 60s)          │
│  - Fetch M5 candles                     │
│  - Fetch M15 candles (cached)           │
│  - Calculate indicators                 │
│  - Get DXY data (if enabled)            │
│  - Check spread                         │
└──────┬──────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────┐
│  3. Build Context                       │
│  - Market data (RSI, ATR, EMA)          │
│  - Support/Resistance levels            │
│  - Price Action patterns                │
│  - Market Structure                     │
│  - DXY correlation signal               │
│  - Regime classification                │
└──────┬──────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────┐
│  4. Check Existing Positions            │
│  - Detect closed positions              │
│  - Process closed (Fase 7)              │
│  - Monitor open positions               │
│  - Update trailing stops                │
└──────┬──────────────────────────────────┘
       │
       ↓ (if no positions)
┌─────────────────────────────────────────┐
│  5. AI Decision                         │
│  - Build prompt with context            │
│  - Call AI (or Ensemble)                │
│  - Parse JSON response                  │
│  - Validate format                      │
└──────┬──────────────────────────────────┘
       │
       ↓ (if not HOLD)
┌─────────────────────────────────────────┐
│  6. Risk Validation                     │
│  - Check confidence threshold           │
│  - Check daily trade limit              │
│  - Check drawdown limit                 │
│  - Check directional conflict           │
│  - Check RSI overbought/oversold        │
│  - Check DXY divergence                 │
│  - Check circuit breaker                │
└──────┬──────────────────────────────────┘
       │
       ↓ (if allowed)
┌─────────────────────────────────────────┐
│  7. Position Sizing                     │
│  - Calculate Kelly lot                  │
│  - Calculate Volatility lot             │
│  - Take minimum (conservative)          │
└──────┬──────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────┐
│  8. Execution                           │
│  - Calculate SL/TP (ATR-based)          │
│  - Send order to MT5                    │
│  - Track position                       │
│  - Save to file                         │
└──────┬──────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────┐
│  9. Sleep & Repeat                      │
│  - 10s if positions open                │
│  - 60s if idle                          │
└──────┬──────────────────────────────────┘
       │
       └──────────────────────────────────┐
                                          │
                                          ↓
                                    (back to step 2)
```

### 2. Fase 7 (Post-Trade Learning) Flow

```
┌─────────────────────────────────────────┐
│  Position Closed (detected)             │
└──────┬──────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────┐
│  Fetch Trade Details from MT5           │
│  - Entry price, close price             │
│  - Profit/Loss                          │
│  - Open/Close time                      │
└──────┬──────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────┐
│  Save to trade_history                  │
│  - ticket, type, prices, profit         │
│  - AI confidence & reason               │
└──────┬──────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────┐
│  AI Self-Reflection                     │
│  - Build reflection prompt              │
│  - Include trade result & context       │
│  - Get lesson learned                   │
└──────┬──────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────┐
│  Save to learning_memory                │
│  - Market context (JSON)                │
│  - Result (WIN/LOSS)                    │
│  - Lesson text                          │
└──────┬──────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────┐
│  Update Performance Tracker             │
│  - Record trade profit                  │
│  - Update win rate                      │
│  - Check deviation vs backtest          │
└──────┬──────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────┐
│  Increment today_trades counter         │
└─────────────────────────────────────────┘
```

## 🔌 Component Dependencies

### Core Dependencies

```
agent.py
  ├── market.py
  │   └── indicators.py
  ├── ai.py
  │   ├── learning.py
  │   └── providers/ninerouter.py
  ├── ai_ensemble.py
  │   └── ai.py
  ├── risk.py
  ├── execution.py
  ├── learning.py
  │   └── database.py
  ├── regime.py
  ├── news_filter.py
  ├── correlation.py
  ├── position_sizer.py
  ├── trailing_stop.py
  └── performance_tracker.py
```

### CLI Dependencies

```
trade.py
  ├── setup_wizard.py
  ├── cli/status.py
  ├── cli/models.py
  │   └── providers/ninerouter.py
  └── cli/start.py
      ├── agent.py
      └── cli/tui/widgets.py
```

## 🗄️ Database Schema

### trade_history
```sql
CREATE TABLE trade_history (
    ticket INTEGER PRIMARY KEY,
    type VARCHAR(10),           -- BUY/SELL
    entry_price FLOAT,
    close_price FLOAT,
    profit FLOAT,               -- in USC
    open_time DATETIME,
    close_time DATETIME,
    ai_confidence INTEGER,      -- 0-100
    ai_reason TEXT
);
```

### learning_memory
```sql
CREATE TABLE learning_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATETIME,
    market_context TEXT,        -- JSON string
    result VARCHAR(10),         -- WIN/LOSS
    lesson TEXT
);
```

## 🔐 State Management

### Runtime State (agent.py)
```python
self.running: bool                          # Loop control
self.mode: str                              # assisted/auto
self.current_equity: float                  # Current account equity
self.daily_pnl: float                       # Today's P&L
self.current_date: date                     # For daily reset
self.tracked_positions: Dict[int, Dict]     # ticket -> position data
self.last_decision: Optional[Dict]          # Last AI decision
self.last_context: Optional[Dict]           # Last market context
self.signal_timestamp: Optional[datetime]   # For signal expiry
```

### Persistent State
```
db/sqlite.db                    # Trade history & learning memory
db/tracked_positions.json       # Open positions tracking
db/performance_state.json       # Performance tracker state
config.yaml                     # Configuration
```

## 🔄 Async Event Loop

Sistem menggunakan `asyncio` untuk non-blocking operations:

```python
async def run_cycle():
    # All I/O operations are async
    await self.data_gathering()          # Async MT5 calls
    context = await self.market.get_context()  # Async
    decision = await self.ai.decide(context)   # Async HTTP
    ticket = await self.executor.send_order()  # Async MT5
```

Keuntungan:
- TUI tidak freeze saat waiting AI response
- Multiple operations bisa parallel
- Better resource utilization

## 🛡️ Error Handling Strategy

### Circuit Breaker Pattern
```
Error Count → Action
1-2 errors  → Log & continue
3 errors    → Hibernate 1 minute
4 errors    → Hibernate 5 minutes
5 errors    → Hibernate 15 minutes
6+ errors   → Hibernate 1 hour
```

### Error Categories
- `ai` - AI provider errors
- `mt5` - MetaTrader 5 errors
- `db` - Database errors
- `network` - Network errors
- `other` - Uncategorized errors

### Recovery Strategy
1. **Exponential Backoff** - Increase sleep time after each error
2. **State Persistence** - Save state before critical operations
3. **Graceful Degradation** - Continue with reduced functionality
4. **Auto-Recovery** - Reset error counter after success
