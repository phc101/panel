import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Forward EUR/PLN z marżą", layout="centered")

st.title("📈 Wycena forward EUR/PLN z marżą brokera")
st.markdown("Załaduj plik CSV z punktami forward i oblicz kursy z narzutem marżowym.")

# 📥 Dane wejściowe
spot = st.number_input("Kurs spot EUR/PLN", value=4.2860, step=0.0001)
margin_percent = st.number_input("Marża całkowita (%)", value=0.5, step=0.1) / 100
uploaded_file = st.file_uploader("📄 Wgraj plik CSV z punktami forward", type="csv")

if uploaded_file:
    try:
        df_raw = pd.read_csv(uploaded_file)

        if "Maturity" not in df_raw.columns or "Bid" not in df_raw.columns:
            st.error("❌ CSV musi zawierać kolumny: 'Maturity' i 'Bid'")
        else:
            df_raw["BidPts"] = df_raw["Bid"] / 10_000
            df_raw["ForwardRynkowy"] = (spot + df_raw["BidPts"]).round(4)

            total_eur = 12_000_000
            total_margin_eur = total_eur * margin_percent
            n = len(df_raw)
            weights = list(range(1, n + 1))
            weight_sum = sum(weights)

            margin_eur_list = [(w / weight_sum) * total_margin_eur for w in weights]
            margin_share_list = [m / 1_000_000 for m in margin_eur_list]
            fwd_final = (df_raw["ForwardRynkowy"] * (1 - pd.Series(margin_share_list))).round(4)

            df_result = pd.DataFrame({
                "Maturity": df_raw["Maturity"],
                "Forward (rynkowy)": df_raw["ForwardRynkowy"],
                "Marża EUR": [round(m) for m in margin_eur_list],
                "Udział %": [round(m * 100, 4) for m in margin_share_list],
                "Forward z marżą": fwd_final
            })

            st.subheader("📋 Tabela wynikowa")
            st.dataframe(df_result, use_container_width=True)

            # 📈 Wykres
            st.subheader("📊 Wykres forwardów")
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(df_result["Maturity"], df_result["Forward (rynkowy)"], marker='o', label="Forward rynkowy")
            ax.plot(df_result["Maturity"], df_result["Forward z marżą"], marker='o', label="Forward z marżą")
            ax.set_ylabel("Kurs EUR/PLN")
            ax.set_xlabel("Termin zapadalności")
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
    st.info("⬆️ Wgraj plik CSV z kolumnami 'Maturity' i 'Bid' (punkty forwardowe w punktach).")
