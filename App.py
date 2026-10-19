"""
Interactive Streamlit Web Dashboard
Deployable to Streamlit Community Cloud and installable as an Android Home Screen PWA.
"""
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from candlestick_patterns import detect_candlestick_patterns

st.set_page_config(page_title="Stock Analyzer & Trade Engine", layout="wide", page_icon="📈")

st.title("📈 Stock Analyzer & Trade Engine")
st.caption("Automated technical analysis, fundamental evaluation, stop-loss, and profit targets.")

default_watchlist = [
    "TCS.NS", "RELIANCE.NS", "HDFCBANK.NS", 
    "INFY.NS", "ICICIBANK.NS", "BHARTIARTL.NS", "ITC.NS", "LT.NS"
]

st.sidebar.header("Navigation & Settings")
selected_ticker = st.sidebar.selectbox("Choose Watchlist Stock:", default_watchlist)
custom_ticker = st.sidebar.text_input("Or enter custom ticker (e.g. TATAMOTORS.NS):")
ticker = custom_ticker.strip().upper() if custom_ticker else selected_ticker

@st.cache_data(ttl=1800)
def load_stock_data(symbol):
    stock = yf.Ticker(symbol)
    df = stock.history(period="1y")
    if len(df) < 50:
        return None, None
    
    df["SMA_20"] = df["Close"].rolling(20).mean()
    df["SMA_50"] = df["Close"].rolling(50).mean()
    
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    df["RSI"] = 100 - (100 / (1 + (gain / loss)))
    
    return df, stock.info

tab1, tab2 = st.tabs(["📊 Stock Deep Dive", "📋 Market Leaderboard"])

with tab1:
    df, info = load_stock_data(ticker)
    if df is not None:
        latest_close = df["Close"].iloc[-1]
        sma_20 = df["SMA_20"].iloc[-1]
        sma_50 = df["SMA_50"].iloc[-1]
        rsi = df["RSI"].iloc[-1]
        
        # Stop-loss and Targets
        support = df["Low"].tail(20).min()
        stop_loss = support * 0.99
        risk = latest_close - stop_loss
        target_1 = latest_close + (1.5 * risk)
        target_2 = latest_close + (2.0 * risk)
        
        # Candlestick patterns
        patterns = detect_candlestick_patterns(df)
        candle_bias = sum(p[2] for p in patterns)
        
        # Fundamentals
        pe = info.get("trailingPE", "N/A")
        roe = info.get("returnOnEquity")
        de = info.get("debtToEquity", "N/A")
        name = info.get("shortName", ticker)
        
        # Metrics Row
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Current Price", f"₹{latest_close:.2f}")
        c2.metric("Stop-Loss (Exit)", f"₹{stop_loss:.2f}", f"-₹{risk:.2f}", delta_color="inverse")
        c3.metric("Target (2:1)", f"₹{target_2:.2f}", f"+₹{(target_2 - latest_close):.2f}")
        c4.metric("14-Day RSI", f"{rsi:.1f}")
        
        # Chart
        st.subheader(f"{name} ({ticker}) — Technical Chart & Levels")
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df.index, open=df["Open"], high=df["High"],
            low=df["Low"], close=df["Close"], name="Candlestick"
        ))
        fig.add_trace(go.Scatter(x=df.index, y=df["SMA_20"], line=dict(color="orange", width=1.5), name="SMA 20"))
        fig.add_trace(go.Scatter(x=df.index, y=df["SMA_50"], line=dict(color="blue", width=1.5), name="SMA 50"))
        
        fig.add_hline(y=target_2, line_dash="dash", line_color="green", annotation_text=f"Target 2: ₹{target_2:.2f}")
        fig.add_hline(y=target_1, line_dash="dot", line_color="#81c784", annotation_text=f"Target 1: ₹{target_1:.2f}")
        fig.add_hline(y=stop_loss, line_dash="dash", line_color="red", annotation_text=f"Stop-Loss: ₹{stop_loss:.2f}")
        
        fig.update_layout(xaxis_rangeslider_visible=False, height=520, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)
        
        # Pattern and Fundamental Details
        col_p, col_f = st.columns(2)
        with col_p:
            st.subheader("Candlestick Patterns Detected")
            if patterns:
                for p_name, p_bias, p_val in patterns:
                    st.info(f"🕯️ **{p_name}** — {p_bias}")
            else:
                st.write("No major reversal pattern on the latest session (normal consolidation).")
                
        with col_f:
            st.subheader("Fundamental Health")
            st.write(f"• **P/E Ratio:** {f'{pe:.1f}' if isinstance(pe, (int, float)) else pe}")
            st.write(f"• **Return on Equity (ROE):** {f'{roe * 100:.1f}%' if roe else 'N/A'}")
            st.write(f"• **Debt-to-Equity:** {f'{de:.1f}%' if isinstance(de, (int, float)) else de}")
            
    else:
        st.error(f"Could not load data for symbol: {ticker}")

with tab2:
    st.subheader("Market Leaderboard Scan")
    if st.button("🔄 Scan Watchlist Now"):
        with st.spinner("Evaluating market leaders across strategies..."):
            from multi_strategy_screener import analyze_stock_full
            data_rows = [analyze_stock_full(t) for t in default_watchlist]
            data_rows = [r for r in data_rows if r is not None]
            df_table = pd.DataFrame(data_rows).sort_values(by="Score", ascending=False)
            st.dataframe(df_table[["Ticker", "Name", "Price", "Score", "Supertrend", "RSI", "P/E", "StopLoss", "Target2"]], use_container_width=True)
    else:
        st.info("Click the button above to run an automated scan across all watchlist stocks.")
