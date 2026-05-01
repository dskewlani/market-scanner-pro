# ================================
# ORB SMART SCANNER - FULL REWRITE
# Dynamic symbol scanning - not fixed to any ticker
# ================================

import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, time as dtime
from concurrent.futures import ThreadPoolExecutor, as_completed
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import traceback

# ================================
# PAGE CONFIG
# ================================
st.set_page_config(
    page_title="ORB Smart Scanner",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    .stMetric label { font-size: 0.75rem; color: #888; }
    .stMetric value { font-size: 1.4rem; font-weight: 600; }
    div[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }
    .signal-buy  { background-color: #e6f4ea !important; color: #1a7f3c !important; font-weight: 600; }
    .signal-sell { background-color: #fce8e6 !important; color: #c5221f !important; font-weight: 600; }
    .stAlert { border-radius: 8px; }
    .scan-header { font-size: 0.7rem; color: #aaa; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.25rem; }
</style>
""", unsafe_allow_html=True)

# ================================
# PRESET SYMBOL LISTS
# (user can override these fully)
# ================================
PRESETS = {
    "Nifty 50 (Large Cap)": [
        "RELIANCE.NS","TCS.NS","HDFCBANK.NS","BHARTIARTL.NS","ICICIBANK.NS",
        "INFOSYS.NS","SBIN.NS","WIPRO.NS","AXISBANK.NS","LT.NS",
        "KOTAKBANK.NS","HCLTECH.NS","BAJFINANCE.NS","ASIANPAINT.NS","MARUTI.NS",
        "TITAN.NS","SUNPHARMA.NS","NTPC.NS","POWERGRID.NS","ULTRACEMCO.NS",
        "NESTLEIND.NS","TATAMOTORS.NS","TATASTEEL.NS","TECHM.NS","INDUSINDBK.NS",
        "ADANIPORTS.NS","CIPLA.NS","HEROMOTOCO.NS","EICHERMOT.NS","BAJAJFINSV.NS",
        "DRREDDY.NS","DIVISLAB.NS","BRITANNIA.NS","APOLLOHOSP.NS","COALINDIA.NS",
        "HINDALCO.NS","JSWSTEEL.NS","ONGC.NS","BPCL.NS","IOC.NS",
        "GRASIM.NS","TATACONSUM.NS","SBILIFE.NS","HDFCLIFE.NS","UPL.NS",
        "BAJAJ-AUTO.NS","SHRIRAMFIN.NS","M&M.NS","ADANIENT.NS","BEL.NS",
    ],
    "Nifty Next 50 (Mid-Large)": [
        "ABB.NS","ADANIGREEN.NS","ADANITRANS.NS","AMBUJACEM.NS","AUROPHARMA.NS",
        "BALKRISIND.NS","BANDHANBNK.NS","BANKBARODA.NS","BERGEPAINT.NS","BOSCHLTD.NS",
        "CANBK.NS","CHOLAFIN.NS","COLPAL.NS","CONCOR.NS","DABUR.NS",
        "DLF.NS","DMART.NS","FEDERALBNK.NS","GAIL.NS","GODREJCP.NS",
        "HAVELLS.NS","HDFCAMC.NS","HINDPETRO.NS","ICICIPRULI.NS","IDFCFIRSTB.NS",
        "IGL.NS","INDIGO.NS","INDUSTOWER.NS","IRCTC.NS","JUBLFOOD.NS",
        "LICI.NS","LODHA.NS","LUPIN.NS","MCDOWELL-N.NS","MFSL.NS",
        "MPHASIS.NS","MUTHOOTFIN.NS","NAUKRI.NS","NMDC.NS","OFSS.NS",
        "PAGEIND.NS","PERSISTENT.NS","PIIND.NS","PNB.NS","RECLTD.NS",
        "SAIL.NS","SIEMENS.NS","TATAPOWER.NS","TORNTPHARM.NS","VEDL.NS",
    ],
    "Nifty Midcap 50": [
        "ABCAPITAL.NS","ABFRL.NS","APLAPOLLO.NS","ASHOKLEY.NS","ASTRAL.NS",
        "AUBANK.NS","AWHCL.NS","BHEL.NS","BIRLACORPN.NS","BSE.NS",
        "CAMS.NS","CANFINHOME.NS","CDSL.NS","CESC.NS","CHAMBLFERT.NS",
        "CROMPTON.NS","CUMMINSIND.NS","DEEPAKNTR.NS","ELGIEQUIP.NS","ENGINERSIN.NS",
        "ESCORTS.NS","FINCABLES.NS","GLENMARK.NS","GNFC.NS","GRINDWELL.NS",
        "GSFC.NS","HFCL.NS","HINDCOPPER.NS","HUDCO.NS","IDEA.NS",
        "IDFC.NS","IIFL.NS","INDIANB.NS","INDIAMART.NS","IOB.NS",
        "KAJARIACER.NS","KPIL.NS","LICHSGFIN.NS","LTTS.NS","MANAPPURAM.NS",
        "MARICO.NS","MCX.NS","METROPOLIS.NS","MOTHERSON.NS","NATIONALUM.NS",
        "NBCC.NS","NLCINDIA.NS","OBEROIRLTY.NS","OFSS.NS","POLICYBZR.NS",
    ],
    "Bank Nifty": [
        "HDFCBANK.NS","ICICIBANK.NS","KOTAKBANK.NS","AXISBANK.NS","SBIN.NS",
        "INDUSINDBK.NS","BANDHANBNK.NS","FEDERALBNK.NS","IDFCFIRSTB.NS","PNB.NS",
        "BANKBARODA.NS","CANBK.NS","UNIONBANK.NS","INDIANB.NS","IOB.NS",
        "UCO.NS","CENTRALBK.NS","MAHABANK.NS","KARURVYSYA.NS","DCBBANK.NS",
    ],
    "IT Sector": [
        "TCS.NS","INFOSYS.NS","WIPRO.NS","HCLTECH.NS","TECHM.NS",
        "MPHASIS.NS","LTTS.NS","PERSISTENT.NS","COFORGE.NS","OFSS.NS",
        "KPITTECH.NS","SONATSOFTW.NS","MASTEK.NS","NIITTECH.NS","HEXAWARE.NS",
    ],
    "Pharma Sector": [
        "SUNPHARMA.NS","DRREDDY.NS","CIPLA.NS","DIVISLAB.NS","LUPIN.NS",
        "APOLLOHOSP.NS","AUROPHARMA.NS","TORNTPHARM.NS","GLENMARK.NS","BIOCON.NS",
        "ALKEM.NS","IPCA.NS","NATCOPHARM.NS","GRANULES.NS","LAURUSLABS.NS",
    ],
    "Auto Sector": [
        "MARUTI.NS","TATAMOTORS.NS","BAJAJ-AUTO.NS","HEROMOTOCO.NS","EICHERMOT.NS",
        "M&M.NS","ASHOKLEY.NS","ESCORTS.NS","MOTHERSON.NS","BHARAT FORGE.NS",
        "BALKRISIND.NS","APOLLOTYRE.NS","CEAT.NS","EXIDEIND.NS","AMARAJABAT.NS",
    ],
    "Custom (Enter Below)": [],
}

# ================================
# MARKET HOURS
# ================================
def is_market_open():
    now = datetime.now().time()
    return dtime(9, 15) <= now <= dtime(15, 30)

def is_pre_market():
    now = datetime.now().time()
    return dtime(9, 0) <= now < dtime(9, 15)

market_open = is_market_open()

# ================================
# SMART AUTO REFRESH
# ================================
refresh_ms = 30_000 if market_open else 300_000
st_autorefresh(interval=refresh_ms, key="smart_refresh")

# ================================
# SESSION STATE INIT
# ================================
def init_state():
    defaults = {
        "capital": 100_000,
        "initial_capital": 100_000,
        "active_trades": {},
        "closed_trades": [],
        "equity": [],
        "scan_results": [],
        "last_scan_time": None,
        "error_log": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ================================
# SIDEBAR — ALL SETTINGS
# ================================
with st.sidebar:
    st.title("⚙️ Scanner Settings")

    st.markdown("### 📋 Symbol Selection")

    preset_choice = st.selectbox(
        "Choose Preset",
        list(PRESETS.keys()),
        index=0
    )

    if preset_choice == "Custom (Enter Below)":
        custom_raw = st.text_area(
            "Enter tickers (one per line or comma-separated)",
            placeholder="RELIANCE\nTCS\nINFY\nor RELIANCE,TCS,INFY",
            height=120
        )
        raw_list = [
            s.strip().upper()
            for part in custom_raw.replace(",", "\n").splitlines()
            for s in [part.strip()] if s.strip()
        ]
        # Auto-append .NS if missing
        symbols_pool = [
            s if s.endswith(".NS") or s.endswith(".BO") else s + ".NS"
            for s in raw_list if s
        ]
    else:
        symbols_pool = PRESETS[preset_choice]

    if symbols_pool:
        selected_symbols = st.multiselect(
            f"Select from {preset_choice.split('(')[0].strip()}",
            options=symbols_pool,
            default=symbols_pool[:15] if len(symbols_pool) > 15 else symbols_pool,
            help="You can add/remove any symbols"
        )
    else:
        selected_symbols = []

    st.caption(f"**{len(selected_symbols)}** symbols selected")

    # Optionally add extra symbols on top of preset
    st.markdown("##### ➕ Add extra symbols")
    extra_raw = st.text_input("Extra tickers (comma-separated)", placeholder="ZOMATO,PAYTM,NYKAA")
    if extra_raw.strip():
        extras = [
            s.strip().upper() + (".NS" if not s.strip().upper().endswith(".NS") else "")
            for s in extra_raw.split(",") if s.strip()
        ]
        selected_symbols = list(dict.fromkeys(selected_symbols + extras))

    st.divider()
    st.markdown("### 📐 Strategy Parameters")

    orb_minutes   = st.number_input("ORB Minutes", 5, 60, 15, help="Opening Range Breakout window in minutes")
    ema_period    = st.number_input("EMA Period", 5, 100, 20)
    atr_period    = st.number_input("ATR Period", 5, 30, 14)

    st.divider()
    st.markdown("### 💰 Risk Management")

    initial_capital = st.number_input("Initial Capital (₹)", 10_000, 10_000_000, 100_000, step=10_000)
    if st.button("🔁 Reset Capital"):
        st.session_state.capital = initial_capital
        st.session_state.initial_capital = initial_capital
        st.session_state.active_trades = {}
        st.session_state.closed_trades = []
        st.session_state.equity = []
        st.rerun()

    risk_pct        = st.slider("Risk per Trade (%)", 0.5, 3.0, 1.0, 0.1)
    max_trades      = st.number_input("Max Concurrent Trades", 1, 30, 5)
    max_risk_pct    = st.slider("Max Portfolio Risk (%)", 1.0, 10.0, 5.0, 0.5)

    st.divider()
    st.markdown("### 🔍 Signal Filters")

    min_vol_ratio   = st.slider("Min Volume Ratio", 1.0, 5.0, 1.8, 0.1, help="Volume vs 20-bar average")
    min_body_pct    = st.slider("Min Candle Body %", 0.3, 0.9, 0.6, 0.05)
    min_ema_dist    = st.slider("Min EMA Distance %", 0.1, 2.0, 0.5, 0.1) / 100
    max_ema_dist    = st.slider("Max EMA Distance %", 0.5, 5.0, 2.0, 0.1) / 100
    min_atr_ratio   = st.slider("Min ATR Ratio %", 0.1, 1.0, 0.3, 0.05) / 100

    st.divider()
    st.markdown("### 🛡️ Trailing Stop")
    trail_buy_pct   = st.slider("Trail Buy SL (%)", 0.1, 2.0, 0.5, 0.05) / 100
    trail_sell_pct  = st.slider("Trail Sell SL (%)", 0.1, 2.0, 0.5, 0.05) / 100

    st.divider()
    show_errors = st.checkbox("Show fetch errors", False)

# ================================
# MAIN HEADER
# ================================
col_h1, col_h2, col_h3 = st.columns([3, 1, 1])
with col_h1:
    st.title("🚀 ORB Smart Scanner")
    status_txt = "🟢 Market Open" if market_open else ("🟡 Pre-Market" if is_pre_market() else "🔴 Market Closed")
    st.caption(f"{status_txt} &nbsp;|&nbsp; {datetime.now().strftime('%d %b %Y, %H:%M:%S')} &nbsp;|&nbsp; {len(selected_symbols)} symbols loaded")

with col_h2:
    manual_scan = st.button("🔄 Scan Now", use_container_width=True, type="primary")

with col_h3:
    if st.button("🧹 Clear Trades", use_container_width=True):
        st.session_state.active_trades = {}
        st.session_state.closed_trades = []
        st.rerun()

if not market_open:
    st.warning("⏸ Market is closed. Auto-scan paused. Use **Scan Now** for manual scan on historical intraday data.")

# ================================
# FETCH FUNCTION
# ================================
def fetch(symbol):
    try:
        df = yf.download(symbol, interval="5m", period="1d", progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.dropna(inplace=True)
        if df.empty:
            return symbol, None, "Empty data returned"
        return symbol, df, None
    except Exception as e:
        return symbol, None, str(e)

# ================================
# INDICATORS
# ================================
def add_indicators(df):
    df = df.copy()
    df["EMA"]     = df["Close"].ewm(span=ema_period, adjust=False).mean()
    df["H_L"]     = df["High"] - df["Low"]
    df["H_PC"]    = abs(df["High"] - df["Close"].shift(1))
    df["L_PC"]    = abs(df["Low"]  - df["Close"].shift(1))
    df["TR"]      = df[["H_L","H_PC","L_PC"]].max(axis=1)
    df["ATR"]     = df["TR"].rolling(atr_period).mean()
    df["Vol_Avg"] = df["Volume"].rolling(20).mean()
    body          = abs(df["Close"] - df["Open"])
    rng           = (df["High"] - df["Low"]).replace(0, 1e-9)
    df["BodyPct"] = body / rng
    return df

# ================================
# SIGNAL FILTERS
# ================================
def breakout_confirmed(df, level, direction):
    last, prev = df["Close"].iloc[-1], df["Close"].iloc[-2]
    return (prev > level and last > level) if direction == "BUY" else (prev < level and last < level)

def check_candle(df):
    return float(df["BodyPct"].iloc[-1]) >= min_body_pct

def check_volume(df):
    vol     = float(df["Volume"].iloc[-1])
    vol_avg = float(df["Vol_Avg"].iloc[-1])
    if vol_avg == 0:
        return False, 0
    ratio = vol / vol_avg
    return ratio >= min_vol_ratio, round(ratio, 2)

def check_ema_dist(df):
    price = float(df["Close"].iloc[-1])
    ema   = float(df["EMA"].iloc[-1])
    dist  = abs(price - ema) / ema
    return min_ema_dist <= dist <= max_ema_dist

def check_atr(df):
    atr   = float(df["ATR"].iloc[-1])
    close = float(df["Close"].iloc[-1])
    return (atr / close) > min_atr_ratio

# ================================
# SIGNAL GENERATOR
# ================================
def get_signal(df):
    df = add_indicators(df)
    df = df.copy()
    df.index = pd.to_datetime(df.index)
    df["_time"] = df.index.time

    cutoff = (
        pd.Timestamp.combine(pd.Timestamp.today().date(), dtime(9, 15))
        + pd.Timedelta(minutes=int(orb_minutes))
    ).time()

    orb_df = df[df["_time"] <= cutoff]
    if len(orb_df) < 3:
        return None, "Insufficient ORB data"

    orb_high = float(orb_df["High"].max())
    orb_low  = float(orb_df["Low"].min())
    last     = float(df["Close"].iloc[-1])
    atr      = float(df["ATR"].iloc[-1]) if not pd.isna(df["ATR"].iloc[-1]) else 0

    if last > orb_high:
        direction, level = "BUY", orb_high
    elif last < orb_low:
        direction, level = "SELL", orb_low
    else:
        return None, "Inside ORB range"

    if not breakout_confirmed(df, level, direction):
        return None, "Breakout not confirmed (2-bar)"
    if not check_candle(df):
        return None, f"Weak candle body ({df['BodyPct'].iloc[-1]:.2f})"
    vol_ok, vol_ratio = check_volume(df)
    if not vol_ok:
        return None, f"Low volume ratio ({vol_ratio}x)"
    if not check_ema_dist(df):
        return None, "EMA distance out of range"
    if not check_atr(df):
        return None, "ATR too low (low volatility)"

    _, vol_ratio = check_volume(df)

    return {
        "direction": direction,
        "price":     round(last, 2),
        "orb_high":  round(orb_high, 2),
        "orb_low":   round(orb_low, 2),
        "atr":       round(atr, 2),
        "vol_ratio": vol_ratio,
        "ema":       round(float(df["EMA"].iloc[-1]), 2),
    }, None

# ================================
# POSITION SIZING
# ================================
def calculate_qty(entry, sl):
    risk_amount    = st.session_state.capital * (risk_pct / 100)
    risk_per_share = abs(entry - sl)
    if risk_per_share == 0:
        return 0
    return max(1, int(risk_amount / risk_per_share))

def total_risk_deployed():
    total = 0
    for sym, t in st.session_state.active_trades.items():
        total += abs(t["entry"] - t["sl"]) * t["qty"]
    return total

# ================================
# TRADE MANAGEMENT
# ================================
def enter_trade(symbol, signal):
    direction = signal["direction"]
    price     = signal["price"]
    orb_high  = signal["orb_high"]
    orb_low   = signal["orb_low"]
    atr       = signal["atr"]

    sl  = orb_low  if direction == "BUY"  else orb_high
    tgt = price + (2 * atr) if direction == "BUY" else price - (2 * atr)
    qty = calculate_qty(price, sl)

    if qty == 0:
        return

    # Check portfolio-level risk cap
    new_risk = abs(price - sl) * qty
    current_risk = total_risk_deployed()
    if (current_risk + new_risk) / st.session_state.capital > (max_risk_pct / 100):
        return  # Would breach portfolio risk cap

    st.session_state.active_trades[symbol] = {
        "type":    direction,
        "entry":   price,
        "sl":      sl,
        "target":  round(tgt, 2),
        "qty":     qty,
        "entry_time": datetime.now().strftime("%H:%M:%S"),
        "atr":     atr,
        "vol_ratio": signal["vol_ratio"],
    }

def manage_trade(symbol, df):
    trade = st.session_state.active_trades[symbol]
    price = float(df["Close"].iloc[-1])

    if trade["type"] == "BUY":
        # Trail stop up
        new_sl = price * (1 - trail_buy_pct)
        trade["sl"] = max(trade["sl"], round(new_sl, 2))
        # Exit conditions
        if price <= trade["sl"]:
            pnl = (price - trade["entry"]) * trade["qty"]
            exit_trade(symbol, price, pnl, "SL Hit")
        elif price >= trade["target"]:
            pnl = (price - trade["entry"]) * trade["qty"]
            exit_trade(symbol, price, pnl, "Target Hit")
    else:
        # Trail stop down
        new_sl = price * (1 + trail_sell_pct)
        trade["sl"] = min(trade["sl"], round(new_sl, 2))
        if price >= trade["sl"]:
            pnl = (trade["entry"] - price) * trade["qty"]
            exit_trade(symbol, price, pnl, "SL Hit")
        elif price <= trade["target"]:
            pnl = (trade["entry"] - price) * trade["qty"]
            exit_trade(symbol, price, pnl, "Target Hit")

def exit_trade(symbol, price, pnl, reason="Manual"):
    trade = st.session_state.active_trades.pop(symbol)
    st.session_state.capital += round(pnl, 2)
    st.session_state.closed_trades.append({
        "Symbol":     symbol,
        "Type":       trade["type"],
        "Entry":      trade["entry"],
        "Exit":       round(price, 2),
        "Qty":        trade["qty"],
        "PnL (₹)":    round(pnl, 2),
        "PnL %":      round((pnl / (trade["entry"] * trade["qty"])) * 100, 2),
        "Reason":     reason,
        "Entry Time": trade.get("entry_time", "—"),
        "Exit Time":  datetime.now().strftime("%H:%M:%S"),
    })

# ================================
# MAIN SCAN LOGIC
# ================================
run_scan = market_open or manual_scan

if run_scan and selected_symbols:
    scan_results  = []
    errors        = []
    signals_found = 0

    progress_bar  = st.progress(0, text="Initialising scan...")
    status_holder = st.empty()
    total         = len(selected_symbols)

    # Batch fetching
    BATCH   = 20
    all_data = []
    done    = 0

    for i in range(0, total, BATCH):
        batch = selected_symbols[i:i + BATCH]
        with ThreadPoolExecutor(max_workers=min(10, len(batch))) as ex:
            futures = {ex.submit(fetch, s): s for s in batch}
            for f in as_completed(futures):
                result = f.result()
                all_data.append(result)
                done += 1
                pct = done / total
                progress_bar.progress(pct, text=f"Fetching data... {done}/{total}")

    progress_bar.empty()
    status_holder.empty()

    # Process each symbol
    for symbol, df, err in all_data:
        if err or df is None or len(df) < 30:
            errors.append({"Symbol": symbol, "Error": err or "Too few bars"})
            scan_results.append({
                "Symbol": symbol, "Signal": "Error", "Price": "—",
                "ORB High": "—", "ORB Low": "—", "ATR": "—",
                "Vol Ratio": "—", "Reason": err or "Insufficient data"
            })
            continue

        # Manage existing trade
        if symbol in st.session_state.active_trades:
            manage_trade(symbol, df)
            trade = st.session_state.active_trades.get(symbol)
            if trade:
                price = float(df["Close"].iloc[-1])
                unreal_pnl = (
                    (price - trade["entry"]) * trade["qty"]
                    if trade["type"] == "BUY"
                    else (trade["entry"] - price) * trade["qty"]
                )
                scan_results.append({
                    "Symbol":    symbol,
                    "Signal":    f"🔵 {trade['type']} (Active)",
                    "Price":     round(price, 2),
                    "ORB High":  "—",
                    "ORB Low":   "—",
                    "ATR":       trade.get("atr", "—"),
                    "Vol Ratio": trade.get("vol_ratio", "—"),
                    "Reason":    f"Unrealised ₹{round(unreal_pnl,2):+,.2f}",
                })
            continue

        # Check for new signal
        n_active = len(st.session_state.active_trades)
        signal, reason = get_signal(df)

        if signal is None:
            scan_results.append({
                "Symbol":    symbol,
                "Signal":    "—",
                "Price":     round(float(df["Close"].iloc[-1]), 2),
                "ORB High":  "—",
                "ORB Low":   "—",
                "ATR":       "—",
                "Vol Ratio": "—",
                "Reason":    reason or "No signal",
            })
            continue

        direction = signal["direction"]
        emoji     = "🟢" if direction == "BUY" else "🔴"

        if n_active >= max_trades:
            scan_results.append({
                "Symbol":    symbol,
                "Signal":    f"{emoji} {direction} (Skipped)",
                "Price":     signal["price"],
                "ORB High":  signal["orb_high"],
                "ORB Low":   signal["orb_low"],
                "ATR":       signal["atr"],
                "Vol Ratio": signal["vol_ratio"],
                "Reason":    "Max trades reached",
            })
            continue

        enter_trade(symbol, signal)
        signals_found += 1

        scan_results.append({
            "Symbol":    symbol,
            "Signal":    f"{emoji} {direction}",
            "Price":     signal["price"],
            "ORB High":  signal["orb_high"],
            "ORB Low":   signal["orb_low"],
            "ATR":       signal["atr"],
            "Vol Ratio": signal["vol_ratio"],
            "Reason":    f"Signal entered @ {signal['price']}",
        })

    st.session_state.scan_results   = scan_results
    st.session_state.last_scan_time = datetime.now().strftime("%H:%M:%S")
    st.session_state.error_log      = errors

    # Equity snapshot
    st.session_state.equity.append({
        "time":    datetime.now(),
        "capital": st.session_state.capital,
    })

    if signals_found > 0:
        st.success(f"✅ Scan complete — **{signals_found} new signal(s)** found across {len(selected_symbols)} symbols")
    else:
        st.info(f"ℹ️ Scan complete — No new signals. {len(selected_symbols)} symbols scanned.")

elif not selected_symbols:
    st.error("⚠️ No symbols selected. Please choose a preset or enter custom tickers in the sidebar.")

# ================================
# DASHBOARD METRICS
# ================================
st.divider()
total_closed_pnl  = sum(t["PnL (₹)"] for t in st.session_state.closed_trades)
win_trades        = [t for t in st.session_state.closed_trades if t["PnL (₹)"] > 0]
win_rate          = (len(win_trades) / len(st.session_state.closed_trades) * 100) if st.session_state.closed_trades else 0
net_change        = st.session_state.capital - st.session_state.get("initial_capital", 100_000)

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("💼 Capital",        f"₹{st.session_state.capital:,.0f}",   f"₹{net_change:+,.0f}")
c2.metric("📈 Realised P&L",   f"₹{total_closed_pnl:,.0f}")
c3.metric("🔓 Active Trades",  len(st.session_state.active_trades),   f"/ {max_trades} max")
c4.metric("📝 Closed Trades",  len(st.session_state.closed_trades))
c5.metric("🏆 Win Rate",       f"{win_rate:.1f}%")
c6.metric("🕒 Last Scan",      st.session_state.last_scan_time or "—")

# ================================
# TABS
# ================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔍 Scan Results",
    "📊 Active Trades",
    "📜 Closed Trades",
    "📈 Equity Curve",
    "⚠️ Error Log",
])

# ---- TAB 1: SCAN RESULTS ----
with tab1:
    if st.session_state.scan_results:
        df_scan = pd.DataFrame(st.session_state.scan_results)

        # Filter controls
        f1, f2, f3 = st.columns(3)
        with f1:
            sig_filter = st.selectbox("Filter by Signal", ["All","BUY","SELL","Active","No Signal","Error"])
        with f2:
            sort_col = st.selectbox("Sort by", ["Symbol","Signal","Price","Vol Ratio","ATR"])
        with f3:
            sort_asc = st.radio("Order", ["↑ Asc","↓ Desc"], horizontal=True) == "↑ Asc"

        # Apply filter
        if sig_filter != "All":
            df_scan = df_scan[df_scan["Signal"].str.contains(sig_filter, case=False, na=False)]

        # Sort (only if column has numeric-friendly data)
        try:
            df_scan = df_scan.sort_values(sort_col, ascending=sort_asc)
        except Exception:
            pass

        st.caption(f"Showing **{len(df_scan)}** of **{len(st.session_state.scan_results)}** symbols")
        st.dataframe(df_scan, use_container_width=True, hide_index=True)
    else:
        st.info("Run a scan to see results here.")

# ---- TAB 2: ACTIVE TRADES ----
with tab2:
    if st.session_state.active_trades:
        rows = []
        for sym, t in st.session_state.active_trades.items():
            live_price = t["entry"]  # will be updated on next scan
            unreal_pnl = (
                (live_price - t["entry"]) * t["qty"]
                if t["type"] == "BUY"
                else (t["entry"] - live_price) * t["qty"]
            )
            rr = abs(t["target"] - t["entry"]) / abs(t["entry"] - t["sl"]) if abs(t["entry"] - t["sl"]) > 0 else 0
            rows.append({
                "Symbol":      sym,
                "Type":        t["type"],
                "Entry":       t["entry"],
                "SL":          t["sl"],
                "Target":      t["target"],
                "Qty":         t["qty"],
                "R:R":         f"1:{rr:.1f}",
                "Entry Time":  t.get("entry_time","—"),
            })

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.markdown("##### Manual Exit")
        exit_sym = st.selectbox("Select symbol to exit", list(st.session_state.active_trades.keys()))
        if st.button(f"🚪 Exit {exit_sym}", type="primary"):
            t = st.session_state.active_trades[exit_sym]
            exit_trade(exit_sym, t["entry"], 0, "Manual Exit")
            st.rerun()
    else:
        st.info("No active trades.")

# ---- TAB 3: CLOSED TRADES ----
with tab3:
    if st.session_state.closed_trades:
        closed_df = pd.DataFrame(st.session_state.closed_trades)
        total_pnl = closed_df["PnL (₹)"].sum()

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Total P&L",  f"₹{total_pnl:,.2f}")
        col_b.metric("Total Trades", len(closed_df))
        col_c.metric("Win Rate", f"{win_rate:.1f}%")

        st.dataframe(closed_df, use_container_width=True, hide_index=True)

        csv = closed_df.to_csv(index=False)
        st.download_button(
            "⬇️ Export to CSV",
            csv,
            file_name=f"orb_trades_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
        )
    else:
        st.info("No closed trades yet.")

# ---- TAB 4: EQUITY CURVE ----
with tab4:
    equity_df = pd.DataFrame(st.session_state.equity)
    if not equity_df.empty:
        initial = st.session_state.get("initial_capital", 100_000)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=equity_df["time"],
            y=equity_df["capital"],
            mode="lines+markers",
            line=dict(color="#2563EB", width=2.5),
            marker=dict(size=4),
            name="Capital",
            fill="tozeroy",
            fillcolor="rgba(37,99,235,0.08)"
        ))
        fig.add_hline(
            y=initial,
            line_dash="dash",
            line_color="gray",
            annotation_text=f"Initial ₹{initial:,.0f}",
            annotation_position="bottom right"
        )
        fig.update_layout(
            title="Equity Curve",
            xaxis_title="Time",
            yaxis_title="Capital (₹)",
            template="plotly_white",
            height=400,
            margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Drawdown
        peak = equity_df["capital"].cummax()
        dd   = ((equity_df["capital"] - peak) / peak) * 100

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=equity_df["time"], y=dd,
            mode="lines", fill="tozeroy",
            line=dict(color="#DC2626", width=1.5),
            fillcolor="rgba(220,38,38,0.1)",
            name="Drawdown %"
        ))
        fig2.update_layout(
            title="Drawdown %",
            xaxis_title="Time",
            yaxis_title="Drawdown (%)",
            template="plotly_white",
            height=220,
            margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No equity data yet. Run a scan to start tracking.")

# ---- TAB 5: ERROR LOG ----
with tab5:
    if st.session_state.error_log:
        st.dataframe(pd.DataFrame(st.session_state.error_log), use_container_width=True, hide_index=True)
        st.caption(f"{len(st.session_state.error_log)} symbol(s) had fetch issues")
    else:
        st.success("No errors in last scan.")
