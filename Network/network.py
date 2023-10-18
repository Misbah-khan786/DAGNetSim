
import matplotlib.pyplot as plt
from Network.node import Node, Coordinator
import random
import os
from graphviz import Digraph
from PIL import Image
import numpy as np
# class Network, representing the whole network
class Network:
    # Initialization function to set up a new Network
    def __init__(self, num_nodes,p, delay_range=(0.05, 0.25)): #, log_queue

        # # Generate the specified number of Nodes for the Network with different delay ranges
        # self.nodes = [Node(f"Node {i + 1}", self,  delay_range=(2 + 0.5 * i, 4 + 0.5 * i)) for i in range(num_nodes)] # log_queue,
        # # adding coordinator to the network
        # self.coordinator = Coordinator("Coordinator", self,  milestones_interval=150, is_coordinator=True) #log_queue,
        # self.nodes.append(self.coordinator)
        # self.configure_nodes_with_coordinator(self.coordinator.coordinator_public_key)
        # # Connect all the nodes in the Network to each other
        # self.create_peers()
        # # Generate delay matrix for the network
        # self.generate_delay_matrix()

        ################################## Uncoment to use PR_AN.py #########################################
        self.N = num_nodes
        print("Initializing nodes...")
        self.nodes = [Node(i,self) for i in range(self.N)]
        print("Nodes initialized.")

        print("Generating peers...")
        self.peers = self.generate_peers(p)
        print("Peers generated.")

        print("Assigning delays...")
        self.delay_matrix = self.assign_delays(delay_range)
        print("Delays assigned.")
        self.future_transactions = {}
        self.time = 0
    ##########################################################################
    def generate_peers(self, p):
        peers = {}
        for i in range(self.N):
            peers[i] = [j for j in range(self.N) if i != j and random.random() < p]
            print(f"Node {i} has peers: {peers[i]}")
        return peers

    def assign_delays(self, delay_range):
        delay_matrix = {}
        for i in range(len(self.nodes)):
            delay_matrix[i] = {}
            for j in self.peers[i]:
                delay_matrix[i][j] = random.uniform(*delay_range)
        return delay_matrix

    def add_transaction_to_future(self, transaction, node_id, delay):
        time_to_execute = self.time + delay
        print(f"Adding transaction {transaction} for node {node_id} to be delivered at time {time_to_execute}")
        if time_to_execute not in self.future_transactions:
            self.future_transactions[time_to_execute] = []
        self.future_transactions[time_to_execute].append((transaction, node_id))

    def simulate_second(self):
        # Generate transactions for each node
        print("Generating transactions for each node...")
        for node in self.nodes:
            node.generate_transaction(self)
        print("Transactions generated.")

        # Move time forward
        self.time += 1

        # Examine the transaction status for node at specific times
        check_times = [10, 50, 59]
        if self.time in check_times:
            for node in self.nodes:
                node_id_to_check = node.name
                future_txs = self.future_transactions_for_node(node_id_to_check)
                received_txs = node.transactions_received()

                print(f"At time {self.time}, node {node_id_to_check} has {future_txs} future transactions.")
                print(f"At time {self.time}, node {node_id_to_check} has received {received_txs} transactions.")

        # Deliver transactions
        print(f"Checking for transactions to deliver at time {self.time}")

        # Use a loop to continuously check for transactions to be delivered during this second
        while True:
            # Find transactions that are set to be delivered within the current second
            deliverable_transactions = [(t, v) for t, v in self.future_transactions.items() if t <= self.time]

            # Exit loop if there are no transactions to deliver
            if not deliverable_transactions:
                break

            # Process each deliverable transaction
            for delivery_time, transactions in deliverable_transactions:
                for transaction, node_id in transactions:
                    print(f"Delivering transaction {transaction} to node {node_id} at time {self.time}")
                    self.nodes[node_id].add_transaction(transaction)

                    # Start gossiping transaction to the peers
                    self.gossip_transaction(transaction, node_id)

                # Remove them from future_transactions once processed
                del self.future_transactions[delivery_time]

        # Update history of each node
        for node in self.nodes:
            node.update_history()

    def gossip_transaction(self, transaction, originating_node_id, visited_nodes=set(), delay=0,  subset_factor=0.7):
        # Avoid cycles
        if originating_node_id in visited_nodes:
            return
        visited_nodes.add(originating_node_id)

        peers = self.peers[originating_node_id]
        # Selecting a subset of peers
        subset_size = int(len(peers) * subset_factor)
        subset_of_peers = random.sample(peers, min(subset_size, len(peers)))

        for peer in subset_of_peers:
            if peer in visited_nodes:  # Avoid sending transaction back to the sender
                continue
            # Deliver transaction to the peer with a delay
            delay = self.delay_matrix[originating_node_id][peer]
            self.add_transaction_to_future(transaction, peer, delay)

            # Recursively gossip the transaction to the peers of the peer
            self.gossip_transaction(transaction, peer, visited_nodes.copy(), delay, subset_factor)

    def combined_generation_rate(self, node_id):
        peer_rates = [self.nodes[peer].tx_rate for peer in self.peers[node_id]]
        return sum(peer_rates)

    def print_combined_generation_rate(self):
        for node_id in range(self.N):  # Assuming self.N is the total number of nodes.
            rate = self.combined_generation_rate(node_id)
            print(f"Node {node_id} has a combined generation rate of: {rate}")
    def average_delay(self, node_id):
        delays = [self.delay_matrix[node_id][peer] for peer in self.peers[node_id]]
        return np.mean(delays), np.var(delays)

    def print_average_delays(self):
        for node_id in range(self.N):
            mean_delay, var_delay = self.average_delay(node_id)
            print(f"Node {node_id} has an average delay of: {mean_delay} with variance: {var_delay}")

    def simulate_without_delays(self, node_id, simulation_time):
        combined_rate = self.combined_generation_rate(node_id)
        times = np.cumsum(np.random.exponential(1 / combined_rate, int(simulation_time * combined_rate)))
        return times[times <= simulation_time]

    def simulate_with_delays(self, node_id, simulation_time):
        times_without_delays = self.simulate_without_delays(node_id, simulation_time)
        times_with_delays = []
        for time in times_without_delays:
            delay = np.random.choice([self.delay_matrix[node_id][peer] for peer in
                                      self.peers[node_id]])  # Randomly choosing a delay from peers
            times_with_delays.append(time + delay)
        return np.array(times_with_delays)

    def inter_arrival_times(sel,times):
        return np.diff(times)

    def plot_inter_arrival_histogram(self, node_id, simulation_time):
        times_with_delays = self.simulate_with_delays(node_id, simulation_time)
        # times_withot_delays = self.simulate_without_delays(node_id, simulation_time)
        inter_arrivals = self.inter_arrival_times(times_with_delays)
        inter_arrivals = [i for i in inter_arrivals if i >= 0]
        # Overlaying the exponential distribution
        lambda_value = 1 / np.mean(inter_arrivals)  # Rate parameter for exponential distribution
        x = np.linspace(min(inter_arrivals), max(inter_arrivals), 1000)
        y = lambda_value * np.exp(-lambda_value * x)
        plt.plot(x, y, 'r-', label="Expected Exponential Distribution")
        plt.hist(inter_arrivals, bins=50, density=True, alpha=0.7, label="Observed Distribution")
        plt.xlabel('Inter-arrival Time')
        plt.ylabel('Frequency')
        plt.legend()
        plt.show(block=True)
    def future_transactions_for_node(self, node_id):
        return sum([len([(t_id, n_id) for t_id, n_id in v if n_id == node_id])
                    for k, v in self.future_transactions.items()])

    def print_all_node_transactions(self):
        for node in self.nodes:
            node.print_transactions()


###############################################################################

    def get_last_receive_time(self, transaction_id):
        last_receive_time = None
        for node in self.nodes:
            if transaction_id in node.transaction_timestamps:
                if last_receive_time is None or node.transaction_timestamps[transaction_id] > last_receive_time:
                    last_receive_time = node.transaction_timestamps[transaction_id]
        return last_receive_time

    # Method to select a random Node from the Network
    def get_random_node(self):

        nodes_without_coordinator = [node for node in self.nodes if not isinstance(node, Coordinator)]
        node = random.choice(nodes_without_coordinator)
        # Return the selected Node
        return node
    # Method to connect each Node in the Network to a subset of the other Nodes
    def create_peers(self):
        # Calculate the number of peers to be connected with
        num_peers = max(1, int(len(self.nodes) * 0.2))
        for node in self.nodes:
            # Select a random subset of nodes, making sure the node doesn't select itself
            potential_peers = [peer for peer in self.nodes if peer != node and peer not in node.peers]
            node.peers = random.sample(potential_peers, min(num_peers, len(potential_peers)))

        # Add all nodes in the network as peers for the coordinator
        self.coordinator.peers = [node for node in self.nodes if
                                  node != self.coordinator]  # exclude coordinator from its own peer list

        # Make sure that the network is strongly connected
        for node in self.nodes:
            while len(node.peers) < 2:
                potential_peers = [peer for peer in self.nodes if peer != node and peer not in node.peers]
                if potential_peers:
                    peer = random.choice(potential_peers)
                    node.peers.append(peer)
                    if node not in peer.peers:  # To avoid Duplicates
                        peer.peers.append(node)
    def generate_delay_matrix(self):
        self.delay_matrix = {}
        # For each pair of Nodes in the Network...
        for i in range(len(self.nodes)):
            for j in range(i + 1, len(self.nodes)):
                current_node = self.nodes[i]
                other_node = self.nodes[j]

                # Generate a unique delay range for each pair of nodes
                min_delay = random.uniform(0.002, 0.01)  # 2ms to 10ms
                max_delay = random.uniform(min_delay,
                                           min_delay + 0.005)  # adding a little variance
                delay = random.uniform(min_delay, max_delay)

                # # If one of the nodes is the coordinator, adjust the delay to be within the delay range
                # if current_node == self.coordinator or other_node == self.coordinator:
                #     # min_delay_coordinator = min_delay
                #     min_delay_coordinator = 0
                #     # max_delay_coordinator = max(self.delay_matrix.values()) if self.delay_matrix else max_delay
                #     max_delay_coordinator = 0
                #     delay = random.uniform(min_delay_coordinator, max_delay_coordinator)

                self.delay_matrix[(current_node, other_node)] = delay
                self.delay_matrix[(other_node, current_node)] = delay


    def configure_nodes_with_coordinator(self, coordinator_public_key):
        for node in self.nodes:
            node.coordinator_public_key = coordinator_public_key
        print("All nodes have been configured with the coordinator's public key.")


    def draw_network(self):
        # Environment variable for Graphviz executable path, replace with your Graphviz bin path
        os.environ["PATH"] += os.pathsep + 'C:/Program Files/Graphviz/bin/'

        # Open an image file
        with Image.open("../Images/lptp.png") as img:
            # Resize the image
            img_resized = img.resize((100, 100))  # change the dimensions as needed
            # Save the resized image
            img_resized.save("../Images/lptp_resized.png")

        # Create a new directed graph
        dot = Digraph(engine="neato", format="pdf")
        dot.attr(overlap="false", size="25, 25", splines="polyline")

        # Define node and edge attributes
        dot.attr('node', fixedsize='true', width='0.3', height='0.3')  # Smaller node size
        dot.attr('edge', len='2.0')  # Longer edges

        for node in self.nodes:
            dot.node(node.name, image="../Images/lptp_resized.png", label=node.name, fontcolor="black", fontsize="8", shape="none")
            # if node.is_coordinator:
            #     # Use a different image, label or any other attributes for the coordinator
            #     dot.node(node.name, image="../Images/coordinator.png", label=node.name, fontcolor="red", fontsize="10",
            #              shape="none")
            # else:
            #     dot.node(node.name, image="../Images/lptp_resized.png", label=node.name, fontcolor="black", fontsize="8", shape="none")

        for i, node in enumerate(self.nodes, start=1):
            dot.node(node.name, image="../Images/lptp_resized.png", shape="none", label=node.name)
            print(f"Node {i}")

            for j, peer in enumerate(node.peers, start=1):
                delay = self.delay_matrix[(node, peer)]
                print(f"  Peer {j}: {peer.name} with delay {delay:.4f}")
                dot.edge(node.name, peer.name, label=f"{delay:.4f}", fontsize="6", arrowsize="0.5")

        dot.view(filename='graph_output')  # Renders and opens the graph

