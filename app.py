import streamlit as st
import yfinance as yf
import pandas as pd
import concurrent.futures

st.set_page_config(page_title="Near Breakout Scanner", layout="wide")

st.title("🎯 Nifty 500: Near-Breakout & Target Scanner")
st.markdown("""
This scanner identifies stocks trading **within 2% of their 20-day high** with high volume support. 
It calculates potential targets based on the breakout level.
""")

# --- 1. Fetch Nifty 500 Tickers ---
@st.cache_data(ttl=86400)
def get_nifty_500_tickers():
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    try:
        df = pd.read_csv(url)
        return [f"{symbol}.NS" for symbol in df['Symbol'].tolist()]
    except Exception:
        # Fallback to a smaller list if NSE is unreachable
        return ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'ICICIBANK.NS', 'INFY.NS']

def check_near_breakout(ticker):
    try:
        # Fetching 50 days of data
        df = yf.download(ticker, period="50d", interval="1d", progress=False)
        
        if df.empty or len(df) < 22: 
            return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # 1. Breakout Price (Resistance) = Max of previous 20 days
        breakout_price = float(df['High'].iloc[-21:-1].max())
        
        # 2. Current Market Price (CMP)
        cmp = float(df['Close'].iloc[-1])
        
        # 3. Volume Logic
        avg_vol = float(df['Volume'].iloc[-21:-1].mean())
        current_vol = float(df['Volume'].iloc[-1])
        vol_ratio = current_vol / avg_vol if avg_vol > 0 else 0
        
        # 4. Proximity Logic (Is CMP within 2% of Breakout Price?)
        # And CMP must still be BELOW or exactly at the breakout price
        distance_to_breakout = ((breakout_price - cmp) / breakout_price) * 100
        
        # We define "Near Breakout" as between 0% and 2% distance
        if 0 <= distance_to_breakout <= 2.0:
            
            # 5. Calculate Target (Example: Breakout Price + 5% for T1, 10% for T2)
            target_1 = breakout_price * 1.05
            target_2 = breakout_price * 1.10
            
            return {
                "Ticker": ticker.replace(".NS", ""),
                "CMP": round(cmp, 2),
                "Breakout Price": round(breakout_price, 2),
                "Distance (%)": round(distance_to_breakout, 2),
                "Vol Ratio": round(vol_ratio, 2),
                "Target 1 (5%)": round(target_1, 2),
                "Target 2 (10%)": round(target_2, 2)
            }
    except:
        return None
    return None

# --- 2. Execution Logic ---
tickers = get_nifty_500_tickers()

if st.button(f'🔭 Scan {len(tickers)} Stocks for Setup'):
    results = []
    
    with st.status("Scanning for setups...", expanded=True) as status:
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            future_to_ticker = {executor.submit(check_near_breakout, t): t for t in tickers}
            
            progress_bar = st.progress(0)
            for i, future in enumerate(concurrent.futures.as_completed(future_to_ticker)):
                res = future.result()
                if res:
                    results.append(res)
                progress_bar.progress((i + 1) / len(tickers))
        
        status.update(label="Scan Complete!", state="complete", expanded=False)

    # --- 3. Display Results ---
    if results:
        df_final = pd.DataFrame(results)
        
        # Priority: Show stocks closest to breakout (lowest distance) with highest volume
        df_final = df_final.sort_values(by=["Distance (%)", "Vol Ratio"], ascending=[True, False])
        
        st.success(f"📈 Found {len(df_final)} stocks near a breakout level!")
        
        # Display with formatting
        st.dataframe(
            df_final, 
            use_container_width=True,
            column_config={
                "CMP": st.column_config.NumberColumn("Current Price", format="₹%.2f"),
                "Breakout Price": st.column_config.NumberColumn("Breakout Level", format="₹%.2f"),
                "Distance (%)": st.column_config.NumberColumn("Distance to BO", format="%.2f%%"),
                "Target 1 (5%)": st.column_config.NumberColumn("Target 1", format="₹%.2f"),
                "Target 2 (10%)": st.column_config.NumberColumn("Target 2", format="₹%.2f"),
            }
        )
    else:
        st.warning("No stocks found within 2% of their 20-day high right now.")

st.sidebar.markdown("""
### Scanner Strategy:
- **Near Breakout**: CMP is within **0% to 2%** of the 20-day High.
- **Breakout Price**: The highest price hit in the last 20 trading sessions.
- **Targets**:
    - **T1**: 5% above Breakout Price.
    - **T2**: 10% above Breakout Price.
- **Tip**: High **Vol Ratio** (> 1.0) increases the chance of a successful breakout.
""")
