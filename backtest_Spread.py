# Dodaj ten kod do swojej aplikacji Streamlit

import streamlit as st
import pandas as pd
import numpy as np

# Expected P/L z backtestów (ŚREDNIE)
expected_pnl_3fwd = {
    'mean': [0.79, 0.58, 0.26],
    'std': [0.45, 0.38, 0.32],  # Przykładowe std dev
    'min': [-1.2, -0.8, -0.6],  # Najgorszy wynik historyczny
    'max': [3.5, 2.8, 2.1]      # Najlepszy wynik historyczny
}

# Disclaimer
st.warning("""
⚠️ **WAŻNE:** Pokazane P/L to **ŚREDNIE HISTORYCZNE** z backtestów 2015-2025.

- **Expected P/L** = Średnia ze wszystkich transakcji tego typu
- **Actual P/L** = Rzeczywisty wynik TWOJEJ transakcji (będzie znany po zamknięciu)
- Każda konkretna transakcja będzie miała **INNE** wyniki w zależności od ruchu rynku

**To NIE jest gwarancja zysków!** Używaj jako wskazówkę, nie pewnik.
""")

# Pokaż expected P/L z rangem
st.subheader("Expected P/L per Forward (z backtestów)")

for i in range(3):
    with st.expander(f"FWD {i+1} (+{i*30}d start)"):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Średnia (Mean)", f"{expected_pnl_3fwd['mean'][i]:+.2f}%")
        
        with col2:
            st.metric("Std Dev", f"±{expected_pnl_3fwd['std'][i]:.2f}%")
        
        with col3:
            st.metric("Najgorszy", f"{expected_pnl_3fwd['min'][i]:+.2f}%")
        
        with col4:
            st.metric("Najlepszy", f"{expected_pnl_3fwd['max'][i]:+.2f}%")
        
        # Dodaj wykres rozkładu
        st.markdown(f"""
        **Interpretacja:**
        - W 68% przypadków wynik będzie między {expected_pnl_3fwd['mean'][i] - expected_pnl_3fwd['std'][i]:.2f}% a {expected_pnl_3fwd['mean'][i] + expected_pnl_3fwd['std'][i]:.2f}%
        - Najgorszy wynik w historii: {expected_pnl_3fwd['min'][i]:.2f}%
        - Najlepszy wynik w historii: {expected_pnl_3fwd['max'][i]:.2f}%
        """)

# Dla konkretnego sygnału - pokaż status
st.subheader("Twoje Pozycje (Real-time)")

# Przykład dla sygnału
signal_date = pd.Timestamp('2025-11-03')

for i in range(3):
    start_date = signal_date + pd.DateOffset(days=i*30)
    end_date = start_date + pd.DateOffset(days=60)
    
    # Check status
    today = pd.Timestamp.now()
    if today < start_date:
        status = "🟡 SCHEDULED"
        status_color = "orange"
    elif start_date <= today <= end_date:
        status = "🟢 ACTIVE"
        status_color = "green"
    else:
        status = "⚫ CLOSED"
        status_color = "gray"
    
    with st.expander(f"FWD {i+1} - {status}"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Planned:**")
            st.write(f"Start: {start_date.strftime('%Y-%m-%d')}")
            st.write(f"End: {end_date.strftime('%Y-%m-%d')}")
            st.write(f"Entry: 4.2537")
        
        with col2:
            st.markdown("**Expected P/L:**")
            st.metric(
                "Mean", 
                f"{expected_pnl_3fwd['mean'][i]:+.2f}%",
                help=f"Średnia historyczna. Twój wynik może być od {expected_pnl_3fwd['min'][i]:.2f}% do {expected_pnl_3fwd['max'][i]:.2f}%"
            )
        
        if status == "🟢 ACTIVE":
            # Symuluj current price (w prawdziwej app: fetch z API)
            current_price = 4.2450  # Przykład
            unrealized_pnl = (4.2537 - current_price) / 4.2537 * 100
            
            st.markdown("**Real-time:**")
            st.metric(
                "Unrealized P/L", 
                f"{unrealized_pnl:+.2f}%",
                delta=f"{unrealized_pnl - expected_pnl_3fwd['mean'][i]:+.2f}% vs expected"
            )
            st.progress(min(max((unrealized_pnl + 2) / 4, 0), 1))  # Progress bar
        
        elif status == "⚫ CLOSED":
            # Przykładowy realized P/L
            realized_pnl = 0.95  # Przykład - będzie z rzeczywistych danych
            
            st.markdown("**Final Result:**")
            st.metric(
                "Realized P/L", 
                f"{realized_pnl:+.2f}%",
                delta=f"{realized_pnl - expected_pnl_3fwd['mean'][i]:+.2f}% vs expected"
            )

print("✅ Kod gotowy do wklejenia do aplikacji Streamlit!")
