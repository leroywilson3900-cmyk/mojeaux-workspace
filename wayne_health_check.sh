#!/bin/bash
# wayne_health_check.sh - Wayne system health check
# Runs before trading to ensure everything is operational

HEALTH_LOG="/home/ubuntu/.openclaw/workspace/trading/health.log"
TRADING_DIR="/home/ubuntu/.openclaw/workspace/trading"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$HEALTH_LOG"
}

check_file() {
    if [ -f "$1" ]; then
        echo "✅ $(basename $1)"
        return 0
    else
        echo "❌ $(basename $1) MISSING"
        return 1
    fi
}

check_python() {
    if python3 -c "import $1" 2>/dev/null; then
        echo "✅ $1 module"
        return 0
    else
        echo "⚠️ $1 not installed"
        return 1
    fi
}

echo "========================================"
echo "Wayne Health Check"
echo "========================================"

ALL_OK=true

# Core files
echo ""
echo "Core Files:"
check_file "$TRADING_DIR/wayne_agent.py" || ALL_OK=false
check_file "$TRADING_DIR/wayne_trading_cron.py" || ALL_OK=false
check_file "$TRADING_DIR/wayne_tape_feed.py" || ALL_OK=false
check_file "$TRADING_DIR/wayne_guardian.sh" || ALL_OK=false

# Python modules
echo ""
echo "Python Modules:"
python3 -c "import json, urllib.request, time" 2>/dev/null && echo "✅ Core modules" || { echo "❌ Core modules missing"; ALL_OK=false; }

# Guardian status
echo ""
echo "Guardian Status:"
"$TRADING_DIR/wayne_guardian.sh" status 2>/dev/null | grep -v "^Wayne"

# Network test
echo ""
echo "Network:"
if curl -s --max-time 5 "https://api.coingecko.com" > /dev/null 2>&1; then
    echo "✅ CoinGecko API reachable"
else
    echo "⚠️ CoinGecko API not reachable"
fi

if curl -s --max-time 5 "https://query1.finance.yahoo.com" > /dev/null 2>&1; then
    echo "✅ Yahoo Finance reachable"
else
    echo "⚠️ Yahoo Finance not reachable"
fi

# Cron check
echo ""
echo "Cron Jobs:"
if crontab -l 2>/dev/null | grep -q "wayne"; then
    echo "✅ Wayne cron installed"
    crontab -l 2>/dev/null | grep wayne
else
    echo "⚠️ No Wayne cron jobs found"
fi

echo ""
echo "========================================"
if [ "$ALL_OK" = true ]; then
    echo "✅ All systems GO"
    log "HEALTH CHECK PASSED"
    exit 0
else
    echo "⚠️ Some issues detected"
    log "HEALTH CHECK FAILED - review above"
    exit 1
fi
