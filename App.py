import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from candlestick_patterns import detect_candlestick_patterns

st.set_page_config(page_title="Stock Analyzer & Trade Engine", layout="wide", page_icon="📈")

st.title("📈 Daily Market Screener & Trade Engine")
st.caption("Live multi-strategy rankings, automatic stop-loss, profit targets, and chart patterns.")

watchlist = [
    "TCS.NS", "RELIANCE.NS", "HDFCBANK.NS", 
    "INFY.NS", "ICICIBANK.NS", "BHARTIARTL.NS", "ITC.NS", "LT.NS"
]

@st.cache_data(ttl=900)  # Caches market data for 15 minutes
def scan_all_watchlist():
    from multi_strategy_screener import analyze_stock_full
    data = [analyze_stock_full(t) for t in watchlist]
    return [d for d in data if d is not None]

# 1. SHOW ALL STOCKS IMMEDIATELY ON THE FRONT PAGE
st.subheader("📋 Market Leaderboard (All Watchlist Stocks)")
with st.spinner("Fetching latest market data for all stocks..."):
    all_stocks = scan_all_watchlist()

if all_stocks:
    df_all = pd.DataFrame(all_stocks).sort_values(by="Score", ascending=False)
    
    # Display the complete multi-stock overview table
    st.dataframe(
        df_all[["Ticker", "Name", "Price", "Score", "Supertrend", "RSI", "P/E", "StopLoss", "Target2"]],
        use_container_width=True,
        hide_index=True
    )
    
    # 2. SELECTOR TO INSPECT ANY STOCK'S DETAILED CHART BELOW
    st.divider()
    st.subheader("🔍 Detailed Stock Inspection")
    
    ticker_options = list(df_all["Ticker"].values)
    selected_ticker = st.selectbox("Select a stock to view its full chart & trade levels:", ticker_options, index=0)
    
    # Fetch detailed history for the chosen stock
    stock = yf.Ticker(selected_ticker)
    df = stock.history(period="1y")
    
    if len(df) >= 50:
        latest_close = df["Close"].iloc[-1]
        df["SMA_20"] = df["Close"].rolling(20).mean()
        df["SMA_50"] = df["Close"].rolling(50).mean()
        
        # Risk management levels
        support = df["Low"].tail(20).min()
        stop_loss = support * 0.99
        risk = latest_close - stop_loss
        target_2 = latest_close + (2.0 * risk)
        
        patterns = detect_candlestick_patterns(df)
        
        # Metric Cards
        c1, c2, c3 = st.columns(3)
        c1.metric("Current Price", f"₹{latest_close:.2f}")
        c2.metric("Stop-Loss (Exit)", f"₹{stop_loss:.2f}", f"-₹{risk:.2f}", delta_color="inverse")
        c3.metric("Target (2:1)", f"₹{target_2:.2f}", f"+₹{(target_2 - latest_close):.2f}")
        
        # Interactive Candlestick Chart
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df.index, open=df["Open"], high=df["High"],
            low=df["Low"], close=df["Close"], name="Price"
        ))
        fig.add_trace(go.Scatter(x=df.index, y=df["SMA_20"], line=dict(color="orange", width=1.5), name="SMA 20"))
        fig.add_trace(go.Scatter(x=df.index, y=df["SMA_50"], line=dict(color="blue", width=1.5), name="SMA 50"))
        fig.add_hline(y=target_2, line_dash="dash", line_color="green", annotation_text=f"Target: ₹{target_2:.2f}")
        fig.add_hline(y=stop_loss, line_dash="dash", line_color="red", annotation_text=f"Stop-Loss: ₹{stop_loss:.2f}")
        
        fig.update_layout(xaxis_rangeslider_visible=False, height=480, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)
        
        # Candlestick summary
        if patterns:
            pattern_text = ", ".join([f"{p[0]} ({p[1]})" for p in patterns])
            st.info(f"🕯️ **Candlestick Patterns Detected:** {pattern_text}")
        else:
            st.info("🕯️ **Candlestick Status:** Normal consolidation, no major reversal pattern.")
