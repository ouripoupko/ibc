class Contract:
    def __init__(self, name, code):
        self.name = name
        self.code = code
        self.partners = []
        self.obj = None

    def run(self, network):
        exec(self.code)
        self.obj = locals()[self.name](network)
        return {'msg': 'contract {} is running!'.format(self.name)}

    def call(self, method, param):
        m = getattr(self.obj, method)
        print(m)
        reply = m(param)
        print(reply)
        return reply

    def connect(self, address, partner_id):
        self.partners.append((partner_id, address))
