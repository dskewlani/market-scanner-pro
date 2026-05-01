# ================================
# IMPORTS
# ================================
import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, time as dtime
from concurrent.futures import ThreadPoolExecutor
import requests

# ================================
# CONFIG
# ================================
st.set_page_config(page_title="ORB V17 Scoring System", layout="wide")
st.title("🎯 ORB V17 (Signal Scoring System)")

# ================================
# SETTINGS
# ================================
col1, col2, col3 = st.columns(3)

with col1:
    category = st.selectbox("Market", ["Nifty 50", "Midcap", "Smallcap"])

with col2:
    ema_period = st.number_input("EMA", 5, 100, 20)

with col3:
    min_score = st.slider("Minimum Score to Trade", 50, 100, 70)

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
# SCORING SYSTEM
# ================================
def calculate_score(df, high, low):
    last = df["Close"].iloc[-1]
    prev = df["Close"].iloc[-2]
    ema = df["EMA"].iloc[-1]
    vwap = df["VWAP"].iloc[-1]

    score = 0

    # 1. Breakout strength
    if last > high * 1.002 or last < low * 0.998:
        score += 20

    # 2. EMA alignment
    if (last > ema) or (last < ema):
        score += 20

    # 3. VWAP alignment
    if (last > vwap) or (last < vwap):
        score += 20

    # 4. Volume spike
    avg_vol = df["Volume"].rolling(20).mean().iloc[-1]
    if df["Volume"].iloc[-1] > avg_vol * 1.5:
        score += 20

    # 5. Momentum
    if abs(last - prev) / prev > 0.002:
        score += 20

    return score

# ================================
# PROCESS
# ================================
def process(symbol_df):
    symbol, df = symbol_df

    if df is None or len(df) < 30:
        return None

    df = add_indicators(df)
    df["Time"] = df.index.time

    cutoff = (datetime.combine(datetime.today(), dtime(9, 15)) +
              pd.Timedelta(minutes=15)).time()

    orb_df = df[df["Time"] <= cutoff]

    if orb_df.empty:
        return None

    high = orb_df["High"].max()
    low = orb_df["Low"].min()

    last = df["Close"].iloc[-1]

    signal = None
    if last > high:
        signal = "BUY"
    elif last < low:
        signal = "SELL"

    if not signal:
        return None

    score = calculate_score(df, high, low)

    if score < min_score:
        return None

    strength = "🔥 Strong" if score >= 80 else "⚠ Medium"

    return {
        "Symbol": symbol,
        "Signal": signal,
        "Price": round(last, 2),
        "Score": score,
        "Strength": strength
    }

# ================================
# RUN SCANNER
# ================================
st.subheader("📡 Scored Signals")

results = []

with ThreadPoolExecutor(max_workers=10) as executor:
    data = list(executor.map(fetch, symbols))

for item in data:
    res = process(item)
    if res:
        results.append(res)

# ================================
# DISPLAY
# ================================
if results:
    df = pd.DataFrame(results).sort_values(by="Score", ascending=False)
    st.dataframe(df, use_container_width=True)
else:
    st.write("No high-quality signals")
