from collections import deque
import time
import rsa
from hashlib import sha256
from datetime import datetime
import hashlib
import sys

class Transaction:
    def __init__(self, txid, parent_txids, node, data=None):
        self.txid = txid
        self.parent_txids = parent_txids
        self.children = []
        self.parent_transactions = []
        self.weight = 1
        self.accumulative_weight = 1
        self.branch_weight = 0
        self.signature = None
        self.data = data
        self.timestamp = datetime.now()
        self.node = node if node else None
        self.is_confirmed = False  #Transaction confirmation check
        self.batch_num = None  # New attribute to store the batch number
        self.nonce = 0
        self.difficulty = 1

    def __str__(self):

        return f"Transaction(ID: {self.txid}, Node: {self.node.name}, Timestamp: {self.timestamp}, Parents: {self.parent_txids})"

    def confirm(self):
        self.is_confirmed = True

    def get_data_to_sign(self):
        data_hash = sha256(self.data.encode()).hexdigest()
        return f'{self.txid}{self.timestamp}{self.parent_txids}{data_hash}'.encode()

    def validate_transaction(self, DIFFICULTY):
        if self.node is None:
            return False
            print("Double spending detected in parent transactions!")
            return False
        if not self.verify_proof_of_work(DIFFICULTY):
            print("Invalid proof of work!")
            return False
        try:
            rsa.verify(
                self.get_data_to_sign(),
                self.signature,
                self.node.public_key
            )
            return True
        except rsa.VerificationError:
            return False

    def update_accumulative_weight(self):
        self.accumulative_weight = self.weight
        for child in self.children:
            child.update_accumulative_weight()
            self.accumulative_weight += child.accumulative_weight
        return self.accumulative_weight

    def get_all_parents(self):
        parents = []
        queue = deque(self.parent_transactions)
        while queue:
            parent = queue.popleft()
            if parent not in parents:
                parents.append(parent)
                queue.extend(parent.parent_transactions)
        return parents

    def update_branch_weight(self):
        self.branch_weight = sum(parent.accumulative_weight for parent in self.get_all_parents())

    def verify_proof_of_work(self, DIFFICULTY):
        # create message using transaction data and nonce
        message = self.get_data_to_sign() + str(self.nonce).encode()

        # compute hash
        hash_result = hashlib.sha256(message).hexdigest()

        # check whether the hash has the required number of leading zeros
        prefix = '0' * DIFFICULTY
        return hash_result.startswith(prefix)
    def get_parents_until_N(self, N_transactions):
        """Get all parent transactions up to N"""
        if not self.parent_transactions or self in N_transactions:
            return []

        parents = []
        for parent in self.parent_transactions:
            parents.append(parent)
            parents.extend(parent.get_parents_until_N(N_transactions))
        return parents


