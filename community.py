class Community:

    def __init__(self):
        self.community = Storage('community')

    def join(self, name, friends):
        _deg = 10
        _n = len(self.community)
        _my_key = str(_n).zfill(10)
        if _n <= _deg:
            _me = {'name': name, 'friends': []}
            for _her_key in self.community:
                _member = self.community[_her_key]
                _member['friends'] = _member['friends'] + [_my_key]
                _me['friends'].append(_her_key)
            self.community[_my_key] = _me
            return
        _a = [[0 for col in range(_n+1)] for row in range(_n+1)]
        _all_keys = [key for key in self.community]
        for _i, _her_key in enumerate(_all_keys):
            _her_friends = self.community[_her_key]['friends']
            for _friend_key in _her_friends:
                if _friend_key in _all_keys:
                    _j = _all_keys.index(_friend_key)
                    _a[_i][_j] = 1
                    _a[_j][_i] = 1
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
        print(len(_a[_n]))
        if sum(_a[_n]) == _deg:
            _w = eig(_a)
            if abs(_w[-2]) < 0.6:
                _me = {'name': name, 'friends': []}
                for _pair in friends:
                    _key1 = self.community.get_last('name', _pair[0])
                    _key2 = self.community.get_last('name', _pair[1])
                    _member1 = self.community[_key1]
                    _member2 = self.community[_key2]
                    _friends1 = _member1['friends']
                    _friends2 = _member2['friends']
                    if _key1 not in _friends2 or _key2 not in _friends1:
                        print('oops')
                        print(_key1, _key2, _member1.get_dict(), _member2.get_dict())
                    _friends1.remove(_key2)
                    _friends2.remove(_key1)
                    _friends1.append(_my_key)
                    _friends2.append(_my_key)
                    _member1['friends'] = _friends1
                    _member2['friends'] = _friends2
                    _me['friends'].append(_key1)
                    _me['friends'].append(_key2)
                print(_me)
                self.community[_my_key] = _me

    def get_community(self):
        return self.community.get()
