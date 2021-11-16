class Person:

    def __init__(self):
        self.posts = Storage('posts')
        self.profile = Storage('profile')
        self.friends = Storage('friends')
        self.groups = Storage('groups')

    def create_post(self, text):
        self.posts.append({'text': text})

    def get_posts(self):
        return {str(key): self.posts[key].get_dict() for key in self.posts}

    def befriend(self, friendship):
        self.friends.append({'contract': friendship})
