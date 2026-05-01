# ================================
# IMPORTS
# ================================
import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, time
from concurrent.futures import ThreadPoolExecutor
import base64

# ================================
# PAGE CONFIG
# ================================
st.set_page_config(page_title="ORB Scanner V8 Lite", layout="wide")

st.title("⚡ ORB Scanner V8 Lite (FREE)")
st.write("Fast ORB Scanner with Alerts + Smart Filters")

# ================================
# AUTO REFRESH (30 sec)
# ================================
st_autorefresh = st.experimental_rerun

if st.button("🔄 Auto Refresh"):
    st_autorefresh()

# ================================
# USER INPUTS
# ================================
category = st.selectbox(
    "Select Market Category",
    ["Large Cap (Nifty 50)", "Mid Cap", "Small Cap"]
)

orb_minutes = st.number_input("ORB Minutes", 1, 60, 15)
volume_multiplier = st.slider("Volume Spike Multiplier", 1.0, 5.0, 1.5)

# ================================
# STOCK UNIVERSE
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
st.write(f"📊 Stocks Loaded: {len(symbols)}")

# ================================
# FETCH DATA (FAST)
# ================================
def fetch(symbol):
    try:
        df = yf.download(symbol, interval="1m", period="1d", progress=False)
        df.dropna(inplace=True)
        return symbol, df
    except:
        return symbol, None

# ================================
# ORB LOGIC
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

    # breakout
    signal = None
    if last_price > orb_high:
        signal = "BUY"
    elif last_price < orb_low:
        signal = "SELL"

    if not signal:
        return None

    # fake breakout
    if (prev_price > orb_high and last_price < orb_high) or \
       (prev_price < orb_low and last_price > orb_low):
        return None

    # volume
    avg_vol = df["Volume"].rolling(20).mean().iloc[-1]
    if df["Volume"].iloc[-1] < avg_vol * volume_multiplier:
        return None

    return {
        "Symbol": symbol,
        "Price": round(last_price, 2),
        "ORB High": round(orb_high, 2),
        "ORB Low": round(orb_low, 2),
        "Signal": signal
    }

# ================================
# SOUND ALERT
# ================================
def play_sound():
    sound_file = open("https://www.soundjay.com/buttons/sounds/button-3.mp3", "rb").read()
    b64 = base64.b64encode(sound_file).decode()
    md = f"""
    <audio autoplay>
    <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
    </audio>
    """
    st.markdown(md, unsafe_allow_html=True)

# ================================
# SCAN BUTTON
# ================================
if st.button("🚀 Run Scanner"):
    st.write("🔍 Scanning...")

    results = []

    progress = st.progress(0)

    with ThreadPoolExecutor(max_workers=10) as executor:
        data = list(executor.map(fetch, symbols))

    for i, item in enumerate(data):
        res = process_stock(item)
        if res:
            results.append(res)

        progress.progress((i + 1) / len(data))

    # ================================
    # OUTPUT
    # ================================
    if results:
        df = pd.DataFrame(results)
        st.success(f"🔥 {len(results)} Signals Found")
        st.dataframe(df, use_container_width=True)

        play_sound()  # 🔔 alert
    else:
        st.info("No signals found")

# ================================
# FOOTER
# ================================
st.write("🕒 Time:", datetime.now().strftime("%H:%M:%S"))
