import numpy as np
import pandas as pd

def calculate_binomial_tree(prices, days=5, risk_free_rate=0.01):
    # Calculate log returns and volatility
    log_returns = np.log(prices[1:] / prices[:-1])
    sigma = np.std(log_returns)
    
    # Binomial tree parameters
    dt = 1 / 252  # 1 trading day
    u = np.exp(sigma * np.sqrt(dt))
    d = 1 / u
    p = (np.exp(risk_free_rate * dt) - d) / (u - d)
    
    # Initialize the tree
    tree = np.zeros((days + 1, days + 1))
    tree[0, 0] = prices[-1]  # Current price
    
    # Build the tree
    for i in range(1, days + 1):
        for j in range(i + 1):
            tree[j, i] = prices[-1] * (u ** (i - j)) * (d ** j)
    
    return tree, p

# Example usage
prices = np.random.uniform(4.4, 4.6, size=20)  # Replace with actual data
binomial_tree, prob = calculate_binomial_tree(prices)

print("Binomial Tree:")
print(binomial_tree)
print("Probability of Up Movement:", prob)
