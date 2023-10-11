import random
import os
import rsa
import math
import time
import networkx as nx
import matplotlib.pyplot as plt
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
plt.ion()
import logging
from Transaction.transaction import Transaction
from RandomWalker.randomwalker_Thread import RandomWalker
from Network.node_Thread import Node, Coordinator

# from Network.node import Node

class IOTA_DAG:
    def __init__(self, poisson_rate, milestones_interval, network ):
        self.creation_time = datetime.now()
        self.network = network
        self.poisson_rate = poisson_rate
        self.transactions = {}
        self.tips = []
        self.graph = nx.DiGraph()
        self.batch_num = 0  # initialize batch number
        self.batches = []  # list of batches
        self.num_batches = 0  # store the number of batches
        self.current_batch = 0  # store the current batch number
        self.coordinator = None
        self.milestones_interval = milestones_interval
        self.last_milestone_time = datetime.now()
        self.milestone_thread = threading.Thread(target=self.invoke_generate_milestone_after_delay)
        self.milestone_thread.start()
        self.print_lock = threading.Lock()  # assuming print_lock is a threading.Lock() object
        self.transactions_lock = threading.Lock()
        self.tips_lock = threading.Lock()
        self.weight_lock = threading.Lock()
        self.loggers = {node.name: logging.getLogger(node.name) for node in network.nodes}

        self.stop_threads = threading.Event()

    def coordinator_genesis_milestone(self):
        # Generate a random data string
        data = os.urandom(500000)  # generates 500,000 bytes = 0.5 MB
        data = data.decode('latin1')  # decode bytes to string using 'latin1' encoding
        # Create the genesis transaction with no parent transactions and with data
        genesis_milestone = Transaction("0", [], None, data)
        # Sign the transaction's data using the Coordinator's private key
        genesis_milestone.signature = rsa.sign(
            genesis_milestone.get_data_to_sign(),
            self.coordinator.private_key,
            'SHA-256'
        )
        # Use Coordinator's method to broadcast the milestone to all peers
        start_time = datetime.now()
        self.tips.append(genesis_milestone)
        self.coordinator.broadcast_milestone(genesis_milestone)
        # Add the genesis milestone to the transactions of DAG_Event
        self.transactions[genesis_milestone.txid] = genesis_milestone

        threads = []
        for node in self.network.nodes:
            if node != self.coordinator:
                delay = self.network.delay_matrix[(self.coordinator, node)]
                thread = threading.Thread(target=self.process_node, args=(node, delay))
                threads.append(thread)
                thread.start()

        for thread in threads:
            thread.join()

        end_time = datetime.now()
        total_time = end_time - start_time
        print(
            f"Total time taken by Coordinator to broadcast to all its peers: {total_time.seconds} seconds, {total_time.microseconds} microseconds")
        self.loggers[node.name].info(
            f"{datetime.now().strftime('%H:%M:%S.%f')} -  Total time taken by Coordinator to broadcast to all its peers: {total_time.seconds} seconds, {total_time.microseconds} microseconds")


    def process_node(self, node, delay):
        time.sleep(delay)
        with self.print_lock:  # assuming print_lock is a threading.Lock() object
            print(f"Transaction received by {node.name} from {self.coordinator.name} with delay: {delay} seconds")
            self.loggers[node.name].info(
                f"{datetime.now().strftime('%H:%M:%S.%f')} - Transaction received by {node.name} from {self.coordinator.name} with delay: {delay} seconds ")
            print("Number of transactions for node", node.name, ":", len(node.nodes_received_transactions))
            self.loggers[node.name].info(
                f"{datetime.now().strftime('%H:%M:%S.%f')} - Number of transactions for node {node.name} : {len(node.nodes_received_transactions)} ")

    def add_transactions(self, node, network):
        print(f"{node.name} Started Genrating the Transaction")
        self.loggers[node.name].info(
            f"{datetime.now().strftime('%H:%M:%S.%f')} -  {node.name} Started Genrating the Transaction")
        start_time = datetime.now()
        new_transactions = []
        last_timestamp = None
        nodes_tips = list(node.tips)  # Create a copy of the tips
        if not nodes_tips:
            return
        # Instantiate the random walker
        random_walker = RandomWalker(W=3, N=2, alpha_low=0.001, alpha_high=1.0, node=node.name)
        new_transactions = []
        random_walk_tips = random_walker.walk_event(self, nodes_tips)
        # if len(set(nodes_tips)) < 2:
        #     random_walk_tips = [nodes_tips[0], nodes_tips[0]]
        # else:
        #     random_walk_tips = random_walker.walk_event(self, nodes_tips)
        tips = random_walk_tips
        if not isinstance(tips, list):
            tips = [tips]  # Convert to list if not a list
        # Validate signatures of parent transactions
        valid = True
        for parent in tips:
            # Skip the genesis transaction
            if parent.txid == "0":
                continue
            print("Started checking conflict")
            self.loggers[node.name].info(
                f"{datetime.now().strftime('%H:%M:%S.%f')} - Start checking the conflict ")
            if not parent.validate_transaction(DIFFICULTY=1):
                print(f"Invalid signature detected in parent transaction: {parent.txid}. Skipping this transaction.")
                self.loggers[node.name].info(
                    f"{datetime.now().strftime('%H:%M:%S.%f')} - Invalid signature detected in parent transaction: {parent.txid}. Skipping this transaction. ")
                valid = False
                break
            if valid:
                print("Parent transaction(s) have valid signatures. No double spending detected.")
                self.loggers[node.name].info(
                    f"{datetime.now().strftime('%H:%M:%S.%f')} - Parent transaction(s) have valid signatures. No double spending detected.  ")
            self.loggers[node.name].info(
                f"{datetime.now().strftime('%H:%M:%S.%f')} - End checking the conflict ")
        with self.transactions_lock:
            txid = str(len(self.transactions))
            parent_txids = list(set(parent.txid for parent in tips))
            tx = node.create_and_sign_transaction(txid, parent_txids, DIFFICULTY=1)
            # Update parent_transactions
            tx.parent_transactions = [self.transactions[parent_id] for parent_id in parent_txids]
            self.transactions[txid] = tx
            new_transactions.append(tx)


        tx.batch_num = self.batch_num

        for parent in tx.parent_transactions:
            parent.children.append(tx)


            if len(parent.children) == 1:
                self.tips.append(parent)

        for parent in parent_txids:
            self.graph.add_edge(parent, txid)


        with self.tips_lock:
            self.tips = [tx for tx in self.tips + list(self.transactions.values()) if not tx.children]
        self.batches.append(new_transactions)
        self.batch_num += 1

        # Update accumulative weights
        with self.weight_lock:
            self.update_weights_topological_order()

        # Update branch weights
        with self.weight_lock:
            for tx in new_transactions:
                tx.update_branch_weight()

        # Broadcast the transaction to all peers
        print(
            f"{datetime.now().strftime('%H:%M:%S.%f')} - {node.name} started broadcasting the TRANSACT ID: {tx.txid}")
        self.loggers[node.name].info(
            f"{datetime.now().strftime('%H:%M:%S.%f')} - {node.name} started broadcasting the TRANSACT ID: {tx.txid} ")
        node.broadcast_transaction(tx, self)
        if network.transaction_received_by_all(txid):
            print(f"Transaction ID {tx.txid} has been received by all nodes.")
            self.loggers[node.name].info(
                f"{datetime.now().strftime('%H:%M:%S.%f')} - Transaction ID {tx.txid} has been received by all nodes. ")

        print(f"{node.name}: Added {tx} to DAG.")
        self.loggers[node.name].info(
            f"{datetime.now().strftime('%H:%M:%S.%f')} - {node.name}: Added {tx} to DAG. ")
        end_time = network.get_last_receive_time(txid)
        total_time = end_time - start_time
        print(f"Total time for transaction {txid} to reach all nodes: {total_time}")
        self.loggers[node.name].info(
            f"{datetime.now().strftime('%H:%M:%S.%f')} - Total time for transaction {txid} to reach all nodes: {total_time} ")

        self.coordinator.cooridnator_view(tx)

    def invoke_generate_milestone_after_delay(self):
        while True:
            current_time =datetime.now()
            if (current_time - self.last_milestone_time).total_seconds() >= self.milestones_interval:
                self.coordinator.generate_milestone(current_time)
                self.last_milestone_time = datetime.now()

    def update_weights_topological_order(self):
        # Get a topological order of the transactions
        order = list(nx.topological_sort(self.graph))

        # Print the order
        print("Topological order of transactions:", order)

        # Update the weights in this order
        for txid in order:
            tx = self.transactions[txid]
            tx.update_accumulative_weight()


    def simulate_node(self, sim_time, node, network, start_time):
        current_time = time.time()
        transactions = []
        node_poisson_rate = self.poisson_rate[node.name]  # Get the Poisson rate for this node

        while current_time - start_time < sim_time * 60:  # Convert minutes to seconds
        # while len(transactions) < sim_time:
            tx = self.add_transactions(node, network)

            # Add new transaction to list
            if tx and tx.parent_txids:
                transactions.append(tx)

            # Update branch weights for all transactions
            transaction_values = list(self.transactions.values())  # Create a list of values
            for tx in transaction_values:
                tx.update_branch_weight()

            # Get delay for the next transaction when all node have same poission rate
            # delay = random.expovariate(self.poisson_rate)
            ############
            # Get delay for the next transaction when all node have diferent poission rate
            delay = random.expovariate(node_poisson_rate)

            # # Wait for the delay
            # time.sleep(delay)

            # Update current time
            current_time = time.time()

        return transactions

    def simulate(self, sim_time, network):
        start_time = time.time()  # Get the current time
        transactions = []

        nodes_without_coordinator = [node for node in network.nodes if not isinstance(node, Coordinator)]
        # Shuffle the nodes list to randomize the order
        random.shuffle(nodes_without_coordinator)

        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(self.simulate_node, sim_time, node, network, start_time) for node in
                       nodes_without_coordinator]

            # Wait for all futures to complete and gather transactions
            transactions = [future.result() for future in futures]

        self.draw()
        self.print_weights()

        # Flatten list of lists
        transactions = [tx for sublist in transactions for tx in sublist]
        # Transactions per second in Tangle
        transactions_per_second = len(transactions) / sim_time
        print(f"Transactions per second: {transactions_per_second}")

        return transactions
    def print_weights(self):
        print("\nUpdated accumulative weights and branch weights:")
        for txid, tx in self.transactions.items():
            print(
                f"Transaction {txid}: Accumulative weight = {tx.accumulative_weight}, Branch weight = {tx.branch_weight}")
        print("\n")

    ###############################################
    def draw(self):
        # Create a directed graph object
        G = nx.DiGraph()

        # Set node colors and labels
        node_colors = {}
        node_labels = {}  # Store node labels
        depth_map = {}
        max_depth = 0

        for tx in self.transactions.values():

            # Add transaction ID as a label
            label = f"ID: {tx.txid}\nAW: {tx.accumulative_weight}"
            node_labels[tx.txid] = label

            # Determine the color of the node
            if tx.txid == '1':  # assuming you have an `is_genesis` property
                node_colors[tx.txid] = 'orange'  # Orange for genesis transaction
                depth_map[tx.txid] = 1

            elif tx in self.tips and tx.txid != "0":
                node_colors[tx.txid] = 'grey'  # grey for tips
                depth_map[tx.txid] = max((depth_map[parent_txid] + 1 for parent_txid in tx.parent_txids),default= 0)
                max_depth = max(max_depth, depth_map[tx.txid])
            elif tx.is_confirmed or tx.txid == '0':
                node_colors[tx.txid] = 'green'  # green for confirmed transactions
                depth_map[tx.txid] = max((depth_map[parent_txid] + 1 for parent_txid in tx.parent_txids), default=0)
                max_depth = max(max_depth, depth_map[tx.txid])
            else:
                node_colors[tx.txid] = 'blue'  # blue for other nodes
                depth_map[tx.txid] = max((depth_map[parent_txid] + 1 for parent_txid in tx.parent_txids),default= 0)
                max_depth = max(max_depth, depth_map[tx.txid])

        # Get node positions
        pos = {}
        for tx in self.transactions.values():
            depth = depth_map[tx.txid]
            same_depth_txs = [t for t, d in depth_map.items() if d == depth]
            level_size = len(same_depth_txs)
            index_in_level = same_depth_txs.index(tx.txid)
            vertical_position = (index_in_level + 1) / (level_size + 1)  # to make it range between 0 and 1
            # vertical_position = (index_in_level + 1) / (level_size + 1) * level_size  # Scale positions by level_size
            pos[tx.txid] = (depth, vertical_position)

        # Convert node_colors to list maintaining the order of transactions
        node_colors_list = [node_colors[tx.txid] for tx in self.transactions.values()]

        # Add edges to the graph and set their colors
        edge_colors = []
        for tx in self.transactions.values():
            for parent_txid in tx.parent_txids:
                G.add_edge(tx.txid, parent_txid)
                # G.add_edge(parent_txid, tx.txid)
                edge_colors.append('grey' if parent_txid == '0' else 'blue')

        # Draw the graph
        plt.figure(figsize=(10, 5))
        nx.draw(G, pos=pos, node_color=node_colors_list, node_size=1000, node_shape='s', edge_color=edge_colors)
        nx.draw_networkx_labels(G, pos, labels=node_labels, font_size=8)
        plt.title(f'Batch {self.current_batch}')
        # plt.ylim(0, max(level_size for level_size in depth_map.values())) # Adjust ylim based on maximum level_size
        plt.ylim(0, 1)  # Make sure all nodes fit in the figure
        plt.xlim(-1, max_depth + 2)
        #plt.savefig(f'Figures/my_plot_{self.current_batch}.png')
        plt.pause(1)
        plt.show(block=True)

