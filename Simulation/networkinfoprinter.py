class NetworkInfoPrinter:
    def __init__(self, network):
        self.network = network

    def print_network_info(self):
        print("Network Information:")
        print(f"Number of Nodes: {len(self.network.nodes)}")
        for node in self.network.nodes:
            print(f"Node: {node.name}")
            print(f"Peers: {', '.join(peer.name for peer in node.peers)}")
            print("Transactions:")
            for transaction in node.transaction_list:
                print(f"  - {transaction}")
            print()

