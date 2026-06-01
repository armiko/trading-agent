# Maintenance Checklist

## Daily Tasks

### 1. Check Bot Status
```bash
# Check if bot is running
ps aux | grep trade.py

# Check logs
tail -f logs/trading.log
```

### 2. Monitor Performance
```bash
# Check win rate
cd trading-agent
python -c "
import sqlite3
conn = sqlite3.connect('db/sqlite.db')
c = conn.cursor()
c.execute('SELECT COUNT(*), SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END), SUM(profit) FROM trade_history WHERE DATE(open_time) = date(\"now\")')
row = c.fetchone()
print(f'Trades today: {row[0]}')
print(f'Wins: {row[1]}')
print(f'Total PnL: {row[2]:.2f} USC')
conn.close()
"
```

### 3. Check Drawdown
```bash
# Check current equity
python trade.py status
```

---

## Weekly Tasks

### 1. Database Backup
```bash
# Backup database
cp db/sqlite.db db/sqlite.db.backup.$(date +%Y%m%d)

# Keep last 30 days
cd db
ls -t sqlite.db.backup.* | tail -n +31 | xargs rm
```

### 2. Review Learning Memory
```bash
# View recent lessons
cd trading-agent
python -c "
import sqlite3
conn = sqlite3.connect('db/sqlite.db')
c = conn.cursor()
c.execute('SELECT * FROM learning_memory ORDER BY date DESC LIMIT 10')
for row in c.fetchall():
    print(f'{row[0]}: {row[3]}')
conn.close()
"
```

### 3. Check Performance Tracker
```bash
# View performance metrics
cat db/performance_state.json | python -m json.tool
```

---

## Monthly Tasks

### 1. Clean Old Data
```bash
# Delete trades older than 90 days
python -c "
import sqlite3
from datetime import datetime, timedelta
conn = sqlite3.connect('db/sqlite.db')
c = conn.cursor()
cutoff = (datetime.now() - timedelta(days=90)).isoformat()
c.execute('DELETE FROM trade_history WHERE open_time < ?', (cutoff,))
conn.commit()
print('Deleted trades older than 90 days')
conn.close()
"
```

### 2. Reset Performance Tracker
```bash
# Reset if needed
python -c "
from core.performance_tracker import LivePerformanceTracker
tracker = LivePerformanceTracker()
tracker.reset()
print('Performance tracker reset')
"
```

### 3. Update Dependencies
```bash
# Update Python packages
pip install -r requirements.txt --upgrade

# Check for security vulnerabilities
pip audit
```

---

## Quarterly Tasks

### 1. Full System Audit
```bash
# Check all files
find . -name "*.py" -type f | wc -l

# Check database size
ls -lh db/

# Check disk space
df -h
```

### 2. Configuration Review
```bash
# Review config.yaml
cat config.yaml

# Compare with template
diff config.yaml config.template.yaml
```

### 3. Security Audit
```bash
# Check for exposed secrets
grep -r "api_key\|password\|secret" . --exclude-dir=.git --exclude="*.md"

# Update 9Router
npm update -g 9router
```

---

## Emergency Procedures

### Bot Not Responding
```bash
# Check if process is running
ps aux | grep trade.py

# If not running, restart
python trade.py start

# If still not working, check logs
tail -f logs/trading.log
```

### High Drawdown
```bash
# Stop bot immediately
# Check current drawdown
python trade.py status

# If drawdown > max_drawdown_percent:
# 1. Bot should be in HIBERNATE mode
# 2. Wait for tomorrow for reset
# 3. Review config if frequent drawdowns
```

### MT5 Connection Lost
```bash
# Check MT5 is running
# Check 'Allow automated trading' enabled
# Restart MT5 if needed
# Re-run bot
python trade.py start
```

### AI Provider Down
```bash
# Check 9Router status
curl http://localhost:20128/v1/models

# If 9Router not running, start it
9router

# Wait for 9Router to initialize
# Re-run bot
python trade.py start
```

---

## Monitoring Dashboard

### Create Custom Dashboard
```bash
# Create monitoring script
cat > monitor.sh << 'EOF'
#!/bin/bash

echo "=== Trading Agent Monitor ==="
echo "Time: $(date)"
echo ""

# Check bot status
if pgrep -f "trade.py" > /dev/null; then
    echo "[OK] Bot is running"
else
    echo "[ERROR] Bot is NOT running"
fi

# Check MT5
python trade.py status 2>&1 | head -20

# Check recent trades
echo ""
echo "=== Recent Trades ==="
python -c "
import sqlite3
conn = sqlite3.connect('db/sqlite.db')
c = conn.cursor()
c.execute('SELECT type, profit, DATE(open_time) FROM trade_history ORDER BY open_time DESC LIMIT 5')
for row in c.fetchall():
    print(f'{row[0]}: {row[1]:.2f} USC on {row[2]}')
conn.close()
"

# Check performance
echo ""
echo "=== Performance ==="
python -c "
import sqlite3
conn = sqlite3.connect('db/sqlite.db')
c = conn.cursor()
c.execute('SELECT COUNT(*), SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END), SUM(profit) FROM trade_history')
row = c.fetchone()
print(f'Total trades: {row[0]}')
print(f'Wins: {row[1]}')
print(f'Total PnL: {row[2]:.2f} USC')
conn.close()
"
EOF

chmod +x monitor.sh
```

### Run Dashboard
```bash
./monitor.sh
```

---

## Log Files

### Console Logs
- **TUI Mode:** Displayed in terminal
- **Headless Mode:** Displayed in terminal

### Database Logs
```bash
# Trade history
cd trading-agent
sqlite3 db/sqlite.db "SELECT * FROM trade_history ORDER BY open_time DESC LIMIT 10;"

# Learning memory
sqlite3 db/sqlite.db "SELECT * FROM learning_memory ORDER BY date DESC LIMIT 5;"
```

### State Files
```bash
# Tracked positions
cat db/tracked_positions.json

# Performance state
cat db/performance_state.json
```

---

## Troubleshooting

### Bot Keeps Restarting
```bash
# Check for errors
tail -f logs/trading.log

# Common causes:
# 1. MT5 connection issues
# 2. AI provider timeout
# 3. Database lock

# Solution:
# 1. Check MT5 is running
# 2. Check 9Router is running
# 3. Check database permissions
```

### High Error Rate
```bash
# Check error categories
python -c "
import sqlite3
conn = sqlite3.connect('db/sqlite.db')
c = conn.cursor()
c.execute('SELECT error_type, COUNT(*) FROM error_log GROUP BY error_type')
for row in c.fetchall():
    print(f'{row[0]}: {row[1]}')
conn.close()
"

# Common errors:
# - AI parsing errors (increase confidence threshold)
# - MT5 connection errors (check MT5 stability)
# - Network errors (check internet connection)
```

### Low Win Rate
```bash
# Check recent performance
python -c "
import sqlite3
conn = sqlite3.connect('db/sqlite.db')
c = conn.cursor()
c.execute('SELECT COUNT(*), SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) FROM trade_history WHERE DATE(open_time) > date(\"now\", \"-7 days\")')
row = c.fetchone()
print(f'Win rate (7 days): {row[1]/row[0]*100:.1f}%')
conn.close()
"

# Solutions:
# 1. Increase confidence threshold
# 2. Review learning memory for patterns
# 3. Check market conditions
```

---

## Maintenance Schedule

| Task | Frequency | Command |
|------|-----------|---------|
| Check bot status | Daily | `ps aux | grep trade.py` |
| Monitor performance | Daily | `python trade.py status` |
| Database backup | Weekly | `cp db/sqlite.db db/backup/` |
| Review lessons | Weekly | `sqlite3 db/sqlite.db` |
| Clean old data | Monthly | `DELETE FROM trade_history...` |
| Full audit | Quarterly | Manual review |

---

## Backup Strategy

### Daily Backup
```bash
# Create daily backup
cp db/sqlite.db db/backups/sqlite.db.$(date +%Y%m%d)

# Keep last 7 days
cd db/backups
ls -t sqlite.db.* | tail -n +8 | xargs rm
```

### Weekly Backup
```bash
# Weekly backup to external storage
cp db/sqlite.db /external/backup/sqlite.db.weekly.$(date +%Y%V)
```

### Monthly Archive
```bash
# Monthly archive
tar -czf db/archive/sqlite.db.$(date +%Y%m).tar.gz db/sqlite.db
```

---

## Rollback Procedure

### If New Version Breaks
```bash
# Stop bot
# Restore from backup
cp db/backups/sqlite.db.YYYYMMDD db/sqlite.db

# Revert config if needed
cp config.yaml.backup config.yaml

# Restart bot
python trade.py start
```

---

## Health Check Script

```bash
cat > health_check.sh << 'EOF'
#!/bin/bash

ERRORS=0

# Check bot running
if ! pgrep -f "trade.py" > /dev/null; then
    echo "[ERROR] Bot is not running"
    ERRORS=$((ERRORS + 1))
fi

# Check MT5
if ! python trade.py status 2>&1 | grep -q "connected"; then
    echo "[ERROR] MT5 not connected"
    ERRORS=$((ERRORS + 1))
fi

# Check 9Router
if ! curl -s http://localhost:20128/v1/models > /dev/null; then
    echo "[ERROR] 9Router not available"
    ERRORS=$((ERRORS + 1))
fi

# Check database
if [ ! -f db/sqlite.db ]; then
    echo "[ERROR] Database not found"
    ERRORS=$((ERRORS + 1))
fi

# Check disk space
if [ $(df -h . | tail -1 | awk '{print $5}' | tr -d '%') -gt 90 ]; then
    echo "[ERROR] Disk space low"
    ERRORS=$((ERRORS + 1))
fi

if [ $ERRORS -eq 0 ]; then
    echo "[OK] All systems healthy"
else
    echo "[WARNING] $ERRORS issues found"
fi
EOF

chmod +x health_check.sh
```

---

## Contact & Support

If issues persist:
1. Check logs
2. Review documentation
3. Contact developer
4. Check GitHub issues
