# The Currency contract maintains a list of accounts for members of the Community contract
#   an external clock triggers currency minting
#   on an external event of Sybil exposing the contract punishes the neighbours of the Sybils
class Currency:
    def __init__(self):
        # Storage is the digital agent interface to the database
        self.accounts = Storage('accounts')
        # parameters is the digital agent interface for persistent parameters
        if parameters.get('community') is None:
            parameters.update({'community': None,
                               'tax_collected': 0,
                               'timestamps': []})

    # the contract is initialized by supplying an external community contract
    def initialize(self, community):
        parameters.update({'community': community})

    # the community adds members manually
    def add_member(self, member):
        community = parameters.get('community')
        if community is None:
            # contract not initialized yet
            return
        if member in self.accounts:
            # skip if member already exists
            return
        if member in community:
            # initialize member's record
            record = {'exposed': False, 'balance': 0, 'fine': []}
            self.accounts[member] = record

    # assume an external mechanism for agent identification
    def check_approvals(self, approvals):
        approval_count = 0
        for approval in approvals:
            if approval in self.accounts:
                approval_count += 1
        # if majority approves transaction is accepted
        if 2*approval_count > len(self.accounts):
            return True
        return False

    # members report a Sybil, pending majority approval
    def report_sybil(self, member, approvals):
        community = parameters.get('community')
        if community is None:
            # contract not initialized yet
            return
        if self.check_approvals(approvals):
            self.accounts.update(member, {'exposed': True})
            # calculate fine
            fine_vector = self.accounts[member]['fine']
            timestamps = parameters.get('timestamps')
            for index, value in enumerate(fine_vector):
                # for each time unit the fine is twice the amount minted, plus unpaid fine
                fine = 2 + value
                # find non exposed neighbours
                candidates = [member]
                non_exposed = []
                exposed = []
                while candidates:
                    new_candidates = []
                    for candidate in candidates:
                        if candidate in exposed or\
                           candidate in non_exposed:
                            continue
                        if self.accounts[candidate]['exposed']:
                            new_candidates.append(community.get_neighbors(candidate, timestamps[index]))
                            exposed.append(candidate)
                        else:
                            non_exposed.append(candidate)
                    candidates = new_candidates
                # divide the fine between the non_exposed neighbors
                if non_exposed:
                    fine = fine/len(non_exposed)
                for neighbor in non_exposed:
                    fine_vector = self.accounts[neighbor]['fine']
                    fine_vector[index] += fine
                    self.accounts.update(neighbor, 'fine', fine_vector)

    # members report ceased members, pending majority approval
    def report_dead(self, member, approvals):
        if parameters.get('community') is None:
            # contract not initialized yet
            return
        if self.check_approvals(approvals):
            del self.accounts[member]

    # an external clock triggers minting
    def tick(self, timestamp):
        if parameters.get('community') is None:
            # contract not initialized yet
            return
        parameters.append('timestamps', timestamp)
        for member in self.accounts:
            if self.accounts[member]['exposed']:
                # exposed Sybils don't mint
                continue
            # at most one coin is minted per clock tick
            minted = 1
            fine_vector = self.accounts[member]['fine']
            # check for induced fine
            for index, value in enumerate(fine_vector):
                payment = min(minted, value)
                parameters.update_increment('tax_collected', payment)
                fine_vector[index] -= payment
                minted -= payment
                if minted == 0:
                    break
            # add to balance what is left after paying the fine
            self.accounts.update_increment(member, 'balance', minted)
            self.accounts.update(member, 'fine', fine_vector)
