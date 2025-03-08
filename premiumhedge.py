        data.iloc[:, 1] = pd.to_numeric(data.iloc[:, 1], errors='coerce')
        data.iloc[:, 2] = pd.to_numeric(data.iloc[:, 2], errors='coerce')
        data["Yield Spread"] = data.iloc[:, 1] - data.iloc[:, 2]
        
        # Train Linear Regression Model
        model = LinearRegression()
        model.fit(data[["Yield Spread"]], data.iloc[:, 3])
        data["Predictive Price"] = model.predict(data[["Yield Spread"]])
        
        # Establish Trading Strategy
        data["Signal"] = np.where(data.iloc[:, 3] < data["Predictive Price"], "BUY", "SELL")
        data["Weekday"] = data["Date"].dt.weekday
        data = data[data["Weekday"] == 0]  # Filter only Mondays
        data["Exit Date"] = data["Date"] + pd.DateOffset(days=30)
        
        # Calculate Returns
        results = []
        stop_loss_pct = st.sidebar.slider("Stop Loss (%)", min_value=0.0, max_value=10.0, value=1.5, step=0.5)
        
        for i, row in data.iterrows():
            exit_row = fx_data[fx_data["Date"] == row["Exit Date"]]
            if not exit_row.empty:
                exit_price = exit_row.iloc[0, 1]
                entry_price = row.iloc[3]
                stop_loss_price = entry_price * (1 - stop_loss_pct / 100) if row["Signal"] == "BUY" else entry_price * (1 + stop_loss_pct / 100)
                
                if row["Signal"] == "BUY":
                    if exit_price < stop_loss_price:
                        exit_price = stop_loss_price  # Enforce stop loss
                    revenue = (exit_price - entry_price) / entry_price * 100
                else:
                    if exit_price > stop_loss_price:
                        exit_price = stop_loss_price  # Enforce stop loss
                    revenue = (entry_price - exit_price) / entry_price * 100
                
                results.append([row["Date"], row["Exit Date"], row["Signal"], entry_price, exit_price, revenue])
        
        result_df = pd.DataFrame(results, columns=["Entry Date", "Exit Date", "Signal", "Entry Price", "Exit Price", "Revenue %"])
        result_df["Cumulative Revenue %"] = result_df["Revenue %"].cumsum()
        result_df["Drawdown %"] = result_df["Cumulative Revenue %"].cummax() - result_df["Cumulative Revenue %"]
        
        # Display Results
        st.subheader("Backtest Results")
        st.dataframe(result_df)

if __name__ == "__main__":
    main()
