#!/usr/bin/env python3
"""
Wayne Tape Feed
Real-time trade tape from Coinbase WebSocket
Shows buy/sell pressure, absorption, and tape direction
"""
import json
import time
import threading
from datetime import datetime
from collections import deque

# Buffered tape per symbol
TAPE_BUFFER = deque(maxlen=100)
SYMBOLS = ['BTC-USD', 'ETH-USD', 'SOL-USD']
COINBASE_WS = 'wss://ws-feed.exchange.coinbase.com'

class TapeReader:
    def __init__(self):
        self.tapes = {s: deque(maxlen=200) for s in SYMBOLS}
        self.running = False
        
    def process_message(self, msg):
        try:
            data = json.loads(msg)
            if data.get('type') == 'match':
                symbol = data.get('product_id', '')
                side = data.get('side', '')
                price = float(data.get('price', 0))
                size = float(data.get('size', 0))
                
                if symbol in SYMBOLS:
                    self.tapes[symbol].append({
                        'time': datetime.now(),
                        'side': side,
                        'price': price,
                        'size': size
                    })
        except:
            pass
    
    def get_tape_stats(self, symbol: str) -> dict:
        """Calculate tape metrics for symbol"""
        tape = list(self.tapes.get(symbol, []))
        if not tape:
            return {'direction': 'NEUTRAL', 'buy_ratio': 0.5, 'absorption': 0, 'signal': 'WAIT'}
        
        # Buy/Sell ratio (last 50 prints)
        recent = tape[-50:]
        buys = sum(1 for t in recent if t['side'] == 'buy')
        sells = sum(1 for t in recent if t['side'] == 'sell')
        total = buys + sells or 1
        buy_ratio = buys / total
        
        # Absorption detection (large sells with no price drop)
        large_sells = [t for t in recent if t['side'] == 'sell' and t['size'] > 0.5]
        absorption_score = 0
        if large_sells:
            price_before = recent[0]['price'] if recent else 0
            price_after = recent[-1]['price']
            if price_after >= price_before * 0.99:  # Price held
                absorption_score = min(10, len(large_sells) * 2)
        
        # Direction
        if buy_ratio > 0.6:
            direction = 'BULLISH'
        elif buy_ratio < 0.4:
            direction = 'BEARISH'
        else:
            direction = 'NEUTRAL'
        
        # Combined signal
        if direction == 'BULLISH' and absorption_score >= 7:
            signal = 'REVERSAL_LONG'
        elif direction == 'BEARISH' and absorption_score >= 7:
            signal = 'REVERSAL_SHORT'
        elif direction == 'BULLISH':
            signal = 'TAPE_LONG'
        elif direction == 'BEARISH':
            signal = 'TAPE_SHORT'
        else:
            signal = 'WAIT'
        
        return {
            'symbol': symbol,
            'direction': direction,
            'buy_ratio': round(buy_ratio, 2),
            'absorption': absorption_score,
            'signal': signal,
            'prints': len(recent),
            'time': datetime.now().strftime('%H:%M:%S')
        }
    
    def get_combined_signal(self, systematic_signal: str = None) -> dict:
        """Combine tape with systematic signal"""
        results = {s: self.get_tape_stats(s) for s in SYMBOLS}
        
        # Aggregate
        bullish_count = sum(1 for r in results.values() if r['direction'] == 'BULLISH')
        bearish_count = sum(1 for r in results.values() if r['direction'] == 'BEARISH')
        
        if bullish_count > bearish_count:
            aggregate = 'BULLISH'
        elif bearish_count > bullish_count:
            aggregate = 'BEARISH'
        else:
            aggregate = 'NEUTRAL'
        
        return {
            'aggregate': aggregate,
            'symbols': results,
            'systematic': systematic_signal,
            'combined': systematic_signal if systematic_signal in ['LONG', 'SHORT'] and aggregate != 'NEUTRAL' else 'WAIT',
            'time': datetime.now().strftime('%H:%M:%S')
        }

def format_tape_report(report: dict) -> str:
    """Format tape report for display/Telegram"""
    lines = [
        "📊 <b>Wayne Tape Feed</b>",
        f"⏰ {report['time']} UTC",
        f"📈 Aggregate: <b>{report['aggregate']}</b>",
        ""
    ]
    
    for symbol, stats in report['symbols'].items():
        emoji = {'BULLISH': '🟢', 'BEARISH': '🔴', 'NEUTRAL': '⚪'}.get(stats['direction'], '⚪')
        lines.append(f"{emoji} {symbol}: {stats['direction']} (buy {stats['buy_ratio']*100:.0f}%)")
        lines.append(f"   Absorption: {stats['absorption']}/10 | Signal: {stats['signal']}")
    
    if report.get('combined') and report['combined'] != 'WAIT':
        lines.append("")
        lines.append(f"🎯 <b>Combined Signal: {report['combined']}</b>")
    
    return '\n'.join(lines)

if __name__ == "__main__":
    tape = TapeReader()
    print("Wayne Tape Feed - Starting...")
    print("Symbols:", SYMBOLS)
    print("Note: WebSocket requires full exchange connection")
    print()
    print("To use in trading system:")
    print("  from wayne_tape_feed import TapeReader, format_tape_report")
    print("  tape = TapeReader()")
    print("  report = tape.get_combined_signal(systematic_signal='LONG')")
