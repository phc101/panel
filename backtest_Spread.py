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
position_size = st.sidebar.number_input("Position Size (Volume per Trade)", min_value=1000, max_value=10000000, value=100000, step=10000)
leverage = st.sidebar.slider("Leverage", 1, 20, 1)
strategy_type = st.sidebar.selectbox("Strategy Type", ["Long and Short", "Long Only", "Short Only"])
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
        df['buy_signal'] = ''
        df['sell_signal'] = ''
        df['long_position'] = 0
        df['short_position'] = 0
        
        # Get Monday dates where we can trade
        monday_dates = df[(df['is_monday']) & (df['tradeable']) & (~df['real_rate'].isna())].index
        
        st.write(f"Tradeable Mondays (R² ≥ {min_r2}): {len(monday_dates)} out of {len(df[df['is_monday']])} total Mondays")
        
        # Execute strategy - allow multiple overlapping positions
        hold_days = hold_period_months * 30
        positions = []
        
        # Track all active positions (can have multiple long and short positions)
        active_long_positions = []
        active_short_positions = []
        
        for monday in monday_dates:
            real_rate = df.loc[monday, 'real_rate']
            fx_price = df.loc[monday, 'fx_price']
            r2 = df.loc[monday, 'r_squared']
            
            if pd.notna(real_rate) and r2 >= min_r2:
                
                # Close expired long positions
                expired_long = []
                for i, pos in enumerate(active_long_positions):
                    days_held = (monday - pos['entry_date']).days
                    if days_held >= hold_days:
                        # Close this long position
                        exit_price = fx_price
                        pnl = exit_price - pos['entry_price']
                        
                        positions.append({
                            'entry_date': pos['entry_date'],
                            'exit_date': monday,
                            'entry_price': pos['entry_price'],
                            'exit_price': exit_price,
                            'entry_real_rate': pos['entry_real_rate'],
                            'exit_real_rate': real_rate,
                            'position': 'Long',
                            'hold_days': days_held,
                            'pnl': pnl,
                            'pnl_pct': (pnl / pos['entry_price']) * 100,
                            'position_size': position_size,
                            'leverage': leverage,
                            'nominal_pnl': pnl * position_size * leverage,
                            'margin_used': position_size / leverage if leverage > 0 else position_size
                        })
                        expired_long.append(i)
                
                # Remove expired long positions
                for i in reversed(expired_long):
                    active_long_positions.pop(i)
                
                # Close expired short positions
                expired_short = []
                for i, pos in enumerate(active_short_positions):
                    days_held = (monday - pos['entry_date']).days
                    if days_held >= hold_days:
                        # Close this short position
                        exit_price = fx_price
                        pnl = pos['entry_price'] - exit_price
                        
                        positions.append({
                            'entry_date': pos['entry_date'],
                            'exit_date': monday,
                            'entry_price': pos['entry_price'],
                            'exit_price': exit_price,
                            'entry_real_rate': pos['entry_real_rate'],
                            'exit_real_rate': real_rate,
                            'position': 'Short',
                            'hold_days': days_held,
                            'pnl': pnl,
                            'pnl_pct': (pnl / pos['entry_price']) * 100,
                            'position_size': position_size,
                            'leverage': leverage,
                            'nominal_pnl': pnl * position_size * leverage,
                            'margin_used': position_size / leverage if leverage > 0 else position_size
                        })
                        expired_short.append(i)
                
                # Remove expired short positions
                for i in reversed(expired_short):
                    active_short_positions.pop(i)
                
                # Enter new long position if conditions are met (every Monday if FX < Real Rate)
                if fx_price < real_rate and strategy_type in ["Long and Short", "Long Only"]:
                    active_long_positions.append({
                        'entry_date': monday,
                        'entry_price': fx_price,
                        'entry_real_rate': real_rate
                    })
                    df.loc[monday, 'buy_signal'] = 'Buy'
                    df.loc[monday, 'long_position'] = len(active_long_positions)
                
                # Enter new short position if conditions are met (every Monday if FX > Real Rate)
                if fx_price > real_rate and strategy_type in ["Long and Short", "Short Only"]:
                    active_short_positions.append({
                        'entry_date': monday,
                        'entry_price': fx_price,
                        'entry_real_rate': real_rate
                    })
                    df.loc[monday, 'sell_signal'] = 'Sell'
                    df.loc[monday, 'short_position'] = -len(active_short_positions)
        
        # Close all remaining positions at the end
        last_date = df.index[-1]
        final_real_rate = df.loc[last_date, 'real_rate'] if pd.notna(df.loc[last_date, 'real_rate']) else 0
        
        # Close remaining long positions
        for pos in active_long_positions:
            exit_price = df.loc[last_date, 'fx_price']
            pnl = exit_price - pos['entry_price']
            positions.append({
                'entry_date': pos['entry_date'],
                'exit_date': last_date,
                'entry_price': pos['entry_price'],
                'exit_price': exit_price,
                'entry_real_rate': pos['entry_real_rate'],
                'exit_real_rate': final_real_rate,
                'position': 'Long',
                'hold_days': (last_date - pos['entry_date']).days,
                'pnl': pnl,
                'pnl_pct': (pnl / pos['entry_price']) * 100,
                'position_size': position_size,
                'leverage': leverage,
                'nominal_pnl': pnl * position_size * leverage,
                'margin_used': position_size / leverage if leverage > 0 else position_size
            })
        
        # Close remaining short positions
        for pos in active_short_positions:
            exit_price = df.loc[last_date, 'fx_price']
            pnl = pos['entry_price'] - exit_price
            positions.append({
                'entry_date': pos['entry_date'],
                'exit_date': last_date,
                'entry_price': pos['entry_price'],
                'exit_price': exit_price,
                'entry_real_rate': pos['entry_real_rate'],
                'exit_real_rate': final_real_rate,
                'position': 'Short',
                'hold_days': (last_date - pos['entry_date']).days,
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
                st.write(f"**Long Performance**: {len(long_trades)} trades, {long_win_rate:.1f}% win rate, {long_avg_pnl_pct:.2f}% avg return, {long_leveraged_return:.2f}% leveraged return, {long_nominal_pnl:,.0f} nominal PnL")
            
            if short_trades:
                short_nominal_pnl = sum(p['nominal_pnl'] for p in short_trades)
                short_wins = sum(1 for p in short_trades if p['pnl'] > 0)
                short_win_rate = (short_wins / len(short_trades)) * 100
                short_avg_pnl_pct = sum(p['pnl_pct'] for p in short_trades) / len(short_trades)
                short_leveraged_return = short_avg_pnl_pct * leverage
                st.write(f"**Short Performance**: {len(short_trades)} trades, {short_win_rate:.1f}% win rate, {short_avg_pnl_pct:.2f}% avg return, {short_leveraged_return:.2f}% leveraged return, {short_nominal_pnl:,.0f} nominal PnL")
                
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
        ax.set_title(f'Real Rate vs Historical FX Rate ({strategy_type}, {hold_period_months} Month Hold)', 
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
        
        # PnL Over Time Chart with Margin Call Analysis
        if positions:
            st.header("Cumulative PnL Over Time with Margin Call Analysis")
            
            # Create detailed PnL timeline with margin tracking
            pnl_timeline = []
            running_balance = 0
            running_margin_used = 0
            
            for pos in positions:
                # Track margin usage during the trade
                margin_for_trade = pos['margin_used']
                
                pnl_timeline.append({
                    'date': pos['exit_date'],
                    'pnl': pos['nominal_pnl'],
                    'position_type': pos['position'],
                    'margin_used': margin_for_trade,
                    'position_size': pos['position_size'],
                    'leverage': pos['leverage']
                })
            
            if pnl_timeline:
                pnl_df = pd.DataFrame(pnl_timeline)
                pnl_df['date'] = pd.to_datetime(pnl_df['date'])
                pnl_df = pnl_df.sort_values('date')
                pnl_df['cumulative_pnl'] = pnl_df['pnl'].cumsum()
                
                # Calculate portfolio equity and margin call levels
                initial_capital = st.sidebar.number_input("Initial Capital", min_value=10000, max_value=100000000, value=500000, step=10000)
                margin_call_threshold = st.sidebar.slider("Margin Call Threshold (%)", 10, 90, 50, 5) / 100
                
                pnl_df['portfolio_equity'] = initial_capital + pnl_df['cumulative_pnl']
                pnl_df['cumulative_margin'] = pnl_df['margin_used'].cumsum()
                pnl_df['margin_ratio'] = pnl_df['portfolio_equity'] / pnl_df['cumulative_margin']
                pnl_df['margin_call_level'] = pnl_df['cumulative_margin'] * margin_call_threshold
                pnl_df['margin_call_triggered'] = pnl_df['portfolio_equity'] < pnl_df['margin_call_level']
                
                # Create separate cumulative for long and short
                long_pnl = pnl_df[pnl_df['position_type'] == 'Long'].copy()
                short_pnl = pnl_df[pnl_df['position_type'] == 'Short'].copy()
                
                if len(long_pnl) > 0:
                    long_pnl['cumulative_long'] = long_pnl['pnl'].cumsum()
                if len(short_pnl) > 0:
                    short_pnl['cumulative_short'] = short_pnl['pnl'].cumsum()
                
                # Create two subplots
                fig2, (ax2a, ax2b) = plt.subplots(2, 1, figsize=(15, 12))
                
                # Top plot: Portfolio Equity vs Margin Call Level
                ax2a.plot(pnl_df['date'], pnl_df['portfolio_equity'], 
                         label='Portfolio Equity', color='blue', linewidth=3)
                ax2a.plot(pnl_df['date'], pnl_df['margin_call_level'], 
                         label=f'Margin Call Level ({margin_call_threshold*100:.0f}%)', 
                         color='red', linewidth=2, linestyle='--')
                ax2a.axhline(initial_capital, color='gray', linestyle='-', alpha=0.5, label='Initial Capital')
                
                # Highlight margin call periods
                margin_call_dates = pnl_df[pnl_df['margin_call_triggered']]
                if len(margin_call_dates) > 0:
                    ax2a.scatter(margin_call_dates['date'], margin_call_dates['portfolio_equity'],
                               color='red', s=100, marker='X', label='Margin Call!', zorder=10)
                    for _, row in margin_call_dates.iterrows():
                        ax2a.annotate('MARGIN CALL', 
                                    xy=(row['date'], row['portfolio_equity']),
                                    xytext=(10, 10), textcoords='offset points',
                                    bbox=dict(boxstyle='round,pad=0.3', facecolor='red', alpha=0.7),
                                    arrowprops=dict(arrowstyle='->', color='red'))
                
                ax2a.set_title(f'Portfolio Equity vs Margin Call Level ({leverage}:1 Leverage)', 
                              fontsize=14, fontweight='bold')
                ax2a.set_ylabel('Capital', fontsize=12)
                ax2a.legend(fontsize=10)
                ax2a.grid(True, alpha=0.3)
                ax2a.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))
                
                # Bottom plot: Cumulative PnL
                ax2b.plot(pnl_df['date'], pnl_df['cumulative_pnl'], 
                         label=f'Total Cumulative PnL ({strategy_type})', 
                         color='blue', linewidth=3, alpha=0.8)
                
                # Plot long cumulative PnL if strategy allows
                if strategy_type in ["Long and Short", "Long Only"] and len(long_pnl) > 0:
                    ax2b.plot(long_pnl['date'], long_pnl['cumulative_long'], 
                             label='Long Positions', color='green', 
                             linewidth=2, alpha=0.7, linestyle='--')
                
                # Plot short cumulative PnL if strategy allows
                if strategy_type in ["Long and Short", "Short Only"] and len(short_pnl) > 0:
                    ax2b.plot(short_pnl['date'], short_pnl['cumulative_short'], 
                             label='Short Positions', color='red', 
                             linewidth=2, alpha=0.7, linestyle='--')
                
                # Add zero line
                ax2b.axhline(0, color='gray', linestyle='-', alpha=0.5)
                
                # Mark individual trade exits
                for i, row in pnl_df.iterrows():
                    color = 'green' if row['pnl'] > 0 else 'red'
                    marker = '^' if row['position_type'] == 'Long' else 'v'
                    ax2b.scatter(row['date'], row['cumulative_pnl'], 
                               color=color, marker=marker, s=30, alpha=0.6, zorder=5)
                
                ax2b.set_title('Cumulative PnL Over Time', fontsize=14, fontweight='bold')
                ax2b.set_xlabel('Date', fontsize=12)
                ax2b.set_ylabel('Cumulative PnL', fontsize=12)
                ax2b.legend(fontsize=10)
                ax2b.grid(True, alpha=0.3)
                ax2b.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))
                
                # Format x-axis for both plots
                for ax in [ax2a, ax2b]:
                    ax.xaxis.set_major_formatter(DateFormatter("%Y-%m"))
                    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
                
                plt.xticks(rotation=45)
                plt.tight_layout()
                st.pyplot(fig2)
                
                # Margin Call Analysis
                st.subheader("Margin Call Risk Analysis")
                
                margin_calls = pnl_df[pnl_df['margin_call_triggered']]
                
                # Check for complete capital wipeout
                capital_wiped_out = pnl_df['portfolio_equity'] <= 0
                wipeout_occurred = capital_wiped_out.any()
                
                if wipeout_occurred:
                    wipeout_date = pnl_df[capital_wiped_out].iloc[0]['date']
                    st.error(f"💀 CAPITAL WIPEOUT: Your entire capital would be lost on {wipeout_date.strftime('%Y-%m-%d')}!")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Wipeout Date", wipeout_date.strftime('%Y-%m-%d'))
                    with col2:
                        final_equity = pnl_df[capital_wiped_out].iloc[0]['portfolio_equity']
                        st.metric("Final Equity", f"{final_equity:,.0f}")
                    with col3:
                        days_to_wipeout = (wipeout_date - pnl_df['date'].iloc[0]).days
                        st.metric("Days to Wipeout", f"{days_to_wipeout}")
                    
                    st.write("**⚠️ This leverage level is EXTREMELY DANGEROUS and would result in total loss of capital!**")
                    
                elif len(margin_calls) > 0:
                    st.error(f"⚠️ WARNING: {len(margin_calls)} margin calls would have occurred!")
                    
                    # Show margin call details
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        first_margin_call = margin_calls.iloc[0]
                        st.metric("First Margin Call", first_margin_call['date'].strftime('%Y-%m-%d'))
                    with col2:
                        lowest_equity = pnl_df['portfolio_equity'].min()
                        st.metric("Lowest Portfolio Value", f"{lowest_equity:,.0f}")
                    with col3:
                        min_margin_ratio = pnl_df['margin_ratio'].min()
                        st.metric("Worst Margin Ratio", f"{min_margin_ratio:.1f}x")
                    
                    # Show critical periods
                    st.write("**Margin Call Events:**")
                    margin_call_summary = margin_calls[['date', 'portfolio_equity', 'margin_call_level', 'cumulative_margin']].copy()
                    margin_call_summary['equity_deficit'] = margin_call_summary['margin_call_level'] - margin_call_summary['portfolio_equity']
                    margin_call_summary['date'] = margin_call_summary['date'].dt.strftime('%Y-%m-%d')
                    st.dataframe(margin_call_summary.round(0))
                    
                else:
                    st.success("✅ No margin calls would have occurred with this leverage level!")
                
                # Enhanced PnL Statistics
                st.subheader("Risk-Adjusted Performance Analysis")
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    max_drawdown = (pnl_df['cumulative_pnl'] - pnl_df['cumulative_pnl'].cummax()).min()
                    st.metric("Max Drawdown", f"{max_drawdown:,.0f}")
                
                with col2:
                    peak_pnl = pnl_df['cumulative_pnl'].max()
                    st.metric("Peak PnL", f"{peak_pnl:,.0f}")
                
                with col3:
                    final_equity = pnl_df['portfolio_equity'].iloc[-1]
                    total_return_pct = ((final_equity - initial_capital) / initial_capital) * 100
                    st.metric("Total Return %", f"{total_return_pct:.1f}%")
                
                with col4:
                    max_margin_used = pnl_df['cumulative_margin'].max()
                    capital_efficiency = (abs(total_nominal_pnl) / max_margin_used) * 100 if max_margin_used > 0 else 0
                    st.metric("Capital Efficiency", f"{capital_efficiency:.1f}%")
                
                with col5:
                    if len(pnl_df) > 1:
                        volatility = pnl_df['pnl'].std()
                        sharpe_ratio = pnl_df['pnl'].mean() / volatility if volatility > 0 else 0
                        st.metric("Sharpe Ratio", f"{sharpe_ratio:.2f}")
                    else:
                        st.metric("Sharpe Ratio", "N/A")
                
                # Leverage safety recommendations
                st.subheader("Leverage Safety Recommendations")
                
                if wipeout_occurred:
                    st.error("🚨 **TOTAL CAPITAL LOSS RISK**: This leverage/capital combination is lethal!")
                    st.write("**Immediate Actions Required:**")
                    st.write("- 🔴 Reduce leverage immediately")
                    st.write("- 🔴 Increase initial capital")
                    st.write("- 🔴 Consider this strategy too risky for leveraged trading")
                    
                    # Calculate minimum safe capital for current leverage
                    max_single_loss = abs(pnl_df['pnl'].min())
                    min_safe_capital = max_single_loss * leverage / margin_call_threshold * 2  # 2x safety margin
                    st.write(f"**Minimum Safe Capital for {leverage}:1 leverage**: {min_safe_capital:,.0f}")
                    
                elif len(margin_calls) > 0:
                    # Calculate safe leverage
                    max_single_loss = abs(pnl_df['pnl'].min())
                    safe_leverage = max(1, int((initial_capital * margin_call_threshold) / max_single_loss))
                    st.warning(f"💡 **Recommended Max Leverage**: {safe_leverage}:1 to avoid margin calls")
                    st.write(f"Current leverage of {leverage}:1 is too high for this strategy with {initial_capital:,} initial capital.")
                    
                    # Show what capital would be needed for current leverage
                    required_capital = (max_single_loss * leverage / margin_call_threshold) * 1.5  # 1.5x safety buffer
                    st.write(f"**Capital needed for {leverage}:1 leverage**: {required_capital:,.0f}")
                    
                else:
                    if leverage < 5:
                        st.info(f"✅ Current leverage of {leverage}:1 appears safe with {initial_capital:,} initial capital")
                    elif leverage < 10:
                        st.warning(f"⚠️ Moderate risk: {leverage}:1 leverage - monitor closely")
                    else:
                        st.error(f"🔥 High risk: {leverage}:1 leverage - consider reducing")
                
                # Risk categorization
                st.subheader("Risk Assessment Summary")
                
                lowest_equity = pnl_df['portfolio_equity'].min()
                equity_drop_pct = ((initial_capital - lowest_equity) / initial_capital) * 100
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if wipeout_occurred:
                        risk_level = "🔴 LETHAL"
                        risk_color = "error"
                    elif equity_drop_pct > 80:
                        risk_level = "🔴 EXTREME"
                        risk_color = "error" 
                    elif equity_drop_pct > 60:
                        risk_level = "🟠 HIGH"
                        risk_color = "warning"
                    elif equity_drop_pct > 40:
                        risk_level = "🟡 MODERATE"
                        risk_color = "warning"
                    elif equity_drop_pct > 20:
                        risk_level = "🟢 LOW"
                        risk_color = "success"
                    else:
                        risk_level = "🟢 MINIMAL"
                        risk_color = "success"
                    
                    if risk_color == "error":
                        st.error(f"Risk Level: {risk_level}")
                    elif risk_color == "warning":
                        st.warning(f"Risk Level: {risk_level}")
                    else:
                        st.success(f"Risk Level: {risk_level}")
                
                with col2:
                    st.metric("Max Equity Drop", f"{equity_drop_pct:.1f}%")
                
                with col3:
                    survival_rate = (1 - (1 if wipeout_occurred else 0)) * 100
                    st.metric("Capital Survival", f"{survival_rate:.0f}%")
                
                # Capital requirements
                st.write("**Capital Requirements Analysis:**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"Initial Capital: **{initial_capital:,}**")
                with col2:
                    max_concurrent_margin = max_margin_used
                    st.write(f"Max Margin Used: **{max_concurrent_margin:,.0f}**")
                with col3:
                    margin_utilization = (max_concurrent_margin / initial_capital) * 100
                    st.write(f"Peak Margin Utilization: **{margin_utilization:.1f}%**")
        
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
            st.header(f"Detailed Trading Results ({strategy_type}, {hold_period_months} Month Hold)")
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
            
            st.dataframe(trades_df, use_container_width=True)
            
            # Add download button for trades
            csv = trades_df.to_csv(index=False)
            st.download_button(
                label="Download Trade Results as CSV",
                data=csv,
                file_name=f"trading_results_{strategy_type.lower().replace(' ', '_')}_{hold_period_months}m.csv",
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

