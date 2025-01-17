import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Tytuł strony
st.title("Model Finansowania i Wyceny Startupu")  # Tytuł aplikacji

# Sekcja wejściowa
st.header("Wprowadź swoje dane o przychodach i kosztach")  # Wyjaśnia, że użytkownik wprowadza swoje dane finansowe

# Dane o przychodach i kosztach
# Tabela danych do uzupełnienia
data = {
    "Rok": [2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032],
    "Przychody netto (zł)": [0, 771875, 2253875, 4106375, 5958875, 7811375, 9663875, 11516375],
    "Koszty (zł)": [850800, 1357200, 1568400, 1568400, 1568400, 1568400, 1568400, 1568400],
}

# Tworzenie DataFrame
financial_data = pd.DataFrame(data)
financial_data["Zysk netto (zł)"] = financial_data["Przychody netto (zł)"] - financial_data["Koszty (zł)"]

# Wyświetlanie danych finansowych
st.subheader("Prognozowane dane finansowe")
st.markdown("<div style='border: 1px solid #ddd; padding: 10px;'>Tabela pokazuje prognozowane przychody, koszty oraz wynikowy zysk netto dla każdego roku. Dane te są podstawą do dalszych obliczeń w modelu.</div>", unsafe_allow_html=True)
st.write(financial_data)  # Wyświetla tabelę z prognozami finansowymi

# Założenia
st.header("Kluczowe założenia")
st.markdown("<div style='border: 1px solid #ddd; padding: 10px;'>Założenia pozwalają dostosować model do rzeczywistości biznesowej. Możesz zmienić oczekiwaną marżę zysku, wskaźnik cena/zysk (P/E) oraz stopę dyskontową, które wpływają na wycenę firmy.</div>", unsafe_allow_html=True)  # Wyjaśnia, że poniżej można zmieniać założenia modelu
przychody_rok_8 = financial_data[financial_data["Rok"] == 2032]["Przychody netto (zł)"].values[0]
koszty_rok_8 = financial_data[financial_data["Rok"] == 2032]["Koszty (zł)"].values[0]
profit_margin = (przychody_rok_8 - koszty_rok_8) / przychody_rok_8  # Automatyczne wyliczenie marży zysku na podstawie danych za rok 8  # Oczekiwana marża zysku
pe_multiple = st.slider("Wskaźnik cena/zysk (P/E):", 5, 25, 15)  # Współczynnik wyceny
discount_rate = st.slider("Stopa dyskontowa (%):", 10, 50, 30) / 100  # Stopa dyskontowa do obliczenia wartości bieżącej

# Obliczenie wyceny w roku 8
przychody_rok_8 = financial_data[financial_data["Rok"] == 2032]["Przychody netto (zł)"].values[0]
zysk_rok_8 = przychody_rok_8 * profit_margin  # Zysk netto w roku 8 = Przychody netto w roku 8 x Marża zysku (założona jako %)
wycena_rok_8 = zysk_rok_8 * pe_multiple  # Wycena firmy w roku 8 = Zysk netto w roku 8 x Wskaźnik cena/zysk (P/E)

# Dyskontowanie do wartości bieżącej
czynnik_dyskontowy = (1 + discount_rate) ** 8
wartosc_biezaca = wycena_rok_8 / czynnik_dyskontowy  # Dyskontowanie wartości przyszłej wyceny do wartości bieżącej

# Zysk inwestorów i założycieli dla różnych P/E
st.header("Zysk nominalny inwestorów i założycieli dla różnych P/E")
pe_values = [10, 15, 20, 25]  # Różne wskaźniki P/E
data_pe = []

for pe in pe_values:
    wycena = zysk_rok_8 * pe
    zysk_inwestorow = wycena * udzial_inwestorow - pozyskany_kapital
    zysk_zalozycieli = wycena * udzial_zalozycieli
    data_pe.append({
        "P/E": pe,
        "Zysk inwestorów (zł)": zysk_inwestorow,
        "Zysk założycieli (zł)": zysk_zalozycieli
    })

# Tworzenie wykresu
pe_df = pd.DataFrame(data_pe)
st.write(pe_df)
st.markdown("<div style='border: 1px solid #ddd; padding: 10px;'>Wykres pokazuje, jak zmieniają się zyski nominalne inwestorów i założycieli w zależności od różnych wskaźników P/E w roku 8.</div>", unsafe_allow_html=True)

fig, ax = plt.subplots()
ax.plot(pe_df["P/E"], pe_df["Zysk inwestorów (zł)"], label="Zysk inwestorów")
ax.plot(pe_df["P/E"], pe_df["Zysk założycieli (zł)"], label="Zysk założycieli")
ax.set_xlabel("Wskaźnik P/E")
ax.set_ylabel("Zysk nominalny (zł)")
ax.set_title("Zysk nominalny inwestorów i założycieli przy różnych P/E")
ax.legend()
st.pyplot(fig)

# Wizualizacje
st.header("Wizualizacje")
st.markdown("<div style='border: 1px solid #ddd; padding: 10px;'>Wizualizacje przedstawiają przychody netto, zyski netto oraz podział udziałów założycieli i inwestorów w firmie.</div>", unsafe_allow_html=True)  # Wyjaśnia, że poniżej znajdują się wykresy

# Wykresy przychodów i zysków
st.line_chart(financial_data.set_index("Rok")["Przychody netto (zł)"], use_container_width=True)
st.line_chart(financial_data.set_index("Rok")["Zysk netto (zł)"], use_container_width=True)

# Wykres udziałów inwestorów i założycieli
fig, ax = plt.subplots()
nowe_udzialy_procent = nowe_udzialy / (nowe_udzialy + 100)
zalozyciele_udzialy_procent = 1 - nowe_udzialy_procent  # Zakładamy, że początkowo jest 100 udziałów
zalozyciele_udzialy_procent = 1 - nowe_udzialy_procent
ax.pie([zalozyciele_udzialy_procent, nowe_udzialy_procent], labels=[f"Założyciele (100 udziałów - {zalozyciele_udzialy_procent * 100:.1f}%)", f"Inwestorzy ({nowe_udzialy:.0f} udziałów - {nowe_udzialy_procent * 100:.1f}%)"], autopct="%1.1f%%", startangle=90)
ax.axis("equal")
st.pyplot(fig)

st.write("### Użyj tego modelu, aby symulować różne scenariusze, zmieniając założenia!")
