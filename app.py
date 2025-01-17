import streamlit as st
import pandas as pd
import numpy as np

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
st.write(financial_data)  # Wyświetla tabelę z prognozami finansowymi

# Założenia
st.header("Kluczowe założenia")  # Wyjaśnia, że poniżej można zmieniać założenia modelu
profit_margin = st.slider("Oczekiwana marża zysku (rok 8, %):", 10, 50, 20) / 100  # Oczekiwana marża zysku
pe_multiple = st.slider("Wskaźnik cena/zysk (P/E):", 5, 25, 15)  # Współczynnik wyceny
discount_rate = st.slider("Stopa dyskontowa (%):", 10, 50, 30) / 100  # Stopa dyskontowa do obliczenia wartości bieżącej

# Obliczenie wyceny w roku 8
przychody_rok_8 = financial_data[financial_data["Rok"] == 2032]["Przychody netto (zł)"].values[0]
zysk_rok_8 = przychody_rok_8 * profit_margin  # Zysk netto w roku 8 = Przychody netto w roku 8 x Marża zysku (założona jako %)
wycena_rok_8 = zysk_rok_8 * pe_multiple  # Wycena firmy w roku 8 = Zysk netto w roku 8 x Wskaźnik cena/zysk (P/E)

# Dyskontowanie do wartości bieżącej
czynnik_dyskontowy = (1 + discount_rate) ** 8
wartosc_biezaca = wycena_rok_8 / czynnik_dyskontowy  # Dyskontowanie wartości przyszłej wyceny do wartości bieżącej

# Wymagania finansowe i udział
st.header("Wymagania finansowe")  # Wyjaśnia, ile kapitału jest potrzebne
koszty_pierwsze_3_lata = financial_data[financial_data["Rok"] <= 2027]["Koszty (zł)"].sum()
udzial_inwestorow = st.slider("Oferowany udział inwestorów (%):", 10, 50, 25) / 100
pozyskany_kapital = koszty_pierwsze_3_lata / udzial_inwestorow
wycena_post_money = pozyskany_kapital / udzial_inwestorow
wycena_pre_money = wycena_post_money - pozyskany_kapital

# Wyświetlanie obliczeń
st.subheader("Wyniki")
st.write(f"### Łączne koszty (pierwsze 3 lata): {koszty_pierwsze_3_lata:,.2f} zł")
st.write(f"### Wycena w roku 8: {wycena_rok_8:,.2f} zł")
st.write(f"### Wartość bieżąca: {wartosc_biezaca:,.2f} zł")
st.write(f"### Pozyskany kapitał: {pozyskany_kapital:,.2f} zł")
st.write(f"### Wycena post-money: {wycena_post_money:,.2f} zł")
st.write(f"### Wycena pre-money: {wycena_pre_money:,.2f} zł")

# Podział udziałów
udzial_zalozycieli = 1 - udzial_inwestorow
st.subheader("Podział udziałów")
st.write(f"- Założyciele: {udzial_zalozycieli * 100:.2f}%")
st.write(f"- Inwestorzy: {udzial_inwestorow * 100:.2f}%")

# Zysk inwestorów
roi_inwestora = wycena_rok_8 * udzial_inwestorow / pozyskany_kapital
zysk_nominalny_inwestora = wycena_rok_8 * udzial_inwestorow - pozyskany_kapital
zysk_procentowy_inwestora = (zysk_nominalny_inwestora / pozyskany_kapital) * 100

st.subheader("Zysk inwestorów")
st.write(f"### Zwrot z inwestycji (ROI): {roi_inwestora:.2f}x")
st.write(f"### Zysk inwestorów (nominalny): {zysk_nominalny_inwestora:,.2f} zł")
st.write(f"### Zysk inwestorów (%): {zysk_procentowy_inwestora:.2f}%")

# Wizualizacje
st.header("Wizualizacje")  # Wyjaśnia, że poniżej znajdują się wykresy

# Wykresy przychodów i zysków
st.line_chart(financial_data.set_index("Rok")["Przychody netto (zł)"], use_container_width=True)
st.line_chart(financial_data.set_index("Rok")["Zysk netto (zł)"], use_container_width=True)

# Wykres udziałów inwestorów i założycieli
import matplotlib.pyplot as plt
fig, ax = plt.subplots()
ax.pie([udzial_zalozycieli, udzial_inwestorow], labels=["Założyciele", "Inwestorzy"], autopct="%1.1f%%", startangle=90)
ax.axis("equal")
st.pyplot(fig)

st.write("### Użyj tego modelu, aby symulować różne scenariusze, zmieniając założenia!")
