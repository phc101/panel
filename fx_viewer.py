import streamlit as st
import pandas as pd

st.title("USD/PLN Forward Rates")

# Replace this with your actual Drive share link
google_drive_url = "https://drive.google.com/file/d/1abcXYZ1234567890/view?usp=sharing"

# Convert to direct download link
file_id = google_drive_url.split("/d/")[1].split("/")[0]
csv_url = f"https://drive.google.com/uc?id={file_id}"

# Try loading the CSV
try:
    df = pd.read_csv(csv_url)
    st.success("Data loaded successfully!")
    st.dataframe(df)

    # Example: plot the forward rates
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)

    st.line_chart(df)

except Exception as e:
    st.error(f"Failed to load CSV: {e}")
