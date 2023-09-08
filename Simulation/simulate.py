from DAG.dag import DAG
from Network.network import Network
from networkinfoprinter import NetworkInfoPrinter
from Network.coordinator import Coordinator

if __name__ == '__main__':
    print("Starting simulation...")

    # Create the network
    network = Network(5)
    #network.draw_network()
    # info_printer = NetworkInfoPrinter(network)
    # info_printer.print_network_info()

    # Create an instance of the Coordinator
    # coordinator = Coordinator("Coordinator", network, milestones_interval=10)
    # coordinator.peers = network.nodes  # Add all nodes in the network to the Coordinator's list of peers
    # Add the coordinator to the network's nodes
    # network.nodes.append(coordinator)
    # Now you can check if a node is a coordinator:
    # for node in network.nodes:
    #     if node.is_coordinator:
    #         print(f"{node.name} is a coordinator!")
    #     else:
    #         print(f"{node.name} is not a coordinator.")

    # # Create an instance of the Coordinator
    # coordinator = Coordinator("Coordinator", network, milestones_interval=10,is_coordinator=True)
    # coordinator.peers = network.nodes  # Add all nodes in the network to the Coordinator's list of peers

    # Configure all nodes in the network with the coordinator's public key
    # network.configure_nodes_with_coordinator(coordinator.coordinator_public_key)
    # print("Coordinator public key", network.coordinator.public_key)
    # network.configure_nodes_with_coordinator(network.coordinator.public_key)

    network.dag = DAG(0.5, milestones_interval=10)
    # network.dag.add_coordinator(coordinator)  # line to set the coordinator object
    network.dag.add_coordinator(network.coordinator)

    # #coordinator.dag = network.dag  # Set the DAG object for the Coordinator
    network.coordinator.dag = network.dag  # Set the DAG object for the Coordinator

    transactions = network.dag.simulate(num_batches=6, network=network)
    print(transactions)
    print("Simulation complete.")
