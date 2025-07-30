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

# Currency pair specification
st.sidebar.header("Currency Pair Setup")
currency_pair = st.sidebar.text_input("Currency Pair (e.g., EUR/USD, GBP/JPY)", value="EUR/USD", help="Format: BASE/QUOTE where BASE is the first currency, QUOTE is the second")

# Parse currency pair
if "/" in currency_pair:
    base_currency, quote_currency = currency_pair.split("/")
    base_currency = base_currency.strip().upper()
    quote_currency = quote_currency.strip().upper()
else:
    st.sidebar.warning("Please enter currency pair in BASE/QUOTE format (e.g., EUR/USD)")
    base_currency, quote_currency = "BASE", "QUOTE"

st.sidebar.write(f"**Base Currency**: {base_currency} (Position Size)")
st.sidebar.write(f"**Quote Currency**: {quote_currency} (PnL Results)")

# File uploaders
col1, col2, col3 = st.columns(3)

with col1:
    fx_file = st.file_uploader("Currency Pair CSV", type="csv", key="fx")
    if currency_pair:
        st.caption(f"📈 {currency_pair} exchange rate data")
    
with col2:
    domestic_file = st.file_uploader("Domestic Bond Yield CSV", type="csv", key="domestic")
    if base_currency != "BASE":
        st.caption(f"🏠 {base_currency} bond yields")
    
with col3:
    foreign_file = st.file_uploader("Foreign Bond Yield CSV", type="csv", key="foreign")
    if quote_currency != "QUOTE":
        st.caption(f"🌍 {quote_currency} bond yields")

# Model parameters
st.sidebar.header("Model Parameters")
lookback_days = st.sidebar.slider("Regression Lookback Days", 30, 252, 126)
min_r2 = st.sidebar.slider("Minimum R² for Trading", 0.1, 0.9, 0.3, 0.05)

st.sidebar.header("Strategy Parameters")
hold_period_days = st.sidebar.slider("Holding Period (Days)", 1, 365, 90)
position_size = st.sidebar.number_input(f"Position Size ({base_currency})", min_value=1000, max_value=10000000, value=100000, step=10000, help=f"Amount of {base_currency} to trade per position")
leverage = st.sidebar.slider("Leverage", 1, 20, 1)
strategy_type = st.sidebar.selectbox("Strategy Type", ["Long and Short", "Long Only", "Short Only"])
show_detailed_trades = st.sidebar.checkbox("Show Detailed Trades", True)
entry_frequency = st.sidebar.selectbox("Entry Frequency", ["Monday Only", "Any Day with Signal"])

# Optimization parameters
st.sidebar.header("Strategy Optimization")
run_optimization = st.sidebar.checkbox("🚀 Run Strategy Optimization", help="Find the best combination of parameters")
if run_optimization:
    optimization_metric = st.sidebar.selectbox("Optimization Target", 
                                             ["Total Return %", "Sharpe Ratio", "Total PnL", "Win Rate", "Profit Factor"],
                                             help="Which metric to optimize for")
    
    # Parameter ranges for optimization
    r2_range = st.sidebar.slider("R² Range", 0.1, 0.9, (0.2, 0.6), 0.05, help="Range of R² thresholds to test")
    hold_range = st.sidebar.slider("Hold Period Range (Days)", 1, 365, (30, 180), 5, help="Range of holding periods to test")
    regression_range = st.sidebar.slider("Regression Period Range (Days)", 30, 500, (60, 252), 10, help="Range of regression lookback periods to test")
    
    max_combinations = st.sidebar.number_input("Max Combinations to Test", 50, 1000, 200, 25, 
                                             help="Limit total combinations to avoid long computation times")

# Add currency info box
currency_info = f"""
**Currency Setup:**
- Position Size: {base_currency}
- PnL Results: {quote_currency}
- Margin: {quote_currency}

**Example:** If {currency_pair} moves from 1.0500 to 1.0600:
- Raw PnL: 0.0100 {quote_currency} per {base_currency}
- For 100,000 {base_currency}: 1,000 {quote_currency} profit
"""
st.sidebar.info(currency_info)

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

def run_single_strategy(df, real_rates_opt, r_squared_opt, hold_days_opt, min_r2_opt, reg_period):
    """Run a single strategy configuration and return performance metrics"""
    
    # Create a copy of dataframe with optimization parameters
    df_opt = df.copy()
    df_opt['real_rate'] = real_rates_opt
    df_opt['r_squared'] = r_squared_opt
    df_opt['tradeable'] = df_opt['r_squared'] >= min_r2_opt
    
    # Determine entry dates
    if entry_frequency == "Monday Only":
        entry_dates = df_opt[(df_opt['is_monday']) & (df_opt['tradeable']) & (~df_opt['real_rate'].isna())].index
    else:
        entry_dates = df_opt[(df_opt['tradeable']) & (~df_opt['real_rate'].isna())].index
    
    if len(entry_dates) == 0:
        return None
    
    # Execute strategy
    positions = []
    active_positions = []
    date_to_index = {date: idx for idx, date in enumerate(df_opt.index)}
    
    for entry_date in entry_dates:
        real_rate = df_opt.loc[entry_date, 'real_rate']
        fx_price = df_opt.loc[entry_date, 'fx_price']
        r2 = df_opt.loc[entry_date, 'r_squared']
        
        if pd.notna(real_rate) and r2 >= min_r2_opt:
            # Calculate exit date
            current_idx = date_to_index[entry_date]
            target_exit_idx = current_idx + hold_days_opt
            
            if target_exit_idx >= len(df_opt):
                exit_date = df_opt.index[-1]
            else:
                exit_date = df_opt.index[target_exit_idx]
            
            # Close expired positions
            positions_to_close = [pos for pos in active_positions if pos['exit_date'] <= entry_date]
            
            for pos in positions_to_close:
                exit_price = df_opt.loc[pos['exit_date'], 'fx_price']
                
                if pos['position_type'] == 'Long':
                    pnl = exit_price - pos['entry_price']
                else:
                    pnl = pos['entry_price'] - exit_price
                
                positions.append({
                    'entry_date': pos['entry_date'],
                    'exit_date': pos['exit_date'],
                    'entry_price': pos['entry_price'],
                    'exit_price': exit_price,
                    'position': pos['position_type'],
                    'hold_days': (pos['exit_date'] - pos['entry_date']).days,
                    'pnl': pnl,
                    'pnl_pct': (pnl / pos['entry_price']) * 100,
                    'nominal_pnl': pnl * position_size * leverage,
                })
            
            # Remove closed positions
            active_positions = [pos for pos in active_positions if pos['exit_date'] > entry_date]
            
            # Enter new positions
            if fx_price < real_rate and strategy_type in ["Long and Short", "Long Only"]:
                active_positions.append({
                    'entry_date': entry_date,
                    'exit_date': exit_date,
                    'entry_price': fx_price,
                    'position_type': 'Long'
                })
            
            if fx_price > real_rate and strategy_type in ["Long and Short", "Short Only"]:
                active_positions.append({
                    'entry_date': entry_date,
                    'exit_date': exit_date,
                    'entry_price': fx_price,
                    'position_type': 'Short'
                })
    
    # Close remaining positions
    for pos in active_positions:
        actual_exit_date = min(pos['exit_date'], df_opt.index[-1])
        exit_price = df_opt.loc[actual_exit_date, 'fx_price']
        
        if pos['position_type'] == 'Long':
            pnl = exit_price - pos['entry_price']
        else:
            pnl = pos['entry_price'] - exit_price
        
        positions.append({
            'entry_date': pos['entry_date'],
            'exit_date': actual_exit_date,
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'position': pos['position_type'],
            'hold_days': (actual_exit_date - pos['entry_date']).days,
            'pnl': pnl,
            'pnl_pct': (pnl / pos['entry_price']) * 100,
            'nominal_pnl': pnl * position_size * leverage,
        })
    
    if len(positions) == 0:
        return None
    
    # Calculate performance metrics
    total_trades = len(positions)
    winning_trades = sum(1 for p in positions if p['pnl'] > 0)
    win_rate = (winning_trades / total_trades) * 100
    
    total_pnl = sum(p['nominal_pnl'] for p in positions)
    total_capital = sum(position_size / leverage for p in positions)
    total_return_pct = (total_pnl / total_capital) * 100 if total_capital > 0 else 0
    
    # Calculate Sharpe ratio
    pnl_series = [p['nominal_pnl'] for p in positions]
    avg_pnl = np.mean(pnl_series)
    std_pnl = np.std(pnl_series)
    sharpe_ratio = avg_pnl / std_pnl if std_pnl > 0 else 0
    
    # Calculate max drawdown
    cumulative_pnl = np.cumsum(pnl_series)
    peak = np.maximum.accumulate(cumulative_pnl)
    drawdown = peak - cumulative_pnl
    max_drawdown = np.max(drawdown)
    
    # Calculate profit factor
    winning_pnl = sum(p['nominal_pnl'] for p in positions if p['nominal_pnl'] > 0)
    losing_pnl = abs(sum(p['nominal_pnl'] for p in positions if p['nominal_pnl'] < 0))
    profit_factor = winning_pnl / losing_pnl if losing_pnl > 0 else float('inf')
    
    return {
        'total_trades': total_trades,
        'win_rate': win_rate,
        'total_return_pct': total_return_pct,
        'total_pnl': total_pnl,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'profit_factor': profit_factor,
        'avg_trade_pnl': avg_pnl,
        'positions': positions
    }

def run_strategy_optimization(df, fx_prices, yield_spreads, base_currency, quote_currency):
    """Run optimization across different parameter combinations"""
    
    # Define parameter ranges
    r2_min, r2_max = r2_range
    hold_min, hold_max = hold_range
    reg_min, reg_max = regression_range
    
    # Create parameter combinations
    r2_values = np.arange(r2_min, r2_max + 0.05, 0.05)
    hold_values = np.arange(hold_min, hold_max + 5, 5)
    reg_values = np.arange(reg_min, reg_max + 10, 10)
    
    # Limit combinations to avoid excessive computation
    total_combinations = len(r2_values) * len(hold_values) * len(reg_values)
    if total_combinations > max_combinations:
        # Reduce step sizes to fit within limit
        step_factor = int(np.ceil(total_combinations / max_combinations))
        r2_values = r2_values[::max(1, step_factor//3)]
        hold_values = hold_values[::max(1, step_factor//3)]
        reg_values = reg_values[::max(1, step_factor//3)]
    
    st.write(f"Testing {len(r2_values)} × {len(hold_values)} × {len(reg_values)} = {len(r2_values) * len(hold_values) * len(reg_values)} combinations...")
    
    optimization_results = []
    progress_bar = st.progress(0)
    total_tests = len(r2_values) * len(hold_values) * len(reg_values)
    current_test = 0
    
    for reg_period in reg_values:
        # Calculate real rates for this regression period
        real_rates_opt, r_squared_opt = rolling_regression(fx_prices, yield_spreads, int(reg_period))
        
        for min_r2_opt in r2_values:
            for hold_days_opt in hold_values:
                current_test += 1
                progress_bar.progress(current_test / total_tests)
                
                try:
                    # Run strategy with these parameters
                    result = run_single_strategy(df, real_rates_opt, r_squared_opt, 
                                               int(hold_days_opt), min_r2_opt, int(reg_period))
                    
                    if result and len(result['positions']) > 0:
                        optimization_results.append({
                            'r2_threshold': min_r2_opt,
                            'hold_period': int(hold_days_opt),
                            'regression_period': int(reg_period),
                            'total_trades': result['total_trades'],
                            'win_rate': result['win_rate'],
                            'total_return_pct': result['total_return_pct'],
                            'total_pnl': result['total_pnl'],
                            'sharpe_ratio': result['sharpe_ratio'],
                            'max_drawdown': result['max_drawdown'],
                            'profit_factor': result['profit_factor'],
                            'avg_trade_pnl': result['avg_trade_pnl'],
                            'positions': result['positions']
                        })
                except Exception as e:
                    # Skip problematic combinations
                    continue
    
    progress_bar.empty()
    return optimization_results

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
        
        # Run optimization if requested
        if run_optimization:
            st.header("🚀 Strategy Optimization Results")
            
            with st.spinner(f"Running optimization across parameter combinations... This may take a few minutes."):
                optimization_results = run_strategy_optimization(df, fx_prices, yield_spreads, base_currency, quote_currency)
            
            if optimization_results:
                results_df = pd.DataFrame(optimization_results)
                
                # Sort by optimization metric
                if optimization_metric == "Total Return %":
                    best_results = results_df.nlargest(10, 'total_return_pct')
                elif optimization_metric == "Sharpe Ratio":
                    best_results = results_df.nlargest(10, 'sharpe_ratio')
                elif optimization_metric == "Total PnL":
                    best_results = results_df.nlargest(10, 'total_pnl')
                elif optimization_metric == "Win Rate":
                    best_results = results_df.nlargest(10, 'win_rate')
                elif optimization_metric == "Profit Factor":
                    # Filter out infinite values for profit factor
                    finite_results = results_df[np.isfinite(results_df['profit_factor'])]
                    best_results = finite_results.nlargest(10, 'profit_factor')
                
                # Display optimization summary
                st.subheader(f"🏆 Top 10 Strategies (Optimized for {optimization_metric})")
                
                # Format the results for display
                display_results = best_results.copy()
                display_results['total_return_pct'] = display_results['total_return_pct'].round(2)
                display_results['win_rate'] = display_results['win_rate'].round(1)
                display_results['sharpe_ratio'] = display_results['sharpe_ratio'].round(3)
                display_results['total_pnl'] = display_results['total_pnl'].round(0)
                display_results['max_drawdown'] = display_results['max_drawdown'].round(0)
                display_results['profit_factor'] = np.where(np.isfinite(display_results['profit_factor']), 
                                                          display_results['profit_factor'].round(2), 
                                                          '∞')
                
                # Select columns for display
                columns_to_show = ['r2_threshold', 'hold_period', 'regression_period', 'total_trades', 
                                 'win_rate', 'total_return_pct', 'sharpe_ratio', 'total_pnl', 'max_drawdown', 'profit_factor']
                
                st.dataframe(display_results[columns_to_show].round(2), use_container_width=True)
                
                # Show best strategy details
                best_strategy = best_results.iloc[0]
                
                st.subheader("🥇 Optimal Strategy Parameters")
                col1, col2, col3, col4, col5, col6 = st.columns(6)
                
                with col1:
                    st.metric("Best R² Threshold", f"{best_strategy['r2_threshold']:.2f}")
                with col2:
                    st.metric("Best Hold Period", f"{int(best_strategy['hold_period'])} days")
                with col3:
                    st.metric("Best Regression Period", f"{int(best_strategy['regression_period'])} days")
                with col4:
                    metric_value = best_strategy[optimization_metric.lower().replace(' ', '_').replace('%', '_pct')]
                    if optimization_metric == "Profit Factor" and np.isinf(metric_value):
                        metric_display = "∞"
                    else:
                        metric_display = f"{metric_value:.2f}"
                        if "%" in optimization_metric:
                            metric_display += "%"
                    st.metric(f"Best {optimization_metric}", metric_display)
                with col5:
                    st.metric("Total Trades", f"{int(best_strategy['total_trades'])}")
                with col6:
                    st.metric(f"Total PnL ({quote_currency})", f"{best_strategy['total_pnl']:,.0f}")
                
                # Performance comparison
                st.subheader("📊 Current vs Optimal Strategy Comparison")
                
                # Run current strategy for comparison
                current_result = run_single_strategy(df, real_rates, r_squared_values, hold_period_days, min_r2, lookback_days)
                
                if current_result:
                    comparison_data = {
                        'Strategy': ['Current Settings', 'Optimal Settings', 'Improvement'],
                        'R² Threshold': [f"{min_r2:.2f}", f"{best_strategy['r2_threshold']:.2f}", 
                                       f"{((best_strategy['r2_threshold'] - min_r2)/min_r2)*100:+.1f}%"],
                        'Hold Period': [f"{hold_period_days} days", f"{int(best_strategy['hold_period'])} days",
                                      f"{int(best_strategy['hold_period']) - hold_period_days:+d} days"],
                        'Regression Period': [f"{lookback_days} days", f"{int(best_strategy['regression_period'])} days",
                                            f"{int(best_strategy['regression_period']) - lookback_days:+d} days"],
                        'Total Return %': [f"{current_result['total_return_pct']:.2f}%", 
                                         f"{best_strategy['total_return_pct']:.2f}%",
                                         f"{best_strategy['total_return_pct'] - current_result['total_return_pct']:+.2f}%"],
                        'Total Trades': [f"{current_result['total_trades']}", f"{int(best_strategy['total_trades'])}",
                                       f"{int(best_strategy['total_trades']) - current_result['total_trades']:+d}"],
                        'Win Rate %': [f"{current_result['win_rate']:.1f}%", f"{best_strategy['win_rate']:.1f}%",
                                     f"{best_strategy['win_rate'] - current_result['win_rate']:+.1f}%"],
                        f'Total PnL ({quote_currency})': [f"{current_result['total_pnl']:,.0f}", 
                                                         f"{best_strategy['total_pnl']:,.0f}",
                                                         f"{best_strategy['total_pnl'] - current_result['total_pnl']:+,.0f}"]
                    }
                    
                    comparison_df = pd.DataFrame(comparison_data)
                    st.dataframe(comparison_df, use_container_width=True, hide_index=True)
                    
                    # Highlight improvements
                    improvement_pnl = best_strategy['total_pnl'] - current_result['total_pnl']
                    improvement_pct = best_strategy['total_return_pct'] - current_result['total_return_pct']
                    
                    if improvement_pnl > 0:
                        st.success(f"🎯 Optimization could improve your strategy by {improvement_pnl:,.0f} {quote_currency} ({improvement_pct:+.2f}% return)!")
                    else:
                        st.info("✅ Your current parameters are already quite good!")
                    
                    # Quick apply button
                    if st.button("🔄 Apply Optimal Parameters"):
                        st.success("Optimal parameters applied! The results below now use the optimized settings.")
                        # Update the parameters for current run
                        lookback_days = int(best_strategy['regression_period'])
                        min_r2 = best_strategy['r2_threshold']
                        hold_period_days = int(best_strategy['hold_period'])
                        
                        # Recalculate with optimal parameters
                        real_rates, r_squared_values = rolling_regression(fx_prices, yield_spreads, lookback_days)
                
                # Download optimization results
                csv_results = results_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Full Optimization Results",
                    data=csv_results,
                    file_name=f"optimization_results_{currency_pair.replace('/', '')}_{strategy_type.lower().replace(' ', '_')}.csv",
                    mime="text/csv"
                )
                
            else:
                st.warning("No successful strategy combinations found. Try widening the parameter ranges.")
        
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
            st.subheader(f"Nominal Value Performance ({quote_currency})")
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric(f"Total Nominal PnL ({quote_currency})", f"{total_nominal_pnl:,.0f}")
            with col2:
                st.metric(f"Avg Nominal PnL ({quote_currency})", f"{avg_nominal_pnl:,.0f}")
            with col3:
                st.metric(f"Best Trade ({quote_currency})", f"{max_nominal_pnl:,.0f}")
            with col4:
                st.metric(f"Worst Trade ({quote_currency})", f"{min_nominal_pnl:,.0f}")
            with col5:
                st.metric(f"Position Size ({base_currency})", f"{position_size:,}")
            
            # Capital deployment info
            st.subheader(f"Capital Deployment & Leverage ({quote_currency})")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(f"Total Margin Used ({quote_currency})", f"{total_capital_deployed:,}")
            with col2:
                total_notional = sum(p['position_size'] for p in positions)
                st.metric(f"Total Notional Value ({base_currency})", f"{total_notional:,}")
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
                st.write(f"**Long Performance**: {len(long_trades)} trades, {long_win_rate:.1f}% win rate, {long_avg_pnl_pct:.2f}% avg return, {long_leveraged_return:.2f}% leveraged return, {long_nominal_pnl:,.0f} {quote_currency} nominal PnL, {long_avg_hold:.1f} avg hold days")
            
            if short_trades:
                short_nominal_pnl = sum(p['nominal_pnl'] for p in short_trades)
                short_wins = sum(1 for p in short_trades if p['pnl'] > 0)
                short_win_rate = (short_wins / len(short_trades)) * 100
                short_avg_pnl_pct = sum(p['pnl_pct'] for p in short_trades) / len(short_trades)
                short_leveraged_return = short_avg_pnl_pct * leverage
                short_avg_hold = np.mean([p['hold_days'] for p in short_trades])
                st.write(f"**Short Performance**: {len(short_trades)} trades, {short_win_rate:.1f}% win rate, {short_avg_pnl_pct:.2f}% avg return, {short_leveraged_return:.2f}% leveraged return, {short_nominal_pnl:,.0f} {quote_currency} nominal PnL, {short_avg_hold:.1f} avg hold days")
                
        else:
            st.warning(f"No trades generated with current parameters (R² ≥ {min_r2}, {hold_period_days} day hold)")
        
        # Model diagnostics
        st.header("Model Diagnostics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Average R²", f"{np.nanmean(r_squared_values):.3f}")
        with col2:
            st.metric(f"Current {currency_pair} Price", f"{df['fx_price'].iloc[-1]:.4f}")
        with col3:
            if not np.isnan(real_rates[-1]):
                st.metric("Current Real Rate", f"{real_rates[-1]:.4f}")
            else:
                st.metric("Current Real Rate", "N/A")
        with col4:
            st.metric(f"Current Spread ({base_currency}-{quote_currency})", f"{df['yield_spread'].iloc[-1]:.2f}%")
        
        # Main Chart: Real Rate vs Historical Rate with Signals
        st.header(f"Real Rate vs Historical {currency_pair} Rate with Trading Signals ({strategy_type})")
        
        fig, ax = plt.subplots(figsize=(15, 8))
        
        # Plot historical FX price
        ax.plot(df.index, df['fx_price'], 
                label=f'Historical {currency_pair} Rate', 
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
        ax.set_title(f'Real Rate vs Historical {currency_pair} Rate ({strategy_type}, {hold_period_days} Day Hold, {entry_frequency})', 
                    fontsize=16, fontweight='bold')
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel(f'{currency_pair} Rate', fontsize=12)
        ax.legend(fontsize=12)
        ax.grid(True, alpha=0.3)
        
        # Format x-axis
        ax.xaxis.set_major_formatter(DateFormatter("%Y-%m"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig)
        
        # Charts and detailed analysis would continue here
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
            
            # Add download button for trades
            csv = trades_df.to_csv(index=False)
            st.download_button(
                label="Download Trade Results as CSV",
                data=csv,
                file_name=f"trading_results_{currency_pair.replace('/', '')}_{strategy_type.lower().replace(' ', '_')}_{hold_period_days}d.csv",
                mime="text/csv"
            )
        
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
    st.write("- **Strategy Optimization**: Find the best combination of R², holding period, and regression period")
    st.write("- **Currency Labels**: Clear labeling of position sizes and PnL currencies")
