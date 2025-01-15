# Plot window duration, forward rates, and profit with enhanced visuals
fig, ax = plt.subplots(figsize=(12, 6))

for _, row in all_cashflows_df.iterrows():
    # Plot the forward rates between Window Open Date and Maturity Date
    ax.plot(
        [row["Window Open Date"], row["Maturity Date"]],
        [row["Forward Rate (Window Open Date)"], row["Forward Rate (Maturity Date)"]],
        color="blue", label="Forward Rates", alpha=0.7
    )
    # Add a vertical line connecting the window open rate to the x-axis
    ax.axvline(
        x=row["Window Open Date"], color="gray", linestyle="--", alpha=0.5
    )
    # Highlight key points (Window Open Rate and Maturity Rate)
    ax.scatter(
        row["Window Open Date"], row["Forward Rate (Window Open Date)"],
        color="orange", s=80, label="Window Open Rate"
    )
    ax.scatter(
        row["Maturity Date"], row["Forward Rate (Maturity Date)"],
        color="green", s=80, label="Maturity Rate"
    )

# Chart styling
ax.set_title("Forward Windows with Enhanced Graphics", fontsize=16)
ax.set_xlabel("Date", fontsize=12)
ax.set_ylabel("Forward Rate (PLN)", fontsize=12)
ax.grid(color="gray", linestyle="--", linewidth=0.5, alpha=0.7)
ax.legend(loc="upper left", fontsize=10)
plt.tight_layout()
st.pyplot(fig)
