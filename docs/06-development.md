# Development Guide

## Setup Development Environment

### Prerequisites
```bash
# Python 3.10+
python3 --version

# MetaTrader 5
# Download from: https://www.metatrader5.com/

# 9Router (AI Provider)
npm install -g 9router
```

### Clone & Install
```bash
git clone https://github.com/armiko/trading-agent.git
cd trading-agent
pip install -r requirements.txt
```

### Initialize Database
```bash
python -c "from core.database import init_database; init_database()"
```

---

## Project Structure

```
trading-agent/
├── trade.py              # CLI entry point
├── setup_wizard.py       # Interactive setup
├── config.yaml           # User configuration
├── config.template.yaml  # Configuration template
├── requirements.txt      # Python dependencies
│
├── core/                 # Core business logic
│   ├── agent.py         # Main orchestrator
│   ├── market.py        # Data gathering
│   ├── ai.py            # AI decision engine
│   ├── risk.py          # Risk management
│   ├── execution.py     # Order execution
│   ├── learning.py      # Learning memory
│   ├── indicators.py    # Technical indicators
│   ├── database.py      # Database init
│   ├── regime.py        # Market regime
│   ├── news_filter.py   # News filter
│   ├── backtest.py      # Backtesting
│   ├── correlation.py   # DXY correlation (NEW)
│   ├── position_sizer.py # Position sizing (NEW)
│   ├── trailing_stop.py  # Trailing stop (NEW)
│   ├── performance_tracker.py # Performance tracking (NEW)
│   └── ai_ensemble.py   # AI ensemble (NEW)
│
├── cli/                  # CLI interface
│   ├── start.py         # TUI entry point
│   ├── status.py        # Status command
│   ├── models.py        # Models command
│   └── tui/
│       └── widgets.py   # TUI widgets
│
├── providers/            # AI providers
│   └── ninerouter.py    # 9Router integration
│
├── db/                   # Database & state
│   ├── sqlite.db        # SQLite database
│   ├── tracked_positions.json
│   └── performance_state.json
│
└── docs/                 # Documentation
    ├── 01-overview.md
    ├── 02-architecture.md
    ├── 03-modules.md
    ├── 04-cli_commands.md
    ├── 05-configuration.md
    ├── 06-development.md (this file)
    ├── 07-maintenance.md
    └── 08-ai_context.md
```

---

## Adding New Features

### 1. Create New Module

**Example:** Adding a new indicator

```python
# core/my_indicator.py
"""
My Custom Indicator
"""
import pandas as pd

class MyIndicator:
    def __init__(self, config: dict):
        self.config = config
        self.enabled = config.get("my_indicator_enabled", False)
    
    def calculate(self, df: pd.DataFrame) -> dict:
        """Calculate indicator and return signal"""
        if not self.enabled:
            return {"signal": "NEUTRAL"}
        
        # Your calculation logic here
        value = df["close"].mean()
        
        return {
            "value": value,
            "signal": "BUY" if value > 2300 else "SELL"
        }
```

### 2. Integrate to Agent

```python
# core/agent.py

# Import
from core.my_indicator import MyIndicator

# Initialize in __init__
self.my_indicator = MyIndicator(self.config)

# Use in run_cycle
if self.my_indicator.enabled:
    signal = self.my_indicator.calculate(self.market._cache_m5)
    context["my_indicator"] = signal
```

### 3. Add Configuration

```yaml
# config.template.yaml

# My Indicator (NEW)
my_indicator_enabled: true
my_indicator_threshold: 2300
```

### 4. Update Documentation

```markdown
# docs/03-modules.md

### 16. my_indicator.py - My Custom Indicator

**Fungsi Utama:** Calculate custom indicator.

**Method Penting:**
- `calculate()` - Calculate indicator value
```

---

## Code Style Guidelines

### Python Style
- Follow PEP 8
- Use type hints
- Docstrings untuk semua functions
- Max line length: 100 characters

### Example
```python
from typing import Dict, Any, Optional

def calculate_signal(
    data: pd.DataFrame,
    threshold: float = 50.0
) -> Dict[str, Any]:
    """
    Calculate trading signal from data.
    
    Args:
        data: OHLCV dataframe
        threshold: Signal threshold
    
    Returns:
        Dictionary with signal and confidence
    """
    value = data["close"].mean()
    
    return {
        "signal": "BUY" if value > threshold else "SELL",
        "confidence": 85
    }
```

### Naming Conventions
- **Files:** `snake_case.py`
- **Classes:** `PascalCase`
- **Functions:** `snake_case()`
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_leading_underscore`

---

## Testing

### Manual Testing
```bash
# Test MT5 connection
python trade.py status

# Test AI provider
python trade.py models

# Test config validation
python trade.py config

# Test TUI (dry run)
python trade.py start
```

### Backtesting
```python
from core.backtest import Backtester

backtester = Backtester(config)
results = await backtester.run_backtest(
    start_date="2024-01-01",
    end_date="2024-12-31"
)

print(f"Win Rate: {results['win_rate']}%")
print(f"Profit Factor: {results['profit_factor']}")
```

---

## Debugging

### Enable Debug Logging
```yaml
# config.yaml
log_level: DEBUG
log_ai_reasoning: true
log_regime_changes: true
```

### Check Database
```bash
sqlite3 db/sqlite.db

# View recent trades
SELECT * FROM trade_history ORDER BY open_time DESC LIMIT 10;

# View learning memory
SELECT * FROM learning_memory ORDER BY date DESC LIMIT 5;

# Exit
.quit
```

### Check State Files
```bash
# Tracked positions
cat db/tracked_positions.json | python -m json.tool

# Performance state
cat db/performance_state.json | python -m json.tool
```

---

## Common Development Tasks

### Add New Risk Rule

```python
# core/risk.py - validate() method

# Add new check
if context.get("my_indicator") == "DANGEROUS":
    return {
        "allowed": False,
        "reason": "My indicator shows dangerous condition"
    }
```

### Add New AI Prompt Section

```python
# core/ai.py - build_prompt() method

my_data = context.get("my_indicator", {})

prompt += f"""
[MY INDICATOR]
- Value: {my_data.get('value', 'N/A')}
- Signal: {my_data.get('signal', 'NEUTRAL')}
"""
```

### Add New CLI Command

```python
# trade.py - main() function

elif command == "mycommand":
    from cli.mycommand import run_mycommand
    run_mycommand()
```

```python
# cli/mycommand.py

def run_mycommand():
    print("Running my command...")
    # Your logic here
```

---

## Git Workflow

### Branch Strategy
```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes
git add .
git commit -m "Add my feature"

# Push to remote
git push origin feature/my-feature

# Create PR on GitHub
```

### Commit Message Format
```
<type>: <subject>

<body>

Types:
- feat: New feature
- fix: Bug fix
- docs: Documentation
- refactor: Code refactoring
- test: Testing
- chore: Maintenance

Example:
feat: Add DXY correlation tracking

- Implement CurrencyCorrelation class
- Integrate with agent.py
- Add configuration options
```

---

## Performance Optimization

### Async Operations
```python
# Good: Parallel async calls
tasks = [
    self.market.update_m5(),
    self.market.update_m15(),
    self.dxy_correlation.fetch_dxy_data()
]
results = await asyncio.gather(*tasks)

# Bad: Sequential calls
await self.market.update_m5()
await self.market.update_m15()
await self.dxy_correlation.fetch_dxy_data()
```

### Caching
```python
# Cache expensive calculations
if self._cache_valid():
    return self._cache

result = expensive_calculation()
self._cache = result
self._cache_time = datetime.now()
return result
```

---

## Troubleshooting Development Issues

### MT5 Connection Issues
```python
# Check MT5 terminal info
import MetaTrader5 as mt5
mt5.initialize()
print(mt5.terminal_info())
print(mt5.version())
```

### AI Provider Issues
```bash
# Check 9Router status
curl http://localhost:20128/v1/models

# Check 9Router logs
9router --verbose
```

### Database Issues
```bash
# Reset database
rm db/sqlite.db
python -c "from core.database import init_database; init_database()"
```

---

## Contributing Guidelines

1. **Fork** repository
2. **Create** feature branch
3. **Write** clean, documented code
4. **Test** thoroughly
5. **Update** documentation
6. **Submit** pull request

### PR Checklist
- [ ] Code follows style guidelines
- [ ] All functions have docstrings
- [ ] Configuration updated (if needed)
- [ ] Documentation updated
- [ ] Tested manually
- [ ] No breaking changes (or documented)

---

## Resources

- **MetaTrader 5 API:** https://www.mql5.com/en/docs/python_metatrader5
- **9Router Docs:** https://9router.com/docs
- **pandas_ta:** https://github.com/twopirllc/pandas-ta
- **Textual (TUI):** https://textual.textualize.io/
