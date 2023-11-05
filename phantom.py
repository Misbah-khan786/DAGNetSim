import networkx as nx
import matplotlib.pyplot as plt
import random


def past(block, dag):
    return set(nx.ancestors(dag, block))


def future(block, dag):
    return set(nx.descendants(dag, block))


def anticone(block, dag):
    past_set = past(block, dag)
    future_set = future(block, dag)
    return set(dag.nodes()) - past_set - future_set


def tips(dag):
    return [node for node, in_degree in dag.out_degree() if in_degree == 0]


def calculate_scores(dag):
    scores = {}
    for node in dag.nodes():
        scores[node] = len(past(node, dag))
    return scores

def blue_past(node, dag, blue_set):
    return past(node, dag).intersection(blue_set)

def calculate_scores_and_blue_scores(dag, blue_set):
    scores = {}
    blue_scores = {}
    for node in dag.nodes():
        scores[node] = len(past(node, dag))
        blue_scores[node] = len(blue_past(node, dag, blue_set))
    return scores, blue_scores

def print_scores_and_blue_scores(scores, blue_scores):
    for node in scores.keys():
        print(f"Block {node}: Score: {scores[node]}, Blue Score: {blue_scores[node]}")


def greedy_chain_selection(dag, scores):
    # Start with the tip with the highest score
    current_node = max(tips(dag), key=scores.get)
    chain = [current_node]

    while current_node != 'genesis':
        predecessors = list(dag.predecessors(current_node))
        if predecessors:
            # Get the maximum score among the predecessors
            max_score = max([scores[node] for node in predecessors])
            # Select all nodes(if max score is similar i.e. all predecessors have the same score.)
            tie_breaking = [node for node in predecessors if scores[node] == max_score]
            # Randomly select among the nodes with the maximum score
            current_node = random.choice(tie_breaking)
            chain.append(current_node)
        else:
            # If no predecessors, break
            break

    return chain


def blue_anticone(block, dag, blue_set):
    general_anticone = anticone(block, dag)
    return general_anticone.intersection(blue_set)


def construct_blue_set(dag, chain, k=3):
    blue_set = []
    # Add the genesis block to the blue set
    blue_set.append('genesis')

    for node in reversed(chain):  # Moving from genesis to the first block in the chain
        node_past = past_for_blue_set(node, dag)
        for block in node_past:
            if len(blue_anticone(block, dag, set(blue_set))) <= k and block not in blue_set:
                blue_set.append(block)

        # Now, check for the current node from the chain
        if len(blue_anticone(node, dag, set(blue_set))) <= k and node not in blue_set:
            blue_set.append(node)

    # Now, go through all tips
    for tip in tips(dag):
        if len(blue_anticone(tip, dag, set(blue_set))) <= k and tip not in blue_set:
            blue_set.append(tip)

    return blue_set


def past_for_blue_set(node, dag):
    visited = set()
    queue = [node]
    ancestors = []

    while queue:
        current_node = queue.pop(0)
        for predecessor in dag.predecessors(current_node):
            if predecessor not in visited:
                visited.add(predecessor)
                queue.append(predecessor)
                ancestors.append(predecessor)

    return ancestors

def order_dag(dag, k):
    def children(node, dag):
        return sorted(list(dag.successors(node)), reverse=True)  # Prioritize blue childern,then red childeren over parent

    blue_set = set(construct_blue_set(dag, greedy_chain_selection(dag, calculate_scores(dag)), k))
    topological_queue = []
    ordered_list  = []

    topological_queue.append('genesis')

    while topological_queue:
        B = topological_queue.pop(0)
        ordered_list.append(B)
        for C in set(children(B, dag)) & blue_set:
            for D in set(past(C, dag)) & set(anticone(B, dag)) - set(ordered_list):
                if D not in topological_queue: # ensure no duplicates
                    topological_queue.append(D)
            if C not in topological_queue: # ensure no duplicates
                topological_queue.append(C)

    # Ensure all blocks are present in the ordered list
    for block in dag.nodes():
        if block not in ordered_list:
            ordered_list.append(block)

    return ordered_list




def block_details(block_name, dag):
    print(f"Details for block {block_name}:")
    print("past({}) =".format(block_name), past(block_name, dag))
    print("future({}) =".format(block_name), future(block_name, dag))
    print("anticone({}) =".format(block_name), anticone(block_name, dag))
    print("tips(G) =", tips(dag))


# Create a directed graph using networkx
dag = nx.DiGraph()
# Add nodes
nodes = ['genesis', 'D', 'B', 'C', 'D', 'E', 'F', 'H', 'I', 'J', 'K', 'L', 'M']
dag.add_nodes_from(nodes)

# Add edges
edges = [('D', 'genesis'), ('C', 'genesis'), ('B', 'genesis'), ('E', 'genesis'), ('H', 'D'), ('H', 'C'),
         ('H', 'E'), ('I', 'E'), ('F', 'B'), ('F', 'C'), ('K', 'B'), ('K', 'H'), ('K', 'I'), ('J', 'F'), ('J', 'H'),
         ('L', 'D'),
         ('L', 'I'), ('M', 'F'), ('M', 'K')]
reversed_edges = [(target, source) for source, target in edges]
dag.add_edges_from(reversed_edges)
# block_name = 'M'
# block_details(block_name, dag)
#################################################
# Calculate scores
scores = calculate_scores(dag)
# Get the greedy chain
chain = greedy_chain_selection(dag, scores)
# Construct the blue set
blue_set = construct_blue_set(dag, chain)
print("Greedy Chain:", chain)
print("Blue Set:", blue_set)
ord_dag = order_dag(dag, 3)
print("Ordered DAG:", ord_dag)
scores, blue_scores = calculate_scores_and_blue_scores(dag, blue_set)
print_scores_and_blue_scores(scores, blue_scores)