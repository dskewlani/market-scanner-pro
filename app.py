# ================================
# IMPORTS
# ================================
import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, time as dtime
from concurrent.futures import ThreadPoolExecutor
import requests
import os
from streamlit_autorefresh import st_autorefresh

# ================================
# CONFIG
# ================================
st.set_page_config(page_title="ORB V16 Pro", layout="wide")
st.title("💰 ORB V16 (Capital + Position Sizing)")

st_autorefresh(interval=60 * 1000, key="refresh")

LOG_FILE = "trade_log.csv"

# ================================
# USER SETTINGS
# ================================
st.sidebar.header("⚙ Risk Settings")

initial_capital = st.sidebar.number_input("Capital (₹)", 10000, 10000000, 100000)
risk_pct = st.sidebar.slider("Risk per Trade (%)", 0.5, 5.0, 1.0)
trailing_pct = st.sidebar.slider("Trailing SL (%)", 0.2, 5.0, 0.5)

# ================================
# TELEGRAM
# ================================
st.sidebar.header("📱 Telegram")
TOKEN = st.sidebar.text_input("Bot Token")
CHAT_ID = st.sidebar.text_input("Chat ID")

def send_telegram(msg):
    if TOKEN and CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
        except:
            pass

# ================================
# INPUTS
# ================================
col1, col2, col3 = st.columns(3)

with col1:
    category = st.selectbox("Market", ["Nifty 50", "Midcap", "Smallcap"])

with col2:
    orb_minutes = st.number_input("ORB Minutes", 1, 60, 15)

with col3:
    ema_period = st.number_input("EMA", 5, 100, 20)

# ================================
# SYMBOLS
# ================================
@st.cache_data(ttl=86400)
def get_symbols(cat):
    if cat == "Nifty 50":
        url = "https://archives.nseindia.com/content/indices/ind_nifty50list.csv"
    elif cat == "Midcap":
        url = "https://archives.nseindia.com/content/indices/ind_niftymidcap100list.csv"
    else:
        url = "https://archives.nseindia.com/content/indices/ind_niftysmallcap100list.csv"

    df = pd.read_csv(url)
    return [s + ".NS" for s in df["Symbol"]]

symbols = get_symbols(category)

# ================================
# SESSION STATE
# ================================
if "capital" not in st.session_state:
    st.session_state.capital = initial_capital

if "active_trades" not in st.session_state:
    st.session_state.active_trades = {}

if "closed_trades" not in st.session_state:
    st.session_state.closed_trades = []

if "running" not in st.session_state:
    st.session_state.running = False

# ================================
# START / STOP
# ================================
c1, c2 = st.columns(2)
with c1:
    if st.button("▶ Start"):
        st.session_state.running = True
with c2:
    if st.button("⏹ Stop"):
        st.session_state.running = False

# ================================
# FETCH
# ================================
def fetch(symbol):
    try:
        df = yf.download(symbol, interval="1m", period="1d", progress=False)
        df.dropna(inplace=True)
        return symbol, df
    except:
        return symbol, None

# ================================
# INDICATORS
# ================================
def add_indicators(df):
    df["EMA"] = df["Close"].ewm(span=ema_period).mean()
    df["TP"] = (df["High"] + df["Low"] + df["Close"]) / 3
    df["VWAP"] = (df["TP"] * df["Volume"]).cumsum() / df["Volume"].cumsum()
    return df

# ================================
# STRATEGY
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
    ema = df["EMA"].iloc[-1]
    vwap = df["VWAP"].iloc[-1]

    if last > high and last > ema and last > vwap:
        return "BUY", last, high, low
    elif last < low and last < ema and last < vwap:
        return "SELL", last, high, low

    return None

# ================================
# POSITION SIZING
# ================================
def calculate_qty(entry, sl):
    risk_amount = st.session_state.capital * (risk_pct / 100)
    risk_per_share = abs(entry - sl)

    if risk_per_share == 0:
        return 0

    qty = int(risk_amount / risk_per_share)
    return max(qty, 1)

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

    send_telegram(f"🚨 {signal} {symbol} @ {price} | Qty: {qty}")

def manage_trade(symbol, df):

    trade = st.session_state.active_trades[symbol]
    price = df["Close"].iloc[-1]

    if trade["type"] == "BUY":
        trade["sl"] = max(trade["sl"], price * (1 - trailing_pct / 100))
        if price <= trade["sl"]:
            pnl = (price - trade["entry"]) * trade["qty"]
            exit_trade(symbol, price, pnl)

    else:
        trade["sl"] = min(trade["sl"], price * (1 + trailing_pct / 100))
        if price >= trade["sl"]:
            pnl = (trade["entry"] - price) * trade["qty"]
            exit_trade(symbol, price, pnl)

def exit_trade(symbol, price, pnl):

    trade = st.session_state.active_trades.pop(symbol)
    st.session_state.capital += pnl

    record = {
        "Symbol": symbol,
        "Type": trade["type"],
        "Entry": trade["entry"],
        "Exit": price,
        "Qty": trade["qty"],
        "PnL": round(pnl, 2),
        "Capital": round(st.session_state.capital, 2)
    }

    st.session_state.closed_trades.append(record)

    send_telegram(f"❌ EXIT {symbol} | PnL: {round(pnl,2)} | Capital: {round(st.session_state.capital,2)}")

# ================================
# SCANNER
# ================================
if st.session_state.running:

    with ThreadPoolExecutor(max_workers=10) as executor:
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
# DASHBOARD
# ================================
st.subheader("💰 Capital")
st.metric("Current Capital", round(st.session_state.capital, 2))

st.subheader("📈 Active Trades")
st.write(st.session_state.active_trades)

st.subheader("📜 Trade History")

if st.session_state.closed_trades:
    df = pd.DataFrame(st.session_state.closed_trades)
    st.dataframe(df)

    st.metric("Total PnL", round(df["PnL"].sum(), 2))
    st.metric("Win Rate (%)", round((df["PnL"] > 0).mean() * 100, 2))
else:
    st.write("No trades yet")

st.write("🕒 Last Update:", datetime.now().strftime("%H:%M:%S"))
