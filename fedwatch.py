import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import re

st.set_page_config(page_title="Forward EUR/PLN z marżą", layout="centered")
st.title("📈 Wycena forward EUR/PLN z marżą brokera")

st.markdown("Wgraj CSV z forwardami (kolumny: `Unnamed: 1`, `bid`), a my zajmiemy się resztą 😉")

# Parametry wejściowe
spot = st.number_input("Kurs spot EUR/PLN", value=4.2860, step=0.0001)
margin_percent = st.number_input("Marża całkowita (%)", value=0.5, step=0.1) / 100
uploaded_file = st.file_uploader("📄 Wgraj plik CSV", type="csv")

# Funkcja do konwersji zapadalności na dni
def maturity_to_days(code):
    code = code.upper()
    if code == "ON": return 1
    elif code == "TN": return 2
    elif code == "SN": return 3
    elif code == "SW": return 7
    match = re.search(r"(\d+)([WMY])", code)
    if match:
        num, unit = int(match.group(1)), match.group(2)
        if unit == "W": return num * 7
        elif unit == "M": return num * 30
        elif unit == "Y": return num * 365
    return 0

if uploaded_file:
    try:
        df_raw = pd.read_csv(uploaded_file)

        if "Unnamed: 1" not in df_raw.columns or "bid" not in df_raw.columns:
            st.error("❌ CSV musi zawierać kolumny: 'Unnamed: 1' i 'bid'")
        else:
            df = df_raw[["Unnamed: 1", "bid"]].copy()
            df.columns = ["MaturityRaw", "Bid"]
            df = df[df["MaturityRaw"].str.contains("EURPLN")]

            # Wydobycie np. '4M', '2W', 'ON' itp.
            df["Maturity"] = df["MaturityRaw"].str.extract(r"EURPLN\s+([A-Z0-9]+)\s+FWD")

            # Obliczenie dat zapadalności
            spot_date = datetime.today() + timedelta(days=2)
            df["DaysToMaturity"] = df["Maturity"].apply(maturity_to_days)
            df["MaturityDate"] = df["DaysToMaturity"].apply(lambda d: (spot_date + timedelta(days=d)).date())

            # Kursy forward
            df["BidPts"] = df["Bid"] / 10_000
            df["ForwardRynkowy"] = (spot + df["BidPts"]).round(4)

            # Obliczenia marży rosnącej
            total_eur = 12_000_000
            total_margin_eur = total_eur * margin_percent
            n = len(df)
            weights = list(range(1, n + 1))
            weight_sum = sum(weights)
            margin_eur_list = [(w / weight_sum) * total_margin_eur for w in weights]
            margin_share_list = [m / 1_000_000 for m in margin_eur_list]

            df["Marża EUR"] = [round(m) for m in margin_eur_list]
            df["Udział %"] = [round(m * 100, 4) for m in margin_share_list]
            df["Forward z marżą"] = (df["ForwardRynkowy"] * (1 - pd.Series(margin_share_list))).round(4)

            # Finalna tabela
            df_result = df[["Maturity", "MaturityDate", "Bid", "ForwardRynkowy", "Marża EUR", "Udział %", "Forward z marżą"]]
            st.subheader("📋 Tabela wynikowa")
            st.dataframe(df_result, use_container_width=True)

            # Wykres
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

            # Eksport CSV
            csv = df_result.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Pobierz jako CSV", data=csv, file_name="forward_z_marza.csv", mime="text/csv")

    except Exception as e:
        st.error(f"❌ Błąd: {e}")
else:
    st.info("⬆️ Wgraj plik CSV z kolumnami: 'Unnamed: 1' (np. 'EURPLN 4M FWD') oraz 'bid' (punkty).")
