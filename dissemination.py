class Dissemination:
    def __init__(self, storage, contract_name, me, partners, threshold, logger):
        self.storage = storage
        collections = storage['collections']
        self.dag = collections.get_sub_collection('dag')
        self.buffer = collections.get_sub_collection('buffer')
        if 'parameters' in self.storage:
            self.parameters = self.storage['parameters']
        else:
            self.parameters = {}
        self.contract_name = contract_name
        self.me = me
        self.logger = logger
        self.partners = partners
        self.threshold = threshold

    def update_partners(self, partners):
        self.partners = partners

    def close(self):
        pass

    def record_message(self, record):
        pass

    def handle_message(self, record, initiate):
        if initiate:
            if record['agent'] == self.me:
                for partner in self.partners:
                    if partner.pid != self.me:
                        partner.disseminate(record)
                    else:
                        pass
            else:
                pass
            return [record]
        else:
            self.logger.error('I should not be here')
        return []
