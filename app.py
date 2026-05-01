import streamlit as st
import pandas as pd
import yfinance as yf
import time
from datetime import datetime, time as dtime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(page_title="ORB V22 Mega-Stable", layout="wide")
st.title("🚀 ORB V22 (Stable 2500+ Scanner)")

# --- UNIVERSE LOADER ---
@st.cache_data
def get_mega_universe():
    urls = [
        "https://archives.nseindia.com/content/indices/ind_nifty500list.csv",
        "https://archives.nseindia.com/content/indices/ind_niftymicrocap250_list.csv",
        "https://archives.nseindia.com/content/indices/ind_nifty_smallcap250list.csv"
    ]
    all_syms = set()
    for url in urls:
        try:
            df = pd.read_csv(url)
            col = [c for c in df.columns if 'Symbol' in c][0]
            for s in df[col].dropna(): all_syms.add(str(s) + ".NS")
        except: continue
    return sorted(list(all_syms))

# --- SINGLE STOCK LOGIC ---
def fetch_and_analyze(symbol, orb_mins):
    try:
        # Requesting ONLY 2 days to minimize data payload
        df = yf.download(symbol, period="2d", interval="5m", progress=False, threads=False, timeout=10)
        if df is None or len(df) < 10: return None
        
        today = df.index.date[-1]
        df_today = df[df.index.date == today].copy()
        
        cutoff = (datetime.combine(datetime.today(), dtime(9, 15)) + timedelta(minutes=orb_mins)).time()
        orb_df = df_today[df_today.index.time <= cutoff]
        
        if orb_df.empty: return None
        
        high, low = orb_df["High"].max(), orb_df["Low"].min()
        last = df_today["Close"].iloc[-1]
        vol_ratio = df_today["Volume"].sum() / (df[df.index.date < today]["Volume"].sum() + 1)
        
        signal = "Neutral"
        if last > high: signal = "BUY"
        elif last < low: signal = "SELL"
            
        return {"Symbol": symbol, "Price": round(last, 2), "Signal": signal, "Vol_Shock": round(vol_ratio, 2)}
    except:
        return None

# --- UI CONTROLS ---
all_stocks = get_mega_universe()
with st.sidebar:
    st.info(f"Universe: {len(all_stocks)} Stocks")
    orb_val = st.number_input("ORB Mins", 5, 60, 15)
    batch_size = st.slider("Batch Size", 20, 100, 50) # Small batches prevent IP blocking
    workers = st.slider("Threads", 10, 50, 20) # Lower threads = higher success rate

# --- EXECUTION ---
if st.button(f"Scan All {len(all_stocks)} Shares"):
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Process in Batches
    for i in range(0, len(all_stocks), batch_size):
        batch = all_stocks[i : i + batch_size]
        status_text.text(f"Scanning Batch {i//batch_size + 1}...")
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_stock = {executor.submit(fetch_and_analyze, s, orb_val): s for s in batch}
            for future in as_completed(future_to_stock):
                res = future.result()
                if res: results.append(res)
        
        # Update Progress
        prog = min((i + batch_size) / len(all_stocks), 1.0)
        progress_bar.progress(prog)
        
        # SMALL COOL DOWN to avoid Yahoo Ban
        time.sleep(1.5) 

    if results:
        res_df = pd.DataFrame(results)
        st.success(f"Scan Complete! Found {len(res_df[res_df['Signal'] != 'Neutral'])} signals.")
        st.dataframe(res_df[res_df["Signal"] != "Neutral"].sort_values("Vol_Shock", ascending=False))
    else:
        st.warning("No data returned. Yahoo Finance might be blocking requests. Try a smaller batch size.")
