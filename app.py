# ================================
# IMPORTS
# ================================
import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, time as dtime
from concurrent.futures import ThreadPoolExecutor
import requests
from streamlit_autorefresh import st_autorefresh

# ================================
# PAGE CONFIG
# ================================
st.set_page_config(page_title="ORB Dashboard V11 (Stable)", layout="wide")

st.title("📊 ORB Trading Dashboard (V11 Stable)")
st.write("Live Scanner with Telegram Alerts (Free Data)")

# ================================
# AUTO REFRESH (SAFE)
# ================================
# Re-runs app every 60 seconds (safe for Streamlit)
st_autorefresh(interval=60 * 1000, key="auto_refresh")

# ================================
# TELEGRAM SETTINGS (SIDEBAR)
# ================================
st.sidebar.header("📱 Telegram Settings")
TELEGRAM_TOKEN = st.sidebar.text_input("Bot Token", type="password")
TELEGRAM_CHAT_ID = st.sidebar.text_input("Chat ID")

def send_telegram(msg: str):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=5)
        except Exception:
            pass

# ================================
# USER INPUTS
# ================================
col1, col2, col3 = st.columns(3)

with col1:
    category = st.selectbox("Market", ["Nifty 50", "Midcap", "Smallcap"])

with col2:
    orb_minutes = st.number_input("ORB Minutes", min_value=1, max_value=60, value=15)

with col3:
    vol_mult = st.slider("Volume Multiplier", min_value=1.0, max_value=5.0, value=1.5)

# ================================
# LOAD SYMBOLS
# ================================
@st.cache_data(ttl=86400)
def get_symbols(cat: str):
    try:
        if cat == "Nifty 50":
            url = "https://archives.nseindia.com/content/indices/ind_nifty50list.csv"
        elif cat == "Midcap":
            url = "https://archives.nseindia.com/content/indices/ind_niftymidcap100list.csv"
        else:
            url = "https://archives.nseindia.com/content/indices/ind_niftysmallcap100list.csv"

        df = pd.read_csv(url)
        syms = df["Symbol"].dropna().astype(str).tolist()
        return [s + ".NS" for s in syms]
    except Exception:
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
# START / STOP
# ================================
c1, c2 = st.columns(2)
with c1:
    if st.button("▶ Start Scanner"):
        st.session_state.running = True
with c2:
    if st.button("⏹ Stop Scanner"):
        st.session_state.running = False

# ================================
# DATA FETCH
# ================================
def fetch(symbol: str):
    try:
        df = yf.download(symbol, interval="1m", period="1d", progress=False)
        if df is None or df.empty:
            return symbol, None
        df = df.dropna()
        return symbol, df
    except Exception:
        return symbol, None

# ================================
# ORB PROCESS
# ================================
def process(symbol_df):
    symbol, df = symbol_df

    if df is None or len(df) < 30:
        return None

    # Ensure time column
    df = df.copy()
    df["Time"] = df.index.time

    market_open = dtime(9, 15)
    cutoff_dt = datetime.combine(datetime.today(), market_open) + pd.Timedelta(minutes=orb_minutes)
    cutoff = cutoff_dt.time()

    orb_df = df[df["Time"] <= cutoff]
    if orb_df.empty:
        return None

    orb_high = float(orb_df["High"].max())
    orb_low = float(orb_df["Low"].min())

    last = float(df["Close"].iloc[-1])
    prev = float(df["Close"].iloc[-2])

    # Breakout
    signal = None
    if last > orb_high:
        signal = "BUY"
    elif last < orb_low:
        signal = "SELL"

    if signal is None:
        return None

    # Fake breakout filter
    if (prev > orb_high and last < orb_high) or (prev < orb_low and last > orb_low):
        return None

    # Volume filter
    vol_ma = df["Volume"].rolling(20).mean().iloc[-1]
    if pd.isna(vol_ma):
        return None
    if float(df["Volume"].iloc[-1]) < float(vol_ma) * float(vol_mult):
        return None

    return {
        "Symbol": symbol,
        "Price": round(last, 2),
        "ORB High": round(orb_high, 2),
        "ORB Low": round(orb_low, 2),
        "Signal": signal,
        "Time": datetime.now().strftime("%H:%M:%S"),
    }

# ================================
# MAIN SCAN
# ================================
st.subheader("📡 Live Signals")

if st.session_state.running and symbols:
    results = []
    progress = st.progress(0)

    # Fetch in parallel
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

        progress.progress((i + 1) / max(len(data), 1))

    st.session_state.signals = results

# ================================
# DISPLAY
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
