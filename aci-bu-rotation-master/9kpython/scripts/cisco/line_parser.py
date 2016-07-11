import re


class LineParser(object):

    def __init__(self, text="", key=""):
        self.text = text
        self.val = []
        self.key = key
        self.parse_line(self.key)

    def parse_line(self, key=""):
        self.val = {}
        keys = key.get_keys()
        for j in range(len(keys)):
            temp_list = []
            if key.get_key_mode(keys[j]) == "many":
                for i in range(len(self.text)):
                    match, val = key.is_match(self.text[i], keys[j][0])
                    if match:
                        temp_list.append(val)

            elif key.get_key_mode(keys[j]) == "once":
                for i in range(len(self.text)):
                    match, val = key.is_match(self.text[i], keys[j][0])
                    if match:
                        temp_list.append(val)
                        break
            self.val[keys[j][0]] = temp_list
        return self.val

    def get_datum(self, index=""):
        if len(self.key.get_keys()) == 1:
            return self.val[self.key.get_keys()[0][0]][0]
        return self.val[index][0]

    def get_data(self, index=""):
        if len(self.key.get_keys()) == 1:
            return self.val[self.key.get_keys()[0][0]]
        return self.val[index]

    def rerun(self, text=""):
        self.text = text
        parse_line(self.key)

    def get_val(self):
        return self.val



