class Contract:
    def __init__(self, name, code):
        self.name = name
        self.code = code
        self.partners = []
        self.obj = None

    def __repr__(self):
        return str({'class': 'Contract', 'name': self.name, 'partners': self.partners})

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

    def connect(self, partner):
        self.partners.append(partner)

