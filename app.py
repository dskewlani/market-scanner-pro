import streamlit as st
import yfinance as yf
import pandas as pd
import concurrent.futures

st.set_page_config(page_title="Pro Breakout Scanner", layout="wide")

st.title("📈 Nifty 500 Real-Time Breakout Scanner")
st.markdown("Scanning **Nifty 500** for stocks hitting 20-day highs with strong volume surge.")

# --- 1. Fetch Nifty 500 Tickers ---
@st.cache_data(ttl=86400) # Cache list for 24 hours
def get_nifty_500_tickers():
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    try:
        # Use a timeout and headers to mimic a browser
        df = pd.read_csv(url)
        return [f"{symbol}.NS" for symbol in df['Symbol'].tolist()]
    except Exception as e:
        st.error(f"Could not fetch Nifty 500 list from NSE. Using Nifty 50 fallback.")
        return [
            'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'ICICIBANK.NS', 'INFY.NS', 
            'BHARTIARTL.NS', 'SBIN.NS', 'ITC.NS', 'LICI.NS', 'LT.NS'
        ]

def check_breakout(ticker):
    try:
        # Fetching 50 days of data
        df = yf.download(ticker, period="50d", interval="1d", progress=False)
        
        if df.empty or len(df) < 22: 
            return None
        
        # Flatten MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # 20-Day High (excluding current candle)
        recent_high = float(df['High'].iloc[-21:-1].max())
        avg_vol = float(df['Volume'].iloc[-21:-1].mean())
        
        current_close = float(df['Close'].iloc[-1])
        current_vol = float(df['Volume'].iloc[-1])
        prev_close = float(df['Close'].iloc[-2])
        
        vol_ratio = current_vol / avg_vol if avg_vol > 0 else 0
        gain_pct = ((current_close - prev_close) / prev_close) * 100
        
        # Breakout Condition: New High + Volume > 1.5x
        if (current_close > recent_high) and (vol_ratio > 1.5):
            return {
                "Ticker": ticker.replace(".NS", ""),
                "Price": round(current_close, 2),
                "20D High": round(recent_high, 2),
                "Vol Ratio": round(vol_ratio, 2),
                "Day Gain %": round(gain_pct, 2)
            }
    except:
        return None
    return None

# --- 2. Execution Logic ---
tickers = get_nifty_500_tickers()

if st.button(f'🔍 Scan {len(tickers)} Stocks Now'):
    breakouts = []
    
    with st.status("Fetching live market data...", expanded=True) as status:
        # ThreadPoolExecutor makes scanning 500 stocks ~10x faster
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            future_to_ticker = {executor.submit(check_breakout, t): t for t in tickers}
            
            progress_bar = st.progress(0)
            for i, future in enumerate(concurrent.futures.as_completed(future_to_ticker)):
                res = future.result()
                if res:
                    breakouts.append(res)
                progress_bar.progress((i + 1) / len(tickers))
        
        status.update(label="Scan Complete!", state="complete", expanded=False)

    # --- 3. Display Results ---
    if breakouts:
        df_final = pd.DataFrame(breakouts)
        
        # Sort by Vol Ratio (Priority)
        df_final = df_final.sort_values(by="Vol Ratio", ascending=False)
        
        st.success(f"🔥 Found {len(df_final)} Potential Breakouts!")
        
        # Using standard dataframe to avoid Matplotlib dependency errors
        st.dataframe(
            df_final, 
            use_container_width=True,
            column_config={
                "Vol Ratio": st.column_config.NumberColumn("Vol Ratio 🚀"),
                "Day Gain %": st.column_config.NumberColumn("Day Gain %", format="%.2f%%")
            }
        )
    else:
        st.warning("No breakout candidates found in the Nifty 500 currently.")

st.sidebar.info("""
**Scan Logic:**
- **Price:** Current Close > High of last 20 days.
- **Volume:** Current Volume > 1.5x of 20-day average.
- **Priority:** Sorted by Volume Ratio (Highest surge at top).
""")
