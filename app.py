# ================================
# IMPORTS
# ================================
import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, time as dtime
from concurrent.futures import ThreadPoolExecutor
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# ================================
# CONFIG
# ================================
st.set_page_config(page_title="ORB V22 Smart System", layout="wide")
st.title("🚀 ORB V22 (Multi-Cap Smart System)")

INITIAL_CAPITAL = 100000

# ================================
# MARKET UNIVERSES
# ================================
LARGE_CAP = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", "HINDUNILVR.NS", "BHARTIARTL.NS", "SBIN.NS", "LT.NS", "ITC.NS"]
MID_CAP = ["TATAPOWER.NS", "VOLTAS.NS", "BATAINDIA.NS", "CUMMINSIND.NS", "AUROPHARMA.NS", "POLYCAB.NS", "COFORGE.NS", "CONCOR.NS", "DIXON.NS"]
SMALL_CAP = ["ZENSARTECH.NS", "RITES.NS", "NBCC.NS", "HFCL.NS", "IEX.NS", "KEI.NS", "CASTROLIND.NS", "MASTEK.NS"]

# ================================
# MARKET HOURS FUNCTION
# ================================
def is_market_open():
    now = datetime.now().time()
    return dtime(9, 15) <= now <= dtime(15, 30)

market_open = is_market_open()

# ================================
# SMART AUTO REFRESH
# ================================
if market_open:
    refresh_interval = 30 * 1000  # 30 sec during market
else:
    refresh_interval = 300 * 1000  # 5 min after market

st_autorefresh(interval=refresh_interval, key="smart_refresh")

# ================================
# SIDEBAR CONTROLS
# ================================
with st.sidebar:
    st.header("⚙️ Strategy Settings")
    orb_minutes = st.number_input("ORB Minutes", 5, 60, 15)
    ema_period = st.number_input("EMA Period", 5, 100, 20)
    risk_pct = st.slider("Risk % per Trade", 0.1, 2.0, 1.0)
    
    st.divider()
    st.header("🏢 Scan Universe")
    segment = st.selectbox("Select Segment", ["Large Cap", "Mid Cap", "Small Cap", "Custom List"])
    
    if segment == "Large Cap":
        target_symbols = LARGE_CAP
    elif segment == "Mid Cap":
        target_symbols = MID_CAP
    elif segment == "Small Cap":
        target_symbols = SMALL_CAP
    else:
        target_symbols = ["RELIANCE.NS", "TCS.NS"] # Default Custom

# ================================
# SESSION STATE
# ================================
if "capital" not in st.session_state:
    st.session_state.capital = INITIAL_CAPITAL
if "active_trades" not in st.session_state:
    st.session_state.active_trades = {}
if "closed_trades" not in st.session_state:
    st.session_state.closed_trades = []
if "equity" not in st.session_state:
    st.session_state.equity = []

# ================================
# CORE LOGIC FUNCTIONS
# ================================
def fetch(symbol):
    try:
        df = yf.download(symbol, interval="5m", period="1d", progress=False)
        df.dropna(inplace=True)
        return symbol, df
    except:
        return symbol, None

def get_signal(df):
    # Indicator Logic
    df["EMA"] = df["Close"].ewm(span=ema_period).mean()
    df["Vol_Avg"] = df["Volume"].rolling(20).mean()
    
    # ORB Logic
    df["Time"] = df.index.time
    cutoff = (datetime.combine(datetime.today(), dtime(9, 15)) + pd.Timedelta(minutes=orb_minutes)).time()
    orb_df = df[df["Time"] <= cutoff]

    if orb_df.empty: return None

    high, low = orb_df["High"].max(), orb_df["Low"].min()
    last = df["Close"].iloc[-1]

    # Filters
    body = abs(df["Close"] - df["Open"])
    rng = (df["High"] - df["Low"]).replace(0, 1e-9)
    body_pct = (body / rng).iloc[-1]
    vol_ratio = (df["Volume"].iloc[-1] / df["Vol_Avg"].iloc[-1])

    if last > high and body_pct >= 0.6 and vol_ratio > 1.5:
        return "BUY", last, high, low
    elif last < low and body_pct >= 0.6 and vol_ratio > 1.5:
        return "SELL", last, high, low
    
    return None

def calculate_qty(entry, sl):
    risk_amt = st.session_state.capital * (risk_pct / 100)
    risk_per_share = abs(entry - sl)
    return int(risk_amt / risk_per_share) if risk_per_share > 0 else 0

# ================================
# MAIN SCANNER EXECUTION
# ================================
st.subheader(f"🔍 Scanner Status: {segment}")
manual_scan = st.button("🔄 Force Manual Scan")

if market_open or manual_scan:
    progress_bar = st.progress(0)
    status_msg = st.empty()
    
    qualified_count = 0
    scanned_count = 0
    scanned_names = []

    # Parallel Data Fetching
    with ThreadPoolExecutor(max_workers=10) as executor:
        data = list(executor.map(fetch, target_symbols))

    for i, (symbol, df) in enumerate(data):
        scanned_count += 1
        pct = scanned_count / len(target_symbols)
        progress_bar.progress(pct)
        status_msg.text(f"Processing Stock {scanned_count}/{len(target_symbols)}: {symbol}")
        scanned_names.append(symbol)

        if df is not None and len(df) > 10:
            if symbol not in st.session_state.active_trades:
                signal = get_signal(df)
                if signal:
                    dir, price, h, l = signal
                    sl = l if dir == "BUY" else h
                    qty = calculate_qty(price, sl)
                    if qty > 0:
                        st.session_state.active_trades[symbol] = {
                            "Type": dir, "Entry": price, "SL": sl, "Qty": qty, "Time": datetime.now().strftime("%H:%M")
                        }
                        qualified_count += 1
            else:
                # If already in trade, it counts as a qualified equity for this session
                qualified_count += 1
    
    status_msg.success(f"✅ Scan Finished! Total Scanned: {scanned_count} | Qualified/Active: {qualified_count}")
    st.caption(f"Symbols checked: {', '.join(scanned_names)}")
else:
    st.info("⏸ Market is currently closed. Auto-refresh is on 5-minute standby.")

# ================================
# DASHBOARD LAYOUT
# ================================
col_metric1, col_metric2, col_metric3 = st.columns(3)
col_metric1.metric("Current Capital", f"₹{round(st.session_state.capital, 2)}")
col_metric2.metric("Active Trades", len(st.session_state.active_trades))
col_metric3.metric("Segment Universe", len(target_symbols))

st.divider()

t_col1, t_col2 = st.columns(2)
with t_col1:
    st.subheader("📈 Active Positions")
    if st.session_state.active_trades:
        st.dataframe(pd.DataFrame(st.session_state.active_trades).T, use_container_width=True)
    else:
        st.write("No active trades.")

with t_col2:
    st.subheader("📜 Closed Trades")
    if st.session_state.closed_trades:
        st.dataframe(pd.DataFrame(st.session_state.closed_trades), use_container_width=True)
    else:
        st.write("History is empty.")

# ================================
# EQUITY CURVE
# ================================
st.session_state.equity.append({"time": datetime.now(), "capital": st.session_state.capital})
eq_df = pd.DataFrame(st.session_state.equity)

st.subheader("📊 Equity Curve")
fig = go.Figure()
fig.add_trace(go.Scatter(x=eq_df["time"], y=eq_df["capital"], mode="lines+markers", name="Net Capital"))
fig.update_layout(template="plotly_dark", margin=dict(l=20, r=20, t=20, b=20))
st.plotly_chart(fig, use_container_width=True)

st.write(f"🕒 Last Engine Pulse: {datetime.now().strftime('%H:%M:%S')}")
