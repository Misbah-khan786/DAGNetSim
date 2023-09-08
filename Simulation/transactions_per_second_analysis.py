import datetime
import re
import os
import matplotlib.pyplot as plt


def extract_all_nodes_transactions_per_second_from_log(file_path):
    # Open the log file and read its content
    with open(file_path, 'r') as f:
        content = f.readlines()

    # Dictionary to store counts of transactions added per second for each node
    nodes_transactions_per_second = {}

    for line in content:
        try:
            # Look for lines where a transaction is added to the DAG
            if "Added Transaction" in line:
                parts = line.split(" - ")  # Split timestamp and log message

                # Extract the node number
                node_number = int(re.findall(r"Node (\d+): Added Transaction", line)[0])

                try:
                    timestamp = datetime.datetime.strptime(parts[0], "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    print(f"Skipping line due to ValueError: {line}")
                    continue

                # Round down the timestamp to the nearest second
                timestamp_sec = timestamp.replace(microsecond=0)

                # Create node entry if it doesn't exist
                if node_number not in nodes_transactions_per_second:
                    nodes_transactions_per_second[node_number] = {}

                # Increment the transaction count for this second for the node
                if timestamp_sec not in nodes_transactions_per_second[node_number]:
                    nodes_transactions_per_second[node_number][timestamp_sec] = 0
                nodes_transactions_per_second[node_number][timestamp_sec] += 1

        except (IndexError, ValueError) as e:
            print(f"Error processing line: {line}")
            print(f"Reason: {e}")
            print(f"Split parts: {line.split(' - ')}")

    return nodes_transactions_per_second


def total_transactions_per_second(nodes_transactions_per_second):
    total_transactions = 0
    earliest_time = None
    latest_time = None

    for node, timestamps in nodes_transactions_per_second.items():
        for timestamp, count in timestamps.items():
            total_transactions += count

            # Check and update the earliest timestamp
            if earliest_time is None or timestamp < earliest_time:
                earliest_time = timestamp

            # Check and update the latest timestamp
            if latest_time is None or timestamp > latest_time:
                latest_time = timestamp

    # Calculate total duration in seconds
    total_duration = (latest_time - earliest_time).total_seconds()

    # To avoid division by zero
    if total_duration == 0:
        return total_transactions

    return total_transactions / total_duration


def extract_nodes_time_to_generate_transaction(file_path):
    with open(file_path, 'r') as f:
        content = f.readlines()

    node_timings = {}

    # Temp storage for start times
    start_times = {}

    for line in content:
        try:
            if "STARTS RANDOM WALK" in line:
                node_number = int(re.findall(r"Node (\d+)", line)[0])
                timestamp = datetime.datetime.strptime(line.split(" - ")[0], "%Y-%m-%d %H:%M:%S")
                start_times[(node_number, "random_walk")] = timestamp

            elif "Reached Tips" in line:
                node_number = int(re.findall(r"Node (\d+)", line)[0])
                timestamp = datetime.datetime.strptime(line.split(" - ")[0], "%Y-%m-%d %H:%M:%S")
                if node_number not in node_timings:
                    node_timings[node_number] = {"random_walk": [], "conflict_check": [], "transaction_gen": []}
                node_timings[node_number]["random_walk"].append(
                    (timestamp - start_times[(node_number, "random_walk")]).total_seconds())

            elif "Start checking the conflict" in line:
                node_number = int(re.findall(r"Node (\d+)", line)[0])
                timestamp = datetime.datetime.strptime(line.split(" - ")[0], "%Y-%m-%d %H:%M:%S")
                start_times[(node_number, "conflict_check")] = timestamp

            elif "End checking the conflict" in line:
                node_number = int(re.findall(r"Node (\d+)", line)[0])
                timestamp = datetime.datetime.strptime(line.split(" - ")[0], "%Y-%m-%d %H:%M:%S")
                node_timings[node_number]["conflict_check"].append(
                    (timestamp - start_times[(node_number, "conflict_check")]).total_seconds())

            elif "Started Genrating the Transaction" in line:
                node_number = int(re.findall(r"Node (\d+)", line)[0])
                timestamp = datetime.datetime.strptime(line.split(" - ")[0], "%Y-%m-%d %H:%M:%S")
                start_times[(node_number, "transaction_gen")] = timestamp

            # elif "started broadcasting the TRANSACT ID" in line:
            #     node_number = int(re.findall(r"Node (\d+)", line)[0])
            #     timestamp = datetime.datetime.strptime(line.split(" - ")[0], "%Y-%m-%d %H:%M:%S")
            #     node_timings[node_number]["transaction_gen"].append(
            #         (timestamp - start_times[(node_number, "transaction_gen")]).total_seconds())

        except (IndexError, ValueError) as e:
            print(f"Error processing line: {line}")
            print(f"Reason: {e}")
            print(f"Split parts: {line.split(' - ')}")

    return node_timings


def print_results(logs_dir):
    log_files = os.listdir(logs_dir)
    combined_results = {}
    combined_timings = {}
    transaction_counts = []
    random_walk_times = []

    for log_file in log_files:
        file_path = os.path.join(logs_dir, log_file)

        # Transactions per node
        transactions_per_node = extract_all_nodes_transactions_per_second_from_log(file_path)

        # Timings to generate transactions
        transaction_timings = extract_nodes_time_to_generate_transaction(file_path)

        for node, tx_count in transactions_per_node.items():
            total_transactions = sum(tx_count.values())
            print(f"Node {node} generated {total_transactions} transactions.")

            # Print random walk timings
            for duration in transaction_timings.get(node, {}).get("random_walk", []):
                print(f"\tRandom walk took {duration} seconds.")

            # Print conflict check timings
            for duration in transaction_timings.get(node, {}).get("conflict_check", []):
                print(f"\tConflict check took {duration} seconds.")

            # Print overall transaction generation timings
            for duration in transaction_timings.get(node, {}).get("transaction_gen", []):
                print(f"\tGenerating a transaction took {duration} seconds.")

        # Merge results for transactions
        for node, timestamps in transactions_per_node.items():
            if node not in combined_results:
                combined_results[node] = {}
            for timestamp, count in timestamps.items():
                if timestamp not in combined_results[node]:
                    combined_results[node][timestamp] = 0
                combined_results[node][timestamp] += count

        # Merge results for timings (if needed)
        for node, timings in transaction_timings.items():
            if node not in combined_timings:
                combined_timings[node] = {"random_walk": [], "conflict_check": [], "transaction_gen": []}
            for category, times in timings.items():
                combined_timings[node][category].extend(times)


    transactions_per_second = total_transactions_per_second(combined_results)
    print(f"Overall transactions per second: {transactions_per_second}")


if __name__ == "__main__":
    logs_dir = "logs_3"
    print_results(logs_dir)
