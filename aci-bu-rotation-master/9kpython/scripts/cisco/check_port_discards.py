from .nxcli import NXCLI
from .interface import get_valid_port
from .key import Key
from .line_parser import LineParser



class CheckPortDiscards(NXCLI):

    def __init__(self,port):
        try:
            self._port = get_valid_port (port)
            self._fport = int  (self._port.split ('/')[-1])
        except:
            print "Invalid: '%s'" % (port)
            raise
        else:
            super(CheckPortDiscards, self).__init__(
                    'show interface ' + self._port, False)

    def parse_specific(self):
        keys = [['(\d+) input discard', 'once']]
        keys1 = [['(\d+) seconds input rate', 'once']]
        #keys2 = [['([a-zA-Z0-9]+[ \]+[a-zA-Z0-9]+)(\d+)', 'many']]
        keys2 = [["(\w+ \w+)\s+(\d+)\s+(\d+)","many"]]
        discardKey = Key(keys)
        counterKey = Key(keys2)

        #frontPortPat = r'eth\d\/(\d+)'
        #frontPortPat = r'eth\d\/(\d+)|ethernet\d\/(\d+)'
        #frontPortPatc = re.compile(frontPortPat)
        #frontPort = frontPortPatc.match(port).group(1)
        #print frontPort

        #intOutput = NXCLI('show interface ' + port)
        self.intOut = self.get_output()
        lParser = LineParser(self.intOut,discardKey)
        (discards,) = lParser.get_datum(keys[0][0])
        #print discards

        if (int(discards) > 0):
            print "Non zero discards"
            dropOutput = \
            NXCLI('show hardware internal interface ' +
            'indiscard-stats front-port %d' % self._fport)
            self.dropOut = dropOutput.get_output()
            lParser1 = LineParser(self.dropOut,counterKey)
            d1 = lParser1.get_data()
            for x, y, z in d1:
                if int(y) > 0 :
                    print 'Discard reason: ' + x + ' ' + y
            #print lParser1.get_data()
        else:
            print "zero discards"


