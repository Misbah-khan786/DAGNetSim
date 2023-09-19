import numpy as np
from scipy.stats import poisson, kstest
from Network.network import Network
import matplotlib.pyplot as plt
def simulate(N, p, duration):
    print("Initializing network...")
    network = Network(N, p)
    print("Network initialized.")
    for _ in range(duration):
        print(f"Simulating second {_}...")
        network.simulate_second()
        print(f"Finished simulating second {_}.")
    # Count transactions for each node
    transaction_counts = [len(node.queue) for node in network.nodes]

    # Return transaction counts for analysis
    return transaction_counts
if __name__ == '__main__':

    print("Starting simulation...")
    transaction_counts = simulate(10, 0.5, 60)
    mean_transactions = np.mean(transaction_counts)
    print("Mean Transactions",mean_transactions)
    expected_distribution = [poisson.pmf(i, mean_transactions) for i in range(max(transaction_counts) + 1)]
    print("Expected distribution", expected_distribution)

    # Calculate mean
    lambda_value = np.mean(transaction_counts)

    # Expected Poisson distribution
    expected_distribution = [poisson.pmf(i, lambda_value) for i in range(max(transaction_counts) + 1)]

    # Plot actual distribution
    plt.hist(transaction_counts, bins=range(0, max(transaction_counts) + 2), density=True, alpha=0.5, label="Observed")

    # Plot expected Poisson distribution
    plt.plot(range(max(transaction_counts) + 1), expected_distribution, 'o-', label="Expected (Poisson)")

    plt.xlabel("Transaction Counts")
    plt.ylabel("Probability")
    plt.legend()
    plt.show(block=True)

    # Kolmogorov-Smirnov test
    observed_cdf = np.cumsum(
        np.histogram(transaction_counts, bins=range(0, max(transaction_counts) + 2), density=True)[0])
    expected_cdf = np.cumsum(expected_distribution)
    statistic, p_value = kstest(observed_cdf, expected_cdf)

    print(f"KS Statistic: {statistic}")
    print(f"P-value: {p_value}")

    if p_value > 0.05:
        print("The observed distribution is not significantly different from the expected Poisson distribution.")
    else:
        print("The observed distribution is significantly different from the expected Poisson distribution.")

    # Descriptive Statistics
    mean = np.mean(transaction_counts)
    median = np.median(transaction_counts)
    variance = np.var(transaction_counts)

