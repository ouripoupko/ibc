class Currency:

    def __init__(self):
        self.accounts = Storage('accounts')

    def create_account(self):
        owner = master()
        if owner not in self.accounts:
            self.accounts[owner] = {'balance': 0,
                                    'last_height': height(),
                                    'locked': []}

    def total_supply(self):
        return sum([account['balance'] for account in self.accounts])

    def balance_of(self, owner):
        balance = 0
        if owner in self.accounts:
            owner_account = self.accounts[owner]
            previous_balance = owner_account['balance']
            minted = height() - owner_account['last_height']
            balance = previous_balance + minted
        return balance

    def update_balance(self, owner):
        current_height = height()
        if owner in self.accounts:
            owner_account = self.accounts[owner]
            previous_balance = owner_account['balance']
            minted = current_height - owner_account['last_height']
            self.accounts[owner] = {'balance': previous_balance + minted,
                                    'last_height': current_height}

    def transfer(self, recipient, value):
        sender = master()
        if sender in self.accounts and recipient in self.accounts:
            self.update_balance(sender)
            sender_account = self.accounts[sender].get_dict()
            recipient_account = self.accounts[recipient].get_dict()
            if sender_account['balance'] > value:
                sender_account['balance'] -= value
                recipient_account['balance'] += value
                self.accounts[sender] = sender_account
                self.accounts[recipient] = recipient_account

    def htl_transfer(self, recipient, value, hash_code, height):
        sender = master()
        if sender in self.accounts and recipient in self.accounts:
            self.update_balance(sender)
            sender_account = self.accounts[sender].get_dict()
            if sender_account['balance'] > value:
                sender_account['balance'] -= value
                sender_account['locked'].append({'recipient': recipient,
                                                 'value': value,
                                                 'hash_code': hash_code,
                                                 'height': height()})
                self.accounts[sender] = sender_account

    def htl_approve(self, sender, hash_key):
        recipient = master()
        if sender in self.accounts and recipient in self.accounts:
            self.update_balance(recipient)
            sender_account = self.accounts[sender].get_dict()
            recipient_account = self.accounts[recipient].get_dict()
            hash_code = sha256(hash_key)
            for index, transaction in enumerate(sender_account['locked']):
                if transaction['recipient'] == recipient and transaction['hash_code'] == hash_code:
                    if transaction['height'] > height():
                        sender_account['locked'].pop(index)
                        recipient_account['balance'] += transaction['value']
                        self.accounts[sender] = sender_account
                        self.accounts[recipient] = recipient_account
                    break

    def htl_withdraw(self, recipient, hash_code):
        sender = master()
        if sender in self.accounts and recipient in self.accounts:
            self.update_balance(sender)
            sender_account = self.accounts[sender].get_dict()
            for index, transaction in enumerate(sender_account['locked']):
                if transaction['recipient'] == recipient and transaction['hash_code'] == hash_code:
                    if transaction['height'] < height():
                        sender_account['locked'].pop(index)
                        sender_account['balance'] += transaction['value']
                        self.accounts[sender] = sender_account
                    break

    def transfer_from(self, _from, to, value):
        pass

    def approve(self, spender, current_value, value):
        pass

    def allowance(self, owner, spender):
        pass
