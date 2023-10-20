from DAG.IOTA_DAG_EVENT_Thread import IOTA_DAG
from Network.network_Thread import Network
import random
from networkinfoprinter import NetworkInfoPrinter
from Network.coordinator import Coordinator

DIFFICULTY =1

if __name__ == '__main__':
    print("Starting simulation...")
    num_nodes = 4
    # poisson_rate = 0.3
    milestones_interval = 7
    sim_time = 0.15 # Add the simulation_time
    # Create the network
    network = Network(num_nodes)
    # Nodes without coordinator
    nodes_without_coordinator = [node for node in network.nodes if not isinstance(node, Coordinator)]
    # Desired total rate for the tangle
    lambda_total = 100
    # Generate random rates for each node
    random_rates = [random.uniform(0.000000001, 0.000000001) for node in nodes_without_coordinator]
    # Calculate the sum of these random rates
    sum_random_rates = sum(random_rates)
    # Normalize the random rates to sum up to lambda_total
    normalized_rates = [lambda_total * (rate / sum_random_rates) for rate in random_rates]
    # Assign these normalized rates to each node
    poisson_rate = {node.name: rate for node, rate in zip(nodes_without_coordinator, normalized_rates)}
    IOTA_DAG = IOTA_DAG(poisson_rate, milestones_interval, network)
    # network.dag.add_coordinator(coordinator)  # line to set the coordinator object
    IOTA_DAG.coordinator = network.coordinator
    IOTA_DAG.coordinator_genesis_milestone()
    network.draw_network()
    transactions =IOTA_DAG.simulate(sim_time, network=network)
    IOTA_DAG.draw()
    print(transactions)
    print("Simulation complete.")
