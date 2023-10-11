from DAG.IOTA_DAG_EVENT import IOTA_DAG
from Network.network import Network
from Network.coordinator import Coordinator
DIFFICULTY =1
import sys
sys.setrecursionlimit(10000)

if __name__ == '__main__':
    print("Starting simulation...")
    num_nodes =4
    # poisson_rate = 0.3
    milestones_interval = 0.5
    sim_time = 30 # Add the simulation_time
    # Create the network
    print("Node/Network setup starting ")
    network = Network(num_nodes, 0.05)
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
    transactions = IOTA_DAG.simulate(sim_time, network)
    print(transactions)
    print("Simulation complete.")

