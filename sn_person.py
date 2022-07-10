class Person:

    def __init__(self):
        self.posts = Storage('posts')
        self.profile = Storage('profile')
        self.friends = Storage('friends')
        self.requests = Storage('requests')
        self.groups = Storage('groups')

    def create_post(self, text):
        self.posts.append({'owner': master(), 'time': timestamp(), 'text': text})

    def get_posts(self):
        return {str(key): self.posts[key].get_dict() for key in self.posts}

    def befriend(self, friendship, request_key=None):
        self.friends.append({'contract': friendship})
        if request_key:
            del self.requests[request_key]

    def get_friends(self):
        return {str(key): self.friends[key].get_dict() for key in self.friends}

    def request(self, server, name, contract):
        self.requests.append({'server': server,
                              'name': name,
                              'contract': contract})

    def get_requests(self):
        return {str(key): self.requests[key].get_dict() for key in self.requests}

    def add_group(self, contract):
        self.groups.append({'contract': contract})

    def get_groups(self):
        return {str(key): self.groups[key].get_dict() for key in self.groups}
