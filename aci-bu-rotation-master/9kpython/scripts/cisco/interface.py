import re,datetime
import nxos_utils
from .nxcli import *

def get_valid_port(port):
    ''' Validate and return correct port here'''
    return Interface.normalize(port)

class ShowInterface(NXCLI):
    def __init__ (self, ifname):
        # acquire the output of "show interface %ifname | xml"
        super(ShowInterface, self).__init__('show interface %s | xml' % ifname, False)

    def parse_specific(self):
        # parse the XML
        elements = self.get_xml_dom_from_cli_output (self.raw_output)
        # loop through the leaves of the XML tree and populate the dictionary
        for element in elements.getiterator():
            # if the element is a leaf
            if not element.getchildren():
                # store it in the dictionary sans the XML namespace prefix
                ret = self.key_value_xml_parser (element)
                if ret:
                    key, value = ret
                    self.__dict__[key] = value



class Interface(object):
    _pat = None
    _interfaces, _Interfaces = None, {}


    @classmethod
    def interfaces(cls, refresh=False):
        '''Returns the list of interfaces on the switch'''
        if cls._interfaces is None or refresh:
            x = nxcli('show interface | exclude "^ " | exclude "^admin state" | include " is " ')
            cls._interfaces = [i.split(' ')[0] for i in x[1].split('\n'
                ) if i ]
        return cls._interfaces


    @classmethod
    def parsed_if(cls, intf):
        if cls._pat is None:
            cls._pat = re.compile('(\D+)(\d.*)')
        m = cls._pat.match(intf)
        if m:
            return m.groups()[0].lower(), map(eval, m.groups()[1].split('/'))
        raise ValueError, 'interface "%s" is not valid' % intf


    @classmethod
    def normalize(cls, intf):
        type, dlist = cls.parsed_if(intf)
        for x in cls.interfaces():
            t, d = cls.parsed_if(x)
            if dlist == d and t.startswith(type):
                return x
        for x in cls.interfaces(True):
            t, d = cls.parsed_if(x)
            if dlist == d and t.startswith(type):
                return x
        raise ValueError, 'interface "%s" is not valid' % intf


    def __new__(cls, intf):
        name = cls.normalize(intf)
        if name not in cls._Interfaces:
            cls._Interfaces[name] = super(Interface, cls).__new__(cls)
            cls._Interfaces[name].name = name
            cls._Interfaces[name]._config = None
            cls._Interfaces[name]._cfgHistory = []
            cls._Interfaces[name].config(True)
            cls._Interfaces[name]._show_obj = ShowInterface(name)
        return cls._Interfaces[name]


    def __del__(cls):
        ''' system shared obj, dont delete '''
        pass


    def __init__(self, intf):
        self._newCfg = None


    def config(self, refresh = False):
        if self._config is None or refresh:
            s, o = nxcli('show runn interface %s' % self.name)
            if s == 0:
                self._config = o
            else:
                raise RuntimeError, \
                    'Cant extract config for interface %s\nError:\n%s\n%s' % (
                            self.name, '-' * 6, o)
        return self._config


    def show(self, key=None):
        self._show_obj.rerun ()
        if not key:
            return self._show_obj
        return getattr (self._show_obj, key)


    def _if_cfg(self, cfg):
        if self._newCfg is None:
            self._newCfg = '''configure term ; interface %s ''' % self.name
        self._newCfg += ' ; ' + cfg


    def set_mode(self, mode='access'):
        if mode.lower() not in ['access', 'trunk']:
            raise ValueError, 'switchport mode %s is unknown' % mode
        self._if_cfg('switchport mode %s' % mode)
        return self.apply_config ()


    def set_switchport(self, **kwargs):
        self._if_cfg(NXCLI._add_no_if_present('switchport', kwargs))
        return self.apply_config()


    def apply_config(self):
        newCfg = self._newCfg
        self._newCfg = None
        if newCfg:
            o,e,s = nxos_utils.runVshCmdEx(newCfg)
        else:
            return False
        if s:
            if e:
                print e
            else:
                print o
        self.config(True)
        self._cfgHistory.append((datetime.datetime.now(), newCfg))
        return s == 0


    def set_description(self, d=None):
        if d:
            self._if_cfg('description %s' % d)
        else:
            self._if_cfg('no description')
        return self.apply_config ()


    def set_state(self, s='up'):
        if s.lower() in ['up', 'no shut', 'noshut']:
            self._if_cfg('no shut')
        else:
            self._if_cfg('shut')
        return self.apply_config ()


    def set_ipaddress(self, ip_address=None, mask=None, secondary=None, delete=None):
        if delete:
            ip_cfg = "no "
        else:
            ip_cfg = ""

        if ip_address:
            if '/' in ip_address:
                addr = ip_address.split('/')
                self.ip_address = addr[0]
                self.mask = addr[1]
            elif mask:
                self.ip_address = ip_address
                self.mask = mask
            else:
                self.ip_address = ip_address

            if '.' in self.ip_address:
                ip_cfg += 'ip address ' + str(self.ip_address) 
            elif ':' in self.ip_address:
                ip_cfg += 'ipv6 address ' + str(self.ip_address)

            if self.mask:
                ip_cfg += '/' + str(self.mask)

            if secondary:
                ip_cfg += " secondary"

            self._if_cfg(ip_cfg)
        else:
            raise pexpect.ExceptionPexpect("IP Address required.")

        self.ip_address = None
        self.mask = None
        return self.apply_config()


