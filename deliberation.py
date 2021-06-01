class Deliberation:

    def __init__(self):
        self.statements = Storage('statements')
        if parameters.get('topics') is None:
            parameters.update({'topics': []})

    def create_statement(self, parents, text, tags):
        if not parents:
            parents = []
        _parents_ref = [{'ref': ref, 'tags': [], 'owner': master()} for ref in parents]
        _record = {'parents': _parents_ref, 'kids': [],
                   'owner': master(), 'text': text, 'tags': tags,
                   'scoring': [], 'ranking_kids': []}
        _sid = self.statements.append(_record)
        for _ref in parents:
            self.statements.update_append(_ref, 'kids', {'ref': _sid, 'tags': [], 'owner': master()})
        if not parents:
            parameters.append('topics', _sid)

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
        self.statements.update_append(sid, 'ranking_kids', {'owner': master(), 'order': order})

    def delete_ranking(self, sid):
        _ranking = self.statements[sid]['ranking_kids']
        _owner = master()
        _new_ranking = [entry for entry in _ranking if entry['owner'] != _owner]
        self.statements.update(sid, {'ranking_kids': _new_ranking})

    def get_statement_dynasty(self, parent, levels):
        _statements_dict = self.get_statements(parent)
        _current_kids_list = list(_statements_dict.keys())
        for _level in range(levels):
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
            _kids = parameters.get('topics')
        return {kid: self.statements[kid] for kid in _kids}

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

    def get_aggregated_ranking(self, sid):
        ranking = self.statements[sid]['ranking']
        kids = [ref['ref'] for ref in self.statements[sid]['kids']]
        n = len(kids)
        indexes = {ref: index for index, ref in enumerate(kids)}
        sum_matrix = [[0 for i in range(n)] for j in range[n]]
        for order in ranking:
            unordered = set(kids)
            for above in order:
                for below in unordered:
                    above_index = indexes[above]
                    below_index = indexes[below]
                    sum_matrix[above_index][below_index] += 1
                unordered.remove(above)
        total_order = []
        for index in range(n):
            first_above = 0
            found = False
            while len(total_order) > first_above and not found:
                compare_list = total_order[first_above]
                if not isinstance(compare_list, list):
                    compare_list = [compare_list]
                for compare in compare_list:
                    if sum_matrix[index][compare] >= sum_matrix[compare][index]:
                        found = True
                        break
                first_above += 1
            last_below = len(total_order)
            while last_below > 0:
                last_below -= 1
                compare_list = total_order[first_above]
                if not isinstance(compare_list, list):
                    compare_list = [compare_list]
                for compare in compare_list:
                    if sum_matrix[index][compare] <= sum_matrix[compare][index]:
                        found = True
                        break
            if last_below >= first_above:
                value = []
                for inner_index in range(first_above, last_below+1):
                    if isinstance(total_order[inner_index], list):
                        value.extend(total_order[inner_index])
                    else:
                        value.append(total_order[inner_index])
                    del total_order[first_above:last_below+1]
                value.append(index)
            else:
                value = index
            total_order.insert(first_above, value)
        return total_order
