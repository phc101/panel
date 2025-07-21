import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import io

# Set page config
st.set_page_config(
    page_title="Pivot Points Trading Strategy",
    page_icon="📊",
    layout="wide"
)

def calculate_pivot_points(df, lookback_days=7):
    """Calculate 7-day rolling pivot points"""
    df = df.copy()
    df['PP'] = np.nan
    df['R1'] = np.nan
    df['R2'] = np.nan
    df['S1'] = np.nan
    df['S2'] = np.nan
    df['Signal'] = 'NO TRADE'
    df['PnL'] = np.nan
    df['PnL_Percent'] = np.nan
    
    for i in range(lookback_days, len(df)):
        # Get last N days for pivot calculation
        last_n_days = df.iloc[i-lookback_days:i]
        
        # Calculate averages
        avg_high = last_n_days['High'].mean()
        avg_low = last_n_days['Low'].mean()
        avg_close = last_n_days['Close'].mean()
        
        # Calculate pivot point
        pivot_point = (avg_high + avg_low + avg_close) / 3
        
        # Calculate support and resistance
        r1 = (2 * pivot_point) - avg_low
        r2 = pivot_point + (avg_high - avg_low)
        s1 = (2 * pivot_point) - avg_high
        s2 = pivot_point - (avg_high - avg_low)
        
        # Store values
        df.loc[df.index[i], 'PP'] = pivot_point
        df.loc[df.index[i], 'R1'] = r1
        df.loc[df.index[i], 'R2'] = r2
        df.loc[df.index[i], 'S1'] = s1
        df.loc[df.index[i], 'S2'] = s2
        
        # Generate signal
        current_open = df.iloc[i]['Open']
        current_close = df.iloc[i]['Close']
        
        if current_open > pivot_point:
            signal = 'BUY'
            pnl = current_close - current_open
        elif current_open < pivot_point:
            signal = 'SELL'
            pnl = current_open - current_close
        else:
            signal = 'NO TRADE'
            pnl = 0
        
        df.loc[df.index[i], 'Signal'] = signal
        df.loc[df.index[i], 'PnL'] = pnl
        
        if signal != 'NO TRADE':
            df.loc[df.index[i], 'PnL_Percent'] = (pnl / current_open) * 100
    
    return df

def create_chart(df):
    """Create interactive chart with pivot points"""
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('USD/PLN Price with Pivot Points', 'Daily P&L'),
        vertical_spacing=0.1,
        row_heights=[0.7, 0.3]
    )
    
    # Price chart
    fig.add_trace(
        go.Scatter(x=df['Date'], y=df['Open'], name='Open', line=dict(color='blue', width=2)),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=df['Date'], y=df['Close'], name='Close', line=dict(color='black', width=2)),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=df['Date'], y=df['PP'], name='Pivot Point', 
                  line=dict(color='red', width=2, dash='dash')),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=df['Date'], y=df['R1'], name='R1', 
                  line=dict(color='orange', width=1, dash='dot')),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=df['Date'], y=df['R2'], name='R2', 
                  line=dict(color='orange', width=1, dash='dashdot')),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=df['Date'], y=df['S1'], name='S1', 
                  line=dict(color='green', width=1, dash='dot')),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=df['Date'], y=df['S2'], name='S2', 
                  line=dict(color='green', width=1, dash='dashdot')),
        row=1, col=1
    )
    
    # P&L chart
    colors = ['green' if x > 0 else 'red' if x < 0 else 'gray' for x in df['PnL'].fillna(0)]
    fig.add_trace(
        go.Bar(x=df['Date'], y=df['PnL'], name='Daily P&L', marker_color=colors),
        row=2, col=1
    )
    
    fig.update_layout(
        height=800,
        title="7-Day Rolling Pivot Points Strategy Analysis",
        showlegend=True,
        hovermode='x unified'
    )
    
    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_yaxes(title_text="Price (USD/PLN)", row=1, col=1)
    fig.update_yaxes(title_text="P&L", row=2, col=1)
    
    return fig

def main():
    st.title("📊 Pivot Points Trading Strategy Analyzer")
    st.markdown("**7-Day Rolling Pivot Points Strategy for USD/PLN**")
    
    # Sidebar
    st.sidebar.header("Settings")
    lookback_days = st.sidebar.slider("Pivot Lookback Days", min_value=3, max_value=20, value=7)
    show_trades_only = st.sidebar.checkbox("Show Trading Days Only", value=False)
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Upload your USD/PLN CSV file", 
        type=['csv'],
        help="Upload a CSV file with columns: Date, Price, Open, High, Low, Vol., Change %"
    )
    
    if uploaded_file is not None:
        try:
            # Read CSV
            df = pd.read_csv(uploaded_file)
            
            # Clean and prepare data
            df['Date'] = pd.to_datetime(df['Date'])
            df['Close'] = pd.to_numeric(df['Price'], errors='coerce')  # Price column is close
            df['Open'] = pd.to_numeric(df['Open'], errors='coerce')
            df['High'] = pd.to_numeric(df['High'], errors='coerce')
            df['Low'] = pd.to_numeric(df['Low'], errors='coerce')
            
            # Remove rows with missing data
            df = df.dropna(subset=['Date', 'Open', 'High', 'Low', 'Close'])
            
            # Sort by date
            df = df.sort_values('Date').reset_index(drop=True)
            
            st.success(f"✅ Loaded {len(df)} rows of data")
            
            # Calculate pivot points
            with st.spinner("Calculating pivot points and signals..."):
                df_with_pivots = calculate_pivot_points(df, lookback_days)
            
            # Performance metrics
            trading_df = df_with_pivots[df_with_pivots['Signal'] != 'NO TRADE'].copy()
            
            if len(trading_df) > 0:
                total_trades = len(trading_df)
                buy_trades = len(trading_df[trading_df['Signal'] == 'BUY'])
                sell_trades = len(trading_df[trading_df['Signal'] == 'SELL'])
                winning_trades = len(trading_df[trading_df['PnL'] > 0])
                losing_trades = len(trading_df[trading_df['PnL'] < 0])
                total_pnl = trading_df['PnL'].sum()
                win_rate = (winning_trades / total_trades) * 100
                
                # Buy/Sell specific metrics
                buy_df = trading_df[trading_df['Signal'] == 'BUY']
                sell_df = trading_df[trading_df['Signal'] == 'SELL']
                buy_win_rate = (len(buy_df[buy_df['PnL'] > 0]) / len(buy_df) * 100) if len(buy_df) > 0 else 0
                sell_win_rate = (len(sell_df[sell_df['PnL'] > 0]) / len(sell_df) * 100) if len(sell_df) > 0 else 0
                
                # Display metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Days", f"{len(df_with_pivots)}")
                    st.metric("Trading Days", f"{total_trades}")
                
                with col2:
                    st.metric("Win Rate", f"{win_rate:.1f}%")
                    st.metric("Total P&L", f"{total_pnl:.4f}", delta=f"{total_pnl:.4f}")
                
                with col3:
                    st.metric("BUY Signals", f"{buy_trades} ({buy_trades/total_trades*100:.1f}%)")
                    st.metric("BUY Win Rate", f"{buy_win_rate:.1f}%")
                
                with col4:
                    st.metric("SELL Signals", f"{sell_trades} ({sell_trades/total_trades*100:.1f}%)")
                    st.metric("SELL Win Rate", f"{sell_win_rate:.1f}%")
                
                # Strategy explanation
                st.markdown("### 📋 Strategy Rules")
                st.info("""
                **BUY Signal:** When Open Price > Pivot Point (PP)  
                **SELL Signal:** When Open Price < Pivot Point (PP)  
                **Exit:** Close all positions at end of day  
                **Pivot Calculation:** {}-day rolling average of (High + Low + Close) / 3
                """.format(lookback_days))
                
                # Chart
                st.markdown("### 📈 Price Chart with Pivot Points")
                chart = create_chart(df_with_pivots)
                st.plotly_chart(chart, use_container_width=True)
                
                # Data table
                st.markdown("### 📊 Trading Data")
                
                if show_trades_only:
                    display_df = trading_df.copy()
                else:
                    display_df = df_with_pivots.copy()
                
                # Format display dataframe
                display_df = display_df[[
                    'Date', 'Open', 'High', 'Low', 'Close', 'PP', 'R1', 'R2', 'S1', 'S2', 
                    'Signal', 'PnL', 'PnL_Percent'
                ]].copy()
                
                display_df['Date'] = display_df['Date'].dt.strftime('%m/%d/%Y')
                
                # Round numerical columns
                numeric_cols = ['Open', 'High', 'Low', 'Close', 'PP', 'R1', 'R2', 'S1', 'S2', 'PnL']
                for col in numeric_cols:
                    display_df[col] = display_df[col].round(4)
                
                display_df['PnL_Percent'] = display_df['PnL_Percent'].round(2)
                
                # Color code the dataframe
                def highlight_pnl(row):
                    if pd.isna(row['PnL']) or row['Signal'] == 'NO TRADE':
                        return ['background-color: #f0f0f0'] * len(row)
                    elif row['PnL'] > 0:
                        return ['background-color: #d4edda'] * len(row)
                    elif row['PnL'] < 0:
                        return ['background-color: #f8d7da'] * len(row)
                    else:
                        return [''] * len(row)
                
                styled_df = display_df.style.apply(highlight_pnl, axis=1)
                st.dataframe(styled_df, use_container_width=True, height=400)
                
                # Download results
                st.markdown("### 💾 Download Results")
                
                # Create download buffer
                buffer = io.StringIO()
                display_df.to_csv(buffer, index=False)
                csv_data = buffer.getvalue()
                
                st.download_button(
                    label="📥 Download Analysis as CSV",
                    data=csv_data,
                    file_name=f"pivot_strategy_analysis_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
                
                # Performance summary
                st.markdown("### 📈 Performance Summary")
                
                if len(trading_df) > 0:
                    avg_win = trading_df[trading_df['PnL'] > 0]['PnL'].mean() if winning_trades > 0 else 0
                    avg_loss = trading_df[trading_df['PnL'] < 0]['PnL'].mean() if losing_trades > 0 else 0
                    profit_factor = abs(avg_win * winning_trades) / abs(avg_loss * losing_trades) if losing_trades > 0 and avg_loss != 0 else float('inf')
                    
                    summary_data = {
                        'Metric': [
                            'Total Trades',
                            'Winning Trades',
                            'Losing Trades',
                            'Win Rate (%)',
                            'Average Win',
                            'Average Loss',
                            'Profit Factor',
                            'Total P&L',
                            'Best Trade',
                            'Worst Trade'
                        ],
                        'Value': [
                            total_trades,
                            winning_trades,
                            losing_trades,
                            f"{win_rate:.2f}%",
                            f"{avg_win:.4f}",
                            f"{avg_loss:.4f}",
                            f"{profit_factor:.2f}" if profit_factor != float('inf') else '∞',
                            f"{total_pnl:.4f}",
                            f"{trading_df['PnL'].max():.4f}",
                            f"{trading_df['PnL'].min():.4f}"
                        ]
                    }
                    
                    summary_df = pd.DataFrame(summary_data)
                    st.table(summary_df)
                
            else:
                st.warning("No trading signals generated. Try adjusting the lookback period.")
                
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.info("Please ensure your CSV has the required columns: Date, Price, Open, High, Low, Vol., Change %")
    
    else:
        st.info("👆 Please upload your USD/PLN CSV file to begin analysis")
        
        # Show example data format
        st.markdown("### 📋 Expected CSV Format")
        example_data = {
            'Date': ['07/18/2025', '07/17/2025', '07/16/2025'],
            'Price': [3.6522, 3.6714, 3.6524],
            'Open': [3.6714, 3.6522, 3.6770],
            'High': [3.6749, 3.6814, 3.6856],
            'Low': [3.6411, 3.6510, 3.6336],
            'Vol.': ['', '', ''],
            'Change %': ['-0.52%', '0.52%', '-0.66%']
        }
        st.table(pd.DataFrame(example_data))

if __name__ == "__main__":
    main()
