import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# Streamlit app title
st.title("Forward Points File Uploader")

# File uploader
uploaded_file = st.file_uploader("Upload an Excel or CSV file", type=["xlsx", "csv"])

if uploaded_file is not None:
    file_extension = uploaded_file.name.split(".")[-1]
    
    try:
        if file_extension == "csv":
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        st.success("File uploaded successfully!")
        st.write("Preview of the uploaded file:")
        st.dataframe(df)
        
        # Assuming the file contains 'Tenor' and 'Forward Points' columns
        if 'Tenor' in df.columns and 'Forward Points' in df.columns:
            st.write("### Forward Points vs Tenor")
            
            # Plotting
            fig, ax = plt.subplots()
            ax.plot(df['Tenor'], df['Forward Points'], marker='o', linestyle='-')
            ax.set_xlabel("Tenor")
            ax.set_ylabel("Forward Points")
            ax.set_title("Forward Points Curve")
            st.pyplot(fig)
        else:
            st.warning("The uploaded file must contain 'Tenor' and 'Forward Points' columns.")
    except Exception as e:
        st.error(f"Error processing file: {e}")
