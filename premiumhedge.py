def run_backtest(self, df, initial_capital=10000, lot_size=1.0, spread_pips=2, holding_days=5):
    """
    Uruchom backtest strategii TYGODNIOWEJ
    Strategia: 
    - Każdy PONIEDZIAŁEK sprawdź sygnał:
      * Jeśli cena < S3 → KUP i trzymaj X dni
      * Jeśli cena > R3 → SPRZEDAJ i trzymaj X dni
    - Pozycje mogą się nakładać (long i short jednocześnie)
    """
    
    trades = []
    capital = initial_capital
    open_positions = []  # Lista otwartych pozycji [{type, entry_date, exit_date, entry_price, ...}]
    
    for i in range(len(df)):
        row = df.iloc[i]
        
        if pd.isna(row.get('S3')) or pd.isna(row.get('R3')):
            continue
        
        current_date = row['Date']
        current_price = row['Close']
        
        # ZAMKNIJ wygasające pozycje
        positions_to_close = []
        for pos_idx, pos in enumerate(open_positions):
            if current_date >= pos['exit_date']:
                positions_to_close.append(pos_idx)
        
        # Zamykaj od końca żeby nie zepsuć indeksów
        for pos_idx in sorted(positions_to_close, reverse=True):
            pos = open_positions.pop(pos_idx)
            
            # Oblicz profit
            pip_value = 0.0001
            if 'JPY' in df.attrs.get('symbol', ''):
                pip_value = 0.01
            
            if pos['type'] == 'long':
                exit_price = current_price - (spread_pips * 0.0001)
                pips_gained = (exit_price - pos['entry_price']) / pip_value
            else:  # short
                exit_price = current_price + (spread_pips * 0.0001)
                pips_gained = (pos['entry_price'] - exit_price) / pip_value
            
            profit = pips_gained * pip_value * pos['lot_size'] * 100000
            capital += profit
            
            days_held = (current_date - pos['entry_date']).days
            
            trades.append({
                'Entry Date': pos['entry_date'],
                'Exit Date': current_date,
                'Type': pos['type'].upper(),
                'Entry Price': pos['entry_price'],
                'Exit Price': exit_price,
                'Entry Level': pos['entry_level'],
                'Exit Level': row['R3'] if pos['type'] == 'long' else row['S3'],
                'Pips': pips_gained,
                'Profit': profit,
                'Capital': capital,
                'Duration': days_held
            })
        
        # OTWIERAJ NOWE POZYCJE W PONIEDZIAŁKI
        if current_date.weekday() == 0:  # 0 = poniedziałek
            
            # Sygnał BUY: cena < S3
            if current_price < row['S3']:
                entry_price = current_price + (spread_pips * 0.0001)
                exit_date = current_date + timedelta(days=holding_days)
                
                open_positions.append({
                    'type': 'long',
                    'entry_date': current_date,
                    'exit_date': exit_date,
                    'entry_price': entry_price,
                    'entry_level': row['S3'],
                    'lot_size': lot_size
                })
            
            # Sygnał SELL: cena > R3
            if current_price > row['R3']:
                entry_price = current_price - (spread_pips * 0.0001)
                exit_date = current_date + timedelta(days=holding_days)
                
                open_positions.append({
                    'type': 'short',
                    'entry_date': current_date,
                    'exit_date': exit_date,
                    'entry_price': entry_price,
                    'entry_level': row['R3'],
                    'lot_size': lot_size
                })
    
    # Zamknij pozostałe pozycje na końcu backtestingu
    last_row = df.iloc[-1]
    for pos in open_positions:
        pip_value = 0.0001
        if 'JPY' in df.attrs.get('symbol', ''):
            pip_value = 0.01
        
        if pos['type'] == 'long':
            exit_price = last_row['Close'] - (spread_pips * 0.0001)
            pips_gained = (exit_price - pos['entry_price']) / pip_value
        else:
            exit_price = last_row['Close'] + (spread_pips * 0.0001)
            pips_gained = (pos['entry_price'] - exit_price) / pip_value
        
        profit = pips_gained * pip_value * pos['lot_size'] * 100000
        capital += profit
        
        days_held = (last_row['Date'] - pos['entry_date']).days
        
        trades.append({
            'Entry Date': pos['entry_date'],
            'Exit Date': last_row['Date'],
            'Type': pos['type'].upper(),
            'Entry Price': pos['entry_price'],
            'Exit Price': exit_price,
            'Entry Level': pos['entry_level'],
            'Exit Level': last_row.get('R3' if pos['type'] == 'long' else 'S3', 0),
            'Pips': pips_gained,
            'Profit': profit,
            'Capital': capital,
            'Duration': days_held
        })
    
    return pd.DataFrame(trades), capital
