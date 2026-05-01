\# ================================
# IMPORTS
# ================================
import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, time
from concurrent.futures import ThreadPoolExecutor
import requests
from streamlit_autorefresh import st_autorefresh

# ================================
# PAGE CONFIG
# ================================
st.set_page_config(page_title="ORB Dashboard V11", layout="wide")

st.title("📊 ORB Trading Dashboard (V11 Stable)")
st.write("Live Scanner + Telegram Alerts")

# ================================
# AUTO REFRESH (SAFE)
# ================================
st_autorefresh(interval=60 * 1000, key="refresh")

# ================================
# TELEGRAM CONFIG
# ================================
st.sidebar.header("📱 Telegram Settings")

TELEGRAM_TOKEN = st.sidebar.text_input("Bot Token")
TELEGRAM_CHAT_ID = st.sidebar.text_input("Chat ID")

def send_telegram(msg):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=5)
        except:
            pass

# ================================
# USER INPUTS
# ================================
col1, col2, col3 = st.columns(3)

with col1:
    category = st.selectbox("Market", ["Nifty 50", "Midcap", "Smallcap"])

with col2:
    orb_minutes = st.number_input("ORB Minutes", 1, 60, 15)

with col3:
    vol_mult = st.slider("Volume Multiplier", 1.0, 5.0, 1.5)

# ================================
# STOCK LIST
# ================================
@st.cache_data(ttl=86400)
def get_symbols(category):
    try:
        if category == "Nifty 50":
            url = "https://archives.nseindia.com/content/indices/ind_nifty50list.csv"
        elif category == "Midcap":
            url = "https://archives.nseindia.com/content/indices/ind_niftymidcap100list.csv"
        else:
            url = "https://archives.nseindia.com/content/indices/ind_niftysmallcap100list.csv"

        df = pd.read_csv(url)
        return [s + ".NS" for s in df["Symbol"]]
    except:
        return []

symbols = get_symbols(category)

st.write(f"📊 Stocks Loaded: {len(symbols)}")

# ================================
# SESSION STATE
# ================================
if "running" not in st.session_state:
    st.session_state.running = False

if "alerts_sent" not in st.session_state:
    st.session_state.alerts_sent = set()

if "signals" not in st.session_state:
    st.session_state.signals = []

# ================================
# START / STOP BUTTONS
# ================================
colA, colB = st.columns(2)

with colA:
    if st.button("▶ Start Scanner"):
        st.session_state.running = True

with colB:
    if st.button("⏹ Stop Scanner"):
        st.session_state.running = False

# ================================
# FETCH DATA
# ================================
def fetch(symbol):
    try:
        df = yf.download(symbol, interval="1m", period="1d", progress=False)
        df.dropna(inplace=True)
        return symbol, df
    except:
        return symbol, None

# ================================
# PROCESS LOGIC
# ================================
def process(symbol_df):
    symbol, df = symbol_df

    if df is None or len(df) < 30:
        return None

    df["Time"] = df.index.time

    cutoff = (datetime.combine(datetime.today(), time(9, 15)) +
              pd.Timedelta(minutes=orb_minutes)).time()

    orb_df = df[df["Time"] <= cutoff]

    if orb_df.empty:
        return None

    orb_high = orb_df["High"].max()
    orb_low = orb_df["Low"].min()

    last = df["Close"].iloc[-1]
    prev = df["Close"].iloc[-2]

    signal = None
    if last > orb_high:
        signal = "BUY"
    elif last < orb_low:
        signal = "SELL"

    if not signal:
        return None

    # Fake breakout filter
    if (prev > orb_high and last < orb_high) or \
       (prev < orb_low and last > orb_low):
        return None

    # Volume filter
    avg_vol = df["Volume"].rolling(20).mean().iloc[-1]
    if df["Volume"].iloc[-1] < avg_vol * vol_mult:
        return None

    return {
        "Symbol": symbol,
        "Price": round(last, 2),
        "Signal": signal,
        "Time": datetime.now().strftime("%H:%M:%S")
    }

# ================================
# MAIN SCAN
# ================================
st.subheader("📡 Live Signals")

if st.session_state.running:

    results = []
    progress = st.progress(0)

    with ThreadPoolExecutor(max_workers=10) as executor:
        data = list(executor.map(fetch, symbols))

    for i, item in enumerate(data):
        res = process(item)

        if res:
            results.append(res)

            key = f"{res['Symbol']}_{res['Signal']}"

            if key not in st.session_state.alerts_sent:
                send_telegram(f"🚨 {res['Signal']} {res['Symbol']} @ {res['Price']}")
                st.session_state.alerts_sent.add(key)

        progress.progress((i + 1) / len(data))

    st.session_state.signals = results

# ================================
# DISPLAY SIGNALS
# ================================
if st.session_state.signals:
    st.success(f"{len(st.session_state.signals)} Signals Found")
    st.dataframe(pd.DataFrame(st.session_state.signals), use_container_width=True)
else:
    st.info("No signals found")

# ================================
# TIMESTAMP
# ================================
st.write("🕒 Last Updated:", datetime.now().strftime("%H:%M:%S"))
