#!/usr/bin/env python3
"""
Wayne Trading Agent - Core Scanner
Scans stocks + crypto for RSI signals and generates trade alerts
Paper trading only - NO real money
"""
import os
import json
import time
from datetime import datetime
from typing import Optional

# API Keys
ALPACA_KEY = os.getenv('ALPACA_KEY', '')
ALPACA_SECRET = os.getenv('ALPACA_SECRET', '')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

# Pairs & Settings
STOCKS = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMD', 'META', 'GOOGL', 'AMZN', 'SPY']
CRYPTO = ['BTC-USD', 'ETH-USD', 'SOL-USD']

PAIR_STOP_OVERRIDES = {
    'BTC-USD': 0.10,   # 10% stop for BTC
    'ETH-USD': 0.10,   # 10% stop for ETH
    'SOL-USD': 0.10,   # 10% stop for SOL
}

RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
RSI_PULLBACK_OVERSOLD = 40  # Pullback buy signal

def send_telegram(msg: str):
    """Send alert to Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[TELEGRAM] {msg}")
        return
    try:
        import urllib.request
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = json.dumps({'chat_id': TELEGRAM_CHAT_ID, 'text': msg, 'parse_mode': 'HTML'}).encode()
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")

def get_rsi_price(symbol: str) -> Optional[tuple]:
    """Get RSI and current price for symbol"""
    try:
        import urllib.request
        if '-' in symbol:  # Crypto
            # Use CoinGecko for RSI approximation
            coin_map = {'BTC-USD': 'bitcoin', 'ETH-USD': 'ethereum', 'SOL-USD': 'solana'}
            coin_id = coin_map.get(symbol, 'bitcoin')
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true"
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read())
            price = data[coin_id]['usd']
            change_24h = data[coin_id].get('usd_24h_change', 0)
            # RSI approximation based on 24h change
            rsi = 50 + (change_24h / 2) if abs(change_24h) < 50 else (30 if change_24h < -10 else 70)
            rsi = max(10, min(90, rsi))
            return rsi, price
        else:
            # Use Yahoo Finance for stocks
            import urllib.parse
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1month"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read())
            result = data['chart']['result'][0]
            closes = [c['close'] for c in result['indicators']['quote'][0]['close'] if c is not None]
            if len(closes) < 15:
                return None, None
            # Calculate RSI
            deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
            gains = [d if d > 0 else 0 for d in deltas[-RSI_PERIOD:]]
            losses = [-d if d < 0 else 0 for d in deltas[-RSI_PERIOD:]]
            avg_gain = sum(gains) / RSI_PERIOD if gains else 0.001
            avg_loss = sum(losses) / RSI_PERIOD if losses else 0.001
            rs = avg_gain / avg_loss if avg_loss else 100
            rsi = 100 - (100 / (1 + rs))
            price = closes[-1]
            return rsi, price
    except Exception as e:
        print(f"[ERROR] {symbol}: {e}")
        return None, None

def get_stop_pct(symbol: str) -> float:
    """Get stop loss percentage for symbol"""
    return PAIR_STOP_OVERRIDES.get(symbol, 0.05)  # 5% default

def format_signal(signal: str, symbol: str, rsi: float, price: float, stop: float) -> str:
    """Format trade signal message"""
    emoji = {'LONG': '🟢', 'SHORT': '🔴', 'WATCH': '👀'}.get(signal, '⚪')
    direction = {'LONG': 'LONG', 'SHORT': 'SHORT', 'WATCH': 'WATCH'}.get(signal, signal)
    return (
        f"{emoji} <b>WAYNE SIGNAL</b>\n"
        f"<b>Symbol:</b> {symbol}\n"
        f"<b>Signal:</b> {direction}\n"
        f"<b>RSI:</b> {rsi:.1f}\n"
        f"<b>Price:</b> ${price:.2f}\n"
        f"<b>Stop:</b> ${price * (1 - stop):.2f} ({stop*100:.0f}%)\n"
        f"<b>Time:</b> {datetime.now().strftime('%I:%M %p UTC')}"
    )

def scan_symbol(symbol: str, primary_strategy: str = 'RSI_PULLBACK') -> Optional[dict]:
    """Scan single symbol and return signal if triggered"""
    rsi, price = get_rsi_price(symbol)
    if rsi is None:
        return None
    
    stop_pct = get_stop_pct(symbol)
    signal = None
    
    if primary_strategy == 'RSI_PULLBACK':
        if rsi < RSI_OVERSOLD:
            signal = 'LONG'
        elif rsi < RSI_PULLBACK_OVERSOLD:
            signal = 'WATCH'
        elif rsi > RSI_OVERBOUGHT:
            signal = 'SHORT'
    elif primary_strategy == 'RSI_TREND':
        if rsi < 45 and rsi > 30:
            signal = 'LONG'
        elif rsi > 55 and rsi < 70:
            signal = 'SHORT'
    
    if signal:
        return {
            'signal': signal,
            'symbol': symbol,
            'rsi': rsi,
            'price': price,
            'stop': stop_pct,
            'strategy': primary_strategy
        }
    return None

def run_scan() -> list:
    """Run full scan on all pairs"""
    results = []
    
    print(f"[{datetime.now().strftime('%I:%M:%S %p UTC')}] Wayne scanning...")
    
    for symbol in STOCKS + CRYPTO:
        result = scan_symbol(symbol, 'RSI_PULLBACK')
        if result:
            results.append(result)
            print(f"  {symbol}: RSI={result['rsi']:.1f} → {result['signal']}")
    
    return results

def paper_trade_alert(signal: dict):
    """Log paper trade (NO real execution)"""
    msg = format_signal(
        signal['signal'],
        signal['symbol'],
        signal['rsi'],
        signal['price'],
        signal['stop']
    )
    print(msg)
    send_telegram(msg + "\n\n<i>⚠️ PAPER TRADING ONLY — NO REAL MONEY</i>")

def main():
    print("=" * 60)
    print(f"Wayne Trading Agent — {datetime.now().strftime('%Y-%m-%d %I:%M %p UTC')}")
    print("=" * 60)
    print("Mode: PAPER TRADING (no real money)")
    print(f"Stocks: {', '.join(STOCKS)}")
    print(f"Crypto: {', '.join(CRYPTO)}")
    print("Strategy: RSI Pullback")
    print("-" * 60)
    
    results = run_scan()
    
    print("-" * 60)
    if results:
        print(f"Signals found: {len(results)}")
        for r in results:
            paper_trade_alert(r)
    else:
        print("No signals triggered")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
