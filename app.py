# ================================
# IMPORTS
# ================================
import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# ================================
# CONFIG
# ================================
st.set_page_config(page_title="ORB V19 PRO", layout="wide")
st.title("🚀 ORB V19 PRO (Top Trades + Equity Curve)")

st_autorefresh(interval=60 * 1000, key="refresh")

INITIAL_CAPITAL = 100000

# ================================
# SESSION STATE
# ================================
if "capital" not in st.session_state:
    st.session_state.capital = INITIAL_CAPITAL

if "equity_curve" not in st.session_state:
    st.session_state.equity_curve = []

if "trade_log" not in st.session_state:
    st.session_state.trade_log = []

# ================================
# SYMBOLS
# ================================
symbols = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS"]

# ================================
# FETCH
# ================================
def fetch(symbol):
    try:
        df = yf.download(symbol, interval="5m", period="1d", progress=False)
        df.dropna(inplace=True)
        return symbol, df
    except:
        return symbol, None

# ================================
# INDICATORS
# ================================
def add_indicators(df):
    df["EMA"] = df["Close"].ewm(span=20).mean()
    return df

# ================================
# SCORING
# ================================
def calculate_score(df):
    last = df["Close"].iloc[-1]
    ema = df["EMA"].iloc[-1]

    score = 0

    if last > ema:
        score += 50

    if abs(df["Close"].iloc[-1] - df["Close"].iloc[-2]) > 0.2:
        score += 50

    return score

# ================================
# PROCESS
# ================================
def process(symbol_df):
    symbol, df = symbol_df

    if df is None or len(df) < 20:
        return None

    df = add_indicators(df)

    high = df["High"].iloc[:3].max()
    low = df["Low"].iloc[:3].min()

    last = df["Close"].iloc[-1]

    signal = None
    if last > high:
        signal = "BUY"
    elif last < low:
        signal = "SELL"

    if not signal:
        return None

    score = calculate_score(df)

    sl = low if signal == "BUY" else high
    risk_per_share = abs(last - sl)

    if risk_per_share == 0:
        return None

    qty = int((st.session_state.capital * 0.01) / risk_per_share)

    return {
        "Symbol": symbol,
        "Signal": signal,
        "Price": last,
        "Score": score,
        "SL": sl,
        "Qty": qty
    }

# ================================
# RUN SCANNER
# ================================
results = []

with ThreadPoolExecutor(max_workers=5) as executor:
    data = list(executor.map(fetch, symbols))

for item in data:
    res = process(item)
    if res:
        results.append(res)

# ================================
# TOP 2 SELECTION
# ================================
df = pd.DataFrame(results)

if not df.empty:
    df = df.sort_values(by="Score", ascending=False).head(2)

# ================================
# DISPLAY
# ================================
st.subheader("🎯 Top 2 Trades")

if not df.empty:
    st.dataframe(df, use_container_width=True)

    # Simulated PnL update
    pnl = 0
    for _, row in df.iterrows():
        pnl += (row["Price"] - row["SL"]) * row["Qty"] * 0.3  # simulated move

    st.session_state.capital += pnl

else:
    st.write("No trades found")

# ================================
# EQUITY CURVE
# ================================
st.session_state.equity_curve.append({
    "time": datetime.now(),
    "capital": st.session_state.capital
})

equity_df = pd.DataFrame(st.session_state.equity_curve)

st.subheader("📈 Equity Curve")

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=equity_df["time"],
    y=equity_df["capital"],
    mode="lines",
    name="Equity"
))

st.plotly_chart(fig, use_container_width=True)

# ================================
# METRICS
# ================================
st.subheader("📊 Performance")

if not equity_df.empty:
    max_capital = equity_df["capital"].cummax()
    drawdown = (equity_df["capital"] - max_capital).min()

    st.metric("Current Capital", round(st.session_state.capital,2))
    st.metric("Max Drawdown", round(drawdown,2))

st.write("🕒 Last Update:", datetime.now().strftime("%H:%M:%S"))
