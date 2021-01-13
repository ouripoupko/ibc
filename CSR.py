class CSR:

    def __init__(self):
        self.community = []
        self.edges = []

    def trigger_edge(self, data):
        return self.network.partners[data['id']].call(
          {'name': 'CSR', 'method': 'addEdge', 'param': {'id': self.network.me}})

    def add_edge(self, data):
        self.community.append((data['id'], self.network.me))
        return {'edges': self.edges}

#    def remove_edge(self, data):
#        return {'reply': 'addEdge called'}

    def add_member(self, data):
        self.community.append(data['id'])
        return {'community': self.community}

#    def remove_member(self, data):
#        return {'reply': 'addEdge called'}
