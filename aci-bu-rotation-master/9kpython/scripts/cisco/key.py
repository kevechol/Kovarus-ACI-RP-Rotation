import re


class Key(object):

    def __init__(self, key="", start="", end=""):
        self.key = key
        self.start = start
        self.end = end

    def is_match(self, line="", key=""):
        val = []
        match = re.search(key, line)
        if match:
            val = match.groups()
            m = True
        else:
            m = False
        return m, val

    def get_keys(self):
        return self.key

    def get_patterns(self):
        temp = []
        for i in self.key:
            temp.append(i[0])
        return temp

    def get_key_mode(self, key):
        return key[1]

    def get_start_key(self):
        return self.start

    def get_end_key(self):
        return self.end



