from Transaction.transaction import Transaction
from Network.node import Node
import rsa
import time
from datetime import datetime

class Coordinator(Node):
    def __init__(self, name, network, milestones_interval=10, is_coordinator=False):
        super().__init__(name, network)
        self.milestones_interval = milestones_interval
        self.milestones = []
        self.transaction_list = []
        self.timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]  # Gives you time up to milliseconds
        self.timestamp += str(int(time.time() * 1e9))[-6:]  # Append the last six digits of the current nanosecond time
        self.peers = []  # Initialize an empty list to store the Coordinator's peers
        # Generate RSA key pair for the Coordinator
        self.coordinator_public_key, self.coordinator_private_key = rsa.newkeys(512)
        self.is_coordinator = is_coordinator  # Override the attribute

    def cooridnator_view(self, transactions):
        transactions = list(transactions)
        self.transaction_list.extend(transactions)
        # print("TRANASCTION IN COORDINATOR VIEW:")
        # for transaction in transactions:
        #     print(transaction.txid)

    def generate_milestone(self):
        recent_transactions = self.get_recent_transactions()
        milestone_index = len(self.milestones) + 1
        milestone = {
            'index': milestone_index,
            'timestamp': self.timestamp,
            'signature': self.sign_milestone(milestone_index),
            'validated_transactions': []
        }

        # Convert list of validated transactions to a set for efficient membership testing
        validated_txids = set(t.txid for t in milestone['validated_transactions'])

        # Validate the signature and double spending for recent transactions
        for tx in recent_transactions:
            if not tx.validate_transaction():
                print(f"Invalid signature detected in transaction: {tx.txid}")

            elif self.is_double_spent(tx):
                print(f"Double spending detected in transaction: {tx.txid}")

            elif tx.txid not in validated_txids:
                milestone['validated_transactions'].append(tx)
                # Once the transaction is validated and added, also add its id to the set
                validated_txids.add(tx.txid)

        self.milestones.append(milestone)
        self.broadcast_milestone(milestone)

        # Print milestone information
        print(f"Milestone {milestone['index']} generated at {milestone['timestamp']}.")
        transaction_ids = [f"Txid={tx.txid}" for tx in milestone['validated_transactions']]
        if transaction_ids:
            print(f"Validated transactions: {', '.join(transaction_ids)}")
        else:
            print("No transactions added in the last 10 seconds")

    def sign_milestone(self, milestone_index):
        # Sign the milestone using the coordinator's private key
        milestone_data = f"{milestone_index}{self.name}".encode()
        signature = rsa.sign(milestone_data, self.coordinator_private_key, 'SHA-256')
        return signature

    def broadcast_milestone(self, milestone):
        # Broadcast the milestone to all peers
        valid_count = 0
        for peer in self.peers:
            if peer.receive_milestone(milestone):
                valid_count += 1

        print(f"Milestone {milestone['index']} has been broadcasted to all peers and validated by {valid_count} out of {len(self.peers)} peers.")

    def receive_milestone(self, milestone):
        # Add the received milestone to the coordinator's list of milestones
        self.milestones.append(milestone)
        # Validate the signature of the milestone
        if self.validate_milestone_signature(milestone):
            print(f"Milestone {milestone['index']} received and signature validated.")
        else:
            print(f"Milestone {milestone['index']} received but signature validation failed.")

    def validate_milestone_signature(self, milestone):
        # Verify the signature of the milestone using the coordinator's public key
        milestone_data = f"{milestone['index']}{self.name}".encode()
        try:
            rsa.verify(milestone_data, milestone['signature'], self.coordinator_public_key)
            return True
        except rsa.VerificationError:
            return False

    # def get_recent_transactions(self):
    #     # current_time = time.time()
    #     # recent_transactions = [tx for tx in self.transaction_list if (current_time - tx.timestamp) <= self.milestones_interval]
    #     # for tx in recent_transactions:
    #     #     # print("RECENT TRANSACTIONS", tx.txid)
    #     # print("Current time:", current_time)
    #     # print("Oldest recent transaction time:",
    #     #       min(tx.timestamp for tx in recent_transactions) if recent_transactions else "None")
    #     # print("Newest transaction time:",
    #     #       max(tx.timestamp for tx in self.transaction_list) if self.transaction_list else "None")
    #
    #     # return recent_transactions

    def get_recent_transactions(self):
        current_time_str = datetime.now().strftime('%H:%M:%S.%f')
        current_time = datetime.strptime(current_time_str, '%H:%M:%S.%f')

        recent_transactions = []
        for tx in self.transaction_list:
            tx_time_str, tx_additional_ns = tx.timestamp[:-6], tx.timestamp[-6:]
            tx_time = datetime.strptime(tx_time_str, '%H:%M:%S.%f')

            # Check if the transaction was created in the recent interval
            if (current_time - tx_time).total_seconds() <= self.milestones_interval:
                recent_transactions.append(tx)

        return recent_transactions

    def run(self):
        while True:
            self.generate_milestone()
            time.sleep(self.milestones_interval)
