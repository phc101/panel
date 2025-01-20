import streamlit as st
import pandas as pd

# Tytuł strony
st.title("Wycena Premium Hedge")  # Tytuł aplikacji

# Sekcja wejściowa
st.header("Wprowadź swoje dane o przychodach i kosztach")  # Wyjaśnia, że użytkownik wprowadza swoje dane finansowe

# Dane o przychodach i kosztach
# Tabela danych do uzupełnienia
data = {
    "Rok": [2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032],
    "Przychody netto (zł)": [0, 812500, 2372500, 4322500, 6272500, 8222500, 10172500, 12122500],
    "Koszty operacyjne (zł)": [910800, 1417200, 1628400, 1628400, 1628400, 1628400, 1628400, 1628400],
    "Prowizja sprzedażowa (zł)": [0, 40625, 118625, 216125, 313625, 411125, 508625, 606125]
}

# Tworzenie DataFrame
financial_data = pd.DataFrame(data)
financial_data["Zysk netto (zł)"] = financial_data["Przychody netto (zł)"] - financial_data["Koszty operacyjne (zł)"] + financial_data["Prowizja sprzedażowa (zł)"]financial_data["Przychody netto (zł)"] - financial_data["Koszty (zł)"]

# Wyświetlanie danych finansowych
st.subheader("Prognozowane dane finansowe")
st.markdown("<div style='border: 1px solid #ddd; padding: 10px;'>Tabela pokazuje prognozowane przychody, koszty oraz wynikowy zysk netto dla każdego roku. Dane te są podstawą do dalszych obliczeń w modelu.</div>", unsafe_allow_html=True)
st.write(financial_data)  # Wyświetla tabelę z prognozami finansowymi

# Założenia
st.header("Kluczowe założenia")
st.markdown("<div style='border: 1px solid #ddd; padding: 10px;'>Założenia pozwalają dostosować model do rzeczywistości biznesowej. Możesz zmienić oczekiwaną marżę zysku, wskaźnik cena/zysk (P/E) oraz stopę dyskontową, które wpływają na wycenę firmy.</div>", unsafe_allow_html=True)  # Wyjaśnia, że poniżej można zmieniać założenia modelu
przychody_rok_8 = financial_data[financial_data["Rok"] == 2032]["Przychody netto (zł)"].values[0]
koszty_rok_8 = financial_data[financial_data["Rok"] == 2032]["Koszty (zł)"].values[0]
profit_margin = st.slider("Oczekiwana marża zysku (rok 8, %):", 10, 80, 20) / 100  # Użytkownik może ustawić oczekiwaną marżę zysku, zakres do 80%  # Automatyczne wyliczenie marży zysku na podstawie danych za rok 8  # Oczekiwana marża zysku
pe_multiple = st.slider("Wskaźnik cena/zysk (P/E):", 5, 25, 15)  # Współczynnik wyceny
discount_rate = st.slider("Stopa dyskontowa (%):", 10, 50, 30) / 100  # Stopa dyskontowa do obliczenia wartości bieżącej

# Obliczenie wyceny w roku 8
przychody_rok_8 = financial_data[financial_data["Rok"] == 2032]["Przychody netto (zł)"].values[0]
zysk_rok_8 = przychody_rok_8 * profit_margin  # Zysk netto w roku 8 = Przychody netto w roku 8 x Marża zysku (założona jako %)
wycena_rok_8 = zysk_rok_8 * pe_multiple  # Wycena firmy w roku 8 = Zysk netto w roku 8 x Wskaźnik cena/zysk (P/E)

# Dyskontowanie do wartości bieżącej
czynnik_dyskontowy = (1 + discount_rate) ** 8
wartosc_biezaca = wycena_rok_8 / czynnik_dyskontowy  # Dyskontowanie wartości przyszłej wyceny do wartości bieżącej

# Definicje udziałów i kapitału
udzial_inwestorow = 0.3  # Inwestorzy otrzymują 30% udziałów
pozyskany_kapital = 3_700_000  # Ręczna kwota pozyskana od inwestorów w zamian za 30% udziałów  # Kwota zainwestowana przez inwestorów
udzial_zalozycieli = 1 - udzial_inwestorow  # Założyciele zachowują 70%

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

# Wyświetlanie stóp zwrotu i zysków nominalnych
st.write(f"### Zysk inwestorów (nominalny): {zysk_inwestorow:,.2f} zł")
st.write(f"### Zysk założycieli (nominalny): {zysk_zalozycieli:,.2f} zł")
st.write(f"### Stopa zwrotu inwestorów (ROI): {roi_inwestorow:.2f}x")

st.write(f"### Wskaźnik 'Wartość bieżąca firmy / Zysk inwestorów': {wartosc_biezaca / zysk_inwestorow if zysk_inwestorow > 0 else 'Nie można obliczyć'}")

# Interpretacja wskaźnika
if zysk_inwestorow > 0:
    st.markdown("<div style='border: 1px solid #ddd; padding: 10px;'>Wskaźnik 'Wartość bieżąca firmy / Zysk inwestorów' pokazuje, ile razy bieżąca wartość całej firmy przewyższa zysk nominalny inwestorów. **Wysoka wartość wskaźnika** oznacza, że inwestorzy uzyskują stosunkowo małą część wartości firmy, co może być korzystne dla założycieli. **Niska wartość wskaźnika** oznacza, że inwestorzy mają znaczący udział w wartości firmy w stosunku do swojego zysku nominalnego.</div>", unsafe_allow_html=True)
else:
    st.markdown("<div style='border: 1px solid #ddd; padding: 10px;'>Wskaźnik nie został obliczony, ponieważ zysk inwestorów jest ujemny lub równy zeru. Może to oznaczać, że inwestycja nie generuje wystarczającego zwrotu w stosunku do wkładu inwestorów.</div>", unsafe_allow_html=True)

st.write("### Użyj tego modelu, aby symulować różne scenariusze, zmieniając założenia!")
