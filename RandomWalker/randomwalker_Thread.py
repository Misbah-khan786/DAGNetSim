import random
from datetime import datetime, timedelta
import threading
import math
from collections import deque
from pprint import pprint
import networkx as nx
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
        self.N = 3
        self.alpha_low = alpha_low
        self.alpha_high = alpha_high
        self.node= node
        self.logger = logging.getLogger(node)

    def walk_event(self, dag, prev_tips):
        print(f" {self.node} TIP SELECTION STARTS")
        self.logger.info(f"{datetime.now().strftime('%H:%M:%S.%f')} - {self.node} STARTS RANDOM WALK")

        # Get the current time
        current_time = datetime.now()

        # Define the interval (W to WD seconds)
        w = 45# Start of interval, in seconds
        wd = w * 2  # End of interval, in seconds
        # for tx in dag.transactions.values():
        #     print(f" Transaction {tx.txid} was  created at {tx.timestamp} with parent {tx.parent_txids} .")

        # If the DAG is younger than the specified interval (WD seconds), adjust WD
        if current_time - dag.creation_time < timedelta(seconds=wd):
            wd = int((current_time - dag.creation_time).total_seconds())
            print(f"DAG is younger than {wd} seconds, adjusted [W,2W] to the DAG's age")
            self.logger.info(f"{datetime.now().strftime('%H:%M:%S.%f')} - For {self.node} : DAG is younger than {wd} seconds, adjusted [W,2W] to the DAG's age  ")

        # Get the start and end times for the interval
        start_time = current_time - timedelta(seconds=wd)
        end_time = current_time - timedelta(seconds=w)

        # Get all transactions that happened within the interval
        interval_transactions = [tx for tx in dag.transactions.values() if start_time <= tx.timestamp <= end_time]


        print(f"Transactions from the past {w}-{wd} seconds:")
        self.logger.info(f"{datetime.now().strftime('%H:%M:%S.%f')} -  For {self.node} Transactions from the past {w}-{wd} seconds:")
        print(', '.join("Txid=" + str(transaction.txid) for transaction in interval_transactions))
        self.logger.info(', '.join("Txid=" + str(transaction.txid) for transaction in interval_transactions))

        if len(interval_transactions) < self.N:
            start_transactions = interval_transactions
            print(f"Not enough transactions in the interval, selected all {len(start_transactions)} transactions")
            self.logger.info(f"{datetime.now().strftime('%H:%M:%S.%f')} - {self.node} : Not enough transactions in the interval, selected all {len(start_transactions)} transactions")
        else:
            # Randomly select N transactions from the interval
            start_transactions = random.sample(interval_transactions, self.N)
            print(f"Randomly selected N={self.N} transactions from the interval:")
            self.logger.info(f"{datetime.now().strftime('%H:%M:%S.%f')} -For {self.node}:Randomly selected N={self.N} transactions from the interval:")
            print(', '.join("Txid=" + str(transaction.txid) for transaction in start_transactions))
            self.logger.info(', '.join("Txid=" + str(transaction.txid) for transaction in start_transactions))

        # Let the transactions perform independent random walks towards the tips
        reached_tips = []
        tip_paths = {}
        #print("Starting random walk for selected N transactions")
        # Prepare threads list
        threads = []
        for i, start_transaction in enumerate(start_transactions):
            # Create a new thread for each random walk and give it a unique name
            t = threading.Thread(target=self.walk_from, args=(start_transaction, reached_tips, tip_paths),
                                 name=f"Thread-{i}")
            # Start the thread
            t.start()
            # Add the thread to the threads list
            threads.append(t)

            # Wait for all threads to finish
        for t in threads:
            t.join()

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
            path_to_tip = self.compute_path_to_tip_event(dag, random_tip, interval_transactions)
            print("RANDOM REACHED TIP PATH", path_to_tip)
            tip_paths[random_tip.txid] = [path_to_tip]
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

    def walk_from(self, start_transaction, reached_tips, tip_paths):
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

                # # Compute and normalize probabilities
                # H_x = current_transaction.accumulative_weight
                # weights = [child.accumulative_weight for child in current_transaction.children]  # H_y values
                # sum_exp = np.sum([np.exp(-self.alpha_low * (H_x - weight)) for weight in weights])
                # probabilities = [np.exp(-self.alpha_low * (H_x - weight)) * sum_exp ** (-1) for weight in weights]
                # probabilities /= np.sum(probabilities)

                # Create a dictionary of child IDs and their corresponding probabilities
                prob_dict = {child.txid: prob for child, prob in zip(current_transaction.children, probabilities)}

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

        # This is a critical section, we must ensure that no two threads modify these lists at the same time
        with threading.Lock():
            # Append a tuple containing the transaction and the current timestamp
            reached_tips.append((current_transaction, datetime.now()))  # Corrected here
            path_ids = [transaction.txid for transaction in path]
            if current_transaction.txid in tip_paths:
                tip_paths[current_transaction.txid].append(path_ids)
            else:
                tip_paths[current_transaction.txid] = [path_ids]

    def compute_path_to_tip_event(self, dag, tip, interval_transactions):
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

    def select_model_tip(self, dag, prev_tips, current_batch_transactions):
        print("MODEL TIP SELECTION START")
        # Get the transactions from W batches back
        if len(dag.batches) < self.W:
            print("Number of batches is less that W=", self.W, "so selected Random Tip")
            if len(prev_tips) >= self.N:  # Check if there are enough tips for sampling
                print("Length of Previous Tips", len(prev_tips))
                a= random.sample(prev_tips, 2)
                print("Selected Tips", a )
                return a
            else:  # If there aren't enough tips, return all of them
                return prev_tips

        transactions = dag.batches[-self.W]
        # If there aren't enough transactions in the batch, select all transactions from the batch
        if len(transactions) < self.N:
            start_transactions = transactions
            print("There aren't enough transactions in the batch, select all transactions from the batch",
                  start_transactions)
        else:
            # Otherwise, randomly select N transactions from the batch
            start_transactions = random.sample(transactions, self.N)
            print("Randomly select N", self.N, " transactions from the batch")
            print("Including: ", ', '.join("Txid=" + str(transaction.txid) for transaction in start_transactions))

        # Let the transactions perform independent random walks towards the tips
        reached_tips = []
        tip_frequency = {}
        tip_paths = {}  # We'll use this to store paths to each tip
        current_batch_txids = set(tx.txid for tx in current_batch_transactions)

        for start_transaction in start_transactions:
            print("Model tip random walk loop started for transaction Txid=", start_transaction.txid)
            current_transaction = start_transaction
            print("current transaction is Txid", current_transaction.txid)
            path = [current_transaction]  # Initialize path list with start transaction
            while current_transaction.children and any(
                    child.txid not in current_batch_txids for child in current_transaction.children):
                # Biased random walk: transition probability is proportional to exp(alpha * Hy)
                probabilities = [np.exp(self.alpha_high * child.accumulative_weight) for child in
                                 current_transaction.children]
                probabilities /= np.sum(probabilities)  # Normalize probabilities
                current_transaction = np.random.choice(current_transaction.children, p=probabilities)
                path.append(current_transaction)  # Add the chosen transaction to the path
                print("Chosed the transaction", current_transaction.txid, "based on high probabilty")

            reached_tips.append(current_transaction)
            # Convert the list of Transaction objects into a list of their txids:
            path_ids = [transaction.txid for transaction in path]
            if current_transaction in tip_paths:
                tip_paths[current_transaction].append(path_ids)  # Add the path to the list of paths for this tip
            else:
                tip_paths[current_transaction] = [path_ids]  # Initialize list of paths for this tip

        for tip in reached_tips:
            if tip in tip_frequency:
                tip_frequency[tip] += 1
            else:
                tip_frequency[tip] = 1

        max_frequency = max(tip_frequency.values())
        if max_frequency == 1:
            print("No deterministic model tip.")
            self.model_tip = random.choice(list(tip_frequency.keys()))
        else:
            # Select the tip that was reached the most times as the model tip
            model_tips = [tip for tip, freq in tip_frequency.items() if freq == max_frequency]
            if len(model_tips) > 1:
                print("Multiple tips reached the same maximum number of times, they are:",
                      ', '.join(str(tip) for tip in model_tips))
            self.model_tip = random.choice(model_tips)

        model_paths = tip_paths[self.model_tip]  # Get the paths leading to the model tip

        print("MODEL TIP SELECTED WITH HIGH FREQUENCY", self.model_tip)
        return [self.model_tip], model_paths  # Return both the model tip and its paths

    def walk(self, dag, prev_tips, current_batch_transactions): # previous tips added to insure parallel behaviour
        # If there aren't enough batches to go W back, select from available tips
        print("TIP SELECTION STARTS")
        if len(dag.batches) < self.W:
            print("Number of batches is less that W=", self.W, "so selected randomly")
            return random.sample(prev_tips, self.N)
            # return random.sample(dag.tips, self.N) # if all transaction are not genrated from one node

        # Get the transactions from W batches back
        transactions = dag.batches[-self.W]
        print("Transaction selected from current - W =", self.W, "batch")
        print("Including: ", ', '.join("Txid=" +str(transaction.txid) for transaction in transactions))

        # If there aren't enough transactions in the batch, select all transactions from the batch
        if len(transactions) < self.N:
            start_transactions = transactions
            print("There aren't enough transactions in the batch, select all transactions from the batch",start_transactions)
        else:
            # Otherwise, randomly select N transactions from the batch
            start_transactions = random.sample(transactions, self.N)
            print("Randomly select N",self.N, " transactions from the batch")
            print("Including: ", ', '.join("Txid=" + str(transaction.txid) for transaction in start_transactions))

        # Let the transactions perform independent random walks towards the tips
        reached_tips = []
        current_batch_txids = set(tx.txid for tx in current_batch_transactions)
        tip_paths = {}
        #print("Starting random walk for selected N transactions")
        for start_transaction in start_transactions:
            print("Random walk loop started for transaction Txid=",  start_transaction.txid)
            current_transaction = start_transaction
            print("current transaction is Txid", current_transaction.txid)
            path = [start_transaction]
            while current_transaction.children and any(child.txid not in current_batch_txids for child in current_transaction.children):
                #print("while current transaction has childern or not reach to the tip")
                if self.alpha_low == 0:
                    # Unbiased random walk: all children have equal probability
                    probabilities = [1 / len(current_transaction.children)] * len(current_transaction.children)
                    print("Unbiased walk because alpha is 0")
                else:
                    # Biased random walk: transition probability is proportional to exp(alpha * Hy)
                    print("Biased Random walk starts")
                    probabilities = [np.exp(self.alpha_low * child.accumulative_weight) for child in current_transaction.children]
                    probabilities /= np.sum(probabilities)  # Normalize probabilities


                current_transaction = np.random.choice(current_transaction.children, p=probabilities)
                path.append(current_transaction) # Updating the path
                print("Chosed the transaction", current_transaction.txid, "based of probabilty")

            reached_tips.append(current_transaction)
            # Convert the list of Transaction objects into a list of their txids:
            path_ids = [transaction.txid for transaction in path]
            if current_transaction in tip_paths:
                tip_paths[current_transaction.txid].append(path_ids)  # Add the path to the list of paths for this tip
            else:
                tip_paths[current_transaction.txid] = [path_ids]  # Initialize list of paths for this tip

        reached_tips = list(set(reached_tips))  # Use a set to remove duplicates

        # If fewer than two unique tips were reached, select additional tips randomly
        while len(reached_tips) < 2:
            print("fewer than two unique tips were reached, select additional tips randomly")
            #available_tips = [tx for tx in dag.tips if tx not in reached_tips]
            available_tips = [tx for tx in prev_tips if tx not in reached_tips] #changed to previous tips
            if not available_tips:
                break   #return 1 tip just in case there is only one tip in the DAG
            random_tip = random.choice(available_tips)
            #reached_tips.append(random_tip)
            path_to_tip = self.compute_path_to_tip(dag, random_tip, self.W)
            print("RANDOM REACHED TIP PATH",path_to_tip)
            tip_paths[random_tip.txid] = [path_to_tip]
            reached_tips.append(random_tip)

        # Return the two transactions that reached the tip set first (we assume that "first" means smallest txid)
        reached_tips.sort(key=lambda tx: tx.txid)
        selected_tips = reached_tips[:2]
        # Get the paths of the selected tips
        selected_paths = [tip_paths[tip.txid] for tip in selected_tips]
        print("Reached Tips", [tx.txid for tx in selected_tips])

        # Print each path separately
        for i, (tip, path) in enumerate(zip(selected_tips, selected_paths), start=1):
            print(f"Path for Reached Tip {i} (Txid={tip.txid}):", path)

        # return selected_tips, selected_paths
        return selected_tips

    def compute_path_to_tip(self, dag, tip, W):
        path = [tip.txid]
        current_transaction = tip
        W_batch_txids = set(tx.txid for tx in dag.batches[-W])

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

    def consistency_check(self, model_path, path):
        # Ensure paths are lists of transactions
        if isinstance(model_path, Transaction):
            model_path = [model_path]
        if isinstance(path, Transaction):
            path = [path]

        if all(isinstance(sublist, list) for sublist in model_path):
            flat_model_path = [transaction for sublist in model_path for transaction in sublist]
        else:
            flat_model_path = model_path  # Assuming model_path is a list of Transaction objects
        set1 = {transaction for transaction in flat_model_path}

        if all(isinstance(sublist, list) for sublist in path):
            flat_path = [transaction for sublist in path for transaction in sublist]
        else:
            flat_path = path  # Assuming model_path is a list of Transaction objects
        set2 = {transaction for transaction in flat_path}

        # Calculate intersection of sets
        intersection = set1 & set2

        # Calculate overlap percentage
        overlap = (len(intersection) / max(len(set1), len(set2))) * 100

        return overlap