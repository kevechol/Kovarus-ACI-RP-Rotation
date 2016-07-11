import re
from .nxcli import *
import nxos_utils

###############################################################################
#  Feature Classes
#
class FeatureFactory(type):
    '''
        _classes    are a dictionary of feature (key)name    to (val) classes 
        _singletons are a dictionary of feature (key)classes to (val) objects 
        _classes    are populated when the module is loaded
        _singletons are on demand when feature objects are instantiated.
       TBD.. determine if we can replace _classes with built in __subclasses__
    '''
    _singletons = {}
    _classes = {}

    #@classmethod
    def get(cls, name):
        '''
           get feature object, create if necessary
           params:  feature name
           returns: feature object
        '''
        if cls._classes.has_key(name):
            c = cls._classes[name]
        else:
            raise RuntimeError, "unrecognized feature: " + name            
        if not cls._singletons.has_key(c):
                o = c()
                
        return cls._singletons[c]

    #@classmethod
    def getFeatureClass(cls, name):
        '''
           get feaure class from name
           params:  feature name
           returns: feature class
        '''
        return cls._classes[name]

    #@classmethod
    def allSupportedFeatures(cls):
        '''
           get list of all supported features.
           TODO:  How do we determine supported features between different
                 platforms 3k / 5k.  At build time or runtime TBD.
           params:  none
           returns: list of feature names
        '''
        return cls._classes.keys()

    #@classmethod
    def isFeatureSupported(cls, feature):
        '''
           check if a given feature is supported on this platform.
           TODO:  How do we determine supported features between different
                 platforms 3k / 5k.  At build time or runtime TBD.
           params:  feature name
           returns: boolean
        '''
        # TBD
        pass


class ShFeature (NXCLI):
    '''
        Runs and parses 'show feature'
    '''
    def __init__ (self):
        super (ShFeature, self).__init__ ('show feature', False)

    def feature (self, name, instance = 0):
        self._state = dict()
        key =  '(\S+)\s+(\d+)\s+(\S.*)$'
        for line in self.processed_output:
            match = re.search(key, line)
            if match and match.group(1) == name:
                if instance > 0:
                    if int(match.group(2)) == instance:
                        self._state = match.group(3)
                        return self._state
                else:
                    self._state[match.group(2)] = match.group(3)
        return self._state


class Feature(object):
    ''' A nxos feature base class.
    '''
    __metaclass__ = FeatureFactory


    def __new__(typ, *args, **kwargs):
        '''Create Single instance of object per derived class'''
        # check whether we have an instance
        if not Feature._singletons.has_key(typ):
            new_feature = object.__new__(typ, *args, **kwargs)
            Feature._singletons[typ] = new_feature
        return Feature._singletons[typ]


    def _run_cfg (self, cmds):
        return NXCLI._run_cfg (cmds)

    def name(self):
        '''feature name - as used in "config terminal"'''
        return self._name


    def show_name(self):
        # may remove this... it was useful for testing.  but may provide 
        # confusion for no actual purpose.
        '''feature name - as seen in "show feature"'''
        if self.__dict__.has_key('_show_name'):
            return self._show_name
        else:
            return self._name


    def state(self, instance = 0):
        '''return state  (or states if multiple instances) of feature
        '''
        # call "show feature".  loop through output, capture status
        if hasattr(self, "_show_name"):
            show_name = self._show_name
        else:
            show_name = self._name
        return ShFeature().feature(show_name, instance)


    def enable (self, **kwargs):
        '''
            start feature
            args:
              no=True         Stops the tacacs
            return: True on success
        '''
        if kwargs.has_key('no') and kwargs['no'] is True:
            confStr = "configure terminal ; no feature " + self._name
        else:
            confStr = "configure terminal ; feature " + self._name
        error, output = nxcli(confStr)
        if error:
            print error
            return False
        return True


    def disable(self):
        '''disable feature'''
        return self.enable(no = 1) 


    def is_enabled(self):
        '''
            Returns True if the feature is enabled.
        '''
        statetable = self.state()
        firststate = statetable.get( statetable.keys()[0] )
        key =  '^enabled.*$'
        match = re.search(key, str(firststate))
        if match:
            return True
        return False




def _create_feature_class(name, doc, show_name = None):
    if show_name != None:
        c = type(name, (Feature,), { '__doc__' : doc, '_name' : name, '_show_name' : show_name })
    else:
        c = type(name, (Feature,), { '__doc__' : doc, '_name' : name })

    import cisco
    setattr(cisco, name, c)
    Feature._classes[name] = c

from .bgp import BGPSession
from .ssh import SSH
from .tacacs import Tacacs
# For now all features are simple derived classes using the feature template.
# as functionality is implemented, non-template derived class will replace
# the template versions of the same.
_create_feature_class('bfd', 'Enable/Disable Bidirectional Flow Detection (BFD)', )
#_create_feature_class('bgp', 'Enable/Disable Border Gateway Protocol (BGP)',)
Feature._classes['bgp'] = BGPSession
_create_feature_class('dhcp', 'Enable/Disable DHCP Snooping',)
_create_feature_class('eigrp', 'Enable/Disable Enhanced Interior Gateway Routing Protocol (EIGRP)',)
_create_feature_class('hsrp', 'Enable/Disable Hot Standby Router Protocol (HSRP)',)
_create_feature_class('interface-vlan', 'Enable/Disable interface vlan',)
_create_feature_class('isis', 'Enable/Disable ISIS',)
_create_feature_class('lacp', 'Enable/Disable LACP',)
_create_feature_class('ldap', 'Enable/Disable LDAP',)
_create_feature_class('lldp', 'Enable/Disable LLDP',)
_create_feature_class('msdp', 'Enable/Disable Multicast Source Discovery Protocol (MSDP)',)
_create_feature_class('ntp', 'Enable/Disable NTP',)
_create_feature_class('nv', 'Enable/Disable NV',)
_create_feature_class('nxapi', 'Enable/Disable nxAPI',)
_create_feature_class('ospf', 'Enable/Disable Open Shortest Path First Protocol (OSPF)',)
_create_feature_class('ospfv3', 'Enable/Disable Open Shortest Path First Version 3 Protocol (OSPFv3)',)
_create_feature_class('password', 'Enable/Disable password',)
_create_feature_class('pim', 'Enable/Disable Protocol Independent Multicast (PIM)',)
#  pim6 is not currently supported on 3k, even though vsh "feature ?"  shows
#       it as a valid feature
#_create_feature_class('pim6', 'Enable/Disable Protocol Independent Multicast (PIM) for IPv6',)
#  poe is not currently supported on 3k, even though vsh "feature ?"  shows
#       it as a valid feature
#_create_feature_class('poe', 'Enable/Disable PoE',)
_create_feature_class('private-vlan', 'Enable/Disable private-vlan',)
#  privilege is confused or broken at the moment.
_create_feature_class('privilege', 'Enable/Disable IOS type privilege level support',)
#_create_feature_class('ptp', 'Enable/Disable PTP',)
_create_feature_class('rip', 'Enable/Disable Routing Information Protocol (RIP)',)
_create_feature_class('scheduler', 'Enable/Disable scheduler',)
_create_feature_class('scp-server', 'Enable/Disable scp server',)
_create_feature_class('sftp-server', 'Enable/Disable sftp server',)
Feature._classes['ssh'] = SSH
Feature._classes['tacacs+'] = Tacacs
_create_feature_class('telnet', 'Enable/Disable telnet', 'telnetServer')
_create_feature_class('udld', 'Enable/Disable UDLD',)
_create_feature_class('vn-segment-vlan-based', 'Enable/Disable VLAN based VN segment',)
_create_feature_class('vpc', 'Enable/Disable VPC (Virtual Port Channel)',)
_create_feature_class('vrrp', 'Enable/Disable Virtual Router Redundancy Protocol (VRRP)',)
_create_feature_class('vtp', 'Enable/Disable Vlan Trunking Protocol (VTP)',)

