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
st.set_page_config(page_title="ORB V22 Mass Scanner", layout="wide")
st.title("🚀 ORB V22 (Full NSE Universe Scanner)")

# ================================
# DYNAMIC FULL UNIVERSE LOADER
# ================================
@st.cache_data
def get_all_nse_symbols(segment_choice):
    """
    Fetches the full list of symbols directly from NSE index files 
    to ensure 100% coverage of the category.
    """
    try:
        if segment_choice == "Nifty 500 (All Large/Mid/Small)":
            url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
        elif segment_choice == "Nifty 100 (Large Cap)":
            url = "https://archives.nseindia.com/content/indices/ind_nifty100list.csv"
        elif segment_choice == "Nifty Midcap 150":
            url = "https://archives.nseindia.com/content/indices/ind_niftymidcap150list.csv"
        else: # Smallcap 250
            url = "https://archives.nseindia.com/content/indices/ind_nifty_smallcap250list.csv"
        
        df = pd.read_csv(url)
        # Yahoo Finance requires .NS suffix for NSE
        return [str(s) + ".NS" for s in df['Symbol'].tolist()]
    except Exception as e:
        st.error(f"Error fetching NSE list: {e}")
        return ["RELIANCE.NS", "TCS.NS", "INFY.NS"]

# ================================
# MARKET HOURS
# ================================
def is_market_open():
    now = datetime.now().time()
    return dtime(9, 15) <= now <= dtime(15, 30)

market_open = is_market_open()
st_autorefresh(interval=60 * 1000 if market_open else 300 * 1000, key="auto_refresh")

# ================================
# SIDEBAR
# ================================
with st.sidebar:
    st.header("⚙️ Scanner Engine")
    segment = st.selectbox("Select Scanning Universe", 
                            ["Nifty 500 (All Large/Mid/Small)", 
                             "Nifty 100 (Large Cap)", 
                             "Nifty Midcap 150", 
                             "Nifty Smallcap 250"])
    
    symbols_to_scan = get_all_nse_symbols(segment)
    
    st.divider()
    orb_minutes = st.number_input("ORB Mins", 5, 60, 15)
    risk_pct = st.slider("Risk %", 0.1, 2.0, 1.0)
    
    # Critical for 500+ stocks: High thread count
    max_workers = st.slider("Scan Threads (Speed)", 20, 100, 60)
    st.warning(f"Total stocks in queue: {len(symbols_to_scan)}")

# ================================
# SESSION STATE
# ================================
if "capital" not in st.session_state: st.session_state.capital = 100000
if "active_trades" not in st.session_state: st.session_state.active_trades = {}
if "equity" not in st.session_state: st.session_state.equity = []

# ================================
# SCANNER FUNCTION
# ================================
def process_stock(symbol):
    try:
        # Fetching minimal data for speed
        df = yf.download(symbol, interval="5m", period="1d", progress=False, threads=False)
        if df is None or len(df) < 10: return None
        
        # ORB Logic
        df["Time"] = df.index.time
        cutoff = (datetime.combine(datetime.today(), dtime(9, 15)) + pd.Timedelta(minutes=orb_minutes)).time()
        orb_df = df[df["Time"] <= cutoff]
        
        if orb_df.empty: return None
        
        high, low = orb_df["High"].max(), orb_df["Low"].min()
        last = df["Close"].iloc[-1]
        
        if last > high:
            return {"symbol": symbol, "signal": "BUY", "price": round(last, 2), "sl": round(low, 2)}
        elif last < low:
            return {"symbol": symbol, "signal": "SELL", "price": round(last, 2), "sl": round(high, 2)}
            
        return None
    except:
        return None

# ================================
# MAIN UI & EXECUTION
# ================================
st.subheader(f"📊 Real-Time Engine: {segment}")
col1, col2, col3 = st.columns(3)
p_bar_text = col1.empty()
scan_metric = col2.empty()
signal_metric = col3.empty()

progress_bar = st.progress(0)
start_scan = st.button(f"🚀 Start Full {len(symbols_to_scan)} Share Scan")

if start_scan or market_open:
    found_signals = []
    scanned_count = 0
    total = len(symbols_to_scan)

    # Parallel Mass Scan
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_stock, s): s for s in symbols_to_scan}
        
        for future in as_completed(futures):
            scanned_count += 1
            res = future.result()
            if res:
                found_signals.append(res)
            
            # Update UI every 5 stocks to save browser resources
            if scanned_count % 5 == 0 or scanned_count == total:
                progress_bar.progress(scanned_count / total)
                p_bar_text.text(f"Scanning: {futures[future]}")
                scan_metric.metric("Shares Scanned", f"{scanned_count} / {total}")
                signal_metric.metric("Breakouts Found", len(found_signals))

    # Add to Active Trades
    for res in found_signals:
        sym = res["symbol"]
        if sym not in st.session_state.active_trades:
            st.session_state.active_trades[sym] = res

# ================================
# RESULTS DISPLAY
# ================================
st.divider()
if st.session_state.active_trades:
    st.subheader("✅ Live Breakout Signals")
    st.dataframe(pd.DataFrame(st.session_state.active_trades).T, use_container_width=True)
else:
    st.info("No breakout signals detected in current universe.")

st.subheader("💰 Performance Tracker")
st.session_state.equity.append({"time": datetime.now(), "capital": st.session_state.capital})
st.line_chart(pd.DataFrame(st.session_state.equity).set_index("time"))

st.write(f"Last Full Scan: {datetime.now().strftime('%H:%M:%S')}")
