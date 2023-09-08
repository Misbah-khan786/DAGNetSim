import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import os
def plot_accumulative_weights():
    accumulative_weights = []
    transaction_count = 0

    with open("../AW.txt", 'r') as file:
        for line in file:
            if "Accumulative weight =" in line:
                weight = int(line.split("Accumulative weight = ")[1].split(",")[0].strip())
                transaction_count += 1
                accumulative_weights.append(weight)

    transaction_labels = [f"Transaction {i}" for i in range(1, transaction_count + 1)]

    df = pd.DataFrame({
        'Transaction': transaction_labels,
        'Accumulative Weight': accumulative_weights
    })

    df = df.sort_values(by='Accumulative Weight', ascending=True)

    y = np.arange(len(df['Transaction']))
    x = df['Accumulative Weight'].values
    norm = plt.Normalize(np.log(x.min()), np.log(x.max()))
    colors = plt.cm.viridis(norm(np.log(x)))
    sm = plt.cm.ScalarMappable(cmap="viridis", norm=norm)
    sm.set_array([])

    fig, ax = plt.subplots(figsize=(10, 15))
    ax.barh(y, x, color=colors)
    n = 10
    ax.set_yticks(y[::n])
    ax.set_yticklabels(df['Transaction'].iloc[::n])
    ax.set_xscale("log")
    ax.get_xaxis().set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x))))

    ax.set_xlabel('Accumulative Weight (Log Scale)')
    ax.set_title('Accumulative Weights of Transactions')
    plt.colorbar(sm, ax=ax, orientation="vertical", label="Log of Accumulative Weight")

    plt.tight_layout()
    plt.show()

def moving_average(data, window_size):
    """Computes moving average using a given window size."""
    return np.convolve(data, np.ones(window_size)/window_size, mode='valid')

def plotly_update_times_vs_transaction_count(threshold_upper, threshold_lower):
    log_dir_path = 'logs_3'

    # This list will store transaction IDs
    transaction_ids = []

    # This list will store raw update times from each entry
    update_times_raw = []

    # Iterate over every log file in the logs_3 directory
    for log_file_name in os.listdir(log_dir_path):
        log_file_path = os.path.join(log_dir_path, log_file_name)

        if os.path.isfile(log_file_path):  # check if it's a file to avoid processing subdirectories
            with open(log_file_path, 'r') as log_file:
                for line in log_file:
                    if "Updating Weights" in line:
                        # Extract update time from the log line
                        update_time = float(line.split("Updating Weights took")[1].split("seconds")[0].strip())
                        # Extract transaction ID from the log line
                        transaction_id = int(line.split("for ID ")[1].split(" ")[0].strip())

                        # Store transaction ID and update time
                        transaction_ids.append(transaction_id)
                        update_times_raw.append(update_time)

    # Sorting the transaction IDs and their corresponding update times
    sorted_indices = sorted(range(len(transaction_ids)), key=lambda k: transaction_ids[k])
    transaction_ids = [transaction_ids[i] for i in sorted_indices]
    update_times_raw = [update_times_raw[i] for i in sorted_indices]

    # Identify indices of outliers
    outlier_indices = [i for i, time in enumerate(update_times_raw) if time > threshold_upper or time < threshold_lower]
    outlier_times = [update_times_raw[i] for i in outlier_indices]
    outlier_transaction_ids = [transaction_ids[i] for i in outlier_indices]
    regular_times = [update_times_raw[i] if i not in outlier_indices else None for i in range(len(update_times_raw))]

    # Creating a Plotly figure
    fig = go.Figure()

    # Adding traces
    fig.add_trace(go.Scatter(x=transaction_ids, y=regular_times, mode='lines+markers', name='Regular Data'))
    fig.add_trace(go.Scatter(x=outlier_transaction_ids, y=outlier_times, mode='markers', name='Outliers',
                             marker=dict(color='red')))

    # Updating Layout
    fig.update_layout(title_text='Actual Update Time vs. Transaction ID',
                      xaxis=dict(title='Transaction ID', tickangle=45, tickfont=dict(size=10)),
                      yaxis=dict(title='Update Time (seconds)', range=[0, threshold_upper]),
                      plot_bgcolor='rgb(230, 230, 230)')

    fig.show()


def plotly_random_walk_vs_data_growth():
    log_dir_path = 'logs_3'

    # List storing transaction IDs
    transaction_ids = []

    # List storing times taken for "Random walk tip selection" across all log files
    random_walk_times = []

    # Initialize a counter for transaction IDs
    transaction_id_counter = 0

    # Iterate over every log file in the logs_3 directory
    for log_file_name in os.listdir(log_dir_path):
        log_file_path = os.path.join(log_dir_path, log_file_name)

        if os.path.isfile(log_file_path):  # check if it's a file to avoid processing subdirectories
            with open(log_file_path, 'r') as log_file:
                for line in log_file:
                    if "Initial Setup for Random walk tip selction took" in line:
                        # Extract random walk time from the log line
                        walk_time = float(
                            line.split("Initial Setup for Random walk tip selction took")[1].split("seconds")[
                                0].strip())
                        random_walk_times.append(walk_time)

                        # Increment transaction ID counter and append it to the list
                        transaction_id_counter += 1
                        transaction_ids.append(transaction_id_counter)

    # Apply moving average to smooth out the random walk times. Choose a window size that works best for you.
    smoothed_walk_times = moving_average(random_walk_times, window_size=10)
    smoothed_transaction_ids = transaction_ids[len(transaction_ids) - len(smoothed_walk_times):]

    # Creating a Plotly figure
    fig = go.Figure()

    fig.add_trace(go.Scatter(x=smoothed_transaction_ids,
                             y=smoothed_walk_times,
                             mode='lines+markers',
                             name='Smoothed Random Walk Time'))

    fig.update_layout(title_text='Smoothed Random Walk Time vs. Transaction ID',
                      xaxis=dict(title='Transaction ID'),
                      yaxis=dict(title='Smoothed Random Walk Time (seconds)'),
                      plot_bgcolor='rgb(230, 230, 230)')

    fig.show()


#### collective
def moving_average(data, window_size):
    cumsum = [0]
    for i, x in enumerate(data, 1):
        cumsum.append(cumsum[i - 1] + x)
        if i >= window_size:
            moving_avg = (cumsum[i] - cumsum[i - window_size]) / window_size
            yield moving_avg

def plotly_random_walk_vs_data_growth():
    base_dir = '.'

    categories_dirs = {
        'BRW_N=3': 'logs_2',
        'BRW_N=6': 'logs_N6',
        'UBW': 'logs'
    }

    colors = ['red', 'green', 'blue']

    fig = go.Figure()

    for category, log_dir in categories_dirs.items():
        transaction_ids = []
        random_walk_times = []
        transaction_id_counter = 0
        log_dir_path = os.path.join(base_dir, log_dir)

        for log_file_name in os.listdir(log_dir_path):
            log_file_path = os.path.join(log_dir_path, log_file_name)

            if os.path.isfile(log_file_path):
                with open(log_file_path, 'r') as log_file:
                    for line in log_file:
                        if "Initial Setup for Random walk tip selction took" in line:
                            walk_time = float(
                                line.split("Initial Setup for Random walk tip selction took")[1].split("seconds")[
                                    0].strip())
                            random_walk_times.append(walk_time)
                            transaction_id_counter += 1
                            transaction_ids.append(transaction_id_counter)

        smoothed_walk_times = list(moving_average(random_walk_times, window_size=10))
        smoothed_transaction_ids = transaction_ids[len(transaction_ids) - len(smoothed_walk_times):]

        print(f"{category} -> Transaction IDs: {len(smoothed_transaction_ids)}, Walk Times: {len(smoothed_walk_times)}")

        fig.add_trace(go.Scatter(x=smoothed_transaction_ids,
                                    y=smoothed_walk_times,
                                    mode='lines+markers',
                                    name=f'Smoothed {category} Walk Time',
                                    line=dict(color=colors.pop(0))))  # Using pop to get the color for each category

    fig.update_layout(title_text='Smoothed Random Walk Time vs. Transaction ID',
                        xaxis=dict(title='Transaction ID'),
                        yaxis=dict(title='Smoothed Random Walk Time (seconds)'),
                        plot_bgcolor='rgb(230, 230, 230)')
    fig.show()



if __name__ == "__main__":

    #plotly_update_times_vs_transaction_count()
    plotly_update_times_vs_transaction_count(threshold_upper=25, threshold_lower=0)
    plotly_random_walk_vs_data_growth()
    plot_accumulative_weights()
    # plotly_random_walk_vs_data_growth()
