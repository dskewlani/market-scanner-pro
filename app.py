import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Market Breakout Scanner", layout="wide")

st.title("🔍 Live Market Breakout Scanner")
st.caption("Scanning Nifty 50 for Volume + Price Breakouts")

# 1. Define the List
WATCHLIST = [
    'ADANIPOWER.NS', 'SCODATUBES.NS', 'RELIANCE.NS', 'TCS.NS', 'INFY.NS', 
    'HDFCBANK.NS', 'ICICIBANK.NS', 'TATASTEEL.NS', 'SBIN.NS', 'BHARTIARTL.NS',
    'ITC.NS', 'ADANIENT.NS', 'JSWSTEEL.NS', 'TITAN.NS', 'SUNPHARMA.NS'
]

def check_breakout(ticker):
    try:
        # Fetching 50 days to ensure we have enough data for 20-day calculations
        df = yf.download(ticker, period="50d", interval="1d", progress=False)
        
        if df.empty or len(df) < 22: 
            return None
        
        # In newer yfinance versions, columns might be multi-index; we flatten them if necessary
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Logic: Current Price > Max of last 20 days AND Volume > 1.5x Avg
        # .iloc[-1] is today, .iloc[-21:-1] is the previous 20 sessions
        recent_high = float(df['High'].iloc[-21:-1].max())
        avg_vol = float(df['Volume'].iloc[-21:-1].mean())
        current_close = float(df['Close'].iloc[-1])
        current_vol = float(df['Volume'].iloc[-1])
        
        is_breakout = (current_close > recent_high) and (current_vol > avg_vol * 1.5)
        
        return {
            "Ticker": ticker,
            "Price": round(current_close, 2),
            "High (20D)": round(recent_high, 2),
            "Vol Ratio": round(current_vol / avg_vol, 2),
            "Status": "🔥 BREAKOUT" if is_breakout else "Normal"
        }
    except Exception as e:
        return None

# 2. Scanner Button
if st.button('🚀 Start Full Market Scan'):
    results = []
    progress_bar = st.progress(0)
    
    for index, stock in enumerate(WATCHLIST):
        res = check_breakout(stock)
        if res:
            results.append(res)
        progress_bar.progress((index + 1) / len(WATCHLIST))
    
    # Check if we actually got data
    if results:
        df_results = pd.DataFrame(results)
        
        # Filter for only the breakouts
        breakouts_only = df_results[df_results['Status'] == "🔥 BREAKOUT"]
        
        if not breakouts_only.empty:
            st.success(f"Found {len(breakouts_only)} Breakouts!")
            st.dataframe(breakouts_only, use_container_width=True)
        else:
            st.warning("No stocks currently breaking out based on 20-day high + volume.")
            
        st.write("### Full Watchlist Status")
        st.dataframe(df_results, use_container_width=True)
    else:
        st.error("Could not fetch data for any stocks. Please check your internet connection or ticker symbols.")

st.sidebar.info("Tip: Open this on your mobile Chrome and 'Add to Home Screen' for an app-like experience.")
