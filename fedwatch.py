import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import re

st.set_page_config(page_title="Forward EUR/PLN z marżą", layout="centered")
st.title("📈 Wycena forward EUR/PLN z marżą brokera")

st.markdown("Załaduj plik CSV z punktami forward, a aplikacja policzy kursy z marżą oraz daty zapadalności.")

# 🔢 Parametry wejściowe
spot = st.number_input("Kurs spot EUR/PLN", value=4.2860, step=0.0001)
margin_percent = st.number_input("Marża całkowita (%)", value=0.5, step=0.1) / 100
uploaded_file = st.file_uploader("📄 Wgraj plik CSV z punktami forward (np. z banku)", type="csv")

# 📆 Funkcja do przeliczania skrótów (np. '1M') na dni
def maturity_to_days_fixed(code):
    if pd.isna(code):
        return 0
    code = code.upper()
    if code == "ON":
        return 1
    elif code == "TN":
        return 2
    elif code == "SN":
        return 3
    elif code == "SW":
        return 7
    elif "W" in code:
        return int(re.findall(r'\d+', code)[0]) * 7
    elif "M" in code:
        return int(re.findall(r'\d+', code)[0]) * 30
    elif "Y" in code:
        return int(re.findall(r'\d+', code)[0]) * 365
    return 0

if uploaded_file:
    try:
        df_raw = pd.read_csv(uploaded_file)

        # 🧹 Wydobycie kolumn z Twojego formatu
        df = df_raw[["Unnamed: 1", "bid"]].copy()
        df.columns = ["MaturityRaw", "Bid"]
        df = df[df["MaturityRaw"].str.contains("EURPLN")]
        df["Maturity"] = df["MaturityRaw"].str.extract(r"EURPLN\s+([A-Z0-9]+)\s+FWD")

        # 📅 Dodanie daty zapadalności
        spot_date = datetime.today() + timedelta(days=2)
        df["DaysToMaturity"] = df["Maturity"].apply(maturity_to_days_fixed)
        df["MaturityDate"] = df["DaysToMaturity"].apply(lambda d: (spot_date + timedelta(days=d)).date())

        # 📊 Kurs forward = spot + punkty
        df["BidPts"] = df["Bid"] / 10_000
        df["ForwardRynkowy"] = (spot + df["BidPts"]).round(4)

        # 🧮 Marża łącznie 0.5% w EUR (rosnąca)
        total_eur = 12_000_000
        total_margin_eur = total_eur * margin_percent
        n = len(df)
        weights = list(range(1, n + 1))
        weight_sum = sum(weights)
        margin_eur_list = [(w / weight_sum) * total_margin_eur for w in weights]
        margin_share_list = [m / 1_000_000 for m in margin_eur_list]

        # 📉 Kursy z marżą
        df["Forward z marżą"] = (df["ForwardRynkowy"] * (1 - pd.Series(margin_share_list))).round(4)
        df["Marża EUR"] = [round(m) for m in margin_eur_list]
        df["Udział %"] = [round(m * 100, 4) for m in margin_share_list]

        # 📋 Widok końcowy
        df_result = df[["Maturity", "MaturityDate", "Bid", "ForwardRynkowy", "Marża EUR", "Udział %", "Forward z marżą"]]
        st.subheader("📋 Tabela wynikowa")
        st.dataframe(df_result, use_container_width=True)

        # 📈 Wykres
        st.subheader("📊 Wykres forwardów")
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(df_result["Maturity"], df_result["ForwardRynkowy"], marker='o', label="Forward rynkowy")
        ax.plot(df_result["Maturity"], df_result["Forward z marżą"], marker='o', label="Forward z marżą")
        ax.set_ylabel("Kurs EUR/PLN")
        ax.set_xlabel("Termin")
        ax.set_title("Porównanie kursów forward EUR/PLN")
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.legend()
        st.pyplot(fig)

        # 📤 Export
        csv = df_result.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Pobierz wynik jako CSV", data=csv, file_name="forward_z_marza.csv", mime="text/csv")

    except Exception as e:
        st.error(f"❌ Błąd przy wczytywaniu pliku: {e}")
else:
    st.info("⬆️ Wgraj plik CSV zawierający kolumny: 'Unnamed: 1' (termin) i 'bid' (punkty)")
