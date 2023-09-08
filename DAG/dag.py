import random
import math
import time
import networkx as nx
import matplotlib.pyplot as plt
import threading
from datetime import datetime
plt.ion()

from Transaction.transaction import Transaction
from RandomWalker.randomwalker import RandomWalker
# from Network.node import Node

class DAG:
    def __init__(self, poisson_rate, milestones_interval ):
        self.poisson_rate = poisson_rate
        self.transactions = {}
        self.genesis_transaction = Transaction("0", [], None)
        self.transactions[self.genesis_transaction.txid] = self.genesis_transaction
        self.tips = [self.genesis_transaction]
        self.graph = nx.DiGraph()
        self.batch_num = 0  # initialize batch number
        self.batches = []  # list of batches
        self.num_batches = 0  # store the number of batches
        self.current_batch = 0  # store the current batch number
        self.coordinator = None
        self.milestones_interval = milestones_interval
        self.creation_time = datetime.now()

    def add_coordinator(self, coordinator):
        self.coordinator = coordinator

    def add_transactions(self, num_transactions,network):

        new_transactions = []
        last_timestamp = None
        #prev_tips = [tx for tx in self.tips + list(self.transactions.values()) if not tx.children]
        prev_tips = list(self.tips)  # Create a copy of the tips
        #print("Tips", prev_tips)
        #print("Previous Tips", prev_tips)
        if not prev_tips:
            return
        # Instantiate the random walker
        random_walker = RandomWalker(W=3, N=2, alpha_low=0.01, alpha_high=1.0)
        new_transactions = []
        for i in range(num_transactions):
            if len(set(prev_tips)) < 2:
                batch_tips = [prev_tips[0], prev_tips[0]]
            else:
                # model_tip, model_path =random_walker.select_model_tip(self,prev_tips,new_transactions)
                # print("MODEL TIP:", model_tip,"\nMODEL PATHS:", model_path)
                # if model_tip is None:
                #     continue  # Skip this iteration if no model tip is available
                # # batch_tips = random_walker.walk(self, prev_tips, new_transactions)
                # # print("BATCH TIP", batch_tips)
                batch_tips = random_walker.walk(self, prev_tips, new_transactions)
                # print("Reached TIP:", batch_tips,"\n Reached Tip PATHS:", paths)
                # Calculate overlap for each path returned from `walk`
                # if isinstance(paths, Transaction):
                #     paths = [paths]  # Make it a list so you can iterate over it
                # for path in paths:
                #     overlap = random_walker.consistency_check(model_path, path)
                #     print(f"Overlap between model path and path from walk: {overlap}%")

            tips = batch_tips
            if not isinstance(tips, list):
                tips = [tips]  # Convert to list if not a list
         # Validate signatures of parent transactions
         #    if self.batch_num > 0:
         #        valid = True
         #        for parent in tips:
         #            if not parent.validate_transaction():
         #                print(f"Invalid signature detected in parent transaction: {parent.txid}")
         #                valid = False
         #                break
         #        if not valid:
         #            continue
         #        print("Parent transaction(s) have valid signatures & No Duble spending.")
            txid = str(len(self.transactions))
            parent_txids = list(set(parent.txid for parent in tips))
            node = network.get_random_node()
            tx = node.create_and_sign_transaction(txid, parent_txids)
            # Update parent_transactions
            tx.parent_transactions = tips
            self.transactions[txid] = tx
            new_transactions.append(tx)
            tx.batch_num = self.batch_num

            for parent in set(tips):  # Use a set to remove duplicates
                parent.children.append(tx)

                if len(parent.children) == 1:
                    self.tips.append(parent)

            # if last_timestamp is not None:
            #     last_timestamp_dt = datetime.fromisoformat(last_timestamp)
            #     tx_timestamp_dt = datetime.fromisoformat(tx.timestamp)
            #     time_difference = tx_timestamp_dt - last_timestamp_dt
            #     print(f"Time difference with previous transaction: {time_difference}")
            #
            # last_timestamp = tx.timestamp

            for parent in parent_txids:
                self.graph.add_edge(parent, txid)
            print(f"Batch {self.batch_num}: Added {tx} to DAG.")
            #self.draw()

        # Pass the new_transactions list to the Coordinator object
        self.coordinator.cooridnator_view(new_transactions)

        #Generate milestone
        if  self.batch_num % self.milestones_interval == 0:
            milestone_thread = threading.Thread(target=self.invoke_generate_milestone_after_delay)
            milestone_thread.start()

        # update tips at the end of the batch
        self.tips = [tx for tx in self.tips + list(self.transactions.values()) if not tx.children]
        self.batches.append(new_transactions)
        self.batch_num += 1

        # Update accumulative weights
        self.update_weights_topological_order()
        # Update branch weights
        for tx in new_transactions:
            tx.update_branch_weight()

    def invoke_generate_milestone_after_delay(self):
        while True:
            time.sleep(self.milestones_interval)  # Adjustable time delay as needed
            self.coordinator.generate_milestone()

    def update_weights_topological_order(self):
        # Get a topological order of the transactions
        order = list(nx.topological_sort(self.graph))

        # Print the order
        print("Topological order of transactions:", order)

        # Update the weights in this order
        for txid in order:
            tx = self.transactions[txid]
            tx.update_accumulative_weight()

    def simulate(self, num_batches,network):
        self.num_batches = num_batches
        transactions = []
        #self.nodes = nodes
        for i in range(num_batches):
            self.current_batch = i  # Store the current batch number
            print("Current batch", self.current_batch)
            num_transactions = math.ceil(random.expovariate(self.poisson_rate))
            self.add_transactions(num_transactions,network)

            # Update accumulative weight for all transactions after each batch
            #self.update_weights_topological_order()

            # Add new transactions to list
            for txid, tx in self.transactions.items():
                if tx.parent_txids:
                    transactions.append(tx)
                #print(f"Batch {self.current_batch}: Added {tx} to DAG.")

            print(f"Batch {i}: Added {num_transactions} transactions to DAG.")

            #Update branch weights for all transactions
            for tx in self.transactions.values():
                tx.update_branch_weight()

            # Print updated accumulative weights
            self.print_weights()
            self.draw()

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

        # Handle the genesis transaction separately
        genesis_tx = self.transactions['1']
        #print("Gensis transaction",genesis_tx)
        node_labels[genesis_tx.txid] = f"ID: {genesis_tx.txid}\nAW: {genesis_tx.accumulative_weight}"
        node_colors[genesis_tx.txid] = 'orange'  # Orange for genesis transaction
        depth_map[genesis_tx.txid] = 1

        # # Handle the transaction with txid == '1' separately
        if '1' in self.transactions and self.current_batch == 0:
            tx_1 = self.transactions['0']
            node_labels[tx_1.txid] = f"ID: {tx_1.txid}\nAW: {tx_1.accumulative_weight}"
            node_colors[tx_1.txid] = 'grey'  # Orange for transaction with txid == '1'
            depth_map[tx_1.txid] = 0
        elif '1' in self.transactions and self.current_batch != 0 and '1' not in self.tips:
            tx_1 = self.transactions['0']
            node_labels[tx_1.txid] = f"ID: {tx_1.txid}\nAW: {tx_1.accumulative_weight}"
            node_colors[tx_1.txid] = 'blue'  # Orange for transaction with txid == '1'
            depth_map[tx_1.txid] = 0
        elif '1' in self.transactions and self.current_batch != 0 and '1' in self.tips:
            tx_1 = self.transactions['0']
            node_labels[tx_1.txid] = f"ID: {tx_1.txid}\nAW: {tx_1.accumulative_weight}"
            node_colors[tx_1.txid] = 'grey'  # Orange for transaction with txid == '1'
            depth_map[tx_1.txid] = 0
        else:
            tx_1 = self.transactions['0']
            node_labels[tx_1.txid] = f"ID: {tx_1.txid}\nAW: {tx_1.accumulative_weight}"
            node_colors[tx_1.txid] = 'blue'  # Orange for transaction with txid == '1'
            depth_map[tx_1.txid] = 0

        for tx in self.transactions.values():

            # Skip the genesis transaction
            if tx.txid == '0' or tx.txid == '1':
                continue
            # Add accumulative weight, branch weight, and transaction ID as a label
            label = f"ID: {tx.txid}\nAW: {tx.accumulative_weight}"
            node_labels[tx.txid] = label

            # Determine the color of the node

            if tx in self.tips:
                node_colors[tx.txid] = 'grey'  # grey for tips
                depth_map[tx.txid] = max((depth_map[parent_txid] + 1 for parent_txid in tx.parent_txids),default= 0)
                max_depth = max(max_depth, depth_map[tx.txid])
            elif tx.is_confirmed:
                node_colors[tx.txid] = 'green'  # green for confirmed transactions
                depth_map[tx.txid] = max((depth_map[parent_txid] + 1 for parent_txid in tx.parent_txids), default=0)
                max_depth = max(max_depth, depth_map[tx.txid])
            else:
                node_colors[tx.txid] = 'blue'  # blue for other nodes
                depth_map[tx.txid] = max((depth_map[parent_txid] + 1 for parent_txid in tx.parent_txids),default= 0)
                max_depth = max(max_depth, depth_map[tx.txid])

            # Print node colors and IDs
        # for txid, color in node_colors.items():
        #     print(f"Node ID: {txid}, Color: {color}")

        # Get node positions
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
        plt.ylim(0, 1)  # Make sure all nodes fit in the figure
        plt.xlim(-1, max_depth + 2)
        #plt.savefig(f'Figures/my_plot_{self.current_batch}.png')
        plt.pause(1)
        plt.show(block=True)

