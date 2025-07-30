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
# Changed to exact days instead of months
hold_period_days = st.sidebar.slider("Holding Period (Days)", 1, 365, 90)
position_size = st.sidebar.number_input("Position Size (Volume per Trade)", min_value=1000, max_value=10000000, value=100000, step=10000)
leverage = st.sidebar.slider("Leverage", 1, 20, 1)
strategy_type = st.sidebar.selectbox("Strategy Type", ["Long and Short", "Long Only", "Short Only"])
show_detailed_trades = st.sidebar.checkbox("Show Detailed Trades", True)
entry_frequency = st.sidebar.selectbox("Entry Frequency", ["Monday Only", "Any Day with Signal"])

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
        
        # Trading logic with exact holding period
        df['tradeable'] = df['r_squared'] >= min_r2
        df['weekday'] = df.index.weekday
        df['is_monday'] = df['weekday'] == 0
        
        # Generate trading signals
        df['buy_signal'] = ''
        df['sell_signal'] = ''
        df['long_position'] = 0
        df['short_position'] = 0
        
        # Determine entry dates based on frequency setting
        if entry_frequency == "Monday Only":
            entry_dates = df[(df['is_monday']) & (df['tradeable']) & (~df['real_rate'].isna())].index
            st.write(f"Tradeable Mondays (R² ≥ {min_r2}): {len(entry_dates)} out of {len(df[df['is_monday']])} total Mondays")
        else:
            entry_dates = df[(df['tradeable']) & (~df['real_rate'].isna())].index
            st.write(f"Tradeable Days (R² ≥ {min_r2}): {len(entry_dates)} out of {len(df)} total days")
        
        # Execute strategy with EXACT holding periods
        positions = []
        active_positions = []  # Track all active positions with their exact exit dates
        
        # Create a dictionary for fast date lookups
        date_to_index = {date: idx for idx, date in enumerate(df.index)}
        
        for entry_date in entry_dates:
            real_rate = df.loc[entry_date, 'real_rate']
            fx_price = df.loc[entry_date, 'fx_price']
            r2 = df.loc[entry_date, 'r_squared']
            
            if pd.notna(real_rate) and r2 >= min_r2:
                
                # Calculate exact exit date (hold_period_days business days later)
                # Find the index of current date
                current_idx = date_to_index[entry_date]
                
                # Calculate target exit index
                target_exit_idx = current_idx + hold_period_days
                
                # Make sure we don't go beyond the data
                if target_exit_idx >= len(df):
                    exit_date = df.index[-1]  # Use last available date
                    actual_hold_days = len(df) - 1 - current_idx
                else:
                    exit_date = df.index[target_exit_idx]
                    actual_hold_days = hold_period_days
                
                # Check for positions that should be closed on this date
                positions_to_close = [pos for pos in active_positions if pos['exit_date'] <= entry_date]
                
                for pos in positions_to_close:
                    # Close this position
                    exit_price = df.loc[pos['exit_date'], 'fx_price']
                    exit_real_rate = df.loc[pos['exit_date'], 'real_rate'] if pd.notna(df.loc[pos['exit_date'], 'real_rate']) else pos['entry_real_rate']
                    
                    if pos['position_type'] == 'Long':
                        pnl = exit_price - pos['entry_price']
                    else:  # Short
                        pnl = pos['entry_price'] - exit_price
                    
                    actual_days_held = (pos['exit_date'] - pos['entry_date']).days
                    
                    positions.append({
                        'entry_date': pos['entry_date'],
                        'exit_date': pos['exit_date'],
                        'entry_price': pos['entry_price'],
                        'exit_price': exit_price,
                        'entry_real_rate': pos['entry_real_rate'],
                        'exit_real_rate': exit_real_rate,
                        'position': pos['position_type'],
                        'hold_days': actual_days_held,
                        'target_hold_days': pos['target_hold_days'],
                        'pnl': pnl,
                        'pnl_pct': (pnl / pos['entry_price']) * 100,
                        'position_size': position_size,
                        'leverage': leverage,
                        'nominal_pnl': pnl * position_size * leverage,
                        'margin_used': position_size / leverage if leverage > 0 else position_size
                    })
                
                # Remove closed positions
                active_positions = [pos for pos in active_positions if pos['exit_date'] > entry_date]
                
                # Enter new long position if conditions are met
                if fx_price < real_rate and strategy_type in ["Long and Short", "Long Only"]:
                    active_positions.append({
                        'entry_date': entry_date,
                        'exit_date': exit_date,
                        'entry_price': fx_price,
                        'entry_real_rate': real_rate,
                        'position_type': 'Long',
                        'target_hold_days': hold_period_days
                    })
                    df.loc[entry_date, 'buy_signal'] = 'Buy'
                    df.loc[entry_date, 'long_position'] = len([p for p in active_positions if p['position_type'] == 'Long'])
                
                # Enter new short position if conditions are met
                if fx_price > real_rate and strategy_type in ["Long and Short", "Short Only"]:
                    active_positions.append({
                        'entry_date': entry_date,
                        'exit_date': exit_date,
                        'entry_price': fx_price,
                        'entry_real_rate': real_rate,
                        'position_type': 'Short',
                        'target_hold_days': hold_period_days
                    })
                    df.loc[entry_date, 'sell_signal'] = 'Sell'
                    df.loc[entry_date, 'short_position'] = -len([p for p in active_positions if p['position_type'] == 'Short'])
        
        # Close all remaining positions at their scheduled exit dates or end of data
        for pos in active_positions:
            # Use the scheduled exit date or last available date, whichever comes first
            actual_exit_date = min(pos['exit_date'], df.index[-1])
            exit_price = df.loc[actual_exit_date, 'fx_price']
            exit_real_rate = df.loc[actual_exit_date, 'real_rate'] if pd.notna(df.loc[actual_exit_date, 'real_rate']) else pos['entry_real_rate']
            
            if pos['position_type'] == 'Long':
                pnl = exit_price - pos['entry_price']
            else:  # Short
                pnl = pos['entry_price'] - exit_price
            
            actual_days_held = (actual_exit_date - pos['entry_date']).days
            
            positions.append({
                'entry_date': pos['entry_date'],
                'exit_date': actual_exit_date,
                'entry_price': pos['entry_price'],
                'exit_price': exit_price,
                'entry_real_rate': pos['entry_real_rate'],
                'exit_real_rate': exit_real_rate,
                'position': pos['position_type'],
                'hold_days': actual_days_held,
                'target_hold_days': pos['target_hold_days'],
                'pnl': pnl,
                'pnl_pct': (pnl / pos['entry_price']) * 100,
                'position_size': position_size,
                'leverage': leverage,
                'nominal_pnl': pnl * position_size * leverage,
                'margin_used': position_size / leverage if leverage > 0 else position_size
            })
        
        # Show basic statistics
        st.header("Strategy Performance")
        
        if positions:
            # Calculate performance metrics
            total_trades = len(positions)
            long_trades = [p for p in positions if p['position'] == 'Long']
            short_trades = [p for p in positions if p['position'] == 'Short']
            winning_trades = sum(1 for p in positions if p['pnl'] > 0)
            
            # Holding period analysis
            actual_hold_days = [p['hold_days'] for p in positions]
            target_hold_days = [p['target_hold_days'] for p in positions]
            avg_actual_hold = np.mean(actual_hold_days)
            avg_target_hold = np.mean(target_hold_days)
            
            # Price-based PnL (original)
            total_pnl = sum(p['pnl'] for p in positions)
            avg_pnl = total_pnl / total_trades
            avg_pnl_pct = sum(p['pnl_pct'] for p in positions) / total_trades
            max_pnl = max(p['pnl'] for p in positions)
            min_pnl = min(p['pnl'] for p in positions)
            
            # Nominal PnL (with position size)
            total_nominal_pnl = sum(p['nominal_pnl'] for p in positions)
            avg_nominal_pnl = total_nominal_pnl / total_trades
            max_nominal_pnl = max(p['nominal_pnl'] for p in positions)
            min_nominal_pnl = min(p['nominal_pnl'] for p in positions)
            
            # Total capital deployed (now based on margin, not full position size)
            total_margin_used = sum(p['margin_used'] for p in positions)
            total_capital_deployed = total_margin_used  # This is the actual capital needed
            total_return_pct = (total_nominal_pnl / total_capital_deployed) * 100 if total_capital_deployed > 0 else 0
            
            win_rate = (winning_trades / total_trades) * 100
            
            # Display main metrics
            st.subheader("Overall Performance")
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            
            with col1:
                st.metric("Total Trades", total_trades)
            with col2:
                st.metric("Long/Short", f"{len(long_trades)}/{len(short_trades)}")
            with col3:
                st.metric("Win Rate", f"{win_rate:.1f}%")
            with col4:
                st.metric("Avg PnL %", f"{avg_pnl_pct:.2f}%")
            with col5:
                st.metric("Total Return %", f"{total_return_pct:.2f}%")
            with col6:
                st.metric("Leverage", f"{leverage}:1")
            
            # Display holding period metrics
            st.subheader("Holding Period Analysis")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Target Hold Days", f"{hold_period_days}")
            with col2:
                st.metric("Avg Actual Hold", f"{avg_actual_hold:.1f} days")
            with col3:
                exact_hold_trades = sum(1 for p in positions if p['hold_days'] == p['target_hold_days'])
                exact_hold_pct = (exact_hold_trades / total_trades) * 100
                st.metric("Exact Hold %", f"{exact_hold_pct:.1f}%")
            with col4:
                st.metric("Entry Frequency", entry_frequency)
            
            # Display nominal value metrics
            st.subheader("Nominal Value Performance")
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric("Total Nominal PnL", f"{total_nominal_pnl:,.0f}")
            with col2:
                st.metric("Avg Nominal PnL", f"{avg_nominal_pnl:,.0f}")
            with col3:
                st.metric("Best Trade", f"{max_nominal_pnl:,.0f}")
            with col4:
                st.metric("Worst Trade", f"{min_nominal_pnl:,.0f}")
            with col5:
                st.metric("Position Size", f"{position_size:,}")
            
            # Capital deployment info
            st.subheader("Capital Deployment & Leverage")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Margin Used", f"{total_capital_deployed:,}")
            with col2:
                total_notional = sum(p['position_size'] for p in positions)
                st.metric("Total Notional Value", f"{total_notional:,}")
            with col3:
                leverage_ratio = total_notional / total_capital_deployed if total_capital_deployed > 0 else 1
                st.metric("Effective Leverage", f"{leverage_ratio:.1f}:1")
            with col4:
                if total_capital_deployed > 0:
                    roi_annualized = (total_return_pct / 100) * (365 / (len(df) if len(df) > 0 else 1))
                    st.metric("Annualized ROI", f"{roi_annualized:.1f}%")
                
            # Separate performance for long and short
            if long_trades:
                long_nominal_pnl = sum(p['nominal_pnl'] for p in long_trades)
                long_wins = sum(1 for p in long_trades if p['pnl'] > 0)
                long_win_rate = (long_wins / len(long_trades)) * 100
                long_avg_pnl_pct = sum(p['pnl_pct'] for p in long_trades) / len(long_trades)
                long_leveraged_return = long_avg_pnl_pct * leverage
                long_avg_hold = np.mean([p['hold_days'] for p in long_trades])
                st.write(f"**Long Performance**: {len(long_trades)} trades, {long_win_rate:.1f}% win rate, {long_avg_pnl_pct:.2f}% avg return, {long_leveraged_return:.2f}% leveraged return, {long_nominal_pnl:,.0f} nominal PnL, {long_avg_hold:.1f} avg hold days")
            
            if short_trades:
                short_nominal_pnl = sum(p['nominal_pnl'] for p in short_trades)
                short_wins = sum(1 for p in short_trades if p['pnl'] > 0)
                short_win_rate = (short_wins / len(short_trades)) * 100
                short_avg_pnl_pct = sum(p['pnl_pct'] for p in short_trades) / len(short_trades)
                short_leveraged_return = short_avg_pnl_pct * leverage
                short_avg_hold = np.mean([p['hold_days'] for p in short_trades])
                st.write(f"**Short Performance**: {len(short_trades)} trades, {short_win_rate:.1f}% win rate, {short_avg_pnl_pct:.2f}% avg return, {short_leveraged_return:.2f}% leveraged return, {short_nominal_pnl:,.0f} nominal PnL, {short_avg_hold:.1f} avg hold days")
                
        else:
            st.warning(f"No trades generated with current parameters (R² ≥ {min_r2}, {hold_period_days} day hold)")
        
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
        st.header(f"Real Rate vs Historical FX Rate with Trading Signals ({strategy_type})")
        
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
        
        # Add buy/sell signals based on strategy type
        buy_signals = df[df['buy_signal'] == 'Buy']
        sell_signals = df[df['sell_signal'] == 'Sell']
        
        if strategy_type in ["Long and Short", "Long Only"] and len(buy_signals) > 0:
            ax.scatter(buy_signals.index, buy_signals['fx_price'], 
                      marker='^', color='green', s=150, 
                      label=f'Buy Signals ({len(buy_signals)})', zorder=5)
        
        if strategy_type in ["Long and Short", "Short Only"] and len(sell_signals) > 0:
            ax.scatter(sell_signals.index, sell_signals['fx_price'], 
                      marker='v', color='red', s=150, 
                      label=f'Sell Signals ({len(sell_signals)})', zorder=5)
        
        # Add title and labels
        ax.set_title(f'Real Rate vs Historical FX Rate ({strategy_type}, {hold_period_days} Day Hold, {entry_frequency})', 
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
        
        # Continue with rest of the charts and analysis...
        # (PnL charts, yield spread, model quality, detailed trades, etc.)
        # [Rest of the original code would continue here]
        
        # Show detailed trades if requested
        if show_detailed_trades and positions:
            st.header(f"Detailed Trading Results ({strategy_type}, {hold_period_days} Day Hold)")
            trades_df = pd.DataFrame(positions)
            trades_df['entry_date'] = pd.to_datetime(trades_df['entry_date']).dt.strftime('%Y-%m-%d')
            trades_df['exit_date'] = pd.to_datetime(trades_df['exit_date']).dt.strftime('%Y-%m-%d')
            
            # Format numeric columns
            numeric_cols = ['entry_price', 'exit_price', 'entry_real_rate', 'exit_real_rate', 'pnl', 'pnl_pct', 'nominal_pnl', 'margin_used']
            for col in numeric_cols:
                if col in trades_df.columns:
                    if col in ['nominal_pnl', 'margin_used']:
                        trades_df[col] = trades_df[col].round(0).astype(int)
                    else:
                        trades_df[col] = trades_df[col].round(4)
            
            # Add holding period comparison
            trades_df['hold_vs_target'] = trades_df['hold_days'] - trades_df['target_hold_days']
            
            st.dataframe(trades_df, use_container_width=True)
            
            # Show holding period statistics
            st.subheader("Holding Period Accuracy")
            exact_matches = (trades_df['hold_days'] == trades_df['target_hold_days']).sum()
            early_exits = (trades_df['hold_days'] < trades_df['target_hold_days']).sum()
            late_exits = (trades_df['hold_days'] > trades_df['target_hold_days']).sum()
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Exact Matches", f"{exact_matches}/{len(trades_df)}")
            with col2:
                st.metric("Early Exits", f"{early_exits}")
            with col3:
                st.metric("Late Exits", f"{late_exits}")
            with col4:
                avg_deviation = trades_df['hold_vs_target'].mean()
                st.metric("Avg Deviation", f"{avg_deviation:.1f} days")
            
            # Add download button for trades
            csv = trades_df.to_csv(index=False)
            st.download_button(
                label="Download Trade Results as CSV",
                data=csv,
                file_name=f"trading_results_{strategy_type.lower().replace(' ', '_')}_{hold_period_days}d.csv",
                mime="text/csv"
            )
        
        # PnL Over Time Chart
        if positions:
            st.header("Cumulative PnL Over Time")
            
            # Create detailed PnL timeline
            pnl_timeline = []
            
            for pos in positions:
                pnl_timeline.append({
                    'date': pos['exit_date'],
                    'pnl': pos['nominal_pnl'],
                    'position_type': pos['position'],
                    'hold_days': pos['hold_days'],
                    'target_hold_days': pos['target_hold_days']
                })
            
            if pnl_timeline:
                pnl_df = pd.DataFrame(pnl_timeline)
                pnl_df['date'] = pd.to_datetime(pnl_df['date'])
                pnl_df = pnl_df.sort_values('date')
                pnl_df['cumulative_pnl'] = pnl_df['pnl'].cumsum()
                
                # Create separate cumulative for long and short
                long_pnl = pnl_df[pnl_df['position_type'] == 'Long'].copy()
                short_pnl = pnl_df[pnl_df['position_type'] == 'Short'].copy()
                
                if len(long_pnl) > 0:
                    long_pnl['cumulative_long'] = long_pnl['pnl'].cumsum()
                if len(short_pnl) > 0:
                    short_pnl['cumulative_short'] = short_pnl['pnl'].cumsum()
                
                fig2, ax2 = plt.subplots(figsize=(15, 8))
                
                # Plot cumulative PnL
                ax2.plot(pnl_df['date'], pnl_df['cumulative_pnl'], 
                         label=f'Total Cumulative PnL ({strategy_type})', 
                         color='blue', linewidth=3, alpha=0.8)
                
                # Plot long cumulative PnL if strategy allows
                if strategy_type in ["Long and Short", "Long Only"] and len(long_pnl) > 0:
                    ax2.plot(long_pnl['date'], long_pnl['cumulative_long'], 
                             label='Long Positions', color='green', 
                             linewidth=2, alpha=0.7, linestyle='--')
                
                # Plot short cumulative PnL if strategy allows
                if strategy_type in ["Long and Short", "Short Only"] and len(short_pnl) > 0:
                    ax2.plot(short_pnl['date'], short_pnl['cumulative_short'], 
                             label='Short Positions', color='red', 
                             linewidth=2, alpha=0.7, linestyle='--')
                
                # Add zero line
                ax2.axhline(0, color='gray', linestyle='-', alpha=0.5)
                
                # Mark individual trade exits with color coding for exact hold period
                for i, row in pnl_df.iterrows():
                    pnl_color = 'green' if row['pnl'] > 0 else 'red'
                    marker = '^' if row['position_type'] == 'Long' else 'v'
                    
                    # Different marker size based on whether exact hold period was achieved
                    marker_size = 40 if row['hold_days'] == row['target_hold_days'] else 20
                    alpha = 0.8 if row['hold_days'] == row['target_hold_days'] else 0.4
                    
                    ax2.scatter(row['date'], row['cumulative_pnl'], 
                               color=pnl_color, marker=marker, s=marker_size, 
                               alpha=alpha, zorder=5)
                
                ax2.set_title(f'Cumulative PnL Over Time ({hold_period_days} Day Hold Period)', 
                              fontsize=14, fontweight='bold')
                ax2.set_xlabel('Date', fontsize=12)
                ax2.set_ylabel('Cumulative PnL', fontsize=12)
                ax2.legend(fontsize=10)
                ax2.grid(True, alpha=0.3)
                ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))
                
                # Format x-axis
                ax2.xaxis.set_major_formatter(DateFormatter("%Y-%m"))
                ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
                
                plt.xticks(rotation=45)
                plt.tight_layout()
                st.pyplot(fig2)
                
                # Show legend explanation
                st.write("**Chart Legend**: Large markers = exact hold period achieved, small markers = early/late exit")
        
        # Secondary Chart: Yield Spread
        st.header("Yield Spread Over Time")
        
        fig3, ax3 = plt.subplots(figsize=(15, 6))
        
        ax3.plot(df.index, df['yield_spread'], 
                 label='Yield Spread (Domestic - Foreign)', 
                 color='blue', 
                 linewidth=2)
        
        ax3.axhline(0, color='gray', linestyle='--', alpha=0.5)
        ax3.set_title('Yield Spread (Domestic - Foreign Bond Yields)', fontsize=16, fontweight='bold')
        ax3.set_xlabel('Date', fontsize=12)
        ax3.set_ylabel('Yield Spread (%)', fontsize=12)
        ax3.legend(fontsize=12)
        ax3.grid(True, alpha=0.3)
        
        # Format x-axis
        ax3.xaxis.set_major_formatter(DateFormatter("%Y-%m"))
        ax3.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig3)
        
        # Model Quality Chart: R² over time
        st.header("Model Quality (R²) Over Time")
        
        fig4, ax4 = plt.subplots(figsize=(15, 6))
        
        valid_mask = ~np.isnan(df['real_rate'])
        valid_data = df[valid_mask]
        
        ax4.plot(valid_data.index, valid_data['r_squared'], 
                 label='R² (Model Fit Quality)', 
                 color='green', 
                 linewidth=2)
        
        ax4.axhline(0.5, color='orange', linestyle='--', alpha=0.7, label='50% R²')
        ax4.axhline(min_r2, color='red', linestyle='--', alpha=0.7, label=f'{min_r2*100:.0f}% R² (Trading Threshold)')
        
        ax4.set_title('Regression Model Quality Over Time', fontsize=16, fontweight='bold')
        ax4.set_xlabel('Date', fontsize=12)
        ax4.set_ylabel('R² Value', fontsize=12)
        ax4.set_ylim(0, 1)
        ax4.legend(fontsize=12)
        ax4.grid(True, alpha=0.3)
        
        # Format x-axis
        ax4.xaxis.set_major_formatter(DateFormatter("%Y-%m"))
        ax4.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig4)
        
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
                    current_signal = ""
                    if difference < 0 and strategy_type in ["Long and Short", "Long Only"]:  # fx_price < real_rate
                        current_signal += "BUY (FX < Real) "
                    if difference > 0 and strategy_type in ["Long and Short", "Short Only"]:  # fx_price > real_rate  
                        current_signal += "SELL (FX > Real)"
                    if current_signal:
                        st.success(current_signal)
                    else:
                        if strategy_type == "Long Only":
                            st.info("WAIT (FX > Real)")
                        elif strategy_type == "Short Only":
                            st.info("WAIT (FX < Real)")
                        else:
                            st.info("NEUTRAL")
                else:
                    st.warning("Low R² - No Signal")
                    
        # Show recent data
        st.header("Recent Data Sample")
        sample_data = df[['fx_price', 'domestic_yield', 'foreign_yield', 'yield_spread', 'real_rate', 'r_squared', 'buy_signal', 'sell_signal']].tail(10)
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
    st.write("")
    st.write("**Key Improvements:**")
    st.write("- **Exact Holding Period**: Positions held for exactly the number of days specified")
    st.write("- **Entry Frequency Options**: Choose Monday-only or any-day entry")
    st.write("- **Precise Exit Timing**: Exits calculated to exact target dates")
    st.write("- **Hold Period Tracking**: Monitor how often exact hold periods are achieved")
