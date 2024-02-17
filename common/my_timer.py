import time
from threading import Lock

class Timer:
    def __init__(self):
        self.start = None
        self.accumulate = 0.0
        self.count = 0

class Timers:
    def __init__(self):
        self.timers : dict[str, Timer] = {}
        self.lock = Lock()

    def start(self, name):
        with self.lock:
            if name not in self.timers:
                self.timers[name] = Timer()
            self.timers[name].start = time.time()

    def stop(self, name):
        with self.lock:
            self.timers[name].accumulate += time.time() - self.timers[name].start
            self.timers[name].count += 1

    def report(self):
        for name in self.timers:
            print(name + ' time ' + str(self.timers[name].accumulate) + ' count ' + str(self.timers[name].count))