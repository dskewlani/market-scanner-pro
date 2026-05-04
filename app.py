# ================================
# ORB SMART SCANNER — FULL ENHANCED REWRITE v2
# FIX: Robust yfinance fetching — handles MultiIndex, empty data,
#      insufficient bars, market-closed fallback to 5d period,
#      column name normalisation, and timezone-aware indexing.
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
import json
import os
import requests
import traceback

# ================================
# PAGE CONFIG
# ================================
st.set_page_config(
    page_title="ORB Smart Scanner Pro",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🚀"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;600;700;800&display=swap');

    html, body, [class*="css"] { font-family: 'Syne', sans-serif; }
    code, .stCode { font-family: 'JetBrains Mono', monospace !important; }

    .block-container { padding-top: 1rem; }
    .stMetric label { font-size: 0.72rem; color: #6b7280; letter-spacing: 0.06em; text-transform: uppercase; }
    .stMetric value { font-size: 1.5rem; font-weight: 700; }

    div[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
    .stAlert { border-radius: 10px; }

    .signal-badge-buy  { display:inline-block; padding:2px 10px; border-radius:20px; background:#d1fae5; color:#065f46; font-weight:700; font-size:0.82rem; }
    .signal-badge-sell { display:inline-block; padding:2px 10px; border-radius:20px; background:#fee2e2; color:#991b1b; font-weight:700; font-size:0.82rem; }
    .signal-badge-none { display:inline-block; padding:2px 10px; border-radius:20px; background:#f3f4f6; color:#6b7280; font-size:0.82rem; }

    .score-bar { display:inline-block; height:8px; border-radius:4px; background:linear-gradient(90deg,#3b82f6,#10b981); vertical-align:middle; margin-left:6px; }

    .metric-card { background:#fff; border:1px solid #e5e7eb; border-radius:12px; padding:14px 18px; }
    .metric-card-dark { background:#111827; border:1px solid #374151; border-radius:12px; padding:14px 18px; color:#f9fafb; }

    .header-title { font-size:2rem; font-weight:800; letter-spacing:-0.02em; color:#111827; }
    .header-subtitle { font-size:0.85rem; color:#6b7280; margin-top:-8px; }

    div[data-testid="stTabs"] button { font-family:'Syne',sans-serif; font-weight:600; font-size:0.85rem; }

    .stButton>button { border-radius:8px; font-family:'Syne',sans-serif; font-weight:600; }
    .stButton>button[kind="primary"] { background:linear-gradient(135deg,#2563eb,#7c3aed); border:none; color:#fff; }
    .stButton>button[kind="primary"]:hover { background:linear-gradient(135deg,#1d4ed8,#6d28d9); }

    .journal-note { background:#fffbeb; border-left:3px solid #f59e0b; padding:8px 12px; border-radius:0 8px 8px 0; font-size:0.85rem; color:#78350f; }

    .backtest-stat { text-align:center; padding:12px; background:#f8fafc; border-radius:10px; border:1px solid #e2e8f0; }
    .backtest-stat .val { font-size:1.4rem; font-weight:800; color:#1e293b; }
    .backtest-stat .lbl { font-size:0.7rem; color:#64748b; text-transform:uppercase; letter-spacing:0.06em; margin-top:2px; }

    .vix-badge-low    { display:inline-block; padding:3px 10px; border-radius:20px; background:#d1fae5; color:#065f46; font-weight:700; font-size:0.82rem; }
    .vix-badge-mid    { display:inline-block; padding:3px 10px; border-radius:20px; background:#fef3c7; color:#92400e; font-weight:700; font-size:0.82rem; }
    .vix-badge-high   { display:inline-block; padding:3px 10px; border-radius:20px; background:#fee2e2; color:#991b1b; font-weight:700; font-size:0.82rem; }

    .nifty-green { color:#16a34a; font-weight:700; }
    .nifty-red   { color:#dc2626; font-weight:700; }

    .daily-limit-banner { background:#fef2f2; border:2px solid #fca5a5; border-radius:10px; padding:14px 18px; text-align:center; color:#991b1b; font-weight:700; font-size:1rem; }
    .daily-profit-banner{ background:#f0fdf4; border:2px solid #86efac; border-radius:10px; padding:14px 18px; text-align:center; color:#166534; font-weight:700; font-size:1rem; }

    .gap-up-badge   { display:inline-block; padding:2px 8px; border-radius:12px; background:#dbeafe; color:#1e40af; font-size:0.78rem; font-weight:600; }
    .gap-down-badge { display:inline-block; padding:2px 8px; border-radius:12px; background:#fce7f3; color:#9d174d; font-size:0.78rem; font-weight:600; }
</style>
""", unsafe_allow_html=True)

# ================================
# SOUND ALERT JS INJECTION
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
        beep(880, 0,   0.15, 0.4);
        beep(1100, 0.18, 0.15, 0.35);
        beep(1320, 0.36, 0.25, 0.3);
    } catch(e) { console.log('Audio not supported'); }
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
        "AUBANK.NS","BHEL.NS","BSE.NS","CAMS.NS","CANFINHOME.NS",
        "CDSL.NS","CESC.NS","CHAMBLFERT.NS","CROMPTON.NS","CUMMINSIND.NS",
        "DEEPAKNTR.NS","ELGIEQUIP.NS","ESCORTS.NS","FINCABLES.NS","GLENMARK.NS",
        "GNFC.NS","GRINDWELL.NS","GSFC.NS","HFCL.NS","HINDCOPPER.NS",
        "HUDCO.NS","IDEA.NS","IIFL.NS","INDIANB.NS","INDIAMART.NS",
        "KAJARIACER.NS","KPIL.NS","LICHSGFIN.NS","LTTS.NS","MANAPPURAM.NS",
        "MARICO.NS","MCX.NS","METROPOLIS.NS","MOTHERSON.NS","NATIONALUM.NS",
        "NBCC.NS","NLCINDIA.NS","OBEROIRLTY.NS","POLICYBZR.NS","IRCTC.NS",
    ],
    "Bank Nifty": [
        "HDFCBANK.NS","ICICIBANK.NS","KOTAKBANK.NS","AXISBANK.NS","SBIN.NS",
        "INDUSINDBK.NS","BANDHANBNK.NS","FEDERALBNK.NS","IDFCFIRSTB.NS","PNB.NS",
        "BANKBARODA.NS","CANBK.NS","UNIONBANK.NS","INDIANB.NS","IOB.NS",
        "UCO.NS","CENTRALBK.NS","KARURVYSYA.NS","DCBBANK.NS","RBLBANK.NS",
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
        "BALKRISIND.NS","APOLLOTYRE.NS","CEAT.NS","EXIDEIND.NS","TIINDIA.NS",
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
    "LT.NS":"Infra","ULTRACEMCO.NS":"Infra","DLF.NS":"Infra","OBEROIRLTY.NS":"Infra",
}

WATCHLIST_FILE = "orb_watchlist.json"

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
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

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
    except Exception as e:
        st.warning(f"Could not save watchlist: {e}")

saved_watchlist = load_watchlist()

# ================================
# SIDEBAR — ALL SETTINGS
# ================================
with st.sidebar:
    st.markdown("## ⚙️ Scanner Settings")

    st.markdown("### 📋 Symbol Selection")
    preset_choice = st.selectbox("Choose Preset", list(PRESETS.keys()), index=0)

    if preset_choice == "Custom (Enter Below)":
        custom_raw = st.text_area(
            "Enter tickers (one per line or comma-separated)",
            placeholder="RELIANCE\nTCS\nINFY",
            height=100
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

    default_saved = saved_watchlist.get(preset_choice, [])
    if default_saved and all(d in symbols_pool for d in default_saved):
        default_sel = default_saved
    else:
        default_sel = symbols_pool[:15] if len(symbols_pool) > 15 else symbols_pool

    if symbols_pool:
        selected_symbols = st.multiselect(
            f"Select symbols",
            options=symbols_pool,
            default=default_sel,
            help="Selections auto-saved to disk"
        )
    else:
        selected_symbols = []

    if selected_symbols != saved_watchlist.get(preset_choice, []):
        saved_watchlist[preset_choice] = selected_symbols
        save_watchlist(saved_watchlist)
        st.caption("💾 Watchlist saved")

    st.caption(f"**{len(selected_symbols)}** symbols selected")

    extra_raw = st.text_input("➕ Extra tickers (comma-separated)", placeholder="ZOMATO,PAYTM")
    if extra_raw.strip():
        extras = [
            s.strip().upper() + ("" if s.strip().upper().endswith(".NS") else ".NS")
            for s in extra_raw.split(",") if s.strip()
        ]
        selected_symbols = list(dict.fromkeys(selected_symbols + extras))

    st.divider()
    st.markdown("### 📐 Strategy Parameters")
    orb_minutes    = st.number_input("ORB Minutes", 5, 60, 15)
    ema_period     = st.number_input("EMA Period (5m)", 5, 100, 20)
    ema_15m_period = st.number_input("EMA Period (15m MTF)", 5, 100, 20)
    atr_period     = st.number_input("ATR Period", 5, 30, 14)
    rsi_period     = st.number_input("RSI Period", 5, 30, 14)
    st_atr_mult    = st.slider("Supertrend ATR Multiplier", 1.0, 5.0, 3.0, 0.5)

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
        st.rerun()

    risk_pct      = st.slider("Risk per Trade (%)", 0.5, 3.0, 1.0, 0.1)
    max_trades    = st.number_input("Max Concurrent Trades", 1, 30, 5)
    max_risk_pct  = st.slider("Max Portfolio Risk (%)", 1.0, 10.0, 5.0, 0.5)

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
    use_mtf        = st.checkbox("MTF Confirmation (15m EMA)", True)
    use_macd       = st.checkbox("MACD Filter", True)
    use_nifty_filter = st.checkbox("Nifty Index Filter", True)
    use_vix_sizing = st.checkbox("VIX-Based Position Sizing", True)
    use_gap_detect = st.checkbox("Gap Detection", True)
    gap_pct        = st.slider("Gap Threshold (%)", 0.5, 3.0, 1.0, 0.1) / 100

    st.divider()
    st.markdown("### 🛡️ Stop Loss")
    use_supertrend  = st.checkbox("Use Supertrend SL (vs fixed %)", True)
    trail_buy_pct   = st.slider("Trail Buy SL % (fallback)", 0.1, 2.0, 0.5, 0.05) / 100
    trail_sell_pct  = st.slider("Trail Sell SL % (fallback)", 0.1, 2.0, 0.5, 0.05) / 100

    st.divider()
    st.markdown("### 📦 Partial Profit")
    use_partial = st.checkbox("Partial Profit Booking (50% @ 1×ATR)", True)

    st.divider()
    st.markdown("### 📡 Telegram Alerts")
    tg_token   = st.text_input("Bot Token", type="password", placeholder="5XXXXXX:AAF...")
    tg_chat_id = st.text_input("Chat ID", placeholder="-100XXXXXXXXXX")
    send_tg    = st.checkbox("Enable Telegram", False)

    st.divider()
    show_errors = st.checkbox("Show fetch errors", False)

# ================================
# HELPER: SEND TELEGRAM
# ================================
def send_telegram(msg: str):
    if not (send_tg and tg_token and tg_chat_id):
        return
    try:
        url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
        requests.post(url, data={"chat_id": tg_chat_id, "text": msg, "parse_mode": "HTML"}, timeout=5)
    except Exception:
        pass

# ================================
# MAIN HEADER
# ================================
col_h1, col_h2, col_h3, col_h4 = st.columns([4, 1, 1, 1])
with col_h1:
    st.markdown('<div class="header-title">🚀 ORB Smart Scanner <span style="color:#6366f1;font-size:1rem;font-weight:600;vertical-align:middle;">PRO</span></div>', unsafe_allow_html=True)
    status_txt = "🟢 Market Open" if market_open else ("🟡 Pre-Market" if is_pre_market() else "🔴 Market Closed")
    st.markdown(f'<div class="header-subtitle">{status_txt} &nbsp;|&nbsp; {datetime.now().strftime("%d %b %Y, %H:%M:%S")} &nbsp;|&nbsp; {len(selected_symbols)} symbols loaded</div>', unsafe_allow_html=True)
with col_h2:
    manual_scan = st.button("🔄 Scan Now", use_container_width=True, type="primary")
with col_h3:
    if st.button("🧹 Clear Trades", use_container_width=True):
        st.session_state.active_trades = {}
        st.session_state.closed_trades = []
        st.rerun()
with col_h4:
    if st.button("🔓 Unlock Trading", use_container_width=True):
        st.session_state.trading_locked = False
        st.session_state.lock_reason = ""
        st.rerun()

# ================================
# DAILY P&L LOCK CHECK
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

if st.session_state.trading_locked:
    if "profit" in st.session_state.lock_reason.lower():
        st.markdown(f'<div class="daily-profit-banner">🏆 TRADING LOCKED — {st.session_state.lock_reason}. Click "Unlock Trading" to override.</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="daily-limit-banner">🛑 TRADING LOCKED — {st.session_state.lock_reason}. Click "Unlock Trading" to override.</div>', unsafe_allow_html=True)

if not market_open:
    st.info("⏸ Market is closed. Fetching last 5 days of intraday data for analysis. Use **Scan Now** to run manually.")

# ================================
# *** CORE FIX: ROBUST FETCH FUNCTION ***
# ================================
def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Robustly flatten MultiIndex columns produced by yfinance.
    Works for both single-ticker and multi-ticker downloads.
    """
    if df is None or df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex):
        # If second level is all empty strings or all same ticker → use first level
        lvl1 = df.columns.get_level_values(1).unique().tolist()
        if len(lvl1) <= 1:
            df.columns = df.columns.get_level_values(0)
        else:
            # Multi-ticker download: pick first ticker's data
            ticker_col = lvl1[0]
            df = df.xs(ticker_col, axis=1, level=1)
    # Normalise column names to Title Case
    df.columns = [str(c).strip().title() for c in df.columns]
    # Rename common variants
    rename_map = {
        "Adj Close": "Close", "Adj_Close": "Close",
        "Adjclose": "Close", "Adj close": "Close",
    }
    df.rename(columns=rename_map, inplace=True)
    return df


def fetch(symbol: str, interval: str = "5m", period: str = "5d") -> tuple:
    """
    Fetch OHLCV data with multiple fallback strategies.
    Returns (symbol, df, error_string_or_None)
    """
    required_cols = {"Open", "High", "Low", "Close", "Volume"}
    min_bars = 10   # reduced minimum — indicator code handles NaNs internally

    # Strategy list: try progressively broader periods
    strategies = [
        {"interval": interval, "period": period},
        {"interval": interval, "period": "5d"},
        {"interval": interval, "period": "1mo"},
    ]
    # For daily data no need for fallbacks
    if interval == "1d":
        strategies = [{"interval": "1d", "period": "5d"}]

    last_err = "Unknown error"
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

            # Verify required columns exist
            missing = required_cols - set(df.columns)
            if missing:
                last_err = f"Missing columns: {missing}"
                continue

            # Drop rows where all OHLC are NaN
            df.dropna(subset=["Open", "High", "Low", "Close"], how="all", inplace=True)

            if len(df) < min_bars:
                last_err = f"Too few bars after cleaning: {len(df)} (need {min_bars})"
                continue

            # Ensure index is DatetimeIndex
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)

            # Remove timezone if present (simplifies time comparisons)
            if df.index.tz is not None:
                df.index = df.index.tz_convert("Asia/Kolkata").tz_localize(None)

            df.sort_index(inplace=True)
            return symbol, df, None

        except Exception as e:
            last_err = f"{type(e).__name__}: {str(e)[:120]}"
            continue

    return symbol, None, last_err


# ================================
# MARKET CONTEXT FETCH (Nifty + VIX)
# ================================
@st.cache_data(ttl=120)
def fetch_nifty_vix():
    result = {"nifty_change": 0.0, "nifty_price": 0.0, "vix": 0.0}
    try:
        _, nifty, _ = fetch("^NSEI", interval="1d", period="5d")
        if nifty is not None and len(nifty) >= 2:
            result["nifty_price"]  = float(nifty["Close"].iloc[-1])
            result["nifty_change"] = float(nifty["Close"].iloc[-1] - nifty["Close"].iloc[-2])
    except Exception:
        pass
    try:
        _, vix, _ = fetch("^INDIAVIX", interval="1d", period="5d")
        if vix is not None and not vix.empty:
            result["vix"] = float(vix["Close"].iloc[-1])
    except Exception:
        pass
    return result

mkt_ctx = fetch_nifty_vix()
st.session_state.nifty_trend = mkt_ctx["nifty_change"]
st.session_state.vix_value   = mkt_ctx["vix"]

# ================================
# INDICATORS
# ================================
def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]
    vol   = df["Volume"]

    # EMA
    df["EMA"] = close.ewm(span=ema_period, adjust=False).mean()

    # ATR (True Range)
    prev_close = close.shift(1)
    df["TR"]   = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)
    df["ATR"]  = df["TR"].rolling(atr_period, min_periods=1).mean()

    # Volume ratio
    df["Vol_Avg"] = vol.rolling(20, min_periods=5).mean()

    # Candle body %
    body          = (close - df["Open"]).abs()
    rng           = (high - low).replace(0, np.nan).fillna(1e-9)
    df["BodyPct"] = (body / rng).clip(0, 1)

    # RSI
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    avg_g = gain.ewm(com=rsi_period - 1, adjust=False).mean()
    avg_l = loss.ewm(com=rsi_period - 1, adjust=False).mean()
    rs    = avg_g / avg_l.replace(0, np.nan).fillna(1e-9)
    df["RSI"] = 100 - (100 / (1 + rs))

    # MACD
    ema12         = close.ewm(span=12, adjust=False).mean()
    ema26         = close.ewm(span=26, adjust=False).mean()
    df["MACD"]     = ema12 - ema26
    df["MACD_sig"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"]= df["MACD"] - df["MACD_sig"]

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
        # Finalise bands
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


# ================================
# SIGNAL FILTERS
# ================================
def breakout_confirmed(df, level, direction):
    if len(df) < 2:
        return False
    last = float(df["Close"].iloc[-1])
    prev = float(df["Close"].iloc[-2])
    if direction == "BUY":
        return prev > level and last > level
    return prev < level and last < level


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


def check_supertrend(df, direction):
    st_d = int(df["ST_dir"].iloc[-1])
    return (st_d == 1 and direction == "BUY") or (st_d == -1 and direction == "SELL")


def check_gap(df_5m):
    """Return gap % vs previous day's close using first bar of today."""
    try:
        df_5m = df_5m.copy()
        df_5m.index = pd.to_datetime(df_5m.index)
        dates = df_5m.index.normalize().unique()
        if len(dates) < 2:
            return 0.0
        today     = dates[-1]
        yesterday = dates[-2]
        today_open  = float(df_5m[df_5m.index.normalize() == today]["Open"].iloc[0])
        yest_close  = float(df_5m[df_5m.index.normalize() == yesterday]["Close"].iloc[-1])
        if yest_close == 0:
            return 0.0
        return (today_open - yest_close) / yest_close
    except Exception:
        return 0.0


def signal_score(vol_ratio, atr_ratio, body_pct, rsi_val, direction):
    """Score 1–5 based on filter quality."""
    score = 0
    if vol_ratio >= 3.0:
        score += 1
    elif vol_ratio >= 2.0:
        score += 0.7
    elif vol_ratio >= min_vol_ratio:
        score += 0.4
    if atr_ratio >= min_atr_ratio * 2:
        score += 1
    elif atr_ratio >= min_atr_ratio:
        score += 0.6
    if body_pct >= 0.8:
        score += 1
    elif body_pct >= 0.65:
        score += 0.7
    elif body_pct >= min_body_pct:
        score += 0.4
    if direction == "BUY":
        if rsi_val >= 65:
            score += 1
        elif rsi_val >= 55:
            score += 0.7
        else:
            score += 0.3
    else:
        if rsi_val <= 35:
            score += 1
        elif rsi_val <= 45:
            score += 0.7
        else:
            score += 0.3
    return round(min(score / 4 * 5, 5), 1)


# ================================
# SIGNAL GENERATOR
# ================================
def get_orb_range(df: pd.DataFrame):
    """Extract ORB high/low from the most recent trading day."""
    df = df.copy()
    df.index = pd.to_datetime(df.index)
    # Get most recent date
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


def get_signal(df_5m: pd.DataFrame, df_15m=None):
    if df_5m is None or len(df_5m) < 10:
        return None, "Insufficient 5m data"

    df = add_indicators(df_5m)
    df.index = pd.to_datetime(df.index)

    orb_df, day_df = get_orb_range(df)

    if len(orb_df) < 2:
        # Fallback: use first N bars of full dataset as ORB
        orb_df  = df.iloc[:max(2, int(orb_minutes // 5))]
        day_df  = df

    orb_high = float(orb_df["High"].max())
    orb_low  = float(orb_df["Low"].min())
    last     = float(df["Close"].iloc[-1])
    atr      = float(df["ATR"].iloc[-1]) if not pd.isna(df["ATR"].iloc[-1]) else 0.0

    if orb_high == orb_low:
        return None, "ORB range is zero"

    if last > orb_high:
        direction, level = "BUY", orb_high
    elif last < orb_low:
        direction, level = "SELL", orb_low
    else:
        return None, "Price inside ORB range"

    if not breakout_confirmed(df, level, direction):
        return None, "Breakout not confirmed (2-bar rule)"

    body_pct = float(df["BodyPct"].iloc[-1])
    if pd.isna(body_pct) or body_pct < min_body_pct:
        return None, f"Weak candle body ({body_pct:.2f})"

    vol_ok, vol_ratio = check_volume(df)
    if not vol_ok:
        return None, f"Low volume ratio ({vol_ratio}x < {min_vol_ratio}x)"

    if not check_ema_dist(df):
        ema_val = float(df["EMA"].iloc[-1])
        dist_pct = abs(last - ema_val) / ema_val * 100 if ema_val else 0
        return None, f"EMA distance out of range ({dist_pct:.2f}%)"

    if not check_atr(df):
        return None, "Low ATR (insufficient volatility)"

    rsi_ok, rsi_val = check_rsi(df, direction)
    if not rsi_ok:
        return None, f"RSI filter failed ({rsi_val})"

    if use_macd and not check_macd(df, direction):
        return None, "MACD histogram against direction"

    # MTF check
    mtf_ema_rising = None
    if use_mtf and df_15m is not None and len(df_15m) >= ema_15m_period + 2:
        df15 = add_indicators_15m(df_15m)
        ema_now  = float(df15["EMA15"].iloc[-1])
        ema_prev = float(df15["EMA15"].iloc[-2])
        mtf_ema_rising = ema_now > ema_prev
        if direction == "BUY" and not mtf_ema_rising:
            return None, "15m EMA not rising (MTF failed)"
        if direction == "SELL" and mtf_ema_rising:
            return None, "15m EMA not falling (MTF failed)"

    # Nifty filter
    if use_nifty_filter:
        nifty_chg = st.session_state.nifty_trend or 0
        if direction == "BUY" and nifty_chg < 0:
            return None, "Nifty is red — BUY skipped"

    # Gap detection
    gap = check_gap(df_5m)
    gap_flag = None
    if use_gap_detect and abs(gap) >= gap_pct:
        gap_flag = "GAP_UP" if gap > 0 else "GAP_DOWN"

    # Supertrend SL
    if use_supertrend:
        sl = float(df["ST_val"].iloc[-1])
    else:
        sl = orb_low if direction == "BUY" else orb_high

    close     = float(df["Close"].iloc[-1])
    atr_ratio = atr / close if close > 0 else 0
    score     = signal_score(vol_ratio, atr_ratio, body_pct, rsi_val, direction)

    # VIX sizing factor
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
    }

    send_telegram(
        f"🚀 <b>ORB Signal — {symbol}</b>\n"
        f"Direction: <b>{direction}</b>\n"
        f"Entry: ₹{price} | SL: ₹{sl} | Target: ₹{round(tgt,2)}\n"
        f"Qty: {qty} | Score: {signal.get('score','—')}/5\n"
        f"RSI: {signal.get('rsi','—')} | Vol Ratio: {signal['vol_ratio']}x\n"
        f"VIX Factor: {vix_factor}"
    )


def manage_trade(symbol, df):
    trade = st.session_state.active_trades[symbol]
    price = float(df["Close"].iloc[-1])
    direction = trade["type"]

    df_ind = add_indicators(df)
    st_val = float(df_ind["ST_val"].iloc[-1]) if "ST_val" in df_ind.columns else None

    # Partial profit booking
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
                st.session_state.capital    += round(partial_pnl, 2)
                st.session_state.daily_pnl  += round(partial_pnl, 2)
                send_telegram(
                    f"📦 <b>Partial Exit — {symbol}</b>\n"
                    f"{partial_qty} qty @ ₹{price:.2f} | P&L: ₹{partial_pnl:+.2f}\n"
                    f"SL moved to breakeven ₹{trade['entry']}"
                )

    # Trailing SL update
    if direction == "BUY":
        if use_supertrend and st_val:
            trade["sl"] = max(trade["sl"], round(st_val, 2))
        else:
            trade["sl"] = max(trade["sl"], round(price * (1 - trail_buy_pct), 2))

        if price <= trade["sl"]:
            pnl = (price - trade["entry"]) * trade["qty_remaining"]
            exit_trade(symbol, price, pnl, "SL Hit")
        elif price >= trade["target"]:
            pnl = (price - trade["entry"]) * trade["qty_remaining"]
            exit_trade(symbol, price, pnl, "Target Hit")
    else:
        if use_supertrend and st_val:
            trade["sl"] = min(trade["sl"], round(st_val, 2))
        else:
            trade["sl"] = min(trade["sl"], round(price * (1 + trail_sell_pct), 2))

        if price >= trade["sl"]:
            pnl = (trade["entry"] - price) * trade["qty_remaining"]
            exit_trade(symbol, price, pnl, "SL Hit")
        elif price <= trade["target"]:
            pnl = (trade["entry"] - price) * trade["qty_remaining"]
            exit_trade(symbol, price, pnl, "Target Hit")


def exit_trade(symbol, price, pnl, reason="Manual"):
    if symbol not in st.session_state.active_trades:
        return
    trade = st.session_state.active_trades.pop(symbol)
    st.session_state.capital   += round(pnl, 2)
    st.session_state.daily_pnl += round(pnl, 2)
    entry_val = trade["entry"] * trade.get("qty_remaining", trade["qty"])
    st.session_state.closed_trades.append({
        "Symbol":     symbol,
        "Type":       trade["type"],
        "Entry":      trade["entry"],
        "Exit":       round(price, 2),
        "Qty":        trade.get("qty_remaining", trade["qty"]),
        "PnL (₹)":   round(pnl, 2),
        "PnL %":      round((pnl / entry_val) * 100, 2) if entry_val else 0,
        "Score":      trade.get("score", "—"),
        "Reason":     reason,
        "Entry Time": trade.get("entry_time", "—"),
        "Exit Time":  datetime.now().strftime("%H:%M:%S"),
        "Note":       "",
    })
    send_telegram(
        f"{'✅' if pnl > 0 else '❌'} <b>Trade Exit — {symbol}</b>\n"
        f"Exit @ ₹{price:.2f} | P&L: ₹{pnl:+.2f}\n"
        f"Reason: {reason}"
    )


# ================================
# MAIN SCAN LOGIC
# ================================
run_scan = (market_open or manual_scan) and not st.session_state.trading_locked

if run_scan and selected_symbols:
    scan_results  = []
    errors        = []
    signals_found = 0

    progress_bar = st.progress(0, text="Initialising scan…")
    total        = len(selected_symbols)

    BATCH     = 20
    all_data  = []
    all_15m   = {}
    done      = 0

    for i in range(0, total, BATCH):
        batch = selected_symbols[i:i + BATCH]
        with ThreadPoolExecutor(max_workers=min(10, len(batch))) as ex:
            futures = {ex.submit(fetch, s, "5m", "5d"): ("5m", s) for s in batch}
            if use_mtf:
                futures.update({ex.submit(fetch, s, "15m", "5d"): ("15m", s) for s in batch})
            for f in as_completed(futures):
                tf, sym = futures[f]
                result  = f.result()
                if tf == "5m":
                    all_data.append(result)
                    done += 1
                    progress_bar.progress(min(done / total, 1.0), text=f"Fetching… {done}/{total}")
                else:
                    _, df15, _ = result
                    if df15 is not None:
                        all_15m[sym] = df15

    progress_bar.empty()

    for symbol, df, err in all_data:
        if err or df is None:
            errors.append({"Symbol": symbol, "Error": err or "No data returned"})
            scan_results.append({
                "Symbol":    "⚠️ " + symbol,
                "Signal":    "Error",
                "Score":     "—",
                "Price":     "—",
                "ORB High":  "—",
                "ORB Low":   "—",
                "ATR":       "—",
                "Vol Ratio": "—",
                "RSI":       "—",
                "Gap %":     "—",
                "Reason":    err or "Fetch failed",
            })
            continue

        # Manage existing active trade
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
                    "Symbol":    symbol,
                    "Signal":    f"🔵 {trade['type']} (Active)",
                    "Score":     trade.get("score", "—"),
                    "Price":     round(price, 2),
                    "ORB High":  "—",
                    "ORB Low":   "—",
                    "ATR":       trade.get("atr", "—"),
                    "Vol Ratio": trade.get("vol_ratio", "—"),
                    "RSI":       trade.get("rsi", "—"),
                    "Gap %":     "—",
                    "Reason":    f"Unrealised ₹{unreal:+,.2f} | SL {trade['sl']}",
                })
            continue

        df15 = all_15m.get(symbol)
        n_active = len(st.session_state.active_trades)
        signal, reason = get_signal(df, df15)

        last_price = round(float(df["Close"].iloc[-1]), 2)

        if signal is None:
            scan_results.append({
                "Symbol":    symbol,
                "Signal":    "—",
                "Score":     "—",
                "Price":     last_price,
                "ORB High":  "—",
                "ORB Low":   "—",
                "ATR":       "—",
                "Vol Ratio": "—",
                "RSI":       "—",
                "Gap %":     "—",
                "Reason":    reason or "No signal",
            })
            continue

        direction = signal["direction"]
        emoji     = "🟢" if direction == "BUY" else "🔴"
        gap_str   = f"{signal['gap']:+.2f}%" if signal.get("gap") else "—"

        if n_active >= max_trades:
            scan_results.append({
                "Symbol":    symbol,
                "Signal":    f"{emoji} {direction} (Skipped)",
                "Score":     signal["score"],
                "Price":     signal["price"],
                "ORB High":  signal["orb_high"],
                "ORB Low":   signal["orb_low"],
                "ATR":       signal["atr"],
                "Vol Ratio": signal["vol_ratio"],
                "RSI":       signal.get("rsi", "—"),
                "Gap %":     gap_str,
                "Reason":    "Max trades reached",
            })
            continue

        enter_trade(symbol, signal)
        signals_found += 1

        scan_results.append({
            "Symbol":    symbol,
            "Signal":    f"{emoji} {direction}",
            "Score":     signal["score"],
            "Price":     signal["price"],
            "ORB High":  signal["orb_high"],
            "ORB Low":   signal["orb_low"],
            "ATR":       signal["atr"],
            "Vol Ratio": signal["vol_ratio"],
            "RSI":       signal.get("rsi", "—"),
            "Gap %":     gap_str,
            "Reason":    f"Entered @ {signal['price']} | Gap: {gap_str}",
        })

    st.session_state.scan_results   = scan_results
    st.session_state.last_scan_time = datetime.now().strftime("%H:%M:%S")
    st.session_state.error_log      = errors

    st.session_state.equity.append({
        "time":    datetime.now(),
        "capital": st.session_state.capital,
    })

    if signals_found > st.session_state.last_signal_count:
        st.components.v1.html(f"<script>checkAndBeep({signals_found});</script>", height=0)
    st.session_state.last_signal_count = signals_found

    if signals_found > 0:
        st.success(f"✅ **{signals_found} new signal(s)** found across {len(selected_symbols)} symbols")
    else:
        error_count = len(errors)
        msg = f"ℹ️ No new signals. {len(selected_symbols)} symbols scanned."
        if error_count:
            msg += f" ({error_count} fetch errors — check Error Log tab)"
        st.info(msg)

elif not selected_symbols:
    st.error("⚠️ No symbols selected. Choose a preset or enter custom tickers in the sidebar.")

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

st.markdown(f"""
<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:10px 18px;margin:8px 0;
            display:flex;gap:24px;align-items:center;font-size:0.9rem;flex-wrap:wrap;">
  <span>🏦 <b>Nifty 50:</b> <span class="{nifty_cls}">{nifty_sym} {abs(nifty_chg):.1f} pts</span></span>
  <span>{vix_badge}</span>
  {'<span style="color:#78350f;font-weight:600;">⚠️ VIX &gt; 20 → Position size halved</span>' if (use_vix_sizing and vix_val > 20) else ''}
  {'<span style="color:#dc2626;font-weight:600;">🚫 Nifty RED → BUY signals filtered</span>' if (use_nifty_filter and nifty_chg < 0) else ''}
  <span style="color:#94a3b8;font-size:0.8rem;">Daily P&L: <b>₹{st.session_state.daily_pnl:+,.0f}</b></span>
</div>
""", unsafe_allow_html=True)

# ================================
# DASHBOARD METRICS
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
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "🔍 Scan Results",
    "📊 Active Trades",
    "📜 Closed Trades",
    "📈 Equity Curve",
    "📊 Perf Stats",
    "🗺️ Sector Heatmap",
    "⚗️ Backtester",
    "⚠️ Error Log",
])

# ── TAB 1: SCAN RESULTS ──
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
                "Partial Done": "✅" if t.get("partial_done") else "⏳",
                "BE SL":        "✅" if t.get("breakeven_sl") else "—",
                "Gap":          t.get("gap_flag", "—") or "—",
                "Entry Time":   t.get("entry_time", "—"),
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
            st.success("Note saved!")
            st.rerun()

        csv = pd.DataFrame(st.session_state.closed_trades).to_csv(index=False)
        st.download_button(
            "⬇️ Export to CSV", csv,
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
                          template="plotly_white", height=400, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)

        peak = equity_df["capital"].cummax()
        dd   = ((equity_df["capital"] - peak) / peak) * 100
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=equity_df["time"], y=dd, mode="lines", fill="tozeroy",
            line=dict(color="#ef4444", width=1.5),
            fillcolor="rgba(239,68,68,0.1)", name="Drawdown %"
        ))
        fig2.update_layout(title="Drawdown %", xaxis_title="Time", yaxis_title="Drawdown (%)",
                            template="plotly_white", height=220, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No equity data yet.")

# ── TAB 5: PERFORMANCE STATS ──
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
        with s1:
            st.markdown(f'<div class="backtest-stat"><div class="val" style="color:#16a34a;">₹{avg_win:,.0f}</div><div class="lbl">Avg Win</div></div>', unsafe_allow_html=True)
        with s2:
            st.markdown(f'<div class="backtest-stat"><div class="val" style="color:#dc2626;">₹{avg_loss:,.0f}</div><div class="lbl">Avg Loss</div></div>', unsafe_allow_html=True)
        with s3:
            st.markdown(f'<div class="backtest-stat"><div class="val">{pf:.2f}x</div><div class="lbl">Profit Factor</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        s4, s5, s6, s7 = st.columns(4)
        with s4:
            st.markdown(f'<div class="backtest-stat"><div class="val">{max_consec_wins}</div><div class="lbl">Max Consec. Wins</div></div>', unsafe_allow_html=True)
        with s5:
            st.markdown(f'<div class="backtest-stat"><div class="val">{max_consec_loss}</div><div class="lbl">Max Consec. Losses</div></div>', unsafe_allow_html=True)
        with s6:
            st.markdown(f'<div class="backtest-stat"><div class="val">{best_hr}:00</div><div class="lbl">Best Hour</div></div>', unsafe_allow_html=True)
        with s7:
            st.markdown(f'<div class="backtest-stat"><div class="val">{worst_hr}:00</div><div class="lbl">Worst Hour</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if not hour_pnl.empty:
            fig_h = px.bar(
                x=[f"{h}:00" for h in hour_pnl.index],
                y=hour_pnl.values,
                color=hour_pnl.values,
                color_continuous_scale=["#ef4444", "#fbbf24", "#22c55e"],
                labels={"x": "Hour", "y": "P&L (₹)"},
                title="P&L by Hour of Day"
            )
            fig_h.update_layout(template="plotly_white", height=300, showlegend=False,
                                 coloraxis_showscale=False, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_h, use_container_width=True)

        df_p2 = df_p[pd.to_numeric(df_p["Score"], errors="coerce").notna()].copy()
        df_p2["Score"] = pd.to_numeric(df_p2["Score"])
        if not df_p2.empty:
            fig_s = px.scatter(
                df_p2, x="Score", y="PnL (₹)", color="Type",
                color_discrete_map={"BUY": "#22c55e", "SELL": "#ef4444"},
                title="Signal Score vs P&L",
                hover_data=["Symbol", "Entry", "Exit"]
            )
            fig_s.update_layout(template="plotly_white", height=300, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_s, use_container_width=True)
    else:
        st.info("No closed trades yet to analyse.")

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
                path=["parent", "Sector"],
                values="Total Signals",
                color="BUY",
                color_continuous_scale=["#fca5a5", "#bbf7d0"],
                title="Signal Distribution by Sector (size = total signals, color = BUY count)"
            )
            fig_tree.update_layout(height=420, margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig_tree, use_container_width=True)

        st.dataframe(heat_df, use_container_width=True, hide_index=True)

        top_sector = heat_df.iloc[0] if not heat_df.empty else None
        if top_sector is not None and top_sector["Total Signals"] > 3:
            st.warning(f"⚠️ Over-concentration: **{top_sector['Sector']}** sector has {top_sector['Total Signals']} signals. Consider diversifying.")
    else:
        st.info("Run a scan first to see sector distribution.")

# ── TAB 7: BACKTESTER ──
with tab7:
    st.markdown("### ⚗️ Built-in Backtester")
    st.caption("Runs ORB logic on last 5 trading days of 5m data — simulates trades day-by-day.")

    bt_col1, bt_col2, bt_col3 = st.columns(3)
    with bt_col1:
        bt_symbols = st.multiselect(
            "Symbols to backtest",
            options=selected_symbols,
            default=selected_symbols[:5] if len(selected_symbols) >= 5 else selected_symbols,
        )
    with bt_col2:
        bt_orb_min = st.number_input("BT ORB Minutes", 5, 60, int(orb_minutes), key="bt_orb")
    with bt_col3:
        bt_atr_tgt = st.number_input("BT ATR Target Multiplier", 1.0, 5.0, 2.0, 0.5, key="bt_atr")

    if st.button("▶️ Run Backtest", type="primary"):
        with st.spinner("Running backtest on 5-day data…"):
            bt_trades = []
            for sym in bt_symbols:
                _, df_bt, err = fetch(sym, "5m", "5d")
                if err or df_bt is None or len(df_bt) < 10:
                    continue
                df_bt = add_indicators(df_bt)
                df_bt.index = pd.to_datetime(df_bt.index)

                for day, grp in df_bt.groupby(df_bt.index.date):
                    grp = grp.copy()
                    grp["_time"] = grp.index.time
                    cutoff_t = (
                        datetime.combine(day, dtime(9, 15))
                        + timedelta(minutes=int(bt_orb_min))
                    ).time()
                    orb_part  = grp[grp["_time"] <= cutoff_t]
                    rest_part = grp[grp["_time"] > cutoff_t]
                    if len(orb_part) < 2 or len(rest_part) < 2:
                        continue

                    orb_h = float(orb_part["High"].max())
                    orb_l = float(orb_part["Low"].min())

                    in_trade = False
                    direction = entry_p = sl_p = tgt_p = 0.0

                    for idx, row in rest_part.iterrows():
                        close = float(row["Close"])
                        atr   = float(row["ATR"]) if not pd.isna(row["ATR"]) else 0

                        if not in_trade:
                            if close > orb_h:
                                direction = "BUY"; entry_p = close
                                sl_p = orb_l; tgt_p = entry_p + bt_atr_tgt * atr
                                in_trade = True
                            elif close < orb_l:
                                direction = "SELL"; entry_p = close
                                sl_p = orb_h; tgt_p = entry_p - bt_atr_tgt * atr
                                in_trade = True
                        else:
                            if direction == "BUY":
                                if close <= sl_p:
                                    bt_trades.append({"Date": str(day), "Symbol": sym, "Dir": "BUY",
                                                       "Entry": round(entry_p, 2), "Exit": round(close, 2),
                                                       "PnL": round(close - entry_p, 2), "Reason": "SL"})
                                    in_trade = False
                                elif close >= tgt_p:
                                    bt_trades.append({"Date": str(day), "Symbol": sym, "Dir": "BUY",
                                                       "Entry": round(entry_p, 2), "Exit": round(close, 2),
                                                       "PnL": round(close - entry_p, 2), "Reason": "TGT"})
                                    in_trade = False
                            else:
                                if close >= sl_p:
                                    bt_trades.append({"Date": str(day), "Symbol": sym, "Dir": "SELL",
                                                       "Entry": round(entry_p, 2), "Exit": round(close, 2),
                                                       "PnL": round(entry_p - close, 2), "Reason": "SL"})
                                    in_trade = False
                                elif close <= tgt_p:
                                    bt_trades.append({"Date": str(day), "Symbol": sym, "Dir": "SELL",
                                                       "Entry": round(entry_p, 2), "Exit": round(close, 2),
                                                       "PnL": round(entry_p - close, 2), "Reason": "TGT"})
                                    in_trade = False

                    if in_trade:
                        close = float(rest_part["Close"].iloc[-1])
                        pnl   = (close - entry_p) if direction == "BUY" else (entry_p - close)
                        bt_trades.append({"Date": str(day), "Symbol": sym, "Dir": direction,
                                           "Entry": round(entry_p, 2), "Exit": round(close, 2),
                                           "PnL": round(pnl, 2), "Reason": "EOD"})

            st.session_state.backtest_results = bt_trades

        if st.session_state.backtest_results:
            bt_df  = pd.DataFrame(st.session_state.backtest_results)
            bt_wins= bt_df[bt_df["PnL"] > 0]
            bt_loss= bt_df[bt_df["PnL"] <= 0]
            bt_wr  = len(bt_wins) / len(bt_df) * 100 if len(bt_df) > 0 else 0
            bt_pf  = abs(bt_wins["PnL"].sum() / bt_loss["PnL"].sum()) \
                     if bt_loss["PnL"].sum() != 0 else float("inf")

            b1, b2, b3, b4, b5 = st.columns(5)
            pnl_color = "#16a34a" if bt_df["PnL"].sum() > 0 else "#dc2626"
            with b1: st.markdown(f'<div class="backtest-stat"><div class="val">{len(bt_df)}</div><div class="lbl">Total Trades</div></div>', unsafe_allow_html=True)
            with b2: st.markdown(f'<div class="backtest-stat"><div class="val" style="color:{pnl_color}">₹{bt_df["PnL"].sum():,.0f}</div><div class="lbl">Total P&L (pts)</div></div>', unsafe_allow_html=True)
            with b3: st.markdown(f'<div class="backtest-stat"><div class="val">{bt_wr:.1f}%</div><div class="lbl">Win Rate</div></div>', unsafe_allow_html=True)
            with b4: st.markdown(f'<div class="backtest-stat"><div class="val">{bt_pf:.2f}x</div><div class="lbl">Profit Factor</div></div>', unsafe_allow_html=True)
            with b5: st.markdown(f'<div class="backtest-stat"><div class="val">{len(bt_wins)}/{len(bt_loss)}</div><div class="lbl">W/L</div></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            bt_df["Cumulative PnL"] = bt_df["PnL"].cumsum()
            fig_bt = go.Figure()
            fig_bt.add_trace(go.Scatter(
                x=list(range(len(bt_df))), y=bt_df["Cumulative PnL"],
                mode="lines+markers", fill="tozeroy",
                line=dict(color="#6366f1", width=2.5),
                fillcolor="rgba(99,102,241,0.1)", name="Cumulative P&L"
            ))
            fig_bt.add_hline(y=0, line_dash="dash", line_color="#94a3b8")
            fig_bt.update_layout(
                title="Backtest Cumulative P&L (price points per share)",
                template="plotly_white", height=350,
                margin=dict(l=10, r=10, t=40, b=10)
            )
            st.plotly_chart(fig_bt, use_container_width=True)
            st.dataframe(bt_df, use_container_width=True, hide_index=True)

            st.download_button(
                "⬇️ Download Backtest CSV",
                bt_df.to_csv(index=False),
                file_name=f"orb_backtest_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )
        else:
            st.warning("No backtest trades generated. Try more symbols or adjust ORB minutes.")

    elif st.session_state.backtest_results:
        st.dataframe(pd.DataFrame(st.session_state.backtest_results), use_container_width=True, hide_index=True)

# ── TAB 8: ERROR LOG ──
with tab8:
    if st.session_state.error_log:
        st.dataframe(pd.DataFrame(st.session_state.error_log), use_container_width=True, hide_index=True)
        st.caption(f"{len(st.session_state.error_log)} symbol(s) had fetch issues")
        st.info(
            "**Common causes of fetch errors:**\n"
            "- Market closed / weekend (5m data may be unavailable — scanner uses 5d period as fallback)\n"
            "- Symbol delisted or incorrect ticker suffix (.NS vs .BO)\n"
            "- Yahoo Finance rate limiting (try again in 30–60 seconds)\n"
            "- Network / proxy issues"
        )
    else:
        st.success("✅ No errors in last scan.")
