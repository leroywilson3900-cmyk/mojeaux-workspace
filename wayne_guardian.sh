#!/bin/bash
# wayne_guardian.sh - Monitors Wayne and prevents disasters
# Guardrails for Wayne's auto-trading system

LOG_FILE="/home/ubuntu/.openclaw/workspace/trading/guardian.log"
MAX_DAILY_LOSS=50          # $50 max daily loss (paper)
MAX_TRADES_PER_HOUR=3      # Max trades per hour
LAST_TRADE_FILE="/home/ubuntu/.openclaw/workspace/trading/.last_trades"
MODE_FILE="/home/ubuntu/.openclaw/workspace/trading/.trading_mode"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

is_paper_mode() {
    # Always returns true = paper mode only
    [ ! -f "$MODE_FILE" ] || [ "$(cat $MODE_FILE)" = "PAPER" ]
}

check_daily_loss() {
    if [ ! -f "/home/ubuntu/.openclaw/workspace/trading/paper_pnl.json" ]; then
        return 0  # No history = ok
    fi
    
    # Check daily P&L
    python3 -c "
import json
from datetime import datetime
try:
    with open('/home/ubuntu/.openclaw/workspace/trading/paper_pnl.json') as f:
        data = json.load(f)
    today = datetime.now().strftime('%Y-%m-%d')
    if data.get('date') == today:
        loss = data.get('daily_pnl', 0)
        if loss < -50:
            print('BLOCK')
        else:
            print('OK')
    else:
        print('OK')
except:
    print('OK')
" 2>/dev/null
}

can_trade() {
    # Check if trading is allowed
    if ! is_paper_mode; then
        log "⚠️ TRADING BLOCKED: Not in paper mode"
        return 1
    fi
    
    if [ "$(check_daily_loss)" = "BLOCK" ]; then
        log "⚠️ TRADING BLOCKED: Daily loss limit reached"
        return 1
    fi
    
    # Check trade frequency
    if [ -f "$LAST_TRADE_FILE" ]; then
        trades=$(cat "$LAST_TRADE_FILE" | python3 -c "
import sys, json
from datetime import datetime, timedelta
try:
    trades = json.load(sys.stdin)
    hour_ago = datetime.now() - timedelta(hours=1)
    recent = [t for t in trades if datetime.fromisoformat(t['time']) > hour_ago]
    print(len(recent))
except:
    print(0)
" 2>/dev/null)
        if [ "$trades" -ge 3 ]; then
            log "⚠️ TRADING BLOCKED: Too many trades in last hour ($trades/3)"
            return 1
        fi
    fi
    
    return 0
}

log_trade() {
    # Log trade for rate limiting
    mkdir -p /home/ubuntu/.openclaw/workspace/trading
    if [ -f "$LAST_TRADE_FILE" ]; then
        python3 -c "
import json, sys
from datetime import datetime
try:
    with open('$LAST_TRADE_FILE') as f:
        trades = json.load(f)
except:
    trades = []
trades.append({'time': datetime.now().isoformat(), 'symbol': '$1', 'signal': '$2'})
with open('$LAST_TRADE_FILE', 'w') as f:
    json.dump(trades[-20:], f)  # Keep last 20
" 2>/dev/null
}

set_paper_mode() {
    mkdir -p /home/ubuntu/.openclaw/workspace/trading
    echo "PAPER" > "$MODE_FILE"
    log "🟢 MODE SET: PAPER TRADING"
}

set_live_mode() {
    log "🔴 DANGER: Attempted LIVE mode switch — BLOCKED"
    echo "PAPER" > "$MODE_FILE"
}

# Auto-set paper mode on startup
set_paper_mode

# Main guard
case "$1" in
    check)
        if can_trade; then
            echo "OK"
        else
            echo "BLOCKED"
        fi
        ;;
    trade)
        if can_trade; then
            log_trade "$2" "$3"
            echo "ALLOWED"
        else
            echo "BLOCKED"
        fi
        ;;
    status)
        echo "Wayne Guardian Status:"
        echo "  Mode: $(cat $MODE_FILE 2>/dev/null || echo 'PAPER')"
        echo "  Daily Loss: $(python3 -c "import json; d=json.load(open('/home/ubuntu/.openclaw/workspace/trading/paper_pnl.json')) if __import__('os').path.exists('/home/ubuntu/.openclaw/workspace/trading/paper_pnl.json') else {'daily_pnl':0}; print(f\"\$(d.get('daily_pnl', 0))\" )" 2>/dev/null || echo '0')"
        ;;
    *)
        echo "Wayne Guardian - Usage:"
        echo "  wayne_guardian.sh check    # Check if trading allowed"
        echo "  wayne_guardian.sh trade   # Log a trade"
        echo "  wayne_guardian.sh status  # Show guardian status"
        ;;
esac
