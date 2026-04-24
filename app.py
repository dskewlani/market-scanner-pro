"""
Alpha Breakout Pro - Advanced AI-Powered Stock Scanner
Multi-factor scoring: Technical + Fundamental + News Sentiment + Volume Analysis
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import concurrent.futures
import json
import os
import requests
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Alpha Breakout Pro",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="📈"
)

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;700;800&display=swap');

:root {
    --bg: #0a0e17;
    --card: #111827;
    --border: #1f2937;
    --accent: #00ff88;
    --accent2: #f59e0b;
    --accent3: #3b82f6;
    --danger: #ef4444;
    --text: #e5e7eb;
    --muted: #6b7280;
}

html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
    background-color: var(--bg) !important;
    color: var(--text) !important;
}

.stApp { background: var(--bg) !important; }

/* Hide streamlit branding */
#MainMenu, footer, header { visibility: hidden; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: var(--card);
    border-radius: 10px;
    padding: 4px;
    border: 1px solid var(--border);
}
.stTabs [data-baseweb="tab"] {
    color: var(--muted) !important;
    font-family: 'Space Mono', monospace;
    font-size: 12px;
    letter-spacing: 0.05em;
}
.stTabs [aria-selected="true"] {
    background: var(--accent) !important;
    color: #000 !important;
    border-radius: 7px;
}

/* Buttons */
.stButton>button {
    background: linear-gradient(135deg, var(--accent), #00cc6a) !important;
    color: #000 !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Space Mono', monospace !important;
    font-weight: 700 !important;
    font-size: 11px !important;
    letter-spacing: 0.08em !important;
    padding: 8px 16px !important;
    transition: all 0.2s !important;
}
.stButton>button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 20px rgba(0,255,136,0.35) !important;
}

/* Score badge */
.score-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 20px;
    font-family: 'Space Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.05em;
}
.score-elite { background: rgba(0,255,136,0.15); color: #00ff88; border: 1px solid rgba(0,255,136,0.3); }
.score-strong { background: rgba(59,130,246,0.15); color: #3b82f6; border: 1px solid rgba(59,130,246,0.3); }
.score-moderate { background: rgba(245,158,11,0.15); color: #f59e0b; border: 1px solid rgba(245,158,11,0.3); }
.score-weak { background: rgba(239,68,68,0.15); color: #ef4444; border: 1px solid rgba(239,68,68,0.3); }

/* Stock card */
.stock-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 12px;
    transition: border-color 0.2s;
}
.stock-card:hover { border-color: var(--accent); }
.stock-card.elite { border-left: 3px solid var(--accent); }
.stock-card.strong { border-left: 3px solid var(--accent3); }
.stock-card.moderate { border-left: 3px solid var(--accent2); }

/* Metric cards */
.mini-metric {
    background: rgba(255,255,255,0.03);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 14px;
    text-align: center;
}
.mini-metric .label {
    font-family: 'Space Mono', monospace;
    font-size: 9px;
    color: var(--muted);
    letter-spacing: 0.1em;
    text-transform: uppercase;
}
.mini-metric .value {
    font-size: 15px;
    font-weight: 700;
    margin-top: 2px;
}

/* Progress bar */
.score-bar-bg {
    background: var(--border);
    border-radius: 4px;
    height: 6px;
    width: 100%;
    margin-top: 6px;
}
.score-bar-fill {
    height: 6px;
    border-radius: 4px;
    transition: width 0.4s ease;
}

/* Sidebar */
.css-1d391kg, [data-testid="stSidebar"] {
    background: var(--card) !important;
    border-right: 1px solid var(--border) !important;
}

/* Expander */
.streamlit-expanderHeader {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 12px !important;
}

/* DataFrame */
.dataframe { font-family: 'Space Mono', monospace !important; font-size: 11px !important; }

/* Title */
.hero-title {
    font-family: 'Syne', sans-serif;
    font-size: 28px;
    font-weight: 800;
    letter-spacing: -0.02em;
    line-height: 1.1;
}
.hero-sub {
    font-family: 'Space Mono', monospace;
    font-size: 11px;
    color: var(--muted);
    letter-spacing: 0.08em;
}
.accent { color: var(--accent); }

.divider {
    border: none;
    border-top: 1px solid var(--border);
    margin: 16px 0;
}

/* Signal pills */
.pill {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-family: 'Space Mono', monospace;
    font-size: 10px;
    margin: 2px;
}
.pill-green { background: rgba(0,255,136,0.12); color: #00ff88; }
.pill-red { background: rgba(239,68,68,0.12); color: #ef4444; }
.pill-yellow { background: rgba(245,158,11,0.12); color: #f59e0b; }
.pill-blue { background: rgba(59,130,246,0.12); color: #3b82f6; }

</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PERSISTENCE
# ─────────────────────────────────────────────
DB_FILE = "alpha_breakout_db.json"

def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {"portfolio": [], "sold": [], "watchlist": []}

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

if 'db' not in st.session_state:
    st.session_state.db = load_data()

# ─────────────────────────────────────────────
# TICKER UNIVERSE
# ─────────────────────────────────────────────
@st.cache_data(ttl=86400)
def get_nifty_500_tickers():
    try:
        url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
        df = pd.read_csv(url)
        return [f"{s}.NS" for s in df['Symbol'].tolist()]
    except:
        # Fallback: large-cap universe
        fallback = [
            'RELIANCE','TCS','HDFCBANK','ICICIBANK','INFY','SBIN','BHARTIARTL',
            'KOTAKBANK','LT','AXISBANK','WIPRO','HCLTECH','ASIANPAINT','MARUTI',
            'TITAN','BAJFINANCE','SUNPHARMA','NESTLEIND','POWERGRID','TECHM',
            'ONGC','NTPC','COALINDIA','HINDALCO','TATASTEEL','JSWSTEEL','GRASIM',
            'ULTRACEMCO','DRREDDY','CIPLA','DIVISLAB','APOLLOHOSP','ADANIENT',
            'ADANIPORTS','BAJAJFINSV','BRITANNIA','EICHERMOT','HEROMOTOCO',
            'HINDUNILVR','ITC','M&M','TATAMOTORS','TATACONSUM','VEDL','BPCL',
            'SHREECEM','PIDILITIND','HAVELLS','DABUR','BERGEPAINT'
        ]
        return [f"{s}.NS" for s in fallback]

# ─────────────────────────────────────────────
# TECHNICAL INDICATORS
# ─────────────────────────────────────────────
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def compute_macd(series):
    ema12 = series.ewm(span=12).mean()
    ema26 = series.ewm(span=26).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    return macd, signal

def compute_atr(df, period=14):
    h_l = df['High'] - df['Low']
    h_pc = abs(df['High'] - df['Close'].shift(1))
    l_pc = abs(df['Low'] - df['Close'].shift(1))
    tr = pd.concat([h_l, h_pc, l_pc], axis=1).max(axis=1)
    return tr.ewm(span=period).mean()

def compute_bollinger(series, period=20):
    mid = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = mid + 2 * std
    lower = mid - 2 * std
    return upper, mid, lower

def compute_adx(df, period=14):
    try:
        df = df.copy()
        df['+DM'] = np.where((df['High'] - df['High'].shift(1)) > (df['Low'].shift(1) - df['Low']),
                              np.maximum(df['High'] - df['High'].shift(1), 0), 0)
        df['-DM'] = np.where((df['Low'].shift(1) - df['Low']) > (df['High'] - df['High'].shift(1)),
                              np.maximum(df['Low'].shift(1) - df['Low'], 0), 0)
        tr = compute_atr(df, period)
        tr14 = tr.ewm(span=period).mean()
        plus_di = 100 * (df['+DM'].ewm(span=period).mean() / tr14)
        minus_di = 100 * (df['-DM'].ewm(span=period).mean() / tr14)
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9)
        return dx.ewm(span=period).mean().iloc[-1]
    except:
        return 0

# ─────────────────────────────────────────────
# FUNDAMENTAL SCORING
# ─────────────────────────────────────────────
def get_fundamental_score(ticker_obj):
    """Score: 0–30 based on fundamentals"""
    score = 0
    signals = []
    try:
        info = ticker_obj.info

        # 1. PE Ratio vs sector – if PE < 30 and not negative
        pe = info.get('trailingPE', None)
        fwd_pe = info.get('forwardPE', None)
        if pe and 0 < pe < 25:
            score += 6
            signals.append(("PE < 25", "green"))
        elif pe and 0 < pe < 35:
            score += 3
            signals.append(("PE 25–35", "yellow"))

        # 2. Revenue Growth (YoY)
        rev_growth = info.get('revenueGrowth', None)
        if rev_growth and rev_growth > 0.20:
            score += 7
            signals.append((f"Rev +{rev_growth*100:.0f}%", "green"))
        elif rev_growth and rev_growth > 0.10:
            score += 4
            signals.append((f"Rev +{rev_growth*100:.0f}%", "yellow"))

        # 3. Earnings Growth
        earn_growth = info.get('earningsGrowth', None)
        if earn_growth and earn_growth > 0.25:
            score += 7
            signals.append((f"EPS +{earn_growth*100:.0f}%", "green"))
        elif earn_growth and earn_growth > 0.10:
            score += 4
            signals.append((f"EPS +{earn_growth*100:.0f}%", "yellow"))

        # 4. ROE
        roe = info.get('returnOnEquity', None)
        if roe and roe > 0.20:
            score += 5
            signals.append((f"ROE {roe*100:.0f}%", "green"))
        elif roe and roe > 0.12:
            score += 2
            signals.append((f"ROE {roe*100:.0f}%", "yellow"))

        # 5. Debt-to-Equity
        de = info.get('debtToEquity', None)
        if de is not None and de < 0.5:
            score += 5
            signals.append(("Low Debt", "green"))
        elif de is not None and de < 1.0:
            score += 2
            signals.append(("Mod Debt", "yellow"))

    except:
        pass
    return min(score, 30), signals

# ─────────────────────────────────────────────
# TECHNICAL SCORING
# ─────────────────────────────────────────────
def get_technical_score(df, cmp):
    """Score: 0–40 based on technicals"""
    score = 0
    signals = []

    close = df['Close']
    high  = df['High']
    low   = df['Low']
    vol   = df['Volume']

    # 1. Breakout proximity (20-day high)
    high_20 = float(high.iloc[-21:-1].max())
    dist_pct = ((high_20 - cmp) / high_20) * 100
    if 0 <= dist_pct <= 0.5:
        score += 10
        signals.append(("Breakout Zone", "green"))
    elif dist_pct <= 1.5:
        score += 7
        signals.append(("Near BO", "green"))
    elif dist_pct <= 3.0:
        score += 4
        signals.append(("Approaching BO", "yellow"))

    # 2. RSI (ideal: 55–70 for momentum breakout)
    rsi = compute_rsi(close)
    rsi_val = float(rsi.iloc[-1])
    if 55 <= rsi_val <= 72:
        score += 8
        signals.append((f"RSI {rsi_val:.0f} ✓", "green"))
    elif 45 <= rsi_val < 55:
        score += 4
        signals.append((f"RSI {rsi_val:.0f}", "yellow"))
    elif rsi_val > 75:
        score -= 3
        signals.append((f"RSI {rsi_val:.0f} OB", "red"))

    # 3. MACD bullish crossover
    macd_line, signal_line = compute_macd(close)
    macd_val = float(macd_line.iloc[-1])
    sig_val  = float(signal_line.iloc[-1])
    macd_prev = float(macd_line.iloc[-2])
    sig_prev  = float(signal_line.iloc[-2])
    if macd_val > sig_val and macd_prev <= sig_prev:
        score += 8
        signals.append(("MACD Cross↑", "green"))
    elif macd_val > sig_val:
        score += 5
        signals.append(("MACD Bull", "green"))
    elif macd_val < sig_val:
        score -= 2
        signals.append(("MACD Bear", "red"))

    # 4. Volume surge (today > 1.5x 20-day avg)
    avg_vol = float(vol.iloc[-21:-1].mean())
    cur_vol = float(vol.iloc[-1])
    vol_ratio = cur_vol / avg_vol if avg_vol > 0 else 0
    if vol_ratio >= 2.0:
        score += 8
        signals.append((f"Vol {vol_ratio:.1f}x🔥", "green"))
    elif vol_ratio >= 1.5:
        score += 5
        signals.append((f"Vol {vol_ratio:.1f}x", "green"))
    elif vol_ratio < 0.7:
        score -= 3
        signals.append(("Low Vol", "red"))

    # 5. Price above key MAs
    ma_50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else None
    ma_20 = float(close.rolling(20).mean().iloc[-1]) if len(close) >= 20 else None
    if ma_50 and cmp > ma_50:
        score += 3
        signals.append(("Above MA50", "green"))
    if ma_20 and cmp > ma_20:
        score += 3
        signals.append(("Above MA20", "green"))

    # 6. ADX (trend strength)
    adx = compute_adx(df)
    if adx > 25:
        score += 3
        signals.append((f"ADX {adx:.0f}", "green"))

    return min(max(score, 0), 40), signals, {
        "rsi": round(rsi_val, 1),
        "vol_ratio": round(vol_ratio, 2),
        "dist_pct": round(dist_pct, 2),
        "breakout_price": round(high_20, 2),
        "ma_20": round(ma_20, 2) if ma_20 else None,
        "ma_50": round(ma_50, 2) if ma_50 else None,
        "macd_bull": macd_val > sig_val,
        "adx": round(adx, 1)
    }

# ─────────────────────────────────────────────
# EARNINGS / RESULTS EXPECTATION SCORING
# ─────────────────────────────────────────────
def get_earnings_score(ticker_obj):
    """Score: 0–15 for upcoming results / beat history"""
    score = 0
    signals = []
    try:
        info = ticker_obj.info
        
        # Earnings surprise history (positive surprises = higher probability)
        cal = ticker_obj.calendar
        if cal is not None and not cal.empty:
            # Upcoming earnings in next 30 days = catalyst
            if hasattr(cal, 'values'):
                score += 5
                signals.append(("Earnings Soon📅", "blue"))

        # EPS surprise from last quarter
        earnings_hist = ticker_obj.earnings_history
        if earnings_hist is not None and not earnings_hist.empty:
            recent = earnings_hist.head(4)
            beats = (recent.get('epsActual', pd.Series()) > recent.get('epsEstimate', pd.Series())).sum()
            if beats >= 3:
                score += 8
                signals.append((f"Beat {beats}/4 Qtrs", "green"))
            elif beats >= 2:
                score += 4
                signals.append((f"Beat {beats}/4 Qtrs", "yellow"))

        # Analyst recommendations
        rec = info.get('recommendationKey', '')
        if rec in ['strong_buy', 'buy']:
            score += 5
            signals.append(("Analyst: Buy", "green"))
        elif rec == 'hold':
            score += 2
            signals.append(("Analyst: Hold", "yellow"))
        elif rec in ['sell', 'strong_sell']:
            score -= 3
            signals.append(("Analyst: Sell", "red"))

        # Price target upside
        current = info.get('currentPrice', 0)
        target_mean = info.get('targetMeanPrice', 0)
        if current and target_mean:
            upside = ((target_mean - current) / current) * 100
            if upside > 20:
                score += 5
                signals.append((f"Target +{upside:.0f}%", "green"))
            elif upside > 10:
                score += 2
                signals.append((f"Target +{upside:.0f}%", "yellow"))
            elif upside < 0:
                score -= 2
                signals.append((f"Target {upside:.0f}%", "red"))

    except:
        pass
    return min(max(score, 0), 15), signals

# ─────────────────────────────────────────────
# NEWS / SENTIMENT SCORING (Lightweight)
# ─────────────────────────────────────────────
def get_news_score(ticker_obj, ticker_symbol):
    """Score: 0–15 based on recent news sentiment"""
    score = 0
    signals = []
    headlines = []
    try:
        news = ticker_obj.news
        if not news:
            return 0, [], []

        positive_kw = ['profit', 'growth', 'surge', 'beat', 'record', 'win', 'expansion',
                       'acquisition', 'order', 'contract', 'launch', 'upgrade', 'rally',
                       'strong', 'positive', 'up', 'gain', 'rise', 'revenue', 'outperform',
                       'breakthrough', 'deal', 'partnership', 'bullish', 'jump', 'soar']
        negative_kw = ['loss', 'decline', 'fall', 'drop', 'weak', 'concern', 'risk',
                       'downgrade', 'sell', 'fraud', 'probe', 'penalty', 'default',
                       'miss', 'cut', 'negative', 'bearish', 'crash', 'exit']

        pos_count = 0
        neg_count = 0
        recent_news = news[:8]  # last 8 articles

        for article in recent_news:
            title = article.get('title', '').lower()
            headlines.append(article.get('title', ''))
            if any(k in title for k in positive_kw):
                pos_count += 1
            if any(k in title for k in negative_kw):
                neg_count += 1

        net = pos_count - neg_count
        if net >= 3:
            score += 10
            signals.append((f"News +{pos_count}↑", "green"))
        elif net >= 1:
            score += 5
            signals.append(("News Positive", "green"))
        elif net == 0:
            score += 2
            signals.append(("News Neutral", "yellow"))
        elif net < 0:
            score -= 3
            signals.append(("News Negative", "red"))

        # Recency bonus — news in last 3 days
        now_ts = datetime.now().timestamp()
        fresh = [n for n in recent_news if (now_ts - n.get('providerPublishTime', 0)) < 259200]
        if len(fresh) >= 2:
            score += 5
            signals.append(("Fresh News", "blue"))

    except:
        pass
    return min(max(score, 0), 15), signals, headlines[:5]

# ─────────────────────────────────────────────
# MASTER SCORE COMPUTATION
# ─────────────────────────────────────────────
def grade_score(total):
    if total >= 75:   return "ELITE", "elite",   "🟢"
    elif total >= 58: return "STRONG", "strong",  "🔵"
    elif total >= 42: return "MODERATE", "moderate", "🟡"
    else:             return "WEAK", "weak", "🔴"

def analyze_stock(ticker):
    """Full multi-factor analysis — returns None if below threshold"""
    try:
        # Download OHLCV
        df = yf.download(ticker, period="100d", interval="1d", progress=False, auto_adjust=True)
        if df.empty or len(df) < 30:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        cmp = float(df['Close'].iloc[-1])
        
        # Quick gate: must be near 20-day high
        high_20 = float(df['High'].iloc[-21:-1].max())
        dist = ((high_20 - cmp) / high_20) * 100
        if dist > 4.0 or dist < 0:
            return None  # Not near breakout

        ticker_obj = yf.Ticker(ticker)

        # SCORING
        tech_score,  tech_signals,  tech_data  = get_technical_score(df, cmp)
        fund_score,  fund_signals               = get_fundamental_score(ticker_obj)
        earn_score,  earn_signals               = get_earnings_score(ticker_obj)
        news_score,  news_signals, headlines   = get_news_score(ticker_obj, ticker)

        total_score = tech_score + fund_score + earn_score + news_score
        grade, grade_cls, grade_emoji = grade_score(total_score)

        # Only surface stocks with meaningful probability
        if total_score < 35:
            return None

        info = ticker_obj.info
        target_price = info.get('targetMeanPrice', None)
        bo_target    = round(high_20 * 1.08, 2)    # 8% post-breakout target
        sl           = round(cmp * 0.955, 2)        # 4.5% stop loss

        return {
            "ticker":       ticker.replace(".NS", ""),
            "cmp":          round(cmp, 2),
            "bo_level":     tech_data['breakout_price'],
            "target":       bo_target,
            "sl":           sl,
            "risk_reward":  round((bo_target - cmp) / (cmp - sl), 2) if (cmp - sl) > 0 else 0,
            "total_score":  round(total_score, 1),
            "tech_score":   tech_score,
            "fund_score":   fund_score,
            "earn_score":   earn_score,
            "news_score":   news_score,
            "grade":        grade,
            "grade_cls":    grade_cls,
            "grade_emoji":  grade_emoji,
            "rsi":          tech_data['rsi'],
            "vol_ratio":    tech_data['vol_ratio'],
            "dist_pct":     tech_data['dist_pct'],
            "macd_bull":    tech_data['macd_bull'],
            "adx":          tech_data['adx'],
            "ma_20":        tech_data['ma_20'],
            "ma_50":        tech_data['ma_50'],
            "all_signals":  tech_signals + fund_signals + earn_signals + news_signals,
            "headlines":    headlines,
            "analyst_target": round(target_price, 2) if target_price else None,
        }

    except Exception as e:
        return None

# ─────────────────────────────────────────────
# ACTION FUNCTIONS
# ─────────────────────────────────────────────
def buy_stock(res):
    new_entry = {
        "ticker":    res['ticker'],
        "buy_price": res['cmp'],
        "target":    res['target'],
        "sl":        res['sl'],
        "bo_level":  res['bo_level'],
        "score":     res['total_score'],
        "grade":     res['grade'],
        "rr":        res['risk_reward'],
        "date":      datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    st.session_state.db["portfolio"].append(new_entry)
    save_data(st.session_state.db)
    st.toast(f"✅ Bought {res['ticker']} @ ₹{res['cmp']}", icon="🚀")

def sell_stock(index, live_price):
    stock = st.session_state.db["portfolio"].pop(index)
    pnl = round(live_price - stock['buy_price'], 2)
    pnl_pct = round((pnl / stock['buy_price']) * 100, 2)
    stock.update({
        "sell_price": live_price,
        "pnl":        pnl,
        "pnl_pct":    pnl_pct,
        "sell_date":  datetime.now().strftime("%Y-%m-%d %H:%M"),
        "outcome":    "WIN" if pnl > 0 else "LOSS"
    })
    st.session_state.db["sold"].append(stock)
    save_data(st.session_state.db)
    st.rerun()

def add_watchlist(ticker):
    wl = st.session_state.db.get("watchlist", [])
    if ticker not in wl:
        wl.append(ticker)
        st.session_state.db["watchlist"] = wl
        save_data(st.session_state.db)
        st.toast(f"👁 Added {ticker} to watchlist")

# ─────────────────────────────────────────────
# SIGNAL PILL RENDERER
# ─────────────────────────────────────────────
def render_pills(signals):
    html = ""
    for label, color in signals[:8]:
        css = f"pill-{color}"
        html += f'<span class="pill {css}">{label}</span>'
    return html

# ─────────────────────────────────────────────
# SCORE BAR RENDERER
# ─────────────────────────────────────────────
def score_bar(score, max_score, color):
    pct = min(int((score / max_score) * 100), 100)
    return f"""
    <div class="score-bar-bg">
        <div class="score-bar-fill" style="width:{pct}%;background:{color};"></div>
    </div>
    """

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown("""
    <div class="hero-title">Alpha Breakout <span class="accent">Pro</span></div>
    <div class="hero-sub">AI-POWERED · MULTI-FACTOR · NSE INDIA · REAL-TIME</div>
    """, unsafe_allow_html=True)
with col_h2:
    now = datetime.now().strftime("%d %b %Y  %H:%M")
    st.markdown(f"""
    <div style="text-align:right; font-family:'Space Mono',monospace; font-size:11px; color:#6b7280; padding-top:8px;">
    {now}<br><span style="color:#00ff88;">● LIVE</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<hr class='divider'>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Scanner Config")
    
    scan_mode = st.selectbox("Universe", ["Nifty 500", "Nifty 200", "Nifty 50", "Custom"])
    max_workers = st.slider("Parallel Workers", 10, 40, 25)
    min_score   = st.slider("Min Score Filter", 30, 80, 40)
    max_dist    = st.slider("Max BO Distance %", 1.0, 5.0, 3.0, step=0.5)
    
    st.markdown("---")
    st.markdown("### 📊 Score Weights")
    st.markdown("""
    <div style="font-family:'Space Mono',monospace;font-size:10px;color:#6b7280;line-height:1.8;">
    TECHNICAL &nbsp;&nbsp;/40<br>
    FUNDAMENTAL /30<br>
    EARNINGS &nbsp;&nbsp;/15<br>
    NEWS SENTIMENT /15<br>
    ─────────────<br>
    TOTAL &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;/100
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Portfolio Summary
    portfolio = st.session_state.db["portfolio"]
    sold = st.session_state.db["sold"]
    
    if portfolio:
        st.markdown("### 💼 Open Positions")
        total_unrealized = 0
        for s in portfolio:
            try:
                lp = yf.Ticker(f"{s['ticker']}.NS").fast_info['last_price']
                pnl = lp - s['buy_price']
                total_unrealized += pnl
                color = "#00ff88" if pnl >= 0 else "#ef4444"
                pct = (pnl / s['buy_price']) * 100
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;font-family:'Space Mono',monospace;font-size:11px;padding:4px 0;border-bottom:1px solid #1f2937;">
                    <span>{s['ticker']}</span>
                    <span style="color:{color};">{'+' if pnl>=0 else ''}{pct:.1f}%</span>
                </div>
                """, unsafe_allow_html=True)
            except:
                pass
        col_s1, col_s2 = st.columns(2)
        col_s1.metric("Unrealized P&L", f"₹{round(total_unrealized, 2)}", 
                       delta=f"{round(total_unrealized, 2)}")
    
    if sold:
        df_sold = pd.DataFrame(sold)
        total_realized = df_sold['pnl'].sum()
        wins = (df_sold['pnl'] > 0).sum()
        win_rate = round(wins / len(df_sold) * 100, 1)
        st.markdown("### 📈 Stats")
        st.metric("Realized P&L", f"₹{round(total_realized, 2)}")
        st.metric("Win Rate", f"{win_rate}%", f"{wins}/{len(df_sold)} trades")

# ─────────────────────────────────────────────
# MAIN TABS
# ─────────────────────────────────────────────
tabs = st.tabs(["🔬 Smart Scanner", "💼 Portfolio", "📜 Trade History", "👁 Watchlist"])

# ══════════════════════════════════════════════
# TAB 1: SMART SCANNER
# ══════════════════════════════════════════════
with tabs[0]:
    st.markdown("#### Multi-Factor Breakout Scanner")
    st.markdown("""
    <div style="font-family:'Space Mono',monospace;font-size:11px;color:#6b7280;margin-bottom:16px;">
    Scores each stock across Technical (40) + Fundamental (30) + Earnings (15) + News (15) = 100pts
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        run_scan = st.button("🚀 Run Full AI Scan", use_container_width=True)
    with c2:
        sort_by = st.selectbox("Sort By", ["Total Score", "RSI", "Volume Ratio", "Risk/Reward"])
    with c3:
        show_count = st.selectbox("Show Top", [10, 20, 30, 50])

    if run_scan:
        all_tickers = get_nifty_500_tickers()
        
        # Filter by universe
        if scan_mode == "Nifty 50":
            all_tickers = all_tickers[:50]
        elif scan_mode == "Nifty 200":
            all_tickers = all_tickers[:200]
        
        results = []
        progress = st.progress(0, text="Initializing scan...")
        status_box = st.empty()
        
        total = len(all_tickers)
        completed = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(analyze_stock, t): t for t in all_tickers}
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result and result['total_score'] >= min_score and result['dist_pct'] <= max_dist:
                    results.append(result)
                completed += 1
                pct = completed / total
                progress.progress(pct, text=f"Scanned {completed}/{total} stocks — {len(results)} candidates found")
        
        progress.empty()
        
        # Sort
        sort_key = {
            "Total Score": "total_score",
            "RSI": "rsi",
            "Volume Ratio": "vol_ratio",
            "Risk/Reward": "risk_reward"
        }[sort_by]
        
        results.sort(key=lambda x: x[sort_key], reverse=True)
        st.session_state.scan_results = results
        st.session_state.scan_time = datetime.now().strftime("%H:%M:%S")
        
        status_box.success(f"✅ Scan complete at {st.session_state.scan_time} — {len(results)} high-probability candidates found")

    # ── Results Display ──
    if 'scan_results' in st.session_state and st.session_state.scan_results:
        results = st.session_state.scan_results[:show_count]
        
        st.markdown(f"""
        <div style="font-family:'Space Mono',monospace;font-size:11px;color:#6b7280;margin-bottom:16px;">
        LAST SCAN: {st.session_state.get('scan_time','–')} &nbsp;·&nbsp; {len(results)} STOCKS SHOWN
        </div>
        """, unsafe_allow_html=True)
        
        for res in results:
            grade_colors = {"elite":"#00ff88", "strong":"#3b82f6", "moderate":"#f59e0b", "weak":"#ef4444"}
            gcolor = grade_colors.get(res['grade_cls'], "#6b7280")
            
            with st.expander(
                f"{res['grade_emoji']} {res['ticker']}  |  Score: {res['total_score']}/100  |  {res['grade']}  |  CMP ₹{res['cmp']}  |  BO Level ₹{res['bo_level']}",
                expanded=res['grade_cls'] == 'elite'
            ):
                # Top row: score breakdown
                sc1, sc2, sc3, sc4 = st.columns(4)
                with sc1:
                    st.markdown(f"""
                    <div class="mini-metric">
                        <div class="label">TECHNICAL</div>
                        <div class="value" style="color:#00ff88;">{res['tech_score']}/40</div>
                        {score_bar(res['tech_score'], 40, '#00ff88')}
                    </div>""", unsafe_allow_html=True)
                with sc2:
                    st.markdown(f"""
                    <div class="mini-metric">
                        <div class="label">FUNDAMENTAL</div>
                        <div class="value" style="color:#3b82f6;">{res['fund_score']}/30</div>
                        {score_bar(res['fund_score'], 30, '#3b82f6')}
                    </div>""", unsafe_allow_html=True)
                with sc3:
                    st.markdown(f"""
                    <div class="mini-metric">
                        <div class="label">EARNINGS</div>
                        <div class="value" style="color:#f59e0b;">{res['earn_score']}/15</div>
                        {score_bar(res['earn_score'], 15, '#f59e0b')}
                    </div>""", unsafe_allow_html=True)
                with sc4:
                    st.markdown(f"""
                    <div class="mini-metric">
                        <div class="label">NEWS</div>
                        <div class="value" style="color:#a855f7;">{res['news_score']}/15</div>
                        {score_bar(res['news_score'], 15, '#a855f7')}
                    </div>""", unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Key metrics
                m1, m2, m3, m4, m5, m6 = st.columns(6)
                m1.metric("CMP", f"₹{res['cmp']}")
                m2.metric("BO Level", f"₹{res['bo_level']}", f"{res['dist_pct']}% away", delta_color="inverse")
                m3.metric("Target (+8%)", f"₹{res['target']}")
                m4.metric("Stop Loss", f"₹{res['sl']}", f"-{round((res['cmp']-res['sl'])/res['cmp']*100,1)}%", delta_color="off")
                m5.metric("Risk:Reward", f"1 : {res['risk_reward']}")
                m6.metric("Volume", f"{res['vol_ratio']}x", "above avg")
                
                st.markdown("<hr class='divider'>", unsafe_allow_html=True)
                
                col_left, col_right = st.columns([3, 2])
                
                with col_left:
                    # Technical indicators
                    st.markdown("""<div style="font-family:'Space Mono',monospace;font-size:10px;color:#6b7280;letter-spacing:0.1em;">SIGNALS</div>""", unsafe_allow_html=True)
                    st.markdown(render_pills(res['all_signals']), unsafe_allow_html=True)
                    
                    # Technical stats
                    st.markdown("<br>", unsafe_allow_html=True)
                    tc1, tc2, tc3, tc4 = st.columns(4)
                    tc1.metric("RSI", res['rsi'])
                    tc2.metric("ADX", res['adx'])
                    tc3.metric("MA20", f"₹{res['ma_20']}" if res['ma_20'] else "–")
                    tc4.metric("MA50", f"₹{res['ma_50']}" if res['ma_50'] else "–")
                
                with col_right:
                    if res['headlines']:
                        st.markdown("""<div style="font-family:'Space Mono',monospace;font-size:10px;color:#6b7280;letter-spacing:0.1em;margin-bottom:8px;">RECENT NEWS</div>""", unsafe_allow_html=True)
                        for h in res['headlines'][:3]:
                            st.markdown(f"""<div style="font-size:11px;color:#9ca3af;padding:4px 0;border-bottom:1px solid #1f2937;">{h[:80]}{'...' if len(h)>80 else ''}</div>""", unsafe_allow_html=True)
                    
                    if res['analyst_target']:
                        upside = round((res['analyst_target'] - res['cmp']) / res['cmp'] * 100, 1)
                        color = "#00ff88" if upside > 0 else "#ef4444"
                        st.markdown(f"""<br><div style="font-family:'Space Mono',monospace;font-size:11px;">
                        Analyst Target: <span style="color:{color};">₹{res['analyst_target']} ({'+' if upside>0 else ''}{upside}%)</span>
                        </div>""", unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Action buttons
                btn1, btn2, btn3 = st.columns([2, 1, 1])
                with btn1:
                    if st.button(f"✅ Confirm Buy {res['ticker']} @ ₹{res['cmp']}", key=f"buy_{res['ticker']}"):
                        buy_stock(res)
                with btn2:
                    if st.button(f"👁 Watchlist", key=f"wl_{res['ticker']}"):
                        add_watchlist(res['ticker'])
                with btn3:
                    chart_url = f"https://finance.yahoo.com/chart/{res['ticker']}.NS"
                    st.link_button("📊 Chart", chart_url)

    elif 'scan_results' in st.session_state and not st.session_state.scan_results:
        st.warning("No stocks matched your criteria. Try lowering the Min Score or increasing Max BO Distance.")

# ══════════════════════════════════════════════
# TAB 2: PORTFOLIO
# ══════════════════════════════════════════════
with tabs[1]:
    portfolio = st.session_state.db["portfolio"]
    st.markdown("#### Active Positions")
    
    if not portfolio:
        st.info("No open positions. Run the scanner and buy a stock.")
    else:
        # Fetch live prices in parallel
        def fetch_live(s):
            try:
                return round(yf.Ticker(f"{s['ticker']}.NS").fast_info['last_price'], 2)
            except:
                return s['buy_price']
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
            live_prices = list(ex.map(fetch_live, portfolio))
        
        total_invested = sum(s['buy_price'] for s in portfolio)
        total_current  = sum(lp for lp in live_prices)
        total_pnl      = total_current - total_invested
        total_pnl_pct  = (total_pnl / total_invested * 100) if total_invested > 0 else 0
        
        # Summary row
        sm1, sm2, sm3, sm4 = st.columns(4)
        sm1.metric("Open Positions", len(portfolio))
        sm2.metric("Total Invested", f"₹{round(total_invested, 2)}")
        sm3.metric("Current Value", f"₹{round(total_current, 2)}")
        sm4.metric("Unrealized P&L", f"₹{round(total_pnl, 2)}", f"{total_pnl_pct:+.2f}%")
        
        st.markdown("<hr class='divider'>", unsafe_allow_html=True)
        
        for i, (s, live_price) in enumerate(zip(portfolio, live_prices)):
            pnl     = round(live_price - s['buy_price'], 2)
            pnl_pct = round((pnl / s['buy_price']) * 100, 2)
            color   = "#00ff88" if pnl >= 0 else "#ef4444"
            
            # Check alerts
            sl_hit  = live_price <= s['sl']
            tgt_hit = live_price >= s['target']
            
            if sl_hit:
                st.error(f"⚠️ **{s['ticker']}** has hit Stop Loss! Consider selling.")
            if tgt_hit:
                st.success(f"🎯 **{s['ticker']}** has hit Target! Consider booking profit.")
            
            with st.container(border=True):
                col1, col2, col3, col4, col5 = st.columns([2, 2, 3, 2, 1])
                
                col1.markdown(f"""
                <div style="font-family:'Syne',sans-serif;font-weight:800;font-size:20px;color:{color};">
                {s['ticker']}
                </div>
                <div style="font-family:'Space Mono',monospace;font-size:10px;color:#6b7280;">
                Score: {s.get('score','–')} | {s.get('grade','–')}
                </div>
                """, unsafe_allow_html=True)
                
                col2.metric("Live Price", f"₹{live_price}", f"{pnl_pct:+.2f}%")
                
                col3.markdown(f"""
                <div style="font-family:'Space Mono',monospace;font-size:11px;line-height:2;">
                Buy: <b>₹{s['buy_price']}</b> &nbsp;|&nbsp; Date: {s['date']}<br>
                Target: <b style="color:#00ff88;">₹{s['target']}</b> &nbsp;|&nbsp; SL: <b style="color:#ef4444;">₹{s['sl']}</b><br>
                R:R = 1:{s.get('rr','–')} &nbsp;|&nbsp; BO Level: ₹{s.get('bo_level','–')}
                </div>
                """, unsafe_allow_html=True)
                
                col4.metric("Unrealized P&L", f"₹{pnl}", f"{pnl_pct:+.2f}%")
                
                with col5:
                    if st.button(f"Sell", key=f"sell_{i}"):
                        sell_stock(i, live_price)

# ══════════════════════════════════════════════
# TAB 3: TRADE HISTORY
# ══════════════════════════════════════════════
with tabs[2]:
    sold_data = st.session_state.db["sold"]
    st.markdown("#### Closed Positions")
    
    if not sold_data:
        st.info("No closed positions yet.")
    else:
        df_sold = pd.DataFrame(sold_data)
        
        # Stats
        total_realized = round(df_sold['pnl'].sum(), 2)
        wins  = (df_sold['pnl'] > 0).sum()
        losses = (df_sold['pnl'] <= 0).sum()
        win_rate = round(wins / len(df_sold) * 100, 1)
        avg_win  = round(df_sold[df_sold['pnl'] > 0]['pnl'].mean(), 2) if wins > 0 else 0
        avg_loss = round(df_sold[df_sold['pnl'] <= 0]['pnl'].mean(), 2) if losses > 0 else 0
        
        h1, h2, h3, h4, h5 = st.columns(5)
        h1.metric("Total Realized P&L", f"₹{total_realized}", delta=total_realized)
        h2.metric("Total Trades", len(df_sold))
        h3.metric("Win Rate", f"{win_rate}%")
        h4.metric("Avg Win", f"₹{avg_win}")
        h5.metric("Avg Loss", f"₹{avg_loss}")
        
        st.markdown("<hr class='divider'>", unsafe_allow_html=True)
        
        # Styled table
        display_cols = ['ticker','buy_price','sell_price','pnl','pnl_pct','date','sell_date','outcome']
        df_display = df_sold[[c for c in display_cols if c in df_sold.columns]].copy()
        df_display.columns = [c.upper() for c in df_display.columns]
        
        def style_pnl(val):
            if isinstance(val, (int, float)):
                return f'color: {"#00ff88" if val > 0 else "#ef4444"}'
            return ''
        
        st.dataframe(
            df_display.style.applymap(style_pnl, subset=[c for c in ['PNL','PNL_PCT'] if c in df_display.columns]),
            use_container_width=True,
            hide_index=True
        )
        
        # Export
        csv = df_display.to_csv(index=False)
        st.download_button("⬇️ Export CSV", csv, "trade_history.csv", "text/csv")

# ══════════════════════════════════════════════
# TAB 4: WATCHLIST
# ══════════════════════════════════════════════
with tabs[3]:
    wl = st.session_state.db.get("watchlist", [])
    st.markdown("#### Watchlist")
    
    col_add1, col_add2 = st.columns([3, 1])
    with col_add1:
        manual_ticker = st.text_input("Add ticker manually (e.g. INFY)", placeholder="INFY")
    with col_add2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Add") and manual_ticker:
            add_watchlist(manual_ticker.upper())
    
    if not wl:
        st.info("No stocks in watchlist. Add from scanner or manually.")
    else:
        def fetch_wl_data(symbol):
            try:
                t = yf.Ticker(f"{symbol}.NS")
                lp = round(t.fast_info['last_price'], 2)
                info = t.info
                return {
                    "ticker": symbol,
                    "price": lp,
                    "pe": round(info.get('trailingPE', 0) or 0, 1),
                    "target": round(info.get('targetMeanPrice', 0) or 0, 2),
                }
            except:
                return {"ticker": symbol, "price": "–", "pe": "–", "target": "–"}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
            wl_data = list(ex.map(fetch_wl_data, wl))
        
        for wd in wl_data:
            wc1, wc2, wc3, wc4, wc5 = st.columns([2, 2, 2, 2, 1])
            wc1.markdown(f"**{wd['ticker']}**")
            wc2.metric("Price", f"₹{wd['price']}")
            wc3.metric("PE Ratio", wd['pe'])
            wc4.metric("Analyst Target", f"₹{wd['target']}" if wd['target'] else "–")
            with wc5:
                if st.button("Remove", key=f"rmwl_{wd['ticker']}"):
                    wl.remove(wd['ticker'])
                    st.session_state.db["watchlist"] = wl
                    save_data(st.session_state.db)
                    st.rerun()
