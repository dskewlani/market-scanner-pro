import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, time as dtime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from streamlit_autorefresh import st_autorefresh

# ================================
# CONFIG & REFRESH
# ================================
st.set_page_config(page_title="ORB V22 Pro", layout="wide")
st.title("🚀 ORB V22 Mega-Scanner (Pro Edition)")

if "capital" not in st.session_state: st.session_state.capital = 100000

# Auto-refresh every 2 minutes during market hours
st_autorefresh(interval=120 * 1000, key="pro_refresh")

# ================================
# DATA FETCHING (2500+ STOCKS)
# ================================
@st.cache_data
def get_mega_universe():
    urls = [
        "https://archives.nseindia.com/content/indices/ind_nifty500list.csv",
        "https://archives.nseindia.com/content/indices/ind_niftymicrocap250_list.csv",
        "https://archives.nseindia.com/content/indices/ind_nifty_smallcap250list.csv",
        "https://archives.nseindia.com/content/indices/ind_niftymidcap150list.csv"
    ]
    all_symbols = set()
    for url in urls:
        try:
            df = pd.read_csv(url)
            sym_col = [c for c in df.columns if 'Symbol' in c][0]
            for s in df[sym_col].astype(str).tolist():
                if s != 'Symbol': all_symbols.add(s + ".NS")
        except: continue
    return sorted(list(all_symbols))

# ================================
# ANALYSIS ENGINE
# ================================
def scan_stock_pro(symbol, orb_mins):
    try:
        # Pull 3 days of data for Yesterday's High and Volume Average
        df = yf.download(symbol, period="3d", interval="5m", progress=False, threads=False)
        if df is None or len(df) < 20: return None
        
        today_date = df.index.date[-1]
        df_today = df[df.index.date == today_date].copy()
        df_prev = df[df.index.date < today_date].copy()
        
        if df_today.empty or df_prev.empty: return None

        # 1. Multi-Timeframe Filter (Prev Day High)
        prev_day_high = df_prev['High'].max()
        
        # 2. Volume Shock (Today's Total vs Yesterday's Total)
        vol_shock = df_today['Volume'].sum() / (df_prev[df_prev.index.date == df_prev.index.date[-1]]['Volume'].sum() + 1)
        
        # 3. EMA Distance (Overextension Check)
        ema_20 = df_today['Close'].ewm(span=20).mean().iloc[-1]
        last_price = df_today['Close'].iloc[-1]
        ema_dist = ((last_price - ema_20) / ema_20) * 100
        
        # 4. ORB Calculation
        df_today["Time"] = df_today.index.time
        cutoff = (datetime.combine(datetime.today(), dtime(9, 15)) + timedelta(minutes=orb_mins)).time()
        orb_range = df_today[df_today["Time"] <= cutoff]
        
        if orb_range.empty: return None
        high_level, low_level = orb_range["High"].max(), orb_range["Low"].min()
        
        res = {
            "Symbol": symbol,
            "Price": round(last_price, 2),
            "Vol_Shock": round(vol_shock, 2),
            "EMA_Dist_%": round(ema_dist, 2),
            "Above_Prev_High": "Yes" if last_price > prev_day_high else "No",
            "Signal": "Neutral"
        }

        if last_price > high_level: res["Signal"] = "BUY"
        elif last_price < low_level: res["Signal"] = "SELL"
            
        return res
    except:
        return None

# ================================
# UI LAYOUT
# ================================
all_symbols = get_mega_universe()

with st.sidebar:
    st.header("⚙️ Pro Filters")
    orb_mins = st.number_input("ORB Minutes", 5, 60, 15)
    min_vol = st.slider("Min Vol Shock", 0.5, 5.0, 1.5)
    max_ema_dist = st.slider("Max EMA Distance %", 1.0, 5.0, 2.5)
    threads = st.slider("Threads", 20, 150, 100)
    
    st.divider()
    st.subheader("📊 Top 100 Volume Shockers")
    sidebar_vol = st.empty()

# ================================
# EXECUTION
# ================================
col1, col2, col3 = st.columns(3)
p_bar = st.progress(0)
status = col1.empty()
m_scan = col2.empty()
m_sig = col3.empty()

if st.button(f"🔥 Deep Scan {len(all_symbols)} Stocks"):
    results = []
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {executor.submit(scan_stock_pro, s, orb_mins): s for s in all_symbols}
        for i, future in enumerate(as_completed(futures)):
            res = future.result()
            if res: results.append(res)
            if i % 25 == 0:
                p_bar.progress((i+1)/len(all_symbols))
                m_scan.metric("Scanned", f"{i+1}/{len(all_symbols)}")

    if results:
        full_df = pd.DataFrame(results)
        
        # Sidebar Update
        top_100 = full_df.sort_values("Vol_Shock", ascending=False).head(100)
        sidebar_vol.dataframe(top_100[["Symbol", "Vol_Shock"]], height=400)
        
        # High Conviction Filter
        qualified = full_df[
            (full_df["Signal"] != "Neutral") & 
            (full_df["Vol_Shock"] >= min_vol) &
            (full_df["EMA_Dist_%"].abs() <= max_ema_dist)
        ]
        
        m_sig.metric("High Conviction", len(qualified))
        
        st.subheader("🎯 High Conviction Signals")
        st.write("Criteria: ORB Breakout + Vol Shock + Within EMA Range")
        st.dataframe(qualified.sort_values("Vol_Shock", ascending=False), use_container_width=True)

st.write(f"Last Scan: {datetime.now().strftime('%H:%M:%S')}")
