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
st.markdown("<div style='border: 1px solid #ddd; padding: 10px;'>Tabela pokazuje prognozowane przychody, koszty oraz wynikowy zysk netto dla każdego roku. Dane te są podstawą do dalszych obliczeń w modelu.</div>", unsafe_allow_html=True)
st.write(financial_data)  # Wyświetla tabelę z prognozami finansowymi

# Założenia
st.header("Kluczowe założenia")
st.markdown("<div style='border: 1px solid #ddd; padding: 10px;'>Założenia pozwalają dostosować model do rzeczywistości biznesowej. Możesz zmienić oczekiwaną marżę zysku, wskaźnik cena/zysk (P/E) oraz stopę dyskontową, które wpływają na wycenę firmy.</div>", unsafe_allow_html=True)  # Wyjaśnia, że poniżej można zmieniać założenia modelu
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
st.header("Wymagania finansowe i emisja nowych udziałów")
st.markdown("<div style='border: 1px solid #ddd; padding: 10px;'>W tej sekcji obliczamy, ile kapitału musisz pozyskać, aby pokryć koszty działalności w pierwszych trzech latach. Możesz również obliczyć, ile nowych udziałów należy wyemitować, aby uzyskać potrzebną kwotę.</div>", unsafe_allow_html=True)  # Wyjaśnia, ile kapitału jest potrzebne
koszty_pierwsze_3_lata = financial_data[financial_data["Rok"] <= 2027]["Koszty (zł)"].sum()
udzial_inwestorow = st.slider("Oferowany udział inwestorów (%):", 10, 50, 25) / 100
pozyskany_kapital = koszty_pierwsze_3_lata / udzial_inwestorow
wycena_post_money = pozyskany_kapital / udzial_inwestorow
wycena_pre_money = wycena_post_money - pozyskany_kapital

# Wyświetlanie obliczeń
st.subheader("Wyniki")
st.markdown("<div style='border: 1px solid #ddd; padding: 10px;'>Wyniki zawierają kluczowe wskaźniki finansowe, takie jak całkowite koszty, wycena firmy w roku 8, wartość bieżąca, a także pozyskany kapitał i wyceny pre-money oraz post-money.</div>", unsafe_allow_html=True)
st.write(f"### Łączne koszty (pierwsze 3 lata): {koszty_pierwsze_3_lata:,.2f} zł")
st.write(f"### Wycena w roku 8: {wycena_rok_8:,.2f} zł")
st.write(f"### Wartość bieżąca: {wartosc_biezaca:,.2f} zł")
st.write(f"### Pozyskany kapitał: {pozyskany_kapital:,.2f} zł")

# Obliczenia dla emisji nowych udziałów
wartosc_nominalna_udzialu = st.number_input("Wartość nominalna jednego udziału (zł):", value=50, step=1)
nowe_udzialy = pozyskany_kapital / wartosc_nominalna_udzialu
st.write(f"### Liczba nowych udziałów do emisji: {nowe_udzialy:.0f}")
st.write(f"### Nowy całkowity kapitał zakładowy: {pozyskany_kapital + wycena_pre_money:,.2f} zł")
st.write(f"### Wycena post-money: {wycena_post_money:,.2f} zł")
st.write("Wycena post-money to wartość firmy po zakończeniu rundy inwestycyjnej. Obejmuje pozyskany kapitał i określa całkowitą wartość firmy w momencie zakończenia inwestycji. Jest kluczowa dla wyznaczenia udziałów założycieli i inwestorów.")
st.write(f"### Wycena pre-money: {wycena_pre_money:,.2f} zł")

# Podział udziałów
udzial_zalozycieli = 1 - udzial_inwestorow
st.subheader("Podział udziałów")
st.markdown("<div style='border: 1px solid #ddd; padding: 10px;'>Pokazujemy, jak udziały w firmie są podzielone między założycieli i inwestorów po zakończeniu rundy inwestycyjnej.</div>", unsafe_allow_html=True)
st.write(f"- Założyciele: {udzial_zalozycieli * 100:.2f}%")
st.write(f"- Inwestorzy: {udzial_inwestorow * 100:.2f}%")

# Zysk inwestorów
roi_inwestora = wycena_rok_8 * udzial_inwestorow / pozyskany_kapital
zysk_nominalny_inwestora = wycena_rok_8 * udzial_inwestorow - pozyskany_kapital
zysk_procentowy_inwestora = (zysk_nominalny_inwestora / pozyskany_kapital) * 100

st.subheader("Zysk inwestorów")
st.markdown("<div style='border: 1px solid #ddd; padding: 10px;'>Obliczamy zwrot z inwestycji (ROI) dla inwestorów w nominalnych wartościach oraz procentach. Zysk ten zależy od wyceny firmy w roku 8 i początkowej inwestycji.</div>", unsafe_allow_html=True)
st.write(f"### Zwrot z inwestycji (ROI): {roi_inwestora:.2f}x")
st.write(f"### Zysk inwestorów (nominalny): {zysk_nominalny_inwestora:,.2f} zł")
st.write(f"### Zysk inwestorów (%): {zysk_procentowy_inwestora:.2f}%")

# Zysk założycieli
zysk_nominalny_zalozycieli = wycena_rok_8 * udzial_zalozycieli
zysk_procentowy_zalozycieli = (zysk_nominalny_zalozycieli / wycena_post_money) * 100

st.subheader("Zysk założycieli")
st.markdown("<div style='border: 1px solid #ddd; padding: 10px;'>Pokazujemy wartość zysku założycieli w oparciu o ich udziały oraz prognozowaną wycenę firmy w roku 8. Zysk ten jest obliczany w wartościach nominalnych i procentowych.</div>", unsafe_allow_html=True)
st.write(f"### Zysk założycieli (nominalny): {zysk_nominalny_zalozycieli:,.2f} zł")
st.write(f"### Zysk założycieli (%): {zysk_procentowy_zalozycieli:.2f}%")

# Wizualizacje
st.header("Wizualizacje")
st.markdown("<div style='border: 1px solid #ddd; padding: 10px;'>Wizualizacje przedstawiają przychody netto, zyski netto oraz podział udziałów założycieli i inwestorów w firmie.</div>", unsafe_allow_html=True)  # Wyjaśnia, że poniżej znajdują się wykresy

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
