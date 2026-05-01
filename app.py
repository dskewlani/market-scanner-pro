# ================================
# IMPORTS
# ================================
import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, time as dtime
from concurrent.futures import ThreadPoolExecutor
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# ================================
# CONFIG
# ================================
st.set_page_config(page_title="ORB V21 Accuracy Pro", layout="wide")
st.title("🎯 ORB V21 (High Accuracy Trading System)")

st_autorefresh(interval=60 * 1000, key="refresh")

INITIAL_CAPITAL = 100000

# ================================
# USER INPUTS
# ================================
col1, col2, col3 = st.columns(3)

with col1:
    orb_minutes = st.number_input("ORB Minutes", 5, 60, 15)

with col2:
    ema_period = st.number_input("EMA Period", 5, 100, 20)

with col3:
    risk_pct = st.slider("Risk %", 0.5, 2.0, 1.0)

# ================================
# SESSION STATE
# ================================
if "capital" not in st.session_state:
    st.session_state.capital = INITIAL_CAPITAL

if "active_trades" not in st.session_state:
    st.session_state.active_trades = {}

if "closed_trades" not in st.session_state:
    st.session_state.closed_trades = []

if "equity" not in st.session_state:
    st.session_state.equity = []

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
    df["EMA"] = df["Close"].ewm(span=ema_period).mean()

    # ATR
    df["H-L"] = df["High"] - df["Low"]
    df["H-PC"] = abs(df["High"] - df["Close"].shift(1))
    df["L-PC"] = abs(df["Low"] - df["Close"].shift(1))
    df["TR"] = df[["H-L", "H-PC", "L-PC"]].max(axis=1)
    df["ATR"] = df["TR"].rolling(14).mean()

    # Volume
    df["Vol_Avg"] = df["Volume"].rolling(20).mean()

    # Candle strength
    body = abs(df["Close"] - df["Open"])
    rng = (df["High"] - df["Low"]).replace(0, 1e-9)
    df["BodyPct"] = body / rng

    return df

# ================================
# ACCURACY FILTERS
# ================================
def breakout_confirmed(df, level, direction):
    last = df["Close"].iloc[-1]
    prev = df["Close"].iloc[-2]
    return (prev > level and last > level) if direction == "BUY" else (prev < level and last < level)

def strong_candle(df):
    return df["BodyPct"].iloc[-1] >= 0.6

def volume_quality(df):
    return df["Volume"].iloc[-1] > df["Vol_Avg"].iloc[-1] * 1.8

def ema_distance_ok(df):
    price = df["Close"].iloc[-1]
    ema = df["EMA"].iloc[-1]
    dist = abs(price - ema) / ema
    return 0.005 <= dist <= 0.02

def atr_filter(df):
    return (df["ATR"].iloc[-1] / df["Close"].iloc[-1]) > 0.003

# ================================
# ENTRY LOGIC (V21)
# ================================
def get_signal(df):

    df = add_indicators(df)
    df["Time"] = df.index.time

    cutoff = (datetime.combine(datetime.today(), dtime(9, 15)) +
              pd.Timedelta(minutes=orb_minutes)).time()

    orb_df = df[df["Time"] <= cutoff]

    if orb_df.empty:
        return None

    high = orb_df["High"].max()
    low = orb_df["Low"].min()

    last = df["Close"].iloc[-1]

    if last > high:
        direction = "BUY"
        level = high
    elif last < low:
        direction = "SELL"
        level = low
    else:
        return None

    # Accuracy filters
    if not breakout_confirmed(df, level, direction):
        return None
    if not strong_candle(df):
        return None
    if not volume_quality(df):
        return None
    if not ema_distance_ok(df):
        return None
    if not atr_filter(df):
        return None

    return direction, last, high, low

# ================================
# POSITION SIZE
# ================================
def calculate_qty(entry, sl):
    risk_amount = st.session_state.capital * (risk_pct / 100)
    risk_per_share = abs(entry - sl)
    if risk_per_share == 0:
        return 0
    return int(risk_amount / risk_per_share)

# ================================
# TRADE FUNCTIONS
# ================================
def enter_trade(symbol, signal, price, high, low):
    sl = low if signal == "BUY" else high
    qty = calculate_qty(price, sl)

    st.session_state.active_trades[symbol] = {
        "type": signal,
        "entry": price,
        "sl": sl,
        "qty": qty
    }

def manage_trade(symbol, df):
    trade = st.session_state.active_trades[symbol]
    price = df["Close"].iloc[-1]

    # Trailing SL
    if trade["type"] == "BUY":
        trade["sl"] = max(trade["sl"], price * 0.995)
        if price <= trade["sl"]:
            pnl = (price - trade["entry"]) * trade["qty"]
            exit_trade(symbol, price, pnl)
    else:
        trade["sl"] = min(trade["sl"], price * 1.005)
        if price >= trade["sl"]:
            pnl = (trade["entry"] - price) * trade["qty"]
            exit_trade(symbol, price, pnl)

def exit_trade(symbol, price, pnl):
    trade = st.session_state.active_trades.pop(symbol)
    st.session_state.capital += pnl

    st.session_state.closed_trades.append({
        "Symbol": symbol,
        "Entry": trade["entry"],
        "Exit": price,
        "PnL": round(pnl,2)
    })

# ================================
# RUN SCANNER
# ================================
with ThreadPoolExecutor(max_workers=5) as executor:
    data = list(executor.map(fetch, symbols))

for symbol, df in data:

    if df is None or len(df) < 30:
        continue

    if symbol not in st.session_state.active_trades:
        signal = get_signal(df)
        if signal:
            enter_trade(symbol, *signal)
    else:
        manage_trade(symbol, df)

# ================================
# EQUITY CURVE
# ================================
st.session_state.equity.append({
    "time": datetime.now(),
    "capital": st.session_state.capital
})

equity_df = pd.DataFrame(st.session_state.equity)

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
st.write("🕒", datetime.now().strftime("%H:%M:%S"))
