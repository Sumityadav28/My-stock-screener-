import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Stock Screener & Trade Engine", layout="wide", page_icon="📈")

st.title("📈 Daily Market Screener & Trade Engine")
st.caption("Live multi-strategy consensus rankings, stop-loss, profit targets, and candlestick patterns.")

# Watchlist of Indian market leaders
WATCHLIST = [
    "TCS.NS", "RELIANCE.NS", "HDFCBANK.NS", 
    "INFY.NS", "ICICIBANK.NS", "BHARTIARTL.NS", "ITC.NS", "LT.NS"
]

def detect_candlestick_patterns(df):
    """Detects major reversal patterns on recent daily candles."""
    if len(df) < 5:
        return []
    
    c0 = df.iloc[-3]
    c1 = df.iloc[-2]
    c2 = df.iloc[-1]
    
    body_2 = abs(c2["Close"] - c2["Open"])
    range_2 = c2["High"] - c2["Low"]
    upper_wick_2 = c2["High"] - max(c2["Close"], c2["Open"])
    lower_wick_2 = min(c2["Close"], c2["Open"]) - c2["Low"]
    is_green_2 = c2["Close"] > c2["Open"]
    is_red_2 = c2["Close"] < c2["Open"]
    is_green_1 = c1["Close"] > c1["Open"]
    is_red_1 = c1["Close"] < c1["Open"]
    
    patterns = []
    
    # Doji
    if range_2 > 0 and body_2 <= (0.10 * range_2):
        if lower_wick_2 >= (0.65 * range_2):
            patterns.append(("Dragonfly Doji", "Bullish Reversal", +1))
        elif upper_wick_2 >= (0.65 * range_2):
            patterns.append(("Gravestone Doji", "Bearish Reversal", -1))
        else:
            patterns.append(("Doji", "Indecision", 0))

    # Hammer & Hanging Man
    if lower_wick_2 >= (2.0 * body_2) and upper_wick_2 <= (0.25 * body_2) and body_2 > 0:
        if is_red_1:
            patterns.append(("Bullish Hammer", "Bullish Reversal", +2))
        else:
            patterns.append(("Hanging Man", "Bearish Warning", -1))
            
    # Shooting Star & Inverted Hammer
    if upper_wick_2 >= (2.0 * body_2) and lower_wick_2 <= (0.25 * body_2) and body_2 > 0:
        if is_green_1:
            patterns.append(("Shooting Star", "Bearish Reversal", -2))
        else:
            patterns.append(("Inverted Hammer", "Bullish Reversal", +1))

    # Engulfing Patterns
    if is_red_1 and is_green_2:
        if c2["Open"] <= c1["Close"] and c2["Close"] >= c1["Open"]:
            patterns.append(("Bullish Engulfing", "Strong Bullish Reversal", +2))
    elif is_green_1 and is_red_2:
        if c2["Open"] >= c1["Close"] and c2["Close"] <= c1["Open"]:
            patterns.append(("Bearish Engulfing", "Strong Bearish Reversal", -2))

    return patterns

def calculate_supertrend(df, period=10, multiplier=3):
    """Calculates Supertrend trailing support/resistance."""
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

def analyze_single_stock(ticker):
    """Runs all technical and fundamental checks on a stock."""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="6mo")
        if len(df) < 50:
            return None
            
        latest_close = df["Close"].iloc[-1]
        
        # Moving averages
        df["SMA_20"] = df["Close"].rolling(20).mean()
        df["SMA_50"] = df["Close"].rolling(50).mean()
        sma20 = df["SMA_20"].iloc[-1]
        sma50 = df["SMA_50"].iloc[-1]
        
        # RSI
        delta = df["Close"].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rsi = (100 - (100 / (1 + (gain / loss)))).iloc[-1]
        
        # MACD
        ema_12 = df["Close"].ewm(span=12, adjust=False).mean()
        ema_26 = df["Close"].ewm(span=26, adjust=False).mean()
        macd = ema_12 - ema_26
        macd_signal = macd.ewm(span=9, adjust=False).mean()
        macd_bullish = macd.iloc[-1] > macd_signal.iloc[-1]
        
        # Supertrend
        st_bullish, st_support = calculate_supertrend(df)
        
        # Candlestick patterns
        patterns = detect_candlestick_patterns(df)
        candle_pts = sum(p[2] for p in patterns)
        
        # Fundamentals
        info = stock.info
        name = info.get("shortName", ticker)
        pe = info.get("trailingPE")
        roe = info.get("returnOnEquity")
        
        # Scoring out of 10 points
        score = 0
        if st_bullish: score += 2
        if macd_bullish: score += 2
        if latest_close > sma20 > sma50: score += 2
        elif latest_close > sma20: score += 1
        if 40 <= rsi <= 68: score += 1
        if roe and roe >= 0.15: score += 1
        if pe and pe < 35: score += 1
        if candle_pts > 0: score += 1
        
        # Trade levels (2:1 reward-to-risk)
        support = max(df["Low"].tail(20).min(), st_support)
        stop_loss = support * 0.99
        risk = latest_close - stop_loss
        target_2 = latest_close + (2.0 * risk)
        
        pattern_label = ", ".join([p[0] for p in patterns]) if patterns else "Consolidation"
        
        return {
            "Ticker": ticker,
            "Name": name,
            "Price": round(latest_close, 2),
            "Score": score,
            "Supertrend": "Bullish" if st_bullish else "Bearish",
            "RSI": round(rsi, 1),
            "P/E": round(pe, 1) if pe else "N/A",
            "ROE": f"{round(roe * 100, 1)}%" if roe else "N/A",
            "Pattern": pattern_label,
            "StopLoss": round(stop_loss, 2),
            "Target": round(target_2, 2)
        }
    except Exception:
        return None

@st.cache_data(ttl=900)
def load_all_stocks():
    results = [analyze_single_stock(t) for t in WATCHLIST]
    return [r for r in results if r is not None]

# --- 1. ALL-STOCKS LEADERBOARD TABLE ---
st.subheader("📋 Market Leaderboard (All Watchlist Stocks)")
with st.spinner("Scanning market data across all strategies..."):
    all_data = load_all_stocks()

if all_data:
    df_table = pd.DataFrame(all_data).sort_values(by="Score", ascending=False)
    
    st.dataframe(
        df_table[["Ticker", "Name", "Price", "Score", "Supertrend", "RSI", "P/E", "StopLoss", "Target"]],
        use_container_width=True,
        hide_index=True
    )
    
    # --- 2. SINGLE STOCK DEEP-DIVE & CHART ---
    st.divider()
    st.subheader("🔍 Detailed Stock Inspection & Chart")
    
    ticker_list = list(df_table["Ticker"].values)
    selected = st.selectbox("Select stock to inspect:", ticker_list, index=0)
    
    # Fetch chart data for chosen stock
    stock_obj = yf.Ticker(selected)
    hist = stock_obj.history(period="6mo")
    
    if len(hist) >= 30:
        latest_c = hist["Close"].iloc[-1]
        hist["SMA_20"] = hist["Close"].rolling(20).mean()
        hist["SMA_50"] = hist["Close"].rolling(50).mean()
        
        row = df_table[df_table["Ticker"] == selected].iloc[0]
        sl = row["StopLoss"]
        tgt = row["Target"]
        risk_amt = latest_c - sl
        
        # Metric cards
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Current Price", f"₹{latest_c:.2f}")
        m2.metric("Stop-Loss (Exit)", f"₹{sl:.2f}", f"-₹{risk_amt:.2f}", delta_color="inverse")
        m3.metric("Target (2:1)", f"₹{tgt:.2f}", f"+₹{(tgt - latest_c):.2f}")
        m4.metric("Consensus Score", f"{row['Score']} / 10")
        
        # Interactive Candlestick Chart
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=hist.index, open=hist["Open"], high=hist["High"],
            low=hist["Low"], close=hist["Close"], name="Candlestick"
        ))
        fig.add_trace(go.Scatter(x=hist.index, y=hist["SMA_20"], line=dict(color="orange", width=1.5), name="SMA 20"))
        fig.add_trace(go.Scatter(x=hist.index, y=hist["SMA_50"], line=dict(color="blue", width=1.5), name="SMA 50"))
        fig.add_hline(y=tgt, line_dash="dash", line_color="green", annotation_text=f"Target: ₹{tgt:.2f}")
        fig.add_hline(y=sl, line_dash="dash", line_color="red", annotation_text=f"Stop-Loss: ₹{sl:.2f}")
        
        fig.update_layout(xaxis_rangeslider_visible=False, height=480, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)
        
        st.info(f"🕯️ **Candlestick Pattern Status:** {row['Pattern']}")
else:
    st.error("Market data currently unavailable. Please try refreshing in a few moments.")
