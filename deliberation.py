class Deliberation:

    def __init__(self):
        self.statements = Storage('statements')
        self.parameters = Storage('parameters')['parameters']
        if not self.parameters.exists():
            self.parameters['topics'] = []
            self.parameters['counter'] = 1

    def create_statement(self, parents, text, tags):
        if not parents:
            parents = []
        _parents_ref = [{'ref': ref, 'tags': [], 'owner': master()} for ref in parents]
        _counter = self.parameters['counter']
        _record = {'parents': _parents_ref, 'kids': [],
                   'owner': master(), 'text': text, 'tags': tags,
                   'scoring': [], 'ranking_kids': {}, 'counter': _counter}
        _sid = str(_counter).zfill(15)
        _counter = _counter + 1
        self.statements[_sid] = _record
        for _ref in parents:
            _kids = self.statements[_ref]['kids']
            _kids.append({'ref': _sid, 'tags': [], 'owner': master()})
            self.statements[_ref] = {'kids': _kids, 'counter': _counter}
            _counter = _counter + 1
        self.parameters['counter'] = _counter
        if not parents:
            _topics = self.parameters['topics']
            _topics.append(_sid)
            self.parameters['topics'] = _topics

    def update_statement(self, sid, mode,
                         parents, kids, text, tags):
        _record = self.statements[sid]
        if text is not None:
            _record['text'] = text
        if mode == 'replace':
            if parents is not None:
                for _parent_id in _record['parents']:
                    _parent = self.statements[_parent_id]
                    _parent_kids = [ref for ref in _parent['kids'] if ref['ref'] != sid]
                    self.statements.update(_parent_id, {'kids': _parent_kids})
                _record['parents'] = parents
            if kids is not None:
                for _kid_id in _record['kids']:
                    _kid = self.statements[_kid_id]
                    _kid_parents = [ref for ref in _kid['parents'] if ref['ref'] != sid]
                    self.statements.update(_kid_id, {'parents': _kid_parents})
                _record['kids'] = kids
            if tags is not None:
                _record['tags'] = tags
        elif mode == 'append':
            if parents is not None:
                _record['parents'].append(parents)
            if kids is not None:
                _record['kids'].append(kids)
            if tags is not None:
                _record['tags'].append(tags)
        if parents is not None:
            for _parent_id in parents:
                self.statements.update_append(_parent_id, 'kids', sid)
        if kids is not None:
            for _kid_id in kids:
                self.statements.update(_kid_id, 'parents', _kid_parents)
        self.statements.update(sid, _record)

    def delete_statement(self, sid):
        del self.statements[sid]

    def set_scoring(self, sid, score_type, value):
        self.statements.update_append(sid, 'scoring', {'owner': master(), 'type': score_type, 'value': value})

    def delete_scoring(self, sid, score_type):
        _scoring = self.statements[sid]['scoring']
        _owner = master()
        _new_scoring = [score for score in _scoring if score['owner'] != _owner or score['type'] != score_type]
        self.statements.update(sid, {'scoring': _new_scoring})

    def set_ranking(self, sid, order):
        _counter = self.parameters['counter']
        self.parameters['counter'] = _counter + 1
        self.statements[sid] = {f'ranking_kids.{master()}': order, 'counter': _counter}

    def delete_ranking(self, sid):
        _ranking = self.statements[sid]['ranking_kids']
        _owner = master()
        _new_ranking = {key: value for key, value in _ranking.entries() if key != _owner}
        self.statements.update(sid, {'ranking_kids': _new_ranking})

    def get_statement_dynasty(self, parent, levels):
        _statements_dict = self.get_statements(parent)
        _current_kids_list = list(_statements_dict.keys())
        for _level in range(levels-1):
            _next_level_kids = dict()
            for _kid in _current_kids_list:
                _next_level_kids.update(self.get_statements(_kid))
            _current_kids_list = list(_next_level_kids.keys())
            _statements_dict.update(_next_level_kids)
        return _statements_dict

    def get_statements(self, parent):
        if parent:
            _kids = [kid['ref'] for kid in self.statements[parent]['kids']]
        else:
            _kids = self.parameters['topics']
        return {kid: self.statements[kid].get_dict() for kid in _kids}

    def get_updates(self, counter):
        return self.statements.get('counter', '>', counter)

    def get_average_scoring(self, sid, score_type):
        scoring = self.statements[sid]['scoring']
        data = [score['value'] for score in scoring if score['type'] == score_type]
        return sum(data)/len(data) if data else 0

    def get_median_scoring(self, sid, score_type):
        scoring = self.statements[sid]['scoring']
        data = [score['value'] for score in scoring if score['type'] == score_type]
        data.sort()
        data_len = len(data)
        index = (data_len - 1) // 2
        return data[index] if data_len % 2 else (data[index] + data[index + 1]) / 2.0
