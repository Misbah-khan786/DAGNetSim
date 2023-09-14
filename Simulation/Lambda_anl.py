import matplotlib.pyplot as plt
import numpy as np

# Define the lambda values and node counts
lambdas = [10, 50, 100]
node_counts = [10, 50, 100, 500, 1000]

# Calculate total transactions generated by each node for different lambda values and node counts over an hour
hour_in_seconds = 3600
transactions_hourly = np.zeros((len(lambdas), len(node_counts)))
transactions_per_second = np.zeros((len(lambdas), len(node_counts)))

for i, l in enumerate(lambdas):
    for j, n in enumerate(node_counts):
        transactions_per_second[i, j] = l / n
        transactions_hourly[i, j] = transactions_per_second[i, j] * hour_in_seconds
# Print the transactions per second for each lambda and node count
for i, l in enumerate(lambdas):
    print(f"\nFor Lambda = {l}:")
    for j, n in enumerate(node_counts):
        print(f"  For {n} nodes: Each node generates approximately {transactions_per_second[i, j]:.2f} transactions per second.")

# Plot
plt.figure(figsize=(12, 7))

for i, l in enumerate(lambdas):
    plt.plot(node_counts, transactions_hourly[i], marker='o', label=f'Lambda={l}')

plt.xlabel('Number of Nodes')
plt.ylabel('Total Transactions per Node in 1 Hour Simulation')
plt.title('Total Transactions generated by each node for different Lambda values and Node counts in 1 Hour')
plt.xscale('log')
plt.xticks(node_counts, node_counts)
plt.legend()
plt.grid(True, which='both', linestyle='--', linewidth=0.5)
plt.tight_layout()
plt.show()

