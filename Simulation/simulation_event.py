from datetime import datetime
import matplotlib.pyplot as plt
plt.ion()
import simpy

from DAG.dag_event import DAG_Event
from Network.network import Network
from Network.node import Node, Coordinator
from Simulation.networkinfoprinter import NetworkInfoPrinter

def run_simulation():
    # Define parameters
    num_nodes = 7
    poisson_rate = 0.5
    milestones_interval = 10
    simulation_time = 100# Add the simulation_time

    # Create a network
    network = Network(num_nodes)
    # Get the loggers of all nodes in the network
    loggers = [node.logger for node in network.nodes]


    # Initialize DAG_Event
    dag_event = DAG_Event(poisson_rate, milestones_interval, network,loggers)
    dag_event.coordinator = network.coordinator
    network.draw_network()
    # Generate and broadcast genesis milestone
    dag_event.coordinator_genesis_milestone()


    # Run the simulation
    dag_event.simulate(simulation_time, network)  # Use the simulate method instead of env.run()
    dag_event.draw_dag_event()
    for node in network.nodes:
        dag_event.draw_dag_event(node)
    # info_printer = NetworkInfoPrinter(network)
    # info_printer.print_network_info()

if __name__ == "__main__":
    run_simulation()
    input("Press Enter to end the simulation...")
