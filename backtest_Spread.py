import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import matplotlib.dates as mdates
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
import warnings
warnings.filterwarnings('ignore')

st.title("Regression-Based Real Rate Strategy")
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
st.sidebar.header("Model Parameters")
lookback_days = st.sidebar.slider("Regression Lookback Days", 30, 252, 126)
min_r2 = st.sidebar.slider("Minimum R² for Trading", 0.1, 0.9, 0.3, 0.05)

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
    coefficients = np.full((len(y), 2), np.nan)  # intercept, slope
    
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
        r_squared[i] = r2_score(y_clean, y_pred_all)
        
        # Store coefficients
        coefficients[i, 0] = model.intercept_
        coefficients[i, 1] = model.coef_[0]
    
    return predictions, r_squared, coefficients

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
        
        # Calculate yield spread
        df['yield_spread'] = df['domestic_yield'] - df['foreign_yield']
        
        st.write(f"Data loaded: {len(df)} days")
        st.write(f"Date range: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")
        
        # Perform rolling regression: FX_Price = f(Yield_Spread)
        fx_prices = df['fx_price'].values
        yield_spreads = df['yield_spread'].values
        
        st.write("Running rolling regression analysis...")
        real_rates, r_squared_values, coeffs = rolling_regression(fx_prices, yield_spreads, lookback_days)
        
        # Add results to dataframe
        df['real_rate'] = real_rates
        df['r_squared'] = r_squared_values
        df['intercept'] = coeffs[:, 0]
        df['slope'] = coeffs[:, 1]
        
        # Find Mondays for trading signals
        df['weekday'] = df.index.weekday
        df['is_monday'] = df['weekday'] == 0
        
        # Filter out low R² periods
        df['tradeable'] = df['r_squared'] >= min_r2
        
        # Get Monday dates where we can trade
        monday_dates = df[(df['is_monday']) & (df['tradeable']) & (~df['real_rate'].isna())].index
        
        st.write(f"Tradeable Mondays (R² ≥ {min_r2}): {len(monday_dates)} out of {len(df[df['is_monday']])} total Mondays")
        
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
            entry_real_rate = None
            
            for monday in monday_dates:
                # Check if we should close existing position
                if current_position != 0 and entry_date is not None:
                    days_held = (monday - entry_date).days
                    if days_held >= hold_days:
                        # Close position
                        exit_price = df_temp.loc[monday, 'fx_price']
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
                    real_rate = df_temp.loc[monday, 'real_rate']
                    fx_price = df_temp.loc[monday, 'fx_price']
                    r2 = df_temp.loc[monday, 'r_squared']
                    
                    if pd.notna(real_rate) and r2 >= min_r2:
                        if real_rate > fx_price:
                            # Buy signal - real rate suggests FX should be higher
                            current_position = 1
                            entry_date = monday
                            entry_price = fx_price
                            entry_real_rate = real_rate
                            df_temp.loc[monday, 'signal'] = 'Buy'
                            
                        elif real_rate < fx_price:
                            # Sell signal - real rate suggests FX should be lower
                            current_position = -1
                            entry_date = monday
                            entry_price = fx_price
                            entry_real_rate = real_rate
                            df_temp.loc[monday, 'signal'] = 'Sell'
            
            # Close any remaining position at the end
            if current_position != 0 and entry_date is not None:
                last_date = df_temp.index[-1]
                exit_price = df_temp.loc[last_date, 'fx_price']
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
            
            results[hold_months] = {
                'df': df_temp,
                'positions': positions
            }
        
        # Display model diagnostics
        st.header("Model Diagnostics")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            avg_r2 = df['r_squared'].mean()
            st.metric("Average R²", f"{avg_r2:.3f}")
        
        with col2:
            tradeable_pct = (df['tradeable'].sum() / len(df)) * 100
            st.metric("Tradeable Days %", f"{tradeable_pct:.1f}%")
            
        with col3:
            current_slope = df['slope'].iloc[-1] if not pd.isna(df['slope'].iloc[-1]) else 0
            st.metric("Current Slope", f"{current_slope:.4f}")
        
        # Performance summary
        st.header("Strategy Performance")
        
        perf_data = []
        for hold_months in [1, 2, 3]:
            positions = results[hold_months]['positions']
            if positions:
                total_pnl = sum(p['pnl'] for p in positions)
                avg_pnl = total_pnl / len(positions)
                win_rate = sum(1 for p in positions if p['pnl'] > 0) / len(positions) * 100
                avg_pnl_pct = sum(p['pnl_pct'] for p in positions) / len(positions)
                
                perf_data.append({
                    'Hold Period': f"{hold_months} months",
                    'Total Trades': len(positions),
                    'Total PnL': f"{total_pnl:.4f}",
                    'Avg PnL': f"{avg_pnl:.4f}",
                    'Avg PnL %': f"{avg_pnl_pct:.2f}%",
                    'Win Rate': f"{win_rate:.1f}%"
                })
        
        if perf_data:
            st.dataframe(pd.DataFrame(perf_data))
        
        # Plotting
        selected_period = st.selectbox("Select holding period to visualize", [1, 2, 3])
        
        df_plot = results[selected_period]['df']
        
        # Create subplots
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        # Top left: FX Price vs Real Rate
        valid_data = df_plot.dropna(subset=['real_rate'])
        ax1.plot(valid_data.index, valid_data['fx_price'], label='FX Price', color='black', linewidth=1)
        ax1.plot(valid_data.index, valid_data['real_rate'], label='Real Rate (Predicted)', color='blue', linewidth=1, alpha=0.7)
        
        # Add buy/sell signals
        buy_signals = df_plot[df_plot['signal'] == 'Buy']
        sell_signals = df_plot[df_plot['signal'] == 'Sell']
        
        if len(buy_signals) > 0:
            ax1.scatter(buy_signals.index, buy_signals['fx_price'], marker='^', color='green', s=100, label='Buy Signal', zorder=5)
        if len(sell_signals) > 0:
            ax1.scatter(sell_signals.index, sell_signals['fx_price'], marker='v', color='red', s=100, label='Sell Signal', zorder=5)
        
        ax1.set_title(f'FX Price vs Real Rate ({selected_period} Month Hold)')
        ax1.set_ylabel('Price')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Top right: Yield Spread
        ax2.plot(df_plot.index, df_plot['yield_spread'], label='Yield Spread', color='orange', linewidth=1)
        ax2.axhline(0, color='gray', linestyle='--', alpha=0.5)
        ax2.set_title('Yield Spread (Domestic - Foreign)')
        ax2.set_ylabel('Yield Spread (%)')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Bottom left: R² over time
        ax3.plot(valid_data.index, valid_data['r_squared'], label='R²', color='purple', linewidth=1)
        ax3.axhline(min_r2, color='red', linestyle='--', alpha=0.7, label=f'Min R² ({min_r2})')
        ax3.set_title('Model R² Over Time')
        ax3.set_ylabel('R²')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # Bottom right: Regression coefficients
        ax4.plot(valid_data.index, valid_data['slope'], label='Slope', color='green', linewidth=1)
        ax4.axhline(0, color='gray', linestyle='--', alpha=0.5)
        ax4.set_title('Regression Slope Over Time')
        ax4.set_xlabel('Date')
        ax4.set_ylabel('Slope')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        # Format x-axis
        for ax in [ax1, ax2, ax3, ax4]:
            ax.xaxis.set_major_formatter(DateFormatter("%Y-%m"))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        
        plt.tight_layout()
        st.pyplot(fig)
        
        # Show detailed trades
        if results[selected_period]['positions']:
            st.header(f"Detailed Trades ({selected_period} Month Hold)")
            trades_df = pd.DataFrame(results[selected_period]['positions'])
            trades_df['entry_date'] = pd.to_datetime(trades_df['entry_date']).dt.strftime('%Y-%m-%d')
            trades_df['exit_date'] = pd.to_datetime(trades_df['exit_date']).dt.strftime('%Y-%m-%d')
            st.dataframe(trades_df.round(4))
        
        # Show current regression stats
        st.header("Current Model State")
        if not pd.isna(df['real_rate'].iloc[-1]):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Current FX Price", f"{df['fx_price'].iloc[-1]:.4f}")
            with col2:
                st.metric("Current Real Rate", f"{df['real_rate'].iloc[-1]:.4f}")
            with col3:
                current_diff = df['real_rate'].iloc[-1] - df['fx_price'].iloc[-1]
                st.metric("Difference", f"{current_diff:.4f}")
            with col4:
                signal = "BUY" if current_diff > 0 else "SELL" if current_diff < 0 else "HOLD"
                st.metric("Signal", signal)
        
else:
    st.info("Please upload all three CSV files to start the analysis:")
    st.write("**Strategy Logic:**")
    st.write("1. Calculate yield spread = domestic_yield - foreign_yield")
    st.write("2. Use rolling regression: FX_Price = f(Yield_Spread)")
    st.write("3. Generate 'real rate' predictions from the model")
    st.write("4. Buy on Monday if real_rate > fx_price")
    st.write("5. Sell on Monday if real_rate < fx_price")
    st.write("6. Only trade when model R² is above minimum threshold")
