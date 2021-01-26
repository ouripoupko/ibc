class Bank:

    def __init__(self):
        self.accounts = {}

    def __repr__(self):
        return str(self.accounts)

    def create(self, data):
        self.accounts[data['pid']] = 500

    def pay(self, data):
        amount = int(data['amount'])
        if self.accounts.get(data['from_pid']) and self.accounts[data['from_pid']] >= amount:
            self.accounts[data['from_pid']] = self.accounts[data['from_pid']] - amount
            if not self.accounts.get(data['to_pid']):
                self.create({'pid': data['to_pid']})
            self.accounts[data['to_pid']] = self.accounts[data['to_pid']] + amount
