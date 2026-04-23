import streamlit as st
import yfinance as yf
import pandas as pd
import concurrent.futures
import json
import os
from datetime import datetime

# --- Configuration & Persistence ---
st.set_page_config(page_title="Alpha Breakout Pro", layout="wide")
DB_FILE = "trading_data.json"

def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {"portfolio": [], "sold": []}

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

# Initialize data
if 'db' not in st.session_state:
    st.session_state.db = load_data()

# --- Helper Functions ---

@st.cache_data(ttl=86400)
def get_nifty_500_tickers():
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    try:
        df = pd.read_csv(url)
        return [f"{symbol}.NS" for symbol in df['Symbol'].tolist()]
    except:
        return ['RELIANCE.NS', 'TCS.NS', 'SBIN.NS']

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
        dist = ((breakout_price - cmp) / breakout_price) * 100
        
        if 0 <= dist <= 3.0:
            return {
                "Ticker": ticker.replace(".NS", ""),
                "CMP": round(cmp, 2),
                "BO_Level": round(breakout_price, 2),
                "Dist": round(dist, 2),
                "Vol_Ratio": round(vol_ratio, 2),
                "Prob": round(vol_ratio * (5 / (dist + 0.1)), 2) # Probability Score
            }
    except: return None

# --- Action Functions ---

def buy_stock(res):
    new_entry = {
        "ticker": res['Ticker'],
        "buy_price": res['CMP'],
        "target": round(res['BO_Level'] * 1.10, 2),
        "sl": round(res['CMP'] * 0.95, 2),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    st.session_state.db["portfolio"].append(new_entry)
    save_data(st.session_state.db)
    st.toast(f"Bought {res['Ticker']}")

def sell_stock(index, current_price):
    stock = st.session_state.db["portfolio"].pop(index)
    pnl = round((current_price - stock['buy_price']), 2)
    stock["sell_price"] = current_price
    stock["pnl"] = pnl
    stock["pnl_pct"] = round((pnl / stock['buy_price']) * 100, 2)
    stock["sell_date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    st.session_state.db["sold"].append(stock)
    save_data(st.session_state.db)
    st.rerun()

# --- UI ---
st.title("🚀 Alpha Breakout Pro")

tabs = st.tabs(["🔍 Probability Scanner", "💼 Active Portfolio", "📜 History (Sold)"])

with tabs[0]:
    tickers = get_nifty_500_tickers()
    if st.button("🔥 Run High-Probability Scan"):
        results = []
        with st.status("Analyzing Market Volatility...", expanded=True):
            with concurrent.futures.ThreadPoolExecutor(max_workers=25) as ex:
                futures = {ex.submit(check_near_breakout, t): t for t in tickers}
                for f in concurrent.futures.as_completed(futures):
                    r = f.result()
                    if r: results.append(r)
        # SORTING BY PROBABILITY (Vol Ratio / Distance)
        st.session_state.scan_results = sorted(results, key=lambda x: x['Prob'], reverse=True)

    if 'scan_results' in st.session_state:
        for res in st.session_state.scan_results:
            with st.expander(f"{res['Ticker']} | Prob Score: {res['Prob']} | Vol: {res['Vol_Ratio']}x"):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("CMP", f"₹{res['CMP']}")
                c2.metric("Breakout Level", f"₹{res['BO_Level']}", f"{res['Dist']}% Away", delta_color="inverse")
                c3.write(f"**Target (10%):** ₹{round(res['BO_Level']*1.1, 2)}")
                if c4.button(f"Confirm Buy {res['Ticker']}", key=f"buy_{res['Ticker']}"):
                    buy_stock(res)

with tabs[1]:
    portfolio = st.session_state.db["portfolio"]
    if not portfolio:
        st.info("No active trades.")
    else:
        total_pnl = 0
        for i, s in enumerate(portfolio):
            try:
                live_price = round(yf.Ticker(f"{s['ticker']}.NS").fast_info['last_price'], 2)
            except: live_price = s['buy_price']
            
            pnl = round(live_price - s['buy_price'], 2)
            total_pnl += pnl
            color = "green" if pnl >= 0 else "red"
            
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
                col1.markdown(f"### :{color}[{s['ticker']}]")
                col2.metric("CMP", f"₹{live_price}", f"{round((pnl/s['buy_price'])*100, 2)}%")
                col3.write(f"**Buy:** ₹{s['buy_price']} | **Target:** ₹{s['target']}")
                if col4.button(f"Sell {s['ticker']}", key=f"sell_{i}"):
                    sell_stock(i, live_price)
        
        st.sidebar.metric("Total Unrealized P&L", f"₹{round(total_pnl, 2)}", delta=total_pnl)

with tabs[2]:
    st.header("Closed Positions")
    sold_data = st.session_state.db["sold"]
    if sold_data:
        df_sold = pd.DataFrame(sold_data)
        def color_pnl(val):
            return 'color: green' if val > 0 else 'color: red'
        st.dataframe(df_sold.style.applymap(color_pnl, subset=['pnl']))
        st.metric("Total Realized P&L", f"₹{round(df_sold['pnl'].sum(), 2)}")
    else:
        st.write("No historical data yet.")
