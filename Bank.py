class Bank:

    def __init__(self):
        self.accounts = {}

    def __repr__(self):
        return str(self.accounts)

    def create(self, pid):
        self.accounts[pid] = 500

    def pay(self, from_pid, to_pid, amount):
        # amount = int(amount)
        if self.accounts.get(from_pid) and self.accounts[from_pid] >= amount:
            self.accounts[from_pid] = self.accounts[from_pid] - amount
            if not self.accounts.get(to_pid):
                self.create(to_pid)
            self.accounts[to_pid] = self.accounts[to_pid] + amount
