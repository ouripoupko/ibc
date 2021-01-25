class Bank:

    def __init__(self):
        self.accounts = {}

    def create(self, data):
        self.accounts[data['pid']] = 500

    def pay(self, data):
        if self.accounts.get(data['from_pid']) and self.accounts[data['from_pid']] >= data['amount']:
            self.accounts[data['from_pid']] = self.accounts[data['from_pid']] - data['amount']
            if not self.accounts.get(data['to_pid']):
                self.create(data['to_pid'])
            self.accounts[data['to_pid']] = self.accounts[data['to_pid']] + data['amount']
