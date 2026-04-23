import streamlit as st
import yfinance as yf
import pandas as pd
import concurrent.futures
from datetime import datetime, timedelta

# --- Configuration ---
st.set_page_config(page_title="Breakout Trader Pro", layout="wide")

# Initialize Portfolio in Session State if it doesn't exist
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=[
        'Ticker', 'Buy Price', 'Target', 'Stop Loss', 'Days to Target', 'Entry Date'
    ])

# --- Functions ---
@st.cache_data(ttl=86400)
def get_nifty_500_tickers():
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    try:
        df = pd.read_csv(url)
        return [f"{symbol}.NS" for symbol in df['Symbol'].tolist()]
    except:
        return ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS']

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

def add_to_portfolio(ticker, buy_price, breakout_level):
    new_entry = pd.DataFrame([{
        'Ticker': ticker,
        'Buy Price': buy_price,
        'Target': round(breakout_level * 1.10, 2), # 10% Target
        'Stop Loss': round(buy_price * 0.95, 2),    # 5% Stop Loss
        'Days to Target': 15,                      # Estimated 15 days
        'Entry Date': datetime.now().strftime("%Y-%m-%d")
    }])
    st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_entry], ignore_index=True)
    st.toast(f"✅ Added {ticker} to Portfolio!")

# --- UI LAYOUT ---
st.title("🎯 Breakout Scanner & Portfolio Manager")

tab1, tab2 = st.tabs(["🔍 Live Scanner", "💼 My Portfolio"])

with tab1:
    tickers = get_nifty_500_tickers()
    if st.button(f'🔭 Scan {len(tickers)} Stocks'):
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

        if results:
            df_results = pd.DataFrame(results)
            st.write("### Stocks Near Breakout Level")
            
            # Display results with a "Buy" interaction
            for index, row in df_results.iterrows():
                cols = st.columns([2, 2, 2, 2, 2, 2])
                cols[0].write(f"**{row['Ticker']}**")
                cols[1].write(f"CMP: ₹{row['CMP']}")
                cols[2].write(f"BO: ₹{row['Breakout Price']}")
                cols[3].write(f"Dist: {row['Distance %']}%")
                cols[4].write(f"Vol: {row['Vol Ratio']}x")
                if cols[5].button("Buy 🛒", key=f"buy_{row['Ticker']}"):
                    add_to_portfolio(row['Ticker'], row['CMP'], row['Breakout Price'])
        else:
            st.warning("No stocks found in range.")

with tab2:
    st.header("My Portfolio")
    if st.session_state.portfolio.empty:
        st.info("Your portfolio is empty. Go to the Scanner tab to add stocks.")
    else:
        # Get live prices for portfolio stocks
        portfolio_list = st.session_state.portfolio['Ticker'].tolist()
        
        # Real-time update logic
        if st.button("🔄 Refresh Portfolio Prices"):
            st.rerun()

        display_data = []
        for _, stock in st.session_state.portfolio.iterrows():
            try:
                # Fetching current price for real-time update
                live_data = yf.Ticker(f"{stock['Ticker']}.NS").fast_info['last_price']
                current_price = round(live_data, 2)
            except:
                current_price = stock['Buy Price']

            pnl = round(current_price - stock['Buy Price'], 2)
            pnl_pct = round((pnl / stock['Buy Price']) * 100, 2)
            
            # Color Logic
            status_color = "green" if current_price >= stock['Buy Price'] else "red"
            
            display_data.append({
                "Ticker": stock['Ticker'],
                "Buy Price": stock['Buy Price'],
                "Live CMP": current_price,
                "P&L (₹)": pnl,
                "P&L %": pnl_pct,
                "Target": stock['Target'],
                "Stop Loss": stock['Stop Loss'],
                "Est. Days": stock['Days to Target'],
                "Color": status_color
            })

        # Render Portfolio with Color-Coding
        for data in display_data:
            with st.container():
                c1, c2, c3, c4, c5, c6 = st.columns(6)
                c1.markdown(f"### :{data['Color']}[{data['Ticker']}]")
                c2.metric("CMP", f"₹{data['Live CMP']}", f"{data['P&L %']}%")
                c3.write(f"**Buy Price:**\n₹{data['Buy Price']}")
                c4.write(f"**Target:**\n₹{data['Target']}")
                c5.write(f"**Stop Loss:**\n₹{data['Stop Loss']}")
                c6.write(f"**Timeline:**\n{data['Est. Days']} Days")
                st.divider()

        if st.button("🗑️ Clear Portfolio"):
            st.session_state.portfolio = pd.DataFrame(columns=['Ticker', 'Buy Price', 'Target', 'Stop Loss', 'Days to Target', 'Entry Date'])
            st.rerun()
