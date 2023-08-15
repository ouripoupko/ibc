class Community:

    def __init__(self):
        self.members = Storage('members')
        self.nominates = Storage('nominates')
        self.tasks = Storage('tasks')
        # self.parameters = Storage('parameters')['parameters']

    def get_tasks(self):
        requester = master()
        return self.tasks[requester].get_dict() if requester in self.tasks else {}

    def get_members(self):
        return {key: self.members[key].get_dict() for key in self.members}

    def get_nominates(self):
        return [key for key in self.nominates]

    def request_join(self):
        requester = master()
        if requester in self.members or requester in self.nominates:
            return False
        if len(self.members) == 0 and len(self.nominates) < 5:
            self.nominates[requester] = {}
            if len(self.nominates) == 5:
                nominates = [key for key in self.nominates]
                for key in nominates:
                    self.tasks[key] = {other: False for other in nominates if other != key}
            return True
        elif len(self.members) > 4 and len(self.tasks) == 0:
            members = [key for key in self.members]
            [r, s] = random(timestamp(), None, len(members))
            first = members[r]
            others = self.members[first]['neighbors']
            [r, s] = random(None, s, len(others))
            second = others[r]
            members.remove(first)
            members.remove(second)
            [r, s] = random(None, s, len(members))
            third = members[r]
            others = [key for key in self.members[third]['neighbors'] if key in members]
            [r, s] = random(None, s, len(others))
            fourth = others[r]
            order = [first, second, third, fourth]
            self.nominates[requester] = {'order': order}
            for key in order:
                self.tasks[key] = {requester: False}
            self.tasks[requester] = {key: False for key in order}
            return True
        return False

    def approve(self, approved):
        approver = master()
        if approver in self.tasks:
            if approved in self.tasks[approver]:
                self.tasks[approver][approved] = True
                all_approved = True
                for key in self.tasks:
                    for task in self.tasks[key]:
                        if not self.tasks[key][task]:
                            all_approved = False
                if all_approved:
                    for key in self.nominates:
                        if 'order' in self.nominates[key]:
                            order = self.nominates[key]['order']
                            for i in range(4):
                                previous = self.members[order[i]]['neighbors']
                                previous.remove(order[i+1-2*(i % 2)])
                                previous.append(key)
                                self.members[order[i]]['neighbors'] = previous
                            self.members[key] = {'neighbors': order}
                        else:
                            self.members[key] = {'neighbors': [other for other in self.tasks[key].get_dict()]}
                        del self.nominates[key]
                    for key in self.tasks:
                        del self.tasks[key]
