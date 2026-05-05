# ================================
# ORB SMART SCANNER PRO — v4 FIXED & ENHANCED
# Key fixes:
# 1. All scan result fields ALWAYS populated (ORB H/L, ATR, Vol Ratio, RSI, Gap%, 3TF, Score)
# 2. Signal strength labels: Strong Buy, Buy, Weak Buy, Neutral, Weak Sell, Sell, Strong Sell
# 3. Portfolio management: add/remove holdings with qty, avg cost, live P&L
# 4. Color-coded P&L (green/red) in metrics and tables
# 5. Daily + Portfolio P&L tracked with colors
# ================================# ================================
# ORB SMART SCANNER PRO — v5 ENHANCED
# New Features:
# 1. Intraday + Delivery/Long-Term dual mode
# 2. All-cap scanning: Large, Mid, Small, Penny
# 3. Buy/Sell buttons inline per row (session_state driven)
# 4. Quantity suggestion per signal
# 5. P&L per holding inline
# 6. Score out of 100
# 7. Row colors: Strong Buy=green, Neutral=white, Avoid=light red, Sell=red
# 8. Separate delivery scoring factors (fundamentals proxy, weekly/monthly TF)
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
import json, os, requests, traceback, time, random

# ================================
# PAGE CONFIG
# ================================
st.set_page_config(
    page_title="ORB Smart Scanner Pro v5",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🚀"
)

# ================================
# DARK MODE
# ================================
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True

dark = st.session_state.dark_mode
bg_main  = "#0a0d14" if dark else "#f5f7fa"
bg_card  = "#111827" if dark else "#ffffff"
bg_card2 = "#1a2035" if dark else "#f8fafc"
txt_main = "#e2e8f0" if dark else "#111827"
txt_sub  = "#64748b" if dark else "#6b7280"
bdr_col  = "#1e293b" if dark else "#e2e8f0"
plotly_tpl = "plotly_dark" if dark else "plotly_white"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Outfit:wght@300;400;500;600;700;800&display=swap');
:root {{
    --bg-main:{bg_main}; --bg-card:{bg_card}; --bg-card2:{bg_card2};
    --txt:{txt_main}; --txt-sub:{txt_sub}; --bdr:{bdr_col};
    --accent:#6366f1; --green:#22c55e; --red:#ef4444;
    --yellow:#f59e0b; --blue:#3b82f6; --purple:#a855f7;
}}
html,body,[class*="css"]{{
    font-family:'Outfit',sans-serif;
    background:var(--bg-main)!important;
    color:var(--txt)!important;
}}
.block-container{{padding-top:.8rem;background:var(--bg-main);}}
.stMetric label{{font-size:.7rem;color:var(--txt-sub);letter-spacing:.07em;text-transform:uppercase;font-family:'Space Mono',monospace;}}
.stMetric [data-testid="stMetricValue"]{{font-size:1.4rem;font-weight:700;}}
.stSidebar,.stSidebar [data-testid="stSidebarContent"]{{background:var(--bg-card)!important;}}
div[data-testid="stDataFrame"]{{border-radius:12px;overflow:hidden;}}
.stButton>button{{border-radius:8px;font-family:'Outfit',sans-serif;font-weight:600;transition:all .2s;font-size:.8rem;padding:4px 12px;}}
.stButton>button[kind="primary"]{{background:linear-gradient(135deg,#22c55e,#16a34a);border:none;color:#fff;}}
.stButton>button[kind="secondary"]{{background:linear-gradient(135deg,#ef4444,#dc2626);border:none;color:#fff;}}

/* Row color classes */
.row-strong-buy  {{background:rgba(34,197,94,.18)!important;border-left:4px solid #22c55e!important;}}
.row-buy         {{background:rgba(34,197,94,.09)!important;border-left:4px solid #4ade80!important;}}
.row-weak-buy    {{background:rgba(34,197,94,.04)!important;border-left:3px solid #86efac!important;}}
.row-neutral     {{background:rgba(255,255,255,.02)!important;border-left:3px solid #64748b!important;}}
.row-avoid       {{background:rgba(239,68,68,.06)!important;border-left:3px solid #fca5a5!important;}}
.row-weak-sell   {{background:rgba(239,68,68,.1)!important;border-left:3px solid #f87171!important;}}
.row-sell        {{background:rgba(239,68,68,.18)!important;border-left:4px solid #ef4444!important;}}
.row-strong-sell {{background:rgba(239,68,68,.28)!important;border-left:4px solid #dc2626!important;}}
.row-active      {{background:rgba(99,102,241,.1)!important;border-left:4px solid #6366f1!important;}}

/* Signal badges */
.sig-strong-buy  {{display:inline-block;padding:3px 10px;border-radius:20px;background:rgba(34,197,94,.2);color:#22c55e;font-weight:700;font-size:.78rem;border:1px solid rgba(34,197,94,.4);}}
.sig-buy         {{display:inline-block;padding:3px 10px;border-radius:20px;background:rgba(34,197,94,.1);color:#4ade80;font-weight:600;font-size:.78rem;border:1px solid rgba(74,222,128,.3);}}
.sig-weak-buy    {{display:inline-block;padding:3px 10px;border-radius:20px;background:rgba(34,197,94,.05);color:#86efac;font-weight:500;font-size:.78rem;border:1px solid rgba(134,239,172,.2);}}
.sig-neutral     {{display:inline-block;padding:3px 10px;border-radius:20px;background:rgba(100,116,139,.15);color:#94a3b8;font-weight:500;font-size:.78rem;border:1px solid rgba(148,163,184,.2);}}
.sig-avoid       {{display:inline-block;padding:3px 10px;border-radius:20px;background:rgba(245,158,11,.15);color:#fbbf24;font-weight:700;font-size:.78rem;border:1px solid rgba(251,191,36,.3);}}
.sig-weak-sell   {{display:inline-block;padding:3px 10px;border-radius:20px;background:rgba(239,68,68,.05);color:#fca5a5;font-weight:500;font-size:.78rem;border:1px solid rgba(252,165,165,.2);}}
.sig-sell        {{display:inline-block;padding:3px 10px;border-radius:20px;background:rgba(239,68,68,.1);color:#f87171;font-weight:600;font-size:.78rem;border:1px solid rgba(248,113,113,.3);}}
.sig-strong-sell {{display:inline-block;padding:3px 10px;border-radius:20px;background:rgba(239,68,68,.2);color:#ef4444;font-weight:700;font-size:.78rem;border:1px solid rgba(239,68,68,.4);}}

/* Score bar */
.score-wrap {{display:flex;align-items:center;gap:8px;}}
.score-bar  {{flex:1;height:8px;border-radius:4px;background:var(--bdr);overflow:hidden;min-width:60px;}}
.score-fill {{height:100%;border-radius:4px;transition:width .4s ease;}}
.score-val  {{font-size:.85rem;font-weight:700;min-width:36px;text-align:right;font-family:'Space Mono',monospace;}}

/* P&L */
.pnl-pos  {{color:#22c55e!important;font-weight:700;}}
.pnl-neg  {{color:#ef4444!important;font-weight:700;}}
.pnl-zero {{color:var(--txt-sub)!important;font-weight:500;}}

/* Cards */
.stat-box {{text-align:center;padding:14px;background:var(--bg-card);border-radius:12px;border:1px solid var(--bdr);}}
.stat-box .val {{font-size:1.5rem;font-weight:800;color:var(--txt);}}
.stat-box .lbl {{font-size:.68rem;color:var(--txt-sub);text-transform:uppercase;letter-spacing:.07em;margin-top:3px;font-family:'Space Mono',monospace;}}

.ctx-bar {{background:var(--bg-card);border:1px solid var(--bdr);border-radius:12px;padding:10px 18px;margin:8px 0;display:flex;gap:20px;align-items:center;flex-wrap:wrap;font-size:.87rem;}}
.hdr-title {{font-size:1.9rem;font-weight:800;letter-spacing:-.03em;color:var(--txt);}}
.hdr-sub {{font-size:.8rem;color:var(--txt-sub);margin-top:-6px;font-family:'Space Mono',monospace;}}

.lock-loss   {{background:#2d1515;border:2px solid #ef4444;border-radius:10px;padding:12px 18px;text-align:center;color:#ef4444;font-weight:700;}}
.lock-profit {{background:#142d1a;border:2px solid #22c55e;border-radius:10px;padding:12px 18px;text-align:center;color:#22c55e;font-weight:700;}}

.regime-trend    {{display:inline-block;padding:2px 10px;border-radius:20px;background:rgba(59,130,246,.2);color:#60a5fa;font-weight:700;font-size:.78rem;}}
.regime-range    {{display:inline-block;padding:2px 10px;border-radius:20px;background:rgba(245,158,11,.2);color:#fbbf24;font-weight:700;font-size:.78rem;}}
.regime-volatile {{display:inline-block;padding:2px 10px;border-radius:20px;background:rgba(239,68,68,.2);color:#f87171;font-weight:700;font-size:.78rem;}}
.regime-unknown  {{display:inline-block;padding:2px 10px;border-radius:20px;background:rgba(100,116,139,.2);color:#94a3b8;font-weight:600;font-size:.78rem;}}

.vix-low  {{display:inline-block;padding:2px 10px;border-radius:20px;background:rgba(34,197,94,.15);color:#22c55e;font-weight:700;font-size:.78rem;}}
.vix-mid  {{display:inline-block;padding:2px 10px;border-radius:20px;background:rgba(245,158,11,.15);color:#fbbf24;font-weight:700;font-size:.78rem;}}
.vix-high {{display:inline-block;padding:2px 10px;border-radius:20px;background:rgba(239,68,68,.15);color:#ef4444;font-weight:700;font-size:.78rem;}}

.mode-intraday  {{display:inline-block;padding:3px 12px;border-radius:20px;background:rgba(99,102,241,.2);color:#818cf8;font-weight:700;font-size:.82rem;border:1px solid rgba(99,102,241,.3);}}
.mode-delivery  {{display:inline-block;padding:3px 12px;border-radius:20px;background:rgba(245,158,11,.2);color:#fbbf24;font-weight:700;font-size:.82rem;border:1px solid rgba(245,158,11,.3);}}

/* Signal result rows */
.signal-row {{
    display:grid;
    grid-template-columns: 120px 90px 80px 90px 80px 80px 80px 80px 80px 1fr 90px 90px;
    gap:8px;
    align-items:center;
    padding:8px 14px;
    border-radius:10px;
    margin-bottom:6px;
    border:1px solid var(--bdr);
    font-size:.82rem;
}}
.signal-row:hover {{border-color:var(--accent);}}
.row-header {{
    font-size:.7rem;text-transform:uppercase;letter-spacing:.08em;
    color:var(--txt-sub);font-family:'Space Mono',monospace;
    padding:6px 14px;margin-bottom:4px;
    display:grid;
    grid-template-columns: 120px 90px 80px 90px 80px 80px 80px 80px 80px 1fr 90px 90px;
    gap:8px;
}}
.btn-buy  {{background:linear-gradient(135deg,#22c55e,#16a34a);color:#fff;border:none;border-radius:7px;padding:5px 14px;font-weight:700;cursor:pointer;font-size:.78rem;font-family:'Outfit',sans-serif;}}
.btn-sell {{background:linear-gradient(135deg,#ef4444,#dc2626);color:#fff;border:none;border-radius:7px;padding:5px 14px;font-weight:700;cursor:pointer;font-size:.78rem;font-family:'Outfit',sans-serif;}}
.btn-hold {{background:rgba(99,102,241,.15);color:#818cf8;border:1px solid rgba(99,102,241,.3);border-radius:7px;padding:5px 14px;font-weight:600;font-size:.78rem;font-family:'Outfit',sans-serif;}}

.cap-large  {{display:inline-block;padding:1px 7px;border-radius:10px;background:rgba(59,130,246,.15);color:#60a5fa;font-size:.7rem;font-weight:600;}}
.cap-mid    {{display:inline-block;padding:1px 7px;border-radius:10px;background:rgba(168,85,247,.15);color:#c084fc;font-size:.7rem;font-weight:600;}}
.cap-small  {{display:inline-block;padding:1px 7px;border-radius:10px;background:rgba(245,158,11,.15);color:#fbbf24;font-size:.7rem;font-weight:600;}}
.cap-penny  {{display:inline-block;padding:1px 7px;border-radius:10px;background:rgba(239,68,68,.15);color:#f87171;font-size:.7rem;font-weight:600;}}
.cap-micro  {{display:inline-block;padding:1px 7px;border-radius:10px;background:rgba(100,116,139,.15);color:#94a3b8;font-size:.7rem;font-weight:600;}}
</style>
""", unsafe_allow_html=True)

# ================================
# SOUND
# ================================
SOUND_JS = """<script>
function playSignalBeep(){
    try{var c=new(window.AudioContext||window.webkitAudioContext)();
    function b(f,s,d,v){var o=c.createOscillator(),g=c.createGain();o.connect(g);g.connect(c.destination);
    o.type='sine';o.frequency.value=f;g.gain.setValueAtTime(v||.3,c.currentTime+s);
    g.gain.exponentialRampToValueAtTime(.001,c.currentTime+s+d);o.start(c.currentTime+s);o.stop(c.currentTime+s+d+.1);}
    b(880,0,.15,.4);b(1100,.18,.15,.35);b(1320,.36,.25,.3);}catch(e){}}
window._orbSigCnt=window._orbSigCnt||0;
function checkAndBeep(n){if(n>window._orbSigCnt){playSignalBeep();window._orbSigCnt=n;}}
</script>"""
st.components.v1.html(SOUND_JS, height=0)

# ================================
# PRESETS — Extended with Mid/Small/Penny
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
    "Bank Nifty": [
        "HDFCBANK.NS","ICICIBANK.NS","KOTAKBANK.NS","AXISBANK.NS","SBIN.NS",
        "INDUSINDBK.NS","BANDHANBNK.NS","FEDERALBNK.NS","IDFCFIRSTB.NS","PNB.NS",
        "BANKBARODA.NS","CANBK.NS","UNIONBANK.NS",
    ],
    "IT Sector": [
        "TCS.NS","INFOSYS.NS","WIPRO.NS","HCLTECH.NS","TECHM.NS",
        "MPHASIS.NS","PERSISTENT.NS","COFORGE.NS","OFSS.NS","KPITTECH.NS",
    ],
    "Pharma Sector": [
        "SUNPHARMA.NS","DRREDDY.NS","CIPLA.NS","DIVISLAB.NS","LUPIN.NS",
        "AUROPHARMA.NS","TORNTPHARM.NS","GLENMARK.NS","ALKEM.NS","LAURUSLABS.NS",
    ],
    "Mid Cap Stars": [
        "Dixon.NS","CAMS.NS","KALYANKJIL.NS","ANGELONE.NS","NAUKRI.NS",
        "METROPOLIS.NS","LTTS.NS","MFSL.NS","AFFLE.NS","ROUTE.NS",
        "HAPPSTMNDS.NS","CLEAN.NS","FINE.NS","VBL.NS","GMMPFAUDLR.NS",
        "SUNTV.NS","PVRINOX.NS","IRCTC.NS","POLYCAB.NS","ASTRAL.NS",
    ],
    "Small Cap Gems": [
        "RATNAMANI.NS","GPPL.NS","KRBL.NS","MAHSEAMLES.NS","NIITLTD.NS",
        "CENTURYPLY.NS","BLUESTARCO.NS","SUPPETRO.NS","TATAELXSI.NS","SAPPHIRE.NS",
        "HERITGFOOD.NS","SYRMA.NS","PNBHOUSING.NS","EPIGRAL.NS","JKPAPER.NS",
    ],
    "Penny Stocks (High Risk)": [
        "SUZLON.NS","YESBANK.NS","IDEA.NS","JPPOWER.NS","RPOWER.NS",
        "SAIL.NS","GMRINFRA.NS","IRFC.NS","PFC.NS","RECLTD.NS",
        "NHPC.NS","SJVN.NS","NBCC.NS","BEL.NS","BEML.NS",
    ],
    "Custom (Enter Below)": [],
}

SECTOR_MAP = {
    "TCS.NS":"IT","INFOSYS.NS":"IT","WIPRO.NS":"IT","HCLTECH.NS":"IT","TECHM.NS":"IT",
    "MPHASIS.NS":"IT","PERSISTENT.NS":"IT","COFORGE.NS":"IT","OFSS.NS":"IT",
    "HDFCBANK.NS":"Bank","ICICIBANK.NS":"Bank","KOTAKBANK.NS":"Bank","AXISBANK.NS":"Bank","SBIN.NS":"Bank",
    "INDUSINDBK.NS":"Bank","BANDHANBNK.NS":"Bank","FEDERALBNK.NS":"Bank","PNB.NS":"Bank",
    "SUNPHARMA.NS":"Pharma","DRREDDY.NS":"Pharma","CIPLA.NS":"Pharma","DIVISLAB.NS":"Pharma",
    "MARUTI.NS":"Auto","TATAMOTORS.NS":"Auto","BAJAJ-AUTO.NS":"Auto","HEROMOTOCO.NS":"Auto",
    "RELIANCE.NS":"Energy","ONGC.NS":"Energy","BPCL.NS":"Energy","NTPC.NS":"Energy",
    "TATASTEEL.NS":"Metals","JSWSTEEL.NS":"Metals","HINDALCO.NS":"Metals","COALINDIA.NS":"Metals",
    "DIXON.NS":"Electronics","POLYCAB.NS":"Electronics",
    "IRCTC.NS":"Travel","PVRINOX.NS":"Media",
    "SUZLON.NS":"Energy","YESBANK.NS":"Bank","IDEA.NS":"Telecom",
}

# Cap classification by typical price range and name list
LARGE_CAP_SYMBOLS = {
    "RELIANCE.NS","TCS.NS","HDFCBANK.NS","BHARTIARTL.NS","ICICIBANK.NS","INFOSYS.NS",
    "SBIN.NS","WIPRO.NS","AXISBANK.NS","LT.NS","KOTAKBANK.NS","HCLTECH.NS","BAJFINANCE.NS",
    "ASIANPAINT.NS","MARUTI.NS","TITAN.NS","SUNPHARMA.NS","NTPC.NS","POWERGRID.NS",
    "ULTRACEMCO.NS","NESTLEIND.NS","TATAMOTORS.NS","TATASTEEL.NS","TECHM.NS","ADANIENT.NS",
    "ADANIPORTS.NS","DRREDDY.NS","CIPLA.NS","HEROMOTOCO.NS","EICHERMOT.NS","BAJAJFINSV.NS",
}

MID_CAP_SYMBOLS = {
    "DIXON.NS","CAMS.NS","KALYANKJIL.NS","ANGELONE.NS","NAUKRI.NS","METROPOLIS.NS",
    "LTTS.NS","MFSL.NS","AFFLE.NS","ROUTE.NS","HAPPSTMNDS.NS","VBL.NS","IRCTC.NS",
    "POLYCAB.NS","ASTRAL.NS","PVRINOX.NS","SUNTV.NS",
}

PENNY_SYMBOLS = {
    "SUZLON.NS","YESBANK.NS","IDEA.NS","JPPOWER.NS","RPOWER.NS","GMRINFRA.NS",
}

PERSISTENCE_FILE = "orb_session_v5.json"
WATCHLIST_FILE   = "orb_watchlist_v5.json"
PORTFOLIO_FILE   = "orb_portfolio_v5.json"

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
refresh_ms = 30_000 if market_open else 300_000
st_autorefresh(interval=refresh_ms, key="smart_refresh_v5")

# ================================
# SESSION STATE
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
        "signal_state": {},
        "fetch_cache": {},
        "market_regime": "Unknown",
        "portfolio": {},
        "dark_mode": True,
        "scan_mode": "Intraday (ORB)",
        "manual_trades": {},   # {symbol: {"qty": int, "buy_price": float, "buy_time": str}}
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ================================
# PERSISTENCE
# ================================
def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE) as f: return json.load(f)
        except: return {}
    return {}

def save_portfolio(data):
    try:
        with open(PORTFOLIO_FILE, "w") as f: json.dump(data, f, indent=2, default=str)
    except: pass

if not st.session_state.portfolio:
    st.session_state.portfolio = load_portfolio()

def save_session():
    try:
        data = {
            "capital": st.session_state.capital,
            "initial_capital": st.session_state.initial_capital,
            "active_trades": st.session_state.active_trades,
            "closed_trades": st.session_state.closed_trades,
            "daily_pnl": st.session_state.daily_pnl,
            "trading_locked": st.session_state.trading_locked,
            "lock_reason": st.session_state.lock_reason,
            "equity": [{"time": str(e["time"]), "capital": e["capital"]} for e in st.session_state.equity],
            "signal_state": st.session_state.signal_state,
            "manual_trades": st.session_state.manual_trades,
        }
        with open(PERSISTENCE_FILE, "w") as f: json.dump(data, f, default=str)
    except: pass

def load_session():
    if not os.path.exists(PERSISTENCE_FILE): return
    try:
        with open(PERSISTENCE_FILE) as f: data = json.load(f)
        if not st.session_state.closed_trades and not st.session_state.active_trades:
            st.session_state.capital         = data.get("capital", 100_000)
            st.session_state.initial_capital = data.get("initial_capital", 100_000)
            st.session_state.active_trades   = data.get("active_trades", {})
            st.session_state.closed_trades   = data.get("closed_trades", [])
            st.session_state.daily_pnl       = data.get("daily_pnl", 0.0)
            st.session_state.trading_locked  = data.get("trading_locked", False)
            st.session_state.lock_reason     = data.get("lock_reason", "")
            st.session_state.signal_state    = data.get("signal_state", {})
            st.session_state.manual_trades   = data.get("manual_trades", {})
            raw_eq = data.get("equity", [])
            st.session_state.equity = [{"time": pd.to_datetime(e["time"]), "capital": e["capital"]} for e in raw_eq]
    except: pass

load_session()

def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE) as f: return json.load(f)
        except: return {}
    return {}

def save_watchlist(data):
    try:
        with open(WATCHLIST_FILE, "w") as f: json.dump(data, f, indent=2)
    except: pass

saved_watchlist = load_watchlist()

# ================================
# CACHE
# ================================
def _cache_ttl(interval):
    return {"5m": 25, "15m": 60, "1h": 300, "1d": 300, "1wk": 600}.get(interval, 60)

def _cache_key(symbol, interval):
    return f"{symbol}_{interval}"

def cache_get(symbol, interval):
    key = _cache_key(symbol, interval)
    entry = st.session_state.fetch_cache.get(key)
    if entry and (time.time() - entry["ts"]) < _cache_ttl(interval):
        return entry["df"]
    return None

def cache_set(symbol, interval, df):
    key = _cache_key(symbol, interval)
    st.session_state.fetch_cache[key] = {"df": df, "ts": time.time()}

def snapshot_cache():
    return dict(st.session_state.fetch_cache)

# ================================
# SIDEBAR
# ================================
with st.sidebar:
    st.markdown("## ⚙️ Scanner Settings")
    c1, c2 = st.columns([3,1])
    with c1: st.markdown("🌙 **Dark Mode**")
    with c2:
        if st.button("Toggle", key="dm_toggle"):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()

    # SCAN MODE
    st.markdown("### 🎯 Scan Mode")
    scan_mode = st.radio("Trading Style", ["Intraday (ORB)", "Delivery / Swing", "Both"], horizontal=False)
    st.session_state.scan_mode = scan_mode

    st.markdown("### 📋 Symbol Selection")
    preset_choice = st.selectbox("Choose Preset", list(PRESETS.keys()), index=0)

    if preset_choice == "Custom (Enter Below)":
        custom_raw = st.text_area("Enter tickers (one per line)", placeholder="RELIANCE\nTCS", height=80)
        raw_list = [s.strip().upper() for s in custom_raw.replace(",","\n").splitlines() if s.strip()]
        symbols_pool = [s if s.endswith(".NS") or s.endswith(".BO") else s+".NS" for s in raw_list]
    else:
        symbols_pool = PRESETS[preset_choice]

    uploaded_csv = st.file_uploader("📂 Import CSV", type=["csv"])
    csv_symbols = []
    if uploaded_csv:
        try:
            df_csv = pd.read_csv(uploaded_csv)
            col = next((c for c in df_csv.columns if "symbol" in c.lower()), df_csv.columns[0])
            csv_symbols = [s.strip().upper() + (".NS" if not s.strip().upper().endswith((".NS",".BO")) else "")
                           for s in df_csv[col].dropna().astype(str).tolist()]
            st.success(f"✅ {len(csv_symbols)} symbols loaded")
        except Exception as e:
            st.error(f"CSV error: {e}")
    if csv_symbols:
        symbols_pool = list(dict.fromkeys(symbols_pool + csv_symbols))

    default_saved = saved_watchlist.get(preset_choice, [])
    default_sel = default_saved if (default_saved and all(d in symbols_pool for d in default_saved)) else (symbols_pool[:10] if len(symbols_pool) > 10 else symbols_pool)

    selected_symbols = st.multiselect(
        f"Select symbols ({len(symbols_pool)} available)", symbols_pool, default=default_sel
    ) if symbols_pool else []

    if selected_symbols != saved_watchlist.get(preset_choice, []):
        saved_watchlist[preset_choice] = selected_symbols
        save_watchlist(saved_watchlist)

    extra_raw = st.text_input("➕ Extra tickers", placeholder="ZOMATO,PAYTM")
    if extra_raw.strip():
        extras = [s.strip().upper() + ("" if s.strip().upper().endswith(".NS") else ".NS")
                  for s in extra_raw.split(",") if s.strip()]
        selected_symbols = list(dict.fromkeys(selected_symbols + extras))

    st.caption(f"**{len(selected_symbols)}** symbols selected")
    st.divider()

    st.markdown("### 📐 Strategy Parameters")
    orb_minutes    = st.number_input("ORB Minutes", 5, 60, 15)
    ema_period     = st.number_input("EMA Period (5m)", 5, 100, 20)
    ema_15m_period = st.number_input("EMA Period (15m)", 5, 100, 20)
    ema_1h_period  = st.number_input("EMA Period (1h)", 5, 50, 20)
    atr_period     = st.number_input("ATR Period", 5, 30, 14)
    rsi_period     = st.number_input("RSI Period", 5, 30, 14)
    st_atr_mult    = st.slider("Supertrend ATR Mult", 1.0, 5.0, 3.0, 0.5)

    st.divider()
    st.markdown("### 📦 Delivery / Swing Settings")
    delivery_ema_wk  = st.number_input("Weekly EMA Period", 5, 50, 20)
    delivery_rsi_min = st.slider("Delivery RSI Min (Buy)", 30, 60, 45)
    delivery_vol_min = st.slider("Delivery Vol Ratio Min", 1.0, 3.0, 1.2, 0.1)
    min_52w_pct      = st.slider("Min from 52W Low (%)", 0, 30, 5)   # not too deep in hole
    max_52w_pct      = st.slider("Max from 52W High (%)", 5, 80, 40) # not too extended

    st.divider()
    st.markdown("### 🛡️ Stop Loss")
    sl_strategy    = st.selectbox("SL Method", ["Supertrend","Chandelier Exit","Fixed ATR","Swing High/Low","Fixed %"])
    sl_atr_mult    = st.slider("SL ATR Multiplier", 1.0, 5.0, 2.0, 0.25)
    swing_lookback = st.number_input("Swing Lookback Bars", 3, 20, 5)
    trail_pct      = st.slider("Trail %", 0.1, 2.0, 0.5, 0.05) / 100

    st.divider()
    st.markdown("### 💰 Risk Management")
    initial_capital = st.number_input("Initial Capital (₹)", 10_000, 10_000_000, 100_000, step=10_000)
    if st.button("🔁 Reset Capital"):
        st.session_state.capital = initial_capital
        st.session_state.initial_capital = initial_capital
        st.session_state.active_trades = {}
        st.session_state.closed_trades = []
        st.session_state.equity = []
        st.session_state.daily_pnl = 0.0
        st.session_state.trading_locked = False
        st.session_state.lock_reason = ""
        st.session_state.signal_state = {}
        st.session_state.manual_trades = {}
        save_session()
        st.rerun()

    risk_pct     = st.slider("Risk per Trade (%)", 0.5, 5.0, 1.0, 0.1)
    max_trades   = st.number_input("Max Concurrent Trades", 1, 30, 5)
    max_risk_pct = st.slider("Max Portfolio Risk (%)", 1.0, 10.0, 5.0, 0.5)

    st.divider()
    st.markdown("### 📅 Daily Limits")
    daily_loss_limit_pct    = st.slider("Daily Loss Limit (%)", 0.5, 10.0, 3.0, 0.5)
    daily_profit_target_pct = st.slider("Daily Profit Target (%)", 1.0, 20.0, 5.0, 0.5)

    st.divider()
    st.markdown("### 🔍 Signal Filters")
    min_vol_ratio = st.slider("Min Volume Ratio", 1.0, 5.0, 1.5, 0.1)
    min_body_pct  = st.slider("Min Candle Body %", 0.3, 0.9, 0.5, 0.05)
    min_ema_dist  = st.slider("Min EMA Distance %", 0.1, 2.0, 0.3, 0.1) / 100
    max_ema_dist  = st.slider("Max EMA Distance %", 0.5, 5.0, 3.0, 0.1) / 100
    min_atr_ratio = st.slider("Min ATR Ratio %", 0.1, 1.0, 0.2, 0.05) / 100
    rsi_buy_min   = st.slider("RSI Min for BUY", 40, 70, 50)
    rsi_sell_max  = st.slider("RSI Max for SELL", 30, 60, 50)
    use_mtf       = st.checkbox("15m EMA Confirmation", True)
    use_3tf       = st.checkbox("1h EMA Confluence", True)
    use_macd      = st.checkbox("MACD Filter", True)
    use_regime    = st.checkbox("Market Regime Filter", True)
    use_nifty_filter   = st.checkbox("Nifty Index Filter", True)
    use_vix_sizing     = st.checkbox("VIX-Based Position Sizing", True)
    use_gap_detect     = st.checkbox("Gap Detection", True)
    gap_pct            = st.slider("Gap Threshold (%)", 0.5, 3.0, 1.0, 0.1) / 100
    use_partial        = st.checkbox("Partial Profit @ 1×ATR", True)

    st.divider()
    st.markdown("### 📡 Alerts")
    with st.expander("📱 Telegram"):
        tg_token   = st.text_input("Bot Token", type="password")
        tg_chat_id = st.text_input("Chat ID")
        send_tg    = st.checkbox("Enable Telegram", False)
    with st.expander("🎮 Discord"):
        discord_webhook = st.text_input("Discord Webhook URL", type="password")
        send_discord    = st.checkbox("Enable Discord", False)

    max_retries = st.number_input("Max Fetch Retries", 1, 5, 3)
    show_errors = st.checkbox("Show fetch errors", False)


# ================================
# ALERT DISPATCHER
# ================================
def send_alert(msg):
    if send_tg and tg_token and tg_chat_id:
        try: requests.post(f"https://api.telegram.org/bot{tg_token}/sendMessage",
                           data={"chat_id": tg_chat_id, "text": msg, "parse_mode":"HTML"}, timeout=5)
        except: pass
    if send_discord and discord_webhook:
        try: requests.post(discord_webhook, json={"content": msg}, timeout=5)
        except: pass


# ================================
# FETCH
# ================================
def _flatten_columns(df):
    if df is None or df.empty: return df
    if isinstance(df.columns, pd.MultiIndex):
        lvl1 = df.columns.get_level_values(1).unique().tolist()
        df = df.xs(lvl1[0], axis=1, level=1) if len(lvl1) > 1 else df
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).strip().title() for c in df.columns]
    rename_map = {"Adj Close":"Close","Adj_Close":"Close","Adjclose":"Close","Adj close":"Close"}
    df.rename(columns=rename_map, inplace=True)
    return df

def fetch(symbol, interval="5m", period="5d", use_cache=True, _cache_snapshot=None):
    required_cols = {"Open","High","Low","Close","Volume"}
    if _cache_snapshot is None: _cache_snapshot = {}
    if use_cache:
        key = _cache_key(symbol, interval)
        entry = _cache_snapshot.get(key)
        if entry and (time.time() - entry["ts"]) < _cache_ttl(interval):
            return symbol, entry["df"], None, None

    strategies = [{"interval":interval,"period":period},
                  {"interval":interval,"period":"5d"},
                  {"interval":interval,"period":"1mo"}]
    if interval == "1d":  strategies = [{"interval":"1d","period":"1y"}]
    if interval == "1wk": strategies = [{"interval":"1wk","period":"2y"}]
    if interval == "1h":  strategies = [{"interval":"1h","period":"5d"},{"interval":"1h","period":"1mo"}]

    last_err = "Unknown"
    for attempt in range(int(max_retries)):
        for strat in strategies:
            try:
                raw = yf.download(symbol, interval=strat["interval"], period=strat["period"],
                                  progress=False, auto_adjust=True, actions=False)
                if raw is None or raw.empty: last_err = "Empty"; continue
                df = _flatten_columns(raw.copy())
                missing = required_cols - set(df.columns)
                if missing: last_err = f"Missing:{missing}"; continue
                df.dropna(subset=["Open","High","Low","Close"], how="all", inplace=True)
                if len(df) < 5: last_err = f"Too few: {len(df)}"; continue
                if not isinstance(df.index, pd.DatetimeIndex):
                    df.index = pd.to_datetime(df.index)
                if df.index.tz is not None:
                    df.index = df.index.tz_convert("Asia/Kolkata").tz_localize(None)
                df.sort_index(inplace=True)
                new_entry = {"df": df, "ts": time.time()}
                return symbol, df, None, (_cache_key(symbol, interval), new_entry)
            except Exception as e:
                last_err = f"{type(e).__name__}:{str(e)[:80]}"; continue
        if attempt < int(max_retries)-1:
            time.sleep((2**attempt) + random.uniform(0,1))
    return symbol, None, last_err, None

def _apply_cache_write(result):
    cw = result[3] if len(result) == 4 else None
    if cw:
        key, entry = cw
        st.session_state.fetch_cache[key] = entry


# ================================
# MARKET CONTEXT
# ================================
@st.cache_data(ttl=120)
def fetch_nifty_vix():
    result = {"nifty_change": 0.0, "nifty_price": 0.0, "vix": 0.0}
    try:
        _, nifty, _, _ = fetch("^NSEI", interval="1d", period="5d", use_cache=False, _cache_snapshot={})
        if nifty is not None and len(nifty) >= 2:
            result["nifty_price"]  = float(nifty["Close"].iloc[-1])
            result["nifty_change"] = float(nifty["Close"].iloc[-1] - nifty["Close"].iloc[-2])
    except: pass
    try:
        _, vix, _, _ = fetch("^INDIAVIX", interval="1d", period="5d", use_cache=False, _cache_snapshot={})
        if vix is not None and not vix.empty:
            result["vix"] = float(vix["Close"].iloc[-1])
    except: pass
    return result

mkt_ctx = fetch_nifty_vix()
st.session_state.nifty_trend = mkt_ctx["nifty_change"]
st.session_state.vix_value   = mkt_ctx["vix"]


# ================================
# MARKET REGIME
# ================================
def detect_market_regime(df):
    if df is None or len(df) < 20: return "Unknown"
    try:
        high, low, close = df["High"], df["Low"], df["Close"]
        tr = pd.concat([high-low, (high-close.shift(1)).abs(), (low-close.shift(1)).abs()], axis=1).max(axis=1)
        atr14 = tr.rolling(14, min_periods=1).mean()
        dm_plus  = (high.diff()).clip(lower=0)
        dm_minus = (-low.diff()).clip(lower=0)
        dp_arr = np.where(dm_plus > dm_minus, dm_plus, 0)
        dm_arr = np.where(pd.Series(dm_minus) > pd.Series(dm_plus), dm_minus, 0)
        di_p = 100 * pd.Series(dp_arr).rolling(14, min_periods=1).mean() / atr14.replace(0, np.nan).fillna(1)
        di_m = 100 * pd.Series(dm_arr).rolling(14, min_periods=1).mean() / atr14.replace(0, np.nan).fillna(1)
        dx   = 100 * (di_p - di_m).abs() / (di_p + di_m).replace(0, np.nan).fillna(1)
        adx  = dx.rolling(14, min_periods=1).mean().iloc[-1]
        sma20 = close.rolling(20, min_periods=5).mean()
        std20 = close.rolling(20, min_periods=5).std()
        bb_w  = (2 * std20 / sma20.replace(0, np.nan).fillna(1)).iloc[-1]
        if adx > 25: return "Trending"
        elif bb_w > 0.04: return "Volatile"
        else: return "Ranging"
    except: return "Unknown"


# ================================
# INDICATORS
# ================================
def add_indicators(df):
    df = df.copy()
    close, high, low, vol = df["Close"], df["High"], df["Low"], df["Volume"]
    df["EMA"]     = close.ewm(span=ema_period, adjust=False).mean()
    prev_close    = close.shift(1)
    df["TR"]      = pd.concat([high-low, (high-prev_close).abs(), (low-prev_close).abs()], axis=1).max(axis=1)
    df["ATR"]     = df["TR"].rolling(atr_period, min_periods=1).mean()
    df["Vol_Avg"] = vol.rolling(20, min_periods=5).mean()
    body = (close - df["Open"]).abs()
    rng  = (high - low).replace(0, np.nan).fillna(1e-9)
    df["BodyPct"] = (body / rng).clip(0, 1)
    delta = close.diff()
    gain, loss = delta.clip(lower=0), (-delta).clip(lower=0)
    avg_g = gain.ewm(com=rsi_period-1, adjust=False).mean()
    avg_l = loss.ewm(com=rsi_period-1, adjust=False).mean()
    rs = avg_g / avg_l.replace(0, np.nan).fillna(1e-9)
    df["RSI"]      = 100 - (100/(1+rs))
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["MACD"]      = ema12 - ema26
    df["MACD_sig"]  = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_sig"]
    hl2 = (high + low) / 2
    ub = (hl2 + st_atr_mult * df["ATR"]).values.copy()
    lb = (hl2 - st_atr_mult * df["ATR"]).values.copy()
    cl = close.values
    st_dir = np.ones(len(df), dtype=int)
    st_val = np.zeros(len(df))
    for i in range(1, len(df)):
        if cl[i-1] <= ub[i-1]: ub[i] = min(ub[i], ub[i-1])
        if cl[i-1] >= lb[i-1]: lb[i] = max(lb[i], lb[i-1])
        if st_dir[i-1] == -1 and cl[i] > ub[i]:  st_dir[i] = 1
        elif st_dir[i-1] == 1 and cl[i] < lb[i]: st_dir[i] = -1
        else: st_dir[i] = st_dir[i-1]
        st_val[i] = lb[i] if st_dir[i] == 1 else ub[i]
    df["ST_dir"] = st_dir
    df["ST_val"] = st_val
    return df

def add_indicators_15m(df):
    df = df.copy(); df["EMA15"] = df["Close"].ewm(span=ema_15m_period, adjust=False).mean(); return df

def add_indicators_1h(df):
    df = df.copy(); df["EMA1H"] = df["Close"].ewm(span=ema_1h_period, adjust=False).mean(); return df

def add_indicators_weekly(df):
    """For delivery mode — weekly indicators"""
    df = df.copy()
    close = df["Close"]
    df["EMA_W"]   = close.ewm(span=int(delivery_ema_wk), adjust=False).mean()
    delta = close.diff()
    gain, loss = delta.clip(lower=0), (-delta).clip(lower=0)
    avg_g = gain.ewm(com=13, adjust=False).mean()
    avg_l = loss.ewm(com=13, adjust=False).mean()
    rs = avg_g / avg_l.replace(0, np.nan).fillna(1e-9)
    df["RSI_W"] = 100 - (100/(1+rs))
    df["Vol_Avg_W"] = df["Volume"].rolling(20, min_periods=5).mean()
    high, low = df["High"], df["Low"]
    tr = pd.concat([high-low, (high-close.shift(1)).abs(), (low-close.shift(1)).abs()], axis=1).max(axis=1)
    df["ATR_W"] = tr.rolling(14, min_periods=1).mean()
    df["SMA20_W"] = close.rolling(20, min_periods=5).mean()
    df["SMA50_W"] = close.rolling(50, min_periods=10).mean()
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["MACD_W"]     = ema12 - ema26
    df["MACD_sig_W"] = df["MACD_W"].ewm(span=9, adjust=False).mean()
    df["MACD_hist_W"] = df["MACD_W"] - df["MACD_sig_W"]
    return df


# ================================
# ORB RANGE HELPER
# ================================
def get_orb_range(df):
    df = df.copy(); df.index = pd.to_datetime(df.index)
    last_date = df.index.normalize().max()
    day_df = df[df.index.normalize() == last_date].copy()
    day_df["_time"] = day_df.index.time
    market_start = dtime(9, 15)
    orb_end_time = (datetime.combine(last_date.date(), market_start) + timedelta(minutes=int(orb_minutes))).time()
    orb_df = day_df[day_df["_time"] <= orb_end_time]
    return orb_df, day_df


# ================================
# CAP CLASSIFICATION
# ================================
def get_cap_category(symbol, price):
    if symbol in LARGE_CAP_SYMBOLS: return "Large"
    if symbol in MID_CAP_SYMBOLS:   return "Mid"
    if symbol in PENNY_SYMBOLS:     return "Penny"
    if price is not None:
        if price < 20:    return "Penny"
        elif price < 100: return "Small"
        elif price < 500: return "Small"
        else: return "Mid"
    return "Mid"

def get_cap_css(cap):
    return {"Large":"cap-large","Mid":"cap-mid","Small":"cap-small","Penny":"cap-penny"}.get(cap, "cap-micro")


# ================================
# INTRADAY METRICS
# ================================
def compute_intraday_metrics(df_5m, df_15m=None, df_1h=None):
    metrics = {
        "orb_high": None, "orb_low": None, "last_price": None,
        "atr": None, "vol_ratio": None, "rsi": None, "body_pct": None,
        "ema": None, "macd_hist": None, "gap_pct": None,
        "mtf_ok": None, "tf3_ok": None, "regime": "Unknown",
        "direction": None, "52w_high": None, "52w_low": None,
    }
    if df_5m is None or len(df_5m) < 10: return metrics
    df = add_indicators(df_5m)
    df.index = pd.to_datetime(df.index)
    orb_df, day_df = get_orb_range(df)
    if len(orb_df) < 1:
        orb_df = df.iloc[:max(2, int(orb_minutes // 5))]
        day_df = df
    metrics["orb_high"]   = round(float(orb_df["High"].max()), 2)
    metrics["orb_low"]    = round(float(orb_df["Low"].min()), 2)
    metrics["last_price"] = round(float(df["Close"].iloc[-1]), 2)
    if not pd.isna(df["ATR"].iloc[-1]):
        metrics["atr"] = round(float(df["ATR"].iloc[-1]), 2)
    if not pd.isna(df["Vol_Avg"].iloc[-1]) and float(df["Vol_Avg"].iloc[-1]) > 0:
        metrics["vol_ratio"] = round(float(df["Volume"].iloc[-1]) / float(df["Vol_Avg"].iloc[-1]), 2)
    if not pd.isna(df["RSI"].iloc[-1]):
        metrics["rsi"] = round(float(df["RSI"].iloc[-1]), 1)
    if not pd.isna(df["BodyPct"].iloc[-1]):
        metrics["body_pct"] = round(float(df["BodyPct"].iloc[-1]), 2)
    if not pd.isna(df["EMA"].iloc[-1]):
        metrics["ema"] = round(float(df["EMA"].iloc[-1]), 2)
    if not pd.isna(df["MACD_hist"].iloc[-1]):
        metrics["macd_hist"] = round(float(df["MACD_hist"].iloc[-1]), 4)
    try:
        dates = df.index.normalize().unique()
        if len(dates) >= 2:
            t_open = float(df[df.index.normalize()==dates[-1]]["Open"].iloc[0])
            y_close = float(df[df.index.normalize()==dates[-2]]["Close"].iloc[-1])
            if y_close > 0:
                metrics["gap_pct"] = round((t_open - y_close) / y_close * 100, 2)
    except: metrics["gap_pct"] = 0.0
    if use_3tf and df_1h is not None and len(df_1h) >= ema_1h_period + 2:
        df1h = add_indicators_1h(df_1h)
        metrics["tf3_ok"] = float(df1h["EMA1H"].iloc[-1]) > float(df1h["EMA1H"].iloc[-2])
    if use_mtf and df_15m is not None and len(df_15m) >= ema_15m_period + 2:
        df15 = add_indicators_15m(df_15m)
        metrics["mtf_ok"] = float(df15["EMA15"].iloc[-1]) > float(df15["EMA15"].iloc[-2])
    metrics["regime"] = detect_market_regime(df)
    last = metrics["last_price"]
    if metrics["orb_high"] and metrics["orb_low"]:
        if last > metrics["orb_high"]:   metrics["direction"] = "BUY"
        elif last < metrics["orb_low"]:  metrics["direction"] = "SELL"
        else:                            metrics["direction"] = "NEUTRAL"
    return metrics


# ================================
# DELIVERY METRICS
# ================================
def compute_delivery_metrics(df_daily, df_weekly=None):
    metrics = {
        "last_price": None, "atr": None, "vol_ratio": None, "rsi": None,
        "macd_hist": None, "ema": None, "direction": None, "regime": "Unknown",
        "52w_high": None, "52w_low": None, "from_52w_low_pct": None,
        "from_52w_high_pct": None, "trend": None,
        "weekly_rsi": None, "weekly_macd_hist": None, "sma20_above_sma50": None,
        "price_above_ema": None, "vol_ratio_d": None,
    }
    if df_daily is None or len(df_daily) < 30: return metrics
    df = add_indicators(df_daily.copy())
    close = df["Close"]
    metrics["last_price"] = round(float(close.iloc[-1]), 2)
    if not pd.isna(df["ATR"].iloc[-1]):
        metrics["atr"] = round(float(df["ATR"].iloc[-1]), 2)
    if not pd.isna(df["Vol_Avg"].iloc[-1]) and float(df["Vol_Avg"].iloc[-1]) > 0:
        metrics["vol_ratio"] = round(float(df["Volume"].iloc[-1]) / float(df["Vol_Avg"].iloc[-1]), 2)
    if not pd.isna(df["RSI"].iloc[-1]):
        metrics["rsi"] = round(float(df["RSI"].iloc[-1]), 1)
    if not pd.isna(df["EMA"].iloc[-1]):
        metrics["ema"] = round(float(df["EMA"].iloc[-1]), 2)
    if not pd.isna(df["MACD_hist"].iloc[-1]):
        metrics["macd_hist"] = round(float(df["MACD_hist"].iloc[-1]), 4)

    # 52-week high/low
    lookback = min(252, len(df))
    recent = close.iloc[-lookback:]
    w52_high = float(recent.max())
    w52_low  = float(recent.min())
    metrics["52w_high"] = round(w52_high, 2)
    metrics["52w_low"]  = round(w52_low, 2)
    last = metrics["last_price"]
    if w52_low > 0:
        metrics["from_52w_low_pct"]  = round((last - w52_low)  / w52_low  * 100, 1)
    if w52_high > 0:
        metrics["from_52w_high_pct"] = round((last - w52_high) / w52_high * 100, 1)

    # Daily trend: price > SMA50 and SMA20 > SMA50
    if "SMA20_W" not in df.columns:
        df["SMA20"] = close.rolling(20, min_periods=5).mean()
        df["SMA50"] = close.rolling(50, min_periods=10).mean()
    else:
        df["SMA20"] = df["SMA20_W"]
        df["SMA50"] = df["SMA50_W"]

    try:
        sma20 = float(df["SMA20"].iloc[-1])
        sma50 = float(df["SMA50"].iloc[-1])
        metrics["sma20_above_sma50"] = sma20 > sma50
        metrics["price_above_ema"]   = last > float(df["EMA"].iloc[-1])
        if last > sma20 and sma20 > sma50: metrics["trend"] = "Uptrend"
        elif last < sma20 and sma20 < sma50: metrics["trend"] = "Downtrend"
        else: metrics["trend"] = "Sideways"
    except: metrics["trend"] = "Unknown"

    # Weekly
    if df_weekly is not None and len(df_weekly) >= 20:
        dfw = add_indicators_weekly(df_weekly.copy())
        if not pd.isna(dfw["RSI_W"].iloc[-1]):
            metrics["weekly_rsi"] = round(float(dfw["RSI_W"].iloc[-1]), 1)
        if not pd.isna(dfw["MACD_hist_W"].iloc[-1]):
            metrics["weekly_macd_hist"] = round(float(dfw["MACD_hist_W"].iloc[-1]), 4)
        if float(dfw["Vol_Avg_W"].iloc[-1]) > 0:
            metrics["vol_ratio_d"] = round(float(dfw["Volume"].iloc[-1]) / float(dfw["Vol_Avg_W"].iloc[-1]), 2)

    metrics["regime"] = detect_market_regime(df)
    # Delivery direction
    rsi = metrics["rsi"] or 50
    macd_hist = metrics["macd_hist"] or 0
    trend = metrics["trend"]
    if trend == "Uptrend" and rsi >= int(delivery_rsi_min) and macd_hist > 0:
        metrics["direction"] = "BUY"
    elif trend == "Downtrend" and rsi <= 55 and macd_hist < 0:
        metrics["direction"] = "SELL"
    else:
        metrics["direction"] = "NEUTRAL"
    return metrics


# ================================
# SCORE OUT OF 100
# ================================
def compute_intraday_score(metrics):
    """Returns integer 0-100"""
    direction = metrics.get("direction", "NEUTRAL")
    if direction == "NEUTRAL" or direction is None: return 25

    vol_ratio = metrics.get("vol_ratio") or 0
    rsi       = metrics.get("rsi") or 50
    body_pct  = metrics.get("body_pct") or 0
    mtf_ok    = metrics.get("mtf_ok")
    tf3_ok    = metrics.get("tf3_ok")
    macd_hist = metrics.get("macd_hist") or 0
    gap_pct   = metrics.get("gap_pct") or 0
    regime    = metrics.get("regime", "Unknown")

    score = 0

    # Volume (0-20)
    if vol_ratio >= 3.0:       score += 20
    elif vol_ratio >= 2.0:     score += 15
    elif vol_ratio >= 1.5:     score += 10
    elif vol_ratio >= 1.2:     score += 5

    # RSI (0-20)
    if direction == "BUY":
        if 55 <= rsi <= 75:    score += 20
        elif 50 <= rsi < 55:   score += 14
        elif 45 <= rsi < 50:   score += 8
        elif rsi > 75:         score += 5  # overbought penalty
    else:
        if 25 <= rsi <= 45:    score += 20
        elif 45 < rsi <= 50:   score += 14
        elif 50 < rsi <= 55:   score += 8

    # Body (0-15)
    if body_pct >= 0.8:        score += 15
    elif body_pct >= 0.65:     score += 10
    elif body_pct >= 0.5:      score += 6
    elif body_pct >= 0.35:     score += 3

    # MTF 15m (0-15)
    if mtf_ok is True:         score += 15
    elif mtf_ok is False:      score -= 5

    # 3TF 1h (0-20)
    if tf3_ok is True:         score += 20
    elif tf3_ok is False:      score -= 10

    # MACD (0-10)
    if direction == "BUY"  and macd_hist > 0: score += 10
    elif direction == "SELL" and macd_hist < 0: score += 10

    # Gap bonus (0-5)
    if direction == "BUY"  and gap_pct > 0.5:   score += 5
    elif direction == "SELL" and gap_pct < -0.5: score += 5

    # Regime bonus/penalty (-10 to +5)
    if regime == "Trending": score += 5
    elif regime == "Ranging": score -= 10

    return max(0, min(100, score))


def compute_delivery_score(metrics):
    """Returns integer 0-100 for delivery/swing"""
    direction = metrics.get("direction", "NEUTRAL")
    if direction == "NEUTRAL" or direction is None: return 25

    rsi          = metrics.get("rsi") or 50
    weekly_rsi   = metrics.get("weekly_rsi") or rsi
    macd_hist    = metrics.get("macd_hist") or 0
    wmh          = metrics.get("weekly_macd_hist") or 0
    vol_ratio    = metrics.get("vol_ratio") or 0
    trend        = metrics.get("trend", "Unknown")
    sma20_above  = metrics.get("sma20_above_sma50")
    price_above  = metrics.get("price_above_ema")
    from_52w_low = metrics.get("from_52w_low_pct") or 0
    from_52w_h   = metrics.get("from_52w_high_pct") or 0
    regime       = metrics.get("regime", "Unknown")

    score = 0

    # Trend alignment (0-25)
    if direction == "BUY":
        if trend == "Uptrend":   score += 25
        elif trend == "Sideways": score += 10
    else:
        if trend == "Downtrend": score += 25
        elif trend == "Sideways": score += 10

    # RSI daily (0-15)
    if direction == "BUY":
        if int(delivery_rsi_min) <= rsi <= 70: score += 15
        elif rsi > 70: score += 5
    else:
        if rsi <= 55: score += 15

    # Weekly RSI (0-10)
    if direction == "BUY":
        if 45 <= weekly_rsi <= 70: score += 10
    else:
        if weekly_rsi <= 50: score += 10

    # MACD daily (0-10)
    if direction == "BUY"  and macd_hist > 0: score += 10
    elif direction == "SELL" and macd_hist < 0: score += 10

    # Weekly MACD (0-10)
    if direction == "BUY"  and wmh > 0: score += 10
    elif direction == "SELL" and wmh < 0: score += 10

    # Volume (0-10)
    if vol_ratio >= 2.0:   score += 10
    elif vol_ratio >= 1.5: score += 6
    elif vol_ratio >= 1.2: score += 3

    # SMA structure (0-10)
    if sma20_above is True  and direction == "BUY":  score += 10
    if sma20_above is False and direction == "SELL": score += 10

    # 52W position (0-10)
    if direction == "BUY":
        if int(min_52w_pct) <= from_52w_low <= 60: score += 10
    if direction == "SELL":
        if from_52w_h < -10: score += 10

    # Regime
    if regime == "Trending": score += 5
    elif regime == "Ranging": score -= 5

    return max(0, min(100, score))


# ================================
# SIGNAL LABEL FROM SCORE
# ================================
def score_to_label(score, direction):
    if direction == "NEUTRAL" or direction is None:
        return "⚪ Neutral", "sig-neutral", "row-neutral"
    if direction == "BUY":
        if score >= 80:   return "🟢 Strong Buy",  "sig-strong-buy",  "row-strong-buy"
        elif score >= 65: return "🟢 Buy",          "sig-buy",          "row-buy"
        elif score >= 50: return "🟡 Weak Buy",     "sig-weak-buy",     "row-weak-buy"
        elif score >= 35: return "🔵 Avoid Buy",    "sig-avoid",        "row-avoid"
        else:             return "⚪ Neutral",       "sig-neutral",      "row-neutral"
    else:  # SELL
        if score >= 80:   return "🔴 Strong Sell", "sig-strong-sell", "row-strong-sell"
        elif score >= 65: return "🔴 Sell",         "sig-sell",         "row-sell"
        elif score >= 50: return "🟠 Weak Sell",    "sig-weak-sell",    "row-weak-sell"
        elif score >= 35: return "🔵 Avoid Sell",   "sig-avoid",        "row-avoid"
        else:             return "⚪ Neutral",       "sig-neutral",      "row-neutral"


# ================================
# POSITION SIZE SUGGESTION
# ================================
def suggest_qty(capital, entry_price, sl_price, risk_pct_val=None):
    rp = risk_pct_val or risk_pct
    risk_amount = capital * (rp / 100)
    risk_per_share = abs(entry_price - sl_price)
    if risk_per_share == 0: return 1
    return max(1, int(risk_amount / risk_per_share))

def compute_sl_from_atr(price, atr, direction):
    if direction == "BUY":  return round(price - sl_atr_mult * (atr or price*0.01), 2)
    else:                   return round(price + sl_atr_mult * (atr or price*0.01), 2)


# ================================
# MANUAL TRADE HELPERS
# ================================
def manual_buy(symbol, price, qty):
    st.session_state.manual_trades[symbol] = {
        "qty": qty, "buy_price": price,
        "buy_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_session()

def manual_sell(symbol):
    if symbol not in st.session_state.manual_trades: return 0.0
    trade = st.session_state.manual_trades.pop(symbol)
    cached = cache_get(symbol, "5m") or cache_get(symbol, "1d")
    cur_price = float(cached["Close"].iloc[-1]) if cached is not None else trade["buy_price"]
    pnl = (cur_price - trade["buy_price"]) * trade["qty"]
    st.session_state.closed_trades.append({
        "Symbol": symbol, "Type": "BUY", "Entry": trade["buy_price"],
        "Exit": round(cur_price, 2), "Qty": trade["qty"],
        "PnL (₹)": round(pnl, 2),
        "PnL %": round((pnl / (trade["buy_price"] * trade["qty"])) * 100, 2) if trade["buy_price"] > 0 else 0,
        "Score": "—", "Signal": "Manual", "SL Strategy": "Manual", "Reason": "Manual Sell",
        "Entry Time": trade["buy_time"], "Exit Time": datetime.now().strftime("%H:%M:%S"),
        "Regime": "—", "Note": "", "Symbol_": symbol,
    })
    save_session()
    return pnl


# ================================
# P&L HELPERS
# ================================
def pnl_cls(v):
    if v > 0: return "pnl-pos"
    if v < 0: return "pnl-neg"
    return "pnl-zero"

def fmt_pnl(v, prefix="₹"):
    cls = pnl_cls(v)
    sign = "+" if v >= 0 else ""
    return f'<span class="{cls}">{prefix}{sign}{v:,.2f}</span>'

def score_color(s):
    if s >= 80:   return "#22c55e"
    elif s >= 65: return "#4ade80"
    elif s >= 50: return "#f59e0b"
    elif s >= 35: return "#f87171"
    else:         return "#94a3b8"

def render_score_bar(score):
    color = score_color(score)
    return f"""
    <div class="score-wrap">
        <div class="score-bar">
            <div class="score-fill" style="width:{score}%;background:{color};"></div>
        </div>
        <span class="score-val" style="color:{color}">{score}</span>
    </div>
    """


# ================================
# AUTO-DETECT SCAN PARAMS
# ================================
def get_scan_intervals(mode):
    if mode == "Intraday (ORB)":
        return {"primary": "5m", "secondary": "15m", "tertiary": "1h", "period": "5d"}
    elif mode == "Delivery / Swing":
        return {"primary": "1d", "secondary": "1wk", "tertiary": None, "period": "1y"}
    else:  # Both
        return {"primary": "5m", "secondary": "1d", "tertiary": "1wk", "period": "1y"}


# ================================
# DAILY LOCK CHECK
# ================================
ic = st.session_state.get("initial_capital", 100_000)
daily_loss_cap   = ic * (daily_loss_limit_pct / 100)
daily_profit_cap = ic * (daily_profit_target_pct / 100)
if not st.session_state.trading_locked:
    if st.session_state.daily_pnl <= -daily_loss_cap:
        st.session_state.trading_locked = True
        st.session_state.lock_reason = f"Daily loss limit ₹{daily_loss_cap:,.0f} hit"
    elif st.session_state.daily_pnl >= daily_profit_cap:
        st.session_state.trading_locked = True
        st.session_state.lock_reason = f"Daily profit target ₹{daily_profit_cap:,.0f} reached"


# ================================
# HEADER
# ================================
ch1, ch2, ch3, ch4, ch5, ch6 = st.columns([4,1.2,1,1,1,1])
with ch1:
    mode_badge = "mode-intraday" if "Intraday" in st.session_state.scan_mode else "mode-delivery"
    mode_icon  = "⚡" if "Intraday" in st.session_state.scan_mode else ("📦" if "Delivery" in st.session_state.scan_mode else "🔄")
    st.markdown(f'<div class="hdr-title">🚀 ORB Smart Scanner <span style="color:#6366f1;font-size:.9rem;font-weight:700;vertical-align:middle;">PRO v5</span></div>', unsafe_allow_html=True)
    status_txt = "🟢 Market Open" if market_open else ("🟡 Pre-Market" if is_pre_market() else "🔴 Market Closed")
    regime_css = {"Trending":"regime-trend","Ranging":"regime-range","Volatile":"regime-volatile"}.get(st.session_state.market_regime, "regime-unknown")
    st.markdown(f'<div class="hdr-sub">{status_txt} &nbsp;|&nbsp; {datetime.now().strftime("%d %b %Y %H:%M:%S")} &nbsp;|&nbsp; {len(selected_symbols)} symbols &nbsp;|&nbsp; <span class="{regime_css}">{st.session_state.market_regime}</span> &nbsp;|&nbsp; <span class="{mode_badge}">{mode_icon} {st.session_state.scan_mode}</span></div>', unsafe_allow_html=True)
with ch2:
    manual_scan = st.button("🔄 Scan Now", use_container_width=True, type="primary")
with ch3:
    if st.button("🧹 Clear", use_container_width=True):
        st.session_state.active_trades = {}; st.session_state.closed_trades = []
        st.session_state.signal_state = {}; st.session_state.manual_trades = {}
        save_session(); st.rerun()
with ch4:
    if st.button("🔓 Unlock", use_container_width=True):
        st.session_state.trading_locked = False; st.session_state.lock_reason = ""; st.rerun()
with ch5:
    if st.button("🗑️ Cache", use_container_width=True):
        st.session_state.fetch_cache = {}; st.rerun()
with ch6:
    if st.button("🌙 Theme", use_container_width=True):
        st.session_state.dark_mode = not st.session_state.dark_mode; st.rerun()

if st.session_state.trading_locked:
    css_lock = "lock-profit" if "profit" in st.session_state.lock_reason.lower() else "lock-loss"
    st.markdown(f'<div class="{css_lock}">{"🏆" if "profit" in st.session_state.lock_reason.lower() else "🛑"} TRADING LOCKED — {st.session_state.lock_reason}</div>', unsafe_allow_html=True)

if not market_open:
    st.info("⏸ Market closed — showing historical signals. Click **Scan Now** to run manually.")


# ================================
# RUN SCAN
# ================================
do_scan = (market_open or manual_scan) and selected_symbols
scan_intervals = get_scan_intervals(st.session_state.scan_mode)

if do_scan:
    scan_results, errors = [], []
    total = len(selected_symbols)
    progress_bar = st.progress(0, text="Initialising scan…")
    cache_snap = snapshot_cache()
    all_data_primary   = []
    all_data_secondary = {}
    all_data_tertiary  = {}
    done = 0
    BATCH = 20

    mode = st.session_state.scan_mode
    primary_interval   = scan_intervals["primary"]
    secondary_interval = scan_intervals["secondary"]
    tertiary_interval  = scan_intervals["tertiary"]
    primary_period     = scan_intervals["period"]

    for i in range(0, total, BATCH):
        batch = selected_symbols[i:i+BATCH]
        with ThreadPoolExecutor(max_workers=min(10, len(batch))) as ex:
            futures = {ex.submit(fetch, s, primary_interval, primary_period, True, cache_snap): ("primary", s) for s in batch}
            if secondary_interval:
                futures.update({ex.submit(fetch, s, secondary_interval, primary_period, True, cache_snap): ("secondary", s) for s in batch})
            if tertiary_interval:
                futures.update({ex.submit(fetch, s, tertiary_interval, "2y", True, cache_snap): ("tertiary", s) for s in batch})
            for f in as_completed(futures):
                tf_type, sym = futures[f]
                try: result = f.result()
                except Exception as exc: result = (sym, None, str(exc), None)
                _apply_cache_write(result)
                sym_r, df_r, err_r = result[0], result[1], result[2]
                if tf_type == "primary":
                    all_data_primary.append((sym_r, df_r, err_r)); done += 1
                    progress_bar.progress(min(done/total, 1.0), text=f"Fetching {done}/{total}…")
                elif tf_type == "secondary" and df_r is not None:
                    all_data_secondary[sym] = df_r
                elif tf_type == "tertiary" and df_r is not None:
                    all_data_tertiary[sym] = df_r

    progress_bar.empty()

    for symbol, df, err in all_data_primary:
        if err or df is None:
            errors.append({"Symbol": symbol, "Error": err or "No data"})
            scan_results.append({
                "symbol": symbol, "label": "❌ Error", "sig_css": "sig-neutral",
                "row_css": "row-neutral", "score": 0, "price": None, "orb_high": None,
                "orb_low": None, "atr": None, "vol_ratio": None, "rsi": None,
                "gap_pct": None, "mtf_ok": None, "tf3_ok": None, "regime": "—",
                "reason": err or "Fetch failed", "direction": None,
                "cap": "—", "suggested_qty": 0, "sl_price": None, "mode": mode,
                "52w_high": None, "52w_low": None, "trend": None,
            })
            continue

        df_sec = all_data_secondary.get(symbol)
        df_ter = all_data_tertiary.get(symbol)

        # Compute metrics based on mode
        if mode == "Delivery / Swing":
            metrics = compute_delivery_metrics(df, df_sec)
            score   = compute_delivery_score(metrics)
        elif mode == "Both":
            m_intra = compute_intraday_metrics(df, None, None)
            m_deliv = compute_delivery_metrics(df_sec, df_ter) if df_sec is not None else {}
            # Blend: prefer intraday for direction if signal, else delivery
            metrics = m_intra.copy()
            if m_deliv:
                metrics["trend"] = m_deliv.get("trend")
                metrics["52w_high"] = m_deliv.get("52w_high")
                metrics["52w_low"]  = m_deliv.get("52w_low")
                metrics["from_52w_low_pct"]  = m_deliv.get("from_52w_low_pct")
                metrics["from_52w_high_pct"] = m_deliv.get("from_52w_high_pct")
            s_intra = compute_intraday_score(m_intra)
            s_deliv = compute_delivery_score(m_deliv) if m_deliv else 25
            score   = int((s_intra * 0.5) + (s_deliv * 0.5))
        else:  # Intraday
            metrics = compute_intraday_metrics(df, df_sec, df_ter)
            score   = compute_intraday_score(metrics)

        direction = metrics.get("direction", "NEUTRAL")
        label, sig_css, row_css = score_to_label(score, direction)

        price    = metrics.get("last_price")
        atr      = metrics.get("atr") or (price * 0.01 if price else 1)
        sl_price = compute_sl_from_atr(price, atr, direction) if price else None
        cap_cat  = get_cap_category(symbol, price)
        suggested_qty = suggest_qty(st.session_state.capital, price, sl_price) if (price and sl_price and price != sl_price) else 1

        scan_results.append({
            "symbol": symbol, "label": label, "sig_css": sig_css,
            "row_css": row_css, "score": score, "price": price,
            "orb_high": metrics.get("orb_high"), "orb_low": metrics.get("orb_low"),
            "atr": atr, "vol_ratio": metrics.get("vol_ratio"),
            "rsi": metrics.get("rsi"), "gap_pct": metrics.get("gap_pct"),
            "mtf_ok": metrics.get("mtf_ok"), "tf3_ok": metrics.get("tf3_ok"),
            "regime": metrics.get("regime", "Unknown"),
            "reason": f"Score {score}/100 | {direction}",
            "direction": direction, "cap": cap_cat,
            "suggested_qty": suggested_qty, "sl_price": sl_price, "mode": mode,
            "52w_high": metrics.get("52w_high"), "52w_low": metrics.get("52w_low"),
            "trend": metrics.get("trend"), "from_52w_low_pct": metrics.get("from_52w_low_pct"),
        })

    st.session_state.scan_results   = scan_results
    st.session_state.last_scan_time = datetime.now().strftime("%H:%M:%S")
    st.session_state.error_log      = errors
    st.session_state.equity.append({"time": datetime.now(), "capital": st.session_state.capital})
    save_session()

    new_sigs = sum(1 for r in scan_results if "Strong Buy" in r["label"] or "Buy" in r["label"])
    if new_sigs > st.session_state.last_signal_count:
        st.components.v1.html(f"<script>checkAndBeep({new_sigs});</script>", height=0)
    st.session_state.last_signal_count = new_sigs

    if new_sigs > 0:
        st.success(f"✅ {new_sigs} buy signal(s) | {len([r for r in scan_results if 'Sell' in r['label']])} sell signal(s) | Mode: {mode}")
    else:
        st.info(f"ℹ️ {len(selected_symbols)} scanned — no strong signals. {len(errors)} error(s).")

elif not selected_symbols:
    st.error("⚠️ No symbols selected.")


# ================================
# MARKET CONTEXT BAR
# ================================
nifty_chg = mkt_ctx["nifty_change"]
vix_val   = mkt_ctx["vix"]
nifty_col = "#22c55e" if nifty_chg >= 0 else "#ef4444"
nifty_sym = "▲" if nifty_chg >= 0 else "▼"
vix_badge_cls = "vix-low" if vix_val <= 15 else ("vix-mid" if vix_val <= 20 else "vix-high")
vix_icon = "🟢" if vix_val <= 15 else ("🟡" if vix_val <= 20 else "⚠️")
dpnl_cls = "pnl-pos" if st.session_state.daily_pnl >= 0 else "pnl-neg"

st.markdown(f"""
<div class="ctx-bar">
  <span>🏦 <b>Nifty 50:</b> <span style="color:{nifty_col};font-weight:700">{nifty_sym} {abs(nifty_chg):.1f} pts ({mkt_ctx["nifty_price"]:.0f})</span></span>
  <span class="{vix_badge_cls}">{vix_icon} VIX {vix_val:.1f}</span>
  {'<span style="color:#fbbf24;font-weight:700">⚠️ VIX>20 → Size ÷2</span>' if (use_vix_sizing and vix_val>20) else ''}
  <span>Daily P&L: <span class="{dpnl_cls}" style="font-weight:700">₹{st.session_state.daily_pnl:+,.0f}</span></span>
  <span style="color:var(--txt-sub);font-size:.82rem">Manual Holds: <b>{len(st.session_state.manual_trades)}</b></span>
  <span style="color:var(--txt-sub);font-size:.82rem">Last scan: <b>{st.session_state.last_scan_time or "—"}</b></span>
  <span style="color:var(--txt-sub);font-size:.82rem">SL: <b>{sl_strategy}</b></span>
</div>
""", unsafe_allow_html=True)


# ================================
# METRICS
# ================================
st.divider()
total_closed_pnl = sum(t["PnL (₹)"] for t in st.session_state.closed_trades)
win_trades = [t for t in st.session_state.closed_trades if t["PnL (₹)"] > 0]
win_rate   = (len(win_trades)/len(st.session_state.closed_trades)*100) if st.session_state.closed_trades else 0
net_change = st.session_state.capital - st.session_state.get("initial_capital", 100_000)

# Manual trade unrealised P&L
manual_pnl = 0.0
for sym, mt in st.session_state.manual_trades.items():
    cached = cache_get(sym, "5m") or cache_get(sym, "1d")
    if cached is not None:
        cur = float(cached["Close"].iloc[-1])
        manual_pnl += (cur - mt["buy_price"]) * mt["qty"]

m1,m2,m3,m4,m5,m6,m7,m8 = st.columns(8)
m1.metric("💼 Capital",        f"₹{st.session_state.capital:,.0f}", f"₹{net_change:+,.0f}")
m2.metric("📈 Realised P&L",   f"₹{total_closed_pnl:+,.0f}")
m3.metric("📅 Daily P&L",      f"₹{st.session_state.daily_pnl:+,.0f}")
m4.metric("💡 Unrealised",     f"₹{manual_pnl:+,.0f}")
m5.metric("📋 Manual Holds",   len(st.session_state.manual_trades))
m6.metric("📝 Closed Trades",  len(st.session_state.closed_trades))
m7.metric("🏆 Win Rate",       f"{win_rate:.1f}%")
m8.metric("📊 Scanned",        len(st.session_state.scan_results))


# ================================
# TABS
# ================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "🔍 Scan Results", "📁 My Holdings", "📜 Trade History",
    "📈 Equity Curve", "📊 Perf Stats", "🗺️ Sector Map",
    "⚗️ Backtester", "🎲 Monte Carlo", "⚠️ Error Log"
])


# ══════════════════════════════════════════════════════════
# TAB 1 — SCAN RESULTS (with inline Buy/Sell buttons + color rows)
# ══════════════════════════════════════════════════════════
with tab1:
    if not st.session_state.scan_results:
        st.info("Run a scan to see results.")
    else:
        results = st.session_state.scan_results

        # Filters
        f1, f2, f3, f4, f5 = st.columns(5)
        with f1:
            sig_filter = st.selectbox("Signal", ["All","Strong Buy","Buy","Weak Buy",
                                                   "Neutral","Sell","Strong Sell","Avoid"])
        with f2:
            sort_by = st.selectbox("Sort By", ["Score ↓","Price ↓","Vol Ratio ↓","RSI ↓","Symbol ↑"])
        with f3:
            min_score_f = st.slider("Min Score", 0, 100, 0, 5)
        with f4:
            cap_filter = st.selectbox("Cap Category", ["All","Large","Mid","Small","Penny"])
        with f5:
            dir_filter = st.selectbox("Direction", ["All","BUY","SELL","NEUTRAL"])

        # Apply filters
        filtered = [r for r in results if r.get("price") is not None or "Error" not in r["label"]]
        if sig_filter != "All":
            filtered = [r for r in filtered if sig_filter.lower() in r["label"].lower()]
        if min_score_f > 0:
            filtered = [r for r in filtered if r["score"] >= min_score_f]
        if cap_filter != "All":
            filtered = [r for r in filtered if r.get("cap") == cap_filter]
        if dir_filter != "All":
            filtered = [r for r in filtered if r.get("direction") == dir_filter]

        # Sort
        sort_key_map = {
            "Score ↓":     lambda x: -x["score"],
            "Price ↓":     lambda x: -(x["price"] or 0),
            "Vol Ratio ↓": lambda x: -(x["vol_ratio"] or 0),
            "RSI ↓":       lambda x: -(x["rsi"] or 0),
            "Symbol ↑":    lambda x: x["symbol"],
        }
        try: filtered.sort(key=sort_key_map[sort_by])
        except: pass

        st.caption(f"Showing **{len(filtered)}** of **{len(results)}** symbols | 🟢=Buy 🔴=Sell ⚪=Neutral 🟡=Avoid")

        # ─── COLUMN HEADERS ───
        cols_h = st.columns([2, 1.2, 1, 1, 1, 1, 1, 1.5, 1.5, 1, 1])
        headers = ["Symbol", "Signal (Score/100)", "Price", "ORB H/L", "ATR", "Vol Ratio", "RSI", "SL / Target", "Sug. Qty", "Buy", "Sell"]
        for col, hdr in zip(cols_h, headers):
            col.markdown(f"<span style='font-size:.7rem;text-transform:uppercase;letter-spacing:.06em;color:var(--txt-sub);font-family:Space Mono,monospace;'>{hdr}</span>", unsafe_allow_html=True)

        st.markdown("---")

        # ─── ROWS ───
        for idx, row in enumerate(filtered):
            sym      = row["symbol"]
            price    = row.get("price")
            score    = row["score"]
            label    = row["label"]
            row_css  = row["row_css"]
            cap      = row.get("cap", "—")
            cap_css  = get_cap_css(cap)
            direction = row.get("direction", "NEUTRAL")
            atr      = row.get("atr") or 0
            vol_r    = row.get("vol_ratio")
            rsi_v    = row.get("rsi")
            orb_h    = row.get("orb_high")
            orb_l    = row.get("orb_low")
            sl_p     = row.get("sl_price")
            sug_qty  = row.get("suggested_qty", 1)
            trend    = row.get("trend", "")
            from_52  = row.get("from_52w_low_pct")

            # Target = entry + 2*ATR (BUY) or entry - 2*ATR (SELL)
            tgt_price = None
            if price and atr:
                tgt_price = round(price + 2*atr, 2) if direction == "BUY" else round(price - 2*atr, 2)

            # Check if already in manual_trades
            in_hold = sym in st.session_state.manual_trades
            hold_pnl = None
            if in_hold:
                mt = st.session_state.manual_trades[sym]
                cached_df = cache_get(sym, "5m") or cache_get(sym, "1d")
                if cached_df is not None:
                    cur_p = float(cached_df["Close"].iloc[-1])
                    hold_pnl = (cur_p - mt["buy_price"]) * mt["qty"]
                    row_css = "row-active"

            # Row background via HTML wrapper
            bg_color = {
                "row-strong-buy":  "rgba(34,197,94,.15)",
                "row-buy":         "rgba(34,197,94,.07)",
                "row-weak-buy":    "rgba(34,197,94,.03)",
                "row-neutral":     "rgba(255,255,255,.01)",
                "row-avoid":       "rgba(239,68,68,.05)",
                "row-weak-sell":   "rgba(239,68,68,.09)",
                "row-sell":        "rgba(239,68,68,.15)",
                "row-strong-sell": "rgba(239,68,68,.23)",
                "row-active":      "rgba(99,102,241,.09)",
            }.get(row_css, "transparent")

            border_color = {
                "row-strong-buy":  "#22c55e",
                "row-buy":         "#4ade80",
                "row-weak-buy":    "#86efac",
                "row-neutral":     "#475569",
                "row-avoid":       "#fca5a5",
                "row-weak-sell":   "#f87171",
                "row-sell":        "#ef4444",
                "row-strong-sell": "#dc2626",
                "row-active":      "#6366f1",
            }.get(row_css, "#475569")

            st.markdown(
                f'<div style="background:{bg_color};border-left:4px solid {border_color};border-radius:10px;padding:2px 0 2px 4px;margin-bottom:2px;"></div>',
                unsafe_allow_html=True
            )

            cols = st.columns([2, 1.2, 1, 1, 1, 1, 1, 1.5, 1.5, 1, 1])

            # Symbol + cap badge
            with cols[0]:
                sym_display = sym.replace(".NS","").replace(".BO","")
                trend_txt = f" | {trend}" if trend and trend != "Unknown" else ""
                st.markdown(
                    f'<div style="background:{bg_color};border-left:4px solid {border_color};border-radius:8px;padding:6px 10px;">'
                    f'<span style="font-weight:700;font-size:.9rem;">{sym_display}</span>'
                    f'&nbsp;<span class="{cap_css}">{cap}</span>'
                    f'<div style="font-size:.7rem;color:var(--txt-sub);margin-top:2px;">{trend_txt or ("52W +" + str(from_52) + "%" if from_52 else "")}</div>'
                    f'</div>', unsafe_allow_html=True
                )

            # Signal + score bar
            with cols[1]:
                sig_color = score_color(score)
                st.markdown(
                    f'<div style="background:{bg_color};padding:6px 4px;border-radius:8px;">'
                    f'<span class="{row["sig_css"]}" style="display:block;margin-bottom:4px;font-size:.75rem;">{label}</span>'
                    f'<div style="display:flex;align-items:center;gap:6px;">'
                    f'<div style="flex:1;height:6px;border-radius:3px;background:var(--bdr);">'
                    f'<div style="width:{score}%;height:6px;border-radius:3px;background:{sig_color};"></div></div>'
                    f'<span style="color:{sig_color};font-weight:700;font-size:.8rem;font-family:Space Mono,monospace;">{score}</span>'
                    f'</div></div>', unsafe_allow_html=True
                )

            # Price
            with cols[2]:
                price_color = "#22c55e" if direction == "BUY" else ("#ef4444" if direction == "SELL" else "var(--txt)")
                st.markdown(
                    f'<div style="background:{bg_color};padding:6px 4px;border-radius:8px;font-weight:700;font-size:.9rem;color:{price_color};">'
                    f'₹{price:.2f}</div>' if price else f'<div style="padding:6px 4px;">—</div>',
                    unsafe_allow_html=True
                )

            # ORB H/L
            with cols[3]:
                orb_txt = f"H {orb_h:.1f}<br>L {orb_l:.1f}" if (orb_h and orb_l) else "—"
                st.markdown(
                    f'<div style="background:{bg_color};padding:6px 4px;border-radius:8px;font-size:.78rem;line-height:1.5;">{orb_txt}</div>',
                    unsafe_allow_html=True
                )

            # ATR
            with cols[4]:
                st.markdown(
                    f'<div style="background:{bg_color};padding:6px 4px;border-radius:8px;font-size:.82rem;">{atr:.2f}</div>',
                    unsafe_allow_html=True
                )

            # Vol Ratio
            with cols[5]:
                vr_color = "#22c55e" if (vol_r or 0) >= min_vol_ratio else "var(--txt-sub)"
                st.markdown(
                    f'<div style="background:{bg_color};padding:6px 4px;border-radius:8px;font-size:.82rem;color:{vr_color};">'
                    f'{vol_r:.2f}x</div>' if vol_r else f'<div style="padding:6px 4px;">—</div>',
                    unsafe_allow_html=True
                )

            # RSI
            with cols[6]:
                rsi_color = "#22c55e" if (rsi_v or 50) < 70 and (rsi_v or 50) > 30 else "#ef4444"
                st.markdown(
                    f'<div style="background:{bg_color};padding:6px 4px;border-radius:8px;font-size:.82rem;color:{rsi_color};">'
                    f'{rsi_v:.1f}</div>' if rsi_v else f'<div style="padding:6px 4px;">50.0</div>',
                    unsafe_allow_html=True
                )

            # SL / Target
            with cols[7]:
                if sl_p and tgt_price:
                    st.markdown(
                        f'<div style="background:{bg_color};padding:6px 4px;border-radius:8px;font-size:.75rem;line-height:1.6;">'
                        f'<span style="color:#ef4444;">SL ₹{sl_p:.2f}</span><br>'
                        f'<span style="color:#22c55e;">T ₹{tgt_price:.2f}</span></div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(f'<div style="padding:6px 4px;font-size:.82rem;">—</div>', unsafe_allow_html=True)

            # Suggested Qty / Current P&L if holding
            with cols[8]:
                if in_hold and hold_pnl is not None:
                    pnl_col = "#22c55e" if hold_pnl >= 0 else "#ef4444"
                    sign = "+" if hold_pnl >= 0 else ""
                    mt_data = st.session_state.manual_trades[sym]
                    st.markdown(
                        f'<div style="background:{bg_color};padding:6px 4px;border-radius:8px;font-size:.75rem;line-height:1.6;">'
                        f'<span style="color:var(--txt-sub);">{mt_data["qty"]} @ ₹{mt_data["buy_price"]:.2f}</span><br>'
                        f'<span style="color:{pnl_col};font-weight:700;">{sign}₹{hold_pnl:,.2f}</span></div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f'<div style="background:{bg_color};padding:6px 4px;border-radius:8px;font-size:.82rem;">'
                        f'<span style="color:var(--txt-sub);">Qty: </span><span style="font-weight:700;">{sug_qty}</span></div>',
                        unsafe_allow_html=True
                    )

            # BUY button
            with cols[9]:
                if not in_hold and price and direction in ("BUY", "NEUTRAL"):
                    qty_to_use = sug_qty
                    if st.button(f"🟢 Buy", key=f"buy_{sym}_{idx}", type="primary", use_container_width=True):
                        manual_buy(sym, price, qty_to_use)
                        send_alert(f"✅ BOUGHT {sym}: {qty_to_use} @ ₹{price:.2f} | SL ₹{sl_p or 0:.2f}")
                        st.rerun()
                elif in_hold:
                    st.markdown('<span style="font-size:.75rem;color:#818cf8;font-weight:600;">✓ Held</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span style="font-size:.75rem;color:var(--txt-sub);">—</span>', unsafe_allow_html=True)

            # SELL button
            with cols[10]:
                if in_hold:
                    if st.button(f"🔴 Sell", key=f"sell_{sym}_{idx}", use_container_width=True):
                        pnl_realized = manual_sell(sym)
                        st.session_state.daily_pnl += pnl_realized
                        st.session_state.capital   += pnl_realized
                        send_alert(f"📤 SOLD {sym} | P&L ₹{pnl_realized:+,.2f}")
                        st.rerun()
                elif price and direction == "SELL":
                    if st.button(f"🔴 Short", key=f"short_{sym}_{idx}", use_container_width=True):
                        manual_buy(sym, price, sug_qty)  # track as short via negative interpretation
                        st.rerun()
                else:
                    st.markdown('<span style="font-size:.75rem;color:var(--txt-sub);">—</span>', unsafe_allow_html=True)

        # ─── LEGEND ───
        st.markdown("""
        <div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:16px;padding:10px 14px;
                    background:var(--bg-card);border-radius:10px;border:1px solid var(--bdr);font-size:.78rem;">
            <span style="display:flex;align-items:center;gap:5px;"><span style="width:12px;height:12px;border-radius:2px;background:rgba(34,197,94,.2);display:inline-block;border-left:3px solid #22c55e;"></span> Strong Buy</span>
            <span style="display:flex;align-items:center;gap:5px;"><span style="width:12px;height:12px;border-radius:2px;background:rgba(34,197,94,.1);display:inline-block;border-left:3px solid #4ade80;"></span> Buy</span>
            <span style="display:flex;align-items:center;gap:5px;"><span style="width:12px;height:12px;border-radius:2px;background:rgba(255,255,255,.02);display:inline-block;border-left:3px solid #64748b;"></span> Neutral</span>
            <span style="display:flex;align-items:center;gap:5px;"><span style="width:12px;height:12px;border-radius:2px;background:rgba(239,68,68,.06);display:inline-block;border-left:3px solid #fca5a5;"></span> Avoid</span>
            <span style="display:flex;align-items:center;gap:5px;"><span style="width:12px;height:12px;border-radius:2px;background:rgba(239,68,68,.18);display:inline-block;border-left:3px solid #ef4444;"></span> Sell</span>
            <span style="display:flex;align-items:center;gap:5px;"><span style="width:12px;height:12px;border-radius:2px;background:rgba(99,102,241,.1);display:inline-block;border-left:3px solid #6366f1;"></span> Active Hold</span>
        </div>
        """, unsafe_allow_html=True)

        # Export
        st.markdown("---")
        export_rows = []
        for r in filtered:
            export_rows.append({
                "Symbol": r["symbol"], "Signal": r["label"], "Score/100": r["score"],
                "Direction": r.get("direction"), "Price": r.get("price"),
                "ORB High": r.get("orb_high"), "ORB Low": r.get("orb_low"),
                "ATR": r.get("atr"), "Vol Ratio": r.get("vol_ratio"), "RSI": r.get("rsi"),
                "SL": r.get("sl_price"), "Suggested Qty": r.get("suggested_qty"),
                "Cap": r.get("cap"), "Trend": r.get("trend"), "Regime": r.get("regime"),
            })
        if export_rows:
            st.download_button("⬇️ Export Results CSV",
                               pd.DataFrame(export_rows).to_csv(index=False),
                               file_name=f"scan_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", mime="text/csv")


# ══════════════════════════════════════════════════════════
# TAB 2 — MY HOLDINGS (Manual Trades)
# ══════════════════════════════════════════════════════════
with tab2:
    st.markdown("### 📁 My Holdings (Manual Trades)")
    st.caption("Stocks you've bought via Buy button — track P&L live")

    if st.session_state.manual_trades:
        hold_rows = []
        total_invested = 0.0
        total_current  = 0.0

        h_cols = st.columns([2, 1, 1, 1, 1.5, 1.5, 1, 1])
        for col, hdr in zip(h_cols, ["Symbol", "Qty", "Buy Price", "Current", "Invested", "P&L (₹)", "P&L %", "Action"]):
            col.markdown(f"<span style='font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:var(--txt-sub);font-family:Space Mono,monospace;'>{hdr}</span>", unsafe_allow_html=True)
        st.markdown("---")

        for sym, mt in st.session_state.manual_trades.items():
            cached_df = cache_get(sym, "5m") or cache_get(sym, "1d")
            cur_price = float(cached_df["Close"].iloc[-1]) if cached_df is not None else mt["buy_price"]
            invested  = mt["buy_price"] * mt["qty"]
            current_v = cur_price * mt["qty"]
            pnl_abs   = current_v - invested
            pnl_pct   = (pnl_abs / invested * 100) if invested > 0 else 0
            total_invested += invested
            total_current  += current_v
            hold_rows.append({**mt, "symbol": sym, "cur_price": cur_price,
                               "pnl_abs": pnl_abs, "pnl_pct": pnl_pct})

            bg = "rgba(34,197,94,.07)" if pnl_abs >= 0 else "rgba(239,68,68,.07)"
            bdr = "#22c55e" if pnl_abs >= 0 else "#ef4444"
            pnl_color = "#22c55e" if pnl_abs >= 0 else "#ef4444"

            h_row = st.columns([2, 1, 1, 1, 1.5, 1.5, 1, 1])
            with h_row[0]:
                st.markdown(f'<div style="background:{bg};border-left:4px solid {bdr};border-radius:8px;padding:8px 10px;font-weight:700;">'
                             f'{sym.replace(".NS","")}</div>', unsafe_allow_html=True)
            with h_row[1]:
                st.markdown(f'<div style="background:{bg};padding:8px 4px;border-radius:8px;">{mt["qty"]}</div>', unsafe_allow_html=True)
            with h_row[2]:
                st.markdown(f'<div style="background:{bg};padding:8px 4px;border-radius:8px;">₹{mt["buy_price"]:.2f}</div>', unsafe_allow_html=True)
            with h_row[3]:
                st.markdown(f'<div style="background:{bg};padding:8px 4px;border-radius:8px;">₹{cur_price:.2f}</div>', unsafe_allow_html=True)
            with h_row[4]:
                st.markdown(f'<div style="background:{bg};padding:8px 4px;border-radius:8px;">₹{invested:,.0f}</div>', unsafe_allow_html=True)
            with h_row[5]:
                sign = "+" if pnl_abs >= 0 else ""
                st.markdown(f'<div style="background:{bg};padding:8px 4px;border-radius:8px;color:{pnl_color};font-weight:700;">{sign}₹{pnl_abs:,.2f}</div>', unsafe_allow_html=True)
            with h_row[6]:
                st.markdown(f'<div style="background:{bg};padding:8px 4px;border-radius:8px;color:{pnl_color};font-weight:700;">{pnl_pct:+.2f}%</div>', unsafe_allow_html=True)
            with h_row[7]:
                if st.button("🔴 Sell", key=f"hold_sell_{sym}", use_container_width=True):
                    realized = manual_sell(sym)
                    st.session_state.daily_pnl += realized
                    st.session_state.capital   += realized
                    save_session(); st.rerun()

        # Summary
        total_pnl = total_current - total_invested
        pnl_color_t = "#22c55e" if total_pnl >= 0 else "#ef4444"
        st.markdown("<br>", unsafe_allow_html=True)
        sc1, sc2, sc3, sc4 = st.columns(4)
        with sc1: st.markdown(f'<div class="stat-box"><div class="val">₹{total_invested:,.0f}</div><div class="lbl">Invested</div></div>', unsafe_allow_html=True)
        with sc2: st.markdown(f'<div class="stat-box"><div class="val">₹{total_current:,.0f}</div><div class="lbl">Current Value</div></div>', unsafe_allow_html=True)
        with sc3: st.markdown(f'<div class="stat-box"><div class="val" style="color:{pnl_color_t}">₹{total_pnl:+,.0f}</div><div class="lbl">Unrealised P&L</div></div>', unsafe_allow_html=True)
        pnl_pct_t = (total_pnl/total_invested*100) if total_invested > 0 else 0
        with sc4: st.markdown(f'<div class="stat-box"><div class="val" style="color:{pnl_color_t}">{pnl_pct_t:+.2f}%</div><div class="lbl">Return</div></div>', unsafe_allow_html=True)

        if st.button("🔄 Refresh Prices", type="primary"):
            for sym in list(st.session_state.manual_trades.keys()):
                _, df_p, _, cw_p = fetch(sym, "5m", "5d", use_cache=False, _cache_snapshot={})
                if cw_p: k_p, e_p = cw_p; st.session_state.fetch_cache[k_p] = e_p
            st.rerun()
    else:
        st.info("No holdings. Use **Buy** buttons in Scan Results to add positions.")


# ══════════════════════════════════════════════════════════
# TAB 3 — TRADE HISTORY
# ══════════════════════════════════════════════════════════
with tab3:
    if st.session_state.closed_trades:
        closed_fixed = []
        for t in st.session_state.closed_trades:
            t2 = dict(t)
            if "Symbol_" in t2: t2["Symbol"] = t2.pop("Symbol_")
            closed_fixed.append(t2)
        closed_df = pd.DataFrame(closed_fixed)
        if "Symbol" not in closed_df.columns and "Symbol_" in closed_df.columns:
            closed_df.rename(columns={"Symbol_":"Symbol"}, inplace=True)

        total_pnl = closed_df["PnL (₹)"].sum()
        ta, tb, tc, td = st.columns(4)
        ta.metric("Total P&L",    f"₹{total_pnl:+,.2f}")
        tb.metric("Total Trades", len(closed_df))
        tc.metric("Win Rate",     f"{win_rate:.1f}%")
        td.metric("Wins / Losses", f"{len(win_trades)} / {len(st.session_state.closed_trades)-len(win_trades)}")

        def style_closed(row):
            pnl_val = row.get("PnL (₹)", 0)
            if pnl_val > 0:   return ["background-color:rgba(34,197,94,.1)"]*len(row)
            elif pnl_val < 0: return ["background-color:rgba(239,68,68,.1)"]*len(row)
            return [""]*len(row)

        st.dataframe(closed_df.style.apply(style_closed, axis=1), use_container_width=True, hide_index=True)

        da, db = st.columns(2)
        with da: st.download_button("⬇️ Export CSV", closed_df.to_csv(index=False),
                                     file_name=f"trades_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", mime="text/csv")
        with db: st.download_button("📓 Export JSON", json.dumps(st.session_state.closed_trades, indent=2),
                                     file_name=f"journal_{datetime.now().strftime('%Y%m%d_%H%M')}.json", mime="application/json")
    else:
        st.info("No closed trades yet.")


# ══════════════════════════════════════════════════════════
# TAB 4 — EQUITY CURVE
# ══════════════════════════════════════════════════════════
with tab4:
    equity_df = pd.DataFrame(st.session_state.equity)
    if not equity_df.empty:
        initial = st.session_state.get("initial_capital", 100_000)
        fig_eq = go.Figure()
        fig_eq.add_trace(go.Scatter(x=equity_df["time"], y=equity_df["capital"],
            mode="lines+markers", line=dict(color="#6366f1",width=2.5),
            marker=dict(size=4), name="Capital", fill="tozeroy",
            fillcolor="rgba(99,102,241,.08)"))
        fig_eq.add_hline(y=initial, line_dash="dash", line_color="#64748b",
                          annotation_text=f"Initial ₹{initial:,.0f}")
        fig_eq.update_layout(title="Equity Curve", xaxis_title="Time", yaxis_title="Capital (₹)",
            template=plotly_tpl, height=400, margin=dict(l=10,r=10,t=40,b=10))
        st.plotly_chart(fig_eq, use_container_width=True)
        peak = equity_df["capital"].cummax()
        dd   = ((equity_df["capital"]-peak)/peak)*100
        fig_dd = go.Figure()
        fig_dd.add_trace(go.Scatter(x=equity_df["time"], y=dd, mode="lines", fill="tozeroy",
            line=dict(color="#ef4444",width=1.5), fillcolor="rgba(239,68,68,.1)", name="Drawdown %"))
        fig_dd.update_layout(title="Drawdown %", template=plotly_tpl, height=220,
                              margin=dict(l=10,r=10,t=40,b=10))
        st.plotly_chart(fig_dd, use_container_width=True)
    else:
        st.info("No equity data yet. Run a scan.")


# ══════════════════════════════════════════════════════════
# TAB 5 — PERF STATS
# ══════════════════════════════════════════════════════════
with tab5:
    if st.session_state.closed_trades:
        df_p = pd.DataFrame([{**t, "Symbol": t.get("Symbol_", t.get("Symbol","—"))} for t in st.session_state.closed_trades])
        wins  = df_p[df_p["PnL (₹)"] > 0]
        loses = df_p[df_p["PnL (₹)"] <= 0]
        avg_win  = wins["PnL (₹)"].mean()  if len(wins)>0  else 0
        avg_loss = loses["PnL (₹)"].mean() if len(loses)>0 else 0
        pf = abs(wins["PnL (₹)"].sum()/loses["PnL (₹)"].sum()) if loses["PnL (₹)"].sum()!=0 else float("inf")
        ps1,ps2,ps3 = st.columns(3)
        with ps1: st.markdown(f'<div class="stat-box"><div class="val" style="color:#22c55e">₹{avg_win:,.0f}</div><div class="lbl">Avg Win</div></div>', unsafe_allow_html=True)
        with ps2: st.markdown(f'<div class="stat-box"><div class="val" style="color:#ef4444">₹{avg_loss:,.0f}</div><div class="lbl">Avg Loss</div></div>', unsafe_allow_html=True)
        with ps3: st.markdown(f'<div class="stat-box"><div class="val">{pf:.2f}x</div><div class="lbl">Profit Factor</div></div>', unsafe_allow_html=True)

        # Score distribution
        if st.session_state.scan_results:
            scores = [r["score"] for r in st.session_state.scan_results if r.get("score") is not None]
            if scores:
                fig_sc = go.Figure()
                fig_sc.add_trace(go.Histogram(x=scores, nbinsx=20, marker_color="#6366f1", opacity=0.8))
                fig_sc.update_layout(title="Score Distribution", template=plotly_tpl, height=280,
                                     xaxis_title="Score/100", yaxis_title="Count",
                                     margin=dict(l=10,r=10,t=40,b=10))
                st.plotly_chart(fig_sc, use_container_width=True)
    else:
        st.info("No closed trades yet.")


# ══════════════════════════════════════════════════════════
# TAB 6 — SECTOR MAP
# ══════════════════════════════════════════════════════════
with tab6:
    st.markdown("### 🗺️ Sector Signal Heatmap")
    if st.session_state.scan_results:
        sector_counts = {}
        for row in st.session_state.scan_results:
            sym = row["symbol"]
            sector = SECTOR_MAP.get(sym, "Other")
            sig = str(row.get("label",""))
            if sector not in sector_counts:
                sector_counts[sector] = {"Strong Buy":0,"Buy":0,"Neutral":0,"Sell":0,"Strong Sell":0,"Avg Score":0,"Count":0}
            if "Strong Buy" in sig:   sector_counts[sector]["Strong Buy"] += 1
            elif "Buy" in sig and "Avoid" not in sig: sector_counts[sector]["Buy"] += 1
            elif "Strong Sell" in sig: sector_counts[sector]["Strong Sell"] += 1
            elif "Sell" in sig:       sector_counts[sector]["Sell"] += 1
            else:                     sector_counts[sector]["Neutral"] += 1
            sector_counts[sector]["Avg Score"] += row.get("score",0)
            sector_counts[sector]["Count"] += 1

        heat_rows = []
        for s, v in sector_counts.items():
            avg = round(v["Avg Score"] / v["Count"], 1) if v["Count"] > 0 else 0
            heat_rows.append({"Sector":s, "Strong Buy":v["Strong Buy"], "Buy":v["Buy"],
                               "Neutral":v["Neutral"], "Sell":v["Sell"], "Strong Sell":v["Strong Sell"],
                               "Avg Score": avg})
        heat_df = pd.DataFrame(heat_rows).sort_values("Avg Score", ascending=False)
        st.dataframe(heat_df, use_container_width=True, hide_index=True)
    else:
        st.info("Run a scan first.")


# ══════════════════════════════════════════════════════════
# TAB 7 — BACKTESTER
# ══════════════════════════════════════════════════════════
with tab7:
    st.markdown("### ⚗️ Walk-Forward Backtester")
    bc1,bc2,bc3,bc4 = st.columns(4)
    with bc1: bt_symbols = st.multiselect("Symbols", selected_symbols, default=selected_symbols[:3] if len(selected_symbols)>=3 else selected_symbols)
    with bc2: bt_orb_min = st.number_input("ORB Min", 5, 60, int(orb_minutes), key="bt_orb")
    with bc3: wf_train   = st.number_input("Train Days", 1, 20, 3)
    with bc4: wf_test    = st.number_input("Test Days",  1, 10, 1)

    def run_orb_bt(df_full, days_list, orb_m, atr_m=2.0):
        trades = []; df_full = add_indicators(df_full.copy()); df_full.index = pd.to_datetime(df_full.index)
        for day in days_list:
            grp = df_full[df_full.index.date == day].copy()
            if len(grp) < 5: continue
            grp["_time"] = grp.index.time
            cutoff_t = (datetime.combine(day, dtime(9,15))+timedelta(minutes=int(orb_m))).time()
            orb_part = grp[grp["_time"] <= cutoff_t]; rest = grp[grp["_time"] > cutoff_t]
            if len(orb_part) < 2 or len(rest) < 2: continue
            orb_h = float(orb_part["High"].max()); orb_l = float(orb_part["Low"].min())
            in_trade = False; direction = entry_p = sl_p = tgt_p = 0.0
            for idx_r, row_r in rest.iterrows():
                close = float(row_r["Close"]); atr = float(row_r["ATR"]) if not pd.isna(row_r.get("ATR",np.nan)) else 0
                if not in_trade:
                    if close > orb_h:   direction="BUY";  entry_p=close; sl_p=orb_l; tgt_p=entry_p+atr_m*atr; in_trade=True
                    elif close < orb_l: direction="SELL"; entry_p=close; sl_p=orb_h; tgt_p=entry_p-atr_m*atr; in_trade=True
                else:
                    hit_sl  = (direction=="BUY" and close<=sl_p)  or (direction=="SELL" and close>=sl_p)
                    hit_tgt = (direction=="BUY" and close>=tgt_p) or (direction=="SELL" and close<=tgt_p)
                    if hit_sl or hit_tgt:
                        pnl = (close-entry_p) if direction=="BUY" else (entry_p-close)
                        trades.append({"day":str(day),"direction":direction,"entry":round(entry_p,2),"exit":round(close,2),"pnl":round(pnl,2),"reason":"TGT" if hit_tgt else "SL"})
                        in_trade = False
            if in_trade:
                close = float(rest["Close"].iloc[-1]); pnl = (close-entry_p) if direction=="BUY" else (entry_p-close)
                trades.append({"day":str(day),"direction":direction,"entry":round(entry_p,2),"exit":round(close,2),"pnl":round(pnl,2),"reason":"EOD"})
        return trades

    if st.button("▶️ Run Walk-Forward Backtest", type="primary"):
        with st.spinner("Running…"):
            wf_results = []
            for sym in bt_symbols:
                _, df_bt, err, cw = fetch(sym, "5m", "1mo", use_cache=False, _cache_snapshot={})
                if cw: k2,e2=cw; st.session_state.fetch_cache[k2]=e2
                if err or df_bt is None or len(df_bt) < 20: continue
                df_bt.index = pd.to_datetime(df_bt.index)
                days = sorted(set(df_bt.index.date.tolist()))
                ws = int(wf_train) + int(wf_test)
                for si in range(0, len(days)-ws+1, int(wf_test)):
                    test_days = days[si+int(wf_train): si+ws]
                    if not test_days: continue
                    for t in run_orb_bt(df_bt, test_days, bt_orb_min):
                        t["symbol"] = sym; wf_results.append(t)
            st.session_state.backtest_results = wf_results
        if wf_results:
            bt_df = pd.DataFrame(wf_results)
            bt_wins = bt_df[bt_df["pnl"]>0]; bt_loss = bt_df[bt_df["pnl"]<=0]
            bt_wr = len(bt_wins)/len(bt_df)*100 if len(bt_df)>0 else 0
            bt_pf = abs(bt_wins["pnl"].sum()/bt_loss["pnl"].sum()) if bt_loss["pnl"].sum()!=0 else float("inf")
            bb1,bb2,bb3,bb4 = st.columns(4)
            pc = "#22c55e" if bt_df["pnl"].sum()>0 else "#ef4444"
            with bb1: st.markdown(f'<div class="stat-box"><div class="val">{len(bt_df)}</div><div class="lbl">OOS Trades</div></div>', unsafe_allow_html=True)
            with bb2: st.markdown(f'<div class="stat-box"><div class="val" style="color:{pc}">₹{bt_df["pnl"].sum():,.1f}</div><div class="lbl">OOS P&L</div></div>', unsafe_allow_html=True)
            with bb3: st.markdown(f'<div class="stat-box"><div class="val">{bt_wr:.1f}%</div><div class="lbl">Win Rate</div></div>', unsafe_allow_html=True)
            with bb4: st.markdown(f'<div class="stat-box"><div class="val">{bt_pf:.2f}x</div><div class="lbl">Profit Factor</div></div>', unsafe_allow_html=True)
            bt_df["Cum PnL"] = bt_df["pnl"].cumsum()
            fig_bt = go.Figure()
            fig_bt.add_trace(go.Scatter(x=list(range(len(bt_df))), y=bt_df["Cum PnL"],
                mode="lines+markers", fill="tozeroy", line=dict(color="#6366f1",width=2.5),
                fillcolor="rgba(99,102,241,.1)"))
            fig_bt.add_hline(y=0, line_dash="dash", line_color="#64748b")
            fig_bt.update_layout(title="Walk-Forward OOS Cumulative P&L", template=plotly_tpl,
                                  height=320, margin=dict(l=10,r=10,t=40,b=10))
            st.plotly_chart(fig_bt, use_container_width=True)
            st.dataframe(bt_df, use_container_width=True, hide_index=True)
        else:
            st.warning("No trades generated.")


# ══════════════════════════════════════════════════════════
# TAB 8 — MONTE CARLO
# ══════════════════════════════════════════════════════════
with tab8:
    st.markdown("### 🎲 Monte Carlo Simulation")
    mc1,mc2,mc3 = st.columns(3)
    with mc1: mc_n_sims = st.number_input("Simulations", 100, 5000, 1000, step=100)
    with mc2: mc_capital = st.number_input("Start Capital (₹)", 10_000, 10_000_000, int(st.session_state.initial_capital), step=10_000)
    with mc3: mc_ruin_thr = st.slider("Ruin Threshold (%)", 10, 90, 30) / 100

    if st.button("▶️ Run Monte Carlo", type="primary"):
        pnl_list = [t["PnL (₹)"] for t in st.session_state.closed_trades]
        if not pnl_list and st.session_state.backtest_results:
            pnl_list = [t.get("pnl",0) for t in st.session_state.backtest_results]
        if len(pnl_list) < 5:
            st.warning("Need at least 5 closed trades.")
        else:
            with st.spinner(f"Running {mc_n_sims:,} simulations…"):
                pnl_arr = np.array(pnl_list); n = len(pnl_arr)
                results = []
                rng = np.random.default_rng(42)
                for _ in range(int(mc_n_sims)):
                    shuffled = rng.choice(pnl_arr, size=n, replace=True)
                    equity = mc_capital + np.cumsum(shuffled)
                    peak = np.maximum.accumulate(equity)
                    dd_pct = ((equity-peak)/peak)*100
                    results.append({"final":float(equity[-1]),"max_dd":float(dd_pct.min()),
                                    "ruined":bool(np.any(equity<=mc_capital*(1-mc_ruin_thr)))})
            res_df = pd.DataFrame(results)
            ruin_rate = res_df["ruined"].mean()*100
            final_arr = res_df["final"].values; dd_arr = res_df["max_dd"].values
            mc_a,mc_b,mc_c,mc_d = st.columns(4)
            rr_col = "#ef4444" if ruin_rate>10 else ("#fbbf24" if ruin_rate>5 else "#22c55e")
            with mc_a: st.markdown(f'<div class="stat-box"><div class="val" style="color:{rr_col}">{ruin_rate:.1f}%</div><div class="lbl">Risk of Ruin</div></div>', unsafe_allow_html=True)
            with mc_b: st.markdown(f'<div class="stat-box"><div class="val" style="color:#ef4444">{np.percentile(dd_arr,95):.1f}%</div><div class="lbl">95th% Max DD</div></div>', unsafe_allow_html=True)
            with mc_c: st.markdown(f'<div class="stat-box"><div class="val">₹{np.percentile(final_arr,50):,.0f}</div><div class="lbl">Median Outcome</div></div>', unsafe_allow_html=True)
            with mc_d: st.markdown(f'<div class="stat-box"><div class="val">₹{np.percentile(final_arr,5):,.0f}</div><div class="lbl">5th% Worst</div></div>', unsafe_allow_html=True)
            fig_mc1 = go.Figure()
            fig_mc1.add_trace(go.Histogram(x=final_arr, nbinsx=50, marker_color="#6366f1", opacity=.8))
            fig_mc1.add_vline(x=mc_capital, line_dash="dash", line_color="#64748b", annotation_text="Start")
            fig_mc1.add_vline(x=float(np.percentile(final_arr,5)), line_dash="dot", line_color="#ef4444", annotation_text="5th%")
            fig_mc1.add_vline(x=float(np.percentile(final_arr,50)), line_dash="dot", line_color="#22c55e", annotation_text="Median")
            fig_mc1.update_layout(title=f"Final Capital Distribution ({mc_n_sims:,} sims)",
                                   template=plotly_tpl, height=350, margin=dict(l=10,r=10,t=50,b=10))
            st.plotly_chart(fig_mc1, use_container_width=True)
            if ruin_rate > 10: st.error(f"⚠️ High risk of ruin: {ruin_rate:.1f}%")
            elif ruin_rate > 5: st.warning(f"⚡ Moderate ruin risk: {ruin_rate:.1f}%")
            else: st.success(f"✅ Low ruin risk: {ruin_rate:.1f}%")


# ══════════════════════════════════════════════════════════
# TAB 9 — ERROR LOG
# ══════════════════════════════════════════════════════════
with tab9:
    if st.session_state.error_log:
        st.dataframe(pd.DataFrame(st.session_state.error_log), use_container_width=True, hide_index=True)
        st.info("Common causes: Market closed, wrong suffix (.NS/.BO), Yahoo Finance rate limiting.")
        if st.button("🧹 Clear Error Log"):
            st.session_state.error_log = []; st.rerun()
    else:
        st.success("✅ No errors.")
    st.markdown("---")
    st.markdown("##### 🗄️ Cache Status")
    cache = st.session_state.fetch_cache; now_t = time.time()
    cache_rows = []
    for k, v in list(cache.items()):
        age = int(now_t - v["ts"]); parts = k.rsplit("_",1); itv = parts[-1] if len(parts)==2 else "?"
        ttl = _cache_ttl(itv)
        cache_rows.append({"Key":k,"Age (s)":age,"TTL (s)":ttl,
                           "Rows":len(v["df"]) if v["df"] is not None else 0,
                           "Status":"✅ Fresh" if age<ttl else "⏰ Stale"})
    if cache_rows:
        st.dataframe(pd.DataFrame(cache_rows), use_container_width=True, hide_index=True)
        if st.button("🗑️ Clear All Cache"):
            st.session_state.fetch_cache = {}; st.rerun()
    else:
        st.info("Cache empty.")

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

# ================================
# PAGE CONFIG
# ================================
st.set_page_config(
    page_title="ORB Smart Scanner Pro v4",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🚀"
)

# ================================
# DARK MODE
# ================================
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True  # default dark

dark = st.session_state.dark_mode
bg_main   = "#0a0d14" if dark else "#f5f7fa"
bg_card   = "#111827" if dark else "#ffffff"
bg_card2  = "#1a2035" if dark else "#f8fafc"
txt_main  = "#e2e8f0" if dark else "#111827"
txt_sub   = "#64748b" if dark else "#6b7280"
bdr_col   = "#1e293b" if dark else "#e2e8f0"
plotly_tpl= "plotly_dark" if dark else "plotly_white"
accent    = "#6366f1"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Outfit:wght@300;400;500;600;700;800&display=swap');
:root {{
    --bg-main:{bg_main}; --bg-card:{bg_card}; --bg-card2:{bg_card2};
    --txt:{txt_main}; --txt-sub:{txt_sub}; --bdr:{bdr_col};
    --accent:#6366f1; --green:#22c55e; --red:#ef4444;
    --yellow:#f59e0b; --blue:#3b82f6; --purple:#a855f7;
}}
html,body,[class*="css"]{{
    font-family:'Outfit',sans-serif;
    background:var(--bg-main)!important;
    color:var(--txt)!important;
}}
.block-container{{padding-top:.8rem;background:var(--bg-main);}}
.stMetric label{{font-size:.7rem;color:var(--txt-sub);letter-spacing:.07em;text-transform:uppercase;font-family:'Space Mono',monospace;}}
.stMetric [data-testid="stMetricValue"]{{font-size:1.4rem;font-weight:700;}}
.stSidebar,.stSidebar [data-testid="stSidebarContent"]{{background:var(--bg-card)!important;}}
div[data-testid="stDataFrame"]{{border-radius:12px;overflow:hidden;}}
.stButton>button{{border-radius:8px;font-family:'Outfit',sans-serif;font-weight:600;transition:all .2s;}}
.stButton>button[kind="primary"]{{background:linear-gradient(135deg,var(--accent),#7c3aed);border:none;color:#fff;}}
.stButton>button[kind="primary"]:hover{{transform:translateY(-1px);box-shadow:0 4px 20px rgba(99,102,241,.4);}}
div[data-testid="stTabs"] button{{font-family:'Outfit',sans-serif;font-weight:600;font-size:.85rem;}}

/* Signal badges */
.sig-strong-buy {{display:inline-block;padding:3px 10px;border-radius:20px;background:rgba(34,197,94,.2);color:#22c55e;font-weight:700;font-size:.78rem;border:1px solid rgba(34,197,94,.4);}}
.sig-buy        {{display:inline-block;padding:3px 10px;border-radius:20px;background:rgba(34,197,94,.1);color:#4ade80;font-weight:600;font-size:.78rem;border:1px solid rgba(74,222,128,.3);}}
.sig-weak-buy   {{display:inline-block;padding:3px 10px;border-radius:20px;background:rgba(34,197,94,.05);color:#86efac;font-weight:500;font-size:.78rem;border:1px solid rgba(134,239,172,.2);}}
.sig-neutral    {{display:inline-block;padding:3px 10px;border-radius:20px;background:rgba(100,116,139,.15);color:#94a3b8;font-weight:500;font-size:.78rem;border:1px solid rgba(148,163,184,.2);}}
.sig-weak-sell  {{display:inline-block;padding:3px 10px;border-radius:20px;background:rgba(239,68,68,.05);color:#fca5a5;font-weight:500;font-size:.78rem;border:1px solid rgba(252,165,165,.2);}}
.sig-sell       {{display:inline-block;padding:3px 10px;border-radius:20px;background:rgba(239,68,68,.1);color:#f87171;font-weight:600;font-size:.78rem;border:1px solid rgba(248,113,113,.3);}}
.sig-strong-sell{{display:inline-block;padding:3px 10px;border-radius:20px;background:rgba(239,68,68,.2);color:#ef4444;font-weight:700;font-size:.78rem;border:1px solid rgba(239,68,68,.4);}}
.sig-avoid      {{display:inline-block;padding:3px 10px;border-radius:20px;background:rgba(245,158,11,.15);color:#fbbf24;font-weight:700;font-size:.78rem;border:1px solid rgba(251,191,36,.3);}}

/* P&L colors */
.pnl-pos{{color:var(--green)!important;font-weight:700;}}
.pnl-neg{{color:var(--red)!important;font-weight:700;}}
.pnl-zero{{color:var(--txt-sub)!important;font-weight:500;}}

/* Cards */
.metric-card{{
    background:var(--bg-card);border:1px solid var(--bdr);border-radius:14px;
    padding:16px 20px;transition:border-color .2s;
}}
.metric-card:hover{{border-color:var(--accent);}}

.stat-box{{text-align:center;padding:14px;background:var(--bg-card);border-radius:12px;border:1px solid var(--bdr);}}
.stat-box .val{{font-size:1.5rem;font-weight:800;color:var(--txt);}}
.stat-box .lbl{{font-size:.68rem;color:var(--txt-sub);text-transform:uppercase;letter-spacing:.07em;margin-top:3px;font-family:'Space Mono',monospace;}}

.ctx-bar{{background:var(--bg-card);border:1px solid var(--bdr);border-radius:12px;padding:10px 18px;margin:8px 0;display:flex;gap:20px;align-items:center;flex-wrap:wrap;font-size:.87rem;}}
.hdr-title{{font-size:1.9rem;font-weight:800;letter-spacing:-.03em;color:var(--txt);}}
.hdr-sub{{font-size:.8rem;color:var(--txt-sub);margin-top:-6px;font-family:'Space Mono',monospace;}}

.lock-loss{{background:#2d1515;border:2px solid #ef4444;border-radius:10px;padding:12px 18px;text-align:center;color:#ef4444;font-weight:700;}}
.lock-profit{{background:#142d1a;border:2px solid #22c55e;border-radius:10px;padding:12px 18px;text-align:center;color:#22c55e;font-weight:700;}}

/* Portfolio table coloring */
.port-gain{{color:#22c55e!important;}}
.port-loss{{color:#ef4444!important;}}

.score-pill{{display:inline-flex;align-items:center;gap:6px;}}
.score-bar-inner{{height:6px;border-radius:3px;background:linear-gradient(90deg,#6366f1,#22c55e);display:inline-block;}}

.regime-trend   {{display:inline-block;padding:2px 10px;border-radius:20px;background:rgba(59,130,246,.2);color:#60a5fa;font-weight:700;font-size:.78rem;}}
.regime-range   {{display:inline-block;padding:2px 10px;border-radius:20px;background:rgba(245,158,11,.2);color:#fbbf24;font-weight:700;font-size:.78rem;}}
.regime-volatile{{display:inline-block;padding:2px 10px;border-radius:20px;background:rgba(239,68,68,.2);color:#f87171;font-weight:700;font-size:.78rem;}}
.regime-unknown {{display:inline-block;padding:2px 10px;border-radius:20px;background:rgba(100,116,139,.2);color:#94a3b8;font-weight:600;font-size:.78rem;}}

.vix-low {{display:inline-block;padding:2px 10px;border-radius:20px;background:rgba(34,197,94,.15);color:#22c55e;font-weight:700;font-size:.78rem;}}
.vix-mid {{display:inline-block;padding:2px 10px;border-radius:20px;background:rgba(245,158,11,.15);color:#fbbf24;font-weight:700;font-size:.78rem;}}
.vix-high{{display:inline-block;padding:2px 10px;border-radius:20px;background:rgba(239,68,68,.15);color:#ef4444;font-weight:700;font-size:.78rem;}}
</style>
""", unsafe_allow_html=True)

# ================================
# SOUND ALERT
# ================================
SOUND_JS = """<script>
function playSignalBeep(){
    try{var c=new(window.AudioContext||window.webkitAudioContext)();
    function b(f,s,d,v){var o=c.createOscillator(),g=c.createGain();o.connect(g);g.connect(c.destination);
    o.type='sine';o.frequency.value=f;g.gain.setValueAtTime(v||.3,c.currentTime+s);
    g.gain.exponentialRampToValueAtTime(.001,c.currentTime+s+d);o.start(c.currentTime+s);o.stop(c.currentTime+s+d+.1);}
    b(880,0,.15,.4);b(1100,.18,.15,.35);b(1320,.36,.25,.3);}catch(e){}}
window._orbSigCnt=window._orbSigCnt||0;
function checkAndBeep(n){if(n>window._orbSigCnt){playSignalBeep();window._orbSigCnt=n;}}
</script>"""
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
    "Bank Nifty": [
        "HDFCBANK.NS","ICICIBANK.NS","KOTAKBANK.NS","AXISBANK.NS","SBIN.NS",
        "INDUSINDBK.NS","BANDHANBNK.NS","FEDERALBNK.NS","IDFCFIRSTB.NS","PNB.NS",
        "BANKBARODA.NS","CANBK.NS","UNIONBANK.NS",
    ],
    "IT Sector": [
        "TCS.NS","INFOSYS.NS","WIPRO.NS","HCLTECH.NS","TECHM.NS",
        "MPHASIS.NS","PERSISTENT.NS","COFORGE.NS","OFSS.NS","KPITTECH.NS",
    ],
    "Pharma Sector": [
        "SUNPHARMA.NS","DRREDDY.NS","CIPLA.NS","DIVISLAB.NS","LUPIN.NS",
        "AUROPHARMA.NS","TORNTPHARM.NS","GLENMARK.NS","ALKEM.NS","LAURUSLABS.NS",
    ],
    "Custom (Enter Below)": [],
}

SECTOR_MAP = {
    "TCS.NS":"IT","INFOSYS.NS":"IT","WIPRO.NS":"IT","HCLTECH.NS":"IT","TECHM.NS":"IT",
    "MPHASIS.NS":"IT","PERSISTENT.NS":"IT","COFORGE.NS":"IT","OFSS.NS":"IT",
    "HDFCBANK.NS":"Bank","ICICIBANK.NS":"Bank","KOTAKBANK.NS":"Bank","AXISBANK.NS":"Bank","SBIN.NS":"Bank",
    "INDUSINDBK.NS":"Bank","BANDHANBNK.NS":"Bank","FEDERALBNK.NS":"Bank","PNB.NS":"Bank",
    "SUNPHARMA.NS":"Pharma","DRREDDY.NS":"Pharma","CIPLA.NS":"Pharma","DIVISLAB.NS":"Pharma",
    "MARUTI.NS":"Auto","TATAMOTORS.NS":"Auto","BAJAJ-AUTO.NS":"Auto","HEROMOTOCO.NS":"Auto",
    "RELIANCE.NS":"Energy","ONGC.NS":"Energy","BPCL.NS":"Energy","NTPC.NS":"Energy",
    "TATASTEEL.NS":"Metals","JSWSTEEL.NS":"Metals","HINDALCO.NS":"Metals","COALINDIA.NS":"Metals",
}

PERSISTENCE_FILE = "orb_session_v4.json"
WATCHLIST_FILE   = "orb_watchlist_v4.json"
PORTFOLIO_FILE   = "orb_portfolio_v4.json"

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
        "signal_state": {},
        "fetch_cache": {},
        "market_regime": "Unknown",
        # Portfolio holdings: {symbol: {"qty": int, "avg_cost": float, "added_time": str}}
        "portfolio": {},
        "dark_mode": True,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ================================
# PORTFOLIO PERSISTENCE
# ================================
def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_portfolio(data: dict):
    try:
        with open(PORTFOLIO_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception:
        pass

if not st.session_state.portfolio:
    st.session_state.portfolio = load_portfolio()

# ================================
# SESSION PERSISTENCE
# ================================
def save_session():
    try:
        data = {
            "capital": st.session_state.capital,
            "initial_capital": st.session_state.initial_capital,
            "active_trades": st.session_state.active_trades,
            "closed_trades": st.session_state.closed_trades,
            "daily_pnl": st.session_state.daily_pnl,
            "trading_locked": st.session_state.trading_locked,
            "lock_reason": st.session_state.lock_reason,
            "equity": [{"time": str(e["time"]), "capital": e["capital"]} for e in st.session_state.equity],
            "signal_state": st.session_state.signal_state,
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
# CACHE HELPERS
# ================================
def _cache_ttl(interval: str) -> int:
    return {"5m": 25, "15m": 60, "1h": 300, "1d": 300}.get(interval, 60)

def _cache_key(symbol: str, interval: str) -> str:
    return f"{symbol}_{interval}"

def cache_get(symbol: str, interval: str):
    key = _cache_key(symbol, interval)
    entry = st.session_state.fetch_cache.get(key)
    if entry and (time.time() - entry["ts"]) < _cache_ttl(interval):
        return entry["df"]
    return None

def cache_set(symbol: str, interval: str, df):
    key = _cache_key(symbol, interval)
    st.session_state.fetch_cache[key] = {"df": df, "ts": time.time()}

def cache_invalidate_expired():
    now = time.time()
    expired = [k for k, v in st.session_state.fetch_cache.items() if (now - v["ts"]) > 3600]
    for k in expired:
        del st.session_state.fetch_cache[k]

def snapshot_cache() -> dict:
    return dict(st.session_state.fetch_cache)

# ================================
# SIDEBAR
# ================================
with st.sidebar:
    st.markdown("## ⚙️ Scanner Settings")
    c1, c2 = st.columns([3,1])
    with c1: st.markdown("🌙 **Dark Mode**")
    with c2:
        if st.button("Toggle", key="dm_toggle"):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()

    st.markdown("### 📋 Symbol Selection")
    preset_choice = st.selectbox("Choose Preset", list(PRESETS.keys()), index=0)

    if preset_choice == "Custom (Enter Below)":
        custom_raw = st.text_area("Enter tickers (one per line)", placeholder="RELIANCE\nTCS", height=80)
        raw_list = [s.strip().upper() for s in custom_raw.replace(",","\n").splitlines() if s.strip()]
        symbols_pool = [s if s.endswith(".NS") or s.endswith(".BO") else s+".NS" for s in raw_list]
    else:
        symbols_pool = PRESETS[preset_choice]

    uploaded_csv = st.file_uploader("📂 Import CSV (Symbol column)", type=["csv"])
    csv_symbols = []
    if uploaded_csv:
        try:
            df_csv = pd.read_csv(uploaded_csv)
            col = next((c for c in df_csv.columns if "symbol" in c.lower()), df_csv.columns[0])
            csv_symbols = [s.strip().upper() + (".NS" if not s.strip().upper().endswith((".NS",".BO")) else "")
                           for s in df_csv[col].dropna().astype(str).tolist()]
            st.success(f"✅ {len(csv_symbols)} symbols loaded")
        except Exception as e:
            st.error(f"CSV error: {e}")

    if csv_symbols:
        symbols_pool = list(dict.fromkeys(symbols_pool + csv_symbols))

    default_saved = saved_watchlist.get(preset_choice, [])
    if default_saved and all(d in symbols_pool for d in default_saved):
        default_sel = default_saved
    else:
        default_sel = symbols_pool[:10] if len(symbols_pool) > 10 else symbols_pool

    selected_symbols = st.multiselect(
        f"Select symbols ({len(symbols_pool)} available)", symbols_pool, default=default_sel
    ) if symbols_pool else []

    if selected_symbols != saved_watchlist.get(preset_choice, []):
        saved_watchlist[preset_choice] = selected_symbols
        save_watchlist(saved_watchlist)

    extra_raw = st.text_input("➕ Extra tickers", placeholder="ZOMATO,PAYTM")
    if extra_raw.strip():
        extras = [s.strip().upper() + ("" if s.strip().upper().endswith(".NS") else ".NS")
                  for s in extra_raw.split(",") if s.strip()]
        selected_symbols = list(dict.fromkeys(selected_symbols + extras))

    st.caption(f"**{len(selected_symbols)}** symbols selected")
    st.divider()

    st.markdown("### 📐 Strategy Parameters")
    orb_minutes    = st.number_input("ORB Minutes", 5, 60, 15)
    ema_period     = st.number_input("EMA Period (5m)", 5, 100, 20)
    ema_15m_period = st.number_input("EMA Period (15m)", 5, 100, 20)
    ema_1h_period  = st.number_input("EMA Period (1h)", 5, 50, 20)
    atr_period     = st.number_input("ATR Period", 5, 30, 14)
    rsi_period     = st.number_input("RSI Period", 5, 30, 14)
    st_atr_mult    = st.slider("Supertrend ATR Mult", 1.0, 5.0, 3.0, 0.5)

    st.divider()
    st.markdown("### 🛡️ Stop Loss")
    sl_strategy    = st.selectbox("SL Method", ["Supertrend","Chandelier Exit","Fixed ATR","Swing High/Low","Fixed %"])
    sl_atr_mult    = st.slider("SL ATR Multiplier", 1.0, 5.0, 2.0, 0.25)
    swing_lookback = st.number_input("Swing Lookback Bars", 3, 20, 5)
    trail_pct      = st.slider("Trail %", 0.1, 2.0, 0.5, 0.05) / 100

    st.divider()
    st.markdown("### 💰 Risk Management")
    initial_capital = st.number_input("Initial Capital (₹)", 10_000, 10_000_000, 100_000, step=10_000)
    if st.button("🔁 Reset Capital"):
        st.session_state.capital = initial_capital
        st.session_state.initial_capital = initial_capital
        st.session_state.active_trades = {}
        st.session_state.closed_trades = []
        st.session_state.equity = []
        st.session_state.daily_pnl = 0.0
        st.session_state.trading_locked = False
        st.session_state.lock_reason = ""
        st.session_state.signal_state = {}
        save_session()
        st.rerun()

    risk_pct     = st.slider("Risk per Trade (%)", 0.5, 3.0, 1.0, 0.1)
    max_trades   = st.number_input("Max Concurrent Trades", 1, 30, 5)
    max_risk_pct = st.slider("Max Portfolio Risk (%)", 1.0, 10.0, 5.0, 0.5)

    st.divider()
    st.markdown("### 📅 Daily Limits")
    daily_loss_limit_pct    = st.slider("Daily Loss Limit (%)", 0.5, 10.0, 3.0, 0.5)
    daily_profit_target_pct = st.slider("Daily Profit Target (%)", 1.0, 20.0, 5.0, 0.5)

    st.divider()
    st.markdown("### 🔍 Signal Filters")
    min_vol_ratio = st.slider("Min Volume Ratio", 1.0, 5.0, 1.5, 0.1)
    min_body_pct  = st.slider("Min Candle Body %", 0.3, 0.9, 0.5, 0.05)
    min_ema_dist  = st.slider("Min EMA Distance %", 0.1, 2.0, 0.3, 0.1) / 100
    max_ema_dist  = st.slider("Max EMA Distance %", 0.5, 5.0, 3.0, 0.1) / 100
    min_atr_ratio = st.slider("Min ATR Ratio %", 0.1, 1.0, 0.2, 0.05) / 100
    rsi_buy_min   = st.slider("RSI Min for BUY", 40, 70, 50)
    rsi_sell_max  = st.slider("RSI Max for SELL", 30, 60, 50)
    use_mtf       = st.checkbox("15m EMA Confirmation", True)
    use_3tf       = st.checkbox("1h EMA Confluence", True)
    use_macd      = st.checkbox("MACD Filter", True)
    use_regime    = st.checkbox("Market Regime Filter", True)
    use_nifty_filter   = st.checkbox("Nifty Index Filter", True)
    use_vix_sizing     = st.checkbox("VIX-Based Position Sizing", True)
    use_gap_detect     = st.checkbox("Gap Detection", True)
    gap_pct            = st.slider("Gap Threshold (%)", 0.5, 3.0, 1.0, 0.1) / 100
    use_partial        = st.checkbox("Partial Profit @ 1×ATR", True)

    st.divider()
    st.markdown("### 📡 Alerts")
    with st.expander("📱 Telegram"):
        tg_token   = st.text_input("Bot Token", type="password")
        tg_chat_id = st.text_input("Chat ID")
        send_tg    = st.checkbox("Enable Telegram", False)
    with st.expander("🎮 Discord"):
        discord_webhook = st.text_input("Discord Webhook URL", type="password")
        send_discord    = st.checkbox("Enable Discord", False)

    max_retries   = st.number_input("Max Fetch Retries", 1, 5, 3)
    show_errors   = st.checkbox("Show fetch errors", False)


# ================================
# ALERT DISPATCHER
# ================================
def send_alert(msg: str, html_msg: str = None):
    if send_tg and tg_token and tg_chat_id:
        try:
            requests.post(f"https://api.telegram.org/bot{tg_token}/sendMessage",
                          data={"chat_id": tg_chat_id, "text": html_msg or msg, "parse_mode":"HTML"}, timeout=5)
        except Exception: pass
    if send_discord and discord_webhook:
        try:
            requests.post(discord_webhook, json={"content": msg}, timeout=5)
        except Exception: pass


# ================================
# CORE FETCH — THREAD-SAFE
# ================================
def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty: return df
    if isinstance(df.columns, pd.MultiIndex):
        lvl1 = df.columns.get_level_values(1).unique().tolist()
        if len(lvl1) <= 1:
            df.columns = df.columns.get_level_values(0)
        else:
            df = df.xs(lvl1[0], axis=1, level=1)
    df.columns = [str(c).strip().title() for c in df.columns]
    rename_map = {"Adj Close":"Close","Adj_Close":"Close","Adjclose":"Close","Adj close":"Close"}
    df.rename(columns=rename_map, inplace=True)
    return df

def fetch(symbol: str, interval: str = "5m", period: str = "5d",
          use_cache: bool = True, _cache_snapshot: dict = None) -> tuple:
    required_cols = {"Open","High","Low","Close","Volume"}
    if _cache_snapshot is None: _cache_snapshot = {}
    if use_cache:
        key = _cache_key(symbol, interval)
        entry = _cache_snapshot.get(key)
        if entry and (time.time() - entry["ts"]) < _cache_ttl(interval):
            return symbol, entry["df"], None, None

    strategies = [{"interval":interval,"period":period},
                  {"interval":interval,"period":"5d"},
                  {"interval":interval,"period":"1mo"}]
    if interval == "1d": strategies = [{"interval":"1d","period":"5d"}]
    if interval == "1h": strategies = [{"interval":"1h","period":"5d"},{"interval":"1h","period":"1mo"}]

    last_err = "Unknown error"
    for attempt in range(int(max_retries)):
        for strat in strategies:
            try:
                raw = yf.download(symbol, interval=strat["interval"], period=strat["period"],
                                  progress=False, auto_adjust=True, actions=False)
                if raw is None or raw.empty:
                    last_err = f"Empty response"; continue
                df = _flatten_columns(raw.copy())
                missing = required_cols - set(df.columns)
                if missing: last_err = f"Missing cols: {missing}"; continue
                df.dropna(subset=["Open","High","Low","Close"], how="all", inplace=True)
                if len(df) < 10: last_err = f"Too few bars: {len(df)}"; continue
                if not isinstance(df.index, pd.DatetimeIndex):
                    df.index = pd.to_datetime(df.index)
                if df.index.tz is not None:
                    df.index = df.index.tz_convert("Asia/Kolkata").tz_localize(None)
                df.sort_index(inplace=True)
                new_entry = {"df": df, "ts": time.time()}
                return symbol, df, None, (_cache_key(symbol, interval), new_entry)
            except Exception as e:
                last_err = f"{type(e).__name__}: {str(e)[:100]}"; continue
        if attempt < int(max_retries) - 1:
            time.sleep((2 ** attempt) + random.uniform(0, 1))

    return symbol, None, last_err, None

def _apply_cache_write(result_tuple):
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
        _, nifty, _, _ = fetch("^NSEI", interval="1d", period="5d", use_cache=False, _cache_snapshot={})
        if nifty is not None and len(nifty) >= 2:
            result["nifty_price"]  = float(nifty["Close"].iloc[-1])
            result["nifty_change"] = float(nifty["Close"].iloc[-1] - nifty["Close"].iloc[-2])
    except Exception: pass
    try:
        _, vix, _, _ = fetch("^INDIAVIX", interval="1d", period="5d", use_cache=False, _cache_snapshot={})
        if vix is not None and not vix.empty:
            result["vix"] = float(vix["Close"].iloc[-1])
    except Exception: pass
    return result

mkt_ctx = fetch_nifty_vix()
st.session_state.nifty_trend = mkt_ctx["nifty_change"]
st.session_state.vix_value   = mkt_ctx["vix"]


# ================================
# MARKET REGIME
# ================================
def detect_market_regime(df: pd.DataFrame) -> str:
    if df is None or len(df) < 20: return "Unknown"
    try:
        high, low, close = df["High"], df["Low"], df["Close"]
        tr = pd.concat([high-low, (high-close.shift(1)).abs(), (low-close.shift(1)).abs()], axis=1).max(axis=1)
        atr14 = tr.rolling(14, min_periods=1).mean()
        dm_plus  = (high.diff()).clip(lower=0)
        dm_minus = (-low.diff()).clip(lower=0)
        dp_arr = np.where(dm_plus > dm_minus, dm_plus, 0)
        dm_arr = np.where(pd.Series(dm_minus) > pd.Series(dm_plus), dm_minus, 0)
        di_p = 100 * pd.Series(dp_arr).rolling(14, min_periods=1).mean() / atr14.replace(0, np.nan).fillna(1)
        di_m = 100 * pd.Series(dm_arr).rolling(14, min_periods=1).mean() / atr14.replace(0, np.nan).fillna(1)
        dx   = 100 * (di_p - di_m).abs() / (di_p + di_m).replace(0, np.nan).fillna(1)
        adx  = dx.rolling(14, min_periods=1).mean().iloc[-1]
        sma20 = close.rolling(20, min_periods=5).mean()
        std20 = close.rolling(20, min_periods=5).std()
        bb_w  = (2 * std20 / sma20.replace(0, np.nan).fillna(1)).iloc[-1]
        if adx > 25: return "Trending"
        elif bb_w > 0.04: return "Volatile"
        else: return "Ranging"
    except Exception: return "Unknown"


# ================================
# INDICATORS
# ================================
def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    close, high, low, vol = df["Close"], df["High"], df["Low"], df["Volume"]
    df["EMA"] = close.ewm(span=ema_period, adjust=False).mean()
    prev_close = close.shift(1)
    df["TR"]  = pd.concat([high-low, (high-prev_close).abs(), (low-prev_close).abs()], axis=1).max(axis=1)
    df["ATR"] = df["TR"].rolling(atr_period, min_periods=1).mean()
    df["Vol_Avg"] = vol.rolling(20, min_periods=5).mean()
    body = (close - df["Open"]).abs()
    rng  = (high - low).replace(0, np.nan).fillna(1e-9)
    df["BodyPct"] = (body / rng).clip(0, 1)
    delta = close.diff()
    gain, loss = delta.clip(lower=0), (-delta).clip(lower=0)
    avg_g = gain.ewm(com=rsi_period-1, adjust=False).mean()
    avg_l = loss.ewm(com=rsi_period-1, adjust=False).mean()
    rs = avg_g / avg_l.replace(0, np.nan).fillna(1e-9)
    df["RSI"] = 100 - (100/(1+rs))
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_sig"]  = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_sig"]

    # Supertrend
    hl2 = (high + low) / 2
    ub = (hl2 + st_atr_mult * df["ATR"]).values.copy()
    lb = (hl2 - st_atr_mult * df["ATR"]).values.copy()
    cl = close.values
    st_dir = np.ones(len(df), dtype=int)
    st_val = np.zeros(len(df))
    for i in range(1, len(df)):
        if cl[i-1] <= ub[i-1]: ub[i] = min(ub[i], ub[i-1])
        if cl[i-1] >= lb[i-1]: lb[i] = max(lb[i], lb[i-1])
        if st_dir[i-1] == -1 and cl[i] > ub[i]: st_dir[i] = 1
        elif st_dir[i-1] == 1 and cl[i] < lb[i]: st_dir[i] = -1
        else: st_dir[i] = st_dir[i-1]
        st_val[i] = lb[i] if st_dir[i] == 1 else ub[i]
    df["ST_dir"] = st_dir
    df["ST_val"] = st_val
    return df

def add_indicators_15m(df): 
    df = df.copy(); df["EMA15"] = df["Close"].ewm(span=ema_15m_period, adjust=False).mean(); return df
def add_indicators_1h(df):  
    df = df.copy(); df["EMA1H"] = df["Close"].ewm(span=ema_1h_period,  adjust=False).mean(); return df


# ================================
# ORB RANGE HELPER
# ================================
def get_orb_range(df: pd.DataFrame):
    df = df.copy(); df.index = pd.to_datetime(df.index)
    last_date = df.index.normalize().max()
    day_df = df[df.index.normalize() == last_date].copy()
    day_df["_time"] = day_df.index.time
    market_start = dtime(9, 15)
    orb_end_time = (datetime.combine(last_date.date(), market_start) + timedelta(minutes=int(orb_minutes))).time()
    orb_df = day_df[day_df["_time"] <= orb_end_time]
    return orb_df, day_df


# ================================
# COMPUTE ALL METRICS FOR A SYMBOL
# (called for every symbol regardless of signal)
# ================================
def compute_symbol_metrics(df_5m, df_15m=None, df_1h=None):
    """Returns dict with all indicator values computed. Never returns — for any field."""
    metrics = {
        "orb_high": None, "orb_low": None, "last_price": None,
        "atr": None, "vol_ratio": None, "rsi": None, "body_pct": None,
        "ema": None, "macd_hist": None, "gap_pct": None,
        "mtf_ok": None, "tf3_ok": None, "regime": "Unknown",
        "direction": None,  # which way is price vs ORB
    }
    if df_5m is None or len(df_5m) < 10:
        return metrics

    df = add_indicators(df_5m)
    df.index = pd.to_datetime(df.index)

    orb_df, day_df = get_orb_range(df)
    if len(orb_df) < 1:
        orb_df = df.iloc[:max(2, int(orb_minutes // 5))]
        day_df = df

    metrics["orb_high"]   = round(float(orb_df["High"].max()), 2)
    metrics["orb_low"]    = round(float(orb_df["Low"].min()), 2)
    metrics["last_price"] = round(float(df["Close"].iloc[-1]), 2)

    if not pd.isna(df["ATR"].iloc[-1]):
        metrics["atr"] = round(float(df["ATR"].iloc[-1]), 2)
    if not pd.isna(df["Vol_Avg"].iloc[-1]) and float(df["Vol_Avg"].iloc[-1]) > 0:
        metrics["vol_ratio"] = round(float(df["Volume"].iloc[-1]) / float(df["Vol_Avg"].iloc[-1]), 2)
    if not pd.isna(df["RSI"].iloc[-1]):
        metrics["rsi"] = round(float(df["RSI"].iloc[-1]), 1)
    if not pd.isna(df["BodyPct"].iloc[-1]):
        metrics["body_pct"] = round(float(df["BodyPct"].iloc[-1]), 2)
    if not pd.isna(df["EMA"].iloc[-1]):
        metrics["ema"] = round(float(df["EMA"].iloc[-1]), 2)
    if not pd.isna(df["MACD_hist"].iloc[-1]):
        metrics["macd_hist"] = round(float(df["MACD_hist"].iloc[-1]), 4)

    # Gap %
    try:
        dates = df.index.normalize().unique()
        if len(dates) >= 2:
            t_open = float(df[df.index.normalize()==dates[-1]]["Open"].iloc[0])
            y_close = float(df[df.index.normalize()==dates[-2]]["Close"].iloc[-1])
            if y_close > 0:
                metrics["gap_pct"] = round((t_open - y_close) / y_close * 100, 2)
    except Exception:
        metrics["gap_pct"] = 0.0

    # 3TF / MTF
    if use_3tf and df_1h is not None and len(df_1h) >= ema_1h_period + 2:
        df1h = add_indicators_1h(df_1h)
        metrics["tf3_ok"] = float(df1h["EMA1H"].iloc[-1]) > float(df1h["EMA1H"].iloc[-2])
    if use_mtf and df_15m is not None and len(df_15m) >= ema_15m_period + 2:
        df15 = add_indicators_15m(df_15m)
        metrics["mtf_ok"] = float(df15["EMA15"].iloc[-1]) > float(df15["EMA15"].iloc[-2])

    # Regime
    metrics["regime"] = detect_market_regime(df)

    # Direction vs ORB
    last = metrics["last_price"]
    if metrics["orb_high"] and metrics["orb_low"]:
        if last > metrics["orb_high"]:
            metrics["direction"] = "BUY"
        elif last < metrics["orb_low"]:
            metrics["direction"] = "SELL"
        else:
            metrics["direction"] = "NEUTRAL"

    return metrics


# ================================
# SIGNAL STRENGTH LABELING
# ================================
def compute_signal_label(metrics: dict, filters_passed: bool, filter_fail_reason: str) -> tuple:
    """
    Returns (label_str, score_float, css_class)
    Labels: Strong Buy, Buy, Weak Buy, Neutral, Weak Sell, Sell, Strong Sell, Avoid Buy
    """
    direction = metrics.get("direction", "NEUTRAL")
    vol_ratio = metrics.get("vol_ratio") or 0
    rsi       = metrics.get("rsi") or 50
    body_pct  = metrics.get("body_pct") or 0
    mtf_ok    = metrics.get("mtf_ok")
    tf3_ok    = metrics.get("tf3_ok")
    atr       = metrics.get("atr") or 0
    price     = metrics.get("last_price") or 1
    ema       = metrics.get("ema") or price
    macd_hist = metrics.get("macd_hist") or 0
    gap_pct   = metrics.get("gap_pct") or 0

    if direction == "NEUTRAL" or direction is None:
        return "⚪ Neutral", 0.0, "sig-neutral"

    # Score components (0-10)
    score = 0.0

    # Volume (0-2)
    if vol_ratio >= 3.0:       score += 2.0
    elif vol_ratio >= 2.0:     score += 1.5
    elif vol_ratio >= 1.5:     score += 1.0
    elif vol_ratio >= 1.2:     score += 0.5

    # RSI (0-2)
    if direction == "BUY":
        if rsi >= 65:          score += 2.0
        elif rsi >= 58:        score += 1.5
        elif rsi >= 52:        score += 1.0
        elif rsi >= 45:        score += 0.5
    else:  # SELL
        if rsi <= 35:          score += 2.0
        elif rsi <= 42:        score += 1.5
        elif rsi <= 48:        score += 1.0
        elif rsi <= 55:        score += 0.5

    # Body (0-1.5)
    if body_pct >= 0.8:        score += 1.5
    elif body_pct >= 0.65:     score += 1.0
    elif body_pct >= 0.5:      score += 0.6
    elif body_pct >= 0.35:     score += 0.3

    # MTF (0-1.5)
    if mtf_ok is True and direction == "BUY":   score += 1.5
    elif mtf_ok is False and direction == "BUY": score -= 0.5
    elif mtf_ok is True and direction == "SELL": score += 1.5
    elif mtf_ok is False and direction == "SELL": score -= 0.5

    # 3TF (0-2)
    if tf3_ok is True and direction == "BUY":   score += 2.0
    elif tf3_ok is False and direction == "BUY": score -= 1.0
    elif tf3_ok is True and direction == "SELL": score += 2.0
    elif tf3_ok is False and direction == "SELL": score -= 1.0

    # MACD (0-1)
    if direction == "BUY" and macd_hist > 0:   score += 1.0
    elif direction == "SELL" and macd_hist < 0: score += 1.0

    # Gap bonus
    if direction == "BUY" and gap_pct > 0.5:   score += 0.5
    elif direction == "SELL" and gap_pct < -0.5: score += 0.5

    score = max(0, min(10, score))
    score_5 = round(score / 10 * 5, 1)

    # Determine label
    if direction == "BUY":
        if score >= 8.5:   label, css = "🟢 Strong Buy",  "sig-strong-buy"
        elif score >= 6.5: label, css = "🟢 Buy",         "sig-buy"
        elif score >= 4.5: label, css = "🟡 Weak Buy",    "sig-weak-buy"
        elif score >= 2.5: label, css = "🔵 Avoid Buy",   "sig-avoid"
        else:              label, css = "⚪ Neutral",      "sig-neutral"
    else:  # SELL
        if score >= 8.5:   label, css = "🔴 Strong Sell", "sig-strong-sell"
        elif score >= 6.5: label, css = "🔴 Sell",        "sig-sell"
        elif score >= 4.5: label, css = "🟠 Weak Sell",   "sig-weak-sell"
        elif score >= 2.5: label, css = "🔵 Avoid Sell",  "sig-avoid"
        else:              label, css = "⚪ Neutral",      "sig-neutral"

    return label, score_5, css


# ================================
# ORIGINAL SIGNAL GATE (pass/fail filters)
# ================================
def passes_entry_filters(df_5m, metrics: dict, df_15m=None, df_1h=None) -> tuple:
    """Returns (passes: bool, reason: str). Uses all strict filters."""
    direction = metrics.get("direction")
    if direction is None or direction == "NEUTRAL":
        return False, "Price inside ORB range"

    orb_high, orb_low = metrics["orb_high"], metrics["orb_low"]
    if orb_high is None or orb_low is None or orb_high == orb_low:
        return False, "ORB range zero"

    df = add_indicators(df_5m)
    last = float(df["Close"].iloc[-1])
    level = orb_high if direction == "BUY" else orb_low

    # 2-bar confirmation
    if len(df) >= 2:
        prev = float(df["Close"].iloc[-2])
        if direction == "BUY" and not (prev > level and last > level):
            return False, "Breakout not confirmed (2-bar)"
        if direction == "SELL" and not (prev < level and last < level):
            return False, "Breakout not confirmed (2-bar)"

    body_pct = metrics.get("body_pct") or 0
    if body_pct < min_body_pct:
        return False, f"Weak body ({body_pct:.2f} < {min_body_pct})"

    vol_ratio = metrics.get("vol_ratio") or 0
    if vol_ratio < min_vol_ratio:
        return False, f"Low volume ({vol_ratio:.1f}x < {min_vol_ratio}x)"

    ema = metrics.get("ema") or last
    if ema > 0:
        dist = abs(last - ema) / ema
        if not (min_ema_dist <= dist <= max_ema_dist):
            return False, f"EMA dist out of range ({dist*100:.2f}%)"

    atr = metrics.get("atr") or 0
    if last > 0 and (atr / last) < min_atr_ratio:
        return False, "Low ATR (low volatility)"

    rsi = metrics.get("rsi") or 50
    if direction == "BUY" and rsi < rsi_buy_min:
        return False, f"RSI too low ({rsi} < {rsi_buy_min})"
    if direction == "SELL" and rsi > rsi_sell_max:
        return False, f"RSI too high ({rsi} > {rsi_sell_max})"

    macd_hist = metrics.get("macd_hist") or 0
    if use_macd:
        if direction == "BUY" and macd_hist < 0:
            return False, "MACD against BUY"
        if direction == "SELL" and macd_hist > 0:
            return False, "MACD against SELL"

    regime = metrics.get("regime", "Unknown")
    if use_regime and regime == "Ranging":
        return False, "Market Ranging — ORB suppressed"

    if use_3tf and metrics.get("tf3_ok") is False:
        return False, "1h 3TF failed"
    if use_mtf and metrics.get("mtf_ok") is False:
        return False, "15m MTF failed"

    nifty_chg = st.session_state.nifty_trend or 0
    if use_nifty_filter and direction == "BUY" and nifty_chg < 0:
        return False, "Nifty RED — BUY skipped"

    return True, "All filters passed"


# ================================
# SL COMPUTATION
# ================================
def compute_sl(df, direction, entry_price, orb_low, orb_high):
    atr = float(df["ATR"].iloc[-1]) if "ATR" in df.columns and not pd.isna(df["ATR"].iloc[-1]) else 0
    n = int(swing_lookback)
    if sl_strategy == "Supertrend" and "ST_val" in df.columns:
        return float(df["ST_val"].iloc[-1])
    elif sl_strategy == "Chandelier Exit":
        if direction == "BUY":
            return round(float(df["High"].rolling(n, min_periods=1).max().iloc[-1]) - sl_atr_mult * atr, 2)
        else:
            return round(float(df["Low"].rolling(n, min_periods=1).min().iloc[-1]) + sl_atr_mult * atr, 2)
    elif sl_strategy == "Fixed ATR":
        return round(entry_price - sl_atr_mult*atr, 2) if direction=="BUY" else round(entry_price+sl_atr_mult*atr, 2)
    elif sl_strategy == "Swing High/Low":
        if direction == "BUY":
            return round(float(df["Low"].rolling(n, min_periods=1).min().iloc[-1]) - 0.1*atr, 2)
        else:
            return round(float(df["High"].rolling(n, min_periods=1).max().iloc[-1]) + 0.1*atr, 2)
    elif sl_strategy == "Fixed %":
        return round(entry_price*(1-trail_pct), 2) if direction=="BUY" else round(entry_price*(1+trail_pct), 2)
    return orb_low if direction == "BUY" else orb_high

def update_sl(df, trade, current_price):
    direction, current_sl = trade["type"], trade["sl"]
    n = int(swing_lookback)
    atr = float(df["ATR"].iloc[-1]) if "ATR" in df.columns and not pd.isna(df["ATR"].iloc[-1]) else 0
    if sl_strategy == "Supertrend" and "ST_val" in df.columns:
        new_sl = float(df["ST_val"].iloc[-1])
    elif sl_strategy == "Fixed ATR":
        new_sl = current_price - sl_atr_mult*atr if direction=="BUY" else current_price+sl_atr_mult*atr
    elif sl_strategy == "Fixed %":
        new_sl = current_price*(1-trail_pct) if direction=="BUY" else current_price*(1+trail_pct)
    else:
        new_sl = current_sl
    return round(max(current_sl, new_sl), 2) if direction=="BUY" else round(min(current_sl, new_sl), 2)


# ================================
# SIGNAL STATE (deduplication)
# ================================
def is_new_breakout(symbol, direction, level):
    state = st.session_state.signal_state.get(symbol, {})
    prev_dir, prev_level, prev_fired = state.get("direction"), state.get("level"), state.get("fired", False)
    if prev_dir != direction or (prev_level and abs(level-prev_level)/max(prev_level,1) > 0.005):
        st.session_state.signal_state[symbol] = {"direction":direction,"level":level,"fired":True}
        return True
    if prev_fired: return False
    st.session_state.signal_state[symbol]["fired"] = True
    return True

def reset_signal_state(symbol):
    if symbol in st.session_state.signal_state:
        st.session_state.signal_state[symbol]["fired"] = False


# ================================
# POSITION SIZING
# ================================
def calculate_qty(entry, sl, vix_factor=1.0):
    risk_amount    = st.session_state.capital * (risk_pct / 100) * vix_factor
    risk_per_share = abs(entry - sl)
    if risk_per_share == 0: return 0
    return max(1, int(risk_amount / risk_per_share))

def total_risk_deployed():
    return sum(abs(t["entry"]-t["sl"])*t["qty"] for t in st.session_state.active_trades.values())


# ================================
# TRADE MANAGEMENT
# ================================
def enter_trade(symbol, direction, price, sl, atr, vix_factor, signal_meta):
    if st.session_state.trading_locked: return
    tgt         = price + 2*atr if direction == "BUY" else price - 2*atr
    tgt_partial = price + 1*atr if direction == "BUY" else price - 1*atr
    qty = calculate_qty(price, sl, vix_factor)
    if qty == 0: return
    new_risk = abs(price-sl)*qty
    if (total_risk_deployed()+new_risk)/max(st.session_state.capital,1) > (max_risk_pct/100): return
    st.session_state.active_trades[symbol] = {
        "type":direction,"entry":price,"sl":round(sl,2),
        "target":round(tgt,2),"target_partial":round(tgt_partial,2),
        "qty":qty,"qty_remaining":qty,"partial_done":False,"breakeven_sl":False,
        "entry_time":datetime.now().strftime("%H:%M:%S"),"atr":atr,
        "sl_strategy":sl_strategy,"regime":signal_meta.get("regime","—"),
        "score":signal_meta.get("score_5",0),"label":signal_meta.get("label","—"),
        "vol_ratio":signal_meta.get("vol_ratio","—"),"rsi":signal_meta.get("rsi","—"),
    }
    send_alert(f"🚀 ORB — {symbol}\n{direction} @ ₹{price} | SL ₹{sl} | Tgt ₹{round(tgt,2)}\nQty:{qty}")

def manage_trade(symbol, df):
    trade = st.session_state.active_trades[symbol]
    price = float(df["Close"].iloc[-1])
    direction = trade["type"]
    df_ind = add_indicators(df)
    if use_partial and not trade["partial_done"] and trade["qty_remaining"] > 1:
        hit_p = (direction=="BUY" and price>=trade["target_partial"]) or \
                (direction=="SELL" and price<=trade["target_partial"])
        if hit_p:
            pq = trade["qty_remaining"] // 2
            if pq > 0:
                ppnl = (price-trade["entry"])*pq if direction=="BUY" else (trade["entry"]-price)*pq
                trade["qty_remaining"] -= pq
                trade["partial_done"] = True; trade["breakeven_sl"] = True; trade["sl"] = trade["entry"]
                st.session_state.capital += round(ppnl, 2); st.session_state.daily_pnl += round(ppnl, 2)
    trade["sl"] = update_sl(df_ind, trade, price)
    if direction == "BUY":
        if price <= trade["sl"]: exit_trade(symbol, price, (price-trade["entry"])*trade["qty_remaining"], "SL Hit")
        elif price >= trade["target"]: exit_trade(symbol, price, (price-trade["entry"])*trade["qty_remaining"], "Target Hit")
    else:
        if price >= trade["sl"]: exit_trade(symbol, price, (trade["entry"]-price)*trade["qty_remaining"], "SL Hit")
        elif price <= trade["target"]: exit_trade(symbol, price, (trade["entry"]-price)*trade["qty_remaining"], "Target Hit")

def exit_trade(symbol, price, pnl, reason="Manual"):
    if symbol not in st.session_state.active_trades: return
    trade = st.session_state.active_trades.pop(symbol)
    st.session_state.capital   += round(pnl, 2)
    st.session_state.daily_pnl += round(pnl, 2)
    entry_val = trade["entry"] * trade.get("qty_remaining", trade["qty"])
    st.session_state.closed_trades.append({
        "Symbol":trade.get("type","—"),"Type":trade["type"],
        "Entry":trade["entry"],"Exit":round(price,2),
        "Qty":trade.get("qty_remaining",trade["qty"]),
        "PnL (₹)":round(pnl,2),
        "PnL %":round((pnl/entry_val)*100,2) if entry_val else 0,
        "Score":trade.get("score","—"),"Signal":trade.get("label","—"),
        "SL Strategy":trade.get("sl_strategy","—"),"Reason":reason,
        "Entry Time":trade.get("entry_time","—"),
        "Exit Time":datetime.now().strftime("%H:%M:%S"),
        "Regime":trade.get("regime","—"),"Note":"",
        "Symbol_":symbol,
    })
    reset_signal_state(symbol)
    send_alert(f"{'✅' if pnl>0 else '❌'} Exit {symbol} @ ₹{price:.2f} | P&L ₹{pnl:+.2f} | {reason}")


# ================================
# DAILY P&L LOCK CHECK
# ================================
ic = st.session_state.get("initial_capital", 100_000)
daily_loss_cap   = ic * (daily_loss_limit_pct / 100)
daily_profit_cap = ic * (daily_profit_target_pct / 100)
if not st.session_state.trading_locked:
    if st.session_state.daily_pnl <= -daily_loss_cap:
        st.session_state.trading_locked = True
        st.session_state.lock_reason = f"Daily loss limit ₹{daily_loss_cap:,.0f} hit"
    elif st.session_state.daily_pnl >= daily_profit_cap:
        st.session_state.trading_locked = True
        st.session_state.lock_reason = f"Daily profit target ₹{daily_profit_cap:,.0f} reached"


# ================================
# HELPER: P&L COLOR CLASS
# ================================
def pnl_cls(v):
    if v > 0: return "pnl-pos"
    if v < 0: return "pnl-neg"
    return "pnl-zero"

def fmt_pnl(v, prefix="₹"):
    cls = pnl_cls(v)
    sign = "+" if v >= 0 else ""
    return f'<span class="{cls}">{prefix}{sign}{v:,.2f}</span>'


# ================================
# HEADER
# ================================
ch1, ch2, ch3, ch4, ch5 = st.columns([4,1,1,1,1])
with ch1:
    st.markdown('<div class="hdr-title">🚀 ORB Smart Scanner <span style="color:#6366f1;font-size:.9rem;font-weight:700;vertical-align:middle;">PRO v4</span></div>', unsafe_allow_html=True)
    status_txt = "🟢 Market Open" if market_open else ("🟡 Pre-Market" if is_pre_market() else "🔴 Market Closed")
    regime_cls_map = {"Trending":"regime-trend","Ranging":"regime-range","Volatile":"regime-volatile"}
    regime_css = regime_cls_map.get(st.session_state.market_regime, "regime-unknown")
    st.markdown(f'<div class="hdr-sub">{status_txt} &nbsp;|&nbsp; {datetime.now().strftime("%d %b %Y %H:%M:%S")} &nbsp;|&nbsp; {len(selected_symbols)} symbols &nbsp;|&nbsp; <span class="{regime_css}">{st.session_state.market_regime}</span></div>', unsafe_allow_html=True)
with ch2:
    manual_scan = st.button("🔄 Scan Now", use_container_width=True, type="primary")
with ch3:
    if st.button("🧹 Clear Trades", use_container_width=True):
        st.session_state.active_trades = {}; st.session_state.closed_trades = []; st.session_state.signal_state = {}
        save_session(); st.rerun()
with ch4:
    if st.button("🔓 Unlock", use_container_width=True):
        st.session_state.trading_locked = False; st.session_state.lock_reason = ""; st.rerun()
with ch5:
    if st.button("🗑️ Clear Cache", use_container_width=True):
        st.session_state.fetch_cache = {}; st.rerun()

if st.session_state.trading_locked:
    css_lock = "lock-profit" if "profit" in st.session_state.lock_reason.lower() else "lock-loss"
    st.markdown(f'<div class="{css_lock}">{"🏆" if "profit" in st.session_state.lock_reason.lower() else "🛑"} TRADING LOCKED — {st.session_state.lock_reason}</div>', unsafe_allow_html=True)

if not market_open:
    st.info("⏸ Market closed — showing historical data. Click **Scan Now** to run manually.")


# ================================
# RUN SCAN
# ================================
do_scan = (market_open or manual_scan) and not st.session_state.trading_locked and selected_symbols

if do_scan:
    cache_invalidate_expired()
    scan_results, errors = [], []
    signals_found = 0
    total = len(selected_symbols)
    progress_bar = st.progress(0, text="Initialising scan…")
    cache_snap = snapshot_cache()
    all_data, all_15m, all_1h = [], {}, {}
    done = 0
    BATCH = 20

    for i in range(0, total, BATCH):
        batch = selected_symbols[i:i+BATCH]
        with ThreadPoolExecutor(max_workers=min(10, len(batch))) as ex:
            futures = {ex.submit(fetch, s, "5m", "5d", True, cache_snap): ("5m", s) for s in batch}
            if use_mtf:
                futures.update({ex.submit(fetch, s, "15m", "5d", True, cache_snap): ("15m", s) for s in batch})
            if use_3tf:
                futures.update({ex.submit(fetch, s, "1h", "5d", True, cache_snap): ("1h", s) for s in batch})
            for f in as_completed(futures):
                tf, sym = futures[f]
                try: result = f.result()
                except Exception as exc: result = (sym, None, str(exc), None)
                _apply_cache_write(result)
                sym_r, df_r, err_r = result[0], result[1], result[2]
                if tf == "5m":
                    all_data.append((sym_r, df_r, err_r)); done += 1
                    progress_bar.progress(min(done/total, 1.0), text=f"Fetching {done}/{total}…")
                elif tf == "15m" and df_r is not None: all_15m[sym] = df_r
                elif tf == "1h"  and df_r is not None: all_1h[sym] = df_r

    progress_bar.empty()

    for symbol, df, err in all_data:
        if err or df is None:
            errors.append({"Symbol": symbol, "Error": err or "No data"})
            scan_results.append({
                "Symbol":symbol, "Signal":"❌ Error", "Score":0.0,
                "Price":"—","ORB High":"—","ORB Low":"—","ATR":"—",
                "Vol Ratio":"—","RSI":"—","Gap %":"—","MTF":"—","3TF":"—",
                "Regime":"—","Reason": err or "Fetch failed",
            })
            continue

        df15 = all_15m.get(symbol); df1h = all_1h.get(symbol)

        # ALWAYS compute all metrics
        metrics = compute_symbol_metrics(df, df15, df1h)

        # Format for display — never show —
        orb_h_str = f"{metrics['orb_high']:.2f}" if metrics['orb_high'] is not None else "N/A"
        orb_l_str = f"{metrics['orb_low']:.2f}"  if metrics['orb_low']  is not None else "N/A"
        atr_str   = f"{metrics['atr']:.2f}"       if metrics['atr']      is not None else "0.00"
        vol_str   = f"{metrics['vol_ratio']:.2f}x" if metrics['vol_ratio'] is not None else "0.00x"
        rsi_str   = f"{metrics['rsi']:.1f}"       if metrics['rsi']      is not None else "50.0"
        gap_str   = f"{metrics['gap_pct']:+.2f}%" if metrics['gap_pct']  is not None else "0.00%"
        mtf_str   = "✅" if metrics['mtf_ok'] is True else ("❌" if metrics['mtf_ok'] is False else "N/A")
        tf3_str   = "✅" if metrics['tf3_ok'] is True else ("❌" if metrics['tf3_ok'] is False else "N/A")
        regime_str = metrics.get("regime", "Unknown")
        price_str  = f"{metrics['last_price']:.2f}" if metrics['last_price'] else "—"

        # If active trade — manage and show
        if symbol in st.session_state.active_trades:
            manage_trade(symbol, df)
            trade = st.session_state.active_trades.get(symbol)
            if trade:
                cur_price = float(df["Close"].iloc[-1])
                unreal = ((cur_price-trade["entry"])*trade["qty_remaining"] if trade["type"]=="BUY"
                          else (trade["entry"]-cur_price)*trade["qty_remaining"])
                scan_results.append({
                    "Symbol":symbol, "Signal":f"🔵 {trade['type']} (Active)",
                    "Score":trade.get("score",0), "Price":price_str,
                    "ORB High":orb_h_str, "ORB Low":orb_l_str, "ATR":atr_str,
                    "Vol Ratio":vol_str, "RSI":rsi_str, "Gap %":gap_str,
                    "MTF":mtf_str, "3TF":tf3_str, "Regime":regime_str,
                    "Reason":f"Unrealised ₹{unreal:+,.2f} | SL {trade['sl']}",
                })
            continue

        # Compute signal label ALWAYS (shows strength even if no trade entered)
        passes, fail_reason = passes_entry_filters(df, metrics, df15, df1h)
        label, score_5, sig_css = compute_signal_label(metrics, passes, fail_reason)

        signal_meta = {
            "label": label, "score_5": score_5,
            "vol_ratio": metrics.get("vol_ratio"), "rsi": metrics.get("rsi"),
            "regime": regime_str,
        }

        vix = st.session_state.vix_value or 0
        vix_factor = 0.5 if (use_vix_sizing and vix > 20) else 1.0

        if passes and is_new_breakout(symbol, metrics["direction"], metrics["orb_high"] if metrics["direction"]=="BUY" else metrics["orb_low"]):
            if len(st.session_state.active_trades) < max_trades:
                df_ind = add_indicators(df)
                sl = compute_sl(df_ind, metrics["direction"], metrics["last_price"],
                                metrics["orb_low"], metrics["orb_high"])
                enter_trade(symbol, metrics["direction"], metrics["last_price"], sl,
                            metrics["atr"] or 1, vix_factor, signal_meta)
                signals_found += 1
                scan_results.append({
                    "Symbol":symbol, "Signal":label, "Score":score_5,
                    "Price":price_str, "ORB High":orb_h_str, "ORB Low":orb_l_str,
                    "ATR":atr_str, "Vol Ratio":vol_str, "RSI":rsi_str, "Gap %":gap_str,
                    "MTF":mtf_str, "3TF":tf3_str, "Regime":regime_str,
                    "Reason":f"✅ Entered @ {metrics['last_price']} | SL {sl}",
                })
                continue
            else:
                st.session_state.signal_state[symbol]["fired"] = False
                scan_results.append({
                    "Symbol":symbol, "Signal":f"{label} (Max Trades)", "Score":score_5,
                    "Price":price_str, "ORB High":orb_h_str, "ORB Low":orb_l_str,
                    "ATR":atr_str, "Vol Ratio":vol_str, "RSI":rsi_str, "Gap %":gap_str,
                    "MTF":mtf_str, "3TF":tf3_str, "Regime":regime_str,
                    "Reason":"Max concurrent trades reached",
                })
                continue

        # No entry — but still show computed values + signal strength
        scan_results.append({
            "Symbol":symbol, "Signal":label, "Score":score_5,
            "Price":price_str, "ORB High":orb_h_str, "ORB Low":orb_l_str,
            "ATR":atr_str, "Vol Ratio":vol_str, "RSI":rsi_str, "Gap %":gap_str,
            "MTF":mtf_str, "3TF":tf3_str, "Regime":regime_str,
            "Reason": fail_reason if not passes else "Signal generated",
        })

    st.session_state.scan_results   = scan_results
    st.session_state.last_scan_time = datetime.now().strftime("%H:%M:%S")
    st.session_state.error_log      = errors
    st.session_state.equity.append({"time": datetime.now(), "capital": st.session_state.capital})
    save_session()

    if signals_found > st.session_state.last_signal_count:
        st.components.v1.html(f"<script>checkAndBeep({signals_found});</script>", height=0)
    st.session_state.last_signal_count = signals_found

    if signals_found > 0:
        st.success(f"✅ {signals_found} new signal(s) fired | {sl_strategy} | 3TF: {'On' if use_3tf else 'Off'}")
    else:
        st.info(f"ℹ️ {len(selected_symbols)} symbols scanned — no new entries. {len(errors)} error(s).")

elif not selected_symbols:
    st.error("⚠️ No symbols selected.")


# ================================
# MARKET CONTEXT BAR
# ================================
nifty_chg = mkt_ctx["nifty_change"]
vix_val   = mkt_ctx["vix"]
nifty_cls = "nifty-green" if nifty_chg >= 0 else "nifty-red"
nifty_sym = "▲" if nifty_chg >= 0 else "▼"
nifty_col = "#22c55e" if nifty_chg >= 0 else "#ef4444"
vix_badge_cls = "vix-low" if vix_val <= 15 else ("vix-mid" if vix_val <= 20 else "vix-high")
vix_icon = "🟢" if vix_val <= 15 else ("🟡" if vix_val <= 20 else "⚠️")

st.markdown(f"""
<div class="ctx-bar">
  <span>🏦 <b>Nifty 50:</b> <span style="color:{nifty_col};font-weight:700">{nifty_sym} {abs(nifty_chg):.1f} pts ({mkt_ctx["nifty_price"]:.0f})</span></span>
  <span class="{vix_badge_cls}">{vix_icon} VIX {vix_val:.1f}</span>
  {'<span style="color:#fbbf24;font-weight:700">⚠️ VIX>20 → Size ÷2</span>' if (use_vix_sizing and vix_val>20) else ''}
  {'<span style="color:#ef4444;font-weight:700">🚫 Nifty RED → BUY filtered</span>' if (use_nifty_filter and nifty_chg<0) else ''}
  <span style="color:var(--txt-sub);font-size:.82rem">Daily P&L: <span class="{pnl_cls(st.session_state.daily_pnl)}" style="font-weight:700">₹{st.session_state.daily_pnl:+,.0f}</span></span>
  <span style="color:var(--txt-sub);font-size:.82rem">SL: <b>{sl_strategy}</b></span>
  <span style="color:var(--txt-sub);font-size:.82rem">Last scan: <b>{st.session_state.last_scan_time or "—"}</b></span>
</div>
""", unsafe_allow_html=True)


# ================================
# METRICS ROW
# ================================
st.divider()
total_closed_pnl = sum(t["PnL (₹)"] for t in st.session_state.closed_trades)
win_trades = [t for t in st.session_state.closed_trades if t["PnL (₹)"] > 0]
win_rate   = (len(win_trades)/len(st.session_state.closed_trades)*100) if st.session_state.closed_trades else 0
net_change = st.session_state.capital - st.session_state.get("initial_capital", 100_000)

# Portfolio P&L
port_pnl = 0.0
for sym, holding in st.session_state.portfolio.items():
    cached = cache_get(sym, "5m")
    if cached is not None and not cached.empty:
        cur = float(cached["Close"].iloc[-1])
        port_pnl += (cur - holding["avg_cost"]) * holding["qty"]

m1,m2,m3,m4,m5,m6,m7,m8 = st.columns(8)
nc_cls  = "normal" if net_change == 0 else ("+" if net_change > 0 else "")
dpnl_delta = f"₹{st.session_state.daily_pnl:+,.0f}"
m1.metric("💼 Capital",        f"₹{st.session_state.capital:,.0f}", f"₹{net_change:+,.0f}")
m2.metric("📈 Realised P&L",   f"₹{total_closed_pnl:+,.0f}")
m3.metric("📅 Daily P&L",      f"₹{st.session_state.daily_pnl:+,.0f}")
m4.metric("📊 Portfolio P&L",  f"₹{port_pnl:+,.0f}")
m5.metric("🔓 Active Trades",  len(st.session_state.active_trades), f"/ {max_trades}")
m6.metric("📝 Closed Trades",  len(st.session_state.closed_trades))
m7.metric("🏆 Win Rate",       f"{win_rate:.1f}%")
m8.metric("💼 Holdings",       len(st.session_state.portfolio))


# ================================
# TABS
# ================================
tab1,tab2,tab3,tab4,tab5,tab6,tab7,tab8,tab9,tab10 = st.tabs([
    "🔍 Scan Results","📊 Active Trades","📁 Portfolio","📜 Closed Trades",
    "📈 Equity Curve","📊 Perf Stats","🗺️ Sector Map","⚗️ Backtester",
    "🎲 Monte Carlo","⚠️ Error Log"
])


# ── TAB 1: SCAN RESULTS ──
with tab1:
    if st.session_state.scan_results:
        df_scan = pd.DataFrame(st.session_state.scan_results)

        f1,f2,f3,f4 = st.columns(4)
        with f1:
            sig_filter = st.selectbox("Filter Signal", ["All","Strong Buy","Buy","Weak Buy","Neutral",
                                                         "Sell","Strong Sell","Active","Error"])
        with f2:
            sort_col = st.selectbox("Sort By", ["Symbol","Score","Price","Vol Ratio","RSI","ATR"])
        with f3:
            sort_asc = st.radio("Order",["↓ Desc","↑ Asc"], horizontal=True) == "↑ Asc"
        with f4:
            min_score = st.slider("Min Score", 0.0, 5.0, 0.0, 0.5)

        if sig_filter != "All":
            df_scan = df_scan[df_scan["Signal"].str.contains(sig_filter, case=False, na=False)]
        if min_score > 0:
            df_scan = df_scan[pd.to_numeric(df_scan["Score"], errors="coerce").fillna(0) >= min_score]
        try:
            df_scan = df_scan.sort_values(sort_col, ascending=sort_asc)
        except Exception: pass

        st.caption(f"Showing **{len(df_scan)}** of **{len(st.session_state.scan_results)}** symbols | All values computed")

        # Color-code the dataframe
        def style_scan_row(row):
            styles = [""] * len(row)
            sig = str(row.get("Signal",""))
            if "Strong Buy" in sig:  bg = "background-color:rgba(34,197,94,.12)"
            elif "Buy" in sig and "Avoid" not in sig: bg = "background-color:rgba(34,197,94,.06)"
            elif "Strong Sell" in sig: bg = "background-color:rgba(239,68,68,.12)"
            elif "Sell" in sig:       bg = "background-color:rgba(239,68,68,.06)"
            elif "Active" in sig:     bg = "background-color:rgba(99,102,241,.1)"
            else:                     bg = ""
            return [bg] * len(row)

        styled_df = df_scan.style.apply(style_scan_row, axis=1)
        st.dataframe(styled_df, use_container_width=True, hide_index=True)

        # Inline chart viewer
        st.markdown("---")
        st.markdown("##### 📈 Chart Viewer")
        chart_syms = [r["Symbol"].replace("⚠️","").strip() for r in st.session_state.scan_results if r.get("Price") not in ("—",None)]
        if chart_syms:
            cc1, cc2 = st.columns([3,1])
            with cc1: chart_sym = st.selectbox("Symbol", chart_syms, key="chart_sym_sel")
            with cc2: load_chart = st.button("📊 Load Chart", key="load_chart_btn", type="primary")
            if load_chart:
                df_chart = cache_get(chart_sym, "5m")
                if df_chart is None:
                    _, df_chart, _, cw = fetch(chart_sym, "5m", "5d", use_cache=False, _cache_snapshot={})
                    if cw: key_c, entry_c = cw; st.session_state.fetch_cache[key_c] = entry_c
                if df_chart is not None:
                    df_chart = add_indicators(df_chart)
                    orb_df_c, _ = get_orb_range(df_chart)
                    orb_h = float(orb_df_c["High"].max()) if not orb_df_c.empty else None
                    orb_l = float(orb_df_c["Low"].min())  if not orb_df_c.empty else None
                    fig_c = go.Figure()
                    fig_c.add_trace(go.Candlestick(x=df_chart.index, open=df_chart["Open"],
                        high=df_chart["High"], low=df_chart["Low"], close=df_chart["Close"],
                        name="OHLC", increasing_line_color="#22c55e", decreasing_line_color="#ef4444"))
                    fig_c.add_trace(go.Scatter(x=df_chart.index, y=df_chart["EMA"], mode="lines",
                        name=f"EMA{ema_period}", line=dict(color="#6366f1",width=1.5,dash="dot")))
                    if "ST_val" in df_chart.columns:
                        fig_c.add_trace(go.Scatter(x=df_chart.index, y=df_chart["ST_val"], mode="lines",
                            name="Supertrend", line=dict(color="#f59e0b",width=1.5)))
                    if orb_h: fig_c.add_hline(y=orb_h, line_dash="dash", line_color="#22c55e",
                                               annotation_text=f"ORB High {orb_h:.2f}", annotation_position="top right")
                    if orb_l: fig_c.add_hline(y=orb_l, line_dash="dash", line_color="#ef4444",
                                               annotation_text=f"ORB Low {orb_l:.2f}", annotation_position="bottom right")
                    fig_c.update_layout(title=f"{chart_sym} — 5m | ORB | EMA | Supertrend",
                        template=plotly_tpl, height=500, xaxis_rangeslider_visible=False,
                        margin=dict(l=10,r=10,t=50,b=10))
                    st.plotly_chart(fig_c, use_container_width=True)

                    r1, r2 = st.columns(2)
                    with r1:
                        fig_rsi = go.Figure()
                        fig_rsi.add_trace(go.Scatter(x=df_chart.index, y=df_chart["RSI"], mode="lines",
                            name="RSI", line=dict(color="#a855f7")))
                        fig_rsi.add_hline(y=70, line_dash="dot", line_color="#ef4444", annotation_text="70")
                        fig_rsi.add_hline(y=50, line_dash="dot", line_color="#64748b", annotation_text="50")
                        fig_rsi.add_hline(y=30, line_dash="dot", line_color="#22c55e", annotation_text="30")
                        fig_rsi.update_layout(title="RSI", template=plotly_tpl, height=220, margin=dict(l=10,r=10,t=30,b=10))
                        st.plotly_chart(fig_rsi, use_container_width=True)
                    with r2:
                        fig_macd = go.Figure()
                        colors_macd = ["#22c55e" if v >= 0 else "#ef4444" for v in df_chart["MACD_hist"].fillna(0)]
                        fig_macd.add_trace(go.Bar(x=df_chart.index, y=df_chart["MACD_hist"], name="MACD Hist", marker_color=colors_macd))
                        fig_macd.add_trace(go.Scatter(x=df_chart.index, y=df_chart["MACD"], mode="lines", name="MACD", line=dict(color="#6366f1")))
                        fig_macd.add_trace(go.Scatter(x=df_chart.index, y=df_chart["MACD_sig"], mode="lines", name="Signal", line=dict(color="#f59e0b")))
                        fig_macd.update_layout(title="MACD", template=plotly_tpl, height=220, margin=dict(l=10,r=10,t=30,b=10))
                        st.plotly_chart(fig_macd, use_container_width=True)
    else:
        st.info("Run a scan to see results.")


# ── TAB 2: ACTIVE TRADES ──
with tab2:
    if st.session_state.active_trades:
        rows = []
        for sym, t in st.session_state.active_trades.items():
            # Fetch current price from cache
            cached_df = cache_get(sym, "5m")
            cur_price = float(cached_df["Close"].iloc[-1]) if cached_df is not None else t["entry"]
            unreal = (cur_price-t["entry"])*t["qty_remaining"] if t["type"]=="BUY" else (t["entry"]-cur_price)*t["qty_remaining"]
            rr = abs(t["target"]-t["entry"])/abs(t["entry"]-t["sl"]) if abs(t["entry"]-t["sl"])>0 else 0
            rows.append({
                "Symbol":sym,"Type":t["type"],"Entry":t["entry"],
                "Current":round(cur_price,2),"SL":t["sl"],"Target":t["target"],
                "Qty":t.get("qty_remaining",t["qty"]),
                "Unrealised P&L":round(unreal,2),
                "P&L %":round(unreal/(t["entry"]*t.get("qty_remaining",t["qty"]))*100,2) if t["entry"]>0 else 0,
                "Score":t.get("score",0),"Signal":t.get("label","—"),
                "R:R":f"1:{rr:.1f}","SL Strategy":t.get("sl_strategy","—"),
                "Entry Time":t.get("entry_time","—"),
            })
        df_active = pd.DataFrame(rows)

        def style_active(row):
            pnl = row.get("Unrealised P&L", 0)
            if pnl > 0:   return ["background-color:rgba(34,197,94,.08)"]*len(row)
            elif pnl < 0: return ["background-color:rgba(239,68,68,.08)"]*len(row)
            return [""]*len(row)

        st.dataframe(df_active.style.apply(style_active, axis=1), use_container_width=True, hide_index=True)

        total_unreal = sum(r["Unrealised P&L"] for r in rows)
        st.markdown(f'Total Unrealised P&L: {fmt_pnl(total_unreal)}', unsafe_allow_html=True)

        st.markdown("##### Manual Exit")
        ec1, ec2 = st.columns([3,1])
        with ec1: exit_sym = st.selectbox("Select symbol", list(st.session_state.active_trades.keys()))
        with ec2:
            if st.button(f"🚪 Exit {exit_sym}", type="primary"):
                t = st.session_state.active_trades[exit_sym]
                cached_df2 = cache_get(exit_sym, "5m")
                ep = float(cached_df2["Close"].iloc[-1]) if cached_df2 is not None else t["entry"]
                pnl_m = (ep-t["entry"])*t.get("qty_remaining",t["qty"]) if t["type"]=="BUY" else (t["entry"]-ep)*t.get("qty_remaining",t["qty"])
                exit_trade(exit_sym, ep, pnl_m, "Manual Exit")
                save_session(); st.rerun()
    else:
        st.info("No active trades.")


# ── TAB 3: PORTFOLIO MANAGER ──
with tab3:
    st.markdown("### 📁 Portfolio Manager")
    st.caption("Track your actual holdings — buy/sell shares and monitor real-time P&L")

    # Add holding
    with st.expander("➕ Add / Update Holding", expanded=True):
        pc1,pc2,pc3,pc4 = st.columns(4)
        with pc1:
            port_sym_raw = st.text_input("Symbol (e.g. RELIANCE or RELIANCE.NS)", key="port_sym_input")
        with pc2:
            port_qty = st.number_input("Quantity (shares)", min_value=1, max_value=100000, value=10, key="port_qty_input")
        with pc3:
            port_cost = st.number_input("Avg Buy Price (₹)", min_value=0.01, value=100.0, step=0.01, key="port_cost_input")
        with pc4:
            port_sector = st.selectbox("Sector", ["Auto","Bank","FMCG","IT","Metals","Energy","Pharma","Infra","Other"], key="port_sector_input")

        pp1, pp2 = st.columns(2)
        with pp1:
            if st.button("📥 Add / Update Holding", type="primary", use_container_width=True):
                if port_sym_raw.strip():
                    sym_clean = port_sym_raw.strip().upper()
                    if not sym_clean.endswith((".NS",".BO")): sym_clean += ".NS"
                    if sym_clean in st.session_state.portfolio:
                        # Weighted average if updating
                        old = st.session_state.portfolio[sym_clean]
                        old_qty, old_cost = old["qty"], old["avg_cost"]
                        new_qty = old_qty + port_qty
                        new_cost = (old_qty*old_cost + port_qty*port_cost) / new_qty
                        st.session_state.portfolio[sym_clean] = {
                            "qty": new_qty, "avg_cost": round(new_cost,4),
                            "sector": port_sector, "added_time": datetime.now().strftime("%Y-%m-%d %H:%M")
                        }
                        st.success(f"Updated {sym_clean}: {new_qty} shares @ avg ₹{new_cost:.2f}")
                    else:
                        st.session_state.portfolio[sym_clean] = {
                            "qty": port_qty, "avg_cost": port_cost,
                            "sector": port_sector, "added_time": datetime.now().strftime("%Y-%m-%d %H:%M")
                        }
                        st.success(f"Added {sym_clean}: {port_qty} shares @ ₹{port_cost:.2f}")
                    save_portfolio(st.session_state.portfolio)
                    st.rerun()
        with pp2:
            if st.button("📤 Sell / Remove Holding", use_container_width=True):
                if port_sym_raw.strip():
                    sym_clean = port_sym_raw.strip().upper()
                    if not sym_clean.endswith((".NS",".BO")): sym_clean += ".NS"
                    if sym_clean in st.session_state.portfolio:
                        old = st.session_state.portfolio[sym_clean]
                        if port_qty >= old["qty"]:
                            del st.session_state.portfolio[sym_clean]
                            st.success(f"Removed {sym_clean} completely")
                        else:
                            st.session_state.portfolio[sym_clean]["qty"] = old["qty"] - port_qty
                            st.success(f"Sold {port_qty} shares of {sym_clean}")
                        save_portfolio(st.session_state.portfolio)
                        st.rerun()
                    else:
                        st.error(f"{sym_clean} not in portfolio")

    # Display portfolio
    if st.session_state.portfolio:
        st.markdown("#### 📊 Holdings")

        port_rows = []
        total_invested = 0.0
        total_current  = 0.0

        for sym, holding in st.session_state.portfolio.items():
            # Try to get current price
            cur_price = None
            cached_df = cache_get(sym, "5m")
            if cached_df is not None and not cached_df.empty:
                cur_price = round(float(cached_df["Close"].iloc[-1]), 2)
            if cur_price is None:
                # Try 1d
                cached_1d = cache_get(sym, "1d")
                if cached_1d is not None and not cached_1d.empty:
                    cur_price = round(float(cached_1d["Close"].iloc[-1]), 2)

            avg_cost = holding["avg_cost"]
            qty      = holding["qty"]
            invested = avg_cost * qty
            current  = (cur_price * qty) if cur_price else invested
            pnl_abs  = current - invested
            pnl_pct  = (pnl_abs / invested * 100) if invested > 0 else 0

            total_invested += invested
            total_current  += current

            port_rows.append({
                "Symbol":sym, "Sector":holding.get("sector","—"),
                "Qty":qty, "Avg Cost (₹)":round(avg_cost,2),
                "Current Price":cur_price if cur_price else "Refresh",
                "Invested (₹)":round(invested,2),
                "Current Value (₹)":round(current,2) if cur_price else "—",
                "P&L (₹)":round(pnl_abs,2) if cur_price else "—",
                "P&L %":round(pnl_pct,2) if cur_price else "—",
                "Added":holding.get("added_time","—"),
            })

        total_pnl_port = total_current - total_invested

        # Summary cards
        sc1,sc2,sc3,sc4 = st.columns(4)
        with sc1: st.markdown(f'<div class="stat-box"><div class="val">₹{total_invested:,.0f}</div><div class="lbl">Total Invested</div></div>', unsafe_allow_html=True)
        with sc2: st.markdown(f'<div class="stat-box"><div class="val">₹{total_current:,.0f}</div><div class="lbl">Current Value</div></div>', unsafe_allow_html=True)
        pnl_color = "#22c55e" if total_pnl_port >= 0 else "#ef4444"
        with sc3: st.markdown(f'<div class="stat-box"><div class="val" style="color:{pnl_color}">₹{total_pnl_port:+,.0f}</div><div class="lbl">Total P&L</div></div>', unsafe_allow_html=True)
        pnl_pct_tot = (total_pnl_port/total_invested*100) if total_invested > 0 else 0
        with sc4: st.markdown(f'<div class="stat-box"><div class="val" style="color:{pnl_color}">{pnl_pct_tot:+.2f}%</div><div class="lbl">Portfolio Return</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        df_port = pd.DataFrame(port_rows)

        def style_portfolio(row):
            pnl_val = row.get("P&L (₹)", 0)
            try: pnl_val = float(pnl_val)
            except: return [""]*len(row)
            if pnl_val > 0:   return ["background-color:rgba(34,197,94,.1)"]*len(row)
            elif pnl_val < 0: return ["background-color:rgba(239,68,68,.1)"]*len(row)
            return [""]*len(row)

        st.dataframe(df_port.style.apply(style_portfolio, axis=1), use_container_width=True, hide_index=True)

        st.markdown(f'**Portfolio P&L:** {fmt_pnl(total_pnl_port)} &nbsp;|&nbsp; **Return:** <span class="{pnl_cls(pnl_pct_tot)}">{pnl_pct_tot:+.2f}%</span>', unsafe_allow_html=True)

        # Portfolio chart
        if len(port_rows) > 1:
            fig_pie = go.Figure(go.Pie(
                labels=[r["Symbol"].replace(".NS","") for r in port_rows],
                values=[r["Invested (₹)"] for r in port_rows],
                hole=0.5, textinfo="label+percent",
                marker=dict(colors=px.colors.qualitative.Set3)
            ))
            fig_pie.update_layout(title="Portfolio Allocation", template=plotly_tpl, height=350, margin=dict(l=10,r=10,t=50,b=10))
            st.plotly_chart(fig_pie, use_container_width=True)

        # Refresh portfolio prices button
        if st.button("🔄 Refresh Portfolio Prices", type="primary"):
            snap = snapshot_cache()
            for sym in list(st.session_state.portfolio.keys()):
                _, df_p, _, cw_p = fetch(sym, "5m", "5d", use_cache=False, _cache_snapshot={})
                if cw_p:
                    k_p, e_p = cw_p; st.session_state.fetch_cache[k_p] = e_p
            st.rerun()

        csv_port = df_port.to_csv(index=False)
        st.download_button("⬇️ Export Portfolio CSV", csv_port,
                           file_name=f"portfolio_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")
    else:
        st.info("No holdings added. Use the form above to add shares to your portfolio.")


# ── TAB 4: CLOSED TRADES ──
with tab4:
    if st.session_state.closed_trades:
        # Fix column name inconsistency
        closed_fixed = []
        for t in st.session_state.closed_trades:
            t2 = dict(t)
            if "Symbol_" in t2:
                t2["Symbol"] = t2.pop("Symbol_")
            closed_fixed.append(t2)

        closed_df = pd.DataFrame(closed_fixed)
        if "Symbol" not in closed_df.columns and "Symbol_" in closed_df.columns:
            closed_df.rename(columns={"Symbol_":"Symbol"}, inplace=True)

        total_pnl = closed_df["PnL (₹)"].sum()
        ta, tb, tc, td = st.columns(4)
        ta.metric("Total P&L",    f"₹{total_pnl:+,.2f}")
        tb.metric("Total Trades", len(closed_df))
        tc.metric("Win Rate",     f"{win_rate:.1f}%")
        td.metric("Wins / Losses", f"{len(win_trades)} / {len(st.session_state.closed_trades)-len(win_trades)}")

        def style_closed(row):
            pnl_val = row.get("PnL (₹)", 0)
            if pnl_val > 0:   return ["background-color:rgba(34,197,94,.1)"]*len(row)
            elif pnl_val < 0: return ["background-color:rgba(239,68,68,.1)"]*len(row)
            return [""]*len(row)

        st.dataframe(closed_df.style.apply(style_closed, axis=1), use_container_width=True, hide_index=True)

        # Trade notes
        st.markdown("##### 📓 Trade Notes")
        note_idx = st.selectbox("Select trade", list(range(len(st.session_state.closed_trades))))
        note_txt = st.text_area("Note", value=st.session_state.closed_trades[note_idx].get("Note",""), height=70)
        if st.button("💾 Save Note"):
            st.session_state.closed_trades[note_idx]["Note"] = note_txt
            save_session(); st.success("Note saved!"); st.rerun()

        da, db = st.columns(2)
        with da:
            st.download_button("⬇️ Export CSV", closed_df.to_csv(index=False),
                               file_name=f"trades_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", mime="text/csv")
        with db:
            st.download_button("📓 Export JSON", json.dumps(st.session_state.closed_trades, indent=2),
                               file_name=f"journal_{datetime.now().strftime('%Y%m%d_%H%M')}.json", mime="application/json")
    else:
        st.info("No closed trades yet.")


# ── TAB 5: EQUITY CURVE ──
with tab5:
    equity_df = pd.DataFrame(st.session_state.equity)
    if not equity_df.empty:
        initial = st.session_state.get("initial_capital", 100_000)
        fig_eq = go.Figure()
        fig_eq.add_trace(go.Scatter(x=equity_df["time"], y=equity_df["capital"],
            mode="lines+markers", line=dict(color="#6366f1",width=2.5), marker=dict(size=4),
            name="Capital", fill="tozeroy", fillcolor="rgba(99,102,241,.08)"))
        fig_eq.add_hline(y=initial, line_dash="dash", line_color="#64748b",
                          annotation_text=f"Initial ₹{initial:,.0f}")
        fig_eq.update_layout(title="Equity Curve", xaxis_title="Time", yaxis_title="Capital (₹)",
            template=plotly_tpl, height=400, margin=dict(l=10,r=10,t=40,b=10))
        st.plotly_chart(fig_eq, use_container_width=True)
        peak = equity_df["capital"].cummax()
        dd   = ((equity_df["capital"]-peak)/peak)*100
        fig_dd = go.Figure()
        fig_dd.add_trace(go.Scatter(x=equity_df["time"], y=dd, mode="lines", fill="tozeroy",
            line=dict(color="#ef4444",width=1.5), fillcolor="rgba(239,68,68,.1)", name="Drawdown %"))
        fig_dd.update_layout(title="Drawdown %", template=plotly_tpl, height=220, margin=dict(l=10,r=10,t=40,b=10))
        st.plotly_chart(fig_dd, use_container_width=True)
    else:
        st.info("No equity data yet. Run a scan.")


# ── TAB 6: PERF STATS ──
with tab6:
    if st.session_state.closed_trades:
        df_p = pd.DataFrame([{**t, "Symbol": t.get("Symbol_", t.get("Symbol","—"))} for t in st.session_state.closed_trades])
        wins  = df_p[df_p["PnL (₹)"] > 0]
        loses = df_p[df_p["PnL (₹)"] <= 0]
        avg_win  = wins["PnL (₹)"].mean()  if len(wins)>0  else 0
        avg_loss = loses["PnL (₹)"].mean() if len(loses)>0 else 0
        pf = abs(wins["PnL (₹)"].sum()/loses["PnL (₹)"].sum()) if loses["PnL (₹)"].sum()!=0 else float("inf")

        ps1,ps2,ps3 = st.columns(3)
        with ps1: st.markdown(f'<div class="stat-box"><div class="val" style="color:#22c55e">₹{avg_win:,.0f}</div><div class="lbl">Avg Win</div></div>', unsafe_allow_html=True)
        with ps2: st.markdown(f'<div class="stat-box"><div class="val" style="color:#ef4444">₹{avg_loss:,.0f}</div><div class="lbl">Avg Loss</div></div>', unsafe_allow_html=True)
        with ps3: st.markdown(f'<div class="stat-box"><div class="val">{pf:.2f}x</div><div class="lbl">Profit Factor</div></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        df_p["Hour"] = pd.to_datetime(df_p.get("Entry Time",""), format="%H:%M:%S", errors="coerce").dt.hour
        hour_pnl = df_p.groupby("Hour")["PnL (₹)"].sum()
        if not hour_pnl.empty:
            fig_h = px.bar(x=[f"{h}:00" for h in hour_pnl.index], y=hour_pnl.values,
                           color=hour_pnl.values, color_continuous_scale=["#ef4444","#fbbf24","#22c55e"],
                           labels={"x":"Hour","y":"P&L (₹)"}, title="P&L by Hour")
            fig_h.update_layout(template=plotly_tpl, height=280, showlegend=False,
                                coloraxis_showscale=False, margin=dict(l=10,r=10,t=40,b=10))
            st.plotly_chart(fig_h, use_container_width=True)

        df_p2 = df_p[pd.to_numeric(df_p.get("Score",""), errors="coerce").notna()].copy()
        df_p2["Score"] = pd.to_numeric(df_p2["Score"])
        if not df_p2.empty:
            fig_s = px.scatter(df_p2, x="Score", y="PnL (₹)", color="Type",
                               color_discrete_map={"BUY":"#22c55e","SELL":"#ef4444"},
                               title="Signal Score vs P&L", hover_data=["Symbol"])
            fig_s.update_layout(template=plotly_tpl, height=300, margin=dict(l=10,r=10,t=40,b=10))
            st.plotly_chart(fig_s, use_container_width=True)
    else:
        st.info("No closed trades yet.")


# ── TAB 7: SECTOR MAP ──
with tab7:
    st.markdown("### 🗺️ Sector Signal Heatmap")
    if st.session_state.scan_results:
        sector_counts = {}
        for row in st.session_state.scan_results:
            sym = row["Symbol"].replace("⚠️","").strip()
            sector = SECTOR_MAP.get(sym, "Other")
            sig = str(row.get("Signal",""))
            if sector not in sector_counts:
                sector_counts[sector] = {"Strong Buy":0,"Buy":0,"Neutral":0,"Sell":0,"Strong Sell":0}
            if "Strong Buy" in sig:   sector_counts[sector]["Strong Buy"]  += 1
            elif "Buy" in sig and "Avoid" not in sig: sector_counts[sector]["Buy"] += 1
            elif "Strong Sell" in sig: sector_counts[sector]["Strong Sell"] += 1
            elif "Sell" in sig:       sector_counts[sector]["Sell"]  += 1
            else:                     sector_counts[sector]["Neutral"] += 1

        heat_rows = [{"Sector":s, **v, "Total Signals":sum(v.values())} for s,v in sector_counts.items()]
        heat_df = pd.DataFrame(heat_rows).sort_values("Total Signals", ascending=False)
        st.dataframe(heat_df, use_container_width=True, hide_index=True)

        bull_sectors = heat_df[heat_df["Strong Buy"] > 0]
        if not bull_sectors.empty:
            fig_tree = px.treemap(bull_sectors.assign(parent="Sectors"),
                                  path=["parent","Sector"], values="Total Signals",
                                  color="Strong Buy", color_continuous_scale=["#1a2035","#22c55e"],
                                  title="Bullish Signal Distribution by Sector")
            fig_tree.update_layout(height=380, margin=dict(l=10,r=10,t=50,b=10))
            st.plotly_chart(fig_tree, use_container_width=True)
    else:
        st.info("Run a scan first.")


# ── TAB 8: BACKTESTER ──
with tab8:
    st.markdown("### ⚗️ Walk-Forward Backtester")
    bc1,bc2,bc3,bc4,bc5 = st.columns(5)
    with bc1: bt_symbols = st.multiselect("Symbols", selected_symbols, default=selected_symbols[:3] if len(selected_symbols)>=3 else selected_symbols)
    with bc2: bt_orb_min = st.number_input("ORB Min", 5, 60, int(orb_minutes), key="bt_orb")
    with bc3: bt_atr_tgt = st.number_input("ATR Target Mult", 1.0, 5.0, 2.0, 0.5, key="bt_atr")
    with bc4: wf_train   = st.number_input("Train Days", 1, 20, 3)
    with bc5: wf_test    = st.number_input("Test Days",  1, 10, 1)

    def run_orb_bt(df_full, days_list, orb_m, atr_m):
        trades = []; df_full = add_indicators(df_full.copy()); df_full.index = pd.to_datetime(df_full.index)
        for day in days_list:
            grp = df_full[df_full.index.date == day].copy()
            if len(grp) < 5: continue
            grp["_time"] = grp.index.time
            cutoff_t = (datetime.combine(day, dtime(9,15))+timedelta(minutes=int(orb_m))).time()
            orb_part = grp[grp["_time"] <= cutoff_t]; rest = grp[grp["_time"] > cutoff_t]
            if len(orb_part) < 2 or len(rest) < 2: continue
            orb_h = float(orb_part["High"].max()); orb_l = float(orb_part["Low"].min())
            in_trade = False; direction = entry_p = sl_p = tgt_p = 0.0
            for idx, row in rest.iterrows():
                close = float(row["Close"]); atr = float(row["ATR"]) if not pd.isna(row.get("ATR",np.nan)) else 0
                if not in_trade:
                    if close > orb_h: direction="BUY";  entry_p=close; sl_p=orb_l; tgt_p=entry_p+atr_m*atr; in_trade=True
                    elif close < orb_l: direction="SELL"; entry_p=close; sl_p=orb_h; tgt_p=entry_p-atr_m*atr; in_trade=True
                else:
                    hit_sl  = (direction=="BUY" and close<=sl_p) or (direction=="SELL" and close>=sl_p)
                    hit_tgt = (direction=="BUY" and close>=tgt_p) or (direction=="SELL" and close<=tgt_p)
                    if hit_sl or hit_tgt:
                        pnl = (close-entry_p) if direction=="BUY" else (entry_p-close)
                        trades.append({"day":str(day),"direction":direction,"entry":round(entry_p,2),
                                       "exit":round(close,2),"pnl":round(pnl,2),"reason":"TGT" if hit_tgt else "SL"})
                        in_trade = False
            if in_trade:
                close = float(rest["Close"].iloc[-1]); pnl = (close-entry_p) if direction=="BUY" else (entry_p-close)
                trades.append({"day":str(day),"direction":direction,"entry":round(entry_p,2),"exit":round(close,2),"pnl":round(pnl,2),"reason":"EOD"})
        return trades

    if st.button("▶️ Run Walk-Forward Backtest", type="primary"):
        with st.spinner("Running…"):
            wf_results = []
            for sym in bt_symbols:
                _, df_bt, err, cw = fetch(sym, "5m", "1mo", use_cache=False, _cache_snapshot={})
                if cw: k2,e2=cw; st.session_state.fetch_cache[k2]=e2
                if err or df_bt is None or len(df_bt) < 20: continue
                df_bt.index = pd.to_datetime(df_bt.index)
                days = sorted(set(df_bt.index.date.tolist()))
                ws = int(wf_train) + int(wf_test)
                for si in range(0, len(days)-ws+1, int(wf_test)):
                    test_days = days[si+int(wf_train): si+ws]
                    if not test_days: continue
                    for t in run_orb_bt(df_bt, test_days, bt_orb_min, bt_atr_tgt):
                        t["symbol"] = sym; wf_results.append(t)
            st.session_state.backtest_results = wf_results

        if wf_results:
            bt_df = pd.DataFrame(wf_results)
            bt_wins = bt_df[bt_df["pnl"]>0]; bt_loss = bt_df[bt_df["pnl"]<=0]
            bt_wr = len(bt_wins)/len(bt_df)*100 if len(bt_df)>0 else 0
            bt_pf = abs(bt_wins["pnl"].sum()/bt_loss["pnl"].sum()) if bt_loss["pnl"].sum()!=0 else float("inf")

            bb1,bb2,bb3,bb4 = st.columns(4)
            pc = "#22c55e" if bt_df["pnl"].sum()>0 else "#ef4444"
            with bb1: st.markdown(f'<div class="stat-box"><div class="val">{len(bt_df)}</div><div class="lbl">OOS Trades</div></div>', unsafe_allow_html=True)
            with bb2: st.markdown(f'<div class="stat-box"><div class="val" style="color:{pc}">₹{bt_df["pnl"].sum():,.1f}</div><div class="lbl">OOS P&L</div></div>', unsafe_allow_html=True)
            with bb3: st.markdown(f'<div class="stat-box"><div class="val">{bt_wr:.1f}%</div><div class="lbl">Win Rate</div></div>', unsafe_allow_html=True)
            with bb4: st.markdown(f'<div class="stat-box"><div class="val">{bt_pf:.2f}x</div><div class="lbl">Profit Factor</div></div>', unsafe_allow_html=True)

            bt_df["Cum PnL"] = bt_df["pnl"].cumsum()
            fig_bt = go.Figure()
            fig_bt.add_trace(go.Scatter(x=list(range(len(bt_df))), y=bt_df["Cum PnL"],
                mode="lines+markers", fill="tozeroy", line=dict(color="#6366f1",width=2.5),
                fillcolor="rgba(99,102,241,.1)"))
            fig_bt.add_hline(y=0, line_dash="dash", line_color="#64748b")
            fig_bt.update_layout(title="Walk-Forward OOS Cumulative P&L", template=plotly_tpl, height=320, margin=dict(l=10,r=10,t=40,b=10))
            st.plotly_chart(fig_bt, use_container_width=True)
            st.dataframe(bt_df, use_container_width=True, hide_index=True)
        else:
            st.warning("No trades generated.")


# ── TAB 9: MONTE CARLO ──
with tab9:
    st.markdown("### 🎲 Monte Carlo Simulation")
    mc1,mc2,mc3 = st.columns(3)
    with mc1: mc_n_sims = st.number_input("Simulations", 100, 5000, 1000, step=100)
    with mc2: mc_capital = st.number_input("Start Capital (₹)", 10_000, 10_000_000, int(st.session_state.initial_capital), step=10_000)
    with mc3: mc_ruin_thr = st.slider("Ruin Threshold (%)", 10, 90, 30) / 100

    if st.button("▶️ Run Monte Carlo", type="primary"):
        pnl_list = [t["PnL (₹)"] for t in st.session_state.closed_trades]
        if not pnl_list and st.session_state.backtest_results:
            pnl_list = [t.get("pnl",0) for t in st.session_state.backtest_results]
        if len(pnl_list) < 5:
            st.warning("Need at least 5 closed trades or backtest results.")
        else:
            with st.spinner(f"Running {mc_n_sims:,} simulations…"):
                pnl_arr = np.array(pnl_list); n = len(pnl_arr)
                results = []
                rng = np.random.default_rng(42)
                for _ in range(int(mc_n_sims)):
                    shuffled = rng.choice(pnl_arr, size=n, replace=True)
                    equity = mc_capital + np.cumsum(shuffled)
                    peak = np.maximum.accumulate(equity)
                    dd_pct = ((equity-peak)/peak)*100
                    results.append({"final":float(equity[-1]),"max_dd":float(dd_pct.min()),
                                    "ruined":bool(np.any(equity<=mc_capital*(1-mc_ruin_thr)))})
            res_df = pd.DataFrame(results)
            ruin_rate = res_df["ruined"].mean()*100
            final_arr = res_df["final"].values; dd_arr = res_df["max_dd"].values

            mc_a,mc_b,mc_c,mc_d = st.columns(4)
            rr_col = "#ef4444" if ruin_rate>10 else ("#fbbf24" if ruin_rate>5 else "#22c55e")
            with mc_a: st.markdown(f'<div class="stat-box"><div class="val" style="color:{rr_col}">{ruin_rate:.1f}%</div><div class="lbl">Risk of Ruin</div></div>', unsafe_allow_html=True)
            with mc_b: st.markdown(f'<div class="stat-box"><div class="val" style="color:#ef4444">{np.percentile(dd_arr,95):.1f}%</div><div class="lbl">95th% Max DD</div></div>', unsafe_allow_html=True)
            with mc_c: st.markdown(f'<div class="stat-box"><div class="val">₹{np.percentile(final_arr,50):,.0f}</div><div class="lbl">Median Outcome</div></div>', unsafe_allow_html=True)
            with mc_d: st.markdown(f'<div class="stat-box"><div class="val">₹{np.percentile(final_arr,5):,.0f}</div><div class="lbl">5th% Worst Case</div></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            fig_mc1 = go.Figure()
            fig_mc1.add_trace(go.Histogram(x=final_arr, nbinsx=50, marker_color="#6366f1", opacity=.8))
            fig_mc1.add_vline(x=mc_capital, line_dash="dash", line_color="#64748b", annotation_text="Start")
            fig_mc1.add_vline(x=float(np.percentile(final_arr,5)), line_dash="dot", line_color="#ef4444", annotation_text="5th%ile")
            fig_mc1.add_vline(x=float(np.percentile(final_arr,50)), line_dash="dot", line_color="#22c55e", annotation_text="Median")
            fig_mc1.update_layout(title=f"Final Capital Distribution ({mc_n_sims:,} sims)", template=plotly_tpl, height=350, margin=dict(l=10,r=10,t=50,b=10))
            st.plotly_chart(fig_mc1, use_container_width=True)

            if ruin_rate > 10: st.error(f"⚠️ High risk of ruin: {ruin_rate:.1f}%. Reduce position size.")
            elif ruin_rate > 5: st.warning(f"⚡ Moderate ruin risk: {ruin_rate:.1f}%.")
            else: st.success(f"✅ Low ruin risk: {ruin_rate:.1f}%.")


# ── TAB 10: ERROR LOG ──
with tab10:
    if st.session_state.error_log:
        st.dataframe(pd.DataFrame(st.session_state.error_log), use_container_width=True, hide_index=True)
        st.info("**Common causes:** Market closed, wrong suffix (.NS/.BO), Yahoo Finance rate limiting, delistedSymbols.")
        if st.button("🧹 Clear Error Log"):
            st.session_state.error_log = []; st.rerun()
    else:
        st.success("✅ No errors.")

    st.markdown("---")
    st.markdown("##### 🗄️ Cache")
    cache = st.session_state.fetch_cache; now_t = time.time()
    cache_rows = []
    for k, v in list(cache.items()):
        age = int(now_t - v["ts"]); parts = k.rsplit("_",1); itv = parts[-1] if len(parts)==2 else "?"
        ttl = _cache_ttl(itv)
        cache_rows.append({"Key":k,"Age (s)":age,"TTL (s)":ttl,
                           "Rows":len(v["df"]) if v["df"] is not None else 0,
                           "Status":"✅ Fresh" if age<ttl else "⏰ Stale"})
    if cache_rows:
        st.dataframe(pd.DataFrame(cache_rows), use_container_width=True, hide_index=True)
        if st.button("🗑️ Clear All Cache"):
            st.session_state.fetch_cache = {}; st.rerun()
    else:
        st.info("Cache empty.")
