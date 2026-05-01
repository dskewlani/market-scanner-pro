# ================================
# IMPORTS
# ================================
import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, time
from streamlit_autorefresh import st_autorefresh

# ================================
# CONFIG
# ================================
st.set_page_config(page_title="ORB Scanner V6", layout="wide")

# ================================
# AUTO REFRESH (LIVE SCANNER)
# ================================
st_autorefresh(interval=60 * 1000, key="live_scan")  # 60 sec refresh

# ================================
# UI HEADER
# ================================
st.title("🔥 ORB Scanner V6 (Institutional Level)")
st.write("Live Market Scanner with True ORB + Fake Breakout Filter")

# ================================
# USER INPUTS
# ================================
symbols_input = st.text_input(
    "Enter Symbols (comma separated)",
    value="RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS"
)

orb_minutes = st.number_input("ORB Minutes", min_value=1, max_value=60, value=15)
volume_multiplier = st.slider("Volume Spike Multiplier", 1.0, 5.0, 1.5)

symbols = [s.strip() for s in symbols_input.split(",")]

# ================================
# DATA FETCH (CACHED)
# ================================
@st.cache_data(ttl=60)
def fetch_data(symbol):
    df = yf.download(
        symbol,
        interval="1m",
        period="1d",
        progress=False
    )
    df.dropna(inplace=True)
    return df

# ================================
# TRUE ORB CALCULATION
# ================================
def calculate_orb(df, orb_minutes):
    market_open = time(9, 15)

    df["Time"] = df.index.time

    orb_df = df[df["Time"] <= (datetime.combine(datetime.today(), market_open) 
                              + pd.Timedelta(minutes=orb_minutes)).time()]

    orb_high = orb_df["High"].max()
    orb_low = orb_df["Low"].min()

    return orb_high, orb_low

# ================================
# FAKE BREAKOUT FILTER
# ================================
def is_fake_breakout(df, orb_high, orb_low):
    last_close = df["Close"].iloc[-1]
    prev_close = df["Close"].iloc[-2]

    # Fake breakout condition
    if prev_close > orb_high and last_close < orb_high:
        return True

    if prev_close < orb_low and last_close > orb_low:
        return True

    return False

# ================================
# VOLUME CONFIRMATION
# ================================
def volume_spike(df, multiplier):
    avg_vol = df["Volume"].rolling(20).mean().iloc[-1]
    current_vol = df["Volume"].iloc[-1]

    return current_vol > avg_vol * multiplier

# ================================
# SCANNER LOGIC
# ================================
def scan_market():
    results = []

    for symbol in symbols:
        try:
            df = fetch_data(symbol)

            if len(df) < 30:
                continue

            orb_high, orb_low = calculate_orb(df, orb_minutes)

            last_price = df["Close"].iloc[-1]

            breakout_type = None

            if last_price > orb_high:
                breakout_type = "BUY"

            elif last_price < orb_low:
                breakout_type = "SELL"

            if breakout_type:

                # Apply Fake Breakout Filter
                if is_fake_breakout(df, orb_high, orb_low):
                    continue

                # Apply Volume Filter
                if not volume_spike(df, volume_multiplier):
                    continue

                results.append({
                    "Symbol": symbol,
                    "Price": round(last_price, 2),
                    "ORB High": round(orb_high, 2),
                    "ORB Low": round(orb_low, 2),
                    "Signal": breakout_type
                })

        except Exception as e:
            continue

    return results

# ================================
# SESSION STATE
# ================================
if "signals" not in st.session_state:
    st.session_state.signals = []

# ================================
# RUN SCANNER
# ================================
signals = scan_market()
st.session_state.signals = signals

# ================================
# DISPLAY OUTPUT
# ================================
st.subheader("📊 Live Signals")

if signals:
    df = pd.DataFrame(signals)
    st.dataframe(df, use_container_width=True)
else:
    st.write("No valid breakout signals")

# ================================
# TIMESTAMP
# ================================
st.write("🕒 Last Scan:", datetime.now().strftime("%H:%M:%S"))

# ================================
# MANUAL REFRESH BUTTON
# ================================
if st.button("🔄 Scan Now"):
    st.session_state.signals = scan_market()
    st.success("Scan Updated")
