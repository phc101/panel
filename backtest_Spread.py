import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import matplotlib.dates as mdates
from datetime import datetime, timedelta

st.title("Real Rate Yield Spread Strategy")
st.write("Upload CSV files for currency pair, domestic bond yield, and foreign bond yield")

# File uploaders
col1, col2, col3 = st.columns(3)

with col1:
    fx_file = st.file_uploader("Currency Pair CSV", type="csv", key="fx")
    
with col2:
    domestic_file = st.file_uploader("Domestic Bond Yield CSV", type="csv", key="domestic")
    
with col3:
    foreign_file = st.file_uploader("Foreign Bond Yield CSV", type="csv", key="foreign")

# Strategy parameters
st.sidebar.header("Strategy Parameters")
real_rate_factor = st.sidebar.slider("Real Rate Factor", 0.1, 2.0, 1.0, 0.1)
spread_multiplier = st.sidebar.slider("Spread Multiplier", 0.5, 3.0, 1.0, 0.1)

def load_and_clean_data(file, data_type):
    """Load and clean data from uploaded CSV"""
    if file is None:
        return None
    
    df = pd.read_csv(file)
    df.columns = df.columns.str.strip()
    
    # Find date and price columns
    date_col = None
    price_col = None
    
    for col in df.columns:
        if 'date' in col.lower():
            date_col = col
            break
    
    for col in df.columns:
        if 'price' in col.lower():
            price_col = col
            break
    
    if date_col is None or price_col is None:
        st.error(f"Could not find Date and Price columns in {data_type} file")
        return None
    
    # Clean and prepare data
    df = df.rename(columns={date_col: 'date', price_col: 'price'})
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date').sort_index()
    
    # Remove any non-numeric characters from price (like % signs)
    if df['price'].dtype == 'object':
        df['price'] = df['price'].astype(str).str.replace('%', '').str.replace(',', '')
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
    
    return df[['price']]

# Load all data
if fx_file and domestic_file and foreign_file:
    
    fx_data = load_and_clean_data(fx_file, "FX")
    domestic_data = load_and_clean_data(domestic_file, "Domestic Bond")
    foreign_data = load_and_clean_data(foreign_file, "Foreign Bond")
    
    if fx_data is not None and domestic_data is not None and foreign_data is not None:
        
        # Rename columns for clarity
        fx_data = fx_data.rename(columns={'price': 'fx_price'})
        domestic_data = domestic_data.rename(columns={'price': 'domestic_yield'})
        foreign_data = foreign_data.rename(columns={'price': 'foreign_yield'})
        
        # Merge all data on date
        df = fx_data.join(domestic_data, how='inner').join(foreign_data, how='inner')
        
        # Remove rows with missing data
        df = df.dropna()
        
        if len(df) == 0:
            st.error("No overlapping dates found between the three datasets")
            st.stop()
        
        # Calculate yield spread and real rate
        df['yield_spread'] = df['domestic_yield'] - df['foreign_yield']
        df['real_rate'] = df['fx_price'] * (1 + df['yield_spread'] * spread_multiplier / 100) * real_rate_factor
        
        # Find Mondays for trading signals
        df['weekday'] = df.index.weekday
        df['is_monday'] = df['weekday'] == 0
        
        # Create signals only on Mondays
        df['signal'] = ''
        df['position'] = 0
        
        # Get Monday dates
        monday_dates = df[df['is_monday']].index
        
        st.write(f"Data loaded: {len(df)} total days, {len(monday_dates)} Mondays")
        st.write(f"Date range: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")
        
        # Strategy execution for different holding periods
        results = {}
        
        for hold_months in [1, 2, 3]:
            df_temp = df.copy()
            
            # Calculate holding period in days (approximate)
            hold_days = hold_months * 30
            
            positions = []
            current_position = 0
            entry_date = None
            entry_price = None
            
            for monday in monday_dates:
                # Check if we should close existing position
                if current_position != 0 and entry_date is not None:
                    days_held = (monday - entry_date).days
                    if days_held >= hold_days:
                        # Close position
                        positions.append({
                            'exit_date': monday,
                            'exit_price': df_temp.loc[monday, 'fx_price'],
                            'position': current_position,
                            'entry_date': entry_date,
                            'entry_price': entry_price,
                            'hold_days': days_held,
                            'pnl': (df_temp.loc[monday, 'fx_price'] - entry_price) * current_position
                        })
                        current_position = 0
                        entry_date = None
                        entry_price = None
                
                # Only enter new position if not currently holding
                if current_position == 0:
                    real_rate = df_temp.loc[monday, 'real_rate']
                    fx_price = df_temp.loc[monday, 'fx_price']
                    
                    if real_rate > fx_price:
                        # Buy signal
                        current_position = 1
                        entry_date = monday
                        entry_price = fx_price
                        df_temp.loc[monday, 'signal'] = 'Buy'
                        df_temp.loc[monday, 'position'] = 1
                        
                    elif real_rate < fx_price:
                        # Sell signal
                        current_position = -1
                        entry_date = monday
                        entry_price = fx_price
                        df_temp.loc[monday, 'signal'] = 'Sell'
                        df_temp.loc[monday, 'position'] = -1
            
            # Close any remaining position at the end
            if current_position != 0 and entry_date is not None:
                last_date = df_temp.index[-1]
                positions.append({
                    'exit_date': last_date,
                    'exit_price': df_temp.loc[last_date, 'fx_price'],
                    'position': current_position,
                    'entry_date': entry_date,
                    'entry_price': entry_price,
                    'hold_days': (last_date - entry_date).days,
                    'pnl': (df_temp.loc[last_date, 'fx_price'] - entry_price) * current_position
                })
            
            results[hold_months] = {
                'df': df_temp,
                'positions': positions
            }
        
        # Display results
        st.header("Strategy Results")
        
        # Performance summary
        perf_data = []
        for hold_months in [1, 2, 3]:
            positions = results[hold_months]['positions']
            if positions:
                total_pnl = sum(p['pnl'] for p in positions)
                avg_pnl = total_pnl / len(positions)
                win_rate = sum(1 for p in positions if p['pnl'] > 0) / len(positions) * 100
                
                perf_data.append({
                    'Hold Period': f"{hold_months} months",
                    'Total Trades': len(positions),
                    'Total PnL': f"{total_pnl:.4f}",
                    'Avg PnL per Trade': f"{avg_pnl:.4f}",
                    'Win Rate': f"{win_rate:.1f}%"
                })
        
        if perf_data:
            st.dataframe(pd.DataFrame(perf_data))
        
        # Plotting
        selected_period = st.selectbox("Select holding period to visualize", [1, 2, 3])
        
        df_plot = results[selected_period]['df']
        
        # Create subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))
        
        # Top plot: FX Price vs Real Rate
        ax1.plot(df_plot.index, df_plot['fx_price'], label='FX Price', color='black', linewidth=1)
        ax1.plot(df_plot.index, df_plot['real_rate'], label='Real Rate', color='blue', linewidth=1, alpha=0.7)
        
        # Add buy/sell signals
        buy_signals = df_plot[df_plot['signal'] == 'Buy']
        sell_signals = df_plot[df_plot['signal'] == 'Sell']
        
        ax1.scatter(buy_signals.index, buy_signals['fx_price'], marker='^', color='green', s=100, label='Buy Signal', zorder=5)
        ax1.scatter(sell_signals.index, sell_signals['fx_price'], marker='v', color='red', s=100, label='Sell Signal', zorder=5)
        
        ax1.set_title(f'FX Price vs Real Rate ({selected_period} Month Hold)')
        ax1.set_ylabel('Price')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Bottom plot: Yield Spread
        ax2.plot(df_plot.index, df_plot['yield_spread'], label='Yield Spread', color='orange', linewidth=1)
        ax2.axhline(0, color='gray', linestyle='--', alpha=0.5)
        ax2.set_title('Yield Spread (Domestic - Foreign)')
        ax2.set_xlabel('Date')
        ax2.set_ylabel('Yield Spread (%)')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Format x-axis
        for ax in [ax1, ax2]:
            ax.xaxis.set_major_formatter(DateFormatter("%Y-%m"))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        
        plt.tight_layout()
        st.pyplot(fig)
        
        # Show detailed trades
        if results[selected_period]['positions']:
            st.header(f"Detailed Trades ({selected_period} Month Hold)")
            trades_df = pd.DataFrame(results[selected_period]['positions'])
            trades_df['entry_date'] = trades_df['entry_date'].dt.strftime('%Y-%m-%d')
            trades_df['exit_date'] = trades_df['exit_date'].dt.strftime('%Y-%m-%d')
            trades_df['position'] = trades_df['position'].map({1: 'Long', -1: 'Short'})
            st.dataframe(trades_df)
        
        # Show current data sample
        st.header("Data Sample")
        st.dataframe(df[['fx_price', 'domestic_yield', 'foreign_yield', 'yield_spread', 'real_rate']].head(10))
        
else:
    st.info("Please upload all three CSV files to start the analysis:")
    st.write("1. **Currency Pair**: FX price data")
    st.write("2. **Domestic Bond**: Domestic bond yield data") 
    st.write("3. **Foreign Bond**: Foreign bond yield data")
    st.write("4. Strategy trades only on Mondays")
    st.write("5. Tests 1, 2, and 3 month holding periods")
