import streamlit as st
import pandas as pd
import numpy as np

# =========================
# 📌 STREAMLIT UI
# =========================
st.set_page_config(page_title="ORB V6 Institutional", layout="wide")

st.title("🔥 ORB Version 6 — Institutional Engine")

# Inputs
orb_minutes = st.sidebar.number_input("ORB Duration (Minutes)", value=5)
rr_ratio = st.sidebar.number_input("Risk Reward Ratio", value=2.0)

use_atr_filter = st.sidebar.checkbox("ATR Filter", True)
use_trailing = st.sidebar.checkbox("Trailing Stop", True)
use_scaling = st.sidebar.checkbox("Scaling Entries", True)
use_chop_filter = st.sidebar.checkbox("Chop Filter", True)

atr_len = st.sidebar.number_input("ATR Length", value=14)
atr_multiplier = st.sidebar.number_input("ATR Multiplier", value=1.2)

# =========================
# 📂 DATA UPLOAD
# =========================
uploaded_file = st.file_uploader("Upload OHLCV CSV", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # Ensure proper columns
    df.columns = [c.lower() for c in df.columns]

    # Expect: time, open, high, low, close, volume
    df['time'] = pd.to_datetime(df['time'])

    # =========================
    # 📊 ATR CALCULATION
    # =========================
    df['tr'] = np.maximum(df['high'] - df['low'],
                 np.maximum(abs(df['high'] - df['close'].shift(1)),
                            abs(df['low'] - df['close'].shift(1))))
    
    df['atr'] = df['tr'].rolling(atr_len).mean()
    df['atr_avg'] = df['atr'].rolling(20).mean()
    df['atr_valid'] = df['atr'] > df['atr_avg'] * atr_multiplier

    # =========================
    # ⏱️ ORB CALCULATION
    # =========================
    df['date'] = df['time'].dt.date
    df['orb_high'] = np.nan
    df['orb_low'] = np.nan

    results = []

    for date, group in df.groupby('date'):
        group = group.copy()

        session_start = group.iloc[0]['time']
        orb_end_time = session_start + pd.Timedelta(minutes=orb_minutes)

        orb_data = group[group['time'] <= orb_end_time]

        if len(orb_data) == 0:
            continue

        orb_high = orb_data['high'].max()
        orb_low = orb_data['low'].min()

        group['orb_high'] = orb_high
        group['orb_low'] = orb_low

        group['after_orb'] = group['time'] > orb_end_time

        # =========================
        # 📉 CHOP FILTER
        # =========================
        range_orb = orb_high - orb_low
        group['is_choppy'] = range_orb < group['atr'] * 0.5

        # =========================
        # 🚀 BREAKOUT
        # =========================
        group['long_break'] = (group['after_orb']) & (group['close'] > orb_high)
        group['short_break'] = (group['after_orb']) & (group['close'] < orb_low)

        group['valid_market'] = True

        if use_atr_filter:
            group['valid_market'] &= group['atr_valid']

        if use_chop_filter:
            group['valid_market'] &= ~group['is_choppy']

        group['long_entry'] = group['long_break'] & group['valid_market']
        group['short_entry'] = group['short_break'] & group['valid_market']

        # =========================
        # 🎯 BACKTEST ENGINE
        # =========================
        position = 0
        entry_price = 0
        pnl = 0
        trades = 0
        wins = 0

        for i in range(len(group)):
            row = group.iloc[i]

            if position == 0:
                if row['long_entry']:
                    position = 1
                    entry_price = row['close']
                    sl = orb_low
                    tp = entry_price + (entry_price - sl) * rr_ratio
                    trades += 1

                elif row['short_entry']:
                    position = -1
                    entry_price = row['close']
                    sl = orb_high
                    tp = entry_price - (sl - entry_price) * rr_ratio
                    trades += 1

            elif position == 1:
                if row['low'] <= sl:
                    pnl += (sl - entry_price)
                    position = 0
                elif row['high'] >= tp:
                    pnl += (tp - entry_price)
                    wins += 1
                    position = 0

            elif position == -1:
                if row['high'] >= sl:
                    pnl += (entry_price - sl)
                    position = 0
                elif row['low'] <= tp:
                    pnl += (entry_price - tp)
                    wins += 1
                    position = 0

        results.append({
            "date": date,
            "trades": trades,
            "wins": wins,
            "pnl": pnl
        })

    # =========================
    # 📊 RESULTS
    # =========================
    results_df = pd.DataFrame(results)

    total_trades = results_df['trades'].sum()
    total_wins = results_df['wins'].sum()
    total_pnl = results_df['pnl'].sum()

    win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0

    st.subheader("📊 Performance Summary")

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Trades", total_trades)
    col2.metric("Win Rate (%)", round(win_rate, 2))
    col3.metric("Total PnL", round(total_pnl, 2))

    st.dataframe(results_df)

else:
    st.info("Upload a CSV file with columns: time, open, high, low, close, volume")
