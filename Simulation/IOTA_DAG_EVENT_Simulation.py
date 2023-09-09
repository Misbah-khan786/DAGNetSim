from DAG.IOTA_DAG_EVENT import IOTA_DAG
from Network.network import Network
import random
from networkinfoprinter import NetworkInfoPrinter
from Network.coordinator import Coordinator
import pickle
import asyncio
DIFFICULTY =1


if __name__ == '__main__':
    print("Starting simulation...")
    num_nodes = 4
    # poisson_rate = 0.3
    milestones_interval = 0.5
    sim_time = 5 # Add the simulation_time
    # Create the network
    network = Network(num_nodes)
    # Nodes without coordinator
    nodes_without_coordinator = [node for node in network.nodes if not isinstance(node, Coordinator)]
    # Desired total rate for the tangle
    lambda_total = 1
    rate_per_node = lambda_total / len(nodes_without_coordinator)
    poisson_rate = {node.name: rate_per_node for node in nodes_without_coordinator}
    IOTA_DAG = IOTA_DAG(poisson_rate, milestones_interval, network)
    IOTA_DAG.coordinator = network.coordinator
    IOTA_DAG.coordinator_genesis_milestone()
    # network.draw_network()
    transactions = IOTA_DAG.simulate(sim_time, network)

    for node in network.nodes:
        trans = node.nodes_received_transactions
        tans = node.transaction_list
        print(trans, tans)
        IOTA_DAG.draw(node)
        # IOTA_DAG.print_weights(node)
    print(transactions)
    print("Simulation complete.")

