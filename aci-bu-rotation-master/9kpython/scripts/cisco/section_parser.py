from .line_parser import LineParser


class SectionParser(LineParser):

    def __init__(self, text="", key=None):
        self.text = text
        self.key = key
        self.sections = []
        self.parse_section(key)

    def parse_section(self, key=None):
        self.sections = []
        sec = False
        temp_head = ""
        temp_sec = []
        start_exp = key.get_start_key()
        end_exp = key.get_end_key()
        for i in self.text:
            if sec is False:
                match, val = key.is_match(i, start_exp)
                if match:
                    temp_head = i
                    sec = True
            elif sec is True:
                if end_exp != "":
                    match, val = key.is_match(i, end_exp)
                    if match:
                       temp_sec.append(i)
                       sec = False
                       self.set_sections(temp_head, temp_sec)
                       temp_head = ""
                       temp_sec = []
                match, val = key.is_match(i, start_exp)
                if match:
                   self.set_sections(temp_head, temp_sec)
                   temp_head = i
                   temp_sec = []
                else:
                   temp_sec.append(i)
        if temp_head != "":
            self.set_sections(temp_head, temp_sec)
        return self.get_sections()

    def set_sections(self, head="", section=""):
        self.sections.append([head, section])

    def get_sections(self):
        return self.sections

    def rerun(self, text=""):
        self.text = text
        self.parse_section(self.key)


