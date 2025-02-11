import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# Streamlit app title
st.title("Forward Points File Uploader")

# File uploader
uploaded_file = st.file_uploader("Upload an Excel file", type=["xlsx"])

if uploaded_file is not None:
    try:
        xls = pd.ExcelFile(uploaded_file)
        sheet_names = xls.sheet_names
        
        # Allow user to select the sheet
        sheet = st.selectbox("Select a currency pair:", sheet_names)
        df = pd.read_excel(xls, sheet_name=sheet)
        
        st.success("File uploaded successfully!")
        st.write("Preview of the uploaded file:")
        st.dataframe(df)
        
        # Ensure required columns exist
        required_columns = {'Tenor', 'BID forward', 'ASK forward'}
        if required_columns.issubset(df.columns):
            st.write("### Forward Points vs Tenor")
            
            # Plotting
            fig, ax = plt.subplots()
            ax.plot(df['Tenor'], df['BID forward'], marker='o', linestyle='-', label='BID forward')
            ax.plot(df['Tenor'], df['ASK forward'], marker='s', linestyle='--', label='ASK forward')
            ax.set_xlabel("Tenor")
            ax.set_ylabel("Forward Rate")
            ax.set_title(f"Forward Points Curve - {sheet}")
            ax.legend()
            plt.xticks(rotation=45)
            st.pyplot(fig)
        else:
            st.warning("The uploaded file must contain 'Tenor', 'BID forward', and 'ASK forward' columns.")
    except Exception as e:
        st.error(f"Error processing file: {e}")
