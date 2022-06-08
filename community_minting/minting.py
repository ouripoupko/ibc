class Minting:
    def __init__(self):
        self.accounts = Storage('accounts')
        self.parameters = Storage('parameters')

    def initialize(self, address, agent, contract):
        if 'community' in self.parameters:
            return
        self.parameters['community'] = {'address': address, 'agent': agent, 'contract': contract, 'balance': 0}
        self.parameters['timers'] = {'start': timestamp(), 'current': timestamp()}

    def get_balance(self, key):
        if key in self.accounts:
            return self.accounts[key]['balance']
        else:
            return 0

    def get_community(self):
        return self.parameters['community'].get_dict()

    def get_timers(self):
        return self.parameters['timers'].get_dict()

    def get_all(self):
        return self.accounts.get()

    def _propagate_over_sybils(self, _accused, _community, _from, _to):
        _more_accused = set()
        _sybils = set()
        while True:
            for _friend_key in _accused:
                if _community[_friend_key]['sybil_exposed']:
                    _sybils.add(_friend_key)
                    _friend_stamps = _community[_friend_key]['timestamps']
                    _j = 0
                    while _j < len(_friend_stamps) and elapsed_time(_friend_stamps[_j], _from) > 0:
                        _j = _j + 1
                    while _j <= len(_friend_stamps):
                        _more_accused.update(_community[_friend_key]['friends'][_j - 1])
                        if _j == len(_friend_stamps) or elapsed_time(_to, _friend_stamps[_j]) > 0:
                            break
                        _j = _j + 1
            _more_accused = _more_accused - _sybils - _accused
            _accused.difference_update(_sybils)
            if not _more_accused:
                break
            _accused.update(_more_accused)
            _more_accused = set()

    def if_part(self, _current, _last_minted, _elapsed, _contract, _community, _key, _timestamps, _member, _fines):
        _key_elapsed = elapsed_time(_timestamps[0], _current)
        if _key_elapsed > _elapsed:
            _key_elapsed = _elapsed
        _balance = _member['balance'] + _key_elapsed
        # Step 2: For every round t_2 < t do the following, as long as v has coins to pay
        for _i in range(len(_timestamps)):
            # Step 2.1: If f(v,t_2) > 0 burn coins up to f(v,t_2)/2 and pay a tax up to f(v,t_2)/2
            _pay = min(_fines[_i], _balance)
            _fines[_i] = _fines[_i] - _pay
            _balance = _balance - _pay
            self.parameters['community']['balance'] = self.parameters['community']['balance'] + _pay / 2
        _member['balance'] = _balance

    def for_loop(self, _current, _last_minted, _elapsed, _contract, _community, _key, _timestamps, _member, _i, _next_timestamp, _accused_fine, _friend_key):
        _friend_stamps = _community[_friend_key]['timestamps']
        _j = 0
        while _j < len(_friend_stamps) and elapsed_time(_friend_stamps[_j], _timestamps[_i]) > 0:
            _j = _j + 1
        _k = _j
        while _k < len(_friend_stamps) and elapsed_time(_friend_stamps[_k], _next_timestamp) > 0:
            _k = _k + 1
        _range = range(_j - 1, _k)
        _accused_slot_fine = _accused_fine / len(_range)
        _friend_fines = self.accounts[_friend_key]['fines']
        for _j in _range:
            _friend_fines[_j] = _friend_fines[_j] + _accused_slot_fine
        self.accounts[_friend_key]['fines'] = _friend_fines

    def while_loop(self, _current, _first_minted, _last_minted, _elapsed, _contract, _community, _key, _timestamps, _member, _fines, _i):
        # Step 3.2.1: fine is set as fine = 2 · m(u,t_2) + f(u,t_2)
        _last_timestamp = _timestamps[_i]
        if elapsed_time(_last_timestamp, _first_minted) > 0:
            _last_timestamp = _first_minted
        _next_timestamp = _timestamps[_i + 1]
        if elapsed_time(_next_timestamp, _last_minted) < 0:
            _next_timestamp = _last_minted
        _key_elapsed = elapsed_time(_last_timestamp, _next_timestamp)
        _fine = 2 * _key_elapsed + _fines[_i]
        _fines[_i] = 0
        _refund = min(_fine, _member['balance'])
        _fine = _fine - _refund
        _member['balance'] = _member['balance'] - _refund
        self.parameters['community']['balance'] = self.parameters['community']['balance'] + _refund / 2
        # Step 3.2.2: For each vertex v ∈ ∂_{x(v)=0}(u,t_2) set
        # f(v,t_2) = f(v,t_2) + fine / |∂_{x(v)=0}(u,t_2)|
        _accused = set(_community[_key]['friends'][_i])
        self._propagate_over_sybils(_accused, _community, _timestamps[_i], _next_timestamp)
        _accused_fine = _fine / len(_accused)  # hold your fingers that there is always someone to accuse
        for _friend_key in _accused:
            self.for_loop(_current, _last_minted, _elapsed, _contract, _community, _key, _timestamps, _member, _i, _next_timestamp, _accused_fine, _friend_key)

    def main_loop(self, _current, _first_minted, _last_minted, _elapsed, _contract, _community, _key):
        _timestamps = _community[_key]['timestamps']
        if _key not in self.accounts:
            self.accounts[_key] = {'balance': 0, 'fines': [], 'sybil': False}
        _member = self.accounts[_key]
        _fines = _member['fines']
        while len(_fines) < len(_timestamps):
            _fines.append(0)
        if not _community[_key]['sybil_exposed']:
            self.if_part(_current, _last_minted, _elapsed, _contract, _community, _key, _timestamps, _member, _fines)
        # Step 3: For every vertex u marked by the community as sybil, the protocol does the following:
        elif elapsed_time(_last_minted, _timestamps[-1]) >= 0:
            # Step 3.1: x(u) is set to 1
            _member['sybil'] = True
            # Step 3.2: For every round t_2 from 0 to t−1 do the following:
            _i = 0
            while _i < len(_timestamps) - 1 and elapsed_time(_timestamps[_i+1], _first_minted) >= 0:
                _i = _i + 1
            while _i < len(_timestamps) - 1 and elapsed_time(_timestamps[_i], _last_minted) >= 0:
                self.while_loop(_current, _first_minted, _last_minted, _elapsed, _contract, _community, _key, _timestamps, _member, _fines, _i)
                _i = _i + 1
            print('done with new sybil')
        _member['fines'] = _fines

    def update_balances(self):
        _current = timestamp()
        _first_minted = self.parameters['timers']['start']
        _last_minted = self.parameters['timers']['current']
        _elapsed = elapsed_time(_last_minted, _current)
        _contract = self.parameters['community']
        _community = Read(_contract['address'], _contract['agent'], _contract['contract'], 'get_community', [], {})
        _keys = _community.keys()
        # Step 1: On each round t, every vertex v where x(v) = 0 mints 1 coin
        for _key in _keys:
            self.main_loop(_current, _first_minted, _last_minted, _elapsed, _contract, _community, _key)
        # Step 4: modify the community graph with user interactions G_{t+1} = Transition(G,t)
        self.parameters['timers']['current'] = _current

    def transfer(self, sender, receiver, amount):
        self.update_balances()
        if sender in self.accounts and not self.accounts[sender]['sybil']:
            if self.accounts[sender]['balance'] >= amount:
                if receiver in self.accounts and not self.accounts[receiver]['sybil']:
                    self.accounts[sender]['balance'] = self.accounts[sender]['balance'] - amount
                    self.accounts[receiver]['balance'] = self.accounts[receiver]['balance'] + amount
