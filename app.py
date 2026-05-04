# ================================
# ORB SMART SCANNER PRO — v3 ENHANCED (BUG-FIXED)
# Fix: st.session_state accessed from ThreadPoolExecutor threads →
#      cache dict is now passed explicitly; no session_state reads inside threads.
# All other enhancements preserved.
# ================================

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, time as dtime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import plotly.graph_objects as go
import plotly.express as px
from streamlit_autorefresh import st_autorefresh
import json, os, requests, traceback, time, random, smtplib, hashlib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from io import StringIO

# ================================
# PAGE CONFIG
# ================================
st.set_page_config(
    page_title="ORB Smart Scanner Pro",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🚀"
)

# ================================
# DARK MODE STATE (must be first)
# ================================
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

dark = st.session_state.dark_mode

# ================================
# CSS (theme-aware via dark_mode flag)
# ================================
bg_main   = "#0f1117" if dark else "#ffffff"
bg_card   = "#1a1d27" if dark else "#f8fafc"
bg_card2  = "#1e2130" if dark else "#ffffff"
txt_main  = "#e8eaf0" if dark else "#111827"
txt_sub   = "#8b92a9" if dark else "#6b7280"
bdr_col   = "#2d3148" if dark else "#e2e8f0"
plotly_tpl= "plotly_dark" if dark else "plotly_white"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;600;700;800&display=swap');

    :root {{
        --bg-main:  {bg_main};
        --bg-card:  {bg_card};
        --bg-card2: {bg_card2};
        --txt-main: {txt_main};
        --txt-sub:  {txt_sub};
        --bdr:      {bdr_col};
    }}

    html, body, [class*="css"] {{
        font-family: 'Syne', sans-serif;
        background-color: var(--bg-main) !important;
        color: var(--txt-main) !important;
    }}
    code, .stCode {{ font-family: 'JetBrains Mono', monospace !important; }}

    .block-container {{ padding-top: 1rem; background: var(--bg-main); }}
    .stMetric label {{ font-size: 0.72rem; color: var(--txt-sub); letter-spacing: 0.06em; text-transform: uppercase; }}
    .stMetric value {{ font-size: 1.5rem; font-weight: 700; color: var(--txt-main); }}

    div[data-testid="stDataFrame"] {{ border-radius: 10px; overflow: hidden; }}
    .stAlert {{ border-radius: 10px; }}

    .signal-badge-buy  {{ display:inline-block; padding:2px 10px; border-radius:20px; background:#d1fae5; color:#065f46; font-weight:700; font-size:0.82rem; }}
    .signal-badge-sell {{ display:inline-block; padding:2px 10px; border-radius:20px; background:#fee2e2; color:#991b1b; font-weight:700; font-size:0.82rem; }}
    .signal-badge-none {{ display:inline-block; padding:2px 10px; border-radius:20px; background:#f3f4f6; color:#6b7280; font-size:0.82rem; }}

    .score-bar {{ display:inline-block; height:8px; border-radius:4px; background:linear-gradient(90deg,#3b82f6,#10b981); vertical-align:middle; margin-left:6px; }}

    .metric-card {{ background:var(--bg-card2); border:1px solid var(--bdr); border-radius:12px; padding:14px 18px; color:var(--txt-main); }}

    .header-title {{ font-size:2rem; font-weight:800; letter-spacing:-0.02em; color:var(--txt-main); }}
    .header-subtitle {{ font-size:0.85rem; color:var(--txt-sub); margin-top:-8px; }}

    div[data-testid="stTabs"] button {{ font-family:'Syne',sans-serif; font-weight:600; font-size:0.85rem; }}
    .stButton>button {{ border-radius:8px; font-family:'Syne',sans-serif; font-weight:600; }}
    .stButton>button[kind="primary"] {{ background:linear-gradient(135deg,#2563eb,#7c3aed); border:none; color:#fff; }}
    .stButton>button[kind="primary"]:hover {{ background:linear-gradient(135deg,#1d4ed8,#6d28d9); }}

    .backtest-stat {{ text-align:center; padding:12px; background:var(--bg-card); border-radius:10px; border:1px solid var(--bdr); }}
    .backtest-stat .val {{ font-size:1.4rem; font-weight:800; color:var(--txt-main); }}
    .backtest-stat .lbl {{ font-size:0.7rem; color:var(--txt-sub); text-transform:uppercase; letter-spacing:0.06em; margin-top:2px; }}

    .vix-badge-low  {{ display:inline-block; padding:3px 10px; border-radius:20px; background:#d1fae5; color:#065f46; font-weight:700; font-size:0.82rem; }}
    .vix-badge-mid  {{ display:inline-block; padding:3px 10px; border-radius:20px; background:#fef3c7; color:#92400e; font-weight:700; font-size:0.82rem; }}
    .vix-badge-high {{ display:inline-block; padding:3px 10px; border-radius:20px; background:#fee2e2; color:#991b1b; font-weight:700; font-size:0.82rem; }}

    .nifty-green {{ color:#16a34a; font-weight:700; }}
    .nifty-red   {{ color:#dc2626; font-weight:700; }}

    .daily-limit-banner  {{ background:#fef2f2; border:2px solid #fca5a5; border-radius:10px; padding:14px 18px; text-align:center; color:#991b1b; font-weight:700; font-size:1rem; }}
    .daily-profit-banner {{ background:#f0fdf4; border:2px solid #86efac; border-radius:10px; padding:14px 18px; text-align:center; color:#166534; font-weight:700; font-size:1rem; }}

    .regime-badge-trend   {{ display:inline-block; padding:3px 12px; border-radius:20px; background:#dbeafe; color:#1e40af; font-weight:700; font-size:0.82rem; }}
    .regime-badge-range   {{ display:inline-block; padding:3px 12px; border-radius:20px; background:#fef3c7; color:#92400e; font-weight:700; font-size:0.82rem; }}
    .regime-badge-volatile{{ display:inline-block; padding:3px 12px; border-radius:20px; background:#fee2e2; color:#991b1b; font-weight:700; font-size:0.82rem; }}

    .ctx-bar {{ background:var(--bg-card); border:1px solid var(--bdr); border-radius:10px; padding:10px 18px; margin:8px 0; display:flex; gap:24px; align-items:center; font-size:0.9rem; flex-wrap:wrap; }}

    .stSidebar {{ background:var(--bg-card) !important; }}
    .stSidebar [data-testid="stSidebarContent"] {{ background:var(--bg-card) !important; }}
</style>
""", unsafe_allow_html=True)

# ================================
# SOUND ALERT JS
# ================================
SOUND_JS = """
<script>
function playSignalBeep() {
    try {
        var ctx = new (window.AudioContext || window.webkitAudioContext)();
        function beep(freq, start, duration, vol) {
            var o = ctx.createOscillator();
            var g = ctx.createGain();
            o.connect(g); g.connect(ctx.destination);
            o.type = 'sine'; o.frequency.value = freq;
            g.gain.setValueAtTime(vol || 0.3, ctx.currentTime + start);
            g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + start + duration);
            o.start(ctx.currentTime + start);
            o.stop(ctx.currentTime + start + duration + 0.1);
        }
        beep(880, 0, 0.15, 0.4);
        beep(1100, 0.18, 0.15, 0.35);
        beep(1320, 0.36, 0.25, 0.3);
    } catch(e) {}
}
window._orbSignalCount = window._orbSignalCount || 0;
function checkAndBeep(newCount) {
    if (newCount > window._orbSignalCount) {
        playSignalBeep();
        window._orbSignalCount = newCount;
    }
}
</script>
"""
st.components.v1.html(SOUND_JS, height=0)

# ================================
# PRESETS
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
        "ABB.NS","ADANIGREEN.NS","AMBUJACEM.NS","AUROPHARMA.NS","BALKRISIND.NS",
        "BANDHANBNK.NS","BANKBARODA.NS","BERGEPAINT.NS","BOSCHLTD.NS","CANBK.NS",
        "CHOLAFIN.NS","COLPAL.NS","CONCOR.NS","DABUR.NS","DLF.NS",
        "DMART.NS","FEDERALBNK.NS","GAIL.NS","GODREJCP.NS","HAVELLS.NS",
        "HDFCAMC.NS","HINDPETRO.NS","ICICIPRULI.NS","IDFCFIRSTB.NS","IGL.NS",
        "INDIGO.NS","INDUSTOWER.NS","IRCTC.NS","JUBLFOOD.NS","LICI.NS",
        "LODHA.NS","LUPIN.NS","MFSL.NS","MPHASIS.NS","MUTHOOTFIN.NS",
        "NAUKRI.NS","NMDC.NS","OFSS.NS","PAGEIND.NS","PERSISTENT.NS",
        "PIIND.NS","PNB.NS","RECLTD.NS","SAIL.NS","SIEMENS.NS",
        "TATAPOWER.NS","TORNTPHARM.NS","VEDL.NS",
    ],
    "Bank Nifty": [
        "HDFCBANK.NS","ICICIBANK.NS","KOTAKBANK.NS","AXISBANK.NS","SBIN.NS",
        "INDUSINDBK.NS","BANDHANBNK.NS","FEDERALBNK.NS","IDFCFIRSTB.NS","PNB.NS",
        "BANKBARODA.NS","CANBK.NS","UNIONBANK.NS","INDIANB.NS","IOB.NS",
        "UCO.NS","KARURVYSYA.NS","DCBBANK.NS","RBLBANK.NS",
    ],
    "IT Sector": [
        "TCS.NS","INFOSYS.NS","WIPRO.NS","HCLTECH.NS","TECHM.NS",
        "MPHASIS.NS","LTTS.NS","PERSISTENT.NS","COFORGE.NS","OFSS.NS",
        "KPITTECH.NS","SONATSOFTW.NS","MASTEK.NS","BIRLASOFT.NS",
    ],
    "Pharma Sector": [
        "SUNPHARMA.NS","DRREDDY.NS","CIPLA.NS","DIVISLAB.NS","LUPIN.NS",
        "APOLLOHOSP.NS","AUROPHARMA.NS","TORNTPHARM.NS","GLENMARK.NS","BIOCON.NS",
        "ALKEM.NS","IPCALAB.NS","NATCOPHARM.NS","GRANULES.NS","LAURUSLABS.NS",
    ],
    "Auto Sector": [
        "MARUTI.NS","TATAMOTORS.NS","BAJAJ-AUTO.NS","HEROMOTOCO.NS","EICHERMOT.NS",
        "M&M.NS","ASHOKLEY.NS","ESCORTS.NS","MOTHERSON.NS","BHARATFORG.NS",
        "BALKRISIND.NS","APOLLOTYRE.NS","CEAT.NS","EXIDEIND.NS",
    ],
    "Custom (Enter Below)": [],
}

SECTOR_MAP = {
    "TCS.NS":"IT","INFOSYS.NS":"IT","WIPRO.NS":"IT","HCLTECH.NS":"IT","TECHM.NS":"IT",
    "MPHASIS.NS":"IT","LTTS.NS":"IT","PERSISTENT.NS":"IT","COFORGE.NS":"IT","OFSS.NS":"IT",
    "HDFCBANK.NS":"Bank","ICICIBANK.NS":"Bank","KOTAKBANK.NS":"Bank","AXISBANK.NS":"Bank","SBIN.NS":"Bank",
    "INDUSINDBK.NS":"Bank","BANDHANBNK.NS":"Bank","FEDERALBNK.NS":"Bank","PNB.NS":"Bank","BANKBARODA.NS":"Bank",
    "SUNPHARMA.NS":"Pharma","DRREDDY.NS":"Pharma","CIPLA.NS":"Pharma","DIVISLAB.NS":"Pharma","LUPIN.NS":"Pharma",
    "APOLLOHOSP.NS":"Pharma","AUROPHARMA.NS":"Pharma","TORNTPHARM.NS":"Pharma","GLENMARK.NS":"Pharma",
    "MARUTI.NS":"Auto","TATAMOTORS.NS":"Auto","BAJAJ-AUTO.NS":"Auto","HEROMOTOCO.NS":"Auto","EICHERMOT.NS":"Auto",
    "M&M.NS":"Auto","ASHOKLEY.NS":"Auto","MOTHERSON.NS":"Auto",
    "RELIANCE.NS":"Energy","ONGC.NS":"Energy","BPCL.NS":"Energy","IOC.NS":"Energy","NTPC.NS":"Energy","POWERGRID.NS":"Energy",
    "TATASTEEL.NS":"Metals","JSWSTEEL.NS":"Metals","HINDALCO.NS":"Metals","SAIL.NS":"Metals","COALINDIA.NS":"Metals",
    "ASIANPAINT.NS":"FMCG","TITAN.NS":"FMCG","NESTLEIND.NS":"FMCG","BRITANNIA.NS":"FMCG","MARICO.NS":"FMCG",
    "ADANIENT.NS":"Conglomerate","ADANIPORTS.NS":"Conglomerate","ADANIGREEN.NS":"Conglomerate",
    "LT.NS":"Infra","ULTRACEMCO.NS":"Infra","DLF.NS":"Infra",
}

PERSISTENCE_FILE = "orb_session.json"
WATCHLIST_FILE   = "orb_watchlist.json"

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
        "last_signal_count": 0,
        "daily_pnl": 0.0,
        "trading_locked": False,
        "lock_reason": "",
        "nifty_trend": None,
        "vix_value": None,
        "backtest_results": None,
        "trade_notes": {},
        # CRITICAL: signal deduplication
        "signal_state": {},
        # CRITICAL: in-memory TTL cache — {cache_key: {"df": ..., "ts": float}}
        # NOTE: only accessed on main thread; threads receive a snapshot copy
        "fetch_cache": {},
        # Market regime
        "market_regime": "Unknown",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ================================
# SESSION PERSISTENCE
# ================================
def save_session():
    try:
        data = {
            "capital":        st.session_state.capital,
            "initial_capital": st.session_state.initial_capital,
            "active_trades":  st.session_state.active_trades,
            "closed_trades":  st.session_state.closed_trades,
            "daily_pnl":      st.session_state.daily_pnl,
            "trading_locked": st.session_state.trading_locked,
            "lock_reason":    st.session_state.lock_reason,
            "equity":         [{"time": str(e["time"]), "capital": e["capital"]} for e in st.session_state.equity],
            "signal_state":   st.session_state.signal_state,
        }
        with open(PERSISTENCE_FILE, "w") as f:
            json.dump(data, f, default=str)
    except Exception:
        pass

def load_session():
    if not os.path.exists(PERSISTENCE_FILE):
        return
    try:
        with open(PERSISTENCE_FILE) as f:
            data = json.load(f)
        if not st.session_state.closed_trades and not st.session_state.active_trades:
            st.session_state.capital         = data.get("capital", 100_000)
            st.session_state.initial_capital = data.get("initial_capital", 100_000)
            st.session_state.active_trades   = data.get("active_trades", {})
            st.session_state.closed_trades   = data.get("closed_trades", [])
            st.session_state.daily_pnl       = data.get("daily_pnl", 0.0)
            st.session_state.trading_locked  = data.get("trading_locked", False)
            st.session_state.lock_reason     = data.get("lock_reason", "")
            st.session_state.signal_state    = data.get("signal_state", {})
            raw_eq = data.get("equity", [])
            st.session_state.equity = [{"time": pd.to_datetime(e["time"]), "capital": e["capital"]} for e in raw_eq]
    except Exception:
        pass

load_session()

# ================================
# WATCHLIST PERSISTENCE
# ================================
def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_watchlist(data: dict):
    try:
        with open(WATCHLIST_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

saved_watchlist = load_watchlist()

# ================================
# SIDEBAR
# ================================
with st.sidebar:
    st.markdown("## ⚙️ Scanner Settings")

    dm_col1, dm_col2 = st.columns([3, 1])
    with dm_col1:
        st.markdown("🌙 **Dark Mode**")
    with dm_col2:
        if st.button("Toggle", key="dm_toggle"):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()

    st.markdown("### 📋 Symbol Selection")
    preset_choice = st.selectbox("Choose Preset", list(PRESETS.keys()), index=0)

    if preset_choice == "Custom (Enter Below)":
        custom_raw = st.text_area(
            "Enter tickers (one per line or comma-separated)",
            placeholder="RELIANCE\nTCS\nINFY",
            height=80
        )
        raw_list = [
            s.strip().upper()
            for part in custom_raw.replace(",", "\n").splitlines()
            for s in [part.strip()] if s.strip()
        ]
        symbols_pool = [
            s if s.endswith(".NS") or s.endswith(".BO") else s + ".NS"
            for s in raw_list if s
        ]
    else:
        symbols_pool = PRESETS[preset_choice]

    st.markdown("##### 📂 Import CSV Watchlist")
    uploaded_csv = st.file_uploader("Drag & drop CSV with 'Symbol' column", type=["csv"], key="csv_wl")
    csv_symbols = []
    if uploaded_csv:
        try:
            df_csv = pd.read_csv(uploaded_csv)
            col = next((c for c in df_csv.columns if "symbol" in c.lower()), df_csv.columns[0])
            csv_syms_raw = df_csv[col].dropna().astype(str).str.strip().str.upper().tolist()
            csv_symbols = [s if s.endswith(".NS") or s.endswith(".BO") else s + ".NS" for s in csv_syms_raw if s]
            st.success(f"✅ Loaded {len(csv_symbols)} symbols from CSV")
        except Exception as e:
            st.error(f"CSV error: {e}")

    if csv_symbols:
        symbols_pool = list(dict.fromkeys(symbols_pool + csv_symbols))

    default_saved = saved_watchlist.get(preset_choice, [])
    if default_saved and all(d in symbols_pool for d in default_saved):
        default_sel = default_saved
    else:
        default_sel = symbols_pool[:15] if len(symbols_pool) > 15 else symbols_pool

    if symbols_pool:
        selected_symbols = st.multiselect(
            f"Select symbols ({len(symbols_pool)} available)",
            options=symbols_pool,
            default=default_sel,
        )
    else:
        selected_symbols = []

    if selected_symbols != saved_watchlist.get(preset_choice, []):
        saved_watchlist[preset_choice] = selected_symbols
        save_watchlist(saved_watchlist)
        st.caption("💾 Watchlist saved")

    extra_raw = st.text_input("➕ Extra tickers (comma-separated)", placeholder="ZOMATO,PAYTM")
    if extra_raw.strip():
        extras = [
            s.strip().upper() + ("" if s.strip().upper().endswith(".NS") else ".NS")
            for s in extra_raw.split(",") if s.strip()
        ]
        selected_symbols = list(dict.fromkeys(selected_symbols + extras))

    st.caption(f"**{len(selected_symbols)}** symbols selected")

    st.divider()
    st.markdown("### 📐 Strategy Parameters")
    orb_minutes    = st.number_input("ORB Minutes", 5, 60, 15)
    ema_period     = st.number_input("EMA Period (5m)", 5, 100, 20)
    ema_15m_period = st.number_input("EMA Period (15m MTF)", 5, 100, 20)
    ema_1h_period  = st.number_input("EMA Period (1h 3TF)", 5, 50, 20)
    atr_period     = st.number_input("ATR Period", 5, 30, 14)
    rsi_period     = st.number_input("RSI Period", 5, 30, 14)
    st_atr_mult    = st.slider("Supertrend ATR Multiplier", 1.0, 5.0, 3.0, 0.5)

    st.divider()
    st.markdown("### 🛡️ Stop Loss Strategy")
    sl_strategy = st.selectbox(
        "SL Method",
        ["Supertrend", "Chandelier Exit", "Fixed ATR", "Swing High/Low", "Fixed %"],
    )
    sl_atr_mult    = st.slider("SL ATR Multiplier (Chandelier/Fixed ATR)", 1.0, 5.0, 2.0, 0.25)
    swing_lookback = st.number_input("Swing Lookback Bars", 3, 20, 5)
    trail_pct      = st.slider("Trail % (Fixed % fallback)", 0.1, 2.0, 0.5, 0.05) / 100

    st.divider()
    st.markdown("### 💰 Risk Management")
    initial_capital = st.number_input("Initial Capital (₹)", 10_000, 10_000_000, 100_000, step=10_000)
    if st.button("🔁 Reset Capital"):
        st.session_state.capital         = initial_capital
        st.session_state.initial_capital = initial_capital
        st.session_state.active_trades   = {}
        st.session_state.closed_trades   = []
        st.session_state.equity          = []
        st.session_state.daily_pnl       = 0.0
        st.session_state.trading_locked  = False
        st.session_state.lock_reason     = ""
        st.session_state.signal_state    = {}
        save_session()
        st.rerun()

    risk_pct     = st.slider("Risk per Trade (%)", 0.5, 3.0, 1.0, 0.1)
    max_trades   = st.number_input("Max Concurrent Trades", 1, 30, 5)
    max_risk_pct = st.slider("Max Portfolio Risk (%)", 1.0, 10.0, 5.0, 0.5)

    st.divider()
    st.markdown("### 📅 Daily P&L Limits")
    daily_loss_limit_pct    = st.slider("Daily Loss Limit (%)", 0.5, 10.0, 3.0, 0.5)
    daily_profit_target_pct = st.slider("Daily Profit Target (%)", 1.0, 20.0, 5.0, 0.5)

    st.divider()
    st.markdown("### 🔍 Signal Filters")
    min_vol_ratio  = st.slider("Min Volume Ratio", 1.0, 5.0, 1.8, 0.1)
    min_body_pct   = st.slider("Min Candle Body %", 0.3, 0.9, 0.6, 0.05)
    min_ema_dist   = st.slider("Min EMA Distance %", 0.1, 2.0, 0.5, 0.1) / 100
    max_ema_dist   = st.slider("Max EMA Distance %", 0.5, 5.0, 2.0, 0.1) / 100
    min_atr_ratio  = st.slider("Min ATR Ratio %", 0.1, 1.0, 0.3, 0.05) / 100
    rsi_buy_min    = st.slider("RSI Min for BUY", 40, 70, 55)
    rsi_sell_max   = st.slider("RSI Max for SELL", 30, 60, 45)
    use_mtf        = st.checkbox("15m EMA Confirmation (MTF)", True)
    use_3tf        = st.checkbox("1h EMA Confluence (3-Timeframe)", True)
    use_macd       = st.checkbox("MACD Filter", True)
    use_regime     = st.checkbox("Market Regime Filter (ADX)", True)
    use_nifty_filter = st.checkbox("Nifty Index Filter", True)
    use_vix_sizing = st.checkbox("VIX-Based Position Sizing", True)
    use_gap_detect = st.checkbox("Gap Detection", True)
    gap_pct        = st.slider("Gap Threshold (%)", 0.5, 3.0, 1.0, 0.1) / 100
    use_corr_filter= st.checkbox("Correlation Filter (same sector, r>0.8)", False)

    st.divider()
    st.markdown("### 📦 Partial Profit")
    use_partial = st.checkbox("Partial Profit Booking (50% @ 1×ATR)", True)

    st.divider()
    st.markdown("### 📡 Alert Channels")
    with st.expander("📱 Telegram"):
        tg_token   = st.text_input("Bot Token", type="password", placeholder="5XXXXXX:AAF...")
        tg_chat_id = st.text_input("Chat ID", placeholder="-100XXXXXXXXXX")
        send_tg    = st.checkbox("Enable Telegram", False)
    with st.expander("🎮 Discord"):
        discord_webhook = st.text_input("Discord Webhook URL", type="password")
        send_discord    = st.checkbox("Enable Discord", False)
    with st.expander("📧 Email (SMTP)"):
        smtp_host = st.text_input("SMTP Host", placeholder="smtp.gmail.com")
        smtp_port = st.number_input("SMTP Port", 1, 65535, 587)
        smtp_user = st.text_input("SMTP Username")
        smtp_pass = st.text_input("SMTP Password", type="password")
        smtp_to   = st.text_input("Recipient Email")
        send_email= st.checkbox("Enable Email", False)
    with st.expander("💬 WhatsApp (Twilio)"):
        twilio_sid   = st.text_input("Twilio Account SID", type="password")
        twilio_token = st.text_input("Twilio Auth Token", type="password")
        twilio_from  = st.text_input("From (whatsapp:+14155238886)", placeholder="whatsapp:+14155238886")
        twilio_to    = st.text_input("To (whatsapp:+91XXXXXXXXXX)", placeholder="whatsapp:+91XXXXXXXXXX")
        send_whatsapp= st.checkbox("Enable WhatsApp", False)

    st.divider()
    st.markdown("### 🗄️ Cache Settings")
    cache_ttl_5m  = st.number_input("5m Cache TTL (seconds)", 10, 300, 25)
    cache_ttl_15m = st.number_input("15m Cache TTL (seconds)", 30, 600, 60)
    cache_ttl_1h  = st.number_input("1h Cache TTL (seconds)", 60, 1800, 300)
    max_retries   = st.number_input("Max Fetch Retries", 1, 5, 3)
    show_errors   = st.checkbox("Show fetch errors", False)


# ================================
# MULTI-CHANNEL ALERT DISPATCHER
# ================================
def send_alert(msg: str, html_msg: str = None):
    if send_tg and tg_token and tg_chat_id:
        try:
            url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
            requests.post(url, data={"chat_id": tg_chat_id, "text": html_msg or msg, "parse_mode": "HTML"}, timeout=5)
        except Exception:
            pass
    if send_discord and discord_webhook:
        try:
            requests.post(discord_webhook, json={"content": msg}, timeout=5)
        except Exception:
            pass
    if send_email and smtp_host and smtp_user and smtp_to:
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = "ORB Signal Alert"
            message["From"]    = smtp_user
            message["To"]      = smtp_to
            message.attach(MIMEText(msg, "plain"))
            with smtplib.SMTP(smtp_host, int(smtp_port), timeout=10) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, smtp_to, message.as_string())
        except Exception:
            pass
    if send_whatsapp and twilio_sid and twilio_token and twilio_from and twilio_to:
        try:
            requests.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json",
                auth=(twilio_sid, twilio_token),
                data={"From": twilio_from, "To": twilio_to, "Body": msg},
                timeout=10,
            )
        except Exception:
            pass


# ================================
# CACHE HELPERS  (main-thread only)
# ================================
def _cache_ttl(interval: str) -> int:
    return {
        "5m":  int(cache_ttl_5m),
        "15m": int(cache_ttl_15m),
        "1h":  int(cache_ttl_1h),
        "1d":  300,
    }.get(interval, 60)

def _cache_key(symbol: str, interval: str) -> str:
    return f"{symbol}_{interval}"

def cache_get(symbol: str, interval: str):
    """Read from session_state cache — MAIN THREAD ONLY."""
    key   = _cache_key(symbol, interval)
    entry = st.session_state.fetch_cache.get(key)
    if entry and (time.time() - entry["ts"]) < _cache_ttl(interval):
        return entry["df"]
    return None

def cache_set(symbol: str, interval: str, df):
    """Write to session_state cache — MAIN THREAD ONLY."""
    key = _cache_key(symbol, interval)
    st.session_state.fetch_cache[key] = {"df": df, "ts": time.time()}

def cache_invalidate_expired():
    """Prune stale entries — MAIN THREAD ONLY."""
    now     = time.time()
    expired = [k for k, v in st.session_state.fetch_cache.items() if (now - v["ts"]) > 3600]
    for k in expired:
        del st.session_state.fetch_cache[k]

def snapshot_cache() -> dict:
    """
    Return a plain-dict snapshot of the current cache for passing into threads.
    Threads receive this dict (no session_state access needed).
    """
    return dict(st.session_state.fetch_cache)


# ================================
# CORE FETCH — THREAD-SAFE
# fetch() now receives `_cache_snapshot` (plain dict) instead of touching
# st.session_state.  The main thread applies cache_set() after threads return.
# ================================
def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex):
        lvl1 = df.columns.get_level_values(1).unique().tolist()
        if len(lvl1) <= 1:
            df.columns = df.columns.get_level_values(0)
        else:
            ticker_col = lvl1[0]
            df = df.xs(ticker_col, axis=1, level=1)
    df.columns = [str(c).strip().title() for c in df.columns]
    rename_map = {"Adj Close": "Close", "Adj_Close": "Close", "Adjclose": "Close", "Adj close": "Close"}
    df.rename(columns=rename_map, inplace=True)
    return df


def fetch(
    symbol: str,
    interval: str = "5m",
    period: str = "5d",
    use_cache: bool = True,
    _cache_snapshot: dict = None,   # ← NEW: plain dict passed from main thread
) -> tuple:
    """
    Fetch OHLCV with TTL cache, exponential backoff + jitter on retry.
    Thread-safe: reads/writes only the plain `_cache_snapshot` dict,
    never touches st.session_state.
    Returns (symbol, df, error_str_or_None, updated_cache_entry_or_None)
    The caller (main thread) is responsible for writing new entries to session_state.
    """
    required_cols = {"Open", "High", "Low", "Close", "Volume"}
    min_bars = 10

    if _cache_snapshot is None:
        _cache_snapshot = {}

    # Check snapshot for a fresh entry
    if use_cache:
        key   = _cache_key(symbol, interval)
        entry = _cache_snapshot.get(key)
        if entry and (time.time() - entry["ts"]) < _cache_ttl(interval):
            return symbol, entry["df"], None, None   # None → no new write needed

    strategies = [
        {"interval": interval, "period": period},
        {"interval": interval, "period": "5d"},
        {"interval": interval, "period": "1mo"},
    ]
    if interval == "1d":
        strategies = [{"interval": "1d", "period": "5d"}]
    if interval == "1h":
        strategies = [{"interval": "1h", "period": "5d"}, {"interval": "1h", "period": "1mo"}]

    last_err = "Unknown error"
    for attempt in range(int(max_retries)):
        for strat in strategies:
            try:
                raw = yf.download(
                    symbol,
                    interval=strat["interval"],
                    period=strat["period"],
                    progress=False,
                    auto_adjust=True,
                    actions=False,
                )
                if raw is None or raw.empty:
                    last_err = f"Empty response (interval={strat['interval']}, period={strat['period']})"
                    continue

                df = _flatten_columns(raw.copy())
                missing = required_cols - set(df.columns)
                if missing:
                    last_err = f"Missing columns: {missing}"
                    continue

                df.dropna(subset=["Open", "High", "Low", "Close"], how="all", inplace=True)
                if len(df) < min_bars:
                    last_err = f"Too few bars: {len(df)}"
                    continue

                if not isinstance(df.index, pd.DatetimeIndex):
                    df.index = pd.to_datetime(df.index)
                if df.index.tz is not None:
                    df.index = df.index.tz_convert("Asia/Kolkata").tz_localize(None)

                df.sort_index(inplace=True)
                # Return df + new cache entry; main thread writes to session_state
                new_entry = {"df": df, "ts": time.time()}
                return symbol, df, None, (_cache_key(symbol, interval), new_entry)

            except Exception as e:
                last_err = f"{type(e).__name__}: {str(e)[:120]}"
                continue

        if attempt < int(max_retries) - 1:
            wait = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait)

    return symbol, None, last_err, None


def _apply_cache_write(result_tuple):
    """Main-thread helper: write new cache entry returned by fetch() into session_state."""
    cache_write = result_tuple[3] if len(result_tuple) == 4 else None
    if cache_write:
        key, entry = cache_write
        st.session_state.fetch_cache[key] = entry


# ================================
# MARKET CONTEXT
# ================================
@st.cache_data(ttl=120)
def fetch_nifty_vix():
    result = {"nifty_change": 0.0, "nifty_price": 0.0, "vix": 0.0}
    try:
        sym, nifty, err, _ = fetch("^NSEI", interval="1d", period="5d", use_cache=False, _cache_snapshot={})
        if nifty is not None and len(nifty) >= 2:
            result["nifty_price"]  = float(nifty["Close"].iloc[-1])
            result["nifty_change"] = float(nifty["Close"].iloc[-1] - nifty["Close"].iloc[-2])
    except Exception:
        pass
    try:
        sym, vix, err, _ = fetch("^INDIAVIX", interval="1d", period="5d", use_cache=False, _cache_snapshot={})
        if vix is not None and not vix.empty:
            result["vix"] = float(vix["Close"].iloc[-1])
    except Exception:
        pass
    return result

mkt_ctx = fetch_nifty_vix()
st.session_state.nifty_trend = mkt_ctx["nifty_change"]
st.session_state.vix_value   = mkt_ctx["vix"]


# ================================
# MARKET REGIME DETECTOR
# ================================
def detect_market_regime(df: pd.DataFrame) -> str:
    if df is None or len(df) < 20:
        return "Unknown"
    try:
        high  = df["High"]
        low   = df["Low"]
        close = df["Close"]

        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low  - close.shift(1)).abs(),
        ], axis=1).max(axis=1)
        atr14 = tr.rolling(14, min_periods=1).mean()

        dm_plus  = (high.diff()).clip(lower=0)
        dm_minus = (-low.diff()).clip(lower=0)
        dm_plus_arr  = np.where(dm_plus > dm_minus, dm_plus, 0)
        dm_minus_arr = np.where(pd.Series(dm_minus) > pd.Series(dm_plus), dm_minus, 0)

        smooth_plus  = pd.Series(dm_plus_arr).rolling(14, min_periods=1).mean()
        smooth_minus = pd.Series(dm_minus_arr).rolling(14, min_periods=1).mean()

        di_plus  = 100 * smooth_plus  / atr14.replace(0, np.nan).fillna(1)
        di_minus = 100 * smooth_minus / atr14.replace(0, np.nan).fillna(1)
        dx       = 100 * (di_plus - di_minus).abs() / (di_plus + di_minus).replace(0, np.nan).fillna(1)
        adx      = dx.rolling(14, min_periods=1).mean().iloc[-1]

        sma20    = close.rolling(20, min_periods=5).mean()
        std20    = close.rolling(20, min_periods=5).std()
        bb_width = (2 * std20 / sma20.replace(0, np.nan).fillna(1)).iloc[-1]

        if adx > 25:
            return "Trending"
        elif bb_width > 0.04:
            return "Volatile"
        else:
            return "Ranging"
    except Exception:
        return "Unknown"


# ================================
# INDICATORS
# ================================
def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df    = df.copy()
    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]
    vol   = df["Volume"]

    df["EMA"] = close.ewm(span=ema_period, adjust=False).mean()

    prev_close = close.shift(1)
    df["TR"]   = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)
    df["ATR"]  = df["TR"].rolling(atr_period, min_periods=1).mean()
    df["Vol_Avg"] = vol.rolling(20, min_periods=5).mean()

    body         = (close - df["Open"]).abs()
    rng          = (high - low).replace(0, np.nan).fillna(1e-9)
    df["BodyPct"] = (body / rng).clip(0, 1)

    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    avg_g = gain.ewm(com=rsi_period - 1, adjust=False).mean()
    avg_l = loss.ewm(com=rsi_period - 1, adjust=False).mean()
    rs    = avg_g / avg_l.replace(0, np.nan).fillna(1e-9)
    df["RSI"] = 100 - (100 / (1 + rs))

    ema12           = close.ewm(span=12, adjust=False).mean()
    ema26           = close.ewm(span=26, adjust=False).mean()
    df["MACD"]      = ema12 - ema26
    df["MACD_sig"]  = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_sig"]

    # Supertrend
    hl2 = (high + low) / 2
    atr  = df["ATR"]
    upper_band = hl2 + st_atr_mult * atr
    lower_band = hl2 - st_atr_mult * atr

    st_dir = np.ones(len(df), dtype=int)
    st_val = np.zeros(len(df))
    ub     = upper_band.values.copy()
    lb     = lower_band.values.copy()
    cl     = close.values

    for i in range(1, len(df)):
        if cl[i - 1] <= ub[i - 1]:
            ub[i] = min(ub[i], ub[i - 1])
        if cl[i - 1] >= lb[i - 1]:
            lb[i] = max(lb[i], lb[i - 1])
        if st_dir[i - 1] == -1 and cl[i] > ub[i]:
            st_dir[i] = 1
        elif st_dir[i - 1] == 1 and cl[i] < lb[i]:
            st_dir[i] = -1
        else:
            st_dir[i] = st_dir[i - 1]
        st_val[i] = lb[i] if st_dir[i] == 1 else ub[i]

    df["ST_upper"] = ub
    df["ST_lower"] = lb
    df["ST_dir"]   = st_dir
    df["ST_val"]   = st_val
    return df


def add_indicators_15m(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["EMA15"] = df["Close"].ewm(span=ema_15m_period, adjust=False).mean()
    return df


def add_indicators_1h(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["EMA1H"] = df["Close"].ewm(span=ema_1h_period, adjust=False).mean()
    return df


# ================================
# SL STRATEGIES
# ================================
def compute_sl(df, direction, entry_price, orb_low, orb_high):
    atr = float(df["ATR"].iloc[-1]) if "ATR" in df.columns else 0
    n   = int(swing_lookback)

    if sl_strategy == "Supertrend":
        if "ST_val" in df.columns:
            return float(df["ST_val"].iloc[-1])
        return orb_low if direction == "BUY" else orb_high

    elif sl_strategy == "Chandelier Exit":
        if direction == "BUY":
            return round(float(df["High"].rolling(n, min_periods=1).max().iloc[-1]) - sl_atr_mult * atr, 2)
        else:
            return round(float(df["Low"].rolling(n, min_periods=1).min().iloc[-1]) + sl_atr_mult * atr, 2)

    elif sl_strategy == "Fixed ATR":
        return round(entry_price - sl_atr_mult * atr, 2) if direction == "BUY" else round(entry_price + sl_atr_mult * atr, 2)

    elif sl_strategy == "Swing High/Low":
        if direction == "BUY":
            return round(float(df["Low"].rolling(n, min_periods=1).min().iloc[-1]) - 0.1 * atr, 2)
        else:
            return round(float(df["High"].rolling(n, min_periods=1).max().iloc[-1]) + 0.1 * atr, 2)

    elif sl_strategy == "Fixed %":
        return round(entry_price * (1 - trail_pct), 2) if direction == "BUY" else round(entry_price * (1 + trail_pct), 2)

    return orb_low if direction == "BUY" else orb_high


def update_sl(df, trade, current_price):
    direction  = trade["type"]
    current_sl = trade["sl"]
    n = int(swing_lookback)
    atr = float(df["ATR"].iloc[-1]) if "ATR" in df.columns else 0

    if sl_strategy == "Supertrend" and "ST_val" in df.columns:
        new_sl = float(df["ST_val"].iloc[-1])
    elif sl_strategy == "Chandelier Exit":
        if direction == "BUY":
            new_sl = float(df["High"].rolling(n, min_periods=1).max().iloc[-1]) - sl_atr_mult * atr
        else:
            new_sl = float(df["Low"].rolling(n, min_periods=1).min().iloc[-1]) + sl_atr_mult * atr
    elif sl_strategy == "Fixed ATR":
        new_sl = current_price - sl_atr_mult * atr if direction == "BUY" else current_price + sl_atr_mult * atr
    elif sl_strategy == "Swing High/Low":
        if direction == "BUY":
            new_sl = float(df["Low"].rolling(n, min_periods=1).min().iloc[-1]) - 0.1 * atr
        else:
            new_sl = float(df["High"].rolling(n, min_periods=1).max().iloc[-1]) + 0.1 * atr
    elif sl_strategy == "Fixed %":
        new_sl = current_price * (1 - trail_pct) if direction == "BUY" else current_price * (1 + trail_pct)
    else:
        new_sl = current_sl

    return round(max(current_sl, new_sl), 2) if direction == "BUY" else round(min(current_sl, new_sl), 2)


# ================================
# SIGNAL FILTERS
# ================================
def breakout_confirmed(df, level, direction):
    if len(df) < 2:
        return False
    last = float(df["Close"].iloc[-1])
    prev = float(df["Close"].iloc[-2])
    return (prev > level and last > level) if direction == "BUY" else (prev < level and last < level)

def check_rsi(df, direction):
    rsi = df["RSI"].iloc[-1]
    if pd.isna(rsi):
        return True, 50.0
    rsi = float(rsi)
    if direction == "BUY":
        return rsi > rsi_buy_min, round(rsi, 1)
    return rsi < rsi_sell_max, round(rsi, 1)

def check_macd(df, direction):
    hist = df["MACD_hist"].iloc[-1]
    if pd.isna(hist):
        return True
    return float(hist) > 0 if direction == "BUY" else float(hist) < 0

def check_volume(df):
    vol     = float(df["Volume"].iloc[-1])
    vol_avg = df["Vol_Avg"].iloc[-1]
    if pd.isna(vol_avg) or vol_avg == 0:
        return False, 0.0
    ratio = vol / float(vol_avg)
    return ratio >= min_vol_ratio, round(ratio, 2)

def check_ema_dist(df):
    price = float(df["Close"].iloc[-1])
    ema   = float(df["EMA"].iloc[-1])
    if ema == 0 or pd.isna(ema):
        return False
    dist = abs(price - ema) / ema
    return min_ema_dist <= dist <= max_ema_dist

def check_atr(df):
    atr   = df["ATR"].iloc[-1]
    close = df["Close"].iloc[-1]
    if pd.isna(atr) or pd.isna(close) or float(close) == 0:
        return False
    return (float(atr) / float(close)) > min_atr_ratio

def check_gap(df_5m):
    try:
        df_5m = df_5m.copy()
        df_5m.index = pd.to_datetime(df_5m.index)
        dates = df_5m.index.normalize().unique()
        if len(dates) < 2:
            return 0.0
        today     = dates[-1]
        yesterday = dates[-2]
        today_open = float(df_5m[df_5m.index.normalize() == today]["Open"].iloc[0])
        yest_close = float(df_5m[df_5m.index.normalize() == yesterday]["Close"].iloc[-1])
        if yest_close == 0:
            return 0.0
        return (today_open - yest_close) / yest_close
    except Exception:
        return 0.0

def signal_score(vol_ratio, atr_ratio, body_pct, rsi_val, direction, mtf_ok, tf3_ok):
    score = 0
    if vol_ratio >= 3.0:            score += 1
    elif vol_ratio >= 2.0:          score += 0.7
    elif vol_ratio >= min_vol_ratio: score += 0.4
    if atr_ratio >= min_atr_ratio * 2: score += 1
    elif atr_ratio >= min_atr_ratio:   score += 0.6
    if body_pct >= 0.8:    score += 1
    elif body_pct >= 0.65: score += 0.7
    elif body_pct >= min_body_pct: score += 0.4
    if direction == "BUY":
        if rsi_val >= 65:   score += 1
        elif rsi_val >= 55: score += 0.7
        else:               score += 0.3
    else:
        if rsi_val <= 35:   score += 1
        elif rsi_val <= 45: score += 0.7
        else:               score += 0.3
    if mtf_ok: score += 0.3
    if tf3_ok: score += 0.4
    return round(min(score / 4.7 * 5, 5), 1)


# ================================
# SIGNAL DEDUPLICATION  (main-thread)
# ================================
def is_new_breakout(symbol: str, direction: str, level: float) -> bool:
    state      = st.session_state.signal_state.get(symbol, {})
    prev_dir   = state.get("direction")
    prev_level = state.get("level")
    prev_fired = state.get("fired", False)
    if prev_dir != direction or (prev_level and abs(level - prev_level) / max(prev_level, 1) > 0.005):
        st.session_state.signal_state[symbol] = {"direction": direction, "level": level, "fired": True}
        return True
    if prev_fired:
        return False
    st.session_state.signal_state[symbol]["fired"] = True
    return True

def reset_signal_state(symbol: str):
    if symbol in st.session_state.signal_state:
        st.session_state.signal_state[symbol]["fired"] = False


# ================================
# CORRELATION FILTER  (main-thread)
# ================================
def is_correlated_with_active(symbol: str, df: pd.DataFrame) -> bool:
    if not use_corr_filter:
        return False
    sym_sector = SECTOR_MAP.get(symbol, "")
    if not sym_sector:
        return False
    active_same_sector = [
        s for s in st.session_state.active_trades
        if SECTOR_MAP.get(s, "") == sym_sector and s != symbol
    ]
    if not active_same_sector:
        return False
    try:
        close_self = df["Close"].dropna()
        for active_sym in active_same_sector:
            entry = st.session_state.fetch_cache.get(_cache_key(active_sym, "5m"))
            if not entry:
                continue
            close_other = entry["df"]["Close"].dropna()
            aligned = pd.concat([close_self, close_other], axis=1).dropna()
            if len(aligned) < 20:
                continue
            if aligned.iloc[:, 0].corr(aligned.iloc[:, 1]) > 0.8:
                return True
    except Exception:
        pass
    return False


# ================================
# ORB RANGE HELPER
# ================================
def get_orb_range(df: pd.DataFrame):
    df = df.copy()
    df.index = pd.to_datetime(df.index)
    last_date = df.index.normalize().max()
    day_df    = df[df.index.normalize() == last_date].copy()
    day_df["_time"] = day_df.index.time

    market_start = dtime(9, 15)
    orb_end_time = (
        datetime.combine(last_date.date(), market_start)
        + timedelta(minutes=int(orb_minutes))
    ).time()

    orb_df = day_df[day_df["_time"] <= orb_end_time]
    return orb_df, day_df


# ================================
# MAIN SIGNAL GENERATOR  (main-thread)
# ================================
def get_signal(symbol: str, df_5m, df_15m=None, df_1h=None):
    if df_5m is None or len(df_5m) < 10:
        return None, "Insufficient 5m data"

    df = add_indicators(df_5m)
    df.index = pd.to_datetime(df.index)

    orb_df, day_df = get_orb_range(df)
    if len(orb_df) < 2:
        orb_df = df.iloc[:max(2, int(orb_minutes // 5))]
        day_df = df

    orb_high = float(orb_df["High"].max())
    orb_low  = float(orb_df["Low"].min())
    last     = float(df["Close"].iloc[-1])
    atr      = float(df["ATR"].iloc[-1]) if not pd.isna(df["ATR"].iloc[-1]) else 0.0

    if orb_high == orb_low:
        return None, "ORB range is zero"

    if last > orb_high:
        direction, level = "BUY",  orb_high
    elif last < orb_low:
        direction, level = "SELL", orb_low
    else:
        reset_signal_state(symbol)
        return None, "Price inside ORB range"

    if not is_new_breakout(symbol, direction, level):
        return None, f"Signal already fired for {direction} @ {level:.2f}"

    if not breakout_confirmed(df, level, direction):
        st.session_state.signal_state[symbol]["fired"] = False
        return None, "Breakout not confirmed (2-bar rule)"

    body_pct = float(df["BodyPct"].iloc[-1])
    if pd.isna(body_pct) or body_pct < min_body_pct:
        st.session_state.signal_state[symbol]["fired"] = False
        return None, f"Weak candle body ({body_pct:.2f})"

    vol_ok, vol_ratio = check_volume(df)
    if not vol_ok:
        st.session_state.signal_state[symbol]["fired"] = False
        return None, f"Low volume ratio ({vol_ratio}x < {min_vol_ratio}x)"

    if not check_ema_dist(df):
        ema_val  = float(df["EMA"].iloc[-1])
        dist_pct = abs(last - ema_val) / ema_val * 100 if ema_val else 0
        st.session_state.signal_state[symbol]["fired"] = False
        return None, f"EMA distance out of range ({dist_pct:.2f}%)"

    if not check_atr(df):
        st.session_state.signal_state[symbol]["fired"] = False
        return None, "Low ATR (insufficient volatility)"

    rsi_ok, rsi_val = check_rsi(df, direction)
    if not rsi_ok:
        st.session_state.signal_state[symbol]["fired"] = False
        return None, f"RSI filter failed ({rsi_val})"

    if use_macd and not check_macd(df, direction):
        st.session_state.signal_state[symbol]["fired"] = False
        return None, "MACD histogram against direction"

    if use_regime:
        regime = detect_market_regime(df)
        st.session_state.market_regime = regime
        if regime == "Ranging":
            st.session_state.signal_state[symbol]["fired"] = False
            return None, "Market regime is Ranging — ORB suppressed"

    tf3_ok = None
    if use_3tf and df_1h is not None and len(df_1h) >= ema_1h_period + 2:
        df1h = add_indicators_1h(df_1h)
        tf3_rising = float(df1h["EMA1H"].iloc[-1]) > float(df1h["EMA1H"].iloc[-2])
        tf3_ok = tf3_rising
        if direction == "BUY" and not tf3_rising:
            st.session_state.signal_state[symbol]["fired"] = False
            return None, "1h EMA not rising (3TF failed)"
        if direction == "SELL" and tf3_rising:
            st.session_state.signal_state[symbol]["fired"] = False
            return None, "1h EMA not falling (3TF failed)"

    mtf_ema_rising = None
    if use_mtf and df_15m is not None and len(df_15m) >= ema_15m_period + 2:
        df15 = add_indicators_15m(df_15m)
        mtf_ema_rising = float(df15["EMA15"].iloc[-1]) > float(df15["EMA15"].iloc[-2])
        if direction == "BUY" and not mtf_ema_rising:
            st.session_state.signal_state[symbol]["fired"] = False
            return None, "15m EMA not rising (MTF failed)"
        if direction == "SELL" and mtf_ema_rising:
            st.session_state.signal_state[symbol]["fired"] = False
            return None, "15m EMA not falling (MTF failed)"

    if use_nifty_filter:
        nifty_chg = st.session_state.nifty_trend or 0
        if direction == "BUY" and nifty_chg < 0:
            st.session_state.signal_state[symbol]["fired"] = False
            return None, "Nifty is red — BUY skipped"

    if is_correlated_with_active(symbol, df):
        st.session_state.signal_state[symbol]["fired"] = False
        return None, "Correlated with active trade (same sector, r>0.8)"

    gap      = check_gap(df_5m)
    gap_flag = None
    if use_gap_detect and abs(gap) >= gap_pct:
        gap_flag = "GAP_UP" if gap > 0 else "GAP_DOWN"

    sl        = compute_sl(df, direction, last, orb_low, orb_high)
    close     = float(df["Close"].iloc[-1])
    atr_ratio = atr / close if close > 0 else 0
    score     = signal_score(vol_ratio, atr_ratio, body_pct, rsi_val, direction,
                             mtf_ema_rising is True, tf3_ok is True)

    vix        = st.session_state.vix_value or 0
    vix_factor = 0.5 if (use_vix_sizing and vix > 20) else 1.0

    return {
        "direction":     direction,
        "price":         round(last, 2),
        "orb_high":      round(orb_high, 2),
        "orb_low":       round(orb_low, 2),
        "atr":           round(atr, 2),
        "vol_ratio":     vol_ratio,
        "ema":           round(float(df["EMA"].iloc[-1]), 2),
        "rsi":           rsi_val,
        "macd_hist":     round(float(df["MACD_hist"].iloc[-1]), 4),
        "sl":            round(sl, 2),
        "score":         score,
        "gap":           round(gap * 100, 2),
        "gap_flag":      gap_flag,
        "vix_factor":    vix_factor,
        "mtf_confirmed": mtf_ema_rising,
        "tf3_confirmed": tf3_ok,
        "sl_strategy":   sl_strategy,
        "regime":        st.session_state.market_regime,
    }, None


# ================================
# POSITION SIZING
# ================================
def calculate_qty(entry, sl, vix_factor=1.0):
    risk_amount    = st.session_state.capital * (risk_pct / 100) * vix_factor
    risk_per_share = abs(entry - sl)
    if risk_per_share == 0:
        return 0
    return max(1, int(risk_amount / risk_per_share))

def total_risk_deployed():
    return sum(
        abs(t["entry"] - t["sl"]) * t["qty"]
        for t in st.session_state.active_trades.values()
    )


# ================================
# TRADE MANAGEMENT
# ================================
def enter_trade(symbol, signal):
    if st.session_state.trading_locked:
        return
    direction  = signal["direction"]
    price      = signal["price"]
    sl         = signal["sl"]
    atr        = signal["atr"]
    vix_factor = signal.get("vix_factor", 1.0)
    tgt         = price + (2 * atr) if direction == "BUY" else price - (2 * atr)
    tgt_partial = price + (1 * atr) if direction == "BUY" else price - (1 * atr)
    qty         = calculate_qty(price, sl, vix_factor)
    if qty == 0:
        return
    new_risk = abs(price - sl) * qty
    if (total_risk_deployed() + new_risk) / max(st.session_state.capital, 1) > (max_risk_pct / 100):
        return

    st.session_state.active_trades[symbol] = {
        "type":           direction,
        "entry":          price,
        "sl":             round(sl, 2),
        "target":         round(tgt, 2),
        "target_partial": round(tgt_partial, 2),
        "qty":            qty,
        "qty_remaining":  qty,
        "partial_done":   False,
        "breakeven_sl":   False,
        "entry_time":     datetime.now().strftime("%H:%M:%S"),
        "atr":            atr,
        "vol_ratio":      signal["vol_ratio"],
        "score":          signal.get("score", "—"),
        "gap_flag":       signal.get("gap_flag", None),
        "rsi":            signal.get("rsi", "—"),
        "sl_strategy":    signal.get("sl_strategy", sl_strategy),
        "regime":         signal.get("regime", "—"),
        "tf3":            signal.get("tf3_confirmed", None),
    }
    msg = (
        f"🚀 ORB Signal — {symbol}\n"
        f"Direction: {direction}\n"
        f"Entry: ₹{price} | SL: ₹{sl} ({sl_strategy}) | Target: ₹{round(tgt,2)}\n"
        f"Qty: {qty} | Score: {signal.get('score','—')}/5\n"
        f"RSI: {signal.get('rsi','—')} | Vol: {signal['vol_ratio']}x\n"
        f"VIX Factor: {vix_factor} | Regime: {signal.get('regime','—')}"
    )
    html_msg = (
        f"🚀 <b>ORB Signal — {symbol}</b>\n"
        f"Direction: <b>{direction}</b>\n"
        f"Entry: ₹{price} | SL: ₹{sl} ({sl_strategy}) | Target: ₹{round(tgt,2)}\n"
        f"Qty: {qty} | Score: {signal.get('score','—')}/5\n"
        f"RSI: {signal.get('rsi','—')} | Vol: {signal['vol_ratio']}x\n"
        f"VIX Factor: {vix_factor} | Regime: {signal.get('regime','—')}"
    )
    send_alert(msg, html_msg)


def manage_trade(symbol, df):
    trade     = st.session_state.active_trades[symbol]
    price     = float(df["Close"].iloc[-1])
    direction = trade["type"]
    df_ind    = add_indicators(df)

    if use_partial and not trade["partial_done"] and trade["qty_remaining"] > 1:
        hit_partial = (direction == "BUY" and price >= trade["target_partial"]) or \
                      (direction == "SELL" and price <= trade["target_partial"])
        if hit_partial:
            partial_qty = trade["qty_remaining"] // 2
            if partial_qty > 0:
                partial_pnl = (
                    (price - trade["entry"]) * partial_qty if direction == "BUY"
                    else (trade["entry"] - price) * partial_qty
                )
                trade["qty_remaining"] -= partial_qty
                trade["partial_done"]   = True
                trade["breakeven_sl"]   = True
                trade["sl"]             = trade["entry"]
                st.session_state.capital   += round(partial_pnl, 2)
                st.session_state.daily_pnl += round(partial_pnl, 2)
                send_alert(
                    f"📦 Partial Exit — {symbol}\n{partial_qty} qty @ ₹{price:.2f} | P&L: ₹{partial_pnl:+.2f}\nSL → breakeven ₹{trade['entry']}",
                    f"📦 <b>Partial Exit — {symbol}</b>\n{partial_qty} qty @ ₹{price:.2f} | P&L: ₹{partial_pnl:+.2f}"
                )

    trade["sl"] = update_sl(df_ind, trade, price)

    if direction == "BUY":
        if price <= trade["sl"]:
            exit_trade(symbol, price, (price - trade["entry"]) * trade["qty_remaining"], "SL Hit")
        elif price >= trade["target"]:
            exit_trade(symbol, price, (price - trade["entry"]) * trade["qty_remaining"], "Target Hit")
    else:
        if price >= trade["sl"]:
            exit_trade(symbol, price, (trade["entry"] - price) * trade["qty_remaining"], "SL Hit")
        elif price <= trade["target"]:
            exit_trade(symbol, price, (trade["entry"] - price) * trade["qty_remaining"], "Target Hit")


def exit_trade(symbol, price, pnl, reason="Manual"):
    if symbol not in st.session_state.active_trades:
        return
    trade = st.session_state.active_trades.pop(symbol)
    st.session_state.capital   += round(pnl, 2)
    st.session_state.daily_pnl += round(pnl, 2)
    entry_val = trade["entry"] * trade.get("qty_remaining", trade["qty"])
    st.session_state.closed_trades.append({
        "Symbol":      symbol,
        "Type":        trade["type"],
        "Entry":       trade["entry"],
        "Exit":        round(price, 2),
        "Qty":         trade.get("qty_remaining", trade["qty"]),
        "PnL (₹)":    round(pnl, 2),
        "PnL %":      round((pnl / entry_val) * 100, 2) if entry_val else 0,
        "Score":       trade.get("score", "—"),
        "SL Strategy": trade.get("sl_strategy", "—"),
        "Reason":      reason,
        "Entry Time":  trade.get("entry_time", "—"),
        "Exit Time":   datetime.now().strftime("%H:%M:%S"),
        "Regime":      trade.get("regime", "—"),
        "Note":        "",
    })
    emoji = "✅" if pnl > 0 else "❌"
    send_alert(
        f"{emoji} Trade Exit — {symbol}\nExit @ ₹{price:.2f} | P&L: ₹{pnl:+.2f}\nReason: {reason}",
        f"{emoji} <b>Trade Exit — {symbol}</b>\nExit @ ₹{price:.2f} | P&L: ₹{pnl:+.2f}\nReason: {reason}"
    )
    reset_signal_state(symbol)


# ================================
# DAILY P&L CHECK
# ================================
ic = st.session_state.get("initial_capital", 100_000)
daily_loss_cap   = ic * (daily_loss_limit_pct / 100)
daily_profit_cap = ic * (daily_profit_target_pct / 100)

if not st.session_state.trading_locked:
    if st.session_state.daily_pnl <= -daily_loss_cap:
        st.session_state.trading_locked = True
        st.session_state.lock_reason = f"Daily loss limit of ₹{daily_loss_cap:,.0f} ({daily_loss_limit_pct}%) hit"
    elif st.session_state.daily_pnl >= daily_profit_cap:
        st.session_state.trading_locked = True
        st.session_state.lock_reason = f"Daily profit target of ₹{daily_profit_cap:,.0f} ({daily_profit_target_pct}%) reached"


# ================================
# HEADER
# ================================
col_h1, col_h2, col_h3, col_h4 = st.columns([4, 1, 1, 1])
with col_h1:
    st.markdown(
        '<div class="header-title">🚀 ORB Smart Scanner '
        '<span style="color:#6366f1;font-size:1rem;font-weight:600;vertical-align:middle;">PRO v3</span></div>',
        unsafe_allow_html=True
    )
    status_txt = "🟢 Market Open" if market_open else ("🟡 Pre-Market" if is_pre_market() else "🔴 Market Closed")
    regime_cls = {"Trending": "regime-badge-trend", "Ranging": "regime-badge-range",
                  "Volatile": "regime-badge-volatile"}.get(st.session_state.market_regime, "regime-badge-range")
    st.markdown(
        f'<div class="header-subtitle">{status_txt} &nbsp;|&nbsp; {datetime.now().strftime("%d %b %Y, %H:%M:%S")} '
        f'&nbsp;|&nbsp; {len(selected_symbols)} symbols &nbsp;|&nbsp; '
        f'<span class="{regime_cls}">Regime: {st.session_state.market_regime}</span></div>',
        unsafe_allow_html=True
    )
with col_h2:
    manual_scan = st.button("🔄 Scan Now", use_container_width=True, type="primary")
with col_h3:
    if st.button("🧹 Clear Trades", use_container_width=True):
        st.session_state.active_trades = {}
        st.session_state.closed_trades = []
        st.session_state.signal_state  = {}
        save_session()
        st.rerun()
with col_h4:
    if st.button("🔓 Unlock", use_container_width=True):
        st.session_state.trading_locked = False
        st.session_state.lock_reason    = ""
        st.rerun()

if st.session_state.trading_locked:
    if "profit" in st.session_state.lock_reason.lower():
        st.markdown(f'<div class="daily-profit-banner">🏆 TRADING LOCKED — {st.session_state.lock_reason}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="daily-limit-banner">🛑 TRADING LOCKED — {st.session_state.lock_reason}</div>', unsafe_allow_html=True)

if not market_open:
    st.info("⏸ Market closed. Fetching last 5 days of intraday data. Click **Scan Now** to run manually.")


# ================================
# RUN SCAN
# ================================
do_scan = (market_open or manual_scan) and not st.session_state.trading_locked and selected_symbols

if do_scan:
    cache_invalidate_expired()

    scan_results  = []
    errors        = []
    signals_found = 0

    progress_bar = st.progress(0, text="Initialising scan…")
    total = len(selected_symbols)
    BATCH = 20

    # Snapshot cache BEFORE spawning threads (thread-safe)
    cache_snap = snapshot_cache()

    all_data = []   # list of (symbol, df, err, cache_write)
    all_15m  = {}   # symbol → df
    all_1h   = {}   # symbol → df
    done     = 0

    for i in range(0, total, BATCH):
        batch = selected_symbols[i:i + BATCH]
        with ThreadPoolExecutor(max_workers=min(10, len(batch))) as ex:
            futures = {
                ex.submit(fetch, s, "5m",  "5d", True, cache_snap): ("5m",  s)
                for s in batch
            }
            if use_mtf:
                futures.update({
                    ex.submit(fetch, s, "15m", "5d", True, cache_snap): ("15m", s)
                    for s in batch
                })
            if use_3tf:
                futures.update({
                    ex.submit(fetch, s, "1h",  "5d", True, cache_snap): ("1h",  s)
                    for s in batch
                })

            for f in as_completed(futures):
                tf, sym = futures[f]
                try:
                    result = f.result()   # (symbol, df, err, cache_write)
                except Exception as exc:
                    result = (sym, None, str(exc), None)

                # Write any new cache entries back to session_state (main thread)
                _apply_cache_write(result)

                symbol_r, df_r, err_r = result[0], result[1], result[2]

                if tf == "5m":
                    all_data.append((symbol_r, df_r, err_r))
                    done += 1
                    progress_bar.progress(min(done / total, 1.0), text=f"Fetching {done}/{total}…")
                elif tf == "15m":
                    if df_r is not None:
                        all_15m[sym] = df_r
                elif tf == "1h":
                    if df_r is not None:
                        all_1h[sym] = df_r

    progress_bar.empty()

    for symbol, df, err in all_data:
        if err or df is None:
            errors.append({"Symbol": symbol, "Error": err or "No data returned"})
            scan_results.append({
                "Symbol": "⚠️ " + symbol, "Signal": "Error", "Score": "—",
                "Price": "—", "ORB High": "—", "ORB Low": "—", "ATR": "—",
                "Vol Ratio": "—", "RSI": "—", "Gap %": "—", "3TF": "—",
                "Regime": "—", "SL Strategy": "—",
                "Reason": err or "Fetch failed",
            })
            continue

        if symbol in st.session_state.active_trades:
            manage_trade(symbol, df)
            trade = st.session_state.active_trades.get(symbol)
            if trade:
                price  = float(df["Close"].iloc[-1])
                unreal = (
                    (price - trade["entry"]) * trade["qty_remaining"]
                    if trade["type"] == "BUY"
                    else (trade["entry"] - price) * trade["qty_remaining"]
                )
                scan_results.append({
                    "Symbol": symbol, "Signal": f"🔵 {trade['type']} (Active)",
                    "Score": trade.get("score", "—"), "Price": round(price, 2),
                    "ORB High": "—", "ORB Low": "—", "ATR": trade.get("atr", "—"),
                    "Vol Ratio": trade.get("vol_ratio", "—"), "RSI": trade.get("rsi", "—"),
                    "Gap %": "—", "3TF": "✅" if trade.get("tf3") else "—",
                    "Regime": trade.get("regime", "—"), "SL Strategy": trade.get("sl_strategy", "—"),
                    "Reason": f"Unrealised ₹{unreal:+,.2f} | SL {trade['sl']}",
                })
            continue

        df15 = all_15m.get(symbol)
        df1h = all_1h.get(symbol)

        signal, reason = get_signal(symbol, df, df15, df1h)
        last_price = round(float(df["Close"].iloc[-1]), 2)

        if signal is None:
            scan_results.append({
                "Symbol": symbol, "Signal": "—", "Score": "—",
                "Price": last_price, "ORB High": "—", "ORB Low": "—",
                "ATR": "—", "Vol Ratio": "—", "RSI": "—", "Gap %": "—",
                "3TF": "—", "Regime": st.session_state.market_regime,
                "SL Strategy": sl_strategy,
                "Reason": reason or "No signal",
            })
            continue

        direction = signal["direction"]
        emoji     = "🟢" if direction == "BUY" else "🔴"
        gap_str   = f"{signal['gap']:+.2f}%" if signal.get("gap") else "—"
        tf3_str   = "✅" if signal.get("tf3_confirmed") else ("—" if not use_3tf else "❌")

        if len(st.session_state.active_trades) >= max_trades:
            scan_results.append({
                "Symbol": symbol, "Signal": f"{emoji} {direction} (Skipped)",
                "Score": signal["score"], "Price": signal["price"],
                "ORB High": signal["orb_high"], "ORB Low": signal["orb_low"],
                "ATR": signal["atr"], "Vol Ratio": signal["vol_ratio"],
                "RSI": signal.get("rsi", "—"), "Gap %": gap_str, "3TF": tf3_str,
                "Regime": signal.get("regime", "—"), "SL Strategy": sl_strategy,
                "Reason": "Max trades reached",
            })
            st.session_state.signal_state[symbol]["fired"] = False
            continue

        enter_trade(symbol, signal)
        signals_found += 1

        scan_results.append({
            "Symbol": symbol, "Signal": f"{emoji} {direction}",
            "Score": signal["score"], "Price": signal["price"],
            "ORB High": signal["orb_high"], "ORB Low": signal["orb_low"],
            "ATR": signal["atr"], "Vol Ratio": signal["vol_ratio"],
            "RSI": signal.get("rsi", "—"), "Gap %": gap_str, "3TF": tf3_str,
            "Regime": signal.get("regime", "—"), "SL Strategy": sl_strategy,
            "Reason": f"Entered @ {signal['price']} | SL: {signal['sl']} ({sl_strategy})",
        })

    st.session_state.scan_results   = scan_results
    st.session_state.last_scan_time = datetime.now().strftime("%H:%M:%S")
    st.session_state.error_log      = errors

    st.session_state.equity.append({
        "time":    datetime.now(),
        "capital": st.session_state.capital,
    })
    save_session()

    if signals_found > st.session_state.last_signal_count:
        st.components.v1.html(f"<script>checkAndBeep({signals_found});</script>", height=0)
    st.session_state.last_signal_count = signals_found

    if signals_found > 0:
        st.success(f"✅ **{signals_found} new signal(s)** found | SL: {sl_strategy} | 3TF: {'On' if use_3tf else 'Off'}")
    else:
        error_count = len(errors)
        msg = f"ℹ️ No new signals. {len(selected_symbols)} symbols scanned."
        if error_count:
            msg += f" ({error_count} fetch errors)"
        st.info(msg)

elif not selected_symbols:
    st.error("⚠️ No symbols selected.")


# ================================
# MARKET CONTEXT BAR
# ================================
nifty_chg = mkt_ctx["nifty_change"]
vix_val   = mkt_ctx["vix"]
nifty_cls = "nifty-green" if nifty_chg >= 0 else "nifty-red"
nifty_sym = "▲" if nifty_chg >= 0 else "▼"
if vix_val > 20:
    vix_badge = f'<span class="vix-badge-high">VIX {vix_val:.1f} ⚠️ HIGH</span>'
elif vix_val > 15:
    vix_badge = f'<span class="vix-badge-mid">VIX {vix_val:.1f} 🟡 MID</span>'
else:
    vix_badge = f'<span class="vix-badge-low">VIX {vix_val:.1f} 🟢 LOW</span>'

regime     = st.session_state.market_regime
regime_cls = {"Trending": "regime-badge-trend", "Ranging": "regime-badge-range",
              "Volatile": "regime-badge-volatile"}.get(regime, "regime-badge-range")

st.markdown(f"""
<div class="ctx-bar">
  <span>🏦 <b>Nifty 50:</b> <span class="{nifty_cls}">{nifty_sym} {abs(nifty_chg):.1f} pts</span></span>
  <span>{vix_badge}</span>
  <span class="{regime_cls}">📊 {regime}</span>
  {'<span style="color:#78350f;font-weight:600;">⚠️ VIX>20 → Size halved</span>' if (use_vix_sizing and vix_val > 20) else ''}
  {'<span style="color:#dc2626;font-weight:600;">🚫 Nifty RED → BUY filtered</span>' if (use_nifty_filter and nifty_chg < 0) else ''}
  {'<span style="color:#7c3aed;font-weight:600;">🔗 Corr Filter ON</span>' if use_corr_filter else ''}
  <span style="color:var(--txt-sub);font-size:0.8rem;">Daily P&L: <b>₹{st.session_state.daily_pnl:+,.0f}</b></span>
  <span style="color:var(--txt-sub);font-size:0.8rem;">SL: <b>{sl_strategy}</b></span>
</div>
""", unsafe_allow_html=True)


# ================================
# METRICS
# ================================
st.divider()
total_closed_pnl = sum(t["PnL (₹)"] for t in st.session_state.closed_trades)
win_trades       = [t for t in st.session_state.closed_trades if t["PnL (₹)"] > 0]
win_rate         = (len(win_trades) / len(st.session_state.closed_trades) * 100) if st.session_state.closed_trades else 0
net_change       = st.session_state.capital - st.session_state.get("initial_capital", 100_000)

c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
c1.metric("💼 Capital",       f"₹{st.session_state.capital:,.0f}", f"₹{net_change:+,.0f}")
c2.metric("📈 Realised P&L",  f"₹{total_closed_pnl:,.0f}")
c3.metric("📅 Daily P&L",     f"₹{st.session_state.daily_pnl:+,.0f}")
c4.metric("🔓 Active Trades", len(st.session_state.active_trades), f"/ {max_trades} max")
c5.metric("📝 Closed Trades", len(st.session_state.closed_trades))
c6.metric("🏆 Win Rate",      f"{win_rate:.1f}%")
c7.metric("🕒 Last Scan",     st.session_state.last_scan_time or "—")


# ================================
# TABS
# ================================
tab_labels = [
    "🔍 Scan Results", "📊 Active Trades", "📜 Closed Trades",
    "📈 Equity Curve", "📊 Perf Stats", "🗺️ Sector Heatmap",
    "⚗️ Backtester", "🎲 Monte Carlo", "⚠️ Error Log",
]
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs(tab_labels)


# ── TAB 1: SCAN RESULTS + INLINE CHART ──
with tab1:
    if st.session_state.scan_results:
        df_scan = pd.DataFrame(st.session_state.scan_results)
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            sig_filter = st.selectbox("Filter Signal", ["All", "BUY", "SELL", "Active", "No Signal", "Error"])
        with f2:
            sort_col = st.selectbox("Sort by", ["Symbol", "Signal", "Score", "Price", "Vol Ratio", "ATR", "RSI"])
        with f3:
            sort_asc = st.radio("Order", ["↑ Asc", "↓ Desc"], horizontal=True) == "↑ Asc"
        with f4:
            min_score = st.slider("Min Score", 0.0, 5.0, 0.0, 0.5)

        if sig_filter != "All":
            df_scan = df_scan[df_scan["Signal"].str.contains(sig_filter, case=False, na=False)]
        if min_score > 0:
            df_scan = df_scan[pd.to_numeric(df_scan["Score"], errors="coerce").fillna(0) >= min_score]
        try:
            df_scan = df_scan.sort_values(sort_col, ascending=sort_asc)
        except Exception:
            pass

        st.caption(f"Showing **{len(df_scan)}** of **{len(st.session_state.scan_results)}** symbols")
        st.dataframe(df_scan, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("##### 📈 Inline Chart Viewer")
        chart_sym_opts = [r["Symbol"].replace("⚠️ ", "") for r in st.session_state.scan_results
                          if r.get("Price") not in ("—", None)]
        if chart_sym_opts:
            chart_sym = st.selectbox("Select symbol for chart", chart_sym_opts, key="chart_sym_sel")
            if st.button("📊 Load Chart", key="load_chart_btn"):
                # Use main-thread cache_get for chart fetch
                df_chart = cache_get(chart_sym, "5m")
                if df_chart is None:
                    _, df_chart, _, cw = fetch(chart_sym, "5m", "5d", use_cache=False, _cache_snapshot={})
                    if df_chart is not None and cw:
                        key_c, entry_c = cw
                        st.session_state.fetch_cache[key_c] = entry_c

                if df_chart is not None:
                    df_chart = add_indicators(df_chart)
                    df_chart.index = pd.to_datetime(df_chart.index)

                    orb_df_c, _ = get_orb_range(df_chart)
                    orb_h = float(orb_df_c["High"].max()) if not orb_df_c.empty else None
                    orb_l = float(orb_df_c["Low"].min())  if not orb_df_c.empty else None

                    fig_c = go.Figure()
                    fig_c.add_trace(go.Candlestick(
                        x=df_chart.index, open=df_chart["Open"], high=df_chart["High"],
                        low=df_chart["Low"], close=df_chart["Close"], name="OHLC",
                        increasing_line_color="#16a34a", decreasing_line_color="#dc2626",
                    ))
                    fig_c.add_trace(go.Scatter(
                        x=df_chart.index, y=df_chart["EMA"],
                        mode="lines", name=f"EMA{ema_period}",
                        line=dict(color="#6366f1", width=1.5, dash="dot"),
                    ))
                    if "ST_val" in df_chart.columns:
                        fig_c.add_trace(go.Scatter(
                            x=df_chart.index, y=df_chart["ST_val"],
                            mode="lines", name="Supertrend",
                            line=dict(color="#f59e0b", width=1.5),
                        ))
                    if orb_h:
                        fig_c.add_hline(y=orb_h, line_dash="dash", line_color="#22c55e",
                                        annotation_text=f"ORB High {orb_h:.2f}", annotation_position="top right")
                    if orb_l:
                        fig_c.add_hline(y=orb_l, line_dash="dash", line_color="#ef4444",
                                        annotation_text=f"ORB Low {orb_l:.2f}", annotation_position="bottom right")
                    fig_c.update_layout(
                        title=f"{chart_sym} — 5m Candlestick | ORB Zone | EMA | Supertrend",
                        template=plotly_tpl, height=520, xaxis_rangeslider_visible=False,
                        margin=dict(l=10, r=10, t=50, b=10),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02),
                    )
                    st.plotly_chart(fig_c, use_container_width=True)

                    fig_sub = go.Figure()
                    fig_sub.add_trace(go.Scatter(x=df_chart.index, y=df_chart["RSI"],
                                                  mode="lines", name="RSI", line=dict(color="#6366f1")))
                    fig_sub.add_hline(y=70, line_dash="dot", line_color="#ef4444", annotation_text="70")
                    fig_sub.add_hline(y=30, line_dash="dot", line_color="#22c55e", annotation_text="30")
                    fig_sub.update_layout(title="RSI", template=plotly_tpl, height=180,
                                          margin=dict(l=10, r=10, t=30, b=10))
                    st.plotly_chart(fig_sub, use_container_width=True)
                else:
                    st.warning(f"Could not load data for {chart_sym}")
    else:
        st.info("Run a scan to see results here.")


# ── TAB 2: ACTIVE TRADES ──
with tab2:
    if st.session_state.active_trades:
        rows = []
        for sym, t in st.session_state.active_trades.items():
            entry = t["entry"]
            rr    = abs(t["target"] - entry) / abs(entry - t["sl"]) if abs(entry - t["sl"]) > 0 else 0
            rows.append({
                "Symbol":       sym,
                "Type":         t["type"],
                "Entry":        entry,
                "SL":           t["sl"],
                "Target":       t["target"],
                "Partial Tgt":  t.get("target_partial", "—"),
                "Qty":          t.get("qty_remaining", t["qty"]),
                "Score":        t.get("score", "—"),
                "R:R":          f"1:{rr:.1f}",
                "SL Strategy":  t.get("sl_strategy", "—"),
                "Partial Done": "✅" if t.get("partial_done") else "⏳",
                "BE SL":        "✅" if t.get("breakeven_sl") else "—",
                "3TF":          "✅" if t.get("tf3") else "—",
                "Regime":       t.get("regime", "—"),
                "Entry Time":   t.get("entry_time", "—"),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.markdown("##### Manual Exit")
        exit_sym = st.selectbox("Select symbol to exit", list(st.session_state.active_trades.keys()))
        if st.button(f"🚪 Exit {exit_sym}", type="primary"):
            t = st.session_state.active_trades[exit_sym]
            exit_trade(exit_sym, t["entry"], 0, "Manual Exit")
            save_session()
            st.rerun()
    else:
        st.info("No active trades.")


# ── TAB 3: CLOSED TRADES + JOURNAL ──
with tab3:
    if st.session_state.closed_trades:
        closed_df = pd.DataFrame(st.session_state.closed_trades)
        total_pnl = closed_df["PnL (₹)"].sum()
        ca, cb, cc = st.columns(3)
        ca.metric("Total P&L",    f"₹{total_pnl:,.2f}")
        cb.metric("Total Trades", len(closed_df))
        cc.metric("Win Rate",     f"{win_rate:.1f}%")

        st.dataframe(closed_df, use_container_width=True, hide_index=True)

        st.markdown("##### 📓 Add Trade Note")
        note_idx = st.selectbox("Select trade (row #)", list(range(len(st.session_state.closed_trades))))
        note_txt = st.text_area("Note", value=st.session_state.closed_trades[note_idx].get("Note", ""), height=80)
        if st.button("💾 Save Note"):
            st.session_state.closed_trades[note_idx]["Note"] = note_txt
            save_session()
            st.success("Note saved!")
            st.rerun()

        csv = closed_df.to_csv(index=False)
        st.download_button(
            "⬇️ Export CSV", csv,
            file_name=f"orb_trades_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
        )
        st.download_button(
            "📓 Export Journal (JSON)",
            json.dumps(st.session_state.closed_trades, indent=2),
            file_name=f"orb_journal_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json",
        )
    else:
        st.info("No closed trades yet.")


# ── TAB 4: EQUITY CURVE ──
with tab4:
    equity_df = pd.DataFrame(st.session_state.equity)
    if not equity_df.empty:
        initial = st.session_state.get("initial_capital", 100_000)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=equity_df["time"], y=equity_df["capital"],
            mode="lines+markers",
            line=dict(color="#6366f1", width=2.5),
            marker=dict(size=4),
            name="Capital", fill="tozeroy",
            fillcolor="rgba(99,102,241,0.08)"
        ))
        fig.add_hline(y=initial, line_dash="dash", line_color="#94a3b8",
                      annotation_text=f"Initial ₹{initial:,.0f}", annotation_position="bottom right")
        fig.update_layout(title="Equity Curve", xaxis_title="Time", yaxis_title="Capital (₹)",
                          template=plotly_tpl, height=400, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)

        peak = equity_df["capital"].cummax()
        dd   = ((equity_df["capital"] - peak) / peak) * 100
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=equity_df["time"], y=dd, mode="lines", fill="tozeroy",
            line=dict(color="#ef4444", width=1.5),
            fillcolor="rgba(239,68,68,0.1)", name="Drawdown %"
        ))
        fig2.update_layout(title="Drawdown %", template=plotly_tpl, height=220,
                            margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No equity data yet.")


# ── TAB 5: PERF STATS ──
with tab5:
    if st.session_state.closed_trades:
        df_p  = pd.DataFrame(st.session_state.closed_trades)
        wins  = df_p[df_p["PnL (₹)"] > 0]
        loses = df_p[df_p["PnL (₹)"] <= 0]

        avg_win  = wins["PnL (₹)"].mean()  if len(wins)  > 0 else 0
        avg_loss = loses["PnL (₹)"].mean() if len(loses) > 0 else 0
        pf       = abs(wins["PnL (₹)"].sum() / loses["PnL (₹)"].sum()) \
                   if loses["PnL (₹)"].sum() != 0 else float("inf")

        pnl_series = df_p["PnL (₹)"].tolist()
        max_consec_wins = max_consec_loss = cur_w = cur_l = 0
        for p in pnl_series:
            if p > 0:
                cur_w += 1; cur_l = 0
                max_consec_wins = max(max_consec_wins, cur_w)
            else:
                cur_l += 1; cur_w = 0
                max_consec_loss = max(max_consec_loss, cur_l)

        df_p["Hour"] = pd.to_datetime(df_p["Entry Time"], format="%H:%M:%S", errors="coerce").dt.hour
        hour_pnl = df_p.groupby("Hour")["PnL (₹)"].sum()
        best_hr  = int(hour_pnl.idxmax()) if not hour_pnl.empty else "—"
        worst_hr = int(hour_pnl.idxmin()) if not hour_pnl.empty else "—"

        s1, s2, s3 = st.columns(3)
        with s1: st.markdown(f'<div class="backtest-stat"><div class="val" style="color:#16a34a;">₹{avg_win:,.0f}</div><div class="lbl">Avg Win</div></div>', unsafe_allow_html=True)
        with s2: st.markdown(f'<div class="backtest-stat"><div class="val" style="color:#dc2626;">₹{avg_loss:,.0f}</div><div class="lbl">Avg Loss</div></div>', unsafe_allow_html=True)
        with s3: st.markdown(f'<div class="backtest-stat"><div class="val">{pf:.2f}x</div><div class="lbl">Profit Factor</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        s4, s5, s6, s7 = st.columns(4)
        with s4: st.markdown(f'<div class="backtest-stat"><div class="val">{max_consec_wins}</div><div class="lbl">Max Consec. Wins</div></div>', unsafe_allow_html=True)
        with s5: st.markdown(f'<div class="backtest-stat"><div class="val">{max_consec_loss}</div><div class="lbl">Max Consec. Losses</div></div>', unsafe_allow_html=True)
        with s6: st.markdown(f'<div class="backtest-stat"><div class="val">{best_hr}:00</div><div class="lbl">Best Hour</div></div>', unsafe_allow_html=True)
        with s7: st.markdown(f'<div class="backtest-stat"><div class="val">{worst_hr}:00</div><div class="lbl">Worst Hour</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if not hour_pnl.empty:
            fig_h = px.bar(
                x=[f"{h}:00" for h in hour_pnl.index], y=hour_pnl.values,
                color=hour_pnl.values,
                color_continuous_scale=["#ef4444", "#fbbf24", "#22c55e"],
                labels={"x": "Hour", "y": "P&L (₹)"}, title="P&L by Hour of Day"
            )
            fig_h.update_layout(template=plotly_tpl, height=300, showlegend=False,
                                 coloraxis_showscale=False, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_h, use_container_width=True)

        if "SL Strategy" in df_p.columns:
            sl_pnl = df_p.groupby("SL Strategy")["PnL (₹)"].agg(["sum", "count", "mean"]).reset_index()
            sl_pnl.columns = ["SL Strategy", "Total P&L", "# Trades", "Avg P&L"]
            st.markdown("##### SL Strategy Performance")
            st.dataframe(sl_pnl, use_container_width=True, hide_index=True)

        df_p2 = df_p[pd.to_numeric(df_p["Score"], errors="coerce").notna()].copy()
        df_p2["Score"] = pd.to_numeric(df_p2["Score"])
        if not df_p2.empty:
            fig_s = px.scatter(
                df_p2, x="Score", y="PnL (₹)", color="Type",
                color_discrete_map={"BUY": "#22c55e", "SELL": "#ef4444"},
                title="Signal Score vs P&L",
                hover_data=["Symbol", "Entry", "Exit"]
            )
            fig_s.update_layout(template=plotly_tpl, height=300, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_s, use_container_width=True)
    else:
        st.info("No closed trades yet.")


# ── TAB 6: SECTOR HEATMAP ──
with tab6:
    st.markdown("### 🗺️ Sector Signal Heatmap")
    if st.session_state.scan_results:
        sector_counts = {}
        for row in st.session_state.scan_results:
            sym    = row["Symbol"].replace("⚠️ ", "").replace("—", "")
            sector = SECTOR_MAP.get(sym, "Other")
            sig    = str(row.get("Signal", ""))
            if sector not in sector_counts:
                sector_counts[sector] = {"BUY": 0, "SELL": 0, "Active": 0, "No Signal": 0}
            if "BUY" in sig and "Active" not in sig and "Skipped" not in sig:
                sector_counts[sector]["BUY"] += 1
            elif "SELL" in sig and "Active" not in sig and "Skipped" not in sig:
                sector_counts[sector]["SELL"] += 1
            elif "Active" in sig:
                sector_counts[sector]["Active"] += 1
            else:
                sector_counts[sector]["No Signal"] += 1

        heat_rows = []
        for sector, counts in sector_counts.items():
            total_sig = counts["BUY"] + counts["SELL"]
            heat_rows.append({
                "Sector":        sector,
                "BUY":           counts["BUY"],
                "SELL":          counts["SELL"],
                "Active":        counts["Active"],
                "No Signal":     counts["No Signal"],
                "Total Signals": total_sig,
            })
        heat_df = pd.DataFrame(heat_rows).sort_values("Total Signals", ascending=False)

        sig_heat = heat_df[heat_df["Total Signals"] > 0]
        if not sig_heat.empty:
            fig_tree = px.treemap(
                sig_heat.assign(parent="Sectors"),
                path=["parent", "Sector"], values="Total Signals",
                color="BUY", color_continuous_scale=["#fca5a5", "#bbf7d0"],
                title="Signal Distribution by Sector"
            )
            fig_tree.update_layout(height=420, margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig_tree, use_container_width=True)

        st.dataframe(heat_df, use_container_width=True, hide_index=True)

        top_sector = heat_df.iloc[0] if not heat_df.empty else None
        if top_sector is not None and top_sector["Total Signals"] > 3:
            st.warning(
                f"⚠️ Over-concentration: **{top_sector['Sector']}** has {top_sector['Total Signals']} signals. "
                f"{'Correlation filter is ON — duplicates suppressed.' if use_corr_filter else 'Enable correlation filter to suppress duplicates.'}"
            )
    else:
        st.info("Run a scan first.")


# ── TAB 7: WALK-FORWARD BACKTESTER ──
with tab7:
    st.markdown("### ⚗️ Walk-Forward Backtester")
    st.caption("True out-of-sample validation with rolling windows.")

    bt_col1, bt_col2, bt_col3, bt_col4, bt_col5 = st.columns(5)
    with bt_col1:
        bt_symbols = st.multiselect(
            "Symbols",
            options=selected_symbols,
            default=selected_symbols[:5] if len(selected_symbols) >= 5 else selected_symbols,
        )
    with bt_col2:
        bt_orb_min = st.number_input("ORB Minutes", 5, 60, int(orb_minutes), key="bt_orb")
    with bt_col3:
        bt_atr_tgt = st.number_input("ATR Target Mult", 1.0, 5.0, 2.0, 0.5, key="bt_atr")
    with bt_col4:
        wf_train_days = st.number_input("Train Window (days)", 1, 20, 3, key="wf_train")
    with bt_col5:
        wf_test_days = st.number_input("Test Window (days)", 1, 10, 1, key="wf_test")

    def run_orb_backtest_on_days(df_full, days_list, orb_m, atr_m):
        trades  = []
        df_full = add_indicators(df_full.copy())
        df_full.index = pd.to_datetime(df_full.index)
        for day in days_list:
            grp = df_full[df_full.index.date == day].copy()
            if len(grp) < 5:
                continue
            grp["_time"] = grp.index.time
            cutoff_t     = (datetime.combine(day, dtime(9, 15)) + timedelta(minutes=int(orb_m))).time()
            orb_part     = grp[grp["_time"] <= cutoff_t]
            rest_part    = grp[grp["_time"] > cutoff_t]
            if len(orb_part) < 2 or len(rest_part) < 2:
                continue
            orb_h = float(orb_part["High"].max())
            orb_l = float(orb_part["Low"].min())
            in_trade = False
            direction = entry_p = sl_p = tgt_p = 0.0

            for idx, row in rest_part.iterrows():
                close = float(row["Close"])
                atr   = float(row["ATR"]) if not pd.isna(row.get("ATR", np.nan)) else 0
                if not in_trade:
                    if close > orb_h:
                        direction = "BUY";  entry_p = close; sl_p = orb_l; tgt_p = entry_p + atr_m * atr; in_trade = True
                    elif close < orb_l:
                        direction = "SELL"; entry_p = close; sl_p = orb_h; tgt_p = entry_p - atr_m * atr; in_trade = True
                else:
                    hit_sl  = (direction == "BUY" and close <= sl_p)  or (direction == "SELL" and close >= sl_p)
                    hit_tgt = (direction == "BUY" and close >= tgt_p) or (direction == "SELL" and close <= tgt_p)
                    if hit_sl or hit_tgt:
                        pnl = (close - entry_p) if direction == "BUY" else (entry_p - close)
                        trades.append({"day": str(day), "direction": direction, "entry": round(entry_p, 2),
                                       "exit": round(close, 2), "pnl": round(pnl, 2),
                                       "reason": "TGT" if hit_tgt else "SL"})
                        in_trade = False

            if in_trade:
                close = float(rest_part["Close"].iloc[-1])
                pnl   = (close - entry_p) if direction == "BUY" else (entry_p - close)
                trades.append({"day": str(day), "direction": direction, "entry": round(entry_p, 2),
                               "exit": round(close, 2), "pnl": round(pnl, 2), "reason": "EOD"})
        return trades

    if st.button("▶️ Run Walk-Forward Backtest", type="primary", key="wf_run"):
        with st.spinner("Running walk-forward backtest…"):
            wf_results = []
            for sym in bt_symbols:
                _, df_bt, err, cw = fetch(sym, "5m", "1mo", use_cache=False, _cache_snapshot={})
                if cw:
                    k2, e2 = cw
                    st.session_state.fetch_cache[k2] = e2
                if err or df_bt is None or len(df_bt) < 20:
                    continue
                df_bt.index = pd.to_datetime(df_bt.index)
                unique_days  = sorted(set(df_bt.index.date.tolist()))
                window_size  = int(wf_train_days) + int(wf_test_days)
                for start_i in range(0, len(unique_days) - window_size + 1, int(wf_test_days)):
                    train_days = unique_days[start_i: start_i + int(wf_train_days)]
                    test_days  = unique_days[start_i + int(wf_train_days): start_i + window_size]
                    if not test_days:
                        continue
                    for t in run_orb_backtest_on_days(df_bt, test_days, bt_orb_min, bt_atr_tgt):
                        t["symbol"] = sym
                        t["window"] = f"{train_days[0]} → {test_days[-1]}"
                        wf_results.append(t)

            st.session_state.backtest_results = wf_results

        if wf_results:
            bt_df  = pd.DataFrame(wf_results)
            bt_wins= bt_df[bt_df["pnl"] > 0]
            bt_loss= bt_df[bt_df["pnl"] <= 0]
            bt_wr  = len(bt_wins) / len(bt_df) * 100 if len(bt_df) > 0 else 0
            bt_pf  = abs(bt_wins["pnl"].sum() / bt_loss["pnl"].sum()) if bt_loss["pnl"].sum() != 0 else float("inf")

            b1, b2, b3, b4, b5 = st.columns(5)
            pnl_color = "#16a34a" if bt_df["pnl"].sum() > 0 else "#dc2626"
            with b1: st.markdown(f'<div class="backtest-stat"><div class="val">{len(bt_df)}</div><div class="lbl">Total OOS Trades</div></div>', unsafe_allow_html=True)
            with b2: st.markdown(f'<div class="backtest-stat"><div class="val" style="color:{pnl_color}">₹{bt_df["pnl"].sum():,.1f}</div><div class="lbl">OOS P&L (pts)</div></div>', unsafe_allow_html=True)
            with b3: st.markdown(f'<div class="backtest-stat"><div class="val">{bt_wr:.1f}%</div><div class="lbl">OOS Win Rate</div></div>', unsafe_allow_html=True)
            with b4: st.markdown(f'<div class="backtest-stat"><div class="val">{bt_pf:.2f}x</div><div class="lbl">Profit Factor</div></div>', unsafe_allow_html=True)
            with b5: st.markdown(f'<div class="backtest-stat"><div class="val">{len(bt_wins)}/{len(bt_loss)}</div><div class="lbl">W/L</div></div>', unsafe_allow_html=True)

            bt_df["Cum PnL"] = bt_df["pnl"].cumsum()
            fig_bt = go.Figure()
            fig_bt.add_trace(go.Scatter(
                x=list(range(len(bt_df))), y=bt_df["Cum PnL"],
                mode="lines+markers", fill="tozeroy",
                line=dict(color="#6366f1", width=2.5),
                fillcolor="rgba(99,102,241,0.1)", name="OOS Cumulative P&L"
            ))
            fig_bt.add_hline(y=0, line_dash="dash", line_color="#94a3b8")
            fig_bt.update_layout(
                title="Walk-Forward OOS Cumulative P&L",
                template=plotly_tpl, height=350,
                margin=dict(l=10, r=10, t=40, b=10)
            )
            st.plotly_chart(fig_bt, use_container_width=True)

            win_perf = bt_df.groupby("window")["pnl"].agg(["sum", "count", "mean"]).reset_index()
            win_perf.columns = ["Window", "Total P&L", "Trades", "Avg P&L"]
            st.markdown("##### Performance by Window")
            st.dataframe(win_perf, use_container_width=True, hide_index=True)
            st.dataframe(bt_df, use_container_width=True, hide_index=True)

            st.download_button(
                "⬇️ Download Backtest CSV", bt_df.to_csv(index=False),
                file_name=f"orb_wf_backtest_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )
        else:
            st.warning("No trades generated. Try more symbols or wider date range.")

    elif st.session_state.backtest_results:
        st.dataframe(pd.DataFrame(st.session_state.backtest_results), use_container_width=True, hide_index=True)


# ── TAB 8: MONTE CARLO ──
with tab8:
    st.markdown("### 🎲 Monte Carlo Simulation")
    st.caption("Shuffles trade outcomes to estimate max drawdown distribution and risk-of-ruin.")

    mc_col1, mc_col2, mc_col3 = st.columns(3)
    with mc_col1:
        mc_n_sims = st.number_input("Simulations", 100, 5000, 1000, step=100)
    with mc_col2:
        mc_capital = st.number_input("Starting Capital (₹)", 10_000, 10_000_000,
                                     int(st.session_state.initial_capital), step=10_000)
    with mc_col3:
        mc_risk_ruin = st.slider("Ruin Threshold (%)", 10, 90, 30) / 100

    if st.button("▶️ Run Monte Carlo", type="primary", key="mc_run"):
        pnl_list = [t["PnL (₹)"] for t in st.session_state.closed_trades]
        if not pnl_list and st.session_state.backtest_results:
            pnl_list = [t.get("pnl", t.get("PnL", 0)) for t in st.session_state.backtest_results]

        if len(pnl_list) < 5:
            st.warning("Need at least 5 closed trades or backtest results to run Monte Carlo.")
        else:
            with st.spinner(f"Running {mc_n_sims:,} simulations…"):
                pnl_arr  = np.array(pnl_list)
                n_trades = len(pnl_arr)
                results  = []
                rng = np.random.default_rng(42)
                for _ in range(int(mc_n_sims)):
                    shuffled = rng.choice(pnl_arr, size=n_trades, replace=True)
                    equity   = mc_capital + np.cumsum(shuffled)
                    peak     = np.maximum.accumulate(equity)
                    dd_pct   = ((equity - peak) / peak) * 100
                    results.append({
                        "final":  float(equity[-1]),
                        "max_dd": float(dd_pct.min()),
                        "ruined": bool(np.any(equity <= mc_capital * (1 - mc_risk_ruin))),
                    })

            res_df    = pd.DataFrame(results)
            ruin_rate = res_df["ruined"].mean() * 100
            final_arr = res_df["final"].values
            dd_arr    = res_df["max_dd"].values

            mc1, mc2, mc3, mc4 = st.columns(4)
            with mc1: st.markdown(f'<div class="backtest-stat"><div class="val">{ruin_rate:.1f}%</div><div class="lbl">Risk of Ruin</div></div>', unsafe_allow_html=True)
            with mc2: st.markdown(f'<div class="backtest-stat"><div class="val" style="color:#dc2626;">{np.percentile(dd_arr, 95):.1f}%</div><div class="lbl">95th % Max DD</div></div>', unsafe_allow_html=True)
            with mc3: st.markdown(f'<div class="backtest-stat"><div class="val">₹{np.percentile(final_arr, 50):,.0f}</div><div class="lbl">Median Outcome</div></div>', unsafe_allow_html=True)
            with mc4: st.markdown(f'<div class="backtest-stat"><div class="val">₹{np.percentile(final_arr, 5):,.0f}</div><div class="lbl">5th % Worst Case</div></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            fig_mc1 = go.Figure()
            fig_mc1.add_trace(go.Histogram(x=final_arr, nbinsx=50, marker_color="#6366f1", opacity=0.8, name="Final Capital"))
            fig_mc1.add_vline(x=mc_capital, line_dash="dash", line_color="#94a3b8", annotation_text="Start Capital")
            fig_mc1.add_vline(x=float(np.percentile(final_arr, 5)), line_dash="dot", line_color="#ef4444", annotation_text="5th %ile")
            fig_mc1.add_vline(x=float(np.percentile(final_arr, 50)), line_dash="dot", line_color="#22c55e", annotation_text="Median")
            fig_mc1.update_layout(
                title=f"Monte Carlo: Final Capital Distribution ({mc_n_sims:,} simulations)",
                template=plotly_tpl, height=380, margin=dict(l=10, r=10, t=50, b=10)
            )
            st.plotly_chart(fig_mc1, use_container_width=True)

            fig_mc2 = go.Figure()
            fig_mc2.add_trace(go.Histogram(x=dd_arr, nbinsx=40, marker_color="#ef4444", opacity=0.7, name="Max Drawdown %"))
            fig_mc2.add_vline(x=float(np.percentile(dd_arr, 95)), line_dash="dot", line_color="#7c3aed", annotation_text="95th %ile")
            fig_mc2.update_layout(title="Max Drawdown Distribution", template=plotly_tpl, height=300, margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig_mc2, use_container_width=True)

            if ruin_rate > 10:
                st.error(f"⚠️ **High risk of ruin: {ruin_rate:.1f}%**. Consider reducing position size or tightening SL.")
            elif ruin_rate > 5:
                st.warning(f"⚡ Moderate risk of ruin: {ruin_rate:.1f}%. Monitor drawdowns carefully.")
            else:
                st.success(f"✅ Low risk of ruin: {ruin_rate:.1f}%.")


# ── TAB 9: ERROR LOG + CACHE STATS ──
with tab9:
    if st.session_state.error_log:
        st.dataframe(pd.DataFrame(st.session_state.error_log), use_container_width=True, hide_index=True)
        st.caption(f"{len(st.session_state.error_log)} symbol(s) had fetch issues")
        st.info(
            "**Common causes:**\n"
            "- Market closed / weekend (5m data unavailable — uses 5d period as fallback)\n"
            "- Symbol delisted or wrong suffix (.NS vs .BO)\n"
            "- Yahoo Finance rate limiting (exponential backoff retries automatically)\n"
            "- Network / proxy issues"
        )
        if st.button("🧹 Clear Error Log"):
            st.session_state.error_log = []
            st.rerun()
    else:
        st.success("✅ No errors in last scan.")

    st.markdown("---")
    st.markdown("##### 🗄️ Cache Statistics")
    cache = st.session_state.fetch_cache
    now_t = time.time()
    cache_rows = []
    for k, v in list(cache.items()):
        age  = int(now_t - v["ts"])
        parts = k.rsplit("_", 1)
        itv  = parts[-1] if len(parts) == 2 else "?"
        ttl  = _cache_ttl(itv)
        cache_rows.append({
            "Key":     k,
            "Age (s)": age,
            "TTL (s)": ttl,
            "Rows":    len(v["df"]) if v["df"] is not None else 0,
            "Status":  "✅ Fresh" if age < ttl else "⏰ Stale",
        })
    if cache_rows:
        st.dataframe(pd.DataFrame(cache_rows), use_container_width=True, hide_index=True)
        if st.button("🗑️ Clear All Cache"):
            st.session_state.fetch_cache = {}
            st.rerun()
    else:
        st.info("Cache is empty.")
