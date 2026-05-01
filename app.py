"""
Alpha Intraday Pro - AI-Powered Intraday Trading System for NSE India
====================================================================
ENHANCEMENTS OVER ORIGINAL:
- Intraday mode: 5-min, 15-min candles (yfinance "1d" period, 5m/15m intervals)
- VWAP calculation (key intraday indicator)
- Opening Range Breakout (ORB) strategy
- Supertrend indicator
- Pre-market gap analysis
- Intraday risk management: auto SL at 1.5% (tight), targets at 1:2 R:R
- Real-time P&L per trade with MTM
- Session timer (market opens 9:15, closes 15:30 IST)
- Position sizing calculator (risk 1% of capital per trade)
- Momentum scanner (top gainers/losers at open)
- Squareoff reminder at 15:10 IST
- Trade journal with auto-tagging (ORB, Breakout, Momentum, Reversal)
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import concurrent.futures
import json
import os
import time
from datetime import datetime, timedelta
import pytz
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Alpha Intraday Pro",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="⚡"
)

IST = pytz.timezone("Asia/Kolkata")

# ─────────────────────────────────────────────
# CUSTOM CSS — Dark terminal aesthetic
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600;700&family=Rajdhani:wght@400;500;600;700&display=swap');

:root {
    --bg:       #080c14;
    --card:     #0d1117;
    --border:   #1a2233;
    --accent:   #00e5ff;
    --green:    #00ff88;
    --red:      #ff3b55;
    --yellow:   #ffc107;
    --purple:   #b388ff;
    --text:     #ccd6f6;
    --muted:    #495670;
    --card2:    #111827;
}
html, body, [class*="css"] {
    font-family: 'Rajdhani', sans-serif;
    background: var(--bg) !important;
    color: var(--text) !important;
}
.stApp { background: var(--bg) !important; }
#MainMenu, footer, header { visibility: hidden; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: var(--card); border-radius:8px; padding:3px; border:1px solid var(--border);
}
.stTabs [data-baseweb="tab"] {
    color: var(--muted) !important;
    font-family: 'JetBrains Mono', monospace; font-size:11px; letter-spacing:0.04em;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #00e5ff22, #00ff8822) !important;
    color: var(--accent) !important; border-radius:6px;
    border: 1px solid var(--accent) !important;
}

/* Buttons */
.stButton>button {
    background: linear-gradient(135deg, #00e5ff, #0099bb) !important;
    color: #000 !important; border:none !important; border-radius:6px !important;
    font-family: 'JetBrains Mono', monospace !important; font-weight:700 !important;
    font-size:11px !important; letter-spacing:0.06em !important; padding:8px 14px !important;
    transition: all 0.2s !important;
}
.stButton>button:hover { transform:translateY(-1px) !important; box-shadow:0 4px 18px rgba(0,229,255,0.3) !important; }

/* Card */
.icard {
    background: var(--card); border:1px solid var(--border);
    border-radius:10px; padding:14px 18px; margin-bottom:10px;
}
.icard.buy-card  { border-left: 3px solid var(--green); }
.icard.sell-card { border-left: 3px solid var(--red); }
.icard.warn-card { border-left: 3px solid var(--yellow); }

/* Mini metrics */
.mmb {
    background: rgba(0,229,255,0.04); border:1px solid var(--border);
    border-radius:8px; padding:10px 12px; text-align:center;
}
.mmb .lbl { font-family:'JetBrains Mono',monospace; font-size:9px; color:var(--muted); letter-spacing:0.1em; text-transform:uppercase; }
.mmb .val { font-size:16px; font-weight:700; margin-top:3px; }

/* Pill */
.pill { display:inline-block; padding:2px 8px; border-radius:4px; font-family:'JetBrains Mono',monospace; font-size:10px; margin:2px; }
.pg { background:rgba(0,255,136,0.1); color:#00ff88; }
.pr { background:rgba(255,59,85,0.1);  color:#ff3b55; }
.py { background:rgba(255,193,7,0.1);  color:#ffc107; }
.pb { background:rgba(0,229,255,0.1);  color:#00e5ff; }
.pp { background:rgba(179,136,255,0.1);color:#b388ff; }

/* Score bar */
.sbb { background:var(--border); border-radius:3px; height:5px; width:100%; margin-top:5px; }
.sbf { height:5px; border-radius:3px; }

/* Hero */
.hero { font-family:'Rajdhani',sans-serif; font-size:30px; font-weight:700; letter-spacing:0.02em; }
.mono { font-family:'JetBrains Mono',monospace; }
.accent { color:var(--accent); }
.green  { color:var(--green); }
.red    { color:var(--red); }
.divider { border:none; border-top:1px solid var(--border); margin:14px 0; }

/* Alert box */
.alert-box {
    border-radius:8px; padding:10px 16px; margin:8px 0;
    font-family:'JetBrains Mono',monospace; font-size:12px;
}
.alert-green { background:rgba(0,255,136,0.08); border:1px solid rgba(0,255,136,0.25); color:#00ff88; }
.alert-red   { background:rgba(255,59,85,0.08);  border:1px solid rgba(255,59,85,0.25);  color:#ff3b55; }
.alert-blue  { background:rgba(0,229,255,0.08);  border:1px solid rgba(0,229,255,0.25);  color:#00e5ff; }
.alert-yellow{ background:rgba(255,193,7,0.08);  border:1px solid rgba(255,193,7,0.25);  color:#ffc107; }

/* Timer */
.timer-box {
    background: var(--card2); border:1px solid var(--accent);
    border-radius:10px; padding:12px 20px; text-align:center;
    box-shadow: 0 0 20px rgba(0,229,255,0.08);
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PERSISTENCE
# ─────────────────────────────────────────────
DB_FILE = "alpha_intraday_db.json"

def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE) as f:
            return json.load(f)
    return {"intraday_trades": [], "closed_trades": [], "watchlist": [], "capital": 100000}

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

if 'db' not in st.session_state:
    st.session_state.db = load_data()

# ─────────────────────────────────────────────
# MARKET TIME HELPERS
# ─────────────────────────────────────────────
def get_ist_now():
    return datetime.now(IST)

def market_status():
    now = get_ist_now()
    open_time  = now.replace(hour=9,  minute=15, second=0, microsecond=0)
    close_time = now.replace(hour=15, minute=30, second=0, microsecond=0)
    sq_time    = now.replace(hour=15, minute=10, second=0, microsecond=0)
    if now < open_time:
        return "PRE-MARKET", (open_time - now).seconds
    elif now > close_time:
        return "CLOSED", 0
    elif now >= sq_time:
        return "SQUAREOFF", (close_time - now).seconds
    else:
        return "LIVE", (close_time - now).seconds

def fmt_seconds(s):
    h, r = divmod(s, 3600)
    m, sec = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"

# ─────────────────────────────────────────────
# POSITION SIZING
# ─────────────────────────────────────────────
def calc_position_size(capital, cmp, sl, risk_pct=1.0):
    """Risk 1% of capital per trade"""
    risk_amt = capital * risk_pct / 100
    risk_per_share = cmp - sl
    if risk_per_share <= 0:
        return 0, 0
    qty = int(risk_amt / risk_per_share)
    invested = qty * cmp
    return qty, round(invested, 2)

# ─────────────────────────────────────────────
# TECHNICAL INDICATORS
# ─────────────────────────────────────────────
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(com=period-1, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).ewm(com=period-1, min_periods=period).mean()
    return 100 - (100 / (1 + gain / loss))

def compute_vwap(df):
    """VWAP = cumulative (Price * Volume) / cumulative Volume"""
    typical = (df['High'] + df['Low'] + df['Close']) / 3
    cum_pv = (typical * df['Volume']).cumsum()
    cum_v  = df['Volume'].cumsum()
    return cum_pv / cum_v

def compute_supertrend(df, period=10, multiplier=3.0):
    """Supertrend indicator"""
    try:
        hl2 = (df['High'] + df['Low']) / 2
        h_l = df['High'] - df['Low']
        h_pc = abs(df['High'] - df['Close'].shift(1))
        l_pc = abs(df['Low']  - df['Close'].shift(1))
        tr = pd.concat([h_l, h_pc, l_pc], axis=1).max(axis=1)
        atr = tr.ewm(span=period).mean()

        upper = hl2 + multiplier * atr
        lower = hl2 - multiplier * atr

        supertrend = pd.Series(index=df.index, dtype=float)
        direction  = pd.Series(index=df.index, dtype=int)

        for i in range(1, len(df)):
            if df['Close'].iloc[i] > upper.iloc[i-1]:
                direction.iloc[i] = 1   # Bullish
            elif df['Close'].iloc[i] < lower.iloc[i-1]:
                direction.iloc[i] = -1  # Bearish
            else:
                direction.iloc[i] = direction.iloc[i-1]

            if direction.iloc[i] == 1:
                supertrend.iloc[i] = lower.iloc[i]
            else:
                supertrend.iloc[i] = upper.iloc[i]

        return supertrend, direction
    except:
        return pd.Series(dtype=float), pd.Series(dtype=int)

def compute_macd(series):
    ema12 = series.ewm(span=12).mean()
    ema26 = series.ewm(span=26).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    return macd, signal

def compute_atr(df, period=14):
    h_l  = df['High'] - df['Low']
    h_pc = abs(df['High'] - df['Close'].shift(1))
    l_pc = abs(df['Low']  - df['Close'].shift(1))
    tr   = pd.concat([h_l, h_pc, l_pc], axis=1).max(axis=1)
    return tr.ewm(span=period).mean()

# ─────────────────────────────────────────────
# OPENING RANGE BREAKOUT (ORB)
# ─────────────────────────────────────────────
def get_opening_range(ticker, orb_minutes=15):
    """Get first N-minute high/low as breakout levels"""
    try:
        df = yf.download(ticker, period="1d", interval="5m", progress=False, auto_adjust=True)
        if df.empty or len(df) < 3:
            return None, None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # Market open = 9:15 IST
        df.index = pd.to_datetime(df.index).tz_convert(IST)
        today = get_ist_now().date()
        today_data = df[df.index.date == today]
        
        if today_data.empty:
            return None, None
        
        n_candles = orb_minutes // 5
        orb_data = today_data.iloc[:n_candles]
        
        orb_high = float(orb_data['High'].max())
        orb_low  = float(orb_data['Low'].min())
        return round(orb_high, 2), round(orb_low, 2)
    except:
        return None, None

# ─────────────────────────────────────────────
# PRE-MARKET GAP ANALYSIS
# ─────────────────────────────────────────────
def get_gap_data(ticker):
    """Compute gap up/down from yesterday's close"""
    try:
        df = yf.download(ticker, period="2d", interval="1d", progress=False, auto_adjust=True)
        if df.empty or len(df) < 2:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        prev_close = float(df['Close'].iloc[-2])
        today_open = float(df['Open'].iloc[-1])
        gap_pct = round(((today_open - prev_close) / prev_close) * 100, 2)
        return {"prev_close": prev_close, "today_open": today_open, "gap_pct": gap_pct}
    except:
        return None

# ─────────────────────────────────────────────
# INTRADAY MULTI-FACTOR SCORE
# ─────────────────────────────────────────────
def analyze_intraday(ticker, orb_minutes=15, capital=100000):
    """
    Intraday scoring (100 pts total):
    - VWAP Position       : 20
    - Supertrend Signal   : 20
    - Volume Surge        : 20
    - RSI Momentum        : 15
    - MACD Cross          : 15
    - ORB Signal          : 10
    """
    try:
        # 5-min data for today
        df5 = yf.download(ticker, period="1d", interval="5m", progress=False, auto_adjust=True)
        if df5.empty or len(df5) < 10:
            return None
        if isinstance(df5.columns, pd.MultiIndex):
            df5.columns = df5.columns.get_level_values(0)

        df5.index = pd.to_datetime(df5.index).tz_convert(IST)

        cmp = float(df5['Close'].iloc[-1])
        score = 0
        signals = []
        strategy_tags = []

        # ── 1. VWAP ──
        vwap = compute_vwap(df5)
        vwap_val = float(vwap.iloc[-1])
        vwap_dist = ((cmp - vwap_val) / vwap_val) * 100

        if cmp > vwap_val and vwap_dist < 1.5:
            score += 20
            signals.append(("Above VWAP ✓", "green"))
            strategy_tags.append("VWAP Long")
        elif cmp > vwap_val:
            score += 12
            signals.append(("Above VWAP", "green"))
        elif cmp < vwap_val and vwap_dist > -0.5:
            score += 8
            signals.append(("Near VWAP", "yellow"))
        else:
            score -= 5
            signals.append(("Below VWAP", "red"))

        # ── 2. Supertrend ──
        st_line, st_dir = compute_supertrend(df5)
        if not st_dir.empty and len(st_dir.dropna()) > 0:
            last_dir = int(st_dir.dropna().iloc[-1]) if not st_dir.dropna().empty else 0
            prev_dir = int(st_dir.dropna().iloc[-2]) if len(st_dir.dropna()) > 1 else last_dir

            if last_dir == 1 and prev_dir == -1:
                score += 20
                signals.append(("ST Crossover↑🔥", "green"))
                strategy_tags.append("Supertrend Buy")
            elif last_dir == 1:
                score += 12
                signals.append(("ST Bullish", "green"))
            elif last_dir == -1 and prev_dir == 1:
                score -= 10
                signals.append(("ST Crossover↓", "red"))
            else:
                score -= 5
                signals.append(("ST Bearish", "red"))

        # ── 3. Volume Surge ──
        avg_vol_5 = float(df5['Volume'].iloc[:-1].mean()) if len(df5) > 1 else 1
        cur_vol   = float(df5['Volume'].iloc[-1])
        vol_ratio = round(cur_vol / avg_vol_5 if avg_vol_5 > 0 else 0, 2)

        if vol_ratio >= 3.0:
            score += 20
            signals.append((f"Vol {vol_ratio}x🚀", "green"))
        elif vol_ratio >= 2.0:
            score += 14
            signals.append((f"Vol {vol_ratio}x", "green"))
        elif vol_ratio >= 1.3:
            score += 8
            signals.append((f"Vol {vol_ratio}x", "yellow"))
        elif vol_ratio < 0.7:
            score -= 5
            signals.append(("Dead Vol", "red"))

        # ── 4. RSI Momentum ──
        rsi = compute_rsi(df5['Close'])
        rsi_val = float(rsi.iloc[-1]) if not rsi.empty else 50

        if 55 <= rsi_val <= 70:
            score += 15
            signals.append((f"RSI {rsi_val:.0f} ✓", "green"))
        elif 70 < rsi_val <= 80:
            score += 8
            signals.append((f"RSI {rsi_val:.0f}", "yellow"))
        elif rsi_val > 80:
            score -= 5
            signals.append((f"RSI {rsi_val:.0f} OB!", "red"))
        elif 45 <= rsi_val < 55:
            score += 6
            signals.append((f"RSI {rsi_val:.0f}", "yellow"))
        else:
            score -= 3
            signals.append((f"RSI {rsi_val:.0f}", "red"))

        # ── 5. MACD on 5-min ──
        macd_l, sig_l = compute_macd(df5['Close'])
        if len(macd_l) >= 2:
            m_cur, m_prev = float(macd_l.iloc[-1]), float(macd_l.iloc[-2])
            s_cur, s_prev = float(sig_l.iloc[-1]),  float(sig_l.iloc[-2])

            if m_cur > s_cur and m_prev <= s_prev:
                score += 15
                signals.append(("MACD X↑", "green"))
                strategy_tags.append("MACD Crossover")
            elif m_cur > s_cur:
                score += 9
                signals.append(("MACD Bull", "green"))
            else:
                score -= 4
                signals.append(("MACD Bear", "red"))

        # ── 6. ORB Signal ──
        orb_h, orb_l = get_opening_range(ticker, orb_minutes)
        orb_signal = None
        if orb_h and orb_l:
            if cmp > orb_h:
                score += 10
                signals.append(("ORB Breakout↑", "green"))
                strategy_tags.append("ORB Long")
                orb_signal = "LONG"
            elif cmp < orb_l:
                score -= 5
                signals.append(("ORB Breakdown↓", "red"))
                orb_signal = "SHORT_AVOID"
            else:
                signals.append(("Inside ORB", "yellow"))
                orb_signal = "INSIDE"

        total_score = min(max(score, 0), 100)

        if total_score < 40:
            return None  # Not worth trading

        # ── Risk Management ──
        atr_series = compute_atr(df5)
        atr_val = float(atr_series.iloc[-1]) if not atr_series.empty else cmp * 0.005

        # Tight intraday SL: max(1.5%, 1x ATR)
        sl_atr  = round(cmp - atr_val, 2)
        sl_pct  = round(cmp * 0.985, 2)   # 1.5%
        sl      = max(sl_atr, sl_pct)      # tighter of the two

        # Target: 1:2 R:R minimum
        risk    = cmp - sl
        target1 = round(cmp + 2 * risk, 2)  # 1:2
        target2 = round(cmp + 3 * risk, 2)  # 1:3

        # Gap data
        gap_data = get_gap_data(ticker)

        # Position sizing
        qty, invested = calc_position_size(capital, cmp, sl)

        # Grade
        if total_score >= 75:   grade, gcls = "ELITE SETUP", "green"
        elif total_score >= 58: grade, gcls = "STRONG",      "blue"
        elif total_score >= 42: grade, gcls = "MODERATE",    "yellow"
        else:                   grade, gcls = "WEAK",        "red"

        return {
            "ticker":        ticker.replace(".NS", ""),
            "cmp":           round(cmp, 2),
            "total_score":   total_score,
            "grade":         grade,
            "grade_cls":     gcls,
            "sl":            round(sl, 2),
            "target1":       target1,
            "target2":       target2,
            "risk":          round(risk, 2),
            "rr":            "1:2 / 1:3",
            "qty":           qty,
            "invested":      invested,
            "vwap":          round(vwap_val, 2),
            "vwap_dist":     round(vwap_dist, 2),
            "rsi":           round(rsi_val, 1),
            "vol_ratio":     vol_ratio,
            "orb_high":      orb_h,
            "orb_low":       orb_l,
            "orb_signal":    orb_signal,
            "atr":           round(atr_val, 2),
            "gap":           gap_data,
            "signals":       signals,
            "strategy_tags": list(set(strategy_tags)) if strategy_tags else ["Intraday Momentum"],
        }

    except Exception as e:
        return None

# ─────────────────────────────────────────────
# TICKERS
# ─────────────────────────────────────────────
NIFTY_50 = [
    'RELIANCE','TCS','HDFCBANK','ICICIBANK','INFY','SBIN','BHARTIARTL',
    'KOTAKBANK','LT','AXISBANK','WIPRO','HCLTECH','ASIANPAINT','MARUTI',
    'TITAN','BAJFINANCE','SUNPHARMA','NESTLEIND','POWERGRID','TECHM',
    'ONGC','NTPC','COALINDIA','HINDALCO','TATASTEEL','JSWSTEEL','GRASIM',
    'ULTRACEMCO','DRREDDY','CIPLA','DIVISLAB','APOLLOHOSP','ADANIENT',
    'ADANIPORTS','BAJAJFINSV','BRITANNIA','EICHERMOT','HEROMOTOCO',
    'HINDUNILVR','ITC','M&M','TATAMOTORS','TATACONSUM','BPCL',
    'SHREECEM','PIDILITIND','HAVELLS','DABUR','BERGEPAINT','VEDL'
]

MIDCAP_PICKS = [
    'ABCAPITAL','ABFRL','APLAPOLLO','ASTRAL','BALKRISIND','BANDHANBNK',
    'CANBK','CHOLAFIN','COFORGE','CROMPTON','DEEPAKNTR','DIXON','ESCORTS',
    'FEDERALBNK','GLENMARK','GMRINFRA','GNFC','GUJGASLTD','HFCL',
    'HINDPETRO','IDFCFIRSTB','INDHOTEL','INDIAMART','INOXWIND','IRCTC',
    'JKCEMENT','JUBLFOOD','KALYANKJIL','KPITTECH','LALPATHLAB','LAURUSLABS',
    'LICHSGFIN','MARICO','MFSL','MPHASIS','MRF','NAVINFLUOR','NAUKRI',
    'OBEROIRLTY','OFSS','PEL','PERSISTENT','PETRONET','PIIND','POLYCAB',
    'RECLTD','SAILINDLTD','SBICARD','STARHEALTH','TATACOMM','TRENT','UPL',
    'VOLTAS','ZYDUSLIFE'
]

@st.cache_data(ttl=3600)
def get_universe(mode):
    if mode == "Nifty 50":    return [f"{s}.NS" for s in NIFTY_50]
    if mode == "Midcap":      return [f"{s}.NS" for s in MIDCAP_PICKS]
    if mode == "Combined":    return [f"{s}.NS" for s in NIFTY_50 + MIDCAP_PICKS]
    return [f"{s}.NS" for s in NIFTY_50]

# ─────────────────────────────────────────────
# RENDER HELPERS
# ─────────────────────────────────────────────
def pills(signals):
    css_map = {"green":"pg","red":"pr","yellow":"py","blue":"pb","purple":"pp"}
    return "".join(f'<span class="pill {css_map.get(c,"pb")}">{lbl}</span>' for lbl, c in signals[:10])

def sbar(val, mx, color):
    pct = min(int(val/mx*100), 100)
    return f'<div class="sbb"><div class="sbf" style="width:{pct}%;background:{color};"></div></div>'

def color_val(val, inv=False):
    if val is None: return "#6b7280"
    return "#00ff88" if (val>=0) != inv else "#ff3b55"

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
h1, h2 = st.columns([3,1])
with h1:
    mstatus, msecs = market_status()
    status_color = {"LIVE":"#00ff88","PRE-MARKET":"#ffc107","CLOSED":"#ff3b55","SQUAREOFF":"#ff3b55"}.get(mstatus,"#6b7280")
    st.markdown(f"""
    <div class="hero">Alpha Intraday <span class="accent">Pro</span></div>
    <div class="mono" style="font-size:11px;color:#495670;letter-spacing:0.08em;">
    NSE INDIA · REAL-TIME · AI-POWERED · VWAP + ORB + SUPERTREND
    </div>
    """, unsafe_allow_html=True)

with h2:
    now_ist = get_ist_now().strftime("%d %b %Y  %H:%M:%S")
    st.markdown(f"""
    <div class="timer-box">
    <div class="mono" style="font-size:10px;color:#495670;">{now_ist} IST</div>
    <div class="mono" style="font-size:16px;font-weight:700;color:{status_color};margin-top:4px;">● {mstatus}</div>
    <div class="mono" style="font-size:11px;color:#495670;">{fmt_seconds(msecs) if msecs else '–'} remaining</div>
    </div>
    """, unsafe_allow_html=True)

# Squareoff warning
if mstatus == "SQUAREOFF":
    st.markdown("""<div class="alert-box alert-red">
    ⚠️ SQUAREOFF TIME — Market closes in under 20 minutes. Close all open intraday positions NOW!
    </div>""", unsafe_allow_html=True)
elif mstatus == "CLOSED":
    st.markdown("""<div class="alert-box alert-yellow">
    🔔 Market is CLOSED. Use this time to plan tomorrow's trades.
    </div>""", unsafe_allow_html=True)

st.markdown("<hr class='divider'>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Intraday Config")
    capital = st.number_input("Trading Capital (₹)", min_value=10000, max_value=10000000,
                               value=st.session_state.db.get("capital", 100000), step=10000)
    st.session_state.db["capital"] = capital
    save_data(st.session_state.db)

    universe_mode = st.selectbox("Universe", ["Nifty 50", "Midcap", "Combined"])
    orb_minutes   = st.selectbox("ORB Window", [15, 30], index=0)
    max_workers   = st.slider("Parallel Workers", 10, 30, 20)
    min_score     = st.slider("Min Score", 35, 80, 45)
    risk_pct      = st.slider("Risk % per Trade", 0.5, 3.0, 1.0, step=0.25)

    st.markdown("---")
    st.markdown("""
    <div class="mono" style="font-size:10px;color:#495670;line-height:2;">
    📊 SCORE BREAKDOWN<br>
    VWAP POSITION  /20<br>
    SUPERTREND     /20<br>
    VOLUME SURGE   /20<br>
    RSI MOMENTUM   /15<br>
    MACD CROSS     /15<br>
    ORB SIGNAL     /10<br>
    ──────────────<br>
    TOTAL          /100
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div class="mono" style="font-size:10px;color:#495670;line-height:1.9;">
    🛡️ RISK RULES<br>
    • SL = 1.5% or 1x ATR (tighter)<br>
    • Target = 1:2 and 1:3 R:R<br>
    • Max 3 concurrent trades<br>
    • Squareoff by 15:10<br>
    • 1% capital risk per trade<br>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    # Live portfolio snapshot
    open_trades = st.session_state.db.get("intraday_trades", [])
    if open_trades:
        st.markdown("### 💼 Open Trades")
        for t in open_trades:
            try:
                lp = yf.Ticker(f"{t['ticker']}.NS").fast_info['last_price']
                pnl = (lp - t['buy_price']) * t['qty']
                c = "#00ff88" if pnl >= 0 else "#ff3b55"
                st.markdown(f"""
                <div class="mono" style="font-size:11px;display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #1a2233;">
                <span>{t['ticker']}</span><span style="color:{c};">₹{pnl:+.0f}</span>
                </div>
                """, unsafe_allow_html=True)
            except: pass

# ─────────────────────────────────────────────
# MAIN TABS
# ─────────────────────────────────────────────
tabs = st.tabs(["⚡ Intraday Scanner", "📊 ORB Dashboard", "💼 Open Trades", "📜 Trade Journal", "🧮 Position Sizer"])

# ══════════════════════════════════════════════
# TAB 1: INTRADAY SCANNER
# ══════════════════════════════════════════════
with tabs[0]:
    st.markdown("#### ⚡ AI Intraday Scanner — VWAP + Supertrend + ORB")

    c1, c2, c3 = st.columns([2,1,1])
    with c1:
        run_scan = st.button("🚀 Run Intraday Scan", use_container_width=True)
    with c2:
        sort_by = st.selectbox("Sort", ["Score","RSI","Vol Ratio"])
    with c3:
        show_n = st.selectbox("Top N", [10,20,30], index=0)

    if mstatus == "CLOSED":
        st.markdown("""<div class="alert-box alert-yellow">
        ⏰ Market closed. Scan will use last available data for planning tomorrow's setups.
        </div>""", unsafe_allow_html=True)

    if run_scan:
        tickers = get_universe(universe_mode)
        results = []
        prog = st.progress(0, text="Scanning...")
        total = len(tickers)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(analyze_intraday, t, orb_minutes, capital): t for t in tickers}
            done = 0
            for f in concurrent.futures.as_completed(futures):
                r = f.result()
                if r and r['total_score'] >= min_score:
                    results.append(r)
                done += 1
                prog.progress(done/total, text=f"Scanned {done}/{total} — {len(results)} setups found")

        prog.empty()

        sk = {"Score":"total_score","RSI":"rsi","Vol Ratio":"vol_ratio"}[sort_by]
        results.sort(key=lambda x: x[sk], reverse=True)
        st.session_state.scan_results = results

        if results:
            st.markdown(f"""<div class="alert-box alert-green">
            ✅ Scan complete — {len(results)} intraday setups found
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""<div class="alert-box alert-yellow">
            No setups found. Lower min score or try different universe.
            </div>""", unsafe_allow_html=True)

    if 'scan_results' in st.session_state and st.session_state.scan_results:
        for res in st.session_state.scan_results[:show_n]:
            gmap = {"green":"#00ff88","blue":"#00e5ff","yellow":"#ffc107","red":"#ff3b55"}
            gc   = gmap.get(res['grade_cls'],"#6b7280")

            tag_html = "".join(f'<span class="pill pp">{t}</span>' for t in res['strategy_tags'])
            gap      = res.get('gap')
            gap_html = ""
            if gap:
                gc2 = "#00ff88" if gap['gap_pct'] >= 0 else "#ff3b55"
                gap_html = f'Gap: <span style="color:{gc2};">{gap["gap_pct"]:+.2f}%</span>'

            with st.expander(
                f"[{res['total_score']}/100] {res['ticker']}  |  {res['grade']}  |  CMP ₹{res['cmp']}  |  SL ₹{res['sl']}  |  T1 ₹{res['target1']}",
                expanded=res['total_score'] >= 70
            ):
                # Strategy tags
                st.markdown(f"{tag_html} {gap_html}", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)

                # Score bars
                s1,s2,s3 = st.columns(3)
                with s1:
                    st.markdown(f"""<div class="mmb">
                    <div class="lbl">TOTAL SCORE</div>
                    <div class="val" style="color:{gc};">{res['total_score']}/100</div>
                    {sbar(res['total_score'],100,gc)}
                    </div>""", unsafe_allow_html=True)
                with s2:
                    vwap_c = "#00ff88" if res['vwap_dist'] >= 0 else "#ff3b55"
                    st.markdown(f"""<div class="mmb">
                    <div class="lbl">VWAP</div>
                    <div class="val" style="color:{vwap_c};">₹{res['vwap']}</div>
                    <div class="mono" style="font-size:10px;color:{vwap_c};">{res['vwap_dist']:+.2f}%</div>
                    </div>""", unsafe_allow_html=True)
                with s3:
                    st.markdown(f"""<div class="mmb">
                    <div class="lbl">VOL SURGE</div>
                    <div class="val" style="color:#00e5ff;">{res['vol_ratio']}x</div>
                    {sbar(min(res['vol_ratio'],5),5,'#00e5ff')}
                    </div>""", unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # Trade levels
                m1,m2,m3,m4,m5,m6 = st.columns(6)
                m1.metric("Entry (CMP)", f"₹{res['cmp']}")
                m2.metric("Stop Loss",   f"₹{res['sl']}",     f"-{round((res['cmp']-res['sl'])/res['cmp']*100,1)}%", delta_color="off")
                m3.metric("Target 1",    f"₹{res['target1']}", f"+{round((res['target1']-res['cmp'])/res['cmp']*100,1)}%")
                m4.metric("Target 2",    f"₹{res['target2']}", f"+{round((res['target2']-res['cmp'])/res['cmp']*100,1)}%")
                m5.metric("Qty (1% risk)", str(res['qty']))
                m6.metric("Invested",    f"₹{res['invested']}")

                st.markdown("<hr class='divider'>", unsafe_allow_html=True)

                cl, cr = st.columns([3,2])
                with cl:
                    st.markdown('<div class="mono" style="font-size:10px;color:#495670;letter-spacing:0.1em;">SIGNALS</div>', unsafe_allow_html=True)
                    st.markdown(pills(res['signals']), unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)
                    tc1,tc2,tc3,tc4 = st.columns(4)
                    tc1.metric("RSI", res['rsi'])
                    tc2.metric("ATR", f"₹{res['atr']}")
                    if res['orb_high']:
                        tc3.metric("ORB High", f"₹{res['orb_high']}")
                        tc4.metric("ORB Low",  f"₹{res['orb_low']}")

                with cr:
                    st.markdown(f"""
                    <div class="mono" style="font-size:11px;line-height:2;color:#8892a4;">
                    Risk per trade: <b style="color:#ff3b55;">₹{round(res['risk']*res['qty'],2)}</b><br>
                    Potential P&L T1: <b style="color:#00ff88;">₹{round((res['target1']-res['cmp'])*res['qty'],2)}</b><br>
                    Potential P&L T2: <b style="color:#00ff88;">₹{round((res['target2']-res['cmp'])*res['qty'],2)}</b><br>
                    R:R Ratio: <b style="color:#00e5ff;">{res['rr']}</b>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                b1,b2,b3 = st.columns([2,1,1])
                with b1:
                    if st.button(f"✅ Buy {res['ticker']} @ ₹{res['cmp']} — Qty {res['qty']}", key=f"ibuy_{res['ticker']}"):
                        open_trades = st.session_state.db.get("intraday_trades", [])
                        if len(open_trades) >= 3:
                            st.error("Max 3 simultaneous intraday trades. Close one first.")
                        else:
                            entry = {
                                "ticker":    res['ticker'],
                                "buy_price": res['cmp'],
                                "sl":        res['sl'],
                                "target1":   res['target1'],
                                "target2":   res['target2'],
                                "qty":       res['qty'],
                                "score":     res['total_score'],
                                "tags":      res['strategy_tags'],
                                "vwap":      res['vwap'],
                                "orb_high":  res['orb_high'],
                                "time":      get_ist_now().strftime("%H:%M:%S"),
                                "date":      get_ist_now().strftime("%Y-%m-%d"),
                            }
                            st.session_state.db["intraday_trades"].append(entry)
                            save_data(st.session_state.db)
                            st.toast(f"✅ Trade opened: {res['ticker']} x{res['qty']}", icon="🚀")
                with b2:
                    if st.button("📊 Chart", key=f"ch_{res['ticker']}"):
                        st.link_button("Open Chart", f"https://finance.yahoo.com/chart/{res['ticker']}.NS")
                with b3:
                    rr_text = f"Entry: ₹{res['cmp']} | SL: ₹{res['sl']} | T1: ₹{res['target1']} | T2: ₹{res['target2']}"
                    st.code(rr_text, language=None)

# ══════════════════════════════════════════════
# TAB 2: ORB DASHBOARD
# ══════════════════════════════════════════════
with tabs[1]:
    st.markdown("#### 📊 Opening Range Breakout Dashboard")
    st.markdown("""
    <div class="mono" style="font-size:11px;color:#495670;margin-bottom:16px;">
    ORB = First 15/30 min high/low. Breakout above = BUY. Breakdown below = AVOID/SHORT.
    </div>
    """, unsafe_allow_html=True)

    orb_tickers_input = st.text_input("Tickers to track (comma-separated)", value="RELIANCE,TCS,INFY,SBIN,HDFCBANK")
    orb_scan_btn = st.button("📊 Fetch ORB Levels", use_container_width=False)

    if orb_scan_btn and orb_tickers_input:
        orb_list = [t.strip().upper() for t in orb_tickers_input.split(",")]
        orb_results = []

        with st.spinner("Fetching ORB levels..."):
            def get_orb_row(sym):
                ticker = f"{sym}.NS"
                orb_h, orb_l = get_opening_range(ticker, 15)
                try:
                    t = yf.Ticker(ticker)
                    cmp = round(t.fast_info['last_price'], 2)
                except:
                    cmp = None

                if orb_h and cmp:
                    if cmp > orb_h:     status, sc = "🟢 BREAKOUT", "green"
                    elif cmp < orb_l:   status, sc = "🔴 BREAKDOWN", "red"
                    else:               status, sc = "🟡 INSIDE ORB","yellow"
                    dist_h = round(((cmp - orb_h) / orb_h) * 100, 2)
                else:
                    status, sc, dist_h = "–", "muted", None

                return {"Symbol": sym, "CMP": cmp, "ORB High": orb_h, "ORB Low": orb_l,
                        "Status": status, "Dist from ORB High%": dist_h}

            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
                orb_results = list(ex.map(get_orb_row, orb_list))

        df_orb = pd.DataFrame(orb_results)
        st.dataframe(df_orb, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("**💡 ORB Strategy Rules:**")
        st.markdown("""
        <div class="mono" style="font-size:11px;color:#8892a4;line-height:2;">
        ✅ BREAKOUT: CMP > ORB High → BUY with SL below ORB Low. Target = 2x ORB range above ORB High<br>
        ❌ BREAKDOWN: CMP < ORB Low → AVOID longs. Short traders can target 2x ORB range below ORB Low<br>
        ⏸️ INSIDE ORB: Wait for breakout. Don't trade yet.
        </div>
        """, unsafe_allow_html=True)

# ══════════════════════════════════════════════
# TAB 3: OPEN TRADES
# ══════════════════════════════════════════════
with tabs[2]:
    open_trades = st.session_state.db.get("intraday_trades", [])
    st.markdown("#### 💼 Open Intraday Positions")

    if mstatus == "SQUAREOFF" and open_trades:
        st.markdown("""<div class="alert-box alert-red">
        ⚠️ SQUAREOFF ALERT — Close all positions before 15:30!
        </div>""", unsafe_allow_html=True)

    if not open_trades:
        st.info("No open intraday positions. Run scanner and buy a setup.")
    else:
        def fetch_live(t):
            try:
                return round(yf.Ticker(f"{t['ticker']}.NS").fast_info['last_price'], 2)
            except:
                return t['buy_price']

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
            live_prices = list(ex.map(fetch_live, open_trades))

        total_pnl = sum((lp - t['buy_price']) * t['qty'] for t, lp in zip(open_trades, live_prices))
        pnl_color = "#00ff88" if total_pnl >= 0 else "#ff3b55"

        sm1,sm2,sm3 = st.columns(3)
        sm1.metric("Open Trades", len(open_trades))
        sm2.metric("Session P&L", f"₹{round(total_pnl,2)}", f"{'▲' if total_pnl>=0 else '▼'} Today")
        sm3.metric("Risk Exposure", f"₹{sum(t['buy_price']*t['qty'] for t in open_trades):,.0f}")

        st.markdown("<hr class='divider'>", unsafe_allow_html=True)

        for i, (t, lp) in enumerate(zip(open_trades, live_prices)):
            pnl     = round((lp - t['buy_price']) * t['qty'], 2)
            pnl_pct = round(((lp - t['buy_price']) / t['buy_price']) * 100, 2)
            pc      = "#00ff88" if pnl >= 0 else "#ff3b55"

            sl_hit  = lp <= t['sl']
            t1_hit  = lp >= t['target1']
            t2_hit  = lp >= t['target2']

            if sl_hit:
                st.markdown(f'<div class="alert-box alert-red">⚠️ {t["ticker"]} SL HIT — Exit NOW @ ₹{lp}</div>', unsafe_allow_html=True)
            elif t2_hit:
                st.markdown(f'<div class="alert-box alert-green">🎯 {t["ticker"]} TARGET 2 HIT — Book full profit @ ₹{lp}</div>', unsafe_allow_html=True)
            elif t1_hit:
                st.markdown(f'<div class="alert-box alert-green">🎯 {t["ticker"]} Target 1 hit — Trail SL or book 50% @ ₹{lp}</div>', unsafe_allow_html=True)

            with st.container(border=True):
                c1,c2,c3,c4,c5 = st.columns([2,2,3,2,1])

                c1.markdown(f"""
                <div style="font-family:'Rajdhani',sans-serif;font-weight:700;font-size:22px;color:{pc};">{t['ticker']}</div>
                <div class="mono" style="font-size:10px;color:#495670;">
                {''.join(f'<span class="pill pp">{tg}</span>' for tg in t.get('tags',[]))}
                </div>
                """, unsafe_allow_html=True)

                c2.metric("Live Price", f"₹{lp}", f"{pnl_pct:+.2f}%")
                c3.markdown(f"""
                <div class="mono" style="font-size:11px;line-height:2;">
                Buy: <b>₹{t['buy_price']}</b> × {t['qty']} shares &nbsp;|&nbsp; {t['time']} IST<br>
                SL: <b style="color:#ff3b55;">₹{t['sl']}</b> &nbsp;|&nbsp; T1: <b style="color:#00ff88;">₹{t['target1']}</b> &nbsp;|&nbsp; T2: <b style="color:#00ff88;">₹{t['target2']}</b><br>
                VWAP: ₹{t.get('vwap','–')} &nbsp;|&nbsp; Score: {t['score']}
                </div>
                """, unsafe_allow_html=True)

                c4.metric("P&L", f"₹{pnl}", f"{pnl_pct:+.2f}%")

                with c5:
                    if st.button("Exit", key=f"exit_{i}"):
                        closed = st.session_state.db["intraday_trades"].pop(i)
                        pnl_r = round((lp - closed['buy_price']) * closed['qty'], 2)
                        pnl_p = round(((lp - closed['buy_price']) / closed['buy_price']) * 100, 2)
                        closed.update({
                            "sell_price": lp,
                            "pnl":        pnl_r,
                            "pnl_pct":    pnl_p,
                            "exit_time":  get_ist_now().strftime("%H:%M:%S"),
                            "outcome":    "WIN" if pnl_r > 0 else "LOSS",
                        })
                        st.session_state.db["closed_trades"].append(closed)
                        save_data(st.session_state.db)
                        st.rerun()

# ══════════════════════════════════════════════
# TAB 4: TRADE JOURNAL
# ══════════════════════════════════════════════
with tabs[3]:
    closed = st.session_state.db.get("closed_trades", [])
    st.markdown("#### 📜 Intraday Trade Journal")

    if not closed:
        st.info("No closed trades yet.")
    else:
        df = pd.DataFrame(closed)

        total_pnl  = round(df['pnl'].sum(), 2)
        wins       = (df['pnl'] > 0).sum()
        losses     = (df['pnl'] <= 0).sum()
        win_rate   = round(wins / len(df) * 100, 1)
        avg_win    = round(df[df['pnl']>0]['pnl'].mean(), 2) if wins else 0
        avg_loss   = round(df[df['pnl']<=0]['pnl'].mean(), 2) if losses else 0
        profit_factor = round(abs(df[df['pnl']>0]['pnl'].sum() / (df[df['pnl']<=0]['pnl'].sum() or 1)), 2)
        expectancy = round((win_rate/100 * avg_win) + ((1-win_rate/100) * avg_loss), 2)

        h1,h2,h3,h4,h5,h6 = st.columns(6)
        h1.metric("Total P&L",      f"₹{total_pnl}", delta=total_pnl)
        h2.metric("Win Rate",       f"{win_rate}%",  f"{wins}W / {losses}L")
        h3.metric("Avg Win",        f"₹{avg_win}")
        h4.metric("Avg Loss",       f"₹{avg_loss}")
        h5.metric("Profit Factor",  profit_factor)
        h6.metric("Expectancy/Trade",f"₹{expectancy}")

        st.markdown("<hr class='divider'>", unsafe_allow_html=True)

        # Group by strategy tag
        if 'tags' in df.columns:
            st.markdown("**P&L by Strategy:**")
            tag_pnl = {}
            for _, row in df.iterrows():
                for tag in (row.get('tags') or ['Unknown']):
                    tag_pnl[tag] = tag_pnl.get(tag, 0) + row['pnl']
            tc = st.columns(len(tag_pnl))
            for i, (tag, pnl) in enumerate(tag_pnl.items()):
                tc[i].metric(tag, f"₹{round(pnl,2)}", delta=round(pnl,2))
            st.markdown("---")

        cols = [c for c in ['ticker','date','time','buy_price','sell_price','qty','pnl','pnl_pct','outcome','exit_time'] if c in df.columns]
        df_disp = df[cols].copy()
        df_disp.columns = [c.upper() for c in df_disp.columns]

        def style_row(val):
            if isinstance(val, (int,float)):
                return f'color:{"#00ff88" if val>0 else "#ff3b55"}'
            return ''

        pnl_cols = [c for c in ['PNL','PNL_PCT'] if c in df_disp.columns]
        st.dataframe(df_disp.style.applymap(style_row, subset=pnl_cols),
                     use_container_width=True, hide_index=True)

        csv = df_disp.to_csv(index=False)
        st.download_button("⬇️ Export Journal CSV", csv, "intraday_journal.csv", "text/csv")

        if st.button("🗑️ Clear Journal"):
            st.session_state.db["closed_trades"] = []
            save_data(st.session_state.db)
            st.rerun()

# ══════════════════════════════════════════════
# TAB 5: POSITION SIZER
# ══════════════════════════════════════════════
with tabs[4]:
    st.markdown("#### 🧮 Intraday Position Size Calculator")
    st.markdown("""
    <div class="mono" style="font-size:11px;color:#495670;margin-bottom:16px;">
    Uses fixed fractional method: Risk exactly N% of capital per trade. Keeps you alive long-term.
    </div>
    """, unsafe_allow_html=True)

    ps1,ps2 = st.columns(2)
    with ps1:
        p_capital  = st.number_input("Capital (₹)",  value=float(capital), step=10000.0)
        p_entry    = st.number_input("Entry Price (₹)", value=1000.0, step=1.0)
        p_sl       = st.number_input("Stop Loss (₹)",   value=985.0,  step=0.5)
        p_target   = st.number_input("Target Price (₹)", value=1030.0, step=1.0)
        p_risk_pct = st.slider("Risk %", 0.5, 3.0, 1.0, step=0.25)

    with ps2:
        if p_entry > p_sl > 0:
            risk_per_share = p_entry - p_sl
            qty = int((p_capital * p_risk_pct / 100) / risk_per_share)
            invested  = round(qty * p_entry, 2)
            max_loss  = round(qty * risk_per_share, 2)
            pot_profit= round(qty * (p_target - p_entry), 2)
            rr        = round((p_target - p_entry) / risk_per_share, 2) if risk_per_share > 0 else 0
            sl_pct    = round(((p_entry - p_sl)   / p_entry) * 100, 2)
            tgt_pct   = round(((p_target - p_entry) / p_entry) * 100, 2)

            ok_rr  = rr >= 2.0
            ok_sl  = sl_pct <= 2.0
            ok_inv = invested <= p_capital * 0.25

            st.markdown(f"""
            <div class="icard">
            <div class="mono" style="font-size:13px;line-height:2.2;">
            📦 Quantity: &nbsp;&nbsp;<b style="color:#00e5ff;font-size:18px;">{qty} shares</b><br>
            💰 Invested: &nbsp;<b>₹{invested:,.2f}</b>
                {'<span class="pill pg">✓ &lt;25% capital</span>' if ok_inv else '<span class="pill pr">⚠ &gt;25% capital</span>'}<br>
            📉 Max Loss: &nbsp;<b style="color:#ff3b55;">₹{max_loss:,.2f}</b> ({p_risk_pct}% of capital)<br>
            📈 Pot. Profit: <b style="color:#00ff88;">₹{pot_profit:,.2f}</b> ({tgt_pct:+.2f}%)<br>
            ⚖️ R:R Ratio: &nbsp;<b style="color:#{'00ff88' if ok_rr else 'ffc107'};">1 : {rr}</b>
                {'<span class="pill pg">✓ Good R:R</span>' if ok_rr else '<span class="pill py">⚠ R:R &lt; 2</span>'}<br>
            🛑 SL %: &nbsp;&nbsp;&nbsp;&nbsp;<b>{sl_pct}%</b>
                {'<span class="pill pg">✓ Tight SL</span>' if ok_sl else '<span class="pill py">⚠ Wide SL</span>'}
            </div>
            </div>
            """, unsafe_allow_html=True)

            if not ok_rr:
                st.markdown('<div class="alert-box alert-yellow">⚠️ R:R below 2:1 — Move target higher or entry lower for better odds.</div>', unsafe_allow_html=True)
            if not ok_inv:
                st.markdown('<div class="alert-box alert-yellow">⚠️ Investing more than 25% of capital in one trade — reduce qty.</div>', unsafe_allow_html=True)
        else:
            st.warning("Entry price must be above Stop Loss.")

    st.markdown("---")
    st.markdown("""
    **💡 Golden Rules for Intraday Profitability:**

    <div class="mono" style="font-size:11px;color:#8892a4;line-height:2.2;">
    1. Never risk more than 1–2% of capital on any single trade<br>
    2. Minimum R:R of 1:2 before entering any trade<br>
    3. Max 3 open intraday trades simultaneously<br>
    4. ALWAYS squareoff by 15:10 — no overnight intraday positions<br>
    5. Trail SL to cost once T1 is hit<br>
    6. If daily loss > 3% of capital — STOP trading for the day<br>
    7. Trade with the trend: VWAP + Supertrend must agree<br>
    8. High volume = conviction — low volume breakouts often fail<br>
    9. Avoid trading within 15 min of open (9:15–9:30) unless ORB setup<br>
    10. Journal every trade — patterns reveal your edge over time
    </div>
    """, unsafe_allow_html=True)
