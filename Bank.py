class Bank:

    def __init__(self):
        self.accounts = Storage('accounts')

    def create(self):
        self.accounts[master()] = {'balance': 500}
        return {key: self.accounts[key] for key in self.accounts}

    def pay_to(self, to_pid, amount):
        _from_pid = master()
        amount = int(amount)
        if _from_pid in self.accounts and self.accounts[_from_pid]['balance'] >= amount and to_pid in self.accounts:
            self.accounts.update(_from_pid, {'balance': self.accounts[_from_pid]['balance'] - amount})
            self.accounts.update(to_pid, {'balance': self.accounts[to_pid]['balance'] + amount})
        return {key: self.accounts[key] for key in self.accounts}

    def get_accounts(self):
        return {key: self.accounts[key] for key in self.accounts}
