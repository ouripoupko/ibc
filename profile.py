class Profile:

    def __init__(self):
        self.profile = Storage('profile')['profile']

    def get_profile(self):
        return self.profile.get_dict()

    def set_value(self, key, value):
        self.profile[key] = value;

    def get_value(self, key):
        return self.profile[key]
