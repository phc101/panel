#!/usr/bin/env python3
"""
Simple Trading Bot for Chromebook
No MT5 MetaEditor needed - pure Python web requests
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json
import schedule
import yfinance as yf

class ChromebookTradingBot:
    def __init__(self):
        self.positions = {}
        self.signals_history = []
        self.last_trade_pnl = 0
        self.running = False
        
        # Strategy settings (edit these)
        self.symbols = ['EURUSD=X', 'CHFPLN=X', 'USDPLN=X', 'EURPLN=X']
        self.holding_days = 10
        self.stop_loss_percent = 2.0
        self.dynamic_leverage = True
        self.no_overlap = False
        
        print("🚀 Chromebook Trading Bot Initialized!")
        print(f"📊 Monitoring: {', '.join(self.symbols)}")
    
    def get_price_data(self, symbol, days=30):
        """Get price data using Yahoo Finance (works on any device)"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=f"{days}d")
            
            if not data.empty:
                data.reset_index(inplace=True)
                return data[['Date', 'Open', 'High', 'Low', 'Close']]
            
            return None
        except Exception as e:
            print(f"❌ Error getting data for {symbol}: {e}")
            return None
    
    def calculate_pivot_points(self, df):
        """Calculate pivot points using 7-day average"""
        if len(df) < 7:
            return None
        
        # Use last 7 days
        window = df.iloc[-7:]
        avg_high = window['High'].mean()
        avg_low = window['Low'].mean()
        avg_close = window['Close'].mean()
        
        pivot = (avg_high + avg_low + avg_close) / 3
        
        return {
            'pivot': pivot,
            'r1': 2 * pivot - avg_low,
            'r2': pivot + (avg_high - avg_low),
            's1': 2 * pivot - avg_high,
            's2': pivot - (avg_high - avg_low)
        }
    
    def check_signals(self):
        """Check for trading signals"""
        signals = []
        
        for symbol in self.symbols:
            try:
                # Skip if position open and no overlap
                if self.no_overlap and symbol in self.positions:
                    continue
                
                # Get data
                df = self.get_price_data(symbol, 30)
                if df is None or len(df) < 7:
                    continue
                
                # Calculate pivots
                pivots = self.calculate_pivot_points(df)
                if not pivots:
                    continue
                
                # Get current price (latest close)
                current_price = df['Close'].iloc[-1]
                
                # Determine leverage
                leverage = 1.0
                if self.dynamic_leverage and self.last_trade_pnl != 0:
                    leverage = 5.0 if self.last_trade_pnl > 0 else 1.0
                
                # Check for signals
                signal = None
                level = None
                
                if current_price < pivots['s2']:
                    signal = 'BUY'
                    level = pivots['s2']
                elif current_price > pivots['r2']:
                    signal = 'SELL' 
                    level = pivots['r2']
                
                if signal:
                    signal_data = {
                        'time': datetime.now().strftime('%H:%M:%S'),
                        'symbol': symbol,
                        'signal': signal,
                        'current_price': current_price,
                        'level': level,
                        'leverage': leverage,
                        'pivots': pivots
                    }
                    
                    signals.append(signal_data)
                    print(f"🎯 {signal} signal for {symbol} at {current_price:.5f} (Level: {level:.5f})")
                
            except Exception as e:
                print(f"❌ Error checking {symbol}: {e}")
                continue
        
        return signals
    
    def execute_signal(self, signal):
        """Simulate trade execution (replace with real broker API)"""
        try:
            symbol = signal['symbol']
            direction = signal['signal']
            price = signal['current_price']
            leverage = signal['leverage']
            
            # Calculate position size based on leverage
            base_position = 1000  # Base units
            position_size = base_position * leverage
            
            # Calculate stop loss and take profit
            if direction == 'BUY':
                stop_loss = price * (1 - self.stop_loss_percent / 100)
                take_profit = price * (1 + 4.0 / 100)  # 4% take profit
            else:
                stop_loss = price * (1 + self.stop_loss_percent / 100)
                take_profit = price * (1 - 4.0 / 100)
            
            # Store position
            self.positions[symbol] = {
                'direction': direction,
                'entry_price': price,
                'entry_time': datetime.now(),
                'position_size': position_size,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'leverage': leverage
            }
            
            print(f"✅ EXECUTED: {direction} {position_size} units of {symbol} @ {price:.5f}")
            print(f"   SL: {stop_loss:.5f} | TP: {take_profit:.5f} | Leverage: {leverage:.1f}x")
            
            return True
            
        except Exception as e:
            print(f"❌ Error executing signal: {e}")
            return False
    
    def manage_positions(self):
        """Manage existing positions"""
        current_time = datetime.now()
        holding_period = timedelta(days=self.holding_days)
        
        positions_to_close = []
        
        for symbol, position in self.positions.items():
            entry_time = position['entry_time']
            
            # Check if holding period exceeded
            if current_time - entry_time > holding_period:
                positions_to_close.append(symbol)
                continue
            
            # Check stop loss / take profit (simplified)
            try:
                df = self.get_price_data(symbol, 2)  # Get last 2 days
                if df is not None and not df.empty:
                    current_price = df['Close'].iloc[-1]
                    
                    # Check exit conditions
                    should_close = False
                    exit_reason = ""
                    
                    if position['direction'] == 'BUY':
                        if current_price <= position['stop_loss']:
                            should_close = True
                            exit_reason = "Stop Loss"
                        elif current_price >= position['take_profit']:
                            should_close = True
                            exit_reason = "Take Profit"
                    else:  # SELL
                        if current_price >= position['stop_loss']:
                            should_close = True
                            exit_reason = "Stop Loss"
                        elif current_price <= position['take_profit']:
                            should_close = True
                            exit_reason = "Take Profit"
                    
                    if should_close:
                        self.close_position(symbol, current_price, exit_reason)
                        positions_to_close.append(symbol)
                        
            except Exception as e:
                print(f"❌ Error managing position {symbol}: {e}")
        
        # Close positions that exceeded holding period
        for symbol in positions_to_close:
            if symbol in self.positions:
                if current_time - self.positions[symbol]['entry_time'] > holding_period:
                    df = self.get_price_data(symbol, 1)
                    if df is not None and not df.empty:
                        current_price = df['Close'].iloc[-1]
                        self.close_position(symbol, current_price, "Holding Period")
    
    def close_position(self, symbol, exit_price, reason):
        """Close a position"""
        try:
            if symbol not in self.positions:
                return
            
            position = self.positions[symbol]
            entry_price = position['entry_price']
            direction = position['direction']
            position_size = position['position_size']
            leverage = position['leverage']
            
            # Calculate P&L
            if direction == 'BUY':
                pnl_per_unit = exit_price - entry_price
            else:
                pnl_per_unit = entry_price - exit_price
            
            total_pnl = pnl_per_unit * position_size
            self.last_trade_pnl = total_pnl
            
            print(f"💰 CLOSED: {direction} {symbol} @ {exit_price:.5f}")
            print(f"   Entry: {entry_price:.5f} | P&L: {total_pnl:.2f} | Reason: {reason}")
            print(f"   Leverage: {leverage:.1f}x | Duration: {datetime.now() - position['entry_time']}")
            
            # Remove position
            del self.positions[symbol]
            
        except Exception as e:
            print(f"❌ Error closing position {symbol}: {e}")
    
    def show_status(self):
        """Show current status"""
        print(f"\n📊 Bot Status - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 Monitoring: {len(self.symbols)} symbols")
        print(f"📈 Open Positions: {len(self.positions)}")
        
        if self.positions:
            print("\n📋 Current Positions:")
            for symbol, pos in self.positions.items():
                duration = datetime.now() - pos['entry_time']
                print(f"   {pos['direction']} {symbol} @ {pos['entry_price']:.5f} ({duration})")
        
        print(f"💰 Last Trade P&L: {self.last_trade_pnl:.2f}")
        print("-" * 50)
    
    def run_strategy_cycle(self):
        """Run one strategy cycle"""
        try:
            print(f"\n🔄 Strategy Cycle - {datetime.now().strftime('%H:%M:%S')}")
            
            # 1. Check for new signals
            signals = self.check_signals()
            
            # 2. Execute new signals
            for signal in signals:
                self.execute_signal(signal)
                time.sleep(1)
            
            # 3. Manage existing positions
            self.manage_positions()
            
            # 4. Show status
            self.show_status()
            
        except Exception as e:
            print(f"❌ Error in strategy cycle: {e}")
    
    def start_bot(self):
        """Start the trading bot"""
        print("🚀 Starting Chromebook Trading Bot...")
        print("⏰ Will check for signals every 5 minutes")
        print("🛑 Press Ctrl+C to stop\n")
        
        self.running = True
        
        # Schedule checks every 5 minutes
        schedule.every(5).minutes.do(self.run_strategy_cycle)
        
        # Run initial cycle
        self.run_strategy_cycle()
        
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(30)  # Check every 30 seconds
                
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user")
            self.stop_bot()
    
    def stop_bot(self):
        """Stop the bot"""
        self.running = False
        
        print("\n📊 Final Status:")
        self.show_status()
        
        if self.positions:
            print(f"⚠️ {len(self.positions)} positions still open")
        
        print("✅ Bot stopped successfully")


def main():
    """Main function"""
    import sys
    
    bot = ChromebookTradingBot()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'test':
            print("🧪 Running test cycle...")
            bot.run_strategy_cycle()
        elif command == 'signals':
            print("🎯 Checking current signals...")
            signals = bot.check_signals()
            if signals:
                for signal in signals:
                    print(f"   {signal['signal']} {signal['symbol']} @ {signal['current_price']:.5f}")
            else:
                print("   No signals found")
        else:
            print("❌ Unknown command. Use: test, signals, or no argument to run bot")
    else:
        # Normal operation
        bot.start_bot()


if __name__ == "__main__":
    """
    Chromebook Trading Bot - No MT5 MetaEditor Required!
    
    Installation:
    1. pip install yfinance pandas numpy schedule
    2. python chromebook_bot.py
    
    Commands:
    - python chromebook_bot.py        # Run bot
    - python chromebook_bot.py test   # Test one cycle  
    - python chromebook_bot.py signals # Check current signals
    
    Features:
    ✅ Works on any device with Python
    ✅ No MetaEditor needed
    ✅ Uses Yahoo Finance for data
    ✅ Simulates trade execution
    ✅ Full position management
    ✅ Dynamic leverage support
    ✅ Stop loss / take profit
    ✅ Time-based exits
    
    To connect to real broker:
    - Replace execute_signal() with real broker API calls
    - Add OANDA REST API, Alpaca, or other broker integration
    """
    main()
