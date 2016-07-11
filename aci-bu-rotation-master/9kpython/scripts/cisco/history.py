from collections import deque
from .nxcli import *

class History(dict):
    cmd_history = deque()
    length = 256
    def __new__(type):
        if not '__HistoryInst__' in type.__dict__:
            type.__HistoryInst__ = super(History, type).__new__(type)
            type.__HistoryInstRefCnt = 0
        type.__HistoryInstRefCnt += 1
        return type.__HistoryInst__

    def __del__(type):
        type.__HistoryInstRefCnt -= 1
        if type.__HistoryInstRefCnt <= 0:
            del type.__HistoryInst__
            del type.__HistoryInstRefCnt

    def add_command(self, command=None):
        if not isinstance(command, nxcli.NXCLI):
            raise TypeError, "Arg 'command' must be a CLI object."
        if command == None:
            raise TypeError, "Must specify arg 'command'."
        self.cmd_history.append(command)
        if len(self.cmd_history) > self.length:
            self.cmd_history.popleft()

    def get_history(self, do_print=True):
        c = []
        for h in self.cmd_history:
            c.append(h.get_command())
            if do_print:
                print h.get_command()
        return c

    def clear_history(self):
        self.cmd_history = []




