#!/usr/bin/env python3
"""
Wayne Hourly Trading Scan
Runs every hour via cron
Scans stocks + crypto for RSI signals
Paper trading only
"""
import os
import sys
import json
import subprocess
from datetime import datetime

TRADING_DIR = "/home/ubuntu/.openclaw/workspace/trading"
WAYNE_AGENT = f"{TRADING_DIR}/wayne_agent.py"
GUARDIAN = f"{TRADING_DIR}/wayne_guardian.sh"
OUTPUT_FILE = f"{TRADING_DIR}/wayne_scan_latest.json"
LOG_FILE = f"{TRADING_DIR}/scanner.log"

def log(msg: str):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{timestamp}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except:
        pass

def check_guardian() -> bool:
    """Check if guardian allows trading"""
    try:
        result = subprocess.run([GUARDIAN, 'check'], capture_output=True, text=True, timeout=5)
        return 'OK' in result.stdout
    except Exception as e:
        log(f"Guardian check failed: {e}")
        return True  # Allow if guardian is unavailable

def run_scan():
    """Execute Wayne scan"""
    try:
        result = subprocess.run(
            ['python3', WAYNE_AGENT],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=TRADING_DIR
        )
        return result.stdout + result.stderr
    except Exception as e:
        return f"ERROR: {e}"

def save_results(signals: list):
    """Save scan results"""
    try:
        with open(OUTPUT_FILE, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'signals': signals,
                'count': len(signals)
            }, f, indent=2)
    except Exception as e:
        log(f"Failed to save results: {e}")

def main():
    log("=" * 50)
    log("Wayne Hourly Scan Started")
    
    # Guardian check
    if not check_guardian():
        log("⚠️ Guardian blocked scan")
        return
    
    # Run scan
    output = run_scan()
    log("Scan output:")
    for line in output.split('\n')[-20:]:  # Last 20 lines
        if line.strip():
            log(f"  {line}")
    
    # Parse signals from output
    signals = []
    for line in output.split('\n'):
        if 'LONG' in line or 'SHORT' in line or 'WATCH' in line:
            signals.append(line.strip())
    
    save_results(signals)
    
    if signals:
        log(f"✅ Found {len(signals)} signals")
    else:
        log("✅ Scan complete — no signals")
    
    log("=" * 50)

if __name__ == "__main__":
    main()
