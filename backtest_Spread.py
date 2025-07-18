import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import matplotlib.dates as mdates

st.title("FX/Bond Yield Backtesting Strategy")

# File uploader
uploaded_file = st.file_uploader("Upload your CSV file from Investing.com", type="csv")

if uploaded_file is not None:
    # Load the data
    df = pd.read_csv(uploaded_file)
    
    # Display the original column names to help debug
    st.write("Original columns:", df.columns.tolist())
    
    # Clean up column names (Investing.com files often have extra spaces)
    df.columns = df.columns.str.strip()
    
    # Handle different possible column names from Investing.com
    date_col = None
    price_col = None
    
    # Look for date column
    for col in df.columns:
        if 'date' in col.lower():
            date_col = col
            break
    
    # Look for price column
    for col in df.columns:
        if 'price' in col.lower():
            price_col = col
            break
    
    if date_col is None or price_col is None:
        st.error("Could not find Date and Price columns. Please check your CSV format.")
        st.write("Available columns:", df.columns.tolist())
        st.stop()
    
    # Rename columns to match your code
    df = df.rename(columns={date_col: 'date', price_col: 'price'})
    
    # Convert date and set as index
    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    
    # Sort by date (Investing.com files are often in reverse chronological order)
    df = df.sort_index()
    
    # Display basic info
    st.write(f"Data loaded: {len(df)} rows from {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")
    
    # Calculate Z-score
    df["z"] = (df["price"] - df["price"].rolling(20).mean()) / df["price"].rolling(20).std()
    
    # Define strategy
    signal = []
    position = 0  # 1 for long, -1 for short, 0 for none
    holding_counter = 0
    entry_price = 0
    
    for i in range(len(df)):
        z = df["z"].iloc[i]
        price = df["price"].iloc[i]
        
        if position == 0:
            if z <= -2:
                position = 1
                entry_price = price
                holding_counter = 8
                signal.append("Buy")
            elif z >= 2:
                position = -1
                entry_price = price
                holding_counter = 8
                signal.append("Sell")
            else:
                signal.append("")
        elif position == 1:
            if price <= entry_price * 0.99:
                signal.append("SL")
                position = 0
            elif holding_counter > 1:
                holding_counter -= 1
                signal.append("Hold")
            else:
                signal.append("Close")
                position = 0
        elif position == -1:
            if price >= entry_price * 1.01:
                signal.append("SL")
                position = 0
            elif holding_counter > 1:
                holding_counter -= 1
                signal.append("Hold")
            else:
                signal.append("Close")
                position = 0
        
        entry_price = entry_price if position != 0 else 0
    
    df["signal"] = signal
    
    # Plot
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(df.index, df["price"], label="Price", color="black")
    ax.axhline(df["price"].mean(), color="gray", linestyle="--", linewidth=0.8)
    
    buy_signals = df[df["signal"] == "Buy"]
    sell_signals = df[df["signal"] == "Sell"]
    close_signals = df[df["signal"] == "Close"]
    sl_signals = df[df["signal"] == "SL"]
    
    ax.plot(buy_signals.index, buy_signals["price"], "^", color="green", markersize=10, label="Buy")
    ax.plot(sell_signals.index, sell_signals["price"], "v", color="red", markersize=10, label="Sell")
    ax.plot(close_signals.index, close_signals["price"], "o", color="blue", markersize=6, label="Close")
    ax.plot(sl_signals.index, sl_signals["price"], "x", color="orange", markersize=6, label="SL")
    
    ax.set_title("Price with Trading Signals")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price")
    ax.legend()
    ax.grid(True)
    ax.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    fig.autofmt_xdate()
    plt.tight_layout()
    
    # Display the plot in Streamlit
    st.pyplot(fig)
    
    # Show signals and dates
    signals_df = df[df["signal"] != ""][["price", "signal"]]
    if not signals_df.empty:
        st.write("Trading Signals:")
        st.dataframe(signals_df)
    else:
        st.write("No trading signals generated with current parameters.")
        
else:
    st.info("Please upload a CSV file to start the analysis.")
    st.write("Expected format: CSV file from Investing.com with Date and Price columns")
