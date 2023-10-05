import numpy as np
from scipy.stats import poisson, kstest
from Network.network import Network
from Network.observer import Observer
import matplotlib.pyplot as plt
def simulate(N, p, duration, observation_times):
    print("Initializing network...")
    network = Network(N, p)
    observer = Observer(network)
    # observation_times = observer.generate_observation_times(end_time=60, num_observations=3)
    print(observation_times)
    print("Network initialized.")

    for _ in range(duration):
        print(f"Simulating second {_}...")
        network.simulate_second()
        if _ in observation_times:
            print("GOING IN OBSERVER")
            observer.observe_nodes([_])  # observe at this second
            # observer.analyse_transactions()
            # observer.analyse_tips()
            # print(f"Time: {_}, {observer.assess_node_convergence(_)}")
        print(f"Finished simulating second {_}.")
    # Count transactions for each node
    transaction_counts = [len(node.queue) for node in network.nodes]

    return transaction_counts, network, observer
if __name__ == '__main__':

    print("Starting simulation...")
    # Generate observation times once
    observer_dummy = Observer(None)  # Temp observer to generate observation times
    observation_times = [round(time) for time in observer_dummy.generate_observation_times(end_time=3600, num_observations=10)]
    print(observation_times)
    transaction_counts, network, observer  = simulate(5, 0.4, 3600, observation_times)
    mean_transactions = np.mean(transaction_counts)
    print("Mean Transactions",mean_transactions)
    # expected_distribution = [poisson.pmf(i, mean_transactions) for i in range(max(transaction_counts) + 1)]
    # # print("Expected distribution", expected_distribution)
    # for node_id_to_visualize in range(10):
    #     network.plot_inter_arrival_histogram(node_id_to_visualize, 3600)
   # # Print the combined generation rate and average delays AFTER the graph
   #  print("\nCombined Generation Rates for Each Node:")
   #  network.print_combined_generation_rate()
   #  print("\nAverage Delays for Each Node:")
   #  network.print_average_delays()
   #  print("\nTransactions for Each Node:")
   #  network.print_all_node_transactions()

    # Observer

    # observer = Observer(network)

    # # uniform or exponential
    # observation_times = observer.generate_observation_times(end_time=600, distribution='uniform')
    # # For fixed intervals of 15 minutes:
    # observation_times = observer.generate_observation_times(end_time=3600, interval=900)
    # For 20 random observations within the hour:
    # observation_times = observer.generate_observation_times(end_time=60, num_observations=3)
    # print(observation_times)
    #
    # observer.observe_nodes(observation_times)
    # print(observer.node_observations.keys())
    # print(observer.node_observations)
    # observer.analyse_transactions()
    # print("Transaction Analysis:", observer.transaction_analysis)
    # observer.analyse_tips()
    # print("Tips Analysis:", observer.tips_analysis)  # Debugging output
    # print(observer.transaction_analysis.keys())
    # print(observer.tips_analysis.keys())

    for time in observation_times:
        print(f"Time: {time}, {observer.assess_node_convergence(time)}")
    # observer.document_tips()

    # # Call other observer methods as needed
    # observer.analyse_tip_convergence()




