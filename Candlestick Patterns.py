"""
Candlestick Pattern Recognition Engine
Scans daily price history and identifies single, double, and triple candle patterns.
"""
import pandas as pd
import numpy as np

def detect_candlestick_patterns(df):
    """
    Scans the most recent 3 daily candles and returns all detected patterns
    along with their market bias (Bullish, Bearish, or Neutral).
    """
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
    
    body_1 = abs(c1["Close"] - c1["Open"])
    range_1 = c1["High"] - c1["Low"]
    is_green_1 = c1["Close"] > c1["Open"]
    is_red_1 = c1["Close"] < c1["Open"]
    
    body_0 = abs(c0["Close"] - c0["Open"])
    is_green_0 = c0["Close"] > c0["Open"]
    is_red_0 = c0["Close"] < c0["Open"]
    
    detected = []
    
    # Doji
    if range_2 > 0 and body_2 <= (0.10 * range_2):
        if lower_wick_2 >= (0.65 * range_2):
            detected.append(("Dragonfly Doji", "Bullish Reversal", +1))
        elif upper_wick_2 >= (0.65 * range_2):
            detected.append(("Gravestone Doji", "Bearish Reversal", -1))
        else:
            detected.append(("Standard Doji", "Market Indecision", 0))

    # Hammer & Hanging Man
    if lower_wick_2 >= (2.0 * body_2) and upper_wick_2 <= (0.25 * body_2) and body_2 > 0:
        if is_red_1:
            detected.append(("Bullish Hammer", "Bullish Reversal", +2))
        else:
            detected.append(("Hanging Man", "Bearish Warning", -1))
            
    # Shooting Star & Inverted Hammer
    if upper_wick_2 >= (2.0 * body_2) and lower_wick_2 <= (0.25 * body_2) and body_2 > 0:
        if is_green_1:
            detected.append(("Shooting Star", "Bearish Reversal", -2))
        else:
            detected.append(("Inverted Hammer", "Bullish Reversal", +1))

    # Engulfing Patterns
    if is_red_1 and is_green_2:
        if c2["Open"] <= c1["Close"] and c2["Close"] >= c1["Open"]:
            detected.append(("Bullish Engulfing", "Strong Bullish Reversal", +2))
            
    elif is_green_1 and is_red_2:
        if c2["Open"] >= c1["Close"] and c2["Close"] <= c1["Open"]:
            detected.append(("Bearish Engulfing", "Strong Bearish Reversal", -2))

    # Piercing Line & Dark Cloud Cover
    midpoint_1 = (c1["Open"] + c1["Close"]) / 2
    if is_red_1 and is_green_2 and c2["Open"] < c1["Low"] and c2["Close"] > midpoint_1 and c2["Close"] < c1["Open"]:
        detected.append(("Piercing Line", "Bullish Reversal", +2))
        
    if is_green_1 and is_red_2 and c2["Open"] > c1["High"] and c2["Close"] < midpoint_1 and c2["Close"] > c1["Open"]:
        detected.append(("Dark Cloud Cover", "Bearish Reversal", -2))

    # Morning Star & Evening Star
    if is_red_0 and body_0 > (0.5 * (c0["High"] - c0["Low"])):
        if body_1 <= (0.35 * body_0) and is_green_2 and c2["Close"] > ((c0["Open"] + c0["Close"]) / 2):
            detected.append(("Morning Star", "High-Probability Bullish Reversal", +3))
            
    if is_green_0 and body_0 > (0.5 * (c0["High"] - c0["Low"])):
        if body_1 <= (0.35 * body_0) and is_red_2 and c2["Close"] < ((c0["Open"] + c0["Close"]) / 2):
            detected.append(("Evening Star", "High-Probability Bearish Reversal", -3))

    # Three White Soldiers & Three Black Crows
    if is_green_0 and is_green_1 and is_green_2:
        if c2["Close"] > c1["Close"] > c0["Close"]:
            detected.append(("Three White Soldiers", "Strong Bullish Continuation", +2))
            
    if is_red_0 and is_red_1 and is_red_2:
        if c2["Close"] < c1["Close"] < c0["Close"]:
            detected.append(("Three Black Crows", "Strong Bearish Trend", -2))

    return detected