import rsa
import datetime
from datetime import datetime
import time
import os
import simpy
from Transaction.transaction import Transaction
from queue import Queue
import asyncio
import threading
import logging
import hashlib


def setup_logger(logger_name, log_file, level=logging.INFO):
    # Create the logs_3 directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    handler = logging.FileHandler(log_file, mode='w')
    # Including time in the log messages
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    # Remove all handlers from the logger if it already exists and has handlers
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.addHandler(handler)
    logger.debug('Logger setup successfully.')
    return logger

#Define a class called Node, representing a participant in the network
class Node:
    # Initialization function to set up a new Node
    def __init__(self, name, network, delay_range=(2, 7)): #is_coordinator=False

        self.network = network
        self.delay_range = delay_range
        # # The Node knows whether it's a coordinator
        # self.is_coordinator = is_coordinator
        # Assign the name passed as an argument to the Node's name
        self.name = name
        # Generate a pair of RSA keys for the Node, one public and one private
        (self.public_key, self.private_key) = rsa.newkeys(512)
        # Initialize an empty list to store the Node's transactions
        self.transaction_list = []
        # Initialize an empty list to store the Node's unconfirmed/confirmed transactions
        self.unconfirmed_transactions = []
        self.confirmed_transactions = []
        # Initialize an empty list to store the Node's peers
        self.peers = []
        # Initialize an empty list to store the Node's milestones
        self.milestones = []
        self.genesis_milestone = None  # to recieve Gensis milestone by Nodes in Dag_Event class
        self.nodes_received_transactions =[]
        self.tips=[]
        self.broadcasted_transactions = []
        self.is_coordinator = False
        self.coordinator_public_key = None
        self.transaction_counter = 0
        self.seen_and_broadcasted_transactions = set()
        # Configure the logger for the node
        log_file = f"logs/{self.name}.log"
        self.logger = setup_logger(self.name, log_file)
        # self.logger.info("This is a test log message.")
        # close_logger(self.logger)

        self.DIFFICULTY = 1

        self.lock = asyncio.Lock()

    def generate_id(self):
        self.transaction_counter += 1
        return f"{self.name}-{self.transaction_counter:01}"

    def create_and_sign_transaction(self, txid, parent_txids, DIFFICULTY):
        # Generate a random data string
        data = os.urandom(500000)  # generates 500,000 bytes = 0.5 MB
        data = data.decode('latin1')  # decode bytes to string using 'latin1' encoding

        # Create a new Transaction object
        transaction = Transaction(txid, parent_txids, self,data)

        # Proof of Work
        prefix = '0' * DIFFICULTY
        nonce = 0
        while True:
            # create message using transaction data and nonce
            message = transaction.get_data_to_sign() + str(nonce).encode()
            # compute hash
            hash_result = hashlib.sha256(message).hexdigest()
            if hash_result.startswith(prefix):
                break
            nonce += 1

        # Sign the transaction's data using the Node's private key
        transaction.signature = rsa.sign(
            transaction.get_data_to_sign(),
            self.private_key,
            'SHA-256'
        )

        transaction.nonce = nonce  # store the nonce in the transaction

        # Add the signed transaction to the Node's list of transactions

        self.transaction_list.append(transaction)
        print("TOTAL GENRATED TRASACTIONS SO FAR BY  NODE", self.name, len(self.transaction_list))
        self.logger.info(f"TOTAL GENRATED TRASACTIONS SO FAR BY  NOD {self.name} are {len(self.transaction_list)}")
        print(f" {datetime.now().strftime('%H:%M:%S.%f')} - {self.name} GENRATED THE TRANSACT ID: {transaction.txid}")
        self.logger.info(f"{datetime.now().strftime('%H:%M:%S.%f')} - {self.name} GENRATED THE TRANSACT ID: {transaction.txid}")

        self.tips.append(transaction)
        tip_ids = list(set([tip.txid for tip in self.tips]))  # Extract tip IDs
        print(f"{self.name} added transaction{transaction.txid} to its tips:{tip_ids}")
        self.logger.info(f"{datetime.now().strftime('%H:%M:%S.%f')} - {self.name} added transaction{transaction.txid} to its tips:{tip_ids} ")

        # If this transaction references any previous tips, remove them from the tips list
        for parent in transaction.parent_txids:
            if parent in self.tips:
                self.tips.remove(parent)
                print(f"{parent} is no loger tip for {self.name}")
                self.logger.info(f"{datetime.now().strftime('%H:%M:%S.%f')} - {parent} is no loger tip for {self.name}")

        return transaction

    async def broadcast_transaction(self, transaction, sender=None):
        if transaction.txid in self.seen_and_broadcasted_transactions:
            return
        tasks = []
        for peer in self.peers:
            if peer == sender:
                continue
            delay = self.network.delay_matrix[(self, peer)]
            tasks.append(asyncio.create_task(self._send_transaction_to_peer(transaction, peer, delay)))
        await asyncio.gather(*tasks)

    async def _send_transaction_to_peer(self, transaction, peer, delay):
        # await asyncio.sleep(delay)
        await peer.receive_transaction(transaction, self)

    async def receive_transaction(self, transaction, sender=None):

        # Check if the transaction has already been received
        if transaction.txid in self.seen_and_broadcasted_transactions:
            return
        if transaction in self.nodes_received_transactions:
            return
        if transaction in self.transaction_list:
            return
        # Add the transaction to the list of unconfirmed transactions
        self.unconfirmed_transactions.append(transaction)

        # The delay logic you had with time.sleep could be replaced with await asyncio.sleep(delay) if want to reintroduce it

        # # Validate the transaction
        # if not transaction.validate_transaction(DIFFICULTY=1):
        #     print(f"Invalid transaction {transaction.txid}")
        #     return

        async with self.lock:
            self.nodes_received_transactions.append(transaction)
        nodes_received_transactions_ids= [tx.txid for tx in self.nodes_received_transactions]
        print("TOTAL Recived TRASACTIONS SO  FAR BY NODE", self.name, nodes_received_transactions_ids)
        self.logger.info(f"TOTAL RECIEVED TRASACTIONS SO FAR BY  NOD {self.name} are {len(self.nodes_received_transactions)}")
        # self.transaction_timestamps[transaction.txid] = datetime.now()
        print(
            f"{datetime.now().strftime('%H:%M:%S.%f')} - {self.name} received Transaction ID {transaction.txid} from {sender.name}")
        # self.logger.info(
        #     f"{datetime.now().strftime('%H:%M:%S.%f')} - {self.name} received Transaction ID {transaction.txid} from {sender.name}")

        # If the transaction has no children, add it to the tips and if its a parent then remove it from tip list
        if not transaction.children and transaction not in self.tips:
            print(
                f" Transaction ID : {transaction.txid} do not have children, that's why added to tip of {self.name}")
            # self.logger.info(
            #     f"{datetime.now().strftime('%H:%M:%S.%f')} - Transaction ID : {transaction.txid} do not have children, that's why added to tip of {self.name} ")
            self.tips.append(transaction)
        for parent in transaction.parent_transactions:
            if parent in self.tips:
                self.tips.remove(parent)
                print(f" Transaction {parent.txid} is no longer a tip for {self.name}")
                # self.logger.info(
                #     f"{datetime.now().strftime('%H:%M:%S.%f')} - Transaction {parent.txid} is no longer a tip for {self.name} ")

        ip_ids = list(set([tip.txid for tip in self.tips]))
        print(f"Tips of {self.name}, {ip_ids}")
        # self.logger.info(f"{datetime.now().strftime('%H:%M:%S.%f')} - Tips of {self.name}, {ip_ids} ")

        # Forward the transaction
        self.seen_and_broadcasted_transactions.add(transaction.txid)

        # Forward the transaction to the peers of this node
        await self.broadcast_transaction(transaction, sender)

    def is_double_spent(self, transaction):
        # Check if the transaction spends from an address that has already been spent
        # Check if the transaction is already in the node's transaction list

        for tx in self.transaction_list:
            if tx != transaction and tx.node == transaction.node and tx.txid == transaction.txid:
                return True

        # # Check if the tx.id is in its parents and also their parents
        # queue = [parent for parent in transaction.parent_txids]
        # while queue:
        #     current = queue.pop(0)
        #     if current == transaction.txid:
        #         return True  # Double spend detected
        #
        #     # Search for transaction with 'current' ID in transaction list
        #     for tx in self.transaction_list:
        #         if tx.txid == current:
        #             queue.extend(tx.parent_txids)
        #             break

        ###################This code uses a breadth-first search approach,
        # where the queue holds the parent transactions that still need to be checked.
        # If it finds a parent transaction that has the same txid as the transaction in question,
        # it means there's a double spend and it returns True.
        # If it checks all parent transactions and doesn't find a match,
        # it means there's no double spend and it returns False.
        ####################

        return False


    def receive_milestone(self, milestone):
        # Store the milestone
        self.milestones.append(milestone)
        # Validate the signature of the milestone
        if self.validate_milestone_signature(milestone):
            # Validate and confirm transactions in the milestone
            for transaction in milestone['validated_transactions']:
                #print("Transactions from Milestone",transaction)
                self.validate_and_confirm(transaction)

            return True
        else:
            return False
        # if self.validate_milestone_signature(milestone):
        #     return True
        # else:
        #     return False

    def validate_and_confirm(self, transaction):
        # existing validation code...
        transaction.confirm()  # confirm the transaction

    def validate_milestone_signature(self, milestone):
        # Verify the signature of the milestone using the coordinator's public key
        if isinstance(milestone, dict):  # For regular milestones represented as dictionaries
            milestone_data = f"{milestone['index']}Coordinator".encode()
            try:
                rsa.verify(milestone_data, milestone['signature'], self.coordinator_public_key)
                return True
            except rsa.VerificationError:
                return False
        elif isinstance(milestone, Transaction):  # For the genesis milestone represented as a Transaction
            # Perform validation for a Transaction object
            try:
                rsa.verify(
                    milestone.get_data_to_sign(),
                    milestone.signature,
                    self.coordinator_public_key
                )
                return True
            except rsa.VerificationError:
                return False
        else:
            raise ValueError("Invalid type for milestone. Expected dict or Transaction.")

    def receive_genesis_milestone(self, genesis_milestone):
        # Store the milestone
        self.genesis_milestone = genesis_milestone
        # Validate the signature of the milestone
        self.nodes_received_transactions.append(genesis_milestone)
        self.tips.append(genesis_milestone)
        if self.validate_milestone_signature(genesis_milestone):
            # Validate and confirm the single transaction in the milestone
            self.validate_and_confirm(genesis_milestone)
            # Store the milestone in the received transactions
            self.nodes_received_transactions.append(genesis_milestone)
            return True
        else:
            return False

class Coordinator(Node):
    def __init__(self, name, network, milestones_interval, is_coordinator=False):
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
        log_file = f"logs/{self.name}.log"
        self.logger = setup_logger(self.name, log_file)
        self.last_milestone_time = datetime.fromtimestamp(time.time())

    def cooridnator_view(self, transaction):
        self.transaction_list.append(transaction)
        # print("TRANASCTION IN COORDINATOR VIEW:")
        # self.logger.info("TRANASCTION IN COORDINATOR VIEW:")
        # for transaction in self.transaction_list:
        #     print(transaction.txid)
        #     self.logger.info(f" Coordinator Know {transaction.txid}")

    def generate_milestone(self, current_time ):

        self.logger.info(f'Current transactions: {[tx.txid for tx in self.transaction_list]}')
        buffer_time = 0.1  # 100 milliseconds
        time.sleep(buffer_time)
        # # Update timestamp for each new milestone
        # self.timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        # self.timestamp += str(int(time.time() * 1e9))[-6:]  # Append the last six digits of the current nanosecond time

        recent_transactions = self.get_recent_transactions(current_time)
        self.logger.info(f"Recent transactions: {[tx.txid for tx in recent_transactions]}")  # NEW LOG STATEMENT
        milestone_index = len(self.milestones) + 1
        milestone = {
            'index': milestone_index,
            'timestamp': datetime.now().strftime('%H:%M:%S.%f'),  # Current time when milestone is generated
            'signature': self.sign_milestone(milestone_index),
            'validated_transactions': []
        }

        # Convert list of validated transactions to a set for efficient membership testing
        validated_txids = set(t.txid for t in milestone['validated_transactions'])

        # Validate the signature and double spending for recent transactions
        for tx in recent_transactions:
            if not tx.validate_transaction(DIFFICULTY=1):
                print(f"Invalid signature detected in transaction: {tx.txid}")
                self.logger.info(f"Invalid signature detected in transaction: {tx.txid}")

            elif self.is_double_spent(tx):
                print(f"Double spending detected in transaction: {tx.txid}")
                self.logger.info(f"Double spending detected in transaction: {tx.txid}")

            elif tx.txid not in validated_txids:
                milestone['validated_transactions'].append(tx)
                # Once the transaction is validated and added, also add its id to the set
                validated_txids.add(tx.txid)

        self.milestones.append(milestone)
        self.last_milestone_time = datetime.fromtimestamp(
            time.time())  # Updates the time each time a new milestone is generated
        self.broadcast_milestone(milestone)

        # Print milestone information
        print(f"Milestone {milestone['index']} generated at {milestone['timestamp']}.")
        self.logger.info(f"Milestone {milestone['index']} generated at {milestone['timestamp']}.")
        transaction_ids = [f"Txid={tx.txid}" for tx in milestone['validated_transactions']]
        if transaction_ids:
            print(f"Validated transactions: {', '.join(transaction_ids)}")
            self.logger.info(f"Validated transactions: {', '.join(transaction_ids)}")
        else:
            print(f"No transactions added since the last Mileston")
            self.logger.info(f"No transactions added since the last Mileston")

    def sign_milestone(self, milestone_index):
        # Sign the milestone using the coordinator's private key
        milestone_data = f"{milestone_index}{self.name}".encode()
        signature = rsa.sign(milestone_data, self.coordinator_private_key, 'SHA-256')
        return signature

    def broadcast_milestone(self, milestone):
        valid_count = 0
        # Send the milestone to all peers in the network
        for peer in self.peers:
            if isinstance(milestone, Transaction):  # If milestone is a Transaction object (genesis milestone)
                # delay = self.network.delay_matrix[(self, peer)]
                # if peer.receive_genesis_milestone(milestone,delay):
                if peer.receive_genesis_milestone(milestone):
                    valid_count += 1
            elif isinstance(milestone, dict):  # If milestone is a dictionary (regular milestone)
                if peer.receive_milestone(milestone):
                    valid_count += 1
        # Log the broadcasted milestone
        if isinstance(milestone, Transaction):  # If milestone is a Transaction object (genesis milestone)
            print(
                f"Genesis milestone (ID: {milestone.txid}) has been broadcasted by coordinator to all peers and validated by {valid_count} out of {len(self.peers)} peers.")
            self.logger.info(f"Genesis milestone (ID: {milestone.txid}) has been broadcasted by coordinator to all peers and validated by {valid_count} out of {len(self.peers)} peers.")
        elif isinstance(milestone, dict):  # If milestone is a dictionary (regular milestone)
            print(
                f"Milestone {milestone['index']} has been broadcasted by coordinator to all peers and validated by {valid_count} out of {len(self.peers)} peers.")
            self.logger.info( f"Milestone {milestone['index']} has been broadcasted by coordinator to all peers and validated by {valid_count} out of {len(self.peers)} peers.")

    def get_recent_transactions(self, current_time):
        # current_time_str = datetime.now().strftime('%H:%M:%S.%f')
        # current_time = datetime.strptime(current_time_str, '%H:%M:%S.%f')

        recent_transactions = []
        for tx in self.transaction_list:
            # tx_time is already a datetime object, no need for conversion
            tx_time = tx.timestamp

            # Check if the transaction was created in the recent interval
            if (current_time - tx_time).total_seconds() <= self.milestones_interval:
                recent_transactions.append(tx)
        # # recent_transactions = [tx for tx in self.transaction_list if self.last_milestone_time <= tx.timestamp < current_time]
        # recent_transactions = [tx for tx in self.transaction_list if
        #                        self.last_milestone_time <= tx.timestamp < current_time]
        #
        # # self.transaction_list = [tx for tx in self.transaction_list if tx.timestamp >= current_time]
        # self.last_milestone_time = current_time

        return recent_transactions

    # def run(self):
    #     while True:
    #         self.generate_milestone()
    #         time.sleep(self.milestones_interval)


