"""
Automated Telegram Alert Script
Runs the multi-strategy screener and sends the top stock recommendation to Android.
"""
import os
import requests
from multi_strategy_screener import analyze_stock_full, watchlist
import pandas as pd

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_TELEGRAM_CHAT_ID_HERE")

def send_daily_alert():
    print("Scanning market leaders...")
    results = [analyze_stock_full(t) for t in watchlist]
    results = [r for r in results if r is not None]
    
    if not results:
        print("No market data returned.")
        return
        
    df = pd.DataFrame(results).sort_values(by="Score", ascending=False)
    top = df.iloc[0]
    
    message = (
        f"🔔 *Daily Market Recommendation*

"
        f"📌 *Stock:* {top['Name']} (`{top['Ticker']}`)
"
        f"⭐ *Consensus Score:* {top['Score']} / 10 points
"
        f"📈 *Trend:* Supertrend {top['Supertrend']} | RSI {top['RSI']}
"
        f"🕯️ *Candlestick:* {top['Candles']}

"
        f"💰 *Current Price:* ₹{top['Price']}
"
        f"🛑 *Stop-Loss:* ₹{top['StopLoss']}
"
        f"🎯 *Target 1 (1.5x):* ₹{top['Target1']}
"
        f"🎯 *Target 2 (2.0x):* ₹{top['Target2']}

"
        f"📊 *Valuation:* P/E {top['P/E']} | ROE {top['ROE']}
"
        f"⚠️ _Verify chart setup before market opening._"
    )
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            print("Alert successfully sent to Android Telegram!")
        else:
            print(f"Telegram response: {res.text}")
    except Exception as e:
        print(f"Failed to send alert: {e}")

if __name__ == "__main__":
    send_daily_alert()
