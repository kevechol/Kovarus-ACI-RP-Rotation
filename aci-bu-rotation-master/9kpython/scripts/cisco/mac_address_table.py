from .vlan import ShowVlan
from .nxcli import *


class MacAddressTable(object):

    def __init__(self):
        self.data = []

    def add_static_mac(self, **args):
        '''
            Add static mac address

            args:
                mac             mac address
                vlan            Vlan id
                interface       interface ethernetx/y or port-channelx
                drop            0 or 1
                auto-learn      0 or 1
        '''
        cmd = ""
        if args.has_key('mac'):
            cmd = "mac address-table static %s " % args['mac']
        else:
            raise ValueError, 'mac address not given'

        if args.has_key('vlan'):
            if ShowVlan()._check_vlan_exists(args['vlan'])==0:
                raise ValueError, 'Vlan %d does not exist' % args['vlan']
            cmd += "vlan %s " % args['vlan']
        else:
            raise ValueError, 'vlan id not given'

        if args.has_key('interface'):
            cmd += "interface %s " % args['interface']
        elif args.has_key('drop'):
            cmd += "drop "
            if args.has_key('auto-learn'):
                cmd += "auto-learn"
        else:
            raise ValueError, 'interface or drop not specified'

        cmd += " ; end" 
        return NXCLI._run_cfg(cmd)


    def remove_static_mac(self, **args):
        '''
            Remove static mac address

            args:
                mac             mac address
                vlan            Vlan id
        '''
        cmd = ""
        if args.has_key('mac'):
            cmd = "no mac address-table static %s " % args['mac']
        else:
            raise ValueError, 'mac address not given'

        if args.has_key('vlan'):
            if ShowVlan()._check_vlan_exists(args['vlan'])==0:
                raise ValueError, 'Vlan %d does not exist' % args['vlan']
            cmd += "vlan %s " % args['vlan']
        else:
            raise ValueError, 'vlan id not given'

        cmd += " ; end" 

        return NXCLI._run_cfg(cmd)


