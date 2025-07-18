import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import matplotlib.dates as mdates
from sklearn.linear_model import LinearRegression
import warnings
warnings.filterwarnings('ignore')

st.title("Real Rate vs Historical Rate Analysis")
st.write("Upload CSV files for currency pair, domestic bond yield, and foreign bond yield")

# File uploaders
col1, col2, col3 = st.columns(3)

with col1:
    fx_file = st.file_uploader("Currency Pair CSV", type="csv", key="fx")
    
with col2:
    domestic_file = st.file_uploader("Domestic Bond Yield CSV", type="csv", key="domestic")
    
with col3:
    foreign_file = st.file_uploader("Foreign Bond Yield CSV", type="csv", key="foreign")

# Model parameters
st.sidebar.header("Model Parameters")
lookback_days = st.sidebar.slider("Regression Lookback Days", 30, 252, 126)
min_r2 = st.sidebar.slider("Minimum R² for Trading", 0.1, 0.9, 0.3, 0.05)

st.sidebar.header("Strategy Parameters")
hold_period_months = st.sidebar.slider("Holding Period (Months)", 1, 12, 3)
show_detailed_trades = st.sidebar.checkbox("Show Detailed Trades", True)

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

def rolling_regression(y, x, window):
    """Perform rolling regression and return predictions"""
    predictions = np.full(len(y), np.nan)
    r_squared = np.full(len(y), np.nan)
    
    for i in range(window-1, len(y)):
        start_idx = i - window + 1
        
        # Get data for regression
        y_window = y[start_idx:i+1]
        x_window = x[start_idx:i+1]
        
        # Remove NaN values
        mask = ~(np.isnan(y_window) | np.isnan(x_window))
        if mask.sum() < 10:  # Need at least 10 data points
            continue
            
        y_clean = y_window[mask]
        x_clean = x_window[mask].reshape(-1, 1)
        
        # Fit regression
        model = LinearRegression()
        model.fit(x_clean, y_clean)
        
        # Make prediction for current point
        prediction = model.predict([[x[i]]])[0]
        predictions[i] = prediction
        
        # Calculate R²
        y_pred_all = model.predict(x_clean)
        r_squared[i] = np.corrcoef(y_clean, y_pred_all)[0, 1] ** 2
    
    return predictions, r_squared

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
        
        # Show data info before merging
        st.write("**Individual Dataset Info:**")
        st.write(f"- FX data: {len(fx_data)} rows, from {fx_data.index[0].strftime('%Y-%m-%d')} to {fx_data.index[-1].strftime('%Y-%m-%d')}")
        st.write(f"- Domestic bond: {len(domestic_data)} rows, from {domestic_data.index[0].strftime('%Y-%m-%d')} to {domestic_data.index[-1].strftime('%Y-%m-%d')}")
        st.write(f"- Foreign bond: {len(foreign_data)} rows, from {foreign_data.index[0].strftime('%Y-%m-%d')} to {foreign_data.index[-1].strftime('%Y-%m-%d')}")
        
        # Try different merge strategies
        st.write("**Trying different merge strategies:**")
        
        # Show overlap analysis
        all_dates = set(fx_data.index) | set(domestic_data.index) | set(foreign_data.index)
        fx_dates = set(fx_data.index)
        domestic_dates = set(domestic_data.index)
        foreign_dates = set(foreign_data.index)
        
        overlap_all = fx_dates & domestic_dates & foreign_dates
        st.write(f"- Exact date overlap: {len(overlap_all)} days")
        
        # Try outer join first to see all data
        df_outer = fx_data.join(domestic_data, how='outer').join(foreign_data, how='outer')
        st.write(f"- Total unique dates: {len(df_outer)} days")
        
        # Use forward fill to handle missing data
        df = df_outer.fillna(method='ffill').fillna(method='bfill')
        
        # Remove rows where we still have NaN (beginning/end of series)
        df = df.dropna()
        
        if len(df) == 0:
            st.error("No overlapping dates found between the three datasets")
            st.stop()
        
        # Calculate yield spread
        df['yield_spread'] = df['domestic_yield'] - df['foreign_yield']
        
        st.write(f"**Final merged data: {len(df)} days**")
        st.write(f"**Date range: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}**")
        
        # Perform rolling regression: FX_Price = f(Yield_Spread)
        fx_prices = df['fx_price'].values
        yield_spreads = df['yield_spread'].values
        
        st.write("Running rolling regression analysis...")
        with st.spinner("Calculating real rates..."):
            real_rates, r_squared_values = rolling_regression(fx_prices, yield_spreads, lookback_days)
        
        # Add results to dataframe
        df['real_rate'] = real_rates
        df['r_squared'] = r_squared_values
        
        # Trading logic
        df['tradeable'] = df['r_squared'] >= min_r2
        df['weekday'] = df.index.weekday
        df['is_monday'] = df['weekday'] == 0
        
        # Generate trading signals
        df['signal'] = ''
        df['position'] = 0
        
        # Get Monday dates where we can trade
        monday_dates = df[(df['is_monday']) & (df['tradeable']) & (~df['real_rate'].isna())].index
        
        st.write(f"Tradeable Mondays (R² ≥ {min_r2}): {len(monday_dates)} out of {len(df[df['is_monday']])} total Mondays")
        
        # Execute strategy
        hold_days = hold_period_months * 30
        positions = []
        current_position = 0
        entry_date = None
        entry_price = None
        entry_real_rate = None
        
        for monday in monday_dates:
            # Check if we should close existing position
            if current_position != 0 and entry_date is not None:
                days_held = (monday - entry_date).days
                if days_held >= hold_days:
                    # Close position
                    exit_price = df.loc[monday, 'fx_price']
                    pnl = (exit_price - entry_price) * current_position
                    
                    positions.append({
                        'entry_date': entry_date,
                        'exit_date': monday,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'entry_real_rate': entry_real_rate,
                        'position': 'Long' if current_position == 1 else 'Short',
                        'hold_days': days_held,
                        'pnl': pnl,
                        'pnl_pct': (pnl / entry_price) * 100
                    })
                    current_position = 0
                    entry_date = None
                    entry_price = None
                    entry_real_rate = None
            
            # Only enter new position if not currently holding
            if current_position == 0:
                real_rate = df.loc[monday, 'real_rate']
                fx_price = df.loc[monday, 'fx_price']
                r2 = df.loc[monday, 'r_squared']
                
                if pd.notna(real_rate) and r2 >= min_r2:
                    if real_rate > fx_price:
                        # Buy signal - real rate suggests FX should be higher
                        current_position = 1
                        entry_date = monday
                        entry_price = fx_price
                        entry_real_rate = real_rate
                        df.loc[monday, 'signal'] = 'Buy'
                        df.loc[monday, 'position'] = 1
                        
                    elif real_rate < fx_price:
                        # Sell signal - real rate suggests FX should be lower
                        current_position = -1
                        entry_date = monday
                        entry_price = fx_price
                        entry_real_rate = real_rate
                        df.loc[monday, 'signal'] = 'Sell'
                        df.loc[monday, 'position'] = -1
        
        # Close any remaining position at the end
        if current_position != 0 and entry_date is not None:
            last_date = df.index[-1]
            exit_price = df.loc[last_date, 'fx_price']
            pnl = (exit_price - entry_price) * current_position
            
            positions.append({
                'entry_date': entry_date,
                'exit_date': last_date,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'entry_real_rate': entry_real_rate,
                'position': 'Long' if current_position == 1 else 'Short',
                'hold_days': (last_date - entry_date).days,
                'pnl': pnl,
                'pnl_pct': (pnl / entry_price) * 100
            })
        
        # Show basic statistics
        st.header("Strategy Performance")
        
        if positions:
            # Calculate performance metrics
            total_trades = len(positions)
            winning_trades = sum(1 for p in positions if p['pnl'] > 0)
            total_pnl = sum(p['pnl'] for p in positions)
            avg_pnl = total_pnl / total_trades
            win_rate = (winning_trades / total_trades) * 100
            avg_pnl_pct = sum(p['pnl_pct'] for p in positions) / total_trades
            max_pnl = max(p['pnl'] for p in positions)
            min_pnl = min(p['pnl'] for p in positions)
            
            # Display metrics
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric("Total Trades", total_trades)
            with col2:
                st.metric("Win Rate", f"{win_rate:.1f}%")
            with col3:
                st.metric("Total PnL", f"{total_pnl:.4f}")
            with col4:
                st.metric("Avg PnL %", f"{avg_pnl_pct:.2f}%")
            with col5:
                st.metric("Best/Worst", f"{max_pnl:.4f} / {min_pnl:.4f}")
                
        else:
            st.warning(f"No trades generated with current parameters (R² ≥ {min_r2}, {hold_period_months} month hold)")
        
        # Model diagnostics
        st.header("Model Diagnostics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Average R²", f"{np.nanmean(r_squared_values):.3f}")
        with col2:
            st.metric("Current FX Price", f"{df['fx_price'].iloc[-1]:.4f}")
        with col3:
            if not np.isnan(real_rates[-1]):
                st.metric("Current Real Rate", f"{real_rates[-1]:.4f}")
            else:
                st.metric("Current Real Rate", "N/A")
        with col4:
            st.metric("Current Spread", f"{df['yield_spread'].iloc[-1]:.2f}%")
        
        # Main Chart: Real Rate vs Historical Rate with Signals
        st.header("Real Rate vs Historical FX Rate with Trading Signals")
        
        fig, ax = plt.subplots(figsize=(15, 8))
        
        # Plot historical FX price
        ax.plot(df.index, df['fx_price'], 
                label='Historical FX Rate', 
                color='black', 
                linewidth=2, 
                alpha=0.8)
        
        # Plot real rate (predicted FX price from regression)
        valid_mask = ~np.isnan(df['real_rate'])
        valid_data = df[valid_mask]
        
        ax.plot(valid_data.index, valid_data['real_rate'], 
                label='Real Rate (Regression Model)', 
                color='red', 
                linewidth=2, 
                alpha=0.7)
        
        # Add buy/sell signals
        buy_signals = df[df['signal'] == 'Buy']
        sell_signals = df[df['signal'] == 'Sell']
        
        if len(buy_signals) > 0:
            ax.scatter(buy_signals.index, buy_signals['fx_price'], 
                      marker='^', color='green', s=150, 
                      label=f'Buy Signals ({len(buy_signals)})', zorder=5)
        
        if len(sell_signals) > 0:
            ax.scatter(sell_signals.index, sell_signals['fx_price'], 
                      marker='v', color='red', s=150, 
                      label=f'Sell Signals ({len(sell_signals)})', zorder=5)
        
        # Add title and labels
        ax.set_title(f'Real Rate vs Historical FX Rate ({hold_period_months} Month Hold Period)', 
                    fontsize=16, fontweight='bold')
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('FX Rate', fontsize=12)
        ax.legend(fontsize=12)
        ax.grid(True, alpha=0.3)
        
        # Format x-axis
        ax.xaxis.set_major_formatter(DateFormatter("%Y-%m"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig)
        
        # Secondary Chart: Yield Spread
        st.header("Yield Spread Over Time")
        
        fig2, ax2 = plt.subplots(figsize=(15, 6))
        
        ax2.plot(df.index, df['yield_spread'], 
                 label='Yield Spread (Domestic - Foreign)', 
                 color='blue', 
                 linewidth=2)
        
        ax2.axhline(0, color='gray', linestyle='--', alpha=0.5)
        ax2.set_title('Yield Spread (Domestic - Foreign Bond Yields)', fontsize=16, fontweight='bold')
        ax2.set_xlabel('Date', fontsize=12)
        ax2.set_ylabel('Yield Spread (%)', fontsize=12)
        ax2.legend(fontsize=12)
        ax2.grid(True, alpha=0.3)
        
        # Format x-axis
        ax2.xaxis.set_major_formatter(DateFormatter("%Y-%m"))
        ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig2)
        
        # Model Quality Chart: R² over time
        st.header("Model Quality (R²) Over Time")
        
        fig3, ax3 = plt.subplots(figsize=(15, 6))
        
        ax3.plot(valid_data.index, valid_data['r_squared'], 
                 label='R² (Model Fit Quality)', 
                 color='green', 
                 linewidth=2)
        
        ax3.axhline(0.5, color='orange', linestyle='--', alpha=0.7, label='50% R²')
        ax3.axhline(0.3, color='red', linestyle='--', alpha=0.7, label='30% R²')
        
        ax3.set_title('Regression Model Quality Over Time', fontsize=16, fontweight='bold')
        ax3.set_xlabel('Date', fontsize=12)
        ax3.set_ylabel('R² Value', fontsize=12)
        ax3.set_ylim(0, 1)
        ax3.legend(fontsize=12)
        ax3.grid(True, alpha=0.3)
        
        # Format x-axis
        ax3.xaxis.set_major_formatter(DateFormatter("%Y-%m"))
        ax3.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig3)
        
        # Show detailed trades if requested
        if show_detailed_trades and positions:
            st.header(f"Detailed Trading Results ({hold_period_months} Month Hold)")
            trades_df = pd.DataFrame(positions)
            trades_df['entry_date'] = pd.to_datetime(trades_df['entry_date']).dt.strftime('%Y-%m-%d')
            trades_df['exit_date'] = pd.to_datetime(trades_df['exit_date']).dt.strftime('%Y-%m-%d')
            
            # Format numeric columns
            numeric_cols = ['entry_price', 'exit_price', 'entry_real_rate', 'pnl', 'pnl_pct']
            for col in numeric_cols:
                if col in trades_df.columns:
                    trades_df[col] = trades_df[col].round(4)
            
            st.dataframe(trades_df, use_container_width=True)
            
            # Add download button for trades
            csv = trades_df.to_csv(index=False)
            st.download_button(
                label="Download Trade Results as CSV",
                data=csv,
                file_name=f"trading_results_{hold_period_months}m.csv",
                mime="text/csv"
            )
        
        # Current analysis
        if not np.isnan(real_rates[-1]):
            st.header("Current Market Analysis")
            current_fx = df['fx_price'].iloc[-1]
            current_real = real_rates[-1]
            difference = current_real - current_fx
            current_r2 = df['r_squared'].iloc[-1]
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Difference (Real - Historical)", f"{difference:.4f}")
            with col2:
                st.metric("Difference %", f"{(difference/current_fx)*100:.2f}%")
            with col3:
                st.metric("Current R²", f"{current_r2:.3f}")
            with col4:
                if current_r2 >= min_r2:
                    if difference > 0:
                        st.success("BUY Signal")
                    elif difference < 0:
                        st.error("SELL Signal")
                    else:
                        st.info("NEUTRAL")
                else:
                    st.warning("Low R² - No Signal")
                    
        # Show sample data
        st.header("Recent Data Sample")
        sample_data = df[['fx_price', 'domestic_yield', 'foreign_yield', 'yield_spread', 'real_rate', 'r_squared', 'signal']].tail(10)
        st.dataframe(sample_data.round(4))
        
else:
    st.info("Please upload all three CSV files to see the analysis:")
    st.write("**What this will show:**")
    st.write("1. **Historical FX Rate**: Your actual currency pair price over time")
    st.write("2. **Real Rate**: Predicted FX rate based on yield spread regression")
    st.write("3. **Yield Spread**: Domestic bond yield minus foreign bond yield")
    st.write("4. **Model Quality**: R² showing how well the regression fits")
    st.write("")
    st.write("**The Strategy Concept:**")
    st.write("- When Real Rate > Historical Rate → FX may be undervalued (BUY)")
    st.write("- When Real Rate < Historical Rate → FX may be overvalued (SELL)")
