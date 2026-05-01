import streamlit as st
import pandas as pd
import yfinance as yf
import time
from datetime import datetime, time as dtime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# ================================
# CONFIG
# ================================
st.set_page_config(page_title="ORB V22 Ultimate", layout="wide")
st.title("🚀 ORB V22 Ultimate (Nifty-Context + RS/RW)")

# --- UNIVERSE LOADER ---
@st.cache_data
def get_mega_universe():
    urls = [
        "https://archives.nseindia.com/content/indices/ind_nifty500list.csv",
        "https://archives.nseindia.com/content/indices/ind_niftymicrocap250_list.csv",
        "https://archives.nseindia.com/content/indices/ind_niftysmallcap250list.csv"
    ]
    all_syms = {"^NSEI"} # Start with Nifty 50 Index for context
    for url in urls:
        try:
            df = pd.read_csv(url)
            col = [c for c in df.columns if 'Symbol' in c][0]
            for s in df[col].dropna(): all_syms.add(str(s) + ".NS")
        except: continue
    return sorted(list(all_syms))

# --- SINGLE STOCK ANALYSIS ENGINE ---
def analyze_stock_ultimate(symbol, orb_mins, nifty_change):
    try:
        df = yf.download(symbol, period="1d", interval="5m", progress=False, threads=False, timeout=10)
        if df is None or len(df) < 10: return None
        
        # 1. Opening Range Calculation
        cutoff = (datetime.combine(datetime.today(), dtime(9, 15)) + timedelta(minutes=orb_mins)).time()
        orb_df = df[df.index.time <= cutoff]
        if orb_df.empty: return None
        
        high, low = orb_df["High"].max(), orb_df["Low"].min()
        last = df["Close"].iloc[-1]
        
        # 2. RS/RW Calculation (Relative Strength vs Nifty)
        stock_change = ((last - df["Open"].iloc[0]) / df["Open"].iloc[0]) * 100
        relative_strength = stock_change - nifty_change
        
        # 3. Volume Intensity
        vol_avg = df["Volume"].rolling(10).mean().iloc[-1]
        vol_ratio = df["Volume"].iloc[-1] / (vol_avg + 1)
        
        signal = "Neutral"
        if last > high: signal = "BUY"
        elif last < low: signal = "SELL"
            
        return {
            "Symbol": symbol,
            "Price": round(last, 2),
            "Signal": signal,
            "RS/RW": round(relative_strength, 2),
            "Vol_Intensity": round(vol_ratio, 2),
            "Stock_Chg_%": round(stock_change, 2)
        }
    except:
        return None

# --- UI CONTROLS ---
all_stocks = get_mega_universe()
with st.sidebar:
    st.header("🛡️ Risk & Context")
    orb_val = st.number_input("ORB Mins", 5, 60, 15)
    min_rs = st.slider("Min Relative Strength (RS)", 0.0, 3.0, 0.5)
    batch_size = st.slider("Batch Size", 20, 100, 50)
    workers = st.slider("Threads", 10, 50, 25)

# --- SCANNER EXECUTION ---
if st.button(f"🔥 Deep Scan {len(all_stocks)} Stocks"):
    # First, get Nifty Context
    nifty_data = yf.download("^NSEI", period="1d", interval="5m", progress=False)
    nifty_change = ((nifty_data["Close"].iloc[-1] - nifty_data["Open"].iloc[0]) / nifty_data["Open"].iloc[0]) * 100
    st.info(f"Market Context: Nifty 50 is trading at {round(nifty_change, 2)}%")

    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i in range(0, len(all_stocks), batch_size):
        batch = all_stocks[i : i + batch_size]
        status_text.text(f"Analyzing {i} to {i+batch_size}...")
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_stock = {executor.submit(analyze_stock_ultimate, s, orb_val, nifty_change): s for s in batch}
            for future in as_completed(future_to_stock):
                res = future.result()
                if res and res['Symbol'] != "^NSEI": results.append(res)
        
        progress_bar.progress(min((i + batch_size) / len(all_stocks), 1.0))
        time.sleep(1.0) # Stability pause

    if results:
        full_df = pd.DataFrame(results)
        
        # FILTER: Only show signals that are stronger than the market (RS/RW)
        high_conviction = full_df[
            (full_df["Signal"] != "Neutral") & 
            (full_df["RS/RW"].abs() >= min_rs)
        ].sort_values("RS/RW", ascending=False)

        st.subheader("🎯 High Conviction Alpha Signals")
        st.write("Criteria: ORB Breakout + Outperforming Nifty 50")
        st.dataframe(high_conviction, use_container_width=True)
        
        # Sidebar Stats
        with st.sidebar:
            st.divider()
            st.write("📈 Scan Summary")
            st.write(f"Total Signals: {len(full_df[full_df['Signal'] != 'Neutral'])}")
            st.write(f"High RS Signals: {len(high_conviction)}")
