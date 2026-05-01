"""
Alpha Intraday Pro v2 - AI-Powered Intraday Trading System for NSE India
========================================================================
Universe: Small Cap | Mid Cap | Large Cap | Any combination
Indicators: VWAP · Supertrend · ORB · RSI · MACD · ATR · Volume Surge
Risk Mgmt : 1% capital risk per trade · 1:2 R:R minimum · Auto SL · Squareoff alert
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import concurrent.futures
import json
import os
from datetime import datetime
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
# CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600;700&family=Rajdhani:wght@400;500;600;700&display=swap');
:root {
    --bg:#080c14; --card:#0d1117; --border:#1a2233;
    --accent:#00e5ff; --green:#00ff88; --red:#ff3b55;
    --yellow:#ffc107; --purple:#b388ff; --text:#ccd6f6; --muted:#495670; --card2:#111827;
}
html,body,[class*="css"]{ font-family:'Rajdhani',sans-serif; background:var(--bg)!important; color:var(--text)!important; }
.stApp{ background:var(--bg)!important; }
#MainMenu,footer,header{ visibility:hidden; }
.stTabs [data-baseweb="tab-list"]{ background:var(--card); border-radius:8px; padding:3px; border:1px solid var(--border); }
.stTabs [data-baseweb="tab"]{ color:var(--muted)!important; font-family:'JetBrains Mono',monospace; font-size:11px; letter-spacing:0.04em; }
.stTabs [aria-selected="true"]{ background:linear-gradient(135deg,#00e5ff22,#00ff8822)!important; color:var(--accent)!important; border-radius:6px; border:1px solid var(--accent)!important; }
.stButton>button{ background:linear-gradient(135deg,#00e5ff,#0099bb)!important; color:#000!important; border:none!important; border-radius:6px!important; font-family:'JetBrains Mono',monospace!important; font-weight:700!important; font-size:11px!important; letter-spacing:0.06em!important; padding:8px 14px!important; transition:all 0.2s!important; }
.stButton>button:hover{ transform:translateY(-1px)!important; box-shadow:0 4px 18px rgba(0,229,255,0.3)!important; }
.icard{ background:var(--card); border:1px solid var(--border); border-radius:10px; padding:14px 18px; margin-bottom:10px; }
.icard.buy-card{ border-left:3px solid var(--green); }
.mmb{ background:rgba(0,229,255,0.04); border:1px solid var(--border); border-radius:8px; padding:10px 12px; text-align:center; }
.mmb .lbl{ font-family:'JetBrains Mono',monospace; font-size:9px; color:var(--muted); letter-spacing:0.1em; text-transform:uppercase; }
.mmb .val{ font-size:16px; font-weight:700; margin-top:3px; }
.pill{ display:inline-block; padding:2px 8px; border-radius:4px; font-family:'JetBrains Mono',monospace; font-size:10px; margin:2px; }
.pg{ background:rgba(0,255,136,0.1); color:#00ff88; }
.pr{ background:rgba(255,59,85,0.1); color:#ff3b55; }
.py{ background:rgba(255,193,7,0.1); color:#ffc107; }
.pb{ background:rgba(0,229,255,0.1); color:#00e5ff; }
.pp{ background:rgba(179,136,255,0.1); color:#b388ff; }
.po{ background:rgba(255,165,0,0.1); color:#ffa500; }
.sbb{ background:var(--border); border-radius:3px; height:5px; width:100%; margin-top:5px; }
.sbf{ height:5px; border-radius:3px; }
.hero{ font-family:'Rajdhani',sans-serif; font-size:30px; font-weight:700; letter-spacing:0.02em; }
.mono{ font-family:'JetBrains Mono',monospace; }
.accent{ color:var(--accent); }
.divider{ border:none; border-top:1px solid var(--border); margin:14px 0; }
.alert-box{ border-radius:8px; padding:10px 16px; margin:8px 0; font-family:'JetBrains Mono',monospace; font-size:12px; }
.alert-green{ background:rgba(0,255,136,0.08); border:1px solid rgba(0,255,136,0.25); color:#00ff88; }
.alert-red{ background:rgba(255,59,85,0.08); border:1px solid rgba(255,59,85,0.25); color:#ff3b55; }
.alert-yellow{ background:rgba(255,193,7,0.08); border:1px solid rgba(255,193,7,0.25); color:#ffc107; }
.timer-box{ background:var(--card2); border:1px solid var(--accent); border-radius:10px; padding:12px 20px; text-align:center; box-shadow:0 0 20px rgba(0,229,255,0.08); }
.uni-badge{ display:inline-flex; align-items:center; gap:6px; padding:4px 12px; border-radius:20px; font-family:'JetBrains Mono',monospace; font-size:10px; font-weight:700; letter-spacing:0.05em; margin:2px; }
.uni-large{ background:rgba(0,229,255,0.12); color:#00e5ff; border:1px solid rgba(0,229,255,0.3); }
.uni-mid{   background:rgba(179,136,255,0.12); color:#b388ff; border:1px solid rgba(179,136,255,0.3); }
.uni-small{ background:rgba(255,165,0,0.12); color:#ffa500; border:1px solid rgba(255,165,0,0.3); }
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
    return {"intraday_trades": [], "closed_trades": [], "capital": 100000}

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

if "db" not in st.session_state:
    st.session_state.db = load_data()

# ─────────────────────────────────────────────
# MARKET TIME
# ─────────────────────────────────────────────
def get_ist_now():
    return datetime.now(IST)

def market_status():
    now    = get_ist_now()
    open_t = now.replace(hour=9,  minute=15, second=0, microsecond=0)
    close_t= now.replace(hour=15, minute=30, second=0, microsecond=0)
    sq_t   = now.replace(hour=15, minute=10, second=0, microsecond=0)
    if now < open_t:
        return "PRE-MARKET", int((open_t - now).total_seconds())
    elif now > close_t:
        return "CLOSED", 0
    elif now >= sq_t:
        return "SQUAREOFF", int((close_t - now).total_seconds())
    else:
        return "LIVE", int((close_t - now).total_seconds())

def fmt_seconds(s):
    h, r = divmod(s, 3600)
    m, sec = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"

# ─────────────────────────────────────────────
# NSE UNIVERSE — 3 Cap Categories
# ─────────────────────────────────────────────

# ── LARGE CAP: Nifty 50 + Nifty Next 50 ──
LARGE_CAP = [
    "RELIANCE","TCS","HDFCBANK","ICICIBANK","INFY","SBIN","BHARTIARTL",
    "KOTAKBANK","LT","AXISBANK","WIPRO","HCLTECH","ASIANPAINT","MARUTI",
    "TITAN","BAJFINANCE","SUNPHARMA","NESTLEIND","POWERGRID","TECHM",
    "ONGC","NTPC","COALINDIA","HINDALCO","TATASTEEL","JSWSTEEL","GRASIM",
    "ULTRACEMCO","DRREDDY","CIPLA","DIVISLAB","APOLLOHOSP","ADANIENT",
    "ADANIPORTS","BAJAJFINSV","BRITANNIA","EICHERMOT","HEROMOTOCO",
    "HINDUNILVR","ITC","M&M","TATAMOTORS","TATACONSUM","BPCL","VEDL",
    "SHREECEM","PIDILITIND","HAVELLS","DABUR","BERGEPAINT",
    # Nifty Next 50
    "ADANIGREEN","ADANIPOWER","AMBUJACEM","BANKBARODA","BEL","BHEL",
    "BOSCHLTD","CANBK","CHOLAFIN","COLPAL","DMART","GAIL","GODREJCP",
    "GODREJPROP","HAL","HDFCAMC","HDFCLIFE","ICICIPRULI","ICICIGI",
    "INDUSINDBK","IRCTC","JSWENERGY","LICHSGFIN","LICI","LUPIN",
    "MARICO","MUTHOOTFIN","NAUKRI","NHPC","NMDC","OFSS","PFC",
    "RECLTD","SAIL","SBICARD","SBILIFE","SHRIRAMFIN","SIEMENS","SRF",
    "TATAPOWER","TORNTPHARM","TRENT","UPL","ZOMATO","ZYDUSLIFE",
    "INDIGO","PAGEIND","ABCAPITAL","MFSL","BAJAJ-AUTO",
]

# ── MID CAP: Nifty Midcap 100 representative ──
MID_CAP = [
    "APLAPOLLO","ASTRAL","BALKRISIND","BANDHANBNK","BHARATFORG",
    "COFORGE","CROMPTON","CUMMINSIND","DEEPAKNTR","DIXON","ESCORTS",
    "FEDERALBNK","GLENMARK","GMRINFRA","GNFC","GUJGASLTD","HFCL",
    "HINDPETRO","IDFCFIRSTB","INDHOTEL","INDIAMART","INOXWIND",
    "JKCEMENT","JUBLFOOD","KALYANKJIL","KPITTECH","LALPATHLAB",
    "LAURUSLABS","MPHASIS","MRF","NAVINFLUOR","OBEROIRLTY","PEL",
    "PERSISTENT","PETRONET","PIIND","POLYCAB","STARHEALTH",
    "TATACOMM","TIINDIA","TORNTPOWER","TRIDENT","TTKPRESTIG",
    "VGUARD","VOLTAS","WHIRLPOOL","YESBANK","ZEEL","ABFRL",
    "ACC","AJANTPHARM","ALKEM","APOLLOTYRE","ARVIND","ASHOKLEY",
    "ATUL","AUBANK","AUROPHARMA","BATAINDIA","BLUEDART",
    "CASTROLIND","CEATLTD","CENTURYTEX","CHAMBLFERT","CONCOR",
    "CREDITACC","CYIENT","EMAMILTD","ENDURANCE","EQUITASBNK",
    "EXIDEIND","FINCABLES","FLUOROCHEM","FORTIS","GRANULES",
    "GSFC","HINDCOPPER","HUDCO","IDBI","IEX","IFBIND",
    "INDIANB","IOB","ISEC","JBCHEPHARM","JKPAPER","JUBLPHARMA",
    "JUSTDIAL","KALPATPOWR","KANSAINER","KEI","KPRMILL","KRBL",
    "LTIM","LTTS","MANAPPURAM","MAPMYINDIA","MAXHEALTH","MCX",
    "METROPOLIS","MOTILALOFS","NATCOPHARM","NUVOCO","OLECTRA",
    "PHOENIXLTD","PNBHOUSING","POLYMED","PRINCEPIPE","RADICO",
    "RAMCOCEM","RATNAMANI","RITES","ROSSARI","ROUTE","SAPPHIRE",
]

# ── SMALL CAP: Nifty Smallcap picks ──
SMALL_CAP = [
    "AARTIDRUGS","ACCELYA","ACRYSIL","ADFFOODS","AEGISCHEM",
    "AFFLE","ALKYLAMINE","ALLCARGO","ALOKINDS","AMBER","AMRUTANJAN",
    "ANANTRAJ","ANGELONE","ANUPAM","APARINDS","APCOTEXIND",
    "ARMANFIN","ASAHIINDIA","ASTERDM","ASTRAMICRO","AVANTIFEED",
    "AXISCADES","BAFNAPH","BALKRISIND","BARBEQUE","BASF",
    "BAYERCROP","BEML","BIRLACORPN","BLISSGVS","BOMDYEING",
    "BOROLTD","BRIGADE","BSOFT","BUTTERFLY","CAPACITE",
    "CARERATING","CCL","CDSL","CERA","CGCL","CHALET",
    "CHEMFAB","COCHINSHIP","CMSINFO","COSMOFILM","CROWN",
    "CSBBANK","DATAPATTNS","DBCORP","DCBBANK","DEEPAKFERT",
    "DELTACORP","DHANI","DHARMAJ","DHUNSERI","DICIND",
    "DOLLAR","EASEMYTRIP","ECLERX","EIDPARRY","ELGIEQUIP",
    "EMKAY","EMUDHRA","ENKEI","EPIGRAL","ERASMEDIA",
    "ESABINDIA","ESTER","EVERESTEDU","EXCEL","EXICOM",
    "FLAIR","GABRIEL","GAEL","GANDHAR","GARFIBRES",
    "GARWARE","GATEWAY","GENUSPAPER","GLOBUSSPR","GOCOLORS",
    "GODHA","GOLDIAM","GOODLUCK","GOODYEAR","GPPL",
    "GREAVESCOT","GREENPANEL","GREENPLY","GRINDWELL","GUFICBIO",
    "GULFOILLUB","HAPPSTMNDS","HARSHA","HBLPOWER","HIKAL",
    "HIMATSEIDE","HINDWAREAP","HONASA","HTMEDIA","HUHTAMAKI",
    "IBREALEST","IMAGICAA","INDBANK","INDIACEM","INDNIPPON",
    "INDOSTAR","INFOBEAN","INOXGREEN","INTELLECT","INVENTURE",
    "IPCALAB","JAIBALAJI","JAINIRRIG","JAMNAAUTO","JAYNECOIND",
    "JKUMARINFR","JOCIL","KRSNAA","LSIL","MASFIN",
    "MOLDTKPAC","MSTCLTD","NKIND","NOCIL","OCCL",
    "ONMOBILE","ORIENTBELL","ORISSAMINE","PALREDTEC","PARADEEP",
    "PARAS","PCBL","PENIND","PGEL","PLASTIBLENDS",
    "PNBGILTS","POLYMED","PRAKASH","PRICOLLTD","PRINCEPIPE",
    "PRSMJOHNSN","QUESS","RAJESHEXPO","RKFORGE","RUSHIL",
    "RUSTOMJEE","SABEVENTS","SAFARI","SANOFI","SAREGAMA",
    "SATIA","SEQUENT","SHANKARA","SHYAMMETL","SMLISUZU",
    "SNOWMAN","SOLARA","SPANDANA","STOVEKRAFT","SUDARSCHEM",
    "SUMICHEM","SUNDARMFIN","SUPRAJIT","SUPRIYA","SURYAROSNI",
    "SWANENERGY","SWSOLAR","SYMPHONY","TANLA","TARSONS",
    "TATACHEM","TATVA","TECHNOE","TEJASNET","THYROCARE",
    "TIMKEN","TIPSIND","TITAN","TRIVENI","UNIENTER",
    "UNIVASTU","UPL","UTIAMC","VGUARD","VIJAYA",
    "VINATIORGA","VMART","VRLLOG","VSTIND","WABAG",
    "WELCORP","WINDMACHIN","XPROINDIA","ZENSARTECH","ZENTEC",
]

# ─────────────────────────────────────────────
# UNIVERSE BUILDER
# ─────────────────────────────────────────────
def get_universe(modes: list) -> list:
    pool = []
    if "Large Cap" in modes: pool += LARGE_CAP
    if "Mid Cap"   in modes: pool += MID_CAP
    if "Small Cap" in modes: pool += SMALL_CAP
    seen, unique = set(), []
    for s in pool:
        if s not in seen:
            seen.add(s); unique.append(s)
    return [f"{s}.NS" for s in unique]

def get_cap(sym: str) -> str:
    if sym in LARGE_CAP: return "Large Cap"
    if sym in MID_CAP:   return "Mid Cap"
    if sym in SMALL_CAP: return "Small Cap"
    return "Unknown"

def cap_badge_html(cap: str) -> str:
    cls = {"Large Cap":"uni-large","Mid Cap":"uni-mid","Small Cap":"uni-small"}.get(cap,"uni-large")
    return f'<span class="uni-badge {cls}">{cap}</span>'

# ─────────────────────────────────────────────
# POSITION SIZING
# ─────────────────────────────────────────────
def calc_qty(capital, cmp, sl, risk_pct=1.0):
    risk_amt = capital * risk_pct / 100
    risk_per  = cmp - sl
    if risk_per <= 0: return 0, 0
    qty = int(risk_amt / risk_per)
    return qty, round(qty * cmp, 2)

# ─────────────────────────────────────────────
# INDICATORS
# ─────────────────────────────────────────────
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(com=period-1, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).ewm(com=period-1, min_periods=period).mean()
    return 100 - (100 / (1 + gain / (loss + 1e-9)))

def compute_vwap(df):
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    return (tp * df["Volume"]).cumsum() / df["Volume"].cumsum()

def compute_atr(df, period=14):
    hl  = df["High"] - df["Low"]
    hpc = (df["High"] - df["Close"].shift(1)).abs()
    lpc = (df["Low"]  - df["Close"].shift(1)).abs()
    tr  = pd.concat([hl, hpc, lpc], axis=1).max(axis=1)
    return tr.ewm(span=period).mean()

def compute_macd(series):
    macd   = series.ewm(span=12).mean() - series.ewm(span=26).mean()
    signal = macd.ewm(span=9).mean()
    return macd, signal

def compute_supertrend(df, period=10, mult=3.0):
    try:
        hl2 = (df["High"] + df["Low"]) / 2
        atr = compute_atr(df, period)
        upper = hl2 + mult * atr
        lower = hl2 - mult * atr
        direction = pd.Series(0, index=df.index, dtype=int)
        for i in range(1, len(df)):
            if   df["Close"].iloc[i] > upper.iloc[i-1]: direction.iloc[i] =  1
            elif df["Close"].iloc[i] < lower.iloc[i-1]: direction.iloc[i] = -1
            else: direction.iloc[i] = direction.iloc[i-1]
        return direction
    except:
        return pd.Series(0, index=df.index, dtype=int)

def get_opening_range(ticker, orb_min=15):
    try:
        df = yf.download(ticker, period="1d", interval="5m",
                         progress=False, auto_adjust=True)
        if df.empty or len(df) < 3: return None, None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.index = pd.to_datetime(df.index).tz_convert(IST)
        today = df[df.index.date == get_ist_now().date()]
        if today.empty: return None, None
        orb = today.iloc[:orb_min // 5]
        return round(float(orb["High"].max()), 2), round(float(orb["Low"].min()), 2)
    except:
        return None, None

def get_gap(ticker):
    try:
        df = yf.download(ticker, period="2d", interval="1d",
                         progress=False, auto_adjust=True)
        if df.empty or len(df) < 2: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        pc = float(df["Close"].iloc[-2])
        to = float(df["Open"].iloc[-1])
        return round(((to - pc) / pc) * 100, 2)
    except:
        return None

# ─────────────────────────────────────────────
# INTRADAY SCORER
# ─────────────────────────────────────────────
def analyze_intraday(ticker, orb_min, capital, risk_pct):
    try:
        df = yf.download(ticker, period="1d", interval="5m",
                         progress=False, auto_adjust=True)
        if df.empty or len(df) < 12: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.index = pd.to_datetime(df.index).tz_convert(IST)

        cmp     = float(df["Close"].iloc[-1])
        score   = 0
        signals = []
        tags    = []

        # ── 1. VWAP (20 pts) ──
        vwap_s   = compute_vwap(df)
        vwap_val = float(vwap_s.iloc[-1])
        vwap_d   = ((cmp - vwap_val) / vwap_val) * 100
        if cmp > vwap_val and vwap_d < 1.5:
            score += 20; signals.append(("Above VWAP ✓","green")); tags.append("VWAP Long")
        elif cmp > vwap_val:
            score += 12; signals.append(("Above VWAP","green"))
        elif abs(vwap_d) < 0.5:
            score += 8;  signals.append(("Near VWAP","yellow"))
        else:
            score -= 5;  signals.append(("Below VWAP","red"))

        # ── 2. Supertrend (20 pts) ──
        st_dir = compute_supertrend(df)
        d_now  = int(st_dir.iloc[-1]) if len(st_dir) >= 1 else 0
        d_prev = int(st_dir.iloc[-2]) if len(st_dir) >= 2 else d_now
        if d_now == 1 and d_prev == -1:
            score += 20; signals.append(("ST Crossover↑🔥","green")); tags.append("Supertrend Buy")
        elif d_now == 1:
            score += 12; signals.append(("ST Bullish","green"))
        elif d_now == -1 and d_prev == 1:
            score -= 10; signals.append(("ST Crossover↓","red"))
        else:
            score -= 5;  signals.append(("ST Bearish","red"))

        # ── 3. Volume Surge (20 pts) ──
        avg_vol = float(df["Volume"].iloc[:-1].mean()) if len(df) > 1 else 1
        cur_vol = float(df["Volume"].iloc[-1])
        vol_r   = round(cur_vol / max(avg_vol, 1), 2)
        if vol_r >= 3.0:
            score += 20; signals.append((f"Vol {vol_r}x 🚀","green"))
        elif vol_r >= 2.0:
            score += 14; signals.append((f"Vol {vol_r}x","green"))
        elif vol_r >= 1.3:
            score += 8;  signals.append((f"Vol {vol_r}x","yellow"))
        elif vol_r < 0.7:
            score -= 5;  signals.append(("Dead Vol","red"))

        # ── 4. RSI (15 pts) ──
        rsi     = compute_rsi(df["Close"])
        rsi_val = float(rsi.iloc[-1]) if not rsi.empty else 50
        if 55 <= rsi_val <= 70:
            score += 15; signals.append((f"RSI {rsi_val:.0f} ✓","green"))
        elif 70 < rsi_val <= 80:
            score += 8;  signals.append((f"RSI {rsi_val:.0f}","yellow"))
        elif rsi_val > 80:
            score -= 5;  signals.append((f"RSI {rsi_val:.0f} OB!","red"))
        elif 45 <= rsi_val < 55:
            score += 6;  signals.append((f"RSI {rsi_val:.0f}","yellow"))
        else:
            score -= 3;  signals.append((f"RSI {rsi_val:.0f}","red"))

        # ── 5. MACD (15 pts) ──
        macd_l, sig_l = compute_macd(df["Close"])
        if len(macd_l) >= 2:
            mc, mp = float(macd_l.iloc[-1]), float(macd_l.iloc[-2])
            sc_, sp = float(sig_l.iloc[-1]),  float(sig_l.iloc[-2])
            if mc > sc_ and mp <= sp:
                score += 15; signals.append(("MACD X↑","green")); tags.append("MACD Cross")
            elif mc > sc_:
                score += 9;  signals.append(("MACD Bull","green"))
            else:
                score -= 4;  signals.append(("MACD Bear","red"))

        # ── 6. ORB (10 pts) ──
        orb_h, orb_l = get_opening_range(ticker, orb_min)
        orb_sig = None
        if orb_h and orb_l:
            if cmp > orb_h:
                score += 10; signals.append(("ORB Breakout↑","green")); tags.append("ORB Long"); orb_sig = "LONG"
            elif cmp < orb_l:
                score -= 5;  signals.append(("ORB Breakdown↓","red")); orb_sig = "AVOID"
            else:
                signals.append(("Inside ORB","yellow")); orb_sig = "INSIDE"

        total = min(max(score, 0), 100)
        if total < 40: return None

        # ── Risk levels ──
        atr_s   = compute_atr(df)
        atr_val = float(atr_s.iloc[-1]) if not atr_s.empty else cmp * 0.005
        sl      = round(max(cmp - atr_val, cmp * 0.985), 2)
        risk    = cmp - sl
        t1      = round(cmp + 2 * risk, 2)
        t2      = round(cmp + 3 * risk, 2)
        qty, invested = calc_qty(capital, cmp, sl, risk_pct)

        sym = ticker.replace(".NS", "")
        if total >= 75:   grade, gcls = "ELITE",    "green"
        elif total >= 58: grade, gcls = "STRONG",   "blue"
        elif total >= 42: grade, gcls = "MODERATE", "yellow"
        else:             grade, gcls = "WEAK",     "red"

        return {
            "ticker":    sym,
            "ticker_ns": ticker,
            "cap":       get_cap(sym),
            "cmp":       round(cmp, 2),
            "score":     total,
            "grade":     grade,
            "gcls":      gcls,
            "sl":        sl,
            "t1":        t1,
            "t2":        t2,
            "risk":      round(risk, 2),
            "qty":       qty,
            "invested":  invested,
            "vwap":      round(vwap_val, 2),
            "vwap_d":    round(vwap_d, 2),
            "rsi":       round(rsi_val, 1),
            "vol_r":     vol_r,
            "atr":       round(atr_val, 2),
            "orb_h":     orb_h,
            "orb_l":     orb_l,
            "orb_sig":   orb_sig,
            "gap":       get_gap(ticker),
            "signals":   signals,
            "tags":      list(set(tags)) if tags else ["Momentum"],
        }
    except:
        return None

# ─────────────────────────────────────────────
# RENDER HELPERS
# ─────────────────────────────────────────────
CSS_MAP = {"green":"pg","red":"pr","yellow":"py","blue":"pb","purple":"pp","orange":"po"}
GRADE_COLOR = {"green":"#00ff88","blue":"#00e5ff","yellow":"#ffc107","red":"#ff3b55"}
CAP_COLOR   = {"Large Cap":"#00e5ff","Mid Cap":"#b388ff","Small Cap":"#ffa500"}
CAP_CLS     = {"Large Cap":"uni-large","Mid Cap":"uni-mid","Small Cap":"uni-small"}

def pills(signals):
    return "".join(
        f'<span class="pill {CSS_MAP.get(c,"pb")}">{lbl}</span>'
        for lbl, c in signals[:10]
    )

def sbar(val, mx, color):
    pct = min(int(val / mx * 100), 100)
    return f'<div class="sbb"><div class="sbf" style="width:{pct}%;background:{color};"></div></div>'

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
h1, h2 = st.columns([3, 1])
with h1:
    st.markdown("""
    <div class="hero">Alpha Intraday <span class="accent">Pro</span></div>
    <div class="mono" style="font-size:11px;color:#495670;letter-spacing:0.08em;">
    NSE INDIA &nbsp;·&nbsp; VWAP + ORB + SUPERTREND &nbsp;·&nbsp;
    <span class="uni-badge uni-large" style="font-size:9px;">LARGE CAP</span>
    <span class="uni-badge uni-mid"   style="font-size:9px;">MID CAP</span>
    <span class="uni-badge uni-small" style="font-size:9px;">SMALL CAP</span>
    </div>
    """, unsafe_allow_html=True)

with h2:
    mstatus, msecs = market_status()
    sc = {"LIVE":"#00ff88","PRE-MARKET":"#ffc107","CLOSED":"#ff3b55","SQUAREOFF":"#ff3b55"}.get(mstatus,"#6b7280")
    st.markdown(f"""
    <div class="timer-box">
    <div class="mono" style="font-size:10px;color:#495670;">{get_ist_now().strftime('%d %b %Y  %H:%M:%S')} IST</div>
    <div class="mono" style="font-size:16px;font-weight:700;color:{sc};margin-top:4px;">● {mstatus}</div>
    <div class="mono" style="font-size:11px;color:#495670;">{fmt_seconds(msecs) if msecs else '–'} remaining</div>
    </div>""", unsafe_allow_html=True)

if mstatus == "SQUAREOFF":
    st.markdown('<div class="alert-box alert-red">⚠️ SQUAREOFF TIME — Market closes in under 20 min. Close ALL intraday positions NOW!</div>', unsafe_allow_html=True)
elif mstatus == "CLOSED":
    st.markdown('<div class="alert-box alert-yellow">🔔 Market CLOSED. Plan tomorrow\'s trades using the scanner in review mode.</div>', unsafe_allow_html=True)

st.markdown("<hr class='divider'>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Scanner Config")

    capital = st.number_input(
        "Trading Capital (₹)", min_value=10000, max_value=10_000_000,
        value=int(st.session_state.db.get("capital", 100000)), step=10000
    )
    st.session_state.db["capital"] = capital
    save_data(st.session_state.db)

    # ── CAP CATEGORY SELECTOR ──
    st.markdown("---")
    st.markdown("### 🏦 Universe Selection")
    st.markdown("""
    <div class="mono" style="font-size:10px;color:#495670;margin-bottom:8px;">
    Select one or more cap categories to scan:
    </div>""", unsafe_allow_html=True)

    use_large = st.checkbox(
        "🔵  Large Cap",
        value=True,
        help="Nifty 50 + Nifty Next 50 (~100 stocks). Most liquid. Tight spreads. Best for beginners."
    )
    st.markdown("""
    <div class="mono" style="font-size:9px;color:#495670;margin:-8px 0 8px 24px;">
    ~100 stocks · High liquidity · Low risk
    </div>""", unsafe_allow_html=True)

    use_mid = st.checkbox(
        "🟣  Mid Cap",
        value=False,
        help="Nifty Midcap 100 stocks. Good momentum plays. Moderate liquidity."
    )
    st.markdown("""
    <div class="mono" style="font-size:9px;color:#495670;margin:-8px 0 8px 24px;">
    ~110 stocks · Moderate liquidity · Medium risk
    </div>""", unsafe_allow_html=True)

    use_small = st.checkbox(
        "🟠  Small Cap",
        value=False,
        help="Nifty Smallcap 250 picks. High momentum but lower liquidity. Advanced traders only."
    )
    st.markdown("""
    <div class="mono" style="font-size:9px;color:#495670;margin:-8px 0 8px 24px;">
    ~150 stocks · Lower liquidity · Higher risk ⚠️
    </div>""", unsafe_allow_html=True)

    # Build selected modes list
    selected_modes = []
    if use_large: selected_modes.append("Large Cap")
    if use_mid:   selected_modes.append("Mid Cap")
    if use_small: selected_modes.append("Small Cap")
    if not selected_modes:
        st.warning("Select at least one category. Defaulting to Large Cap.")
        selected_modes = ["Large Cap"]

    universe_tickers = get_universe(selected_modes)

    # Universe summary card
    lc_n  = len([t for t in universe_tickers if t.replace(".NS","") in LARGE_CAP])
    mc_n  = len([t for t in universe_tickers if t.replace(".NS","") in MID_CAP])
    sc_n  = len([t for t in universe_tickers if t.replace(".NS","") in SMALL_CAP])

    st.markdown(f"""
    <div class="icard" style="margin-top:10px;padding:10px 14px;">
    <div class="mono" style="font-size:10px;color:#495670;margin-bottom:6px;">ACTIVE UNIVERSE</div>
    <div style="font-size:18px;font-weight:700;color:#00e5ff;">{len(universe_tickers)} stocks</div>
    <div style="margin-top:6px;">
    {f'<span class="uni-badge uni-large">Large: {lc_n}</span>' if lc_n else ''}
    {f'<span class="uni-badge uni-mid">Mid: {mc_n}</span>'     if mc_n else ''}
    {f'<span class="uni-badge uni-small">Small: {sc_n}</span>' if sc_n else ''}
    </div>
    </div>""", unsafe_allow_html=True)

    if use_small:
        st.markdown("""
        <div class="alert-box alert-yellow" style="font-size:10px;padding:8px 12px;">
        ⚠️ Small Cap: Use wider SL (+0.5%), smaller qty, and check liquidity before entry.
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    orb_min     = st.selectbox("ORB Window (min)", [15, 30], index=0)
    max_workers = st.slider("Parallel Workers", 10, 40, 20)
    min_score   = st.slider("Min Score Filter", 35, 80, 45)
    risk_pct    = st.slider("Risk % per Trade", 0.5, 3.0, 1.0, step=0.25)

    st.markdown("---")
    st.markdown("""
    <div class="mono" style="font-size:10px;color:#495670;line-height:2;">
    📊 SCORE WEIGHTS<br>
    VWAP POSITION &nbsp;/20<br>
    SUPERTREND &nbsp;&nbsp;&nbsp;/20<br>
    VOLUME SURGE &nbsp;/20<br>
    RSI MOMENTUM &nbsp;/15<br>
    MACD CROSS &nbsp;&nbsp;&nbsp;/15<br>
    ORB SIGNAL &nbsp;&nbsp;&nbsp;/10<br>
    ─────────────<br>
    TOTAL &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;/100
    </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div class="mono" style="font-size:10px;color:#495670;line-height:1.9;">
    🛡️ RISK RULES<br>
    • SL = 1.5% or 1×ATR (tighter)<br>
    • Targets: 1:2 and 1:3 R:R<br>
    • Max 3 concurrent trades<br>
    • Squareoff by 15:10 IST<br>
    • 1% capital risk per trade
    </div>""", unsafe_allow_html=True)

    # Live P&L snapshot
    open_trades = st.session_state.db.get("intraday_trades", [])
    if open_trades:
        st.markdown("---")
        st.markdown("### 💼 Open Trades")
        for t in open_trades:
            try:
                lp  = yf.Ticker(f"{t['ticker']}.NS").fast_info["last_price"]
                pnl = (lp - t["buy_price"]) * t["qty"]
                c   = "#00ff88" if pnl >= 0 else "#ff3b55"
                cap_c = CAP_COLOR.get(t.get("cap","Large Cap"), "#00e5ff")
                st.markdown(f"""
                <div class="mono" style="font-size:11px;display:flex;justify-content:space-between;
                padding:4px 0;border-bottom:1px solid #1a2233;">
                <span style="color:{cap_c};">{t['ticker']}</span>
                <span style="color:{c};">₹{pnl:+.0f}</span>
                </div>""", unsafe_allow_html=True)
            except:
                pass

# ─────────────────────────────────────────────
# MAIN TABS
# ─────────────────────────────────────────────
tabs = st.tabs([
    "⚡ Intraday Scanner",
    "📊 ORB Dashboard",
    "💼 Open Trades",
    "📜 Trade Journal",
    "🧮 Position Sizer"
])

# ══════════════════════════════════════════════
# TAB 1 — INTRADAY SCANNER
# ══════════════════════════════════════════════
with tabs[0]:
    st.markdown("#### ⚡ AI Intraday Scanner")

    # Active universe display
    badge_row = "".join(
        f'<span class="uni-badge {CAP_CLS.get(m,"uni-large")}">{m} ({len([t for t in universe_tickers if t.replace(".NS","") in (LARGE_CAP if m=="Large Cap" else MID_CAP if m=="Mid Cap" else SMALL_CAP)])})</span>'
        for m in selected_modes
    )
    st.markdown(f'<div style="margin-bottom:12px;">Scanning: {badge_row}</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        run_scan = st.button("🚀 Run Intraday Scan", use_container_width=True)
    with c2:
        sort_by = st.selectbox("Sort By", ["Score", "RSI", "Vol Ratio"])
    with c3:
        show_n = st.selectbox("Top N", [10, 20, 30], index=0)

    if run_scan:
        results = []
        prog = st.progress(0, text="Initialising scan…")
        total = len(universe_tickers)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {
                ex.submit(analyze_intraday, t, orb_min, capital, risk_pct): t
                for t in universe_tickers
            }
            done = 0
            for f in concurrent.futures.as_completed(futures):
                r = f.result()
                if r and r["score"] >= min_score:
                    results.append(r)
                done += 1
                prog.progress(done / total,
                              text=f"Scanned {done}/{total} — {len(results)} setups found")

        prog.empty()
        sk = {"Score":"score","RSI":"rsi","Vol Ratio":"vol_r"}[sort_by]
        results.sort(key=lambda x: x[sk], reverse=True)
        st.session_state.scan_results = results

        if results:
            lc = sum(1 for r in results if r["cap"] == "Large Cap")
            mc = sum(1 for r in results if r["cap"] == "Mid Cap")
            sc_ = sum(1 for r in results if r["cap"] == "Small Cap")
            st.markdown(f"""
            <div class="alert-box alert-green">
            ✅ Scan complete — <b>{len(results)}</b> setups found &nbsp;|&nbsp;
            🔵 Large: {lc} &nbsp; 🟣 Mid: {mc} &nbsp; 🟠 Small: {sc_}
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="alert-box alert-yellow">No setups found. Lower min score or add more cap categories.</div>', unsafe_allow_html=True)

    # ── Results display ──
    if "scan_results" in st.session_state and st.session_state.scan_results:

        # Post-scan cap filter
        st.markdown("**Filter displayed results by Cap:**")
        fc1, fc2, fc3 = st.columns(3)
        show_lc = fc1.checkbox("🔵 Large Cap", value=True,  key="fl")
        show_mc = fc2.checkbox("🟣 Mid Cap",   value=True,  key="fm")
        show_sc = fc3.checkbox("🟠 Small Cap", value=True,  key="fs")
        cap_filter = []
        if show_lc: cap_filter.append("Large Cap")
        if show_mc: cap_filter.append("Mid Cap")
        if show_sc: cap_filter.append("Small Cap")

        display = [r for r in st.session_state.scan_results
                   if r["cap"] in cap_filter][:show_n]

        st.markdown(f"""
        <div class="mono" style="font-size:11px;color:#495670;margin-bottom:12px;">
        Showing {len(display)} of {len(st.session_state.scan_results)} results
        </div>""", unsafe_allow_html=True)

        for res in display:
            gc  = GRADE_COLOR.get(res["gcls"], "#6b7280")
            cc  = CAP_COLOR.get(res["cap"], "#6b7280")
            cls = CAP_CLS.get(res["cap"], "uni-large")
            tags_html = "".join(f'<span class="pill pp">{t}</span>' for t in res["tags"])
            gap = res.get("gap")
            gap_html = ""
            if gap is not None:
                gc2 = "#00ff88" if gap >= 0 else "#ff3b55"
                gap_html = f' &nbsp; Gap: <span style="color:{gc2};">{gap:+.2f}%</span>'

            label = (f"[{res['score']}/100]  {res['ticker']}  |  "
                     f"{res['cap']}  |  {res['grade']}  |  "
                     f"CMP ₹{res['cmp']}  |  SL ₹{res['sl']}  |  T1 ₹{res['t1']}")

            with st.expander(label, expanded=res["score"] >= 72):

                st.markdown(
                    f'<span class="uni-badge {cls}">{res["cap"]}</span> {tags_html}{gap_html}',
                    unsafe_allow_html=True
                )
                st.markdown("<br>", unsafe_allow_html=True)

                # Metric tiles
                s1, s2, s3 = st.columns(3)
                with s1:
                    st.markdown(f"""<div class="mmb">
                    <div class="lbl">TOTAL SCORE</div>
                    <div class="val" style="color:{gc};">{res['score']}/100</div>
                    {sbar(res['score'],100,gc)}
                    </div>""", unsafe_allow_html=True)
                with s2:
                    vc = "#00ff88" if res["vwap_d"] >= 0 else "#ff3b55"
                    st.markdown(f"""<div class="mmb">
                    <div class="lbl">VWAP</div>
                    <div class="val" style="color:{vc};">₹{res['vwap']}</div>
                    <div class="mono" style="font-size:10px;color:{vc};">{res['vwap_d']:+.2f}%</div>
                    </div>""", unsafe_allow_html=True)
                with s3:
                    st.markdown(f"""<div class="mmb">
                    <div class="lbl">VOL SURGE</div>
                    <div class="val" style="color:#00e5ff;">{res['vol_r']}x</div>
                    {sbar(min(res['vol_r'],5),5,'#00e5ff')}
                    </div>""", unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                m1,m2,m3,m4,m5,m6 = st.columns(6)
                m1.metric("Entry",   f"₹{res['cmp']}")
                sl_d = round((res['cmp']-res['sl'])/res['cmp']*100,1)
                m2.metric("SL",      f"₹{res['sl']}",  f"-{sl_d}%", delta_color="off")
                t1_u = round((res['t1']-res['cmp'])/res['cmp']*100,1)
                m3.metric("Target 1",f"₹{res['t1']}",  f"+{t1_u}%")
                t2_u = round((res['t2']-res['cmp'])/res['cmp']*100,1)
                m4.metric("Target 2",f"₹{res['t2']}",  f"+{t2_u}%")
                m5.metric(f"Qty ({risk_pct}%)", str(res["qty"]))
                m6.metric("Invested", f"₹{res['invested']:,}")

                st.markdown("<hr class='divider'>", unsafe_allow_html=True)

                cl, cr = st.columns([3, 2])
                with cl:
                    st.markdown('<div class="mono" style="font-size:10px;color:#495670;">SIGNALS</div>', unsafe_allow_html=True)
                    st.markdown(pills(res["signals"]), unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)
                    tc1,tc2,tc3,tc4 = st.columns(4)
                    tc1.metric("RSI",  res["rsi"])
                    tc2.metric("ATR",  f"₹{res['atr']}")
                    if res["orb_h"]:
                        tc3.metric("ORB High", f"₹{res['orb_h']}")
                        tc4.metric("ORB Low",  f"₹{res['orb_l']}")
                with cr:
                    ml   = round(res["risk"] * res["qty"], 2)
                    pt1  = round((res["t1"] - res["cmp"]) * res["qty"], 2)
                    pt2  = round((res["t2"] - res["cmp"]) * res["qty"], 2)
                    st.markdown(f"""
                    <div class="mono" style="font-size:11px;line-height:2.2;color:#8892a4;">
                    Risk/trade: &nbsp;<b style="color:#ff3b55;">₹{ml:,}</b><br>
                    Profit (T1): <b style="color:#00ff88;">₹{pt1:,}</b><br>
                    Profit (T2): <b style="color:#00ff88;">₹{pt2:,}</b><br>
                    R:R Ratio: &nbsp;<b style="color:#00e5ff;">1:2 / 1:3</b>
                    </div>""", unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                b1, b2, b3 = st.columns([2, 1, 1])
                with b1:
                    if st.button(
                        f"✅ Buy {res['ticker']} @ ₹{res['cmp']} × {res['qty']}",
                        key=f"buy_{res['ticker']}"
                    ):
                        ot = st.session_state.db.get("intraday_trades", [])
                        if len(ot) >= 3:
                            st.error("Max 3 trades open. Close one first.")
                        else:
                            entry = {
                                "ticker":    res["ticker"],
                                "cap":       res["cap"],
                                "buy_price": res["cmp"],
                                "sl":        res["sl"],
                                "t1":        res["t1"],
                                "t2":        res["t2"],
                                "qty":       res["qty"],
                                "score":     res["score"],
                                "tags":      res["tags"],
                                "vwap":      res["vwap"],
                                "orb_h":     res["orb_h"],
                                "time":      get_ist_now().strftime("%H:%M:%S"),
                                "date":      get_ist_now().strftime("%Y-%m-%d"),
                            }
                            st.session_state.db["intraday_trades"].append(entry)
                            save_data(st.session_state.db)
                            st.toast(f"✅ {res['ticker']} × {res['qty']} opened!", icon="🚀")
                with b2:
                    st.link_button("📊 Chart", f"https://finance.yahoo.com/chart/{res['ticker']}.NS")
                with b3:
                    lvl = f"Entry ₹{res['cmp']} | SL ₹{res['sl']} | T1 ₹{res['t1']} | T2 ₹{res['t2']}"
                    st.code(lvl, language=None)

# ══════════════════════════════════════════════
# TAB 2 — ORB DASHBOARD
# ══════════════════════════════════════════════
with tabs[1]:
    st.markdown("#### 📊 Opening Range Breakout Dashboard")
    st.markdown("""
    <div class="mono" style="font-size:11px;color:#495670;margin-bottom:16px;">
    ORB = first 15-min high/low. Breakout above = BUY. Breakdown below = AVOID.
    </div>""", unsafe_allow_html=True)

    orb_input = st.text_input(
        "Tickers to track (comma-separated)",
        value="RELIANCE,TCS,INFY,SBIN,HDFCBANK,TATAMOTORS,ICICIBANK,WIPRO"
    )
    orb_btn = st.button("📊 Fetch ORB Levels")

    if orb_btn and orb_input:
        orb_list = [t.strip().upper() for t in orb_input.split(",") if t.strip()]

        def orb_row(sym):
            t_ns = f"{sym}.NS"
            oh, ol = get_opening_range(t_ns, 15)
            try:   cmp_ = round(yf.Ticker(t_ns).fast_info["last_price"], 2)
            except: cmp_ = None
            cap_ = get_cap(sym)
            if oh and cmp_:
                if cmp_ > oh:   status, emoji = "BREAKOUT",  "🟢"
                elif cmp_ < ol: status, emoji = "BREAKDOWN", "🔴"
                else:           status, emoji = "INSIDE ORB","🟡"
                dist = round(((cmp_ - oh) / oh) * 100, 2)
            else:
                status, emoji, dist = "–", "⚫", None
            return {"Cap":cap_,"Symbol":sym,"CMP":cmp_,
                    "ORB High":oh,"ORB Low":ol,
                    "Status":f"{emoji} {status}","Dist from ORB High%":dist}

        with st.spinner("Fetching ORB levels…"):
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
                rows = list(ex.map(orb_row, orb_list))

        df_orb = pd.DataFrame(rows)
        st.dataframe(df_orb, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("""
        <div class="mono" style="font-size:11px;color:#8892a4;line-height:2.2;">
        🟢 BREAKOUT → BUY. SL below ORB Low. Target = 2× ORB range above High.<br>
        🔴 BREAKDOWN → AVOID longs. Short opportunity for advanced traders.<br>
        🟡 INSIDE ORB → Wait. Don't trade until direction is confirmed.
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
# TAB 3 — OPEN TRADES
# ══════════════════════════════════════════════
with tabs[2]:
    open_trades = st.session_state.db.get("intraday_trades", [])
    st.markdown("#### 💼 Open Intraday Positions")

    if mstatus == "SQUAREOFF" and open_trades:
        st.markdown('<div class="alert-box alert-red">⚠️ SQUAREOFF ALERT — Exit ALL positions before 15:30!</div>', unsafe_allow_html=True)

    if not open_trades:
        st.info("No open trades. Run the scanner and buy a setup.")
    else:
        def fetch_lp(t):
            try:   return round(yf.Ticker(f"{t['ticker']}.NS").fast_info["last_price"], 2)
            except: return t["buy_price"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
            live_prices = list(ex.map(fetch_lp, open_trades))

        session_pnl = sum((lp - t["buy_price"]) * t["qty"]
                          for t, lp in zip(open_trades, live_prices))
        total_inv   = sum(t["buy_price"] * t["qty"] for t in open_trades)

        sm1, sm2, sm3 = st.columns(3)
        sm1.metric("Open Trades",    len(open_trades))
        sm2.metric("Session P&L",    f"₹{round(session_pnl,2)}")
        sm3.metric("Total Exposure", f"₹{total_inv:,.0f}")
        st.markdown("<hr class='divider'>", unsafe_allow_html=True)

        for i, (t, lp) in enumerate(zip(open_trades, live_prices)):
            pnl     = round((lp - t["buy_price"]) * t["qty"], 2)
            pnl_pct = round(((lp - t["buy_price"]) / t["buy_price"]) * 100, 2)
            pc      = "#00ff88" if pnl >= 0 else "#ff3b55"
            cap_    = t.get("cap", "Large Cap")
            cap_cls = CAP_CLS.get(cap_, "uni-large")

            if lp <= t["sl"]:
                st.markdown(f'<div class="alert-box alert-red">⚠️ {t["ticker"]} SL HIT — Exit NOW @ ₹{lp}</div>', unsafe_allow_html=True)
            elif lp >= t.get("t2", 1e9):
                st.markdown(f'<div class="alert-box alert-green">🎯 {t["ticker"]} TARGET 2 HIT — Book full profit @ ₹{lp}</div>', unsafe_allow_html=True)
            elif lp >= t.get("t1", 1e9):
                st.markdown(f'<div class="alert-box alert-green">🎯 {t["ticker"]} Target 1 hit — Trail SL or book 50% @ ₹{lp}</div>', unsafe_allow_html=True)

            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([2,2,3,2,1])
                c1.markdown(f"""
                <div style="font-family:'Rajdhani',sans-serif;font-weight:700;font-size:22px;color:{pc};">{t['ticker']}</div>
                <span class="uni-badge {cap_cls}">{cap_}</span><br>
                <div class="mono" style="font-size:10px;color:#495670;margin-top:4px;">
                {"".join(f'<span class="pill pp">{tg}</span>' for tg in t.get("tags",[]))}
                </div>""", unsafe_allow_html=True)
                c2.metric("Live Price", f"₹{lp}", f"{pnl_pct:+.2f}%")
                c3.markdown(f"""
                <div class="mono" style="font-size:11px;line-height:2;">
                Buy: <b>₹{t['buy_price']}</b> × {t['qty']} &nbsp;|&nbsp; {t['time']} IST<br>
                SL: <b style="color:#ff3b55;">₹{t['sl']}</b> &nbsp;|&nbsp;
                T1: <b style="color:#00ff88;">₹{t.get('t1','–')}</b> &nbsp;|&nbsp;
                T2: <b style="color:#00ff88;">₹{t.get('t2','–')}</b><br>
                VWAP at entry: ₹{t.get('vwap','–')} &nbsp;|&nbsp; Score: {t['score']}
                </div>""", unsafe_allow_html=True)
                c4.metric("P&L", f"₹{pnl}", f"{pnl_pct:+.2f}%")
                with c5:
                    if st.button("Exit", key=f"exit_{i}"):
                        ct = st.session_state.db["intraday_trades"].pop(i)
                        p  = round((lp - ct["buy_price"]) * ct["qty"], 2)
                        pp = round(((lp - ct["buy_price"]) / ct["buy_price"]) * 100, 2)
                        ct.update({
                            "sell_price": lp, "pnl": p, "pnl_pct": pp,
                            "exit_time":  get_ist_now().strftime("%H:%M:%S"),
                            "outcome":    "WIN" if p > 0 else "LOSS",
                        })
                        st.session_state.db["closed_trades"].append(ct)
                        save_data(st.session_state.db)
                        st.rerun()

# ══════════════════════════════════════════════
# TAB 4 — TRADE JOURNAL
# ══════════════════════════════════════════════
with tabs[3]:
    closed = st.session_state.db.get("closed_trades", [])
    st.markdown("#### 📜 Intraday Trade Journal")

    if not closed:
        st.info("No closed trades yet.")
    else:
        df = pd.DataFrame(closed)
        total_pnl  = round(df["pnl"].sum(), 2)
        wins       = int((df["pnl"] > 0).sum())
        losses     = int((df["pnl"] <= 0).sum())
        win_rate   = round(wins / len(df) * 100, 1)
        avg_win    = round(df[df["pnl"]>0]["pnl"].mean(), 2) if wins else 0
        avg_loss   = round(df[df["pnl"]<=0]["pnl"].mean(), 2) if losses else 0
        gw         = df[df["pnl"]>0]["pnl"].sum()
        gl         = abs(df[df["pnl"]<=0]["pnl"].sum())
        pf         = round(gw / max(gl, 1), 2)
        expect     = round((win_rate/100 * avg_win) + ((1-win_rate/100) * avg_loss), 2)

        h1,h2,h3,h4,h5,h6 = st.columns(6)
        h1.metric("Total P&L",        f"₹{total_pnl}", delta=total_pnl)
        h2.metric("Win Rate",         f"{win_rate}%",  f"{wins}W / {losses}L")
        h3.metric("Avg Win",          f"₹{avg_win}")
        h4.metric("Avg Loss",         f"₹{avg_loss}")
        h5.metric("Profit Factor",    pf)
        h6.metric("Expectancy/Trade", f"₹{expect}")

        st.markdown("<hr class='divider'>", unsafe_allow_html=True)

        # P&L by Cap Category
        if "cap" in df.columns:
            st.markdown("**P&L by Cap Category:**")
            cap_pnl = df.groupby("cap")["pnl"].sum().reset_index()
            cp_cols = st.columns(max(len(cap_pnl), 1))
            for i, row in cap_pnl.iterrows():
                cp_cols[i].metric(row["cap"], f"₹{round(row['pnl'],2)}", delta=round(row["pnl"],2))
            st.markdown("---")

        # P&L by Strategy
        if "tags" in df.columns:
            st.markdown("**P&L by Strategy:**")
            tag_pnl = {}
            for _, row in df.iterrows():
                for tag in (row.get("tags") or ["Unknown"]):
                    tag_pnl[tag] = tag_pnl.get(tag, 0) + row["pnl"]
            tc = st.columns(max(len(tag_pnl),1))
            for i, (tag, p) in enumerate(tag_pnl.items()):
                tc[i].metric(tag, f"₹{round(p,2)}", delta=round(p,2))
            st.markdown("---")

        cols = [c for c in ["ticker","cap","date","time","buy_price","sell_price",
                              "qty","pnl","pnl_pct","outcome","exit_time"] if c in df.columns]
        df_d = df[cols].copy()
        df_d.columns = [c.upper() for c in df_d.columns]

        def style_pnl(val):
            if isinstance(val, (int, float)):
                return f'color:{"#00ff88" if val>0 else "#ff3b55"}'
            return ""

        pnl_cols = [c for c in ["PNL","PNL_PCT"] if c in df_d.columns]
        st.dataframe(
            df_d.style.applymap(style_pnl, subset=pnl_cols),
            use_container_width=True, hide_index=True
        )

        dl, cl = st.columns(2)
        with dl:
            st.download_button("⬇️ Export CSV",
                               df_d.to_csv(index=False),
                               "intraday_journal.csv", "text/csv")
        with cl:
            if st.button("🗑️ Clear Journal"):
                st.session_state.db["closed_trades"] = []
                save_data(st.session_state.db)
                st.rerun()

# ══════════════════════════════════════════════
# TAB 5 — POSITION SIZER
# ══════════════════════════════════════════════
with tabs[4]:
    st.markdown("#### 🧮 Position Size Calculator")
    st.markdown("""
    <div class="mono" style="font-size:11px;color:#495670;margin-bottom:16px;">
    Fixed-fractional method: risk exactly N% of capital per trade. Protects your account long-term.
    </div>""", unsafe_allow_html=True)

    ps1, ps2 = st.columns(2)
    with ps1:
        pc_  = st.number_input("Capital (₹)",      value=float(capital), step=10000.0)
        pe_  = st.number_input("Entry Price (₹)",  value=1000.0, step=1.0)
        psl_ = st.number_input("Stop Loss (₹)",    value=985.0,  step=0.5)
        pt_  = st.number_input("Target Price (₹)", value=1030.0, step=1.0)
        pr_  = st.slider("Risk %", 0.5, 3.0, 1.0, step=0.25)

        # Cap type hint
        cap_hint = st.selectbox("Cap Category (hint)", ["Large Cap","Mid Cap","Small Cap"])
        if cap_hint == "Small Cap":
            st.markdown("""<div class="alert-box alert-yellow" style="font-size:10px;padding:8px 12px;">
            ⚠️ Small Cap: Consider adding 0.5% buffer to SL for wider spreads.
            </div>""", unsafe_allow_html=True)

    with ps2:
        if pe_ > psl_ > 0:
            rps  = pe_ - psl_
            q    = int((pc_ * pr_ / 100) / rps)
            inv  = round(q * pe_, 2)
            ml   = round(q * rps, 2)
            pp_  = round(q * (pt_ - pe_), 2)
            rr   = round((pt_ - pe_) / rps, 2) if rps > 0 else 0
            sl_p = round((pe_ - psl_) / pe_ * 100, 2)
            tp_p = round((pt_ - pe_)  / pe_ * 100, 2)
            ok_rr  = rr >= 2.0
            ok_sl  = sl_p <= 2.5
            ok_inv = inv <= pc_ * 0.25

            st.markdown(f"""
            <div class="icard">
            <div class="mono" style="font-size:13px;line-height:2.3;">
            📦 Quantity: &nbsp;&nbsp;<b style="color:#00e5ff;font-size:20px;">{q} shares</b><br>
            💰 Invested: &nbsp;<b>₹{inv:,.2f}</b>
                {'<span class="pill pg">✓ &lt;25%</span>' if ok_inv else '<span class="pill pr">⚠ &gt;25%</span>'}<br>
            📉 Max Loss: &nbsp;<b style="color:#ff3b55;">₹{ml:,.2f}</b> ({pr_}% of capital)<br>
            📈 Potential: &nbsp;<b style="color:#00ff88;">₹{pp_:,.2f}</b> ({tp_p:+.2f}%)<br>
            ⚖️ R:R Ratio: <b style="color:#{'00ff88' if ok_rr else 'ffc107'};">1 : {rr}</b>
                {'<span class="pill pg">✓ Good</span>' if ok_rr else '<span class="pill py">⚠ Improve</span>'}<br>
            🛑 SL %: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>{sl_p}%</b>
                {'<span class="pill pg">✓ Tight</span>' if ok_sl else '<span class="pill py">⚠ Wide</span>'}
            </div>
            </div>""", unsafe_allow_html=True)

            if not ok_rr:
                st.markdown('<div class="alert-box alert-yellow">⚠️ R:R below 2:1 — Adjust target or find better entry.</div>', unsafe_allow_html=True)
            if not ok_inv:
                st.markdown('<div class="alert-box alert-yellow">⚠️ Investing >25% capital in one trade — reduce qty.</div>', unsafe_allow_html=True)
        else:
            st.warning("Entry price must be above Stop Loss.")

    st.markdown("---")
    st.markdown("**💡 Golden Rules by Cap Category**")
    st.markdown("""
    <div class="mono" style="font-size:11px;color:#8892a4;line-height:2.3;">
    <span class="uni-badge uni-large">Large Cap</span><br>
    &nbsp;· Tightest SL (1–1.5%) · Best liquidity · Ideal for beginners<br>
    &nbsp;· Trade any time after 9:30 · Volume > 1.5x avg is sufficient<br><br>
    <span class="uni-badge uni-mid">Mid Cap</span><br>
    &nbsp;· SL 1.5–2% · Check bid-ask before entry · Avoid last 30 min<br>
    &nbsp;· Wait for volume > 2x avg · Stronger breakout confirmation needed<br><br>
    <span class="uni-badge uni-small">Small Cap</span><br>
    &nbsp;· SL 2–2.5% · Lower qty · Mandatory liquidity check<br>
    &nbsp;· Avoid first 30 min · Only trade volume > 3x avg · Advanced only<br><br>
    <b style="color:#ffc107;">Universal Rules:</b><br>
    1. Never risk &gt;1–2% of capital per trade<br>
    2. Minimum R:R 1:2 before entry — no exceptions<br>
    3. Max 3 concurrent positions<br>
    4. Squareoff ALL by 15:10 IST — no exceptions<br>
    5. Trail SL to cost once Target 1 is hit<br>
    6. Daily loss &gt;3% → Stop trading for the day<br>
    7. VWAP + Supertrend must agree for entry<br>
    8. Journal every trade — your edge lives in the data
    </div>""", unsafe_allow_html=True)
