class Person:

    def __init__(self):
        self.posts = Storage('posts')

    def create_post(self, text):
        self.posts.append({'owner': master(), 'time': timestamp(), 'text': text})

    def get_posts(self):
        return {str(key): self.posts[key].get_dict() for key in self.posts}
