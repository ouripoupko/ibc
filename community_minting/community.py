class Community:

    def __init__(self):
        self.community = Storage('community')
        self.properties = Storage('properties')
        self.properties['timestamps'] = {'start': timestamp()}

    def prepare_matrix(self):
        _all_keys = [key for key in self.community if not self.community[key]['sybil_exposed']]
        _n = len(_all_keys)
        _a = [[0 for col in range(_n + 1)] for row in range(_n + 1)]
        for _i, _her_key in enumerate(_all_keys):
            _her_friends = self.community[_her_key]['friends'][-1]
            for _friend_key in _her_friends:
                if _friend_key in _all_keys:
                    _j = _all_keys.index(_friend_key)
                    _a[_i][_j] = 1
                    _a[_j][_i] = 1
        return _a, _n

    def add_new_candidate(self, _a, _n, friends):
        _all_keys = [key for key in self.community if not self.community[key]['sybil_exposed']]
        for _pair in friends:
            _key1 = self.community.get_last('name', _pair[0])
            _key2 = self.community.get_last('name', _pair[1])
            if _key1 in _all_keys and _key2 in _all_keys:
                _i = _all_keys.index(_key1)
                _j = _all_keys.index(_key2)
                if _a[_i][_j] == 1:
                    _a[_i][_j] = 0
                    _a[_j][_i] = 0
                    _a[_n][_i] = 1
                    _a[_n][_j] = 1
                    _a[_i][_n] = 1
                    _a[_j][_n] = 1

    def join(self, name, friends):
        _deg = 10
        _n = len(self.community)
        _my_key = str(_n).zfill(10)
        if _n <= _deg:
            _me = {'name': name, 'friends': [[]], 'timestamps': [self.properties['timestamps']['start']],
                   'sybil_exposed': False}
            for _her_key in self.community:
                _member = self.community[_her_key]
                _her_friends = _member['friends']
                _her_friends[0].append(_my_key)
                _member['friends'] = _her_friends
                _me['friends'][0].append(_her_key)
            self.community[_my_key] = _me
            return
        _a, _n = self.prepare_matrix()
        self.add_new_candidate(_a, _n, friends)
        if sum(_a[_n]) == _deg:
            _w = eig(_a)
            if abs(_w[-2]) < 0.6:
                _me = {'name': name, 'friends': [[]], 'timestamps': [timestamp()], 'sybil_exposed': False}
                for _pair in friends:
                    _key1 = self.community.get_last('name', _pair[0])
                    _key2 = self.community.get_last('name', _pair[1])
                    _member1 = self.community[_key1]
                    _member2 = self.community[_key2]
                    _friends1 = _member1['friends']
                    _friends2 = _member2['friends']
                    _new_set1 = _friends1[-1][:]
                    _new_set2 = _friends2[-1][:]
                    _new_set1.remove(_key2)
                    _new_set2.remove(_key1)
                    _new_set1.append(_my_key)
                    _new_set2.append(_my_key)
                    _friends1.append(_new_set1)
                    _friends2.append(_new_set2)
                    _member1['friends'] = _friends1
                    _member1['timestamps'] = _member1['timestamps'] + [timestamp()]
                    _member2['friends'] = _friends2
                    _member2['timestamps'] = _member2['timestamps'] + [timestamp()]
                    _me['friends'][0].append(_key1)
                    _me['friends'][0].append(_key2)
                self.community[_my_key] = _me

    def check_all_pairs(self, _friends, _f_of_f, _order):
        _rest_order = []
        for _pair in range(1, len(_order)):
            _first = _order[0]
            _second = _order[_pair]
            if not _friends[_first] in _f_of_f[_second] and not _friends[_second] in _f_of_f[_first]:
                _rest_list = _order[1:]
                del _rest_list[_pair-1]
                if _rest_list:
                    _rest_order = self.check_all_pairs(_friends, _f_of_f, _rest_list)
                if _rest_order or not _rest_list:
                    _rest_order = [[_order[0], _order[_pair]]] + _rest_order
                    break
        return _rest_order

    def report_sybil(self, name):
        _key = self.community.get_last('name', name)
        _member = self.community[_key]
        _friends = _member['friends'][-1]
        _f_of_f = []
        for _her_key in _friends:
            _f_of_f.append(self.community[_her_key]['friends'][-1])
            if _key not in _f_of_f[-1]:
                print(_f_of_f)
            _f_of_f[-1].remove(_key)
        _order = self.check_all_pairs(_friends, _f_of_f, list(range(len(_friends))))
        for _pair in _order:
            _f_of_f[_pair[0]].append(_friends[_pair[1]])
            _f_of_f[_pair[1]].append(_friends[_pair[0]])
        for index, _her_key in enumerate(_friends):
            _her_member = self.community[_her_key]
            _her_member['friends'] = _her_member['friends'] + [_f_of_f[index]]
            _her_member['timestamps'] = _her_member['timestamps'] + [timestamp()]
        _member['friends'] = _member['friends'] + [[]]
        _member['timestamps'] = _member['timestamps'] + [timestamp()]
        _member['sybil_exposed'] = True

    def get_community(self):
        return self.community.get()
