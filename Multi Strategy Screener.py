"""
Multi-Strategy Quantitative Screener
Evaluates stocks using Supertrend, MACD, 20/50/200 SMA, RSI, Bollinger Bands, Fundamentals, and Candlestick Patterns.
"""
import yfinance as yf
import pandas as pd
import numpy as np
from candlestick_patterns import detect_candlestick_patterns

watchlist = [
    "TCS.NS", "RELIANCE.NS", "HDFCBANK.NS", 
    "INFY.NS", "ICICIBANK.NS", "BHARTIARTL.NS", "ITC.NS", "LT.NS"
]

def calculate_supertrend(df, period=10, multiplier=3):
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    
    hl2 = (high + low) / 2
    basic_upper = hl2 + (multiplier * atr)
    basic_lower = hl2 - (multiplier * atr)
    
    upper_band = basic_upper.copy()
    lower_band = basic_lower.copy()
    supertrend = pd.Series(True, index=df.index)
    
    for i in range(1, len(df)):
        if basic_upper.iloc[i] < upper_band.iloc[i-1] or close.iloc[i-1] > upper_band.iloc[i-1]:
            upper_band.iloc[i] = basic_upper.iloc[i]
        else:
            upper_band.iloc[i] = upper_band.iloc[i-1]
            
        if basic_lower.iloc[i] > lower_band.iloc[i-1] or close.iloc[i-1] < lower_band.iloc[i-1]:
            lower_band.iloc[i] = basic_lower.iloc[i]
        else:
            lower_band.iloc[i] = lower_band.iloc[i-1]
            
        if close.iloc[i] > upper_band.iloc[i-1]:
            supertrend.iloc[i] = True
        elif close.iloc[i] < lower_band.iloc[i-1]:
            supertrend.iloc[i] = False
        else:
            supertrend.iloc[i] = supertrend.iloc[i-1]
            
    return supertrend.iloc[-1], lower_band.iloc[-1]

def analyze_stock_full(ticker):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y")
        if len(df) < 60:
            return None
            
        latest_close = df["Close"].iloc[-1]
        
        # 1. Moving Averages
        df["SMA_20"] = df["Close"].rolling(20).mean()
        df["SMA_50"] = df["Close"].rolling(50).mean()
        df["SMA_200"] = df["Close"].rolling(min(200, len(df))).mean()
        sma20 = df["SMA_20"].iloc[-1]
        sma50 = df["SMA_50"].iloc[-1]
        sma200 = df["SMA_200"].iloc[-1]
        
        # 2. MACD
        ema_12 = df["Close"].ewm(span=12, adjust=False).mean()
        ema_26 = df["Close"].ewm(span=26, adjust=False).mean()
        df["MACD"] = ema_12 - ema_26
        df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
        macd_val = df["MACD"].iloc[-1]
        macd_sig = df["MACD_Signal"].iloc[-1]
        
        # 3. Bollinger Bands
        bb_std = df["Close"].rolling(20).std()
        bb_upper = sma20 + (2 * bb_std.iloc[-1])
        bb_lower = sma20 - (2 * bb_std.iloc[-1])
        
        # 4. RSI
        delta = df["Close"].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rsi = (100 - (100 / (1 + (gain / loss)))).iloc[-1]
        
        # 5. Supertrend
        st_bullish, st_support = calculate_supertrend(df)
        
        # 6. Candlestick Patterns
        patterns = detect_candlestick_patterns(df)
        candle_points = sum(p[2] for p in patterns)
        
        # 7. Fundamentals
        info = stock.info
        pe = info.get("trailingPE")
        roe = info.get("returnOnEquity")
        de = info.get("debtToEquity")
        name = info.get("shortName", ticker)
        
        # Scoring (Out of 10)
        score = 0
        if st_bullish: score += 2
        if macd_val > macd_sig: score += 2
        if latest_close > sma20 > sma50: score += 2
        elif latest_close > sma200: score += 1
        
        if 40 <= rsi <= 65 or rsi < 35: score += 1
        if latest_close > sma20 and latest_close < bb_upper: score += 1
        
        if roe and roe >= 0.15: score += 1
        if pe and pe < 35: score += 1
        if candle_points > 0: score += 1
        
        # Risk Management (2:1 Ratio)
        support = max(df["Low"].tail(20).min(), st_support)
        stop_loss = support * 0.99
        risk = latest_close - stop_loss
        target_1 = latest_close + (1.5 * risk)
        target_2 = latest_close + (2.0 * risk)
        
        pattern_str = ", ".join([p[0] for p in patterns]) if patterns else "Consolidation"
        
        return {
            "Ticker": ticker,
            "Name": name,
            "Price": round(latest_close, 2),
            "Score": score,
            "RSI": round(rsi, 1),
            "P/E": round(pe, 1) if pe else "N/A",
            "ROE": f"{round(roe * 100, 1)}%" if roe else "N/A",
            "Supertrend": "Bullish" if st_bullish else "Bearish",
            "Candles": pattern_str,
            "StopLoss": round(stop_loss, 2),
            "Target1": round(target_1, 2),
            "Target2": round(target_2, 2)
        }
    except Exception as e:
        return None

if __name__ == "__main__":
    print("Running Multi-Strategy Market Screener...")
    results = [analyze_stock_full(t) for t in watchlist]
    results = [r for r in results if r is not None]
    
    df_res = pd.DataFrame(results).sort_values(by="Score", ascending=False)
    top = df_res.iloc[0]
    
    print("
" + "=" * 60)
    print(f"⭐ BEST TRADE TODAY: {top['Name']} ({top['Ticker']})")
    print(f"Consensus Score: {top['Score']} / 10 | Supertrend: {top['Supertrend']}")
    print(f"Current Price:   ₹{top['Price']}")
    print(f"Stop-Loss:       ₹{top['StopLoss']}")
    print(f"Target 1 (1.5x): ₹{top['Target1']}")
    print(f"Target 2 (2:1):  ₹{top['Target2']}")
    print(f"Candlestick:     {top['Candles']}")
    print("=" * 60)
    print("
--- Full Market Leaderboard ---")
    print(df_res[["Ticker", "Price", "Score", "Supertrend", "RSI", "P/E", "StopLoss", "Target2"]].to_string(index=False))