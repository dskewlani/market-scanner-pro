# ================================
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
# CONFIG
# ================================
st.set_page_config(page_title="ORB Scanner V8 Auto", layout="wide")

st.title("⚡ ORB Scanner V8.2 (Fully Automatic)")
st.write("Continuous ORB Scanner + Telegram Alerts")

# ================================
# TELEGRAM CONFIG
# ================================
TELEGRAM_TOKEN = "YOUR_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        requests.post(url, data=payload, timeout=5)
    except:
        pass

# ================================
# AUTO REFRESH LOOP
# ================================
st_autorefresh(interval=60 * 1000, key="auto_scan")

# ================================
# INPUTS
# ================================
category = st.selectbox(
    "Market Category",
    ["Large Cap (Nifty 50)", "Mid Cap", "Small Cap"]
)

orb_minutes = st.number_input("ORB Minutes", 1, 60, 15)
volume_multiplier = st.slider("Volume Multiplier", 1.0, 5.0, 1.5)

# ================================
# LOAD SYMBOLS
# ================================
@st.cache_data(ttl=86400)
def get_symbols(category):
    try:
        if "Large" in category:
            url = "https://archives.nseindia.com/content/indices/ind_nifty50list.csv"
        elif "Mid" in category:
            url = "https://archives.nseindia.com/content/indices/ind_niftymidcap100list.csv"
        else:
            url = "https://archives.nseindia.com/content/indices/ind_niftysmallcap100list.csv"

        df = pd.read_csv(url)
        return [s + ".NS" for s in df["Symbol"].tolist()]
    except:
        return []

symbols = get_symbols(category)
st.write(f"📊 Scanning {len(symbols)} stocks...")

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
# PROCESS STOCK
# ================================
def process_stock(symbol_df):
    symbol, df = symbol_df

    if df is None or len(df) < 30:
        return None

    df["Time"] = df.index.time

    market_open = time(9, 15)
    cutoff = (datetime.combine(datetime.today(), market_open) +
              pd.Timedelta(minutes=orb_minutes)).time()

    orb_df = df[df["Time"] <= cutoff]

    if orb_df.empty:
        return None

    orb_high = orb_df["High"].max()
    orb_low = orb_df["Low"].min()

    last_price = df["Close"].iloc[-1]
    prev_price = df["Close"].iloc[-2]

    signal = None
    if last_price > orb_high:
        signal = "BUY"
    elif last_price < orb_low:
        signal = "SELL"

    if not signal:
        return None

    # fake breakout filter
    if (prev_price > orb_high and last_price < orb_high) or \
       (prev_price < orb_low and last_price > orb_low):
        return None

    # volume filter
    avg_vol = df["Volume"].rolling(20).mean().iloc[-1]
    if df["Volume"].iloc[-1] < avg_vol * volume_multiplier:
        return None

    return {
        "Symbol": symbol,
        "Price": round(last_price, 2),
        "Signal": signal
    }

# ================================
# SESSION STATE
# ================================
if "sent_alerts" not in st.session_state:
    st.session_state.sent_alerts = set()

# ================================
# MAIN SCAN
# ================================
st.subheader("📊 Live Signals")

results = []
progress = st.progress(0)

with ThreadPoolExecutor(max_workers=10) as executor:
    data = list(executor.map(fetch, symbols))

for i, item in enumerate(data):
    res = process_stock(item)

    if res:
        results.append(res)

        key = f"{res['Symbol']}_{res['Signal']}"

        if key not in st.session_state.sent_alerts:
            msg = f"🚨 ORB {res['Signal']} Signal\n{res['Symbol']} @ {res['Price']}"
            send_telegram(msg)
            st.session_state.sent_alerts.add(key)

    progress.progress((i + 1) / len(data))

# ================================
# DISPLAY
# ================================
if results:
    df = pd.DataFrame(results)
    st.success(f"{len(results)} Signals Found")
    st.dataframe(df, use_container_width=True)
else:
    st.info("No signals found")

# ================================
# TIME
# ================================
st.write("🕒 Last Scan:", datetime.now().strftime("%H:%M:%S"))
