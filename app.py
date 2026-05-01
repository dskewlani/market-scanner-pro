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
st.set_page_config(page_title="ORB V20 PRO", layout="wide")
st.title("🚀 ORB V20 PRO (Multi Trade + Equity System)")

st_autorefresh(interval=60 * 1000, key="refresh")

INITIAL_CAPITAL = 100000
MAX_TRADES_PER_DAY = 5

# ================================
# SESSION STATE
# ================================
if "capital" not in st.session_state:
    st.session_state.capital = INITIAL_CAPITAL

if "equity_curve" not in st.session_state:
    st.session_state.equity_curve = []

if "active_trades" not in st.session_state:
    st.session_state.active_trades = {}

if "closed_trades" not in st.session_state:
    st.session_state.closed_trades = []

if "trade_count" not in st.session_state:
    st.session_state.trade_count = 0

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
# ENTRY LOGIC
# ================================
def check_entry(symbol, df):

    if symbol in st.session_state.active_trades:
        return

    if st.session_state.trade_count >= MAX_TRADES_PER_DAY:
        return

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
        return

    score = calculate_score(df)

    if score < 70:
        return

    sl = low if signal == "BUY" else high
    risk_per_share = abs(last - sl)

    if risk_per_share == 0:
        return

    qty = int((st.session_state.capital * 0.01) / risk_per_share)

    st.session_state.active_trades[symbol] = {
        "type": signal,
        "entry": last,
        "sl": sl,
        "qty": qty
    }

    st.session_state.trade_count += 1

# ================================
# EXIT LOGIC
# ================================
def manage_trade(symbol, df):

    trade = st.session_state.active_trades[symbol]
    price = df["Close"].iloc[-1]

    if trade["type"] == "BUY":
        if price <= trade["sl"]:
            pnl = (price - trade["entry"]) * trade["qty"]
            exit_trade(symbol, price, pnl)
    else:
        if price >= trade["sl"]:
            pnl = (trade["entry"] - price) * trade["qty"]
            exit_trade(symbol, price, pnl)

# ================================
# EXIT FUNCTION
# ================================
def exit_trade(symbol, price, pnl):

    trade = st.session_state.active_trades.pop(symbol)

    st.session_state.capital += pnl

    st.session_state.closed_trades.append({
        "Symbol": symbol,
        "Entry": trade["entry"],
        "Exit": price,
        "PnL": pnl
    })

# ================================
# RUN SCANNER
# ================================
with ThreadPoolExecutor(max_workers=5) as executor:
    data = list(executor.map(fetch, symbols))

for symbol, df in data:

    if df is None or len(df) < 20:
        continue

    check_entry(symbol, df)

    if symbol in st.session_state.active_trades:
        manage_trade(symbol, df)

# ================================
# EQUITY CURVE
# ================================
st.session_state.equity_curve.append({
    "time": datetime.now(),
    "capital": st.session_state.capital
})

equity_df = pd.DataFrame(st.session_state.equity_curve)

# ================================
# DISPLAY
# ================================
st.subheader("📈 Active Trades")
st.write(st.session_state.active_trades)

st.subheader("📜 Closed Trades")
st.write(pd.DataFrame(st.session_state.closed_trades))

st.subheader("📊 Equity Curve")

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=equity_df["time"],
    y=equity_df["capital"],
    mode="lines"
))

st.plotly_chart(fig, use_container_width=True)

st.metric("Capital", round(st.session_state.capital,2))
st.metric("Trades Today", st.session_state.trade_count)

st.write("🕒 Last Update:", datetime.now().strftime("%H:%M:%S"))
