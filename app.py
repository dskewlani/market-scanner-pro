import streamlit as st
import yfinance as yf
import pandas as pd
import concurrent.futures

st.set_page_config(page_title="Pro Breakout Scanner", layout="wide")

st.title("📈 Nifty 500 Real-Time Breakout Scanner")
st.markdown("This scanner checks the entire **Nifty 500** for stocks hitting 20-day highs with 1.5x average volume.")

# --- 1. Fetch Nifty 500 Tickers ---
@st.cache_data
def get_nifty_500_tickers():
    # URL for Nifty 500 list from NSE
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    try:
        df = pd.read_csv(url)
        # Append .NS to symbols for yfinance
        return [f"{symbol}.NS" for symbol in df['Symbol'].tolist()]
    except:
        # Fallback list if NSE link is down
        return ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS']

def check_breakout(ticker):
    try:
        # Fetching 50 days of data
        df = yf.download(ticker, period="50d", interval="1d", progress=False)
        
        if df.empty or len(df) < 22: 
            return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # 20-Day High (excluding today)
        recent_high = float(df['High'].iloc[-21:-1].max())
        avg_vol = float(df['Volume'].iloc[-21:-1].mean())
        
        current_close = float(df['Close'].iloc[-1])
        current_vol = float(df['Volume'].iloc[-1])
        
        # Calculate Volume Ratio
        vol_ratio = current_vol / avg_vol if avg_vol > 0 else 0
        
        # Breakout Condition
        is_breakout = (current_close > recent_high) and (vol_ratio > 1.5)
        
        if is_breakout:
            return {
                "Ticker": ticker.replace(".NS", ""),
                "Price": round(current_close, 2),
                "20D High": round(recent_high, 2),
                "Vol Ratio": round(vol_ratio, 2),
                "Gain %": round(((current_close - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100, 2)
            }
    except:
        return None
    return None

# --- 2. Execution Logic ---
tickers = get_nifty_500_tickers()

if st.button(f'🔍 Scan All {len(tickers)} Stocks'):
    breakouts = []
    
    with st.status("Scanning Nifty 500... this may take a minute", expanded=True) as status:
        # Use ThreadPoolExecutor to speed up yfinance calls
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ticker = {executor.submit(check_breakout, t): t for t in tickers}
            
            # Update progress
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
        
        # Sort by Volume Ratio (Highest priority first)
        df_final = df_final.sort_values(by="Vol Ratio", ascending=False)
        
        st.success(f"🔥 Found {len(df_final)} Breakout Candidates!")
        
        # Highlight high volume breakouts
        st.dataframe(
            df_final.style.background_gradient(subset=['Vol Ratio'], cmap='YlOrRd'),
            use_container_width=True
        )
    else:
        st.warning("No stocks are currently showing breakout signals.")

st.sidebar.markdown("""
### Strategy Details:
1. **Price Action**: Current Close > Max High of previous 20 sessions.
2. **Volume Confirmation**: Current Volume > 150% of 20-day average volume.
3. **Priority**: Stocks are sorted by **Volume Ratio**.
""")
