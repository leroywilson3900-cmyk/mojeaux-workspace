#!/usr/bin/env python3
"""
Wayne Status Report
Quick health check on Wayne's trading systems
"""
import os
import sys
from datetime import datetime

def check_file(path, name):
    if os.path.exists(path):
        size = os.path.getsize(path)
        return f"✅ {name}: Found ({size} bytes)"
    return f"❌ {name}: NOT FOUND at {path}"

def main():
    print("=" * 50)
    print(f"Wayne Status Report — {datetime.now().strftime('%I:%M %p UTC')}")
    print("=" * 50)
    print()
    
    base = "/home/ubuntu/.openclaw/workspace/trading"
    
    checks = [
        (f"{base}/wayne_trading_cron.py", "Trading Cron"),
        (f"{base}/wayne_agent.py", "Wayne Agent"),
        (f"{base}/wayne_tape_feed.py", "Tape Feed"),
        (f"{base}/wayne_guardian.sh", "Guardian Script"),
        (f"{base}/wayne_health_check.sh", "Health Check"),
        ("/home/ubuntu/.openclaw/cron/jobs.json", "Cron Jobs"),
    ]
    
    all_ok = True
    for path, name in checks:
        result = check_file(path, name)
        print(result)
        if "NOT FOUND" in result:
            all_ok = False
    
    print()
    if all_ok:
        print("✅ All Wayne systems operational")
        return 0
    else:
        print("⚠️ Some Wayne systems missing — need rebuild")
        return 1

if __name__ == "__main__":
    sys.exit(main())
