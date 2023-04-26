class Community:

    def __init__(self):
        self.members = Storage('members')
        # self.parameters = Storage('parameters')['parameters']

    def get_tasks(self):
        return ['Alice', 'Bob', 'Carol']

    def get_members(self):
        return ['my', 'you', 'everybody', 'nobody']