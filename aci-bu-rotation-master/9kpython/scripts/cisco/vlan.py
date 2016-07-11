from .nxcli import NXCLI
from .key import Key
from .line_parser import LineParser


class ShowVlan(NXCLI):
    def __init__(self):
        super(ShowVlan, self).__init__('show vlan', False)

    def get_vlans(self):
        '''
            return: list of vlans
        '''
        self.vlans = []
        vKey = Key([[r"(\d+)\s+\S+\s+\S+\s+\S*", "many"]])
        vParser = LineParser(self.get_output(),vKey)
        self.vlans = vParser.get_data(vKey)
        return self.vlans

    def _check_vlan_exists(self,id):
        '''
            check if the vlan is already created
            args:
                id  Vlan id
            return: 
                0:  not created
                1:  created
        '''
        vlanExists = 0
        i = -1
        data = self.get_vlans()
        try:
            for x in data:
                if id == int(x[0]):
                    i = 0
        except ValueError:
            i = -1

        if i != -1:
            vlanExists = 1

        return vlanExists

class Vlan(object):

    def __init__(self):
        self.data = []

    def _show_cli_get(self):
        try:
            return self._shvlan
        except AttributeError:
            self._shvlan = ShowVlan()
            return self._shvlan

    def show_vlan(self):
        '''
            return: Vlans configured on the switch
        '''
        s = self._show_cli_get()
        if s.get_status() == 20:
            self.enable = False
            return None
        s.rerun()
        return s

    def create_vlan(self, id, **args):
        '''
            create the vlan

            args:
                id        Vlan id

            optional args:
                name      Vlan description
                state     Vlan state
                mode      Vlan mode
                type      Vlan type
        '''
        cmd = ""

        if id == "":
            raise ValueError, 'Vlan %d not given to create' % id

        # verify the vlan is not created already
        if ShowVlan()._check_vlan_exists(id):
            raise ValueError, 'Vlan %d already exists' % id
        else:
            cmd += "vlan %d\n" % id

        if args.has_key('name'):
            cmd += "name %s\n" % args['name']

        if args.has_key('state'):
            cmd += "state %s\n" % args['state']

        if args.has_key('mode'):
            cmd += "mode %s\n" % args['mode']

        if args.has_key('type'):
            cmd += "private-vlan %s\n" % args['type']

        cmd += "end\n"

        return NXCLI._run_cfg(cmd)

    def delete_vlan(self,id):
        '''
            delete the vlan

            args:
                id        Vlan id
        '''
        cmd = ""

        if id == "":
            raise ValueError, 'Vlan %d not given to create' % id

        # verify the vlan is not created already
        if ShowVlan()._check_vlan_exists(id):
            cmd += "no vlan %d\n" % id
        else:
            raise ValueError, 'Vlan %d  does not exist' % id

        cmd += "end\n"

        return NXCLI._run_cfg(cmd)



