# ================================
# IMPORTS
# ================================
import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, time as dtime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# ================================
# CONFIG
# ================================
st.set_page_config(page_title="ORB V22 Institutional", layout="wide")
st.title("🚀 ORB V22 Mega Scanner (Institutional Flow)")

# ================================
# MEGA UNIVERSE LOADER
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
# MARKET HOURS & REFRESH
# ================================
def is_market_open():
    now = datetime.now().time()
    return dtime(9, 15) <= now <= dtime(15, 30)

market_open = is_market_open()
st_autorefresh(interval=120 * 1000 if market_open else 600 * 1000, key="mega_refresh")

# ================================
# CORE SCANNER ENGINE
# ================================
def scan_stock(symbol, orb_mins):
    try:
        # Fetch 2 days of data to calculate average volume comparison
        df = yf.download(symbol, period="2d", interval="5m", progress=False, threads=False)
        if df is None or len(df) < 20: return None
        
        # Split into Yesterday and Today
        today_date = df.index.date[-1]
        df_today = df[df.index.date == today_date].copy()
        df_prev = df[df.index.date < today_date].copy()
        
        if df_today.empty: return None

        # Institutional Volume Metric (Today's Total Vol vs Prev Day Total Vol)
        vol_ratio = df_today['Volume'].sum() / (df_prev['Volume'].sum() + 1)
        
        # ORB Calculation
        df_today["Time"] = df_today.index.time
        cutoff = (datetime.combine(datetime.today(), dtime(9, 15)) + timedelta(minutes=orb_mins)).time()
        orb_range = df_today[df_today["Time"] <= cutoff]
        
        if orb_range.empty: return None
        
        high, low = orb_range["High"].max(), orb_range["Low"].min()
        last = df_today["Close"].iloc[-1]
        
        # Signal Result
        res = {
            "Symbol": symbol,
            "Price": round(last, 2),
            "Vol_Shock": round(vol_ratio, 2),
            "Signal": "Neutral",
            "Level": 0.0
        }

        if last > high:
            res.update({"Signal": "BUY", "Level": round(high, 2)})
        elif last < low:
            res.update({"Signal": "SELL", "Level": round(low, 2)})
            
        return res
    except:
        return None

# ================================
# SIDEBAR & INPUTS
# ================================
all_symbols = get_mega_universe()

with st.sidebar:
    st.header("⚡ Institutional Controls")
    orb_minutes = st.number_input("ORB Timeframe", 5, 60, 15)
    min_vol_ratio = st.slider("Min Vol Shock (vs Prev Day)", 0.5, 5.0, 1.5)
    max_threads = st.slider("Threads", 20, 150, 100)
    
    st.divider()
    st.subheader("📊 Top 100 Volume Gainers")
    vol_placeholder = st.empty()

# ================================
# EXECUTION LOGIC
# ================================
m1, m2, m3 = st.columns(3)
p_bar_text = m1.empty()
scan_metric = m2.empty()
signal_metric = m3.empty()
progress_bar = st.progress(0)

start_button = st.button(f"🔥 Run Deep Scan ({len(all_symbols)} Stocks)")

if start_button or market_open:
    all_results = []
    scanned_count = 0
    total = len(all_symbols)

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = {executor.submit(scan_stock, s, orb_minutes): s for s in all_symbols}
        
        for future in as_completed(futures):
            scanned_count += 1
            res = future.result()
            if res:
                all_results.append(res)
            
            if scanned_count % 25 == 0 or scanned_count == total:
                progress_bar.progress(scanned_count / total)
                p_bar_text.text(f"Processing: {futures[future]}")
                scan_metric.metric("Total Scanned", f"{scanned_count}/{total}")
                
    if all_results:
        full_df = pd.DataFrame(all_results)
        
        # 1. Update Sidebar with Volume Gainers
        top_vol = full_df.sort_values(by="Vol_Shock", ascending=False).head(100)
        vol_placeholder.dataframe(top_vol[["Symbol", "Vol_Shock"]], height=400)
        
        # 2. Filter for ORB Qualified Signals (Breakout + High Vol)
        qualified = full_df[
            (full_df["Signal"] != "Neutral") & 
            (full_df["Vol_Shock"] >= min_vol_ratio)
        ]
        
        signal_metric.metric("High-Conviction Signals", len(qualified))
        
        st.divider()
        st.subheader("🎯 Qualified Breakouts (Institutional Footprint Found)")
        if not qualified.empty:
            st.dataframe(qualified.sort_values(by="Vol_Shock", ascending=False), use_container_width=True)
        else:
            st.info("Scanning complete. No stocks met both ORB and Volume Shock criteria yet.")
            
        # 3. Analytics Chart
        st.subheader("📈 Volatility vs Volume Shock")
        fig = go.Figure(data=go.Scatter(
            x=full_df["Vol_Shock"], 
            y=full_df["Price"], 
            mode='markers',
            marker=dict(size=8, color=full_df["Vol_Shock"], colorscale='Viridis', showscale=True),
            text=full_df["Symbol"]
        ))
        fig.update_layout(xaxis_title="Volume Shock Ratio", yaxis_title="Price")
        st.plotly_chart(fig, use_container_width=True)

st.caption(f"Last Heartbeat: {datetime.now().strftime('%H:%M:%S')} | Total Universe: {len(all_symbols)}")
