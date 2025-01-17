import streamlit as st
import pandas as pd

# Tytuł strony
st.title("Model Finansowania i Wyceny Startupu")

# Sekcja wejściowa
st.header("Wprowadź swoje dane o przychodach i kosztach")

# Dane o przychodach i kosztach
data = {
    "Rok": [2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032],
    "Przychody netto (zł)": [0, 771875, 2253875, 4106375, 5958875, 7811375, 9663875, 11516375],
    "Koszty (zł)": [850800, 1357200, 1568400, 1568400, 1568400, 1568400, 1568400, 1568400],
}

# Tworzenie DataFrame
financial_data = pd.DataFrame(data)
financial_data["Zysk netto (zł)"] = financial_data["Przychody netto (zł)"] - financial_data["Koszty (zł)"]
financial_data["Oczekiwana marża netto (%)"] = (financial_data["Zysk netto (zł)"] / financial_data["Przychody netto (zł)"]).fillna(0) * 100

# Wyświetlanie danych finansowych
st.subheader("Prognozowane dane finansowe")
st.markdown("<div style='border: 1px solid #ddd; padding: 10px;'>Tabela pokazuje prognozowane przychody, koszty, zysk netto oraz oczekiwaną marżę netto dla każdego roku. Dane te są podstawą do dalszych obliczeń w modelu.</div>", unsafe_allow_html=True)
st.write(financial_data)

# Założenia
st.header("Kluczowe założenia")
profit_margin = st.slider("Oczekiwana marża zysku (rok 8, %):", 10, 80, 20) / 100
pe_multiple = st.slider("Wskaźnik cena/zysk (P/E):", 5, 25, 15)
discount_rate = st.slider("Stopa dyskontowa (%):", 10, 50, 30) / 100
udzial_inwestorow = st.slider("Udział inwestorów (%):", 5, 95, 30) / 100

# Obliczenie wyceny w roku 8
przychody_rok_8 = financial_data[financial_data["Rok"] == 2032]["Przychody netto (zł)"].values[0]
zysk_rok_8 = przychody_rok_8 * profit_margin
wycena_rok_8 = zysk_rok_8 * pe_multiple

# Dyskontowanie do wartości bieżącej
czynnik_dyskontowy = (1 + discount_rate) ** 8
wartosc_biezaca = wycena_rok_8 / czynnik_dyskontowy

# Definicje udziałów i kapitału
pozyskany_kapital = 3_700_000
udzial_zalozycieli = 1 - udzial_inwestorow

# Wyświetlanie wyników
st.header("Wyniki i stopy zwrotu")
st.write(f"### Wycena firmy w roku 8: {wycena_rok_8:,.2f} zł")
st.write(f"### Wartość bieżąca firmy: {wartosc_biezaca:,.2f} zł")
st.write(f"### Pozyskany kapitał od inwestorów: {pozyskany_kapital:,.2f} zł")
st.write(f"### Udział założycieli: {udzial_zalozycieli * 100:.2f}%")
st.write(f"### Udział inwestorów: {udzial_inwestorow * 100:.2f}%")

# Obliczenie stopy zwrotu (ROI) i zysków nominalnych
zysk_inwestorow = wycena_rok_8 * udzial_inwestorow - pozyskany_kapital
zysk_zalozycieli = wycena_rok_8 * udzial_zalozycieli
roi_inwestorow = wycena_rok_8 * udzial_inwestorow / pozyskany_kapital

# Obliczenie wskaźnika zysk inwestora / wartość bieżąca firmy
if wartosc_bieząca > 0:
    ratio_value = zysk_inwestorow / wartosc_bieząca
    ratio_value_rounded = round(ratio_value, 2)
    if ratio_value_rounded > 1:
        ratio_interpretation = "Inwestycja jest bardzo opłacalna dla inwestorów."
    elif 0.8 <= ratio_value_rounded <= 1:
        ratio_interpretation = "Inwestycja jest uczciwie wyważona między zyskami a wartością firmy."
    elif 0.5 <= ratio_value_rounded < 0.8:
        ratio_interpretation = "Inwestycja jest umiarkowanie opłacalna dla inwestorów."
    else:
        ratio_interpretation = "Inwestycja jest mało opłacalna dla inwestorów."
else:
    ratio_value_rounded = "Nie można obliczyć"
    ratio_interpretation = "Wartość bieżąca firmy jest równa zeru lub ujemna."

# Wyświetlanie wskaźnika i interpretacji
st.write(f"### Wskaźnik zysk inwestora / wartość bieżąca firmy: {ratio_value_rounded}")
st.write(f"### Interpretacja wskaźnika: {ratio_interpretation}")

# Wyświetlanie stóp zwrotu i zysków nominalnych
st.write(f"### Zysk inwestorów (nominalny): {zysk_inwestorow:,.2f} zł")
st.write(f"### Zysk założycieli (nominalny): {zysk_zalozycieli:,.2f} zł")
st.write(f"### Stopa zwrotu inwestorów (ROI): {roi_inwestorow:.2f}x")

# Interpretacja wskaźnika ROI
if roi_inwestorow >= 2:
    interpretation = "Bardzo wysoka stopa zwrotu dla inwestorów. Inwestycja jest wysoce opłacalna."
elif 1 <= roi_inwestorow < 2:
    interpretation = "Dobra stopa zwrotu. Inwestycja jest atrakcyjna, ale nie spektakularna."
else:
    interpretation = "Niska stopa zwrotu. Inwestycja może nie spełnić oczekiwań."

st.write(f"### Interpretacja stopy zwrotu: {interpretation}")

st.write("### Użyj tego modelu, aby symulować różne scenariusze, zmieniając założenia!")
