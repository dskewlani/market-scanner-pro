# ================================
# ORB SMART SCANNER PRO — v6 ENHANCED
# New in v6:
# 1. Buy/Sell modal dialogs (qty input + swipe-style confirm button)
# 2. Intraday vs Delivery toggle in buy/sell dialog
# 3. Delivery % from NSE (or estimated from volume data)
# 4. Portfolio stores full history per symbol (each buy/sell logged)
# 5. Portfolio refresh fixed (individual symbol re-fetch)
# 6. Watchlist for any BSE/NSE symbol with full signal + delivery %
# 7. Trade history preserved correctly across all sessions
# ================================

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, time as dtime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import plotly.graph_objects as go
import json, os, time, random, traceback

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except ImportError:
    HAS_AUTOREFRESH = False

# ================================
# PAGE CONFIG
# ================================
st.set_page_config(
    page_title="ORB Smart Scanner Pro v6",
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
html,body,[class*="css"]{{font-family:'Outfit',sans-serif;background:var(--bg-main)!important;color:var(--txt)!important;}}
.block-container{{padding-top:.8rem;background:var(--bg-main);}}
.stMetric label{{font-size:.7rem;color:var(--txt-sub);letter-spacing:.07em;text-transform:uppercase;font-family:'Space Mono',monospace;}}
.stMetric [data-testid="stMetricValue"]{{font-size:1.4rem;font-weight:700;}}
.stSidebar,.stSidebar [data-testid="stSidebarContent"]{{background:var(--bg-card)!important;}}
.stButton>button{{border-radius:8px;font-family:'Outfit',sans-serif;font-weight:600;transition:all .2s;font-size:.8rem;padding:4px 12px;}}
.stButton>button[kind="primary"]{{background:linear-gradient(135deg,#22c55e,#16a34a);border:none;color:#fff;}}
.modal-box{{background:var(--bg-card);border:1px solid var(--bdr);border-radius:16px;padding:24px;margin:8px 0;}}
.delivery-badge-high{{display:inline-block;padding:2px 10px;border-radius:20px;background:rgba(34,197,94,.2);color:#22c55e;font-weight:700;font-size:.78rem;border:1px solid rgba(34,197,94,.4);}}
.delivery-badge-med {{display:inline-block;padding:2px 10px;border-radius:20px;background:rgba(245,158,11,.2);color:#fbbf24;font-weight:700;font-size:.78rem;border:1px solid rgba(245,158,11,.4);}}
.delivery-badge-low {{display:inline-block;padding:2px 10px;border-radius:20px;background:rgba(239,68,68,.2);color:#f87171;font-weight:700;font-size:.78rem;border:1px solid rgba(239,68,68,.4);}}
.row-strong-buy{{background:rgba(34,197,94,.18)!important;border-left:4px solid #22c55e!important;}}
.row-buy{{background:rgba(34,197,94,.09)!important;border-left:4px solid #4ade80!important;}}
.row-weak-buy{{background:rgba(34,197,94,.04)!important;border-left:3px solid #86efac!important;}}
.row-neutral{{background:rgba(255,255,255,.02)!important;border-left:3px solid #64748b!important;}}
.row-avoid{{background:rgba(239,68,68,.06)!important;border-left:3px solid #fca5a5!important;}}
.row-sell{{background:rgba(239,68,68,.18)!important;border-left:4px solid #ef4444!important;}}
.row-strong-sell{{background:rgba(239,68,68,.28)!important;border-left:4px solid #dc2626!important;}}
.row-active{{background:rgba(99,102,241,.1)!important;border-left:4px solid #6366f1!important;}}
.stat-box{{text-align:center;padding:14px;background:var(--bg-card);border-radius:12px;border:1px solid var(--bdr);}}
.stat-box .val{{font-size:1.5rem;font-weight:800;color:var(--txt);}}
.stat-box .lbl{{font-size:.68rem;color:var(--txt-sub);text-transform:uppercase;letter-spacing:.07em;margin-top:3px;font-family:'Space Mono',monospace;}}
.hdr-title{{font-size:1.9rem;font-weight:800;letter-spacing:-.03em;color:var(--txt);}}
.ctx-bar{{background:var(--bg-card);border:1px solid var(--bdr);border-radius:12px;padding:10px 18px;margin:8px 0;display:flex;gap:20px;align-items:center;flex-wrap:wrap;font-size:.87rem;}}
.pnl-pos{{color:#22c55e!important;font-weight:700;}}
.pnl-neg{{color:#ef4444!important;font-weight:700;}}
.trade-type-intraday{{display:inline-block;padding:2px 8px;border-radius:12px;background:rgba(99,102,241,.2);color:#818cf8;font-size:.72rem;font-weight:700;}}
.trade-type-delivery{{display:inline-block;padding:2px 8px;border-radius:12px;background:rgba(245,158,11,.2);color:#fbbf24;font-size:.72rem;font-weight:700;}}
.wl-card{{background:var(--bg-card);border:1px solid var(--bdr);border-radius:12px;padding:12px 16px;margin-bottom:8px;}}
</style>
""", unsafe_allow_html=True)

if HAS_AUTOREFRESH:
    refresh_ms = 30_000
    st_autorefresh(interval=refresh_ms, key="auto_refresh_v6")

# ================================
# PERSISTENCE FILES
# ================================
PORTFOLIO_FILE   = "orb_portfolio_v6.json"
WATCHLIST_FILE   = "orb_watchlist_v6.json"
TRADE_HIST_FILE  = "orb_trade_history_v6.json"
SESSION_FILE     = "orb_session_v6.json"

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
    "Mid Cap": [
        "KALYANKJIL.NS","ANGELONE.NS","NAUKRI.NS","IRCTC.NS","POLYCAB.NS",
        "ASTRAL.NS","PVRINOX.NS","SUNTV.NS","CAMS.NS","AFFLE.NS","VBL.NS",
    ],
    "Custom (Enter Below)": [],
}

LARGE_CAP = {
    "RELIANCE.NS","TCS.NS","HDFCBANK.NS","BHARTIARTL.NS","ICICIBANK.NS","INFOSYS.NS",
    "SBIN.NS","WIPRO.NS","AXISBANK.NS","LT.NS","KOTAKBANK.NS","HCLTECH.NS","BAJFINANCE.NS",
    "ASIANPAINT.NS","MARUTI.NS","TITAN.NS","SUNPHARMA.NS","NTPC.NS","POWERGRID.NS",
    "ULTRACEMCO.NS","NESTLEIND.NS","TATAMOTORS.NS","TATASTEEL.NS","TECHM.NS","ADANIENT.NS",
    "ADANIPORTS.NS","DRREDDY.NS","CIPLA.NS","HEROMOTOCO.NS","EICHERMOT.NS","BAJAJFINSV.NS",
}

# ================================
# SESSION STATE INIT
# ================================
def init_state():
    defaults = {
        "capital": 100_000,
        "initial_capital": 100_000,
        "portfolio": {},          # {sym: {qty, avg_price, trade_type, history:[{qty,price,type,time}]}}
        "trade_history": [],      # all closed trades with full detail
        "equity_curve": [],
        "scan_results": [],
        "last_scan_time": None,
        "error_log": [],
        "daily_pnl": 0.0,
        "trading_locked": False,
        "lock_reason": "",
        "nifty_change": 0.0,
        "nifty_price": 0.0,
        "vix_value": 0.0,
        "market_regime": "Unknown",
        "fetch_cache": {},
        "dark_mode": True,
        "scan_mode": "Intraday (ORB)",
        "watchlist": [],          # list of symbols in watchlist
        "watchlist_data": {},     # cached scan data for watchlist symbols
        # Modal state
        "show_buy_modal": None,
        "show_sell_modal": None,
        "modal_row_data": {},
        "delivery_cache": {},     # {sym: {pct, timestamp}}
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ================================
# PERSISTENCE
# ================================
def save_all():
    try:
        data = {
            "capital": st.session_state.capital,
            "initial_capital": st.session_state.initial_capital,
            "portfolio": st.session_state.portfolio,
            "trade_history": st.session_state.trade_history,
            "daily_pnl": st.session_state.daily_pnl,
            "equity_curve": [{"time": str(e["time"]), "capital": e["capital"]} for e in st.session_state.equity_curve],
            "trading_locked": st.session_state.trading_locked,
            "lock_reason": st.session_state.lock_reason,
            "watchlist": st.session_state.watchlist,
        }
        with open(SESSION_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        pass  # Silent fail — don't break UI

def load_all():
    if not os.path.exists(SESSION_FILE):
        return
    try:
        with open(SESSION_FILE) as f:
            data = json.load(f)
        st.session_state.capital          = data.get("capital", 100_000)
        st.session_state.initial_capital  = data.get("initial_capital", 100_000)
        st.session_state.portfolio        = data.get("portfolio", {})
        st.session_state.trade_history    = data.get("trade_history", [])
        st.session_state.daily_pnl        = data.get("daily_pnl", 0.0)
        st.session_state.trading_locked   = data.get("trading_locked", False)
        st.session_state.lock_reason      = data.get("lock_reason", "")
        st.session_state.watchlist        = data.get("watchlist", [])
        raw_eq = data.get("equity_curve", [])
        st.session_state.equity_curve = [{"time": pd.to_datetime(e["time"]), "capital": e["capital"]} for e in raw_eq]
    except:
        pass

load_all()

# ================================
# CACHE HELPERS
# ================================
def _cache_ttl(interval):
    return {"5m": 25, "15m": 60, "1h": 300, "1d": 600, "1wk": 1200}.get(interval, 60)

def cache_get(symbol, interval):
    key = f"{symbol}_{interval}"
    entry = st.session_state.fetch_cache.get(key)
    if entry and (time.time() - entry["ts"]) < _cache_ttl(interval):
        return entry["df"]
    return None

def cache_set(symbol, interval, df):
    key = f"{symbol}_{interval}"
    st.session_state.fetch_cache[key] = {"df": df, "ts": time.time()}

# ================================
# FETCH DATA
# ================================
def _flatten(df):
    if df is None or df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex):
        lvls = df.columns.get_level_values(1).unique().tolist()
        df = df.xs(lvls[0], axis=1, level=1) if len(lvls) > 1 else df
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).strip().title() for c in df.columns]
    for old, new in [("Adj Close","Close"),("Adj_Close","Close"),("Adjclose","Close")]:
        if old in df.columns:
            df.rename(columns={old: new}, inplace=True)
    return df

def fetch_data(symbol, interval="5m", period="5d", force=False):
    """Fetch OHLCV data. Returns (df, error_str)"""
    if not force:
        cached = cache_get(symbol, interval)
        if cached is not None:
            return cached, None

    required = {"Open","High","Low","Close","Volume"}
    strategies = [{"interval": interval, "period": period}]
    if interval == "1d":
        strategies = [{"interval": "1d", "period": "1y"}]
    elif interval == "1wk":
        strategies = [{"interval": "1wk", "period": "2y"}]
    elif interval == "1h":
        strategies = [{"interval": "1h", "period": "5d"}]

    for attempt in range(3):
        for strat in strategies:
            try:
                raw = yf.download(symbol, interval=strat["interval"], period=strat["period"],
                                  progress=False, auto_adjust=True, actions=False)
                if raw is None or raw.empty:
                    continue
                df = _flatten(raw.copy())
                if len(required - set(df.columns)) > 0:
                    continue
                df.dropna(subset=["Open","High","Low","Close"], how="all", inplace=True)
                if len(df) < 3:
                    continue
                if not isinstance(df.index, pd.DatetimeIndex):
                    df.index = pd.to_datetime(df.index)
                if df.index.tz is not None:
                    df.index = df.index.tz_convert("Asia/Kolkata").tz_localize(None)
                df.sort_index(inplace=True)
                cache_set(symbol, interval, df)
                return df, None
            except Exception as e:
                last_err = str(e)[:80]
        if attempt < 2:
            time.sleep(1 + random.uniform(0, 1))
    return None, f"Fetch failed after 3 attempts"

# ================================
# DELIVERY PERCENTAGE ESTIMATION
# ================================
def get_delivery_pct(symbol):
    """
    Estimate delivery % from recent volume patterns.
    True delivery data requires NSE bhav copy or paid API.
    We estimate: if today's volume is higher and price moved up with body,
    it suggests delivery buying. We use a proxy formula.
    """
    cached = st.session_state.delivery_cache.get(symbol)
    if cached and (time.time() - cached["ts"]) < 3600:
        return cached["pct"]

    try:
        df, err = fetch_data(symbol, "1d", "1mo")
        if err or df is None or len(df) < 10:
            return None

        # Proxy delivery % calculation:
        # High delivery = high volume relative to avg, price close near high, large body
        close = df["Close"]
        high  = df["High"]
        low   = df["Low"]
        vol   = df["Volume"]

        last_vol   = float(vol.iloc[-1])
        avg_vol    = float(vol.rolling(20, min_periods=5).mean().iloc[-1])
        vol_ratio  = last_vol / avg_vol if avg_vol > 0 else 1.0

        body  = abs(float(close.iloc[-1]) - float(df["Open"].iloc[-1]))
        rng   = float(high.iloc[-1]) - float(low.iloc[-1])
        body_pct = body / rng if rng > 0 else 0.5

        # Price position in range (close near high = bullish delivery)
        pos_in_rng = (float(close.iloc[-1]) - float(low.iloc[-1])) / rng if rng > 0 else 0.5

        # Estimate delivery % — ranges 20–80% typically
        # High vol ratio + body + position => higher delivery
        estimated_delivery = min(85, max(15,
            (vol_ratio * 0.3 + body_pct * 0.4 + pos_in_rng * 0.3) * 70 + 10
        ))

        st.session_state.delivery_cache[symbol] = {"pct": round(estimated_delivery, 1), "ts": time.time()}
        return round(estimated_delivery, 1)
    except:
        return None

def delivery_badge(pct):
    if pct is None:
        return '<span style="color:var(--txt-sub);font-size:.75rem;">—</span>'
    if pct >= 50:
        return f'<span class="delivery-badge-high">🟢 {pct}% Del</span>'
    elif pct >= 30:
        return f'<span class="delivery-badge-med">🟡 {pct}% Del</span>'
    else:
        return f'<span class="delivery-badge-low">🔴 {pct}% Del</span>'

def delivery_suggestion(pct):
    if pct is None:
        return "No data"
    if pct >= 55:
        return "✅ High delivery — Good for long-term buying"
    elif pct >= 35:
        return "⚡ Moderate delivery — Suitable for swing"
    else:
        return "⚠️ Low delivery — Mostly speculative/intraday"

# ================================
# MARKET CONTEXT
# ================================
@st.cache_data(ttl=120)
def fetch_nifty_vix():
    result = {"nifty_change": 0.0, "nifty_price": 0.0, "vix": 0.0}
    try:
        df, _ = fetch_data("^NSEI", "1d", "5d", force=True)
        if df is not None and len(df) >= 2:
            result["nifty_price"]  = round(float(df["Close"].iloc[-1]), 2)
            result["nifty_change"] = round(float(df["Close"].iloc[-1]) - float(df["Close"].iloc[-2]), 2)
    except:
        pass
    try:
        df, _ = fetch_data("^INDIAVIX", "1d", "5d", force=True)
        if df is not None and not df.empty:
            result["vix"] = round(float(df["Close"].iloc[-1]), 2)
    except:
        pass
    return result

mkt_ctx = fetch_nifty_vix()

# ================================
# INDICATORS
# ================================
def add_indicators(df, ema_p=20, rsi_p=14, atr_p=14, st_mult=3.0):
    df = df.copy()
    c, h, l, v = df["Close"], df["High"], df["Low"], df["Volume"]
    df["EMA"] = c.ewm(span=ema_p, adjust=False).mean()
    pc = c.shift(1)
    df["TR"] = pd.concat([h-l, (h-pc).abs(), (l-pc).abs()], axis=1).max(axis=1)
    df["ATR"] = df["TR"].rolling(atr_p, min_periods=1).mean()
    df["Vol_Avg"] = v.rolling(20, min_periods=5).mean()
    body = (c - df["Open"]).abs()
    rng  = (h - l).replace(0, np.nan).fillna(1e-9)
    df["BodyPct"] = (body / rng).clip(0, 1)
    delta = c.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    ag = gain.ewm(com=rsi_p-1, adjust=False).mean()
    al = loss.ewm(com=rsi_p-1, adjust=False).mean()
    df["RSI"] = 100 - (100 / (1 + ag / al.replace(0, np.nan).fillna(1e-9)))
    e12 = c.ewm(span=12, adjust=False).mean()
    e26 = c.ewm(span=26, adjust=False).mean()
    df["MACD"] = e12 - e26
    df["MACD_sig"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_sig"]
    # Supertrend
    hl2 = (h + l) / 2
    ub = (hl2 + st_mult * df["ATR"]).values.copy()
    lb = (hl2 - st_mult * df["ATR"]).values.copy()
    cl = c.values
    st_dir = np.ones(len(df), dtype=int)
    for i in range(1, len(df)):
        if cl[i-1] <= ub[i-1]: ub[i] = min(ub[i], ub[i-1])
        if cl[i-1] >= lb[i-1]: lb[i] = max(lb[i], lb[i-1])
        if st_dir[i-1] == -1 and cl[i] > ub[i]: st_dir[i] = 1
        elif st_dir[i-1] == 1 and cl[i] < lb[i]: st_dir[i] = -1
        else: st_dir[i] = st_dir[i-1]
    df["ST_dir"] = st_dir
    return df

def detect_regime(df):
    if df is None or len(df) < 20:
        return "Unknown"
    try:
        close = df["Close"]
        h, l  = df["High"], df["Low"]
        tr = pd.concat([h-l, (h-close.shift(1)).abs(), (l-close.shift(1)).abs()], axis=1).max(axis=1)
        atr14 = tr.rolling(14, min_periods=1).mean()
        sma20 = close.rolling(20, min_periods=5).mean()
        std20 = close.rolling(20, min_periods=5).std()
        bb_w  = (2*std20 / sma20.replace(0,np.nan).fillna(1)).iloc[-1]
        dm_p = (h.diff()).clip(lower=0)
        dm_m = (-l.diff()).clip(lower=0)
        dp = 100 * pd.Series(np.where(dm_p>dm_m, dm_p, 0)).rolling(14,min_periods=1).mean() / atr14.replace(0,np.nan).fillna(1)
        dm = 100 * pd.Series(np.where(pd.Series(dm_m)>pd.Series(dm_p), dm_m, 0)).rolling(14,min_periods=1).mean() / atr14.replace(0,np.nan).fillna(1)
        dx = 100*(dp-dm).abs()/(dp+dm).replace(0,np.nan).fillna(1)
        adx = dx.rolling(14,min_periods=1).mean().iloc[-1]
        if adx > 25: return "Trending"
        elif bb_w > 0.04: return "Volatile"
        else: return "Ranging"
    except:
        return "Unknown"

def get_orb_range(df, orb_minutes=15):
    df = df.copy()
    df.index = pd.to_datetime(df.index)
    last_date = df.index.normalize().max()
    day_df = df[df.index.normalize() == last_date].copy()
    day_df["_t"] = day_df.index.time
    ms = dtime(9, 15)
    cutoff = (datetime.combine(last_date.date(), ms) + timedelta(minutes=int(orb_minutes))).time()
    orb_df = day_df[day_df["_t"] <= cutoff]
    return orb_df, day_df

# ================================
# SIGNAL SCORING
# ================================
def compute_signal(df_5m, df_15m=None, df_1h=None, df_daily=None, df_weekly=None,
                   mode="Intraday (ORB)", orb_min=15, ema_p=20):
    result = {
        "direction": "NEUTRAL", "score": 25, "label": "⚪ Neutral",
        "sig_css": "sig-neutral", "row_css": "row-neutral",
        "price": None, "orb_high": None, "orb_low": None,
        "atr": None, "vol_ratio": None, "rsi": None,
        "gap_pct": None, "regime": "Unknown",
        "sl_price": None, "target_price": None,
        "trend": None, "from_52w_low": None, "from_52w_high": None,
        "macd_hist": None, "body_pct": None,
        "mtf_bull": None, "h1_bull": None,
    }

    if mode in ("Intraday (ORB)", "Both"):
        if df_5m is None or len(df_5m) < 10:
            return result
        df = add_indicators(df_5m, ema_p=ema_p)
        orb_df, _ = get_orb_range(df, orb_min)
        if len(orb_df) < 1:
            orb_df = df.iloc[:max(2, orb_min//5)]
        result["orb_high"] = round(float(orb_df["High"].max()), 2)
        result["orb_low"]  = round(float(orb_df["Low"].min()), 2)
        last_row = df.iloc[-1]
        price = round(float(last_row["Close"]), 2)
        result["price"] = price
        atr = float(last_row["ATR"]) if not pd.isna(last_row.get("ATR", np.nan)) else price * 0.01
        result["atr"] = round(atr, 2)
        va = float(last_row["Vol_Avg"]) if not pd.isna(last_row.get("Vol_Avg", np.nan)) else 1
        result["vol_ratio"] = round(float(last_row["Volume"]) / va, 2) if va > 0 else None
        result["rsi"]       = round(float(last_row["RSI"]), 1) if not pd.isna(last_row.get("RSI", np.nan)) else 50
        result["body_pct"]  = round(float(last_row["BodyPct"]), 2) if not pd.isna(last_row.get("BodyPct", np.nan)) else 0.5
        result["macd_hist"] = round(float(last_row["MACD_hist"]), 4) if not pd.isna(last_row.get("MACD_hist", np.nan)) else 0
        result["regime"]    = detect_regime(df)

        # Gap
        try:
            dates = df.index.normalize().unique()
            if len(dates) >= 2:
                t_open  = float(df[df.index.normalize() == dates[-1]]["Open"].iloc[0])
                y_close = float(df[df.index.normalize() == dates[-2]]["Close"].iloc[-1])
                if y_close > 0:
                    result["gap_pct"] = round((t_open - y_close) / y_close * 100, 2)
        except:
            pass

        # 15m MTF
        if df_15m is not None and len(df_15m) >= 22:
            df15 = add_indicators(df_15m, ema_p=ema_p)
            result["mtf_bull"] = float(df15["EMA"].iloc[-1]) > float(df15["EMA"].iloc[-2])

        # 1h
        if df_1h is not None and len(df_1h) >= 22:
            df1h = add_indicators(df_1h, ema_p=ema_p)
            result["h1_bull"] = float(df1h["EMA"].iloc[-1]) > float(df1h["EMA"].iloc[-2])

        # Direction
        if result["orb_high"] and result["orb_low"]:
            if price > result["orb_high"]:   direction = "BUY"
            elif price < result["orb_low"]:  direction = "SELL"
            else:                            direction = "NEUTRAL"
        else:
            direction = "NEUTRAL"
        result["direction"] = direction

        # Score
        score = 0
        vr = result["vol_ratio"] or 0
        rsi = result["rsi"] or 50
        bp  = result["body_pct"] or 0
        mh  = result["macd_hist"] or 0

        if vr >= 3.0: score += 20
        elif vr >= 2.0: score += 15
        elif vr >= 1.5: score += 10
        elif vr >= 1.2: score += 5

        if direction == "BUY":
            if 55 <= rsi <= 75: score += 20
            elif 50 <= rsi < 55: score += 13
            elif rsi > 75: score += 5
        elif direction == "SELL":
            if 25 <= rsi <= 45: score += 20
            elif 45 < rsi <= 50: score += 13

        if bp >= 0.8: score += 15
        elif bp >= 0.65: score += 10
        elif bp >= 0.5: score += 6

        if result["mtf_bull"] is True:   score += 15
        elif result["mtf_bull"] is False: score -= 5
        if result["h1_bull"] is True:    score += 20
        elif result["h1_bull"] is False:  score -= 10

        if direction == "BUY" and mh > 0: score += 10
        elif direction == "SELL" and mh < 0: score += 10
        if result["regime"] == "Trending": score += 5
        elif result["regime"] == "Ranging": score -= 10

        result["score"] = max(0, min(100, score))

    elif mode == "Delivery / Swing":
        if df_daily is None or len(df_daily) < 30:
            return result
        df = add_indicators(df_daily.copy(), ema_p=ema_p)
        close = df["Close"]
        price = round(float(close.iloc[-1]), 2)
        result["price"] = price
        last = df.iloc[-1]
        atr = float(last["ATR"]) if not pd.isna(last.get("ATR", np.nan)) else price * 0.02
        result["atr"] = round(atr, 2)
        va = float(last["Vol_Avg"]) if not pd.isna(last.get("Vol_Avg", np.nan)) else 1
        result["vol_ratio"] = round(float(last["Volume"]) / va, 2) if va > 0 else None
        result["rsi"]       = round(float(last["RSI"]), 1) if not pd.isna(last.get("RSI", np.nan)) else 50
        result["macd_hist"] = round(float(last["MACD_hist"]), 4) if not pd.isna(last.get("MACD_hist", np.nan)) else 0
        result["regime"]    = detect_regime(df)

        lb = min(252, len(df))
        w52h = float(close.iloc[-lb:].max())
        w52l = float(close.iloc[-lb:].min())
        result["from_52w_low"]  = round((price - w52l) / w52l * 100, 1) if w52l > 0 else None
        result["from_52w_high"] = round((price - w52h) / w52h * 100, 1) if w52h > 0 else None

        df["SMA20"] = close.rolling(20, min_periods=5).mean()
        df["SMA50"] = close.rolling(50, min_periods=10).mean()
        try:
            sma20 = float(df["SMA20"].iloc[-1])
            sma50 = float(df["SMA50"].iloc[-1])
            if price > sma20 and sma20 > sma50: result["trend"] = "Uptrend"
            elif price < sma20 and sma20 < sma50: result["trend"] = "Downtrend"
            else: result["trend"] = "Sideways"
        except:
            result["trend"] = "Sideways"

        rsi = result["rsi"] or 50
        mh  = result["macd_hist"] or 0
        score = 0

        if result["trend"] == "Uptrend": score += 25
        elif result["trend"] == "Downtrend": score -= 10

        if 45 <= rsi <= 70: score += 20
        elif rsi > 70: score += 5

        if mh > 0: score += 15
        if (result["vol_ratio"] or 0) >= 1.5: score += 10
        if result["regime"] == "Trending": score += 10

        direction = "BUY" if result["trend"] == "Uptrend" and rsi < 70 and mh > 0 else \
                    "SELL" if result["trend"] == "Downtrend" and rsi > 55 and mh < 0 else "NEUTRAL"
        result["direction"] = direction
        result["score"] = max(0, min(100, score))

    # Label from score+direction
    s = result["score"]
    d = result["direction"]
    if d == "NEUTRAL":
        result["label"] = "⚪ Neutral"
        result["sig_css"] = "sig-neutral"
        result["row_css"] = "row-neutral"
    elif d == "BUY":
        if s >= 80:   result["label"], result["sig_css"], result["row_css"] = "🟢 Strong Buy", "sig-strong-buy", "row-strong-buy"
        elif s >= 65: result["label"], result["sig_css"], result["row_css"] = "🟢 Buy", "sig-buy", "row-buy"
        elif s >= 50: result["label"], result["sig_css"], result["row_css"] = "🟡 Weak Buy", "sig-weak-buy", "row-weak-buy"
        else:         result["label"], result["sig_css"], result["row_css"] = "⚪ Neutral", "sig-neutral", "row-neutral"
    else:
        if s >= 80:   result["label"], result["sig_css"], result["row_css"] = "🔴 Strong Sell", "sig-strong-sell", "row-strong-sell"
        elif s >= 65: result["label"], result["sig_css"], result["row_css"] = "🔴 Sell", "sig-sell", "row-sell"
        elif s >= 50: result["label"], result["sig_css"], result["row_css"] = "🟠 Weak Sell", "sig-weak-sell", "row-weak-sell"
        else:         result["label"], result["sig_css"], result["row_css"] = "⚪ Neutral", "sig-neutral", "row-neutral"

    # SL / Target
    price = result["price"]
    atr   = result["atr"] or 0
    if price:
        sl_mult = 2.0
        if d == "BUY":
            result["sl_price"]     = round(price - sl_mult * atr, 2)
            result["target_price"] = round(price + 2 * atr, 2)
        elif d == "SELL":
            result["sl_price"]     = round(price + sl_mult * atr, 2)
            result["target_price"] = round(price - 2 * atr, 2)

    return result

# ================================
# PORTFOLIO OPERATIONS
# ================================
def portfolio_buy(symbol, qty, price, trade_type="Delivery"):
    """Add a buy to portfolio with history"""
    port = st.session_state.portfolio
    now  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if symbol not in port:
        port[symbol] = {
            "qty": 0,
            "avg_price": 0.0,
            "trade_type": trade_type,
            "history": []
        }
    pos = port[symbol]
    # Update avg price (weighted)
    old_cost = pos["qty"] * pos["avg_price"]
    new_cost = qty * price
    pos["qty"]       += qty
    pos["avg_price"]  = round((old_cost + new_cost) / pos["qty"], 2) if pos["qty"] > 0 else price
    pos["trade_type"] = trade_type
    pos["history"].append({
        "action": "BUY",
        "qty": qty,
        "price": price,
        "trade_type": trade_type,
        "timestamp": now,
        "amount": round(qty * price, 2),
    })
    st.session_state.portfolio = port
    st.session_state.capital  -= qty * price
    save_all()

def portfolio_sell(symbol, qty, current_price):
    """Sell qty from portfolio, book P&L"""
    port = st.session_state.portfolio
    if symbol not in port or port[symbol]["qty"] < qty:
        return 0.0, "Insufficient qty"
    pos = port[symbol]
    avg = pos["avg_price"]
    pnl = round((current_price - avg) * qty, 2)
    pnl_pct = round((current_price - avg) / avg * 100, 2) if avg > 0 else 0
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pos["qty"] -= qty
    pos["history"].append({
        "action": "SELL",
        "qty": qty,
        "price": current_price,
        "avg_cost": avg,
        "pnl": pnl,
        "pnl_pct": pnl_pct,
        "timestamp": now,
        "amount": round(qty * current_price, 2),
    })
    # Add to global trade history
    st.session_state.trade_history.append({
        "Symbol": symbol,
        "Action": "SELL",
        "Qty": qty,
        "Buy Price (Avg)": avg,
        "Sell Price": current_price,
        "P&L (₹)": pnl,
        "P&L %": pnl_pct,
        "Trade Type": pos["trade_type"],
        "Date": now,
    })
    st.session_state.capital += qty * current_price
    st.session_state.daily_pnl += pnl
    if pos["qty"] == 0:
        # Keep in portfolio for history but mark closed
        pos["status"] = "Closed"
    st.session_state.equity_curve.append({"time": datetime.now(), "capital": st.session_state.capital})
    save_all()
    return pnl, None

def get_current_price(symbol):
    """Get latest price from cache or fetch"""
    for interval in ["5m", "1d"]:
        df = cache_get(symbol, interval)
        if df is not None and not df.empty:
            return round(float(df["Close"].iloc[-1]), 2)
    # Try fresh fetch
    df, _ = fetch_data(symbol, "1d", "5d", force=True)
    if df is not None and not df.empty:
        return round(float(df["Close"].iloc[-1]), 2)
    return None

# ================================
# BUY / SELL MODALS
# ================================
def show_buy_modal(sym, row_data):
    """Renders buy dialog inside an expander/container"""
    price     = row_data.get("price", 0) or 0
    atr       = row_data.get("atr", 0) or 0
    sl_price  = row_data.get("sl_price", 0) or (price * 0.97)
    tgt_price = row_data.get("target_price", 0) or (price * 1.03)
    score     = row_data.get("score", 0)
    label     = row_data.get("label", "")
    delivery_pct = get_delivery_pct(sym)

    risk_amt = abs(price - sl_price)
    cap = st.session_state.capital
    sug_qty = max(1, int((cap * 0.01) / risk_amt)) if risk_amt > 0 else 1

    with st.container():
        st.markdown(f"""
        <div class="modal-box">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
            <div>
              <span style="font-size:1.3rem;font-weight:800;">{sym.replace('.NS','').replace('.BO','')}</span>
              &nbsp;<span style="color:#22c55e;font-size:1rem;">₹{price:.2f}</span>
            </div>
            <div>{label} | Score: <b>{score}/100</b></div>
          </div>
          <div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:16px;font-size:.85rem;">
            <span>📉 SL: <b style="color:#ef4444;">₹{sl_price:.2f}</b></span>
            <span>🎯 Target: <b style="color:#22c55e;">₹{tgt_price:.2f}</b></span>
            <span>📦 ATR: <b>₹{atr:.2f}</b></span>
            <span>💰 Available: <b>₹{cap:,.0f}</b></span>
          </div>
          <div style="margin-bottom:12px;">{delivery_badge(delivery_pct)} &nbsp; <span style="font-size:.8rem;color:var(--txt-sub);">{delivery_suggestion(delivery_pct)}</span></div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            trade_type = st.radio("Trade Type", ["Delivery", "Intraday (Leverage)"], key=f"modal_type_{sym}",
                                   help="Delivery = hold overnight | Intraday = same-day, leveraged")
        with col2:
            qty = st.number_input("Quantity", min_value=1, max_value=10000,
                                   value=sug_qty, step=1, key=f"modal_qty_{sym}")
            total_amount = qty * price
            st.markdown(f"**Total: ₹{total_amount:,.2f}**")
            if trade_type == "Intraday (Leverage)":
                leverage_note = "⚡ 5× leverage (MIS) — ensure proper margin"
                st.info(leverage_note, icon="⚡")
            if total_amount > cap and trade_type == "Delivery":
                st.error(f"⚠️ Insufficient capital! Need ₹{total_amount:,.0f}, have ₹{cap:,.0f}")

        can_buy = (trade_type == "Intraday (Leverage)") or (total_amount <= cap)

        bc1, bc2 = st.columns([3, 1])
        with bc1:
            if can_buy:
                if st.button(f"✅ Confirm BUY {qty} × {sym.replace('.NS','')} @ ₹{price:.2f}",
                              type="primary", key=f"confirm_buy_{sym}", use_container_width=True):
                    actual_deduct = total_amount if trade_type == "Delivery" else 0
                    portfolio_buy(sym, qty, price, trade_type)
                    st.success(f"✅ Bought {qty} shares of {sym.replace('.NS','')} @ ₹{price:.2f} | {trade_type}")
                    st.session_state.show_buy_modal = None
                    st.rerun()
        with bc2:
            if st.button("✖ Cancel", key=f"cancel_buy_{sym}", use_container_width=True):
                st.session_state.show_buy_modal = None
                st.rerun()

def show_sell_modal(sym):
    """Renders sell dialog"""
    port = st.session_state.portfolio
    if sym not in port or port[sym]["qty"] == 0:
        st.warning("No open position for this symbol.")
        return

    pos = port[sym]
    qty_held = pos["qty"]
    avg_price = pos["avg_price"]
    trade_type = pos.get("trade_type", "Delivery")
    cur_price = get_current_price(sym)

    if cur_price is None:
        st.error("Could not fetch current price. Please try again.")
        return

    pnl_per_share = cur_price - avg_price
    delivery_pct  = get_delivery_pct(sym)

    with st.container():
        pnl_color = "#22c55e" if pnl_per_share >= 0 else "#ef4444"
        pnl_icon  = "🟢" if pnl_per_share >= 0 else "🔴"
        st.markdown(f"""
        <div class="modal-box">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
            <div>
              <span style="font-size:1.3rem;font-weight:800;">{sym.replace('.NS','').replace('.BO','')}</span>
              &nbsp;<span class="trade-type-{'delivery' if 'Delivery' in trade_type else 'intraday'}">{trade_type}</span>
            </div>
            <div>{pnl_icon} P&L/share: <b style="color:{pnl_color};">₹{pnl_per_share:+.2f}</b></div>
          </div>
          <div style="display:flex;gap:20px;flex-wrap:wrap;margin-bottom:12px;font-size:.85rem;">
            <span>📊 Held: <b>{qty_held} shares</b></span>
            <span>💵 Avg Cost: <b>₹{avg_price:.2f}</b></span>
            <span>💰 LTP: <b>₹{cur_price:.2f}</b></span>
            <span>📦 Invested: <b>₹{qty_held*avg_price:,.0f}</b></span>
          </div>
          <div style="margin-bottom:12px;">{delivery_badge(delivery_pct)}</div>
        </div>
        """, unsafe_allow_html=True)

        sell_qty = st.number_input("Sell Quantity", min_value=1, max_value=qty_held,
                                    value=qty_held, step=1, key=f"sell_qty_{sym}")

        total_sell_val = sell_qty * cur_price
        total_pnl_sell = (cur_price - avg_price) * sell_qty
        pnl_pct_sell   = (total_pnl_sell / (avg_price * sell_qty) * 100) if avg_price > 0 else 0

        pnl_c = "#22c55e" if total_pnl_sell >= 0 else "#ef4444"
        st.markdown(f"""
        <div style="background:var(--bg-card2);border-radius:10px;padding:12px 16px;margin:8px 0;">
          <div style="font-size:.9rem;display:flex;gap:24px;flex-wrap:wrap;">
            <span>Sell Value: <b>₹{total_sell_val:,.2f}</b></span>
            <span style="color:{pnl_c};">P&L: <b>₹{total_pnl_sell:+,.2f} ({pnl_pct_sell:+.2f}%)</b></span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        sc1, sc2 = st.columns([3, 1])
        with sc1:
            if st.button(f"✅ Confirm SELL {sell_qty} × {sym.replace('.NS','')} @ ₹{cur_price:.2f}",
                          key=f"confirm_sell_{sym}", use_container_width=True):
                pnl, err = portfolio_sell(sym, sell_qty, cur_price)
                if err:
                    st.error(err)
                else:
                    sign = "+" if pnl >= 0 else ""
                    st.success(f"✅ Sold {sell_qty} shares @ ₹{cur_price:.2f} | P&L: {sign}₹{pnl:,.2f}")
                    st.session_state.show_sell_modal = None
                    st.rerun()
        with sc2:
            if st.button("✖ Cancel", key=f"cancel_sell_{sym}", use_container_width=True):
                st.session_state.show_sell_modal = None
                st.rerun()

# ================================
# MARKET STATUS
# ================================
def is_market_open():
    now = datetime.now().time()
    return dtime(9, 15) <= now <= dtime(15, 30)

market_open = is_market_open()

# ================================
# SIDEBAR
# ================================
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    c1, c2 = st.columns([3,1])
    with c1: st.markdown("🌙 **Dark Mode**")
    with c2:
        if st.button("Toggle", key="sb_dark"):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()

    st.markdown("### 🎯 Scan Mode")
    scan_mode = st.radio("Style", ["Intraday (ORB)", "Delivery / Swing"], horizontal=False)
    st.session_state.scan_mode = scan_mode

    st.markdown("### 📋 Symbols")
    preset_choice = st.selectbox("Preset", list(PRESETS.keys()))
    if preset_choice == "Custom (Enter Below)":
        custom_raw = st.text_area("Tickers (one per line)", height=80)
        raw_list = [s.strip().upper() for s in custom_raw.replace(",","\n").splitlines() if s.strip()]
        symbols_pool = [s if s.endswith((".NS",".BO")) else s+".NS" for s in raw_list]
    else:
        symbols_pool = PRESETS[preset_choice]

    extra_raw = st.text_input("➕ Extra tickers", placeholder="ZOMATO,PAYTM")
    if extra_raw.strip():
        extras = [s.strip().upper()+(""if s.strip().upper().endswith(".NS")else".NS") for s in extra_raw.split(",") if s.strip()]
        symbols_pool = list(dict.fromkeys(symbols_pool + extras))

    default_sel = symbols_pool[:10] if len(symbols_pool) > 10 else symbols_pool
    selected_symbols = st.multiselect(f"Select ({len(symbols_pool)} avail)", symbols_pool, default=default_sel)

    st.divider()
    st.markdown("### 📐 Parameters")
    orb_minutes   = st.number_input("ORB Minutes", 5, 60, 15)
    ema_period    = st.number_input("EMA Period", 5, 100, 20)
    atr_period    = st.number_input("ATR Period", 5, 30, 14)
    rsi_period    = st.number_input("RSI Period", 5, 30, 14)

    st.divider()
    st.markdown("### 💰 Risk")
    initial_capital = st.number_input("Capital (₹)", 10_000, 10_000_000, 100_000, step=10_000)
    risk_pct        = st.slider("Risk/Trade (%)", 0.5, 5.0, 1.0, 0.1)
    max_trades      = st.number_input("Max Trades", 1, 30, 5)

    if st.button("🔁 Reset Session", key="sb_reset"):
        st.session_state.capital         = initial_capital
        st.session_state.initial_capital = initial_capital
        st.session_state.portfolio       = {}
        st.session_state.trade_history   = []
        st.session_state.equity_curve    = []
        st.session_state.daily_pnl       = 0.0
        st.session_state.trading_locked  = False
        save_all()
        st.rerun()

    st.divider()
    st.markdown("### 📅 Daily Limits")
    daily_loss_pct   = st.slider("Loss Limit (%)", 0.5, 10.0, 3.0, 0.5)
    daily_profit_pct = st.slider("Profit Target (%)", 1.0, 20.0, 5.0, 0.5)

    st.divider()
    st.markdown("### 🔍 Filters")
    min_vol_ratio = st.slider("Min Vol Ratio", 1.0, 5.0, 1.5, 0.1)
    min_score     = st.slider("Min Score", 0, 100, 0, 5)
    use_mtf       = st.checkbox("15m MTF Confirmation", True)
    use_1h        = st.checkbox("1h Confluence", True)
    max_retries   = 3

# ================================
# DAILY LOCK
# ================================
ic = st.session_state.initial_capital
daily_loss_cap   = ic * (daily_loss_pct / 100)
daily_profit_cap = ic * (daily_profit_pct / 100)
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
ch1, ch2, ch3, ch4 = st.columns([4, 1.2, 1, 1])
with ch1:
    status = "🟢 Market Open" if market_open else "🔴 Market Closed"
    st.markdown('<div class="hdr-title">🚀 ORB Smart Scanner <span style="color:#6366f1;font-size:.9rem;">PRO v6</span></div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:.8rem;color:var(--txt-sub);margin-top:-6px;">{status} | {datetime.now().strftime("%d %b %Y %H:%M")} | {len(selected_symbols)} symbols | Mode: {scan_mode}</div>', unsafe_allow_html=True)
with ch2:
    manual_scan = st.button("🔄 Scan Now", use_container_width=True, type="primary", key="hdr_scan")
with ch3:
    if st.button("🧹 Clear", use_container_width=True, key="hdr_clear"):
        st.session_state.scan_results = []
        st.session_state.show_buy_modal = None
        st.session_state.show_sell_modal = None
        st.rerun()
with ch4:
    if st.button("🔓 Unlock", use_container_width=True, key="hdr_unlock"):
        st.session_state.trading_locked = False
        st.session_state.lock_reason = ""
        st.rerun()

if st.session_state.trading_locked:
    css = "lock-profit" if "profit" in st.session_state.lock_reason.lower() else "lock-loss"
    st.markdown(f'<div style="background:{"#142d1a" if "profit" in st.session_state.lock_reason.lower() else "#2d1515"};border:2px solid {"#22c55e" if "profit" in st.session_state.lock_reason.lower() else "#ef4444"};border-radius:10px;padding:10px 16px;text-align:center;font-weight:700;color:{"#22c55e" if "profit" in st.session_state.lock_reason.lower() else "#ef4444"};">{"🏆" if "profit" in st.session_state.lock_reason.lower() else "🛑"} TRADING LOCKED — {st.session_state.lock_reason}</div>', unsafe_allow_html=True)

# ================================
# CONTEXT BAR
# ================================
nifty_col = "#22c55e" if mkt_ctx["nifty_change"] >= 0 else "#ef4444"
nifty_sym = "▲" if mkt_ctx["nifty_change"] >= 0 else "▼"
vix = mkt_ctx["vix"]
vix_cls = "vix-low" if vix <= 15 else ("vix-mid" if vix <= 20 else "vix-high")

# Portfolio unrealised PnL
unrealised = 0.0
for sym, pos in st.session_state.portfolio.items():
    if pos["qty"] > 0:
        cp = get_current_price(sym)
        if cp:
            unrealised += (cp - pos["avg_price"]) * pos["qty"]

dpnl = st.session_state.daily_pnl
dpnl_color = "#22c55e" if dpnl >= 0 else "#ef4444"

st.markdown(f"""
<div class="ctx-bar">
  <span>🏦 <b>Nifty:</b> <span style="color:{nifty_col};font-weight:700">{nifty_sym} {abs(mkt_ctx["nifty_change"]):.1f} ({mkt_ctx["nifty_price"]:.0f})</span></span>
  <span style="display:inline-block;padding:2px 10px;border-radius:20px;background:rgba(239,68,68,.15);color:#f87171;font-weight:700;font-size:.78rem;">VIX {vix:.1f}</span>
  <span>Daily P&L: <span style="color:{dpnl_color};font-weight:700">₹{dpnl:+,.0f}</span></span>
  <span>Unrealised: <span style="color:{"#22c55e" if unrealised>=0 else "#ef4444"};font-weight:700">₹{unrealised:+,.0f}</span></span>
  <span style="color:var(--txt-sub);font-size:.82rem">Positions: <b>{sum(1 for p in st.session_state.portfolio.values() if p["qty"]>0)}</b></span>
  <span style="color:var(--txt-sub);font-size:.82rem">Last scan: <b>{st.session_state.last_scan_time or "—"}</b></span>
</div>
""", unsafe_allow_html=True)

# ================================
# METRICS ROW
# ================================
st.divider()
total_realised = sum(t["P&L (₹)"] for t in st.session_state.trade_history)
wins = [t for t in st.session_state.trade_history if t["P&L (₹)"] > 0]
wr   = len(wins) / len(st.session_state.trade_history) * 100 if st.session_state.trade_history else 0

m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
m1.metric("💼 Capital",      f"₹{st.session_state.capital:,.0f}")
m2.metric("📈 Realised",     f"₹{total_realised:+,.0f}")
m3.metric("💡 Unrealised",   f"₹{unrealised:+,.0f}")
m4.metric("📅 Daily P&L",    f"₹{dpnl:+,.0f}")
m5.metric("📋 Positions",    sum(1 for p in st.session_state.portfolio.values() if p["qty"]>0))
m6.metric("🏆 Win Rate",     f"{wr:.1f}%")
m7.metric("📊 Scanned",      len(st.session_state.scan_results))

# ================================
# RUN SCAN
# ================================
do_scan = (market_open or manual_scan) and selected_symbols

if do_scan:
    scan_results = []
    errors       = []
    total        = len(selected_symbols)
    pb           = st.progress(0, text="Scanning…")

    def scan_symbol(sym):
        try:
            if scan_mode == "Intraday (ORB)":
                df5, _  = fetch_data(sym, "5m", "5d")
                df15, _ = fetch_data(sym, "15m", "5d") if use_mtf else (None, None)
                df1h, _ = fetch_data(sym, "1h", "5d") if use_1h else (None, None)
                result  = compute_signal(df5, df15, df1h, mode=scan_mode, orb_min=orb_minutes, ema_p=ema_period)
            else:
                dfd, _  = fetch_data(sym, "1d", "1y")
                dfw, _  = fetch_data(sym, "1wk", "2y")
                result  = compute_signal(None, None, None, dfd, dfw, mode=scan_mode, ema_p=ema_period)
            result["symbol"] = sym
            return sym, result, None
        except Exception as e:
            return sym, None, str(e)[:80]

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(scan_symbol, s): s for s in selected_symbols}
        done = 0
        for f in as_completed(futures):
            sym_r, result_r, err_r = f.result()
            done += 1
            pb.progress(done / total, text=f"Scanning {done}/{total}…")
            if err_r or result_r is None:
                errors.append({"Symbol": sym_r, "Error": err_r or "No data"})
                scan_results.append({
                    "symbol": sym_r, "label": "❌ Error", "sig_css": "sig-neutral",
                    "row_css": "row-neutral", "score": 0, "price": None,
                    "direction": None, "atr": None, "vol_ratio": None, "rsi": None,
                    "orb_high": None, "orb_low": None, "sl_price": None, "target_price": None,
                    "regime": "—", "trend": None, "from_52w_low": None, "macd_hist": None,
                })
            else:
                scan_results.append(result_r)

    pb.empty()
    st.session_state.scan_results   = scan_results
    st.session_state.last_scan_time = datetime.now().strftime("%H:%M:%S")
    st.session_state.error_log      = errors
    st.session_state.equity_curve.append({"time": datetime.now(), "capital": st.session_state.capital})
    save_all()

    buys = sum(1 for r in scan_results if "Buy" in r.get("label",""))
    sells= sum(1 for r in scan_results if "Sell" in r.get("label",""))
    if buys > 0 or sells > 0:
        st.success(f"✅ {buys} buy signal(s) | {sells} sell signal(s) | {len(errors)} error(s)")
    else:
        st.info(f"ℹ️ {total} scanned — no strong signals. {len(errors)} error(s).")

elif not selected_symbols:
    st.error("⚠️ No symbols selected.")

# ================================
# TABS
# ================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🔍 Scan Results", "📁 Portfolio", "📜 Trade History",
    "📈 Equity Curve", "👁️ Watchlist", "⚗️ Backtester", "⚠️ Errors"
])

# ══════════════════════════════════════════════════════════
# TAB 1 — SCAN RESULTS
# ══════════════════════════════════════════════════════════
with tab1:
    if not st.session_state.scan_results:
        st.info("Press **Scan Now** to run a scan.")
    else:
        results = st.session_state.scan_results

        f1, f2, f3, f4 = st.columns(4)
        with f1: sig_filter  = st.selectbox("Signal", ["All","Strong Buy","Buy","Neutral","Sell","Strong Sell"])
        with f2: sort_by     = st.selectbox("Sort", ["Score ↓","Vol Ratio ↓","RSI ↓","Symbol ↑"])
        with f3: min_score_f = st.slider("Min Score", 0, 100, 0, 5, key="t1_minscore")
        with f4: dir_filter  = st.selectbox("Direction", ["All","BUY","SELL","NEUTRAL"])

        filtered = [r for r in results if r.get("price") is not None or "❌" not in r.get("label","")]
        if sig_filter != "All":
            filtered = [r for r in filtered if sig_filter.lower() in r.get("label","").lower()]
        if min_score_f > 0:
            filtered = [r for r in filtered if r.get("score",0) >= min_score_f]
        if dir_filter != "All":
            filtered = [r for r in filtered if r.get("direction") == dir_filter]

        sort_map = {
            "Score ↓":     lambda x: -x.get("score",0),
            "Vol Ratio ↓": lambda x: -(x.get("vol_ratio") or 0),
            "RSI ↓":       lambda x: -(x.get("rsi") or 0),
            "Symbol ↑":    lambda x: x.get("symbol",""),
        }
        filtered.sort(key=sort_map.get(sort_by, lambda x: -x.get("score",0)))

        st.caption(f"Showing **{len(filtered)}** of **{len(results)}** | Click 🟢 Buy or 🔴 Sell to open trade dialog")

        # Headers
        hcols = st.columns([1.8, 1.2, 0.9, 0.9, 0.9, 0.9, 0.9, 1.1, 0.9, 0.9])
        for col, h in zip(hcols, ["Symbol","Signal/Score","Price","Del%","Vol×","RSI","ATR","SL/Target","Buy","Sell"]):
            col.markdown(f"<span style='font-size:.68rem;text-transform:uppercase;color:var(--txt-sub);letter-spacing:.06em;font-family:Space Mono,monospace;'>{h}</span>", unsafe_allow_html=True)
        st.markdown("---")

        # Check if a modal is currently open
        modal_sym_buy  = st.session_state.get("show_buy_modal")
        modal_sym_sell = st.session_state.get("show_sell_modal")

        for idx, row in enumerate(filtered):
            sym       = row.get("symbol","")
            price     = row.get("price")
            score     = row.get("score", 0)
            label     = row.get("label","—")
            row_css   = row.get("row_css","row-neutral")
            direction = row.get("direction","NEUTRAL")
            vol_r     = row.get("vol_ratio")
            rsi_v     = row.get("rsi")
            atr       = row.get("atr") or 0
            sl_p      = row.get("sl_price")
            tgt_p     = row.get("target_price")
            regime    = row.get("regime","?")
            trend     = row.get("trend")
            in_hold   = sym in st.session_state.portfolio and st.session_state.portfolio[sym]["qty"] > 0

            # Delivery %
            del_pct = st.session_state.delivery_cache.get(sym, {}).get("pct", None)

            bg_map = {
                "row-strong-buy":  "rgba(34,197,94,.15)","row-buy": "rgba(34,197,94,.07)",
                "row-weak-buy":    "rgba(34,197,94,.03)","row-neutral": "rgba(255,255,255,.01)",
                "row-avoid":       "rgba(239,68,68,.05)","row-weak-sell": "rgba(239,68,68,.09)",
                "row-sell":        "rgba(239,68,68,.15)","row-strong-sell": "rgba(239,68,68,.23)",
                "row-active":      "rgba(99,102,241,.09)",
            }
            bd_map = {
                "row-strong-buy":  "#22c55e","row-buy": "#4ade80","row-weak-buy": "#86efac",
                "row-neutral":     "#475569","row-avoid": "#fca5a5","row-weak-sell": "#f87171",
                "row-sell":        "#ef4444","row-strong-sell": "#dc2626","row-active": "#6366f1",
            }
            rc = "row-active" if in_hold else row_css
            bg  = bg_map.get(rc, "transparent")
            bdr = bd_map.get(rc, "#475569")

            cols = st.columns([1.8, 1.2, 0.9, 0.9, 0.9, 0.9, 0.9, 1.1, 0.9, 0.9])

            with cols[0]:
                sym_disp = sym.replace(".NS","").replace(".BO","")
                sub_txt  = trend or regime or ""
                held_badge = ' <span style="color:#818cf8;font-size:.7rem;font-weight:700;">● Held</span>' if in_hold else ""
                st.markdown(
                    f'<div style="background:{bg};border-left:4px solid {bdr};border-radius:8px;padding:5px 8px;">'
                    f'<b style="font-size:.88rem;">{sym_disp}</b>{held_badge}'
                    f'<div style="font-size:.68rem;color:var(--txt-sub);">{sub_txt}</div></div>',
                    unsafe_allow_html=True
                )
            with cols[1]:
                sc = score
                sc_color = "#22c55e" if sc>=65 else ("#f59e0b" if sc>=45 else "#ef4444")
                st.markdown(
                    f'<div style="background:{bg};padding:5px 4px;border-radius:8px;">'
                    f'<span style="font-size:.72rem;">{label}</span>'
                    f'<div style="display:flex;align-items:center;gap:4px;margin-top:3px;">'
                    f'<div style="flex:1;height:5px;background:var(--bdr);border-radius:3px;">'
                    f'<div style="width:{sc}%;height:5px;background:{sc_color};border-radius:3px;"></div></div>'
                    f'<span style="color:{sc_color};font-size:.78rem;font-weight:700;min-width:26px;">{sc}</span></div></div>',
                    unsafe_allow_html=True
                )
            with cols[2]:
                pc = "#22c55e" if direction=="BUY" else ("#ef4444" if direction=="SELL" else "var(--txt)")
                st.markdown(
                    f'<div style="background:{bg};padding:5px 4px;border-radius:8px;font-weight:700;font-size:.85rem;color:{pc};">'
                    f'{"₹"+str(price) if price else "—"}</div>',
                    unsafe_allow_html=True
                )
            with cols[3]:
                # Delivery %
                if del_pct is None:
                    d_txt = '<span style="font-size:.72rem;color:var(--txt-sub);">—</span>'
                else:
                    d_col = "#22c55e" if del_pct>=50 else ("#f59e0b" if del_pct>=30 else "#ef4444")
                    d_txt = f'<span style="font-size:.78rem;color:{d_col};font-weight:700;">{del_pct}%</span>'
                st.markdown(f'<div style="background:{bg};padding:5px 4px;border-radius:8px;">{d_txt}</div>', unsafe_allow_html=True)
            with cols[4]:
                vr_c = "#22c55e" if (vol_r or 0) >= min_vol_ratio else "var(--txt-sub)"
                st.markdown(
                    f'<div style="background:{bg};padding:5px 4px;border-radius:8px;font-size:.82rem;color:{vr_c};">'
                    f'{vol_r:.2f}×</div>' if vol_r else f'<div style="padding:5px 4px;background:{bg};border-radius:8px;">—</div>',
                    unsafe_allow_html=True
                )
            with cols[5]:
                rsi_c = "#22c55e" if rsi_v and 30<rsi_v<70 else "#ef4444"
                st.markdown(
                    f'<div style="background:{bg};padding:5px 4px;border-radius:8px;font-size:.82rem;color:{rsi_c};">'
                    f'{rsi_v:.0f}</div>' if rsi_v else f'<div style="padding:5px 4px;background:{bg};border-radius:8px;">—</div>',
                    unsafe_allow_html=True
                )
            with cols[6]:
                st.markdown(
                    f'<div style="background:{bg};padding:5px 4px;border-radius:8px;font-size:.82rem;">{atr:.2f}</div>',
                    unsafe_allow_html=True
                )
            with cols[7]:
                if sl_p and tgt_p:
                    st.markdown(
                        f'<div style="background:{bg};padding:5px 4px;border-radius:8px;font-size:.72rem;line-height:1.6;">'
                        f'<span style="color:#ef4444;">SL ₹{sl_p:.1f}</span><br>'
                        f'<span style="color:#22c55e;">T ₹{tgt_p:.1f}</span></div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(f'<div style="padding:5px 4px;background:{bg};border-radius:8px;">—</div>', unsafe_allow_html=True)

            with cols[8]:
                if price and direction in ("BUY","NEUTRAL") and not in_hold:
                    if st.button("🟢 Buy", key=f"t1_buy_{sym}_{idx}", use_container_width=True, type="primary"):
                        st.session_state.show_buy_modal = sym
                        st.session_state.modal_row_data = row
                        st.rerun()
                elif in_hold:
                    st.markdown('<span style="font-size:.72rem;color:#818cf8;font-weight:600;">✓ Held</span>', unsafe_allow_html=True)
                else:
                    st.markdown("—")

            with cols[9]:
                if in_hold:
                    if st.button("🔴 Sell", key=f"t1_sell_{sym}_{idx}", use_container_width=True):
                        st.session_state.show_sell_modal = sym
                        st.rerun()
                elif price and direction == "SELL" and not in_hold:
                    if st.button("🔴 Short", key=f"t1_short_{sym}_{idx}", use_container_width=True):
                        st.session_state.show_buy_modal = sym
                        st.session_state.modal_row_data = row
                        st.rerun()
                else:
                    st.markdown("—")

        # ── BUY MODAL ──
        if st.session_state.get("show_buy_modal"):
            sym_m = st.session_state.show_buy_modal
            st.markdown("---")
            st.markdown(f"### 🟢 Buy Dialog — {sym_m.replace('.NS','')}")
            show_buy_modal(sym_m, st.session_state.modal_row_data)

        # ── SELL MODAL ──
        if st.session_state.get("show_sell_modal"):
            sym_m = st.session_state.show_sell_modal
            st.markdown("---")
            st.markdown(f"### 🔴 Sell Dialog — {sym_m.replace('.NS','')}")
            show_sell_modal(sym_m)

        # Export
        st.markdown("---")
        export_rows = [
            {"Symbol": r.get("symbol",""), "Signal": r.get("label",""), "Score": r.get("score",0),
             "Direction": r.get("direction",""), "Price": r.get("price",""),
             "Delivery%": st.session_state.delivery_cache.get(r.get("symbol",""),{}).get("pct",""),
             "Vol Ratio": r.get("vol_ratio",""), "RSI": r.get("rsi",""),
             "SL": r.get("sl_price",""), "Target": r.get("target_price",""),
             "ATR": r.get("atr",""), "Trend": r.get("trend",""), "Regime": r.get("regime","")}
            for r in filtered
        ]
        if export_rows:
            st.download_button("⬇️ Export CSV", pd.DataFrame(export_rows).to_csv(index=False),
                               file_name=f"scan_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                               mime="text/csv", key="t1_csv")


# ══════════════════════════════════════════════════════════
# TAB 2 — PORTFOLIO
# ══════════════════════════════════════════════════════════
with tab2:
    st.markdown("### 📁 Portfolio")

    # Refresh button — re-fetches prices one by one (no batch crash)
    rc1, rc2 = st.columns([2, 5])
    with rc1:
        if st.button("🔄 Refresh Prices", type="primary", key="t2_refresh"):
            with st.spinner("Fetching latest prices…"):
                for sym in list(st.session_state.portfolio.keys()):
                    if st.session_state.portfolio[sym]["qty"] > 0:
                        try:
                            df_r, err_r = fetch_data(sym, "1d", "5d", force=True)
                            if df_r is not None:
                                cache_set(sym, "1d", df_r)
                        except:
                            pass
            st.success("Prices refreshed!")
            st.rerun()
    with rc2:
        show_closed = st.checkbox("Show closed positions", False, key="t2_show_closed")

    open_positions  = {s: p for s, p in st.session_state.portfolio.items() if p["qty"] > 0}
    closed_positions= {s: p for s, p in st.session_state.portfolio.items() if p["qty"] == 0}

    if not st.session_state.portfolio:
        st.info("No positions yet. Use the **Buy** button in Scan Results.")
    else:
        # Open positions
        if open_positions:
            st.markdown("#### 📊 Open Positions")
            total_inv = 0.0
            total_cur = 0.0

            ph = st.columns([2, 1, 1, 1, 1.2, 1.2, 1, 1.2, 1])
            for c, h in zip(ph, ["Symbol","Type","Qty","Avg","Current","Invested","P&L","P&L%","Action"]):
                c.markdown(f"<span style='font-size:.68rem;text-transform:uppercase;color:var(--txt-sub);'>{h}</span>", unsafe_allow_html=True)
            st.markdown("---")

            for sym, pos in open_positions.items():
                cp = get_current_price(sym)
                if cp is None:
                    cp = pos["avg_price"]
                invested  = pos["avg_price"] * pos["qty"]
                current_v = cp * pos["qty"]
                pnl_abs   = current_v - invested
                pnl_pct   = (pnl_abs / invested * 100) if invested > 0 else 0
                total_inv += invested
                total_cur += current_v
                pnl_c  = "#22c55e" if pnl_abs >= 0 else "#ef4444"
                bg_r   = "rgba(34,197,94,.06)" if pnl_abs >= 0 else "rgba(239,68,68,.06)"
                bdr_r  = "#22c55e" if pnl_abs >= 0 else "#ef4444"
                tt     = pos.get("trade_type","Delivery")
                del_pct = st.session_state.delivery_cache.get(sym,{}).get("pct",None)

                pr = st.columns([2, 1, 1, 1, 1.2, 1.2, 1, 1.2, 1])
                with pr[0]:
                    sym_d = sym.replace(".NS","").replace(".BO","")
                    d_badge = f' <span style="font-size:.68rem;color:{"#22c55e" if (del_pct or 0)>=50 else "#f59e0b"};">{del_pct}%Del</span>' if del_pct else ""
                    st.markdown(f'<div style="background:{bg_r};border-left:4px solid {bdr_r};border-radius:8px;padding:6px 10px;"><b>{sym_d}</b>{d_badge}</div>', unsafe_allow_html=True)
                with pr[1]:
                    badge_css = "trade-type-delivery" if "Delivery" in tt else "trade-type-intraday"
                    st.markdown(f'<div style="background:{bg_r};padding:6px 4px;border-radius:8px;"><span class="{badge_css}">{tt[:8]}</span></div>', unsafe_allow_html=True)
                with pr[2]:
                    st.markdown(f'<div style="background:{bg_r};padding:6px 4px;border-radius:8px;">{pos["qty"]}</div>', unsafe_allow_html=True)
                with pr[3]:
                    st.markdown(f'<div style="background:{bg_r};padding:6px 4px;border-radius:8px;">₹{pos["avg_price"]:.2f}</div>', unsafe_allow_html=True)
                with pr[4]:
                    st.markdown(f'<div style="background:{bg_r};padding:6px 4px;border-radius:8px;font-weight:700;">₹{cp:.2f}</div>', unsafe_allow_html=True)
                with pr[5]:
                    st.markdown(f'<div style="background:{bg_r};padding:6px 4px;border-radius:8px;">₹{invested:,.0f}</div>', unsafe_allow_html=True)
                with pr[6]:
                    st.markdown(f'<div style="background:{bg_r};padding:6px 4px;border-radius:8px;color:{pnl_c};font-weight:700;">₹{pnl_abs:+,.0f}</div>', unsafe_allow_html=True)
                with pr[7]:
                    st.markdown(f'<div style="background:{bg_r};padding:6px 4px;border-radius:8px;color:{pnl_c};font-weight:700;">{pnl_pct:+.2f}%</div>', unsafe_allow_html=True)
                with pr[8]:
                    if st.button("Sell", key=f"t2_sell_{sym}", use_container_width=True):
                        st.session_state.show_sell_modal = sym
                        st.rerun()

            total_pnl = total_cur - total_inv
            pnl_c2    = "#22c55e" if total_pnl >= 0 else "#ef4444"
            st.markdown("<br>", unsafe_allow_html=True)
            sc1, sc2, sc3, sc4 = st.columns(4)
            with sc1: st.markdown(f'<div class="stat-box"><div class="val">₹{total_inv:,.0f}</div><div class="lbl">Invested</div></div>', unsafe_allow_html=True)
            with sc2: st.markdown(f'<div class="stat-box"><div class="val">₹{total_cur:,.0f}</div><div class="lbl">Current Value</div></div>', unsafe_allow_html=True)
            with sc3: st.markdown(f'<div class="stat-box"><div class="val" style="color:{pnl_c2}">₹{total_pnl:+,.0f}</div><div class="lbl">Unrealised P&L</div></div>', unsafe_allow_html=True)
            pnl_pct2 = (total_pnl / total_inv * 100) if total_inv > 0 else 0
            with sc4: st.markdown(f'<div class="stat-box"><div class="val" style="color:{pnl_c2}">{pnl_pct2:+.2f}%</div><div class="lbl">Return</div></div>', unsafe_allow_html=True)

        # Sell modal (in portfolio tab)
        if st.session_state.get("show_sell_modal"):
            sym_m = st.session_state.show_sell_modal
            st.markdown("---")
            st.markdown(f"### 🔴 Sell — {sym_m.replace('.NS','')}")
            show_sell_modal(sym_m)

        # Position history
        if open_positions:
            st.markdown("---")
            st.markdown("#### 📋 Transaction History per Position")
            for sym, pos in open_positions.items():
                if pos.get("history"):
                    with st.expander(f"{sym.replace('.NS','')} — {len(pos['history'])} transaction(s)"):
                        hist_df = pd.DataFrame(pos["history"])
                        def style_hist(row):
                            if row.get("action","") == "BUY":
                                return ["background-color:rgba(34,197,94,.08)"] * len(row)
                            return ["background-color:rgba(239,68,68,.08)"] * len(row)
                        st.dataframe(hist_df.style.apply(style_hist, axis=1), use_container_width=True, hide_index=True)

        # Closed positions
        if show_closed and closed_positions:
            st.markdown("---")
            st.markdown("#### 📁 Closed Positions (History)")
            for sym, pos in closed_positions.items():
                if pos.get("history"):
                    with st.expander(f"{sym.replace('.NS','')} — Closed | {len(pos['history'])} transactions"):
                        hist_df = pd.DataFrame(pos["history"])
                        st.dataframe(hist_df, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════
# TAB 3 — TRADE HISTORY
# ══════════════════════════════════════════════════════════
with tab3:
    st.markdown("### 📜 Trade History")
    if st.session_state.trade_history:
        th_df = pd.DataFrame(st.session_state.trade_history)
        tw = [t for t in st.session_state.trade_history if t.get("P&L (₹)",0) > 0]
        tl = [t for t in st.session_state.trade_history if t.get("P&L (₹)",0) <= 0]
        tot_pnl = sum(t.get("P&L (₹)",0) for t in st.session_state.trade_history)
        win_r   = len(tw)/len(st.session_state.trade_history)*100 if st.session_state.trade_history else 0
        avg_w   = sum(t.get("P&L (₹)",0) for t in tw)/len(tw) if tw else 0
        avg_l   = sum(t.get("P&L (₹)",0) for t in tl)/len(tl) if tl else 0
        pf      = abs(sum(t.get("P&L (₹)",0) for t in tw) / sum(t.get("P&L (₹)",0) for t in tl)) if tl and sum(t.get("P&L (₹)",0) for t in tl) != 0 else float("inf")

        ta, tb, tc, td, te = st.columns(5)
        tc_color = "#22c55e" if tot_pnl >= 0 else "#ef4444"
        ta.metric("Total P&L", f"₹{tot_pnl:+,.2f}")
        tb.metric("Trades", len(st.session_state.trade_history))
        tc.metric("Win Rate", f"{win_r:.1f}%")
        td.metric("Profit Factor", f"{pf:.2f}×")
        te.metric("Avg Win / Loss", f"₹{avg_w:,.0f} / ₹{avg_l:,.0f}")

        def style_th(row):
            v = row.get("P&L (₹)",0)
            if v > 0:  return ["background-color:rgba(34,197,94,.08)"] * len(row)
            elif v < 0:return ["background-color:rgba(239,68,68,.08)"] * len(row)
            return [""] * len(row)

        st.dataframe(th_df.style.apply(style_th, axis=1), use_container_width=True, hide_index=True)

        col_a, col_b = st.columns(2)
        with col_a:
            st.download_button("⬇️ Export CSV", th_df.to_csv(index=False),
                               file_name=f"trades_{datetime.now().strftime('%Y%m%d')}.csv",
                               mime="text/csv", key="t3_csv")
        with col_b:
            st.download_button("📓 Export JSON",
                               json.dumps(st.session_state.trade_history, indent=2),
                               file_name=f"journal_{datetime.now().strftime('%Y%m%d')}.json",
                               mime="application/json", key="t3_json")
    else:
        st.info("No closed trades yet.")


# ══════════════════════════════════════════════════════════
# TAB 4 — EQUITY CURVE
# ══════════════════════════════════════════════════════════
with tab4:
    eq_df = pd.DataFrame(st.session_state.equity_curve)
    if not eq_df.empty and len(eq_df) > 1:
        init_cap = st.session_state.initial_capital
        fig_eq = go.Figure()
        fig_eq.add_trace(go.Scatter(x=eq_df["time"], y=eq_df["capital"],
            mode="lines+markers", line=dict(color="#6366f1", width=2.5),
            fill="tozeroy", fillcolor="rgba(99,102,241,.08)", name="Capital"))
        fig_eq.add_hline(y=init_cap, line_dash="dash", line_color="#64748b",
                          annotation_text=f"Initial ₹{init_cap:,.0f}")
        fig_eq.update_layout(title="Equity Curve", template=plotly_tpl, height=380,
                              margin=dict(l=10,r=10,t=40,b=10))
        st.plotly_chart(fig_eq, use_container_width=True)
        # Drawdown
        peak = eq_df["capital"].cummax()
        dd   = ((eq_df["capital"] - peak) / peak * 100)
        fig_dd = go.Figure()
        fig_dd.add_trace(go.Scatter(x=eq_df["time"], y=dd, mode="lines", fill="tozeroy",
            line=dict(color="#ef4444", width=1.5), fillcolor="rgba(239,68,68,.1)", name="Drawdown%"))
        fig_dd.update_layout(title="Drawdown %", template=plotly_tpl, height=220,
                              margin=dict(l=10,r=10,t=40,b=10))
        st.plotly_chart(fig_dd, use_container_width=True)
    else:
        st.info("Run scans to build equity curve data.")


# ══════════════════════════════════════════════════════════
# TAB 5 — WATCHLIST
# ══════════════════════════════════════════════════════════
with tab5:
    st.markdown("### 👁️ Watchlist")
    st.caption("Add any NSE/BSE symbol to track signals, delivery %, and get buy/sell suggestions")

    # Add to watchlist
    wl_col1, wl_col2, wl_col3 = st.columns([2, 1, 1])
    with wl_col1:
        new_wl_sym = st.text_input("Add symbol (e.g. ZOMATO, NIFTY50)", placeholder="ZOMATO", key="wl_input").strip().upper()
    with wl_col2:
        if st.button("➕ Add to Watchlist", key="wl_add", type="primary"):
            if new_wl_sym:
                sym_full = new_wl_sym if new_wl_sym.endswith((".NS",".BO")) else new_wl_sym + ".NS"
                if sym_full not in st.session_state.watchlist:
                    st.session_state.watchlist.append(sym_full)
                    save_all()
                    st.success(f"Added {sym_full}")
                    st.rerun()
                else:
                    st.info("Already in watchlist.")
    with wl_col3:
        if st.button("🔄 Refresh Watchlist", key="wl_refresh"):
            with st.spinner("Scanning watchlist…"):
                wl_data = {}
                for sym in st.session_state.watchlist:
                    try:
                        if scan_mode == "Intraday (ORB)":
                            df5,  _ = fetch_data(sym, "5m",  "5d",  force=True)
                            df15, _ = fetch_data(sym, "15m", "5d",  force=True)
                            df1h, _ = fetch_data(sym, "1h",  "5d",  force=True)
                            sig = compute_signal(df5, df15, df1h, mode="Intraday (ORB)", orb_min=orb_minutes, ema_p=ema_period)
                        else:
                            dfd, _ = fetch_data(sym, "1d", "1y",  force=True)
                            dfw, _ = fetch_data(sym, "1wk","2y",  force=True)
                            sig = compute_signal(None, None, None, dfd, dfw, mode="Delivery / Swing", ema_p=ema_period)
                        sig["symbol"] = sym
                        # Delivery %
                        del_pct = get_delivery_pct(sym)
                        sig["delivery_pct"] = del_pct
                        wl_data[sym] = sig
                    except Exception as e:
                        wl_data[sym] = {"symbol": sym, "label": f"❌ Error", "price": None, "score": 0,
                                         "direction": None, "delivery_pct": None, "error": str(e)[:60]}
                st.session_state.watchlist_data = wl_data
            st.success("Watchlist refreshed!")
            st.rerun()

    if not st.session_state.watchlist:
        st.info("Your watchlist is empty. Add symbols using the field above.")
    else:
        st.markdown(f"**{len(st.session_state.watchlist)} symbol(s)** in watchlist")
        wl_data = st.session_state.get("watchlist_data", {})

        for sym in st.session_state.watchlist:
            sig = wl_data.get(sym, {})
            price    = sig.get("price")
            label    = sig.get("label", "⏳ Not scanned")
            score    = sig.get("score", 0)
            direction= sig.get("direction", None)
            del_pct  = sig.get("delivery_pct", None)
            vol_r    = sig.get("vol_ratio", None)
            rsi_v    = sig.get("rsi", None)
            trend    = sig.get("trend", None)
            regime   = sig.get("regime", "—")

            # Suggestion text
            if direction == "BUY" and score >= 65:
                if del_pct and del_pct >= 50:
                    suggest = "🟢 Strong candidate for DELIVERY buying — High score + high delivery"
                elif del_pct and del_pct >= 30:
                    suggest = "🟡 Good for SWING — Moderate delivery, solid signal"
                else:
                    suggest = "⚡ Intraday candidate — Low delivery, buy signal present"
            elif direction == "BUY" and score >= 45:
                suggest = "🟡 Weak buy — Watch for confirmation"
            elif direction == "SELL" and score >= 65:
                suggest = "🔴 Sell/Short candidate — Consider exit or avoid entry"
            elif not sig:
                suggest = "⏳ Click Refresh Watchlist to scan"
            else:
                suggest = "⚪ No clear signal — Monitor"

            sc_color = "#22c55e" if score>=65 else ("#f59e0b" if score>=45 else "#ef4444")
            d_color  = "#22c55e" if (del_pct or 0)>=50 else ("#f59e0b" if (del_pct or 0)>=30 else "#ef4444")

            wl_row = st.columns([2, 1.2, 1, 1.2, 1, 1, 3, 0.8])
            with wl_row[0]:
                sym_d = sym.replace(".NS","").replace(".BO","")
                st.markdown(f'<div class="wl-card"><b style="font-size:.95rem;">{sym_d}</b><div style="font-size:.72rem;color:var(--txt-sub);">{trend or regime}</div></div>', unsafe_allow_html=True)
            with wl_row[1]:
                pc = "#22c55e" if direction=="BUY" else ("#ef4444" if direction=="SELL" else "var(--txt)")
                st.markdown(f'<div class="wl-card" style="color:{pc};font-weight:700;">{"₹"+str(price) if price else "—"}</div>', unsafe_allow_html=True)
            with wl_row[2]:
                st.markdown(f'<div class="wl-card"><span style="font-size:.75rem;">{label}</span><br><span style="color:{sc_color};font-weight:700;font-size:.85rem;">{score}/100</span></div>', unsafe_allow_html=True)
            with wl_row[3]:
                del_txt = f'<span style="color:{d_color};font-weight:700;">{del_pct}%</span>' if del_pct else "—"
                del_sug = "Long-term 🟢" if (del_pct or 0)>=50 else ("Swing 🟡" if (del_pct or 0)>=30 else "Intraday ⚡")
                st.markdown(f'<div class="wl-card">Del: {del_txt}<div style="font-size:.7rem;color:var(--txt-sub);">{del_sug}</div></div>', unsafe_allow_html=True)
            with wl_row[4]:
                vr_c = "#22c55e" if (vol_r or 0)>=1.5 else "var(--txt-sub)"
                st.markdown(f'<div class="wl-card" style="font-size:.82rem;color:{vr_c};">{str(round(vol_r,2))+"×" if vol_r else "—"}</div>', unsafe_allow_html=True)
            with wl_row[5]:
                rsi_c = "#22c55e" if rsi_v and 30<rsi_v<70 else "#ef4444"
                st.markdown(f'<div class="wl-card" style="font-size:.82rem;color:{rsi_c};">RSI {round(rsi_v,0) if rsi_v else "—"}</div>', unsafe_allow_html=True)
            with wl_row[6]:
                st.markdown(f'<div class="wl-card" style="font-size:.78rem;">{suggest}</div>', unsafe_allow_html=True)
            with wl_row[7]:
                if st.button("❌", key=f"wl_del_{sym}", help=f"Remove {sym} from watchlist"):
                    st.session_state.watchlist.remove(sym)
                    if sym in st.session_state.watchlist_data:
                        del st.session_state.watchlist_data[sym]
                    save_all()
                    st.rerun()

        # Export watchlist
        if wl_data:
            wl_export = [
                {"Symbol": s, "Price": d.get("price",""), "Signal": d.get("label",""),
                 "Score": d.get("score",""), "Delivery%": d.get("delivery_pct",""),
                 "Direction": d.get("direction",""), "Vol Ratio": d.get("vol_ratio",""),
                 "RSI": d.get("rsi",""), "Trend": d.get("trend","")}
                for s, d in wl_data.items()
            ]
            st.download_button("⬇️ Export Watchlist CSV", pd.DataFrame(wl_export).to_csv(index=False),
                               file_name=f"watchlist_{datetime.now().strftime('%Y%m%d')}.csv",
                               mime="text/csv", key="wl_export_csv")


# ══════════════════════════════════════════════════════════
# TAB 6 — BACKTESTER (simplified)
# ══════════════════════════════════════════════════════════
with tab6:
    st.markdown("### ⚗️ ORB Backtester")
    bc1, bc2 = st.columns(2)
    with bc1:
        bt_syms = st.multiselect("Symbols", selected_symbols,
                                  default=selected_symbols[:3] if len(selected_symbols)>=3 else selected_symbols,
                                  key="bt_syms")
        bt_orb  = st.number_input("ORB Minutes", 5, 60, 15, key="bt_orb")
    with bc2:
        bt_atr_mult = st.slider("ATR Target Mult", 1.0, 4.0, 2.0, 0.5, key="bt_atr")
        bt_sl_mult  = st.slider("ATR SL Mult", 0.5, 3.0, 1.5, 0.25, key="bt_sl")

    if st.button("▶️ Run Backtest", type="primary", key="t6_run"):
        with st.spinner("Running…"):
            all_trades = []
            for sym in bt_syms:
                df5, err = fetch_data(sym, "5m", "1mo", force=False)
                if err or df5 is None or len(df5) < 20:
                    continue
                df5 = add_indicators(df5.copy(), ema_p=ema_period)
                df5.index = pd.to_datetime(df5.index)
                for day in sorted(set(df5.index.date)):
                    grp = df5[df5.index.date == day].copy()
                    if len(grp) < 6:
                        continue
                    grp["_t"] = grp.index.time
                    cutoff = (datetime.combine(day, dtime(9,15)) + timedelta(minutes=int(bt_orb))).time()
                    orb_p  = grp[grp["_t"] <= cutoff]
                    rest   = grp[grp["_t"] > cutoff]
                    if len(orb_p) < 1 or len(rest) < 2:
                        continue
                    orb_h = float(orb_p["High"].max())
                    orb_l = float(orb_p["Low"].min())
                    in_trade = False
                    ep = sl_p = tp = 0.0
                    dirn = ""
                    for _, row_r in rest.iterrows():
                        cl  = float(row_r["Close"])
                        atr = float(row_r["ATR"]) if not pd.isna(row_r.get("ATR",np.nan)) else 0
                        if not in_trade:
                            if cl > orb_h:
                                dirn="BUY"; ep=cl; sl_p=ep-bt_sl_mult*atr; tp=ep+bt_atr_mult*atr; in_trade=True
                            elif cl < orb_l:
                                dirn="SELL"; ep=cl; sl_p=ep+bt_sl_mult*atr; tp=ep-bt_atr_mult*atr; in_trade=True
                        else:
                            hit_sl  = (dirn=="BUY" and cl<=sl_p) or (dirn=="SELL" and cl>=sl_p)
                            hit_tgt = (dirn=="BUY" and cl>=tp)   or (dirn=="SELL" and cl<=tp)
                            if hit_sl or hit_tgt:
                                pnl_pt = (cl-ep) if dirn=="BUY" else (ep-cl)
                                all_trades.append({"symbol":sym,"day":str(day),"direction":dirn,
                                                   "entry":round(ep,2),"exit":round(cl,2),
                                                   "pnl":round(pnl_pt,2),"reason":"TGT" if hit_tgt else "SL"})
                                in_trade = False
                    if in_trade:
                        cl2 = float(rest["Close"].iloc[-1])
                        pnl_pt = (cl2-ep) if dirn=="BUY" else (ep-cl2)
                        all_trades.append({"symbol":sym,"day":str(day),"direction":dirn,
                                           "entry":round(ep,2),"exit":round(cl2,2),
                                           "pnl":round(pnl_pt,2),"reason":"EOD"})

        if all_trades:
            bt_df   = pd.DataFrame(all_trades)
            bt_wins = bt_df[bt_df["pnl"] > 0]
            bt_loss = bt_df[bt_df["pnl"] <= 0]
            wr_bt   = len(bt_wins)/len(bt_df)*100
            pf_bt   = abs(bt_wins["pnl"].sum()/bt_loss["pnl"].sum()) if bt_loss["pnl"].sum() != 0 else float("inf")
            pnl_tot = bt_df["pnl"].sum()
            pc      = "#22c55e" if pnl_tot > 0 else "#ef4444"

            ba, bb, bc3, bd = st.columns(4)
            with ba: st.markdown(f'<div class="stat-box"><div class="val">{len(bt_df)}</div><div class="lbl">Total Trades</div></div>', unsafe_allow_html=True)
            with bb: st.markdown(f'<div class="stat-box"><div class="val" style="color:{pc}">₹{pnl_tot:,.1f}</div><div class="lbl">Total P&L (pts)</div></div>', unsafe_allow_html=True)
            with bc3: st.markdown(f'<div class="stat-box"><div class="val">{wr_bt:.1f}%</div><div class="lbl">Win Rate</div></div>', unsafe_allow_html=True)
            with bd: st.markdown(f'<div class="stat-box"><div class="val">{pf_bt:.2f}×</div><div class="lbl">Profit Factor</div></div>', unsafe_allow_html=True)

            bt_df["Cumulative"] = bt_df["pnl"].cumsum()
            fig_bt = go.Figure()
            fig_bt.add_trace(go.Scatter(x=list(range(len(bt_df))), y=bt_df["Cumulative"],
                mode="lines+markers", fill="tozeroy", line=dict(color="#6366f1", width=2.5),
                fillcolor="rgba(99,102,241,.1)"))
            fig_bt.add_hline(y=0, line_dash="dash", line_color="#64748b")
            fig_bt.update_layout(title="Cumulative P&L (points)", template=plotly_tpl, height=320,
                                  margin=dict(l=10,r=10,t=40,b=10))
            st.plotly_chart(fig_bt, use_container_width=True)
            st.dataframe(bt_df, use_container_width=True, hide_index=True)
        else:
            st.warning("No trades generated — try different symbols or parameters.")


# ══════════════════════════════════════════════════════════
# TAB 7 — ERROR LOG
# ══════════════════════════════════════════════════════════
with tab7:
    if st.session_state.error_log:
        st.dataframe(pd.DataFrame(st.session_state.error_log), use_container_width=True, hide_index=True)
        st.info("Common causes: Market closed, wrong suffix (.NS/.BO), Yahoo Finance rate limiting. Wait a minute and try again.")
        if st.button("🧹 Clear Errors", key="t7_clear"):
            st.session_state.error_log = []
            st.rerun()
    else:
        st.success("✅ No errors.")

    st.markdown("---")
    st.markdown("##### 🗄️ Cache Status")
    cache_rows = []
    now_t = time.time()
    for k, v in list(st.session_state.fetch_cache.items()):
        age  = int(now_t - v["ts"])
        itv  = k.rsplit("_",1)[-1]
        ttl  = _cache_ttl(itv)
        cache_rows.append({"Key":k, "Age(s)":age, "TTL(s)":ttl,
                            "Rows":len(v["df"]) if v["df"] is not None else 0,
                            "Status":"✅ Fresh" if age<ttl else "⏰ Stale"})
    if cache_rows:
        st.dataframe(pd.DataFrame(cache_rows), use_container_width=True, hide_index=True)
    if st.button("🗑️ Clear Cache", key="t7_cache"):
        st.session_state.fetch_cache = {}
        st.rerun()

    st.markdown("---")
    st.markdown("**v6 Changelog:** Buy/Sell modal dialogs · Intraday/Delivery trade type selection · Delivery % estimation · Portfolio history per symbol · Watchlist with signal scanning · Fixed portfolio refresh · Trade history preserved cross-session")
