", 0.0, 10.0, 3.0, step=0.25) / 100

# Horizontal bookmarks for month navigation
selected_month = st.radio(
    "Months", MONTH_NAMES, index=st.session_state.selected_month - 1, horizontal=True
)
st.session_state.selected_month = MONTH_NAMES.index(selected_month) + 1

# Sidebar for managing cashflows
with st.sidebar:
    st.header(f"Add Cashflow for {selected_month}")
    currency = st.selectbox("Currency", ["EUR", "USD"], key="currency")
    amount = st.number_input("Cashflow Amount", min_value=0.0, value=1000.0, step=100.0, key="amount")
    window_open_date = st.date_input("Window Open Date", min_value=datetime.today(), key="window_open_date")
    window_tenor = st.number_input("Window Tenor (in months)", min_value=1, value=1, step=1, key="window_tenor")
    spot_rate = st.number_input("Spot Rate", min_value=0.0, value=4.5, step=0.0001, key="spot_rate")
    points_adjustment = st.slider(
        "Adjust Forward Points up to Window Open Date (%)", 
        0.0, 1.0, 1.0, step=0.01
    )

    # Ensure the tab corresponds to the month of the Window Open Date
    if window_open_date.month != st.session_state.selected_month:
        st.session_state.selected_month = window_open_date.month

    # Calculate maturity date
    maturity_date = window_open_date + timedelta(days=30 * window_tenor)

    if st.button("Add Cashflow"):
        st.session_state.monthly_cashflows[st.session_state.selected_month].append({
            "Currency": currency,
            "Amount": amount,
            "Window Open Date": str(window_open_date),  # Convert to string to ensure persistence
            "Window Tenor (months)": window_tenor,
            "Maturity Date": str(maturity_date),  # Convert to string to ensure persistence
            "Spot Rate": spot_rate,
            "Points Adjustment": points_adjustment,  # Save the points adjustment
        })

# Display and edit cashflows for the selected month
st.header(f"Cashflow Records for {selected_month}")

if len(st.session_state.monthly_cashflows[st.session_state.selected_month]) > 0:
    # Button to delete all records
    if st.button("Delete All"):
        st.session_state.monthly_cashflows[st.session_state.selected_month] = []

    # Editable table simulation with delete buttons
    for idx, cashflow in enumerate(st.session_state.monthly_cashflows[st.session_state.selected_month], start=1):
        st.write(f"Record {idx}:")
        col1, col2 = st.columns([9, 1])
        with col1:
            st.write(f"""
            - Currency: {cashflow['Currency']}
            - Amount: {cashflow['Amount']}
            - Window Open Date: {cashflow['Window Open Date']}
            - Window Tenor: {cashflow['Window Tenor (months)']} months
            - Maturity Date: {cashflow['Maturity Date']}
            - Spot Rate: {cashflow['Spot Rate']}
            - Forward Points Adjustment: {cashflow['Points Adjustment'] * 100:.2f}%
            """)
        with col2:
            if st.button("🗑", key=f"delete_{idx}"):
                st.session_state.monthly_cashflows[st.session_state.selected_month].pop(idx - 1)

# Generate a chart for all records across months
st.header("Forward Window Overview")
all_cashflows = [
    cashflow for cashflows in st.session_state.monthly_cashflows.values() for cashflow in cashflows
]
if all_cashflows:
    all_cashflows_df = pd.DataFrame(all_cashflows)
    # Ensure 'Window Open Date' and 'Maturity Date' are datetime objects
    all_cashflows_df["Window Open Date"] = pd.to_datetime(all_cashflows_df["Window Open Date"])
    all_cashflows_df["Maturity Date"] = pd.to_datetime(all_cashflows_df["Maturity Date"])

    # Calculate forward rates
    all_cashflows_df["Forward Rate (Window Open Date)"] = all_cashflows_df.apply(
        lambda row: row["Spot Rate"] + (
            (calculate_forward_rate(
                row["Spot Rate"], global_domestic_rate, global_foreign_rate,
                (row["Window Open Date"] - datetime.today()).days
            ) - row["Spot Rate"]) * row["Points Adjustment"]
        ),
        axis=1
    )

    # Enhanced Chart: L-Shape for Forward Rates with Custom Date Axis
    fig, ax = plt.subplots(figsize=(12, 6))

    # Collect all relevant dates for the x-axis
    x_ticks = sorted(
        set(all_cashflows_df["Window Open Date"].tolist() + all_cashflows_df["Maturity Date"].tolist())
    )

    for _, row in all_cashflows_df.iterrows():
        # Plot the horizontal line for the forward rate between Window Open Date and Maturity Date
        ax.hlines(
            row["Forward Rate (Window Open Date)"], 
            xmin=row["Window Open Date"], 
            xmax=row["Maturity Date"], 
            color="blue", label="Forward Rate", linewidth=2, alpha=0.7
        )
        # Add vertical line connecting Window Open Rate to x-axis
        ax.axvline(
            x=row["Window Open Date"], 
            color="gray", linestyle="--", alpha=0.5
        )
        # Highlight the starting point (Window Open Rate)
        ax.scatter(
            row["Window Open Date"], row["Forward Rate (Window Open Date)"], 
            color="orange", s=80, label="Window Open Rate"
        )

    # Chart styling
    ax.set_title("Forward Windows with L-Shape Representation", fontsize=16)
    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Forward Rate (PLN)", fontsize=12)
    ax.set_xticks(x_ticks)  # Set x-axis ticks to relevant dates
    ax.set_xticklabels([date.strftime('%Y-%m-%d') for date in x_ticks], rotation=45, fontsize=10)
    ax.grid(color="gray", linestyle="--", linewidth=0.5, alpha=0.7)
    ax.legend(loc="upper left", fontsize=10)
    plt.tight_layout()
    st.pyplot(fig)

    # Aggregated Table: Add Window Open Forward Rate
    st.header("Aggregated Cashflow Summary")
    aggregated_results = []
    for _, row in all_cashflows_df.iterrows():
        aggregated_results.append({
            "Currency": row["Currency"],
            "Amount": row["Amount"],
            "Window Open Date": row["Window Open Date"].strftime("%Y-%m-%d"),
            "Window Tenor (months)": row["Window Tenor (months)"],
            "Maturity Date": row["Maturity Date"].strftime("%Y-%m-%d"),
            "Spot Rate": row["Spot Rate"],
            "Forward Rate (Window Open Date)": row["Forward Rate (Window Open Date)"],
        })
    aggregated_df = pd.DataFrame(aggregated_results)
    st.table(aggregated_df)

# Footer
st.markdown("---")
st.caption("Developed using Streamlit")
