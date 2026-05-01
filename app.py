# ================================
# IMPORTS
# ================================
import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, time as dtime
from concurrent.futures import ThreadPoolExecutor, as_completed
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# ================================
# CONFIG
# ================================
st.set_page_config(page_title="ORB V22 Mega Scanner", layout="wide")
st.title("🚀 ORB V22 (Total Market 2500+ Scanner)")

# ================================
# HIGH-VOLUME SYMBOL LOADER
# ================================
@st.cache_data
def get_mega_universe():
    """
    Combines major NSE indices to reach the ~2000-2500 stock mark.
    """
    urls = [
        "https://archives.nseindia.com/content/indices/ind_nifty500list.csv",
        "https://archives.nseindia.com/content/indices/ind_niftymicrocap250_list.csv",
        "https://archives.nseindia.com/content/indices/ind_niftysmallcap250list.csv"
    ]
    
    all_symbols = set()
    for url in urls:
        try:
            df = pd.read_csv(url)
            # Standardize column naming as different NSE files use different headers
            sym_col = [c for c in df.columns if 'Symbol' in c][0]
            for s in df[sym_col].astype(str).tolist():
                all_symbols.add(s + ".NS")
        except:
            continue
            
    # Fallback if NSE site is down
    if not all_symbols:
        return ["RELIANCE.NS", "TCS.NS", "SBIN.NS"]
        
    return sorted(list(all_symbols))

# ================================
# MARKET HOURS
# ================================
def is_market_open():
    now = datetime.now().time()
    return dtime(9, 15) <= now <= dtime(15, 30)

market_open = is_market_open()
# Longer refresh for mega-scans to prevent IP blocking (2 min)
st_autorefresh(interval=120 * 1000 if market_open else 600 * 1000, key="mega_refresh")

# ================================
# SIDEBAR
# ================================
with st.sidebar:
    st.header("⚙️ Mega-Engine Config")
    all_symbols = get_mega_universe()
    st.success(f"Universe Loaded: {len(all_symbols)} Stocks")
    
    st.divider()
    orb_minutes = st.number_input("ORB Mins", 5, 60, 15)
    
    # Advanced Threading for 2500+ stocks
    st.subheader("🚀 Speed Settings")
    max_workers = st.slider("Parallel Threads", 20, 150, 80)
    st.info("Higher threads = Faster scan, but requires better internet.")

# ================================
# CORE ANALYSIS
# ================================
def scan_stock(symbol):
    try:
        # download only essential data (period='1d')
        df = yf.download(symbol, period="1d", interval="5m", progress=False, threads=False)
        if df is None or len(df) < 5: return None
        
        # Indicator Math
        df["Vol_Avg"] = df["Volume"].rolling(10).mean()
        
        # ORB Levels
        df["Time"] = df.index.time
        cutoff = (datetime.combine(datetime.today(), dtime(9, 15)) + pd.Timedelta(minutes=orb_minutes)).time()
        orb_df = df[df["Time"] <= cutoff]
        
        if orb_df.empty: return None
        
        high, low = orb_df["High"].max(), orb_df["Low"].min()
        last = df["Close"].iloc[-1]
        vol_now = df["Volume"].iloc[-1]
        
        # Signal Logic
        if last > high and vol_now > df["Vol_Avg"].iloc[-1]:
            return {"Symbol": symbol, "Signal": "BUY", "Price": round(last, 2), "Level": round(high, 2)}
        elif last < low and vol_now > df["Vol_Avg"].iloc[-1]:
            return {"Symbol": symbol, "Signal": "SELL", "Price": round(last, 2), "Level": round(low, 2)}
            
        return None
    except:
        return None

# ================================
# MAIN DASHBOARD
# ================================
m1, m2, m3 = st.columns(3)
p_bar_text = m1.empty()
scan_metric = m2.empty()
signal_metric = m3.empty()

progress_bar = st.progress(0)
start_button = st.button(f"🔥 Start Mega-Scan ({len(all_symbols)} Shares)")

if "signals" not in st.session_state: st.session_state.signals = []

if start_button or market_open:
    current_cycle_signals = []
    scanned_count = 0
    total = len(all_symbols)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(scan_stock, s): s for s in all_symbols}
        
        for future in as_completed(future_map):
            scanned_count += 1
            res = future.result()
            if res:
                current_cycle_signals.append(res)
            
            # Optimized UI updates (every 20 stocks for speed)
            if scanned_count % 20 == 0 or scanned_count == total:
                progress_bar.progress(scanned_count / total)
                p_bar_text.text(f"Scanning: {future_map[future]}")
                scan_metric.metric("Total Scanned", f"{scanned_count} / {total}")
                signal_metric.metric("Breakouts", len(current_cycle_signals))
    
    st.session_state.signals = current_cycle_signals

# ================================
# DISPLAY RESULTS
# ================================
st.divider()
if st.session_state.signals:
    st.subheader(f"✅ Active Signals ({len(st.session_state.signals)})")
    res_df = pd.DataFrame(st.session_state.signals)
    st.dataframe(res_df, use_container_width=True)
else:
    st.info("No active breakouts found in the current market universe.")

st.caption(f"Engine Heartbeat: {datetime.now().strftime('%H:%M:%S')} | Environment: Multi-Threaded NSE-Total")
