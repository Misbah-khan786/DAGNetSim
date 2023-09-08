import pandas as pd
import matplotlib.pyplot as plt
import datetime
import os
import re
import seaborn as sns


def extract_info_from_log(file_path):
    with open(file_path, 'r') as f:
        content = f.readlines()

    generated = {}
    received = {}
    for line in content:
        try:
            if "GENRATED THE TRANSACT ID:" in line:
                parts = line.split(" - ")  # split timestamp and log message
                try:
                    timestamp = datetime.datetime.strptime(parts[0], "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    print(f"Skipping line due to ValueError: {line}")
                    continue
                node = int(re.findall(r"Node (\d+)", parts[4])[0])  # Adjusted index
                transaction_id = int(re.findall(r"TRANSACT ID: (\d+)", parts[4])[0])  # Adjusted index

                if node not in generated:
                    generated[node] = 0
                generated[node] += 1

                if transaction_id not in received:
                    received[transaction_id] = timestamp.timestamp()

            if "has been received by all nodes." in line:
                parts = line.split(" - ")
                parts = line.split(" - ")  # split timestamp and log message
                try:
                    timestamp = datetime.datetime.strptime(parts[0], "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    print(f"Skipping line due to ValueError: {line}")
                    continue
                transaction_id = int(re.findall(r"Transaction ID (\d+)", parts[4])[0])  # Adjusted index

                if transaction_id in received:
                    received[transaction_id] = timestamp.timestamp() - received[transaction_id]
        except IndexError:
            print(f"Error processing line: {line}")
            print(f"Split parts: {line.split(' - ')}")

    return generated, received

# Improve overall aesthetics
sns.set_theme()

def to_dataframe(generated, received):
    # Convert the received dict to a DataFrame
    received_df = pd.DataFrame(list(received.items()), columns=['Transaction_ID', 'Time'])

    # Convert the generated dict to a DataFrame, and transpose it for easier plotting
    generated_df = pd.DataFrame(dict([(k, pd.Series(v)) for k, v in generated.items()])).T
    generated_df = generated_df.reset_index().rename(columns={'index': 'Node'})

    # Merge the two DataFrames on the transaction ID
    df = pd.merge(generated_df, received_df, on='Transaction_ID')

    return df

def print_info(generated, received):
    print("\nNumber of transactions generated by each node:")
    for node, count in sorted(generated.items()):
        print(f"Node {node}: {count} transactions")

    print("\nPropagation time for each transaction:")
    for trans_id, time in sorted(received.items()):
        print(f"Transaction {trans_id}: propagated in {time} seconds")

    print("\nAverage propagation time:", sum(received.values()) / len(received.values()))



def visualize_info(generated, received):
    if not received:  # Check if 'received' is empty
        print("No transactions received by all nodes in the logs_3.")
        return
    # Scatter plot for transaction propagation times
    # plt.figure(figsize=(10, 6))
    # plt.scatter(received.keys(), received.values(), color='red', alpha=0.7, edgecolors='w', linewidth=0.5)
    # # Compute the average propagation time and plot it as a line
    # average_time = sum(received.values()) / len(received.values())
    # plt.axhline(average_time, color='b', linestyle='--')
    # # Add a text box with the average value on the plot
    # plt.text(0.02, average_time, f'Average: {average_time:.2f}', fontsize=12, va='center', ha='left',
    #          backgroundcolor='w')
    # plt.title("Transaction Propagation Time", fontsize=20, fontweight='bold')
    # plt.xlabel("Transaction ID", fontsize=14)
    # plt.ylabel("Propagation Time (seconds)", fontsize=14)
    # plt.grid(True)
    # plt.show()
    # Scatter plot for transaction propagation times
    plt.figure(figsize=(10, 6))
    plt.scatter(received.keys(), [value * 1000 for value in received.values()], color='red', alpha=0.7, edgecolors='w',
                linewidth=0.5)

    # Compute the average propagation time (in milliseconds) and plot it as a line
    average_time_milliseconds = sum(received.values()) * 1000 / len(received.values())
    plt.axhline(average_time_milliseconds, color='b', linestyle='--')

    # Add a text box with the average value (in milliseconds) on the plot
    plt.text(0.02, average_time_milliseconds, f'Average: {average_time_milliseconds:.4f} ms', fontsize=12, va='center',
             ha='left',
             backgroundcolor='w')

    plt.title("Transaction Propagation Time", fontsize=20, fontweight='bold')
    plt.xlabel("Transaction ID", fontsize=14)
    plt.ylabel("Propagation Time (milliseconds)", fontsize=14)
    plt.grid(True)
    plt.show()
    # Bar chart for transactions generated by each node
    # Create the bar chart with a single subdued color
    plt.figure(figsize=(8, 7))

    # Use a gray or similar color for a subdued look
    plt.bar(generated.keys(), generated.values(), color='lightblue', edgecolor='black', linewidth=0.5)

    # Adding a title and labels
    plt.title("Number of Transactions Generated by Each Node", fontsize=16)
    plt.xlabel("Node", fontsize=14)
    plt.ylabel("Number of Transactions", fontsize=14)

    # Displaying node labels on the x-axis
    plt.xticks(list(generated.keys()))

    # Adding minor gridlines for clarity
    plt.minorticks_on()
    plt.grid(which='major', linestyle='-', linewidth='0.5', axis='y')
    plt.grid(which='minor', linestyle=':', linewidth='0.5', axis='y')

    # # Displaying values on top of bars (optional)
    # for i, v in enumerate(generated.values()):
    #     plt.text(i, v + 0.5, str(v), ha='center', va='bottom', fontsize=10)

    # Using tight layout
    plt.tight_layout()

    # Showing the plot
    plt.show()
    #
    # # Pie chart for transactions generated by each node
    # plt.figure(figsize=(10, 6))
    # # Explode out the largest piece
    # explode = [0.1 if i == max(generated.values()) else 0 for i in generated.values()]
    # plt.pie(generated.values(), labels=generated.keys(), autopct='%1.1f%%', startangle=140, explode=explode)
    # plt.title("Proportion of Transactions Generated by Each Node")
    # plt.show()

    # # Line chart for transactions generated by each node
    # plt.figure(figsize=(10, 6))
    # sns.lineplot(x=list(generated.keys()), y=list(generated.values()), sort=False, lw=2)
    # plt.title("Number of Transactions Generated by Each Node")
    # plt.xlabel("Node")
    # plt.ylabel("Number of Transactions")
    # plt.show()


def analyze_logs(logs_dir):
    generated = {}  # {node: count_of_generated_transactions}
    received = {}  # {transaction_id: propagation_time}

    for log_file in os.listdir(logs_dir):
        file_path = os.path.join(logs_dir, log_file)
        gen, rec = extract_info_from_log(file_path)

        # Combine dictionaries
        for node, count in gen.items():
            if node not in generated:
                generated[node] = 0
            generated[node] += count

        for trans_id, time in rec.items():
            if trans_id not in received:
                received[trans_id] = 0.0
            received[trans_id] = max(received[trans_id], time)  # get the max time for each transaction

    # Visualization
    visualize_info(generated, received)
    # Printing raw data
    print_info(generated, received)

if __name__ == "__main__":
    # Your logs_3 directory
    logs_dir = "logs_3"
    analyze_logs(logs_dir)
