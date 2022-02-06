class Voting:

    def __init__(self):
        self.ballots = Storage('topics')

    def create_ballot(self, topic, options):
        _record = {'owner': master(), 'topic': topic, 'options': options,
                   'votes': {}, 'updaters': {}}
        _last_key = "0"
        for _key in self.ballots:
            if _key > _last_key:
                _last_key = _key
        _bid = str(int(_last_key)+1).zfill(5)
        self.ballots[_bid] = _record

    def delete_ballot(self, bid):
        _bid = str(bid).zfill(5)
        del self.ballots[bid]

    def vote(self, bid, oid, updater):
        _bid = str(bid).zfill(5)
        _ballot = self.ballots[_bid]
        _votes = _ballot['votes']
        _votes[master()] = oid

        _num_opt = len(_ballot['options'])
        _count = [0] * _num_opt
        for _voter in _votes:
            _count[_votes[_voter]] += 1
        _num_vot = len(_votes)
        for _option in range(_num_opt):
            if _count[_option] * 2 > _num_vot:
                for _voter in _votes:
                    _votes[_voter] = _option

        _ballot['votes'] = _votes

    def get_ballots(self):
        return {bid: self.ballots[bid].get_dict() for bid in self.ballots}
