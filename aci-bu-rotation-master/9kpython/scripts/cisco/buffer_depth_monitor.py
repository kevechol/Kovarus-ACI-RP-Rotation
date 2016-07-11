from .nxcli import NXCLI
from .line_parser import LineParser
from .key import Key


class BufferDepthMonitor(NXCLI):

    def __init__(self):
        super(BufferDepthMonitor, self).__init__('show hardware internal '
                                                 'buffer info pkt-stats', False)


    def parse_specific(self):
        tikeys = [["\s+Total Instant Usage\s+(\d+)", "once"]]
        rikeys = [["\s+Remaining Instant Usage\s+(\d+)", "once"]]
        mckeys = [["\s+Max Cell Usage\s+(\d+)", "once"]]
        sckeys = [["\s+Switch Cell Count\s+(\d+)", "once"]]

        tikey = Key(tikeys)
        rikey = Key(rikeys)
        mckey = Key(mckeys)
        sckey = Key(sckeys)
        self.BufferMonitor = {}


        self.bufOut = self.get_output()
        lParser = LineParser(self.bufOut, tikey)
        self.BufferMonitor['Total Instant Usage'] = eval(lParser.get_data()[0][0])
        #print self.BufferMonitor['Total Instant Usage']

        lParser = LineParser(self.bufOut, rikey)
        self.BufferMonitor['Remaining Instant Usage'] = eval(lParser.get_data()[0][0])
        #print self.BufferMonitor['Remaining Instant Usage']

        lParser = LineParser(self.bufOut, mckey)
        self.BufferMonitor['Max Cell Usage'] = eval(lParser.get_data()[0][0])
        #print self.BufferMonitor['Max Cell Usage']

        lParser = LineParser(self.bufOut, sckey)
        self.BufferMonitor['Switch Cell Count'] = eval(lParser.get_data()[0][0])
        #print self.BufferMonitor['Switch Cell Count']


    def get_total_instant_usage(self):
        return self.BufferMonitor['Total Instant Usage']


    def get_remaining_instant_usage(self):
        return self.BufferMonitor['Remaining Instant Usage']


    def get_max_cell_usage(self):
        return self.BufferMonitor['Max Cell Usage']


    def get_switch_cell_count(self):
        return self.BufferMonitor['Switch Cell Count']


    def get_status(self):
        return self.BufferMonitor


    def dumps(self):
        import json
        return json.dumps(self.BufferMonitor)





