class Contract:
    def __init__(self, name):
        self.name = name
        self.code = None
        self.partners = []
        self.obj = None

    def init_from_code(self, code):
        self.code = code

    def init_from_partner(self, partner):
        pass

    def run(self):
        exec(self.code)
        self.obj = locals()[self.name]()
        return {'msg': 'contract {} is running!'.format(self.name)}

    def call(self, method, param):
        m = getattr(self.obj, method)
        print(m)
        reply = m(param)
        print(reply)
        return reply

    def connect(self, address, partner_id):
        self.partners.append((partner_id, address))

    def add_partner(self, message):
        pass
#        if message['pid'] not in self.partners:
#            self.partners[message['pid']] = Partner(message['address'], message['pid'], self.me)
#        self.partners[pid].add_contract(contract)
