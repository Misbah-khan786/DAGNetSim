import random
from datetime import datetime, timedelta
import threading
import asyncio
import matplotlib.pyplot as plt
import numpy as np
import logging
from Transaction.transaction import Transaction

plt.ion()
import datetime
from datetime import datetime

class RandomWalker:
    def __init__(self, W, N, alpha_low, alpha_high, node):
        self.W = W
        self.N = 2
        self.alpha_low = alpha_low
        self.alpha_high = alpha_high
        self.node= node
        self.logger = logging.getLogger(node)

    async def walk_event(self, dag, prev_tips):
        print(f" {self.node} TIP SELECTION STARTS")
        self.logger.info(f"{datetime.now().strftime('%H:%M:%S.%f')} - {self.node} STARTS RANDOM WALK")

        # Get the current time
        current_time = datetime.now()

        # Define the interval (W to WD seconds)
        w = 30# Start of interval, in seconds
        wd = w * 2  # End of interval, in seconds

        # If the DAG is younger than the specified interval (WD seconds), adjust WD
        if current_time - dag.creation_time < timedelta(seconds=wd):
            wd = int((current_time - dag.creation_time).total_seconds())
            print(f"DAG is younger than {wd} seconds, adjusted [W,2W] to the DAG's age")
            self.logger.info(f"{datetime.now().strftime('%H:%M:%S.%f')} - For {self.node} : DAG is younger than {wd} seconds, adjusted [W,2W] to the DAG's age  ")

        # Get the start and end times for the interval
        start_time = current_time - timedelta(seconds=wd)
        end_time = current_time - timedelta(seconds=w)

        # Get all transactions that happened within the interval
        interval_transactions = [tx for tx in prev_tips if start_time <= tx.timestamp <= end_time]
        # print("Interval Transactions", interval_transactions)
        print(f"Transactions from the past {w}-{wd} seconds:")
        print(', '.join("Txid=" + str(transaction.txid) for transaction in interval_transactions))
        self.logger.info(', '.join("Txid=" + str(transaction.txid) for transaction in interval_transactions))
        if len(interval_transactions) < self.N:
            start_transactions = interval_transactions
            print(f"Not enough transactions in the interval, selected all {len(start_transactions)} transactions")
        else:
            # Randomly select N transactions from the interval
            start_transactions = random.sample(interval_transactions, self.N)
            print(f"Randomly selected N={self.N} transactions from the interval:")
            print(', '.join("Txid=" + str(transaction.txid) for transaction in start_transactions))
            self.logger.info(', '.join("Txid=" + str(transaction.txid) for transaction in start_transactions))

        # Let the transactions perform independent random walks towards the tips
        reached_tips = []
        tip_paths = {}
        #print("Starting random walk for selected N transactions")
        # Prepare tasks list
        tasks = []
        for i, start_transaction in enumerate(start_transactions):
            # Create a new task for each random walk
            t = asyncio.create_task(self.walk_from(start_transaction, reached_tips, tip_paths))
            # Add the task to the tasks list
            tasks.append(t)
        # Wait for all tasks to finish
        await asyncio.gather(*tasks)
        reached_tips = list(set(reached_tips))  # Use a set to remove duplicates
        # If fewer than two unique tips were reached, select additional tips randomly
        while len(reached_tips) < 2:
            print("Fewer than two unique tips were reached, selected tips randomly")
            self.logger.info(
                f"{datetime.now().strftime('%H:%M:%S.%f')} - For {self.node} Fewer than two unique tips were reached, selected tips randomly")
            available_tips = [tx for tx in prev_tips if tx not in reached_tips]  # changed to previous tips
            if not available_tips:
                break
            random_tip = random.choice(available_tips)
            path_to_tip = await self.compute_path_to_tip_event(dag, random_tip, interval_transactions)
            print("RANDOM REACHED TIP PATH", path_to_tip)
            tip_paths[random_tip.txid] = [ path_to_tip]
            reached_tips.append((random_tip, datetime.now()))

        # Sort the tips by the time they were reached (the second element of the tuple) and take the first two
        reached_tips.sort(key=lambda tup: tup[1])
        selected_tips = [tup[0] for tup in reached_tips[:2]]  # We only want the transaction, not the timestamp
        # Get the paths of the selected tips
        selected_paths = [tip_paths[tip.txid] for tip in selected_tips]
        print("First 2 Reached Tips", [tx.txid for tx in selected_tips])
        reached_tips_str = ", ".join([tx.txid for tx in selected_tips])
        self.logger.info(f"{datetime.now().strftime('%H:%M:%S.%f')} - First 2 Reached Tips: {reached_tips_str}")

        # Print each path separately
        for i, (tip, path) in enumerate(zip(selected_tips, selected_paths), start=1):
            print(f"Path for Reached Tip {i} (Txid={tip.txid}):", path)
            self.logger.info(f"{datetime.now().strftime('%H:%M:%S.%f')} - Path for Reached Tip {i} (Txid={tip.txid}): {str(path)}")

        # return selected_tips, selected_paths
        return selected_tips

    async def walk_from(self, start_transaction, reached_tips, tip_paths):
        print(
            f"{threading.current_thread().name} - Random walk loop started for transaction Txid= {start_transaction.txid}")
        self.logger.info(
            f"{datetime.now().strftime('%H:%M:%S.%f')} - {threading.current_thread().name} - For {self.node} Random walk loop started for transaction Txid= {start_transaction.txid}")
        current_transaction = start_transaction
        print("current transaction is Txid", current_transaction.txid)
        self.logger.info(
            f"{datetime.now().strftime('%H:%M:%S.%f')} - {threading.current_thread().name} For {self.node} current transaction is Txid = {current_transaction.txid} ")
        path = [start_transaction]
        while current_transaction.children:
            # print("while current transaction has childern or not reach to the tip")
            if self.alpha_low == 0:
                # Unbiased random walk: all children have equal probability
                probabilities = [1 / len(current_transaction.children)] * len(current_transaction.children)
                print("Unbiased walk because alpha is 0")
            else:
                # Biased random walk: transition probability is proportional to exp(alpha * Hy)
                print("Biased Random walk starts")

                # Compute and normalize probabilities
                weights = [child.accumulative_weight for child in current_transaction.children]
                probabilities = [np.exp(self.alpha_low * weight) for weight in weights]
                probabilities /= np.sum(probabilities)
                # Create a dictionary of child IDs and their corresponding probabilities and weights
                prob_and_weight_dict = {child.txid: {"prob": prob, "weight": weight} for child, prob, weight in
                                        zip(current_transaction.children, probabilities, weights)}
                print(f"Probability and weight distribution: {prob_and_weight_dict}")
                self.logger.info(
                    f"{datetime.now().strftime('%H:%M:%S.%f')} - {threading.current_thread().name} For {self.node} Probability and weight distribution: {prob_and_weight_dict}")
            current_transaction = np.random.choice(current_transaction.children, p=probabilities)
            path.append(current_transaction)  # Updating the path
            print(
                f"{threading.current_thread().name} - Chose the transaction {current_transaction.txid} based on probability")
            self.logger.info(
                f"{datetime.now().strftime('%H:%M:%S.%f')} - {threading.current_thread().name} - For {self.node}  Select Transaction {current_transaction.txid} based on probability {probabilities}")
        # This is a critical section, we must ensure that no two tasks modify these lists at the same time
        async with asyncio.Lock():
            # Append a tuple containing the transaction and the current timestamp
            reached_tips.append((current_transaction, datetime.now()))  # Corrected here
            path_ids = [transaction.txid for transaction in path]
            if current_transaction.txid in tip_paths:
                tip_paths[current_transaction.txid].append(path_ids)
            else:
                tip_paths[current_transaction.txid] = [path_ids]
    async def compute_path_to_tip_event(self, dag, tip, interval_transactions):
        path = [tip.txid]
        current_transaction = tip
        W_batch_txids = set(tx.txid for tx in interval_transactions)

        while current_transaction.parent_transactions and not any(
                parent.txid in W_batch_txids for parent in current_transaction.parent_transactions):
            # Select the first parent for simplicity; you might need to adjust this
            current_transaction = current_transaction.parent_transactions[0]
            path.append(current_transaction.txid)
        # Add the W-th transaction to the path if it's one of the parents of the current transaction
        W_transaction = [parent for parent in current_transaction.parent_transactions if parent.txid in W_batch_txids]
        if W_transaction:
            path.append(W_transaction[0].txid)
            # Reverse the path so it starts with the W-th transaction and ends with the tip
        path = list(reversed(path))
        return path
