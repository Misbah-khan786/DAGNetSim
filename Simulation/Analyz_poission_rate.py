import os
import re
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import expon
import numpy as np

def extract_timestamps_from_log(file_path):

    with open(file_path, 'r') as f:
        content = f.readlines()

    timestamps = []
    for line in content:
        match = re.search(r'(\d{2}:\d{2}:\d{2}\.\d{6}) - Node \d+ GENRATED THE TRANSACT ID:', line)
        if match:
            timestamps.append(match.group(1))

    return timestamps

def analyze_logs(logs_dir):
    log_files = os.listdir(logs_dir)

    all_timestamps = []
    for log_file in log_files:
        file_path = os.path.join(logs_dir, log_file)
        all_timestamps.extend(extract_timestamps_from_log(file_path))

    # Convert strings to datetime objects
    all_timestamps = pd.to_datetime(all_timestamps)

    # Compute inter-arrival times
    inter_arrival_times = all_timestamps.to_series().sort_values().diff().dt.total_seconds()[
                          1:]  # exclude the first NaN value
    print(inter_arrival_times)

    # Plot histogram of inter_arrival_times and fitted exponential distribution
    inter_arrival_times.plot(bins=20, kind='hist', density=True, edgecolor='black', alpha=0.5, label='Data')

    # Calculate parameters for the fitted exponential distribution
    lambda_rate = 1 / inter_arrival_times.mean()

    # Generate values for x (inter-arrival times)
    x = np.linspace(inter_arrival_times.min(), inter_arrival_times.max(), 100)

    # Plot the fitted exponential distribution
    plt.plot(x, expon.pdf(x, scale=1 / lambda_rate), 'r-', lw=2, alpha=0.6, label='Fitted Exponential Distribution')

    # Labeling the plot
    plt.title("Histogram of Inter-Arrival Times & Fitted Exponential Distribution")
    plt.xlabel("Inter-Arrival Time (Seconds)")
    plt.ylabel("Density")
    plt.legend()  # Display the labels in plot
    plt.show()


if __name__ == "__main__":
    # Your logs_3 directory
    logs_dir = "logs_3"
    analyze_logs(logs_dir)
