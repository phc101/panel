import streamlit as st
import pandas as pd
from datetime import datetime
import io

st.set_page_config(page_title="Pivot Strategy", layout="wide")

st.title("📈 7-Day Rolling Pivot Points Trading Strategy")
st.write("Upload your USD/PLN CSV file to analyze trading signals.")

uploaded_file = st.file_uploader("Upload CSV", type="csv")

@st.cache_data
def load_data(file):
    content = file.read().decode('utf-8')
    lines = content.strip().split('\n')
    headers = lines[0].split(',')
    rows = [line.split(',') for line in lines[1:] if len(line.split(',')) >= 7]

    data = []
    for row in rows:
        try:
            date = datetime.strptime(row[0].replace('"', ''), "%b %d, %Y")
            open_price = float(row[2].replace('"', '').replace(',', ''))
            high = float(row[3].replace('"', '').replace(',', ''))
            low = float(row[4].replace('"', '').replace(',', ''))
            close = float(row[1].replace('"', '').replace(',', ''))
            change_percent = row[6].replace('"', '')
            data.append({
                "date": date,
                "date_str": row[0].replace('"', ''),
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "change_percent": change_percent
            })
        except Exception:
            continue

    df = pd.DataFrame(data)
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

def calculate_pivots(df):
    processed = []

    for i in range(len(df)):
        row = df.iloc[i]
        pivots = None
        signal = "NO TRADE"
        pnl = None
        pnl_pct = None

        if i >= 7:
            last7 = df.iloc[i-7:i]
            avg_high = last7["high"].mean()
            avg_low = last7["low"].mean()
            avg_close = last7["close"].mean()
            pp = (avg_high + avg_low + avg_close) / 3

            r1 = (2 * pp) - avg_low
            r2 = pp + (avg_high - avg_low)
            s1 = (2 * pp) - avg_high
            s2 = pp - (avg_high - avg_low)

            open_price = row["open"]
            tolerance = 0.01

            if abs(open_price - s1) / s1 <= tolerance or abs(open_price - s2) / s2 <= tolerance:
                signal = "BUY"
                pnl = row["close"] - open_price
            elif abs(open_price - r1) / r1 <= tolerance or abs(open_price - r2) / r2 <= tolerance:
                signal = "SELL"
                pnl = open_price - row["close"]

            if pnl is not None:
                pnl_pct = (pnl / open_price) * 100

            pivots = {
                "PP": pp,
                "R1": r1,
                "R2": r2,
                "S1": s1,
                "S2": s2
            }

        processed.append({
            "Date": row["date_str"],
            "Open": row["open"],
            "High": row["high"],
            "Low": row["low"],
            "Close": row["close"],
            "PP": pivots["PP"] if pivots else None,
            "R1": pivots["R1"] if pivots else None,
            "R2": pivots["R2"] if pivots else None,
            "S1": pivots["S1"] if pivots else None,
            "S2": pivots["S2"] if pivots else None,
            "Signal": signal,
            "PnL": pnl,
            "PnL %": pnl_pct
        })

    return pd.DataFrame(processed)

if uploaded_file:
    try:
        raw_data = load_data(uploaded_file)
        df = calculate_pivots(raw_data)

        st.success("✅ Data loaded and processed successfully!")
        
        # Metrics
        trading_days = df[df["Signal"] != "NO TRADE"]
        buy_trades = trading_days[trading_days["Signal"] == "BUY"]
        sell_trades = trading_days[trading_days["Signal"] == "SELL"]
        win_trades = trading_days[trading_days["PnL"] > 0]
        total_pnl = trading_days["PnL"].sum()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📅 Total Days", len(df))
        col2.metric("📊 Trading Days", len(trading_days))
        col3.metric("✅ Win Rate", f"{(len(win_trades)/len(trading_days)*100):.1f}%" if len(trading_days) > 0 else "0%")
        col4.metric("💰 Total P&L", f"{total_pnl:.4f}")

        # Signal breakdown
        st.markdown("### 📉 Signal Summary")
        col1, col2, col3 = st.columns(3)

        col1.metric("BUY Signals", f"{len(buy_trades)} ({(len(buy_trades)/len(trading_days)*100):.1f}%)" if len(trading_days) > 0 else "0")
        col2.metric("SELL Signals", f"{len(sell_trades)} ({(len(sell_trades)/len(trading_days)*100):.1f}%)" if len(trading_days) > 0 else "0")
        col3.metric("No Trade", f"{len(df) - len(trading_days)}")

        st.markdown("### 📐 Strategy Rules")
        with st.expander("How it works"):
            st.markdown("""
            - **BUY** if Open is near S1 or S2 (±1%)
            - **SELL** if Open is near R1 or R2 (±1%)
            - **Close** all trades end of day.
            - **Pivot =** (High + Low + Close)/3
            - **Support/Resistance:**
                - R1 = (2 × PP) - Low
                - R2 = PP + (High - Low)
                - S1 = (2 × PP) - High
                - S2 = PP - (High - Low)
            """)

        # Table toggle
        show_only_trades = st.checkbox("Show only trading days", value=False)
        display_df = df[df["Signal"] != "NO TRADE"] if show_only_trades else df

        st.markdown("### 📋 Results Table")
        st.dataframe(display_df, use_container_width=True)

        # Chart preview
        st.markdown("### 📈 PnL Over Time")
        st.line_chart(trading_days.set_index("Date")["PnL"])

    except Exception as e:
        st.error("⚠️ Error loading file.")
        st.exception(e)
else:
    st.info("📤 Please upload a CSV file to get started.")
