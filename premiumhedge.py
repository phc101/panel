def run_backtest(self, df, initial_capital=10000, lot_size=1.0, spread_pips=2, holding_days=5):
    """
    Uruchom backtest strategii
    Strategia: 
    - KUP gdy cena dotknie lub przekroczy S3
    - ZAMKNIJ pozycję po X dniach (stały okres)
    """
    
    trades = []
    capital = initial_capital
    position = None  # None, 'long'
    
    for i in range(len(df)):
        row = df.iloc[i]
        
        # Pomiń jeśli brak poziomów pivot
        if pd.isna(row.get('S3')) or pd.isna(row.get('R3')):
            continue
        
        current_price = row['Close']
        current_high = row['High']
        current_low = row['Low']
        
        # Sprawdź czy należy zamknąć istniejącą pozycję (po X dniach)
        if position is not None:
            days_held = (row['Date'] - position['entry_date']).days
            
            if days_held >= holding_days:
                # Zamknij pozycję po X dniach
                exit_price = current_price
                
                # Uwzględnij spread przy zamknięciu
                exit_price_with_spread = exit_price - (spread_pips * 0.0001)
                
                # Oblicz profit
                pip_value = 0.0001  # dla większości par
                if 'JPY' in df.attrs.get('symbol', ''):
                    pip_value = 0.01
                
                pips_gained = (exit_price_with_spread - position['entry_price']) / pip_value
                profit = pips_gained * pip_value * position['lot_size'] * 100000  # standardowy lot
                
                # Aktualizuj kapitał
                capital += profit
                
                # Zapisz transakcję
                trades.append({
                    'Entry Date': position['entry_date'],
                    'Exit Date': row['Date'],
                    'Entry Price': position['entry_price'],
                    'Exit Price': exit_price_with_spread,
                    'Entry S3': position['entry_s3'],
                    'Exit R3': row.get('R3', 0),
                    'Pips': pips_gained,
                    'Profit': profit,
                    'Capital': capital,
                    'Duration': days_held,
                    'Exit Reason': f'Time ({holding_days} days)'
                })
                
                # Resetuj pozycję
                position = None
        
        # Otwórz nową pozycję LONG gdy cena dotknie S3 (tylko jeśli nie mamy pozycji)
        if position is None:
            # Sprawdź czy Low dotknęło lub przekroczyło S3
            if current_low <= row['S3']:
                # Otwórz pozycję na cenie Close lub S3 (która jest wyższa)
                entry_price = max(current_price, row['S3'])
                
                # Uwzględnij spread
                entry_price_with_spread = entry_price + (spread_pips * 0.0001)
                
                position = {
                    'type': 'long',
                    'entry_date': row['Date'],
                    'entry_price': entry_price_with_spread,
                    'entry_s3': row['S3'],
                    'target_r3': row['R3'],
                    'lot_size': lot_size
                }
    
    # Zamknij otwartą pozycję na końcu backtestingu
    if position is not None:
        last_row = df.iloc[-1]
        exit_price = last_row['Close'] - (spread_pips * 0.0001)
        
        pip_value = 0.0001
        if 'JPY' in df.attrs.get('symbol', ''):
            pip_value = 0.01
        
        pips_gained = (exit_price - position['entry_price']) / pip_value
        profit = pips_gained * pip_value * position['lot_size'] * 100000
        
        capital += profit
        
        days_held = (last_row['Date'] - position['entry_date']).days
        
        trades.append({
            'Entry Date': position['entry_date'],
            'Exit Date': last_row['Date'],
            'Entry Price': position['entry_price'],
            'Exit Price': exit_price,
            'Entry S3': position['entry_s3'],
            'Exit R3': last_row.get('R3', 0),
            'Pips': pips_gained,
            'Profit': profit,
            'Capital': capital,
            'Duration': days_held,
            'Exit Reason': 'End of data'
        })
    
    return pd.DataFrame(trades), capital
