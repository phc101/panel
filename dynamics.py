import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

st.set_page_config(page_title="FX & Yield Data Downloader", layout="wide")
st.title("📉 EUR/PLN, USD/PLN & Bond Yields Downloader")

st.markdown("Ten agent pobiera dane za ostatnie 12 miesięcy i zapisuje je do CSV.")

# Ustaw daty
end_date = datetime.today()
start_date = end_date - timedelta(days=365)

# Symbole do pobrania
symbols = {
    "EUR/PLN": "EURPLN=X",
    "USD/PLN": "USDPLN=X",
    "PL 3M Yield": "PL3M.IR",       # Przybliżenie 2M
    "DE 3M Yield": "^IRX.DE",       # Możliwe, że trzeba zmienić na konkretny ticker
    "US 3M Yield": "^IRX"           # 13-week T-Bill (3M) jako przybliżenie 2M
}

# Funkcja pobierająca dane
@st.cache_data
def fetch_data():
    data = pd.DataFrame(index=pd.date_range(start=start_date, end=end_date, freq='D'))

    for label, ticker in symbols.items():
        try:
            df = yf.download(ticker, start=start_date, end=end_date)
            df = df[['Close']].rename(columns={'Close': label})
            data = data.join(df, how='left')
        except Exception as e:
            st.warning(f"Nie udało się pobrać danych dla {label}: {e}")

    data = data.dropna(how='all')
    data = data.fillna(method='ffill')  # Uzupełnij luki
    return data

if st.button("📥 Pobierz dane"):
    df = fetch_data()
    st.success("✅ Dane pobrane pomyślnie!")
    st.dataframe(df.tail(10), use_container_width=True)

    csv = df.to_csv(index=True).encode('utf-8')
    st.download_button(
        label="💾 Eksportuj do CSV",
        data=csv,
        file_name='fx_yield_data.csv',
        mime='text/csv',
    )
