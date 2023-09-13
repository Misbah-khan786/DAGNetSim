
from Network.node import Node, Coordinator
from datetime import datetime
import rsa
import random
import time
import os
from graphviz import Digraph
import simpy
from PIL import Image
from DAG.dag import DAG

# class Network, representing the whole network
class Network:
    # Initialization function to set up a new Network
    def __init__(self, num_nodes): #, log_queue

        # Generate the specified number of Nodes for the Network with different delay ranges
        self.nodes = [Node(f"Node {i + 1}", self,  delay_range=(2 + 0.5 * i, 4 + 0.5 * i)) for i in range(num_nodes)] # log_queue,
        # adding coordinator to the network
        self.coordinator = Coordinator("Coordinator", self,  milestones_interval=150, is_coordinator=True) #log_queue,
        self.nodes.append(self.coordinator)
        self.configure_nodes_with_coordinator(self.coordinator.coordinator_public_key)
        # Connect all the nodes in the Network to each other
        self.create_peers()
        # Generate delay matrix for the network
        self.generate_delay_matrix()

    # def transaction_received_by_all(self, transaction_id):
    #     nodes_received_transaction = []
    #     for node in self.nodes:
    #         nodes_received_transaction.extend([(node.name, trans_id) for trans_id in node.nodes_received_transactions if
    #                                            trans_id == transaction_id])
    #
    #     for node in self.nodes:
    #         if node.name not in nodes_received_transaction and transaction_id in node.transaction_list:
    #             return False
    #     return True

    def get_last_receive_time(self, transaction_id):
        last_receive_time = None
        for node in self.nodes:
            if transaction_id in node.transaction_timestamps:
                if last_receive_time is None or node.transaction_timestamps[transaction_id] > last_receive_time:
                    last_receive_time = node.transaction_timestamps[transaction_id]
        return last_receive_time

    # Method to select a random Node from the Network
    def get_random_node(self):
        # Select a Node at random
        # node = random.choice(self.nodes)
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

