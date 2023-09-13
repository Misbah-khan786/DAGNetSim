import simpy
from Transaction.transaction import Transaction
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time

import rsa
import threading
from threading import Thread, Lock
import time
import math
import random
import os
import networkx as nx
import multiprocessing as mp
from Transaction.transaction import Transaction
from Network.node import Node, Coordinator
from concurrent.futures import ThreadPoolExecutor

from RandomWalker.randomwalker import RandomWalker


class DAG_Event:
    def __init__(self, poisson_rate, milestones_interval, network, loggers):
        self.poisson_rate = poisson_rate
        self.transactions = {}
        self.tips = []
        self.graph = nx.DiGraph()
        self.coordinator = None
        self.milestones_interval = milestones_interval
        self.env = simpy.Environment()  # Add simpy Environment
        self.network = network  # Network reference
        self.graphs = {node.name: nx.DiGraph() for node in self.network.nodes}
        self.graph_events = []  # List to store data for graph drawing events
        self.timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]  # Gives you time up to milliseconds
        self.timestamp += str(int(time.time() * 1e9))[-6:]  # Append the last six digits of the current nanosecond time
        self.print_lock = threading.Lock()
        self.graphs_lock = threading.Lock()
        self.transaction_lock = threading.Lock()
        self.txid_lock = threading.Lock()
        self.txid_counter = 1
        self.loggers = loggers  # loggers is now a list
        for logger in self.loggers:
            logger.info("DAG_Event logger initialized")  # log initialization for each logger

    def log_event(self, event_message):
        for logger in self.loggers:
            logger.info(event_message)  # log the event for each logger

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
        print(f"Total time taken by Coordinator to broadcast to all its peers: {total_time.seconds} seconds, {total_time.microseconds} microseconds")

        # # Update and draw graphs for each node after broadcasting the genesis transaction
        # for node in self.network.nodes:
        #     self.update_and_draw_graphs(node)

    def process_node(self, node, delay):
        time.sleep(delay)
        with self.print_lock:  # assuming print_lock is a threading.Lock() object
            print(f"Transaction received by {node.name} from {self.coordinator.name} with delay: {delay} seconds")
            print("Number of transactions for node", node.name, ":", len(node.nodes_received_transactions))
        # with self.graphs_lock:  # graphs_lock is a threading.Lock() object
        #     plt.figure(node.name)
        #     self.update_and_draw_graphs(node)
        #     plt.savefig(f'plot_node_{node.name}.png')
        #     plt.close()

    def add_transaction(self, node):
        start_time = datetime.now().strftime('%H:%M:%S.%f')[:-3]  # Gives you time up to milliseconds
        start_time += str(int(time.time() * 1e9))[-6:]  # Append the last six digits of the current nanosecond time

        with self.txid_lock:
            txid = str(self.txid_counter)
            self.txid_counter += 1
        tips = node.tips
        # print("Available tips", tips)
        # self.log_event(f"Available tips {tips}")

        parent_txids = [parent.txid for parent in tips if not parent.children]
        print(f"Available tips {parent_txids} of Node {node.name}")
        # self.log_event(f"Available tips {parent_txids} of Node {node.name}")

        if parent_txids:

            # Limit to only two parent transactions.
            parent_txids = parent_txids[:2]
            tx = node.create_and_sign_transaction_event(txid, parent_txids)
            tx.parent_transactions = [self.transactions[parent_id] for parent_id in parent_txids]
            self.transactions[txid] = tx

            for parent_id in parent_txids:
                self.graph.add_edge(parent_id, txid)
                parent = self.transactions[parent_id]

            print(f" {node.name} Added {tx} to DAG.")
            #self.log_event(f"{node.name}Added {tx} to DAG.")
            # print(f"{node.name} Started Broadcasting the Transcation to All of its Peers")
            #self.log_event(f"{node.name} Started Broadcasting the Transcation to All of its Peers")
            # node.broadcast_transaction_event(tx)
            # Update the weight of the transaction

            for peer in node.peers:
                if peer != node and tx not in peer.transaction_list:  # condition to prevent duplicate processing
                    delay = self.network.delay_matrix[(node,peer)]
                    node.direct_broadcast_transaction_event(tx)
                    print(f"{node.name} Started Broadcasting the Transcation {tx.txid} to {peer.name}")
                    self.log_event(f"{node.name} Started Broadcasting the Transcation {tx.txid} to {peer.name}")
                    print(f"Delay between {node.name} and {peer.name} is {delay}")
                    # self.log_event(f"Delay between {node.name} and {peer.name} is {delay}")
                    # peer.receive_transaction_event(delay)
                    # print(f" TRANSACTION {tx.txid} OF {node.name} HAS BEEB BROADCASTED TO WHOLE NETWORK")
                    # self.log_event(f" TRANSACTION {tx.txid} OF {node.name} HAS BEEB BROADCASTED TO WHOLE NETWORK")
            peer.receive_transaction_event(delay)
            print(f" TRANSACTION {tx.txid} OF {node.name} HAS BEEB BROADCASTED TO WHOLE NETWORK")
            self.log_event(f" TRANSACTION {tx.txid} OF {node.name} HAS BEEB BROADCASTED TO WHOLE NETWORK")
            end_time = datetime.now().strftime('%H:%M:%S.%f')[:-3]  # Gives you time up to milliseconds
            end_time += str(int(time.time() * 1e9))[-6:]  # Append the last six digits of the current nanosecond time

            for parent_tx in tx.parent_transactions:
                if parent_tx in self.tips:
                    self.tips.remove(parent_tx)

                # Then add the new transaction to the tips
            self.tips.append(tx)
            return tx
        else:
            print("No tips available for transaction.")
            return None

    def process_peer(self, peer, tx, delay):
        time.sleep(delay)
        peer.receive_transaction_event()
        print(f" Transaction of {peer.name} has been broadcasted to all of its network")

    def simulate(self, simulation_time, network):
        self.simulation_time = simulation_time
        transactions = []

        nodes_without_coordinator = [node for node in network.nodes if not isinstance(node, Coordinator)]
        # Shuffle the nodes list to randomize the order
        random.shuffle(nodes_without_coordinator)

        with ThreadPoolExecutor(max_workers=len(nodes_without_coordinator)) as executor:
            future_to_node = {executor.submit(self.run_node, node, simulation_time, transactions): node for node in
                              nodes_without_coordinator}
        return transactions

    def run_node(self, node, simulation_time, transactions):

        ########################################################### Thread logic 2  (Using this one)
        # num_transactions = math.ceil(random.expovariate(self.poisson_rate) * simulation_time)
        # print(f"Number of transactions {num_transactions}")
        # Get the start time of the simulation.
        # #start_time = datetime.now()
        # # Continue the simulation until the elapsed time is greater than the simulation time.
        # while (datetime.now() - start_time) < timedelta(seconds=simulation_time):
        #     for _ in range(num_transactions):
        #         tx = self.add_transaction(node)
        #         if tx is not None:
        #             with self.transaction_lock:  # assuming transaction_lock is a threading.Lock() or similar
        #                 transactions.append(tx)
        #
        num_transactions =2
        for _ in range(num_transactions):
            tx = self.add_transaction(node)
            if tx is not None:
                with self.transaction_lock:  # assuming transaction_lock is a threading.Lock() or similar
                    transactions.append(tx)
        all_transactions = self.transactions.keys()
        print("All transaction in the network", all_transactions)
        self.log_event(f"All transaction in the network: {all_transactions}")


    def update_weights_topological_order(self):
        # Get a topological order of the transactions
        order = list(nx.topological_sort(self.graph))

        # Print the order
        print("Topological order of transactions:", order)

        # Update the weights in this order
        for txid in order:
            tx = self.transactions[txid]
            tx.update_accumulative_weight()

    def print_weights(self):
        print("\nUpdated accumulative weights and branch weights:")
        for txid, tx in self.transactions.items():
            print(
                f"Transaction {txid}: Accumulative weight = {tx.accumulative_weight}, Branch weight = {tx.branch_weight}")
        print("\n")
    def update_and_draw_graphs(self, node):
        self.graphs[node.name].clear()
        color_map = ['blue'] * len(self.graphs[node.name].nodes)
        labels = {}

        with self.transaction_lock:  # assuming transaction_lock is a threading.Lock() object
            if node.name == "Coordinator":
                node.nodes_received_transactions.append(self.genesis_milestone())

            for transaction in node.nodes_received_transactions:
                self.graphs[node.name].add_node(transaction.txid)
                for parent_txid in transaction.parent_txids:
                    self.graphs[node.name].add_edge(parent_txid, transaction.txid)

                if transaction.txid == "0":
                    color_map.append('orange')
                    labels[transaction.txid] = 'Gen'
                else:
                    color_map.append('blue')
                    labels[transaction.txid] = transaction.txid

        plt.title(f'Node {node.name} DAG view')
        nx.draw(self.graphs[node.name], node_color=color_map, labels=labels, with_labels=True, node_size=1000,
                node_shape='s')

        with self.print_lock:
            print("Number of transactions for node", node.name, ":", len(node.nodes_received_transactions))

    def draw_dag_event(self, node=None):
        # Create a directed graph object
        G = nx.DiGraph()

        # Node colors and labels
        node_colors = {}
        node_labels = {}
        depth_map = {}
        max_depth = 0.5

        transactions_to_draw = self.transactions.values() if node is None else node.transaction_list  # Change Node to node

        for tx in self.transactions.values():
            # Add transaction ID as a label
            label = f"ID: {tx.txid}\nAW: {tx.accumulative_weight}"
            node_labels[tx.txid] = label

            # Determine the color of the node
            if tx.txid == "0":  # assuming you have an `is_genesis` property
                node_colors[tx.txid] = 'orange'  # Orange for genesis transaction
                depth_map[tx.txid] = 0
            elif tx in self.tips:
                node_colors[tx.txid] = 'grey'  # Grey for tips
                depth_map[tx.txid] = max((depth_map[parent_txid] + 1 for parent_txid in tx.parent_txids), default=0)
                max_depth = max(max_depth, depth_map[tx.txid])
            else:
                node_colors[tx.txid] = 'blue'  # Blue for other nodes
                depth_map[tx.txid] = max((depth_map[parent_txid] + 1 for parent_txid in tx.parent_txids), default=0)
                max_depth = max(max_depth, depth_map[tx.txid])

            # # Add edges to the graph
            # for parent_txid in tx.parent_txids:
            #     G.add_edge(parent_txid, tx.txid)  # parent -> child direction
        pos = {}
        for tx in self.transactions.values():
            depth = depth_map[tx.txid]
            same_depth_txs = [t for t, d in depth_map.items() if d == depth]
            level_size = len(same_depth_txs)
            index_in_level = same_depth_txs.index(tx.txid)
            vertical_position = (index_in_level + 1) / (level_size + 1)  # to make it range between 0 and 1
            pos[tx.txid] = (depth, vertical_position)

        # Convert node_colors to list maintaining the order of transactions
        node_colors_list = [node_colors[tx.txid] for tx in self.transactions.values()]

        edge_colors = []
        for tx in self.transactions.values():
            for parent_txid in tx.parent_txids:
                G.add_edge(tx.txid, parent_txid)
                # G.add_edge(parent_txid, tx.txid)
                edge_colors.append('grey' if parent_txid == '0' else 'blue')

        # Draw the graph
        plt.figure(figsize=(10, 5))
        #pos = nx.spring_layout(G)
        if node is None:
            plt.title('Whole DAG graph')
        else:
            plt.title(f'{node.name} graph')
        nx.draw(G, pos=pos, node_color=node_colors_list, node_size=1000, node_shape='s', edge_color=edge_colors)
        nx.draw_networkx_labels(G, pos, labels=node_labels, font_size=8)
        # nx.draw(G, pos, node_color=node_colors_list, labels=node_labels, with_labels=True)
        # plt.title('Transaction DAG')
        plt.show(block=True)



