import random
import os
import rsa
import threading
import networkx as nx
import matplotlib.pyplot as plt
from datetime import datetime
from Transaction.transaction import Transaction
from RandomWalker.randomwalker import RandomWalker
from Network.node import Node, Coordinator
import asyncio
import pickle
# from aiomultiprocess import Pool
from multiprocessing import Pool
import logging
import uuid
import time
from contextlib import contextmanager


# Top-level
def run_simulation(sim_time, node, network, start_time, poisson_rate, milestones_interval):
    # Create a new loop for this process
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Instantiate IOTA_DAG with the required arguments
    iota_dag_instance = IOTA_DAG(milestones_interval=milestones_interval, network=network, poisson_rate=poisson_rate)

    result = loop.run_until_complete(iota_dag_instance.simulate_node(sim_time, node, network, start_time))

    loop.close()
    return result
@contextmanager
def time_block(label, logger=None, id=None):
    start_time = time.perf_counter()
    yield
    end_time = time.perf_counter()
    duration = end_time - start_time
    message = f"{label} took {duration:0.4f} seconds."
    if id:
        logger.info(f"for ID {id} {message} ")
    elif logger:
        logger.info(message)
    else:
        print(message)
class IOTA_DAG:
    def __init__(self, poisson_rate, milestones_interval, network ):
        self.creation_time = datetime.now()
        self.network = network
        self.poisson_rate = poisson_rate
        self.transactions = {}
        self.tips = []
        self.graph = nx.DiGraph()
        self.node_graphs = {node.name: nx.DiGraph() for node in network.nodes}
        self.batch_num = 0  # initialize batch number
        self.batches = []  # list of batches
        self.num_batches = 0  # store the number of batches
        self.current_batch = 0  # store the current batch number
        self.coordinator = None
        self.milestones_interval = milestones_interval
        self.last_milestone_time = datetime.now()
        # self.milestone_thread = threading.Thread(target=self.invoke_generate_milestone_after_delay)
        # self.milestone_thread.start()
        self.print_lock = threading.Lock()  # assuming print_lock is a threading.Lock() object
        # self.loggers = {node.name: logging.getLogger(node.name) for node in network.nodes}
        # self.loggers = {node.name: logging.getLogger(node.name) for node in network.nodes}

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
        self.coordinator.transaction_list.append(genesis_milestone)
        print(self.transactions)

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
        # self.loggers[node.name].info(
        #     f"{datetime.now().strftime('%H:%M:%S.%f')} -  Total time taken by Coordinator to broadcast to all its peers: {total_time.seconds} seconds, {total_time.microseconds} microseconds")

        # # Update and draw graphs for each node after broadcasting the genesis transaction
        # for node in self.network.nodes:
        #     self.update_and_draw_graphs(node)

    def process_node(self, node, delay):
        time.sleep(delay)
        with self.print_lock:
            print(f"Transaction received by {node.name} from {self.coordinator.name} with delay: {delay} seconds")
            # self.loggers[node.name].info(
            #     f"{datetime.now().strftime('%H:%M:%S.%f')} - Transaction received by {node.name} from {self.coordinator.name} with delay: {delay} seconds ")
            print("Number of transactions for node", node.name, ":", len(node.nodes_received_transactions))
            # # self.loggers[node.name].info(
            #     f"{datetime.now().strftime('%H:%M:%S.%f')} - Number of transactions for node {node.name} : {len(node.nodes_received_transactions)} ")

    def get_transaction_by_id(self, node, txid):
        """Retrieve transaction by ID from a node's context."""
        for tx in node.transaction_list + node.nodes_received_transactions:
            if tx.txid == txid:
                return tx
        return None
    async def add_transactions(self, node, network):
        trans = node.nodes_received_transactions
        tans = node.transaction_list
        trans_ids = [tx.txid for tx in trans]
        tans_ids = [tx.txid for tx in tans]
        total = trans+tans
        print(f" Recieved {trans_ids},Total {len(total)}, Genrated {tans_ids},  ")
        start_time = datetime.now()
        with time_block("Initial Setup for Random walk tip selction"):# self.loggers[node.name
            print(f"{node.name} Started Generating the Transaction")
            # self.loggers[node.name].info(
            #     f"{datetime.now().strftime('%H:%M:%S.%f')} -  {node.name} Started Generating the Transaction")
            new_transactions = []
            nodes_tips = list(node.tips)  # Create a copy of the tips
            nodes_tip_ids = [tx.txid for tx in nodes_tips]
            print(f"Tips of {node.name} are {nodes_tip_ids}")
            if not nodes_tips:
                return
            # if len(nodes_tips) >= 2:
            #     tips = random.sample(nodes_tips, 2)
            # else:
            #     tips = nodes_tips
            # Instantiate the random walker
            random_walker = RandomWalker(W=3, N=2, alpha_low=0, alpha_high=0.0, node=node.name)
            new_transactions = []
            random_walk_tips = await random_walker.walk_event(self, nodes_tips)
            tips = random_walk_tips
            tip_ids = [tx.txid for tx in tips]
            print(f" Tips Returned by RANDOMWALK {tip_ids}")
            if not isinstance(tips, list):
                tips = [tips]  # Convert to list if not a list

        # with time_block("Parent Transaction Validation", self.loggers[node.name]):
        #     valid = True
        #     for parent in tips:
        #         if parent.txid == "0":  # Skip the genesis transaction
        #             continue
        #         print("Started checking conflict")
        #         # self.loggers[node.name].info(
        #         #     f"{datetime.now().strftime('%H:%M:%S.%f')} - Start checking the conflict ")
        #         if not parent.validate_transaction(DIFFICULTY=1):
        #             print(
        #                 f"Invalid signature detected in parent transaction: {parent.txid}. Skipping this transaction.")
        #             # self.loggers[node.name].info(
        #             #     f"{datetime.now().strftime('%H:%M:%S.%f')} - Invalid signature detected in parent transaction: {parent.txid}. Skipping this transaction. ")
        #             valid = False
        #             break
        #         if valid:
        #             print("Parent transaction(s) have valid signatures. No double spending detected.")
        #         #     self.loggers[node.name].info(
        #         #         f"{datetime.now().strftime('%H:%M:%S.%f')} - Parent transaction(s) have valid signatures. No double spending detected.  ")
        #         # self.loggers[node.name].info(
        #         #     f"{datetime.now().strftime('%H:%M:%S.%f')} - End checking the conflict ")

        with time_block("Transaction Creation and appending"): #  self.loggers[node.name]
            # txid = str(len(self.transactions))
            # txid = str(uuid.uuid4())
            txid = node.generate_id()
            parent_txids = list(set(parent.txid for parent in tips))
            tx = node.create_and_sign_transaction(txid, parent_txids, DIFFICULTY=1)
            tx.parent_transactions = [self.get_transaction_by_id(node, parent_id) for parent_id in parent_txids]
            # tx.parent_transactions = [self.transactions[parent_id] for parent_id in parent_txids]
            # self.transactions[txid] = tx
            # new_transactions.append(tx)

        with time_block("Updating Tips and Graph"): #self.loggers[node.name]
            # tx.batch_num = self.batch_num
            for parent in tx.parent_transactions:
                parent.children.append(tx)
                # if parent in node.tips:
                #     node.tips.remove(parent)
                    # print(f"{parent} is no loger tip for {node.name} IN CREATING")
                    # self.logger.info(
                    #     f"{datetime.now().strftime('%H:%M:%S.%f')} - {parent} is no loger tip for {node.name}")
                # # if len(parent.children) == 1:
                #     node.tips.append(parent)
            node_graph = self.node_graphs[node.name]
            for parent in parent_txids:
                node_graph.add_edge(parent, txid)
                # self.graph.add_edge(parent, txid)
                self.draw(node)



            # self.tips = [tx for tx in self.tips + list(self.transactions.values()) if not tx.children]
            # self.batches.append(new_transactions)
            # self.batch_num += 1
        with time_block("Updating Weights"): # self.loggers[node.name], id=tx.txid
            self.update_weights_topological_order(node)
            # Update branch weights
            # with self.weight_lock:
            #     for tx in new_transactions:
            #         tx.update_branch_weight()

        overall_end_time = datetime.now()  # Capture the end time to generate a transaction
        total_duration = overall_end_time - start_time
        print(f"Total time taken by {node.name} to generate a transaction: {total_duration}")
        # self.loggers[node.name].info(f"Total time taken by {node.name} to generate a transaction: {total_duration}")

        # Broadcast the transaction to all peers
        print(
            f"{datetime.now().strftime('%H:%M:%S.%f')} - {node.name} started broadcasting the TRANSACT ID: {tx.txid}")
        # self.loggers[node.name].info(
        #     f"{datetime.now().strftime('%H:%M:%S.%f')} - {node.name} started broadcasting the TRANSACT ID: {tx.txid} ")
        await node.broadcast_transaction(tx, self)
        #node.broadcast_transaction(tx, self)
        print(f"{node.name}: Added {tx} to DAG.")
        # self.loggers[node.name].info(
        #     f"{datetime.now().strftime('%H:%M:%S.%f')} - {node.name}: Added {tx} to DAG. ")

        # self.coordinator.cooridnator_view(tx)

    async def simulate_node(self, sim_time, node, network, start_time):
        current_time = time.time()
        transactions = []
        node_poisson_rate = self.poisson_rate[node.name]  # Get the Poisson rate for this node

        while current_time - start_time < sim_time * 60:  # Convert minutes to seconds
            tx = await self.add_transactions(node, network)

            # Add new transaction to list
            if tx and tx.parent_txids:
                transactions.append(tx)

            # Update branch weights for all transactions
            transaction_values = list(self.transactions.values())  # Create a list of values

            # Get delay for the next transaction when all node have different poisson rate
            delay = random.expovariate(node_poisson_rate)

            # Use async sleep now
            await asyncio.sleep(delay)

            # Update current time
            current_time = time.time()

        return transactions

    def simulate(self, sim_time, network):
        start_time = time.time()  # Get the current time

        nodes_without_coordinator = [node for node in network.nodes if not isinstance(node, Coordinator)]
        # Shuffle the nodes list to randomize the order
        random.shuffle(nodes_without_coordinator)
        #  multiprocessing instead of threading
        with Pool() as pool:
            # multiple arguments
            results = pool.starmap(run_simulation,
                       [(sim_time, node, network, start_time, self.poisson_rate, self.milestones_interval) for node
                        in nodes_without_coordinator])

        transactions = [tx for sublist in results for tx in sublist]

        # for node in network.nodes:
        #     self.draw(node)
        # self.print_weights()
        input("Press any key to exit...")

        # Transactions per second in Tangle
        transactions_per_second = len(transactions) / sim_time
        print(f"Transactions per second: {transactions_per_second}")

        return transactions


    def invoke_generate_milestone_after_delay(self):
        while True:
            current_time =datetime.now()
            if (current_time - self.last_milestone_time).total_seconds() >= self.milestones_interval:
                self.coordinator.generate_milestone(current_time)
                self.last_milestone_time = datetime.now()

            # time.sleep(self.milestones_interval)  # Adjustable time delay as needed
            # self.coordinator.generate_milestone()

    def update_weights_topological_order(self,node):
        node_graph = self.node_graphs[node.name]
        # Get a topological order of the transactions
        order = list(nx.topological_sort(node_graph))
        # order = list(nx.topological_sort(self.graph))

        # Print the order
        # print("Topological order of transactions:", order)
        #
        # print(f" SELF GENRATED TRANSACTIONS {len(node.transaction_list)}")
        # print(f" RECEIVED  TRANSACTIONS {len(node.nodes_received_transactions)}")

        # transaction_list and nodes_received_transactions are attributes of 'node'.
        all_transactions = node.transaction_list + node.nodes_received_transactions
        transaction_ids = [tx.txid for tx in all_transactions]

        # print(f"THE LENGHT OF ALL TRANSACTIONS IN WEIGHT METHOD IS {len(all_transactions)}")
        # print("Start of weight-------", transaction_ids)

        # Update the weights in this order
        for txid in order:
            # print("Starting the weight update")
            tx = next((trans for trans in all_transactions if trans.txid == txid), None)
            # print(f"weight for tx")
            if tx:
                updated_weight =tx.update_accumulative_weight()
                # print("Updated weight for tx", txid , updated_weight)

        #
        # # Update the weights in this order
        # for txid in order:
        #     tx = self.transactions[txid]
        #     tx.update_accumulative_weight()

    def print_weights(self, node):
        print("\nUpdated accumulative weights and branch weights:")
        all_transactions = node.transaction_list + node.nodes_received_transactions

        for tx in all_transactions:
            print(
                f"Transaction {tx.txid}: Accumulative weight = {tx.accumulative_weight}, Branch weight = {tx.branch_weight}")
        print("\n")
        # for txid, tx in self.transactions.items():
        #     print(
        #         f"Transaction {txid}: Accumulative weight = {tx.accumulative_weight}, Branch weight = {tx.branch_weight}")
        # print("\n")


    ###############################################
    def draw(self, node):

        # save_path = r'C:\Users\z5307913\Figures'

        if not os.path.exists('Figures'):
            os.makedirs('Figures')

        # Now, any file operations you do with the 'Figures' path will use this directory.

        # if not os.path.exists(save_path):
        #     os.makedirs(save_path)

        # print(node.nodes_received_transactions)
        # print(node.transaction_list)

        all_transactions = node.nodes_received_transactions + node.transaction_list
        # print(f"Total transactions to be drawn: {len(all_transactions)}")
        # Create a directed graph object
        G = nx.DiGraph()

        # Set node colors and labels
        node_colors = {}
        node_labels = {}  # Store node labels
        depth_map = {}
        max_depth = 0

        for tx in all_transactions:

            # Add transaction ID as a label
            label = f"{tx.txid}\nAW: {tx.accumulative_weight}"
            node_labels[tx.txid] = label

            # Determine the color of the node
            if tx.txid == '0':  # assuming you have an `is_genesis` property
                node_colors[tx.txid] = 'blue'  # Orange for genesis transaction
                depth_map[tx.txid] = 0

            # elif tx in node.tips:
            #     node_colors[tx.txid] = 'grey'  # grey for tips
            #     depth_map[tx.txid] = max((depth_map[parent_txid] + 1 for parent_txid in tx.parent_txids),default= 0)
            #     max_depth = max(max_depth, depth_map[tx.txid])
            # elif tx.is_confirmed:
            #     node_colors[tx.txid] = 'green'  # green for confirmed transactions
            #     depth_map[tx.txid] = max((depth_map[parent_txid] + 1 for parent_txid in tx.parent_txids), default=0)
            #     max_depth = max(max_depth, depth_map[tx.txid])
            else:
                node_colors[tx.txid] = 'blue'  # blue for other nodes
                depth_map[tx.txid] = max((depth_map[parent_txid] + 1 for parent_txid in tx.parent_txids),default= 0)
                max_depth = max(max_depth, depth_map[tx.txid])

        # Get node positions
        pos = {}
        for tx in all_transactions:
            depth = depth_map[tx.txid]
            same_depth_txs = [t for t, d in depth_map.items() if d == depth]
            level_size = len(same_depth_txs)
            index_in_level = same_depth_txs.index(tx.txid)
            vertical_position = (index_in_level + 1) / (level_size + 1)  # to make it range between 0 and 1
            # vertical_position = (index_in_level + 1) / (level_size + 1) * level_size  # Scale positions by level_size
            pos[tx.txid] = (depth, vertical_position)

        # Convert node_colors to list maintaining the order of transactions
        node_colors_list = [node_colors[tx.txid] for tx in all_transactions]

        # Add edges to the graph and set their colors
        edge_colors = []
        for tx in all_transactions:
            for parent_txid in tx.parent_txids:
                # print(f"Adding edge from {tx.txid} to {parent_txid}")
                G.add_edge(tx.txid, parent_txid)
                # G.add_edge(parent_txid, tx.txid)
                edge_colors.append('grey' if parent_txid == '0' else 'blue')

        # Draw the graph
        plt.figure(figsize=(10, 5))
        nx.draw(G, pos=pos, node_color=node_colors_list, node_size=1300, node_shape='s', edge_color=edge_colors)
        nx.draw_networkx_labels(G, pos, labels=node_labels, font_size=8)
        plt.title(f'{node.name}')
        # plt.ylim(0, max(level_size for level_size in depth_map.values())) # Adjust ylim based on maximum level_size
        plt.ylim(0, 1)  # Make sure all nodes fit in the figure
        plt.xlim(-1, max_depth + 2)
        plt.pause(1)
        # plt.savefig(os.path.join(save_path, f'my_plot_{node.name}.png'))
        plt.savefig(os.path.join('Figures', f'{node.name}.png'))
        plt.show()
        plt.close()




