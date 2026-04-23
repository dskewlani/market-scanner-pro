import streamlit as st
import yfinance as yf
import pandas as pd
import concurrent.futures
from datetime import datetime

# --- Configuration ---
st.set_page_config(page_title="Breakout Trader Pro", layout="wide")

# 1. Initialize Portfolio in Session State
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = []

# --- Helper Functions ---

@st.cache_data(ttl=86400)
def get_nifty_500_tickers():
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    try:
        df = pd.read_csv(url)
        return [f"{symbol}.NS" for symbol in df['Symbol'].tolist()]
    except:
        return ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'SBIN.NS', 'INFY.NS']

def add_to_portfolio(ticker, buy_price, breakout_level):
    """Callback function to ensure immediate state update"""
    entry = {
        'Ticker': ticker,
        'Buy Price': buy_price,
        'Target': round(breakout_level * 1.10, 2),
        'Stop Loss': round(buy_price * 0.95, 2),
        'Days to Target': 15,
        'Entry Date': datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    st.session_state.portfolio.append(entry)
    st.toast(f"✅ {ticker} moved to Portfolio!")

def check_near_breakout(ticker):
    try:
        df = yf.download(ticker, period="50d", interval="1d", progress=False)
        if df.empty or len(df) < 22: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        breakout_price = float(df['High'].iloc[-21:-1].max())
        cmp = float(df['Close'].iloc[-1])
        avg_vol = float(df['Volume'].iloc[-21:-1].mean())
        current_vol = float(df['Volume'].iloc[-1])
        vol_ratio = current_vol / avg_vol if avg_vol > 0 else 0
        distance = ((breakout_price - cmp) / breakout_price) * 100
        
        if 0 <= distance <= 2.5:
            return {
                "Ticker": ticker.replace(".NS", ""),
                "CMP": round(cmp, 2),
                "Breakout Price": round(breakout_price, 2),
                "Distance %": round(distance, 2),
                "Vol Ratio": round(vol_ratio, 2)
            }
    except: return None

# --- UI LAYOUT ---
st.title("🎯 Breakout Scanner & Portfolio Manager")

tab1, tab2 = st.tabs(["🔍 Live Scanner", "💼 My Portfolio"])

# --- TAB 1: SCANNER ---
with tab1:
    tickers = get_nifty_500_tickers()
    
    if st.button(f'🔭 Start New Scan ({len(tickers)} Stocks)'):
        results = []
        with st.status("Scanning Nifty 500...", expanded=True) as status:
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                future_to_ticker = {executor.submit(check_near_breakout, t): t for t in tickers}
                progress_bar = st.progress(0)
                for i, future in enumerate(concurrent.futures.as_completed(future_to_ticker)):
                    res = future.result()
                    if res: results.append(res)
                    progress_bar.progress((i + 1) / len(tickers))
            status.update(label="Scan Complete!", state="complete", expanded=False)
        st.session_state.last_results = results

    # Display results from the last scan
    if 'last_results' in st.session_state and st.session_state.last_results:
        st.write("### 📈 Stocks Near Breakout")
        
        # Header Row
        h1, h2, h3, h4, h5, h6 = st.columns([2, 2, 2, 2, 2, 2])
        h1.write("**Ticker**")
        h2.write("**CMP**")
        h3.write("**Breakout Level**")
        h4.write("**Distance %**")
        h5.write("**Vol Ratio**")
        h6.write("**Action**")
        st.divider()

        for res in st.session_state.last_results:
            c1, c2, c3, c4, c5, c6 = st.columns([2, 2, 2, 2, 2, 2])
            c1.write(f"**{res['Ticker']}**")
            c2.write(f"₹{res['CMP']}")
            c3.write(f"₹{res['Breakout Price']}")
            c4.write(f"{res['Distance %']}%")
            c5.write(f"{res['Vol Ratio']}x")
            
            # Key fix: Pass arguments to the function via lambda or button logic
            if c6.button("Buy 🛒", key=f"btn_{res['Ticker']}"):
                add_to_portfolio(res['Ticker'], res['CMP'], res['Breakout Price'])
    else:
        st.info("Click the button above to scan the market.")

# --- TAB 2: PORTFOLIO ---
with tab2:
    st.header("Active Portfolio Holdings")
    
    if not st.session_state.portfolio:
        st.warning("Your portfolio is currently empty. Buy stocks from the Scanner tab.")
    else:
        if st.button("🗑️ Clear All Holdings"):
            st.session_state.portfolio = []
            st.rerun()

        # Iterate through portfolio and get live updates
        for item in st.session_state.portfolio:
            try:
                # Fetch fresh CMP for live P&L tracking
                ticker_obj = yf.Ticker(f"{item['Ticker']}.NS")
                # Using fast_info for speed
                live_cmp = round(ticker_obj.fast_info['last_price'], 2)
            except:
                live_cmp = item['Buy Price']

            pnl_val = round(live_cmp - item['Buy Price'], 2)
            pnl_pct = round((pnl_val / item['Buy Price']) * 100, 2)
            
            # Logic: If Live CMP > Buy Price -> Green, else Red
            theme_color = "green" if live_cmp >= item['Buy Price'] else "red"

            with st.container():
                p1, p2, p3, p4, p5, p6 = st.columns([2, 2, 2, 2, 2, 2])
                
                # Column 1: Ticker with Color
                p1.markdown(f"### :{theme_color}[{item['Ticker']}]")
                p1.caption(f"Added: {item['Entry Date']}")
                
                # Column 2: Price Performance
                p2.metric("Live CMP", f"₹{live_cmp}", f"{pnl_pct}%")
                
                # Column 3 & 4: Entry & Exit Levels
                p3.write(f"**Buy Price:**\n₹{item['Buy Price']}")
                p4.write(f"**Target:**\n₹{item['Target']}")
                
                # Column 5: Risk Management
                p5.write(f"**Stop Loss:**\n₹{item['Stop Loss']}")
                
                # Column 6: Status
                status_text = "✅ IN PROFIT" if theme_color == "green" else "🔻 IN LOSS"
                p6.write(f"**Status:**\n{status_text}")
                
                st.divider()

st.sidebar.markdown("""
### How to use:
1. Run a **Scan** in Tab 1.
2. Click **Buy 🛒** on any stock you like.
3. Switch to **My Portfolio** to see live tracking.
---
**Note:** Data is saved in the current session. Refreshing the browser page will reset the portfolio.
""")
