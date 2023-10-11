import random
import numpy as np
from collections import Counter
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import copy
class Observer:
    def __init__(self, network):
        self.transaction_analysis = None
        self.network = network
        self.node_observations = {}
        self.tip_observations = []

  #   def generate_observation_times(self, end_time, distribution='uniform', lambda_val=1):
  #       observation_times = []
  #       if distribution == 'uniform':
  #           observation_times = sorted([random.uniform(0, end_time) for _ in range(end_time)])
  #       elif distribution == 'exponential':
  #           observation_times = sorted([random.expovariate(lambda_val) for _ in range(end_time)])
  #       return observation_times
  # #Fixed Intervals (e.g., every 10 minutes within 1 hour):
  #   def generate_observation_times(self, end_time, interval=600):
  #       # 600 seconds = 10 minutes
  #       return list(range(0, end_time + 1, interval))
   #Random Intervals (e.g., 10 random times within 1 hour):
    def generate_observation_times(self, end_time, num_observations=10):
        observation_times = sorted([random.uniform(0, end_time) for _ in range(num_observations)])
        observation_times = [round(t, 3) for t in observation_times]
        return observation_times

    def observe_nodes(self, observation_times):
        print(f"Observing nodes at times: {observation_times}")
        for time in observation_times:
            self.node_observations[time] = {}
            for node in self.network.nodes:
                node_data = {
                    'received_transactions': copy.deepcopy(node.queue),
                    'generated_transactions': copy.deepcopy(node.generated_transactions),
                    'tips': copy.deepcopy(node.tips)
                }
                # Adding 'all_transactions' key to node_data
                node_data['all_transactions'] = node_data['received_transactions'] + node_data['generated_transactions']
                self.node_observations[time][node.name] = node_data
                self.tip_observations.extend(node.tips)

                # print(f"Data for time {time}: {self.node_observations[time]}")
                print(
                    f"FOR TIME {time}Node {node.name}: received_transactions={len(node_data['received_transactions'])},"
                    f"\n Tips={len(node_data['tips'])} \ngenerated_transactions={len(node_data['generated_transactions'])}")
                # print(f"Time: {time}, {self.assess_node_convergence(observation_times)}")

    def document_tips(self):
        self.tips_data = {}
        for time, observations in self.node_observations.items():
            self.tips_data[time] = {}
            for node_name, node_data in observations.items():
                self.tips_data[time][node_name] = node_data['tips']

    def assess_node_convergence(self, observation_time):

        observations = self.node_observations[observation_time]
        avg_overlaps_tips = self.compute_average_overlap(observations, 'tips')
        avg_jaccard_tips = self.compute_jaccard_similarity(observations, 'tips')

        avg_overlaps_trans = self.compute_average_overlap(observations, 'all_transactions')
        avg_jaccard_trans = self.compute_jaccard_similarity(observations, 'all_transactions')

        avg_jaccard_tips_val = sum(sum(sim.values()) for sim in avg_jaccard_tips.values()) / (
                len(observations) * (len(observations) - 1))

        # Removed multiplication by 100
        avg_overlap_tips_percent = sum(avg_overlaps_tips.values()) / len(observations)

        avg_jaccard_trans_val = sum(sum(sim.values()) for sim in avg_jaccard_trans.values()) / (
                len(observations) * (len(observations) - 1))

        # Removed multiplication by 100
        avg_overlap_trans_percent = sum(avg_overlaps_trans.values()) / len(observations)

        return (f"Convergence Status:\n"
                f"Tips - Average Overlap: {avg_overlap_tips_percent:.5f}%, Average Jaccard Similarity: {avg_jaccard_tips_val:.5f}\n"
                f"All Transactions - Average Overlap: {avg_overlap_trans_percent:.5f}%, Average Jaccard Similarity: {avg_jaccard_trans_val:.5f}")

    def compute_pairwise_overlap(self, observations, data_key):
        nodes = list(observations.keys())
        overlaps = {}
        for i in nodes:
            overlaps[i] = {}
            for j in nodes:
                if i != j:
                    flat_list_i = self.flatten(observations[i][data_key])
                    flat_list_j = self.flatten(observations[j][data_key])

                    try:
                        set_i = set(flat_list_i)
                        set_j = set(flat_list_j)
                    except TypeError as e:
                        print(f"Error when processing nodes {i} and {j} with data key {data_key}")
                        print("Content of flat_list_i:", flat_list_i)
                        print("Content of flat_list_j:", flat_list_j)
                        raise e

                    overlap = len(set_i.intersection(set_j))
                    total = len(set_i.union(set_j))
                    overlap_percentage = (overlap / total) * 100 if total != 0 else 0

                    overlaps[i][j] = overlap_percentage
        return overlaps

    def compute_average_overlap(self, observations, data_key):
        pairwise_overlaps = self.compute_pairwise_overlap(observations, data_key)
        return {node: sum(overlaps.values()) / (len(overlaps) - 1) for node, overlaps in pairwise_overlaps.items()}

    def compute_jaccard_similarity(self, observations, data_key):
        nodes = list(observations.keys())
        similarities = {}
        for i in nodes:
            similarities[i] = {}
            for j in nodes:
                if i != j:
                    flat_list_i = self.flatten(observations[i][data_key])
                    flat_list_j = self.flatten(observations[j][data_key])

                    try:
                        set_i = set(flat_list_i)
                        set_j = set(flat_list_j)
                    except TypeError as e:
                        print(f"Error when processing nodes {i} and {j} with data key {data_key}")
                        print("Content of flat_list_i:", flat_list_i)
                        print("Content of flat_list_j:", flat_list_j)
                        raise e

                    intersection = len(set_i.intersection(set_j))
                    union = len(set_i.union(set_j))

                    similarity = intersection / union if union != 0 else 0
                    similarities[i][j] = similarity
        return similarities

    def flatten(self, some_list):
        flat_list = []
        for item in some_list:
            if isinstance(item, list):
                flat_list.extend(self.flatten(item))
            elif isinstance(item, tuple):
                flat_list.append(tuple(self.flatten(list(item))))
            else:
                flat_list.append(item)
        return flat_list

    def compute_tip_frequency(self):
        """
        Computes the frequency of each tip across all nodes.
        """
        all_tips = [tip for observations in self.node_observations.values()
                    for node_data in observations.values()
                    for tip in node_data['tips']]

        tip_counts = Counter(all_tips)

        # Sort by frequency
        sorted_tips = sorted(tip_counts.items(), key=lambda x: x[1], reverse=True)

        return sorted_tips

    def plot_tip_frequencies(self, tip_frequencies):

        tips, frequencies = zip(*tip_frequencies)

        # Plotting only top N tips for clarity
        N = 20
        plt.bar(tips[:N], frequencies[:N])

        plt.xlabel('Tips')
        plt.ylabel('Frequency')
        plt.title('Top N Tip Frequencies')
        plt.xticks(rotation=45)
        plt.show(block=True)

    def plot_tips_over_time(self):
        tips_counts = {time: sum([len(node_data['tips']) for node_data in observations.values()])
                       for time, observations in self.node_observations.items()}

        plt.plot(list(tips_counts.keys()), list(tips_counts.values()))
        plt.xlabel('Time')
        plt.ylabel('Number of Tips')
        plt.title('Tips Over Time')
        plt.grid(True)
        plt.show(block=True)

    def plot_lifetime_of_tips(self):
        tip_lifetimes = {}
        for time, observations in self.node_observations.items():
            for node_data in observations.values():
                for tip in node_data['tips']:
                    if tip not in tip_lifetimes:
                        tip_lifetimes[tip] = time
                    else:
                        tip_lifetimes[tip] = time - tip_lifetimes[tip]

        plt.hist(list(tip_lifetimes.values()), bins=20)
        plt.xlabel('Lifetime of Tips')
        plt.ylabel('Frequency')
        plt.title('Distribution of Tip Lifetimes')
        plt.grid(True)
        plt.show(block=True)

    def plot_tip_validation_distribution(self):
        node_tip_counts = {}
        for time, observations in self.node_observations.items():
            for node, node_data in observations.items():
                if node not in node_tip_counts:
                    node_tip_counts[node] = len(node_data['tips'])
                else:
                    node_tip_counts[node] += len(node_data['tips'])

        sorted_nodes = sorted(node_tip_counts.items(), key=lambda x: x[1], reverse=True)
        nodes, tip_counts = zip(*sorted_nodes)
        plt.bar(nodes, tip_counts)
        plt.xlabel('Node')
        plt.ylabel('Number of Tips Validated')
        plt.title('Node-wise Tip Validation Distribution')
        plt.xticks(rotation=90)
        plt.grid(True)
        plt.show(block=True)

    def compute_average_tip_lifetime(self):
        all_lifetimes = [node.tip_lifetimes for node in self.network.nodes]
        all_lifetimes_flat = [lifetime for lifetimes in all_lifetimes for lifetime in lifetimes.values()]
        return np.mean(all_lifetimes_flat)

    def tip_confirmation_rate(self):
        confirmed_tips = sum([len(node.tip_lifetimes) for node in self.network.nodes])
        total_tips = confirmed_tips + sum([len(node.tip_creation_times) for node in self.network.nodes])
        return confirmed_tips / total_tips if total_tips else 0

    def plot_pairwise_overlap_heatmap(self, data_key):
        # Generate pairwise overlap data
        overlap_data = self.compute_pairwise_overlap(self.node_observations, data_key)

        # Convert dictionary to matrix format
        nodes = list(overlap_data.keys())
        overlap_matrix = [[overlap_data[i][j] for j in nodes] for i in nodes]

        # Plot heatmap
        plt.figure(figsize=(10, 8))
        sns.heatmap(overlap_matrix, annot=True, cmap='viridis', xticklabels=nodes, yticklabels=nodes)
        plt.title(f'Pairwise Overlap for {data_key}')
        plt.show(block=True)

    def plot_average_overlap_heatmap(self, data_key):
        # Generate average overlap data
        avg_overlap_data = self.compute_average_overlap(self.node_observations, data_key)

        # Convert dictionary to matrix format
        nodes = list(avg_overlap_data.keys())
        avg_overlap_matrix = [[avg_overlap_data[node]] for node in nodes]

        # Plot heatmap
        plt.figure(figsize=(10, 8))
        sns.heatmap(avg_overlap_matrix, annot=True, cmap='viridis', xticklabels=nodes, yticklabels=['Avg Overlap'])
        plt.title(f'Average Overlap for {data_key}')
        plt.show(block=True)

    def plot_jaccard_similarity_heatmap(self, data_key):
        # Generate Jaccard similarity data
        jaccard_data = self.compute_jaccard_similarity(self.node_observations, data_key)

        # Convert dictionary to matrix format
        nodes = list(jaccard_data.keys())
        jaccard_matrix = [[jaccard_data[i][j] for j in nodes] for i in nodes]

        # Plot heatmap
        plt.figure(figsize=(10, 8))
        sns.heatmap(jaccard_matrix, annot=True, cmap='viridis', xticklabels=nodes, yticklabels=nodes)
        plt.title(f'Jaccard Similarity for {data_key}')
        plt.show(block=True)

    def visualize(self):

        for observation_time in self.node_observations.keys():  # Loop over all observation times
            nodes = list(self.node_observations[observation_time].keys())

            # Calculate pairwise overlaps for  data_key
            pairwise_overlaps = self.compute_pairwise_overlap(self.node_observations[observation_time], 'all_transactions')

            # Diagnostic print
            print(f"Observation Time: {observation_time}")
            print(f"Nodes: {nodes}")
            print(f"Pairwise overlaps: {pairwise_overlaps}")

            # Construct heatmap matrix
            overlap_matrix = []
            for i in nodes:
                row = []
                for j in nodes:
                    try:
                        # If i and j are the same (diagonal), set overlap to 100
                        if i == j:
                            row.append(100)
                        else:
                            row.append(pairwise_overlaps[i][j])
                    except KeyError as e:
                        print(f"Error accessing pairwise_overlaps with i={i} and j={j}. Error: {e}")
                        row.append(0)  # Defaulting to zero or any other value if you'd like.
                overlap_matrix.append(row)

            # Using Seaborn's heatmap function to plot
            plt.figure(figsize=(10, 8))
            sns.heatmap(overlap_matrix, annot=True, cmap="RdYlGn", xticklabels=nodes, yticklabels=nodes, fmt='.0f', linewidths=0)
            plt.title(f"Pairwise Node Convergence for All Transactions - Observation Count {observation_time}")
            plt.xlabel("Nodes")
            plt.ylabel("Nodes")
            plt.show(block=True)

    # Identifying Time of Minimum Difference: For identifying the time at which nodes have the minimum difference,
    # you can keep track of the variance or some other measure of dispersion in the number of transactions or
    # tips at each observation time, and then find the time with the lowest value.

    def time_of_minimum_difference(self):
        min_diff_time = None
        min_variance = float('inf')

        for time, analysis in self.transaction_analysis.items():  # or self.tips_analysis.items()
            variances = self.compute_variances(analysis)

            if variances < min_variance:
                min_variance = variances
                min_diff_time = time

        return min_diff_time

    def compute_variances(self, analysis):
        # For simplicity, computing variance based on the number of unique transactions/tips across nodes.
        transaction_variance = len(analysis['all_transactions']['different']) - analysis['all_transactions']['same']
        tips_variance = len(self.tips_analysis.items()) - self.tips_analysis['same_tips']
        return transaction_variance + tips_variance





