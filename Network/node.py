import rsa
import datetime
from datetime import datetime, timedelta

import time
import os
import simpy
from Transaction.transaction import Transaction
from queue import Queue
import asyncio
import threading
import logging
import hashlib
from multiprocessing import Process, Queue
import logging.handlers
from multiprocessing import Manager

import pickle
import random
import numpy as np

def setup_logger(logger_name, log_file, level=logging.INFO):
    # Create the logs directory if it doesn't exist
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
    return logger
# a class  Node, representing a participant in the network
class Node:
    # Initialization function to set up a new Node
    def __init__(self, name, network, delay_range=(2, 7)): #is_coordinator=False ##, log_queue
        manager = Manager()
        self.network = network
        self.delay_range = delay_range
        # Assign the name passed as an argument to the Node's name
        self.name = name
        # Generate a pair of RSA keys for the Node, one public and one private
        (self.public_key, self.private_key) = rsa.newkeys(512)
        # Initialize an empty list to store the Node's transactions
        self.transaction_list = []# manager.list()
        # Initialize an empty list to store the Node's unconfirmed/confirmed transactions
        self.unconfirmed_transactions = []
        self.confirmed_transactions = []
        # Initialize an empty list to store the Node's peers
        self.peers = []
        # Initialize an empty list to store the Node's milestones
        self.milestones = []
        self.genesis_milestone = None  # to recieve Gensis milestone by Nodes in Dag_Event class
        self.nodes_received_transactions = []# manager.list()
        self.tips= [] # manager.list()#
        self.broadcasted_transactions = []
        self.is_coordinator = False
        self.coordinator_public_key = None
        self.transaction_counter = 0
        self.seen_and_broadcasted_transactions = set()
        self.DIFFICULTY = 1
        self.lock = asyncio.Lock()
        self.pending_transactions = []  # list of tuples to store pending transactions and their timestamp

        self.MAX_PENDING_DURATION = timedelta(seconds=60)
        self.PENDING_CHECK_INTERVAL = 10  # How often to check the pending transactions, in seconds

        self.tips_lock = manager.Lock()
        self.nodes_received_transactions_lock= manager.Lock()
        self.transaction_list_lock = manager.Lock()

        ################################## Uncoment to use PR_AN.py #########################################
        # self.queue = []
        # self.tx_rate = random.uniform(0.01, 0.1)
        # self.transaction_count = 0
        # self.generated_transactions = []
        # self.transaction_history = []  # For historical data
        # self.current_transactions = 0  # For the current second
        # self.parent_map = {'genesis': False}  # Dictionary to keep track of which transactions are parents
        # self.tips = ['genesis']  # List to keep track of tips, initialized with the genesis transaction
        # self.tip_creation_times = {}  # {tip_id: creation_time}
        # self.tip_lifetimes = {}  # {tip_id: lifetime}

        #########################################

    def generate_transaction(self, network):
        # Draw a sample from Poisson distribution to get the number of transactions for this node at this time step
        num_transactions = np.random.poisson(self.tx_rate)
        for _ in range(num_transactions):
            self.transaction_count += 1
            txid = f"Node {self.name}-{self.transaction_count}"
            print(f"Node {self.name} has available tips: {self.tips}")
            # transaction = (txid, network.time)  # (node_id, timestamp)
            # Select parents from transactions which are not yet parents (i.e., they are tips)
            possible_parents = [tx for tx, is_parent in self.parent_map.items() if not is_parent]
            num_parents = min(2, len(possible_parents))
            parents = random.sample(possible_parents, num_parents) if num_parents > 0 else ['genesis']
            print(f"Node {self.name} selected parents: {parents} for transaction {txid} ")

            transaction = (txid, network.time, parents)  # (node_id, timestamp, [parent_ids])

            # Update the parent_map and tips
            self.update_parent_map_and_tips(txid, parents)
            # Append the generated transaction ID to the list of generated transactions
            self.generated_transactions.append(txid)
            print(
                f"Node {self.name} generated a transaction {transaction}at time {network.time} "
                f"for peers {network.peers[self.name]}")
            for peer in network.peers[self.name]:
                delay = network.delay_matrix[self.name][peer]
                network.add_transaction_to_future(transaction, peer, delay)

    def add_transaction(self, transaction):
        txid, _, parents = transaction  # Unpack transaction to get txid and parents
        self.queue.append(transaction)
        self.current_transactions += 1
        # Update the parent_map and tips for the received transaction
        self.update_parent_map_and_tips(txid, parents)

    def update_parent_map_and_tips(self, txid, parents):
        # Mark the selected parents as parents in parent_map
        for parent in parents:
            self.parent_map[parent] = True

        # Update the tips list
        old_tips = self.tips.copy()
        self.tips = [tip for tip in self.tips if tip not in parents]  # Remove parents from tips
        self.tips.append(txid)  # Add the new transaction to tips

        # Also, add the new transaction to the parent_map with is_parent as False
        self.parent_map[txid] = False
        for parent in parents:
            if parent in self.tip_creation_times:
                self.tip_lifetimes[parent] = self.network.time - self.tip_creation_times[parent]
                del self.tip_creation_times[parent]  # remove the tip since it's confirmed

            # For the new tip:
        self.tip_creation_times[txid] = self.network.time
        # print(f"Node {self.name} removed {parents} from tips.")
        # print(f"Node {self.name} added {txid} to tips.")
        # print(f"Node {self.name} updated tips: {self.tips} from old tips: {old_tips}")
    def transactions_received(self):
        return len(self.queue)
    def generate_id(self):
        self.transaction_counter += 1
        return f"{self.name}-{self.transaction_counter:01}"
    def update_history(self):
        self.transaction_history.append(self.current_transactions)
        self.current_transactions = 0

    def print_transactions(self):
        Total_gen = len(self.generated_transactions)
        Total_rec = len(self.queue)
        print(f"Node {self.name} has Generated (Total:{Total_gen}) the following transactions:")
        print(self.generated_transactions)  # Print the generated transactions
        print(f"Node {self.name} has Received (Total:{Total_rec}) the following transactions:")
        print(self.queue)
        ########################################
    def create_and_sign_transaction(self, txid, parent_txids, DIFFICULTY):
        # Generate a random data string
        # data = os.urandom(500000)  # generates 500,000 bytes = 0.5 MB
        data = os.urandom(1024)  # generates 1024 bytes = 1 KB = 0.001 MB
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
        print(f" {datetime.now().strftime('%H:%M:%S.%f')} - {self.name} GENRATED THE TRANSACT ID: {transaction.txid}")
        with self.tips_lock:
            self.tips.append(transaction)
            tip_ids = list(set([tip.txid for tip in self.tips]))  # Extract tip IDs
            print(f"{self.name} added transaction{transaction.txid} to its tips:{tip_ids}")

        # print(self.logger.__dict__)
        return transaction

    async def broadcast_transaction(self, transaction, sender=None):
        if transaction.txid in self.seen_and_broadcasted_transactions:
            return
        threads = []
        tasks = []
        for peer in self.peers:
            if peer == sender:
                continue
            delay = self.network.delay_matrix[(self, peer)]

            # Broadcast the transaction and its approved parents
            tasks.append(asyncio.create_task(self._send_transaction_to_peer(transaction, peer, delay)))
            for approved_transaction in transaction.parent_transactions:
                tasks.append(asyncio.create_task(self._send_transaction_to_peer(approved_transaction, peer, delay)))

        await asyncio.gather(*tasks)


    async def _send_transaction_to_peer(self, transaction, peer, delay):
        # await asyncio.sleep(delay)
        await peer.receive_transaction(transaction, delay, self)

    async def receive_transaction(self, transaction, delay, sender=None):
        # print("ENTERING IN THE RECEIVE")
        # Check if the transaction has already been received
        if transaction.txid in self.seen_and_broadcasted_transactions:
            # print("ALREADY SEEN")
            return
        if transaction in list(self.nodes_received_transactions):
            # print("ALREADY RECEIVEEd")
            return
        if transaction in list(self.transaction_list):
            # print("OWN TRANSACTION")
            return

        # First, check if we have the approved parents of this transaction
        nodes_received_transactions_ids = {tx.txid for tx in self.nodes_received_transactions}
        own_transactions_ids = {tx.txid for tx in self.transaction_list}
        missing_parents = [t for t in transaction.parent_transactions if
                           t.txid not in self.seen_and_broadcasted_transactions and t.txid
                           not in nodes_received_transactions_ids and t.txid not in own_transactions_ids]

        missing_parents_ids = [tx.txid for tx in missing_parents]
        if missing_parents:
            print("UNKNOWN PARENT", missing_parents_ids)
            # Request the missing parent transactions
            for parent_tx in missing_parents:
                print("ASKING FOR MISSING PARENTS")
                await self.request_parent_transaction(parent_tx.txid, sender)
            # If there are missing parents, delay processing this transaction
            # Store it in some buffer or queue for later processing
            # When adding to pending
            self.pending_transactions.append((transaction, datetime.now()))
            print("ADDED TRANSACTION TO MISSING PARENT")
            return

     # The delay logic  with time.sleep could be replaced with await asyncio.sleep(delay) if want to reintroduce it

        # Validate the transaction
        # if not transaction.validate_transaction(DIFFICULTY=1):
        #     print(f"Invalid transaction {transaction.txid}")
        #     return
        nodes_received_transactions_ids_b =[tx.txid for tx in self.nodes_received_transactions]
        transaction_list_id = [tx.txid for tx in self.transaction_list]
        print(f"{self.name} list of OWN TRANSACTIONS {transaction_list_id}")
        print(
            f"{self.name} list of received transaction before appending the new transaction {list(set(nodes_received_transactions_ids_b))}")
        # async with self.lock:
        self.nodes_received_transactions.append(transaction)
        nodes_received_transactions_ids = [tx.txid for tx in self.nodes_received_transactions]
        print("TOTAL Received TRANSACTIONS SO  FAR BY NODE", self.name, list(set(nodes_received_transactions_ids)))
        # self.transaction_timestamps[transaction.txid] = datetime.now()
        print(f"{datetime.now().strftime('%H:%M:%S.%f')} - {self.name} received Transaction ID {transaction.txid} from {sender.name} with delay {delay}")
        # If the transaction has no children, add it to the tips and if its a parent then remove it from tip list
        if not transaction.children and transaction not in self.tips:
            print(f" Transaction ID : {transaction.txid} do not have children, that's why added to tip of {self.name}")
            self.tips.append(transaction)
        for parent in transaction.parent_transactions:
            if parent in self.tips:
                self.tips.remove(parent)
                print(f" Transaction {parent.txid} is no longer a tip for {self.name}")

        ip_ids = list(set([tip.txid for tip in self.tips]))
        print(f"Tips of {self.name}, {ip_ids}")


        # Forward the transaction
        self.seen_and_broadcasted_transactions.add(transaction.txid)

        # When checking pending transactions
        for pending_tx, timestamp in list(self.pending_transactions):
            if datetime.now() - timestamp > self.MAX_PENDING_DURATION:
                self.pending_transactions.remove((pending_tx, timestamp))

        # Forward the transaction to the peers of this node
        await self.broadcast_transaction(transaction, sender)
    async def process_pending_transactions(self):
        while True:
            successfully_processed = []
            for transaction, timestamp in list(self.pending_transactions):
                success = await self.receive_transaction(transaction)
                if success:
                    successfully_processed.append((transaction, timestamp))
            # Remove processed transactions outside the loop
            for transaction, timestamp in successfully_processed:
                self.pending_transactions.remove((transaction, timestamp))
            await asyncio.sleep(self.PENDING_CHECK_INTERVAL)

    # Adding a method to request missing parent transactions
    async def request_parent_transaction(self, missing_txid, sender):
        if missing_txid not in self.seen_and_broadcasted_transactions:
            # send a request to sender or all peers to provide the missing transaction
            # for this example, let's just request it from the sender
            print("PROVIDING MISSING PARENT")
            await sender.provide_missing_transaction(missing_txid, self)

    # The corresponding method to provide the missing transaction
    async def provide_missing_transaction(self, txid, requester):
        # search for the transaction in the node's database and send it to the requester
        transaction = self.find_transaction_by_id(txid)
        if transaction:
            await self._send_transaction_to_peer(transaction, requester, 0)  # no delay in this case

    def find_transaction_by_id(self, txid):
        for transaction in self.nodes_received_transactions and self.transaction_list:
            if transaction.txid == txid:
                return transaction
        return None
    #
    # def broadcast_transaction(self, transaction, sender=None):
    #     pickle.dumps(transaction)
    #     if transaction.txid in self.seen_and_broadcasted_transactions:
    #         return
    #     threads = []
    #     tasks = []
    #     for peer in self.peers:
    #         if peer == sender:
    #             continue
    #         delay = self.network.delay_matrix[(self, peer)]
    #         # Broadcast the transaction and its approved parents
    #         tasks.append(asyncio.create_task(self._send_transaction_to_peer(transaction, peer, delay)))
    #         for approved_transaction in transaction.parent_transactions:
    #             tasks.append(asyncio.create_task(self._send_transaction_to_peer(approved_transaction, peer, delay)))
    #
    #     await asyncio.gather(*tasks)
    #
    #
    # async def _send_transaction_to_peer(self, transaction, peer, delay):
    #     # await asyncio.sleep(delay)
    #     await peer.receive_transaction(transaction, delay, self)
    #
    # def receive_transaction(self, transaction, delay, sender=None):
    #     # print("ENTERING IN THE RECEIVE")
    #     # Check if the transaction has already been received
    #     if transaction.txid in self.seen_and_broadcasted_transactions:
    #         # print("ALREADY SEEN")
    #         return
    #     if transaction in self.nodes_received_transactions:
    #         # print("ALREADY RECEIVEEd")
    #         return
    #     if transaction in self.transaction_list:
    #         # print("OWN TRANSACTION")
    #         return
    #
    #     # First, check if we have the approved parents of this transaction
    #     nodes_received_transactions_ids = {tx.txid for tx in self.nodes_received_transactions}
    #     own_transactions_ids = {tx.txid for tx in self.transaction_list}
    #     missing_parents = [t for t in transaction.parent_transactions if
    #                        t.txid not in self.seen_and_broadcasted_transactions and t.txid
    #                        not in nodes_received_transactions_ids and t.txid not in own_transactions_ids]
    #
    #     missing_parents_ids = [tx.txid for tx in missing_parents]
    #     if missing_parents:
    #         print("UNKNOWN PARENT", missing_parents_ids)
    #         # Request the missing parent transactions
    #         for parent_tx in missing_parents:
    #             print("ASKING FOR MISSING PARENTS")
    #             self.request_parent_transaction(parent_tx.txid, sender)
    #         # If there are missing parents, delay processing this transaction
    #         # Store it in some buffer or queue for later processing
    #         # When adding to pending
    #         self.pending_transactions.append((transaction, datetime.now()))
    #         print("ADDED TRANSACTION TO MISSING PARENT")
    #         return
    #
    #  # The delay logic  with time.sleep could be replaced with await asyncio.sleep(delay) if want to reintroduce it
    #
    #
    #     # # Validate the transaction
    #     # if not transaction.validate_transaction(DIFFICULTY=1):
    #     #     print(f"Invalid transaction {transaction.txid}")
    #     #     return
    #     nodes_received_transactions_ids_b = [tx.txid for tx in self.nodes_received_transactions]
    #     transaction_list_id = [tx.txid for tx in self.transaction_list]
    #     print(f"{self.name} list of OWN TRANSACTIONS {transaction_list_id}")
    #     print(f"{self.name} list of received transaction before appending the new transaction {nodes_received_transactions_ids_b}")
    #     self.nodes_received_transactions.append(transaction)
    #     nodes_received_transactions_ids = [tx.txid for tx in self.nodes_received_transactions]
    #     print("TOTAL Received TRANSACTIONS SO  FAR BY NODE", self.name, nodes_received_transactions_ids)
    # # self.transaction_timestamps[transaction.txid] = datetime.now()
    #     print(f"{datetime.now().strftime('%H:%M:%S.%f')} - {self.name} received Transaction ID {transaction.txid} from {sender.name} with delay {delay}")
    #     # If the transaction has no children, add it to the tips and if its a parent then remove it from tip list
    #     if not transaction.children and transaction not in self.tips:
    #         print(f" Transaction ID : {transaction.txid} do not have children, that's why added to tip of {self.name}")
    #         self.tips.append(transaction)
    #     for parent in transaction.parent_transactions:
    #         if parent in self.tips:
    #             self.tips.remove(parent)
    #             print(f" Transaction {parent.txid} is no longer a tip for {self.name}")
    #
    #     ip_ids = list(set([tip.txid for tip in self.tips]))
    #     print(f"Tips of {self.name}, {ip_ids}")
    #
    #     # Forward the transaction
    #         if peer == sender:
    #             continue
    #         delay = self.network.delay_matrix[(self, peer)]
    #         peer.receive_transaction(transaction, delay, self)
    #         # #added threading
    #         # if transaction.txid not in self.transaction_list:
    #         #     thread = threading.Thread(target=peer.receive_transaction, args=(transaction, delay, self))
    #         #     threads.append(thread)
    #         #     thread.start()
    #         #     # Wait for all threads to complete
    #         # for thread in threads:
    #         #     thread.join()
    #     #
    #     #     # Broadcast the transaction and its approved parents
    #     #     tasks.append(asyncio.create_task(self._send_transaction_to_peer(transaction, peer, delay)))
    #     #     for approved_transaction in transaction.parent_transactions:
    #     #         tasks.append(asyncio.create_task(self._send_transaction_to_peer(approved_transaction, peer, delay)))
    #     #
    #     # await asyncio.gather(*tasks)
    #
    #
    # # async def _send_transaction_to_peer(self, transaction, peer, delay):
    # #     # await asyncio.sleep(delay)
    # #     await peer.receive_transaction(transaction, self)
    #
    # def receive_transaction(self, transaction, delay, sender ): #
    #     print("ENTERING IN THE RECEIVE")
    #     # Check if the transaction has already been received
    #     if transaction.txid in self.seen_and_broadcasted_transactions:
    #         print("ALREADY SEEN")
    #         return
    #     if transaction in self.nodes_received_transactions:
    #         print("ALREADY RECEIVEEd")
    #         return
    #     if transaction in self.transaction_list:
    #         print("OWN TRANSACTION")
    #         return
    #
    #     # First, check if we have the approved parents of this transaction
    #     nodes_received_transactions_ids = {tx.txid for tx in self.nodes_received_transactions}
    #     own_transactions_ids = {tx.txid for tx in self.transaction_list}
    #     missing_parents = [t for t in transaction.parent_transactions if
    #                        t.txid not in self.seen_and_broadcasted_transactions and t.txid
    #                        not in nodes_received_transactions_ids and t.txid not in own_transactions_ids]
    #
    #     missing_parents_ids = [tx.txid for tx in missing_parents]
    #     if missing_parents:
    #         print("UNKNOWN PARENT", missing_parents_ids)
    #         # Request the missing parent transactions
    #         for parent_tx in missing_parents:
    #             print("ASKING FOR MISSING PARENTS")
    #             self.request_parent_transaction(parent_tx.txid, sender)
    #         # If there are missing parents, delay processing this transaction
    #         # Store it in some buffer or queue for later processing
    #         # When adding to pending
    #         self.pending_transactions.append((transaction, datetime.now()))
    #         print("ADDED TRANSACTION TO MISSING PARENT")
    #         return
    #
    #  # The delay logic  with time.sleep could be replaced with await asyncio.sleep(delay) if want to reintroduce it
    #
    #
    #     # # Validate the transaction
    #     # if not transaction.validate_transaction(DIFFICULTY=1):
    #     #     print(f"Invalid transaction {transaction.txid}")
    #     #     return
    #     nodes_received_transactions_ids_b = [tx.txid for tx in self.nodes_received_transactions]
    #     transaction_list_id = [tx.txid for tx in self.transaction_list]
    #     print(f"{self.name} list of OWN TRANSACTIONS {transaction_list_id}")
    #     print(f"{self.name} list of received transaction before appending the new transaction {nodes_received_transactions_ids_b}")
    #
    #     self.nodes_received_transactions.append(transaction)
    #     nodes_received_transactions_ids = [tx.txid for tx in self.nodes_received_transactions]
    #     print("TOTAL Received TRANSACTIONS SO  FAR BY NODE", self.name, nodes_received_transactions_ids)
    # # self.transaction_timestamps[transaction.txid] = datetime.now()
    #     print(f"{datetime.now().strftime('%H:%M:%S.%f')} - {self.name} received Transaction ID {transaction.txid} from {sender.name} with delay {delay}")
    #     # If the transaction has no children, add it to the tips and if its a parent then remove it from tip list
    #     if not transaction.children and transaction not in self.tips:
    #         print(
    #             f" Transaction ID : {transaction.txid} do not have children, that's why added to tip of {self.name}")
    #         self.tips.append(transaction)
    #     for parent in transaction.parent_transactions:
    #         if parent in self.tips:
    #             self.tips.remove(parent)
    #             print(f" Transaction {parent.txid} is no longer a tip for {self.name}")
    #
    #     ip_ids = list(set([tip.txid for tip in self.tips]))
    #     print(f"Tips of {self.name}, {ip_ids}")
    #
    #     # Forward the transaction
    #     self.seen_and_broadcasted_transactions.add(transaction.txid)
    #
    #     # When checking pending transactions
    #     for pending_tx, timestamp in list(self.pending_transactions):
    #         if datetime.now() - timestamp > self.MAX_PENDING_DURATION:
    #             self.pending_transactions.remove((pending_tx, timestamp))
    #
    #     # Forward the transaction to the peers of this node
    #     self.broadcast_transaction(transaction, sender)
    # def process_pending_transactions(self):
    #     while True:
    #         successfully_processed = []
    #         for transaction, timestamp in list(self.pending_transactions):
    #             success =  self.receive_transaction(transaction)
    #             if success:
    #                 successfully_processed.append((transaction, timestamp))
    #         # Remove processed transactions outside the loop
    #         for transaction, timestamp in successfully_processed:
    #             self.pending_transactions.remove((transaction, timestamp))
    #             time.sleep(self.PENDING_CHECK_INTERVAL)
    #
    # # Adding a method to request missing parent transactions
    # def request_parent_transaction(self, missing_txid, sender):
    #     if missing_txid not in self.seen_and_broadcasted_transactions:
    #         # send a request to sender or all peers to provide the missing transaction
    #         # for this example, let's just request it from the sender
    #         sender.provide_missing_transaction(missing_txid, self)
    #
    # # The corresponding method to provide the missing transaction
    # def provide_missing_transaction(self, txid, requester):
    #     # search for the transaction in the node's database and send it to the requester
    #     transaction = self.find_transaction_by_id(txid)
    #     if transaction:
    #          self._send_transaction_to_peer(transaction, requester, 0)  # no delay in this case
    #
    # def find_transaction_by_id(self, txid):
    #     for transaction in self.nodes_received_transactions and self.transaction_list:
    #         if transaction.txid == txid:
    #             return transaction
    #     return None

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
    def __init__(self, name, network, milestones_interval, is_coordinator=False):  # log_queue,
        super().__init__(name, network) #, log_queue
        self.milestones_interval = milestones_interval
        self.milestones = []
        self.transaction_list = []
        self.timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]  # Gives you time up to milliseconds
        self.timestamp += str(int(time.time() * 1e9))[-6:]  # Append the last six digits of the current nanosecond time
        self.peers = []  # Initialize an empty list to store the Coordinator's peers
        # Generate RSA key pair for the Coordinator
        self.coordinator_public_key, self.coordinator_private_key = rsa.newkeys(512)
        self.is_coordinator = is_coordinator  # Override the attribute
        # log_file = f"logs/{self.name}.log"
        # self.logger = setup_logger(self.name, log_file, log_queue)
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
            # self.logger.info(f"Genesis milestone (ID: {milestone.txid}) has been broadcasted by coordinator to all peers and validated by {valid_count} out of {len(self.peers)} peers.")
        elif isinstance(milestone, dict):  # If milestone is a dictionary (regular milestone)
            print(
                f"Milestone {milestone['index']} has been broadcasted by coordinator to all peers and validated by {valid_count} out of {len(self.peers)} peers.")
            # self.logger.info( f"Milestone {milestone['index']} has been broadcasted by coordinator to all peers and validated by {valid_count} out of {len(self.peers)} peers.")

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


