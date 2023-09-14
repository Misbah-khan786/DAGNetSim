from DAG.IOTA_DAG_EVENT import IOTA_DAG
from Network.network import Network
import random
from networkinfoprinter import NetworkInfoPrinter
from Network.coordinator import Coordinator
# from Network.node import logger_listener_process
import pickle
import asyncio
DIFFICULTY =1
import sys
sys.setrecursionlimit(10000)

from multiprocessing import Process, Queue
from multiprocessing import Manager

if __name__ == '__main__':
    # manager = Manager()
    # log_queue = manager.Queue()
    # listener_process = Process(target=logger_listener_process, args=(log_queue,))
    # print("Starting listener process...")
    # listener_process.start()
    # print("Listener process started.")

    print("Starting simulation...")
    num_nodes =5
    # poisson_rate = 0.3
    milestones_interval = 0.5
    sim_time = 1 # Add the simulation_time
    # Create the network
    # network = Network(num_nodes, log_queue)
    print("Node/Network setup starting ")
    network = Network(num_nodes)
    print("Node/Network setup done")
    # Nodes without coordinator
    nodes_without_coordinator = [node for node in network.nodes if not isinstance(node, Coordinator)]
    print("Created the list of Nodes without coordinator")
    # Desired total rate for the tangle
    lambda_total = 100
    rate_per_node = lambda_total / len(nodes_without_coordinator)
    print("Rate per node will be", rate_per_node)
    poisson_rate = {node.name: rate_per_node for node in nodes_without_coordinator}
    IOTA_DAG = IOTA_DAG(poisson_rate, milestones_interval, network)
    IOTA_DAG.coordinator = network.coordinator
    IOTA_DAG.coordinator_genesis_milestone()
    # network.draw_network()
    transactions = IOTA_DAG.simulate(sim_time, network)
    # log_queue.put(None)
    # listener_process.join()
    print("Listener process joined.")

    # for node in network.nodes:
    #     trans = node.nodes_received_transactions
    #     tans = node.transaction_list
        # print(trans, tans)
        # IOTA_DAG.draw(node)node
        # IOTA_DAG.print_weights(node)
    print(transactions)
    print("Simulation complete.")

