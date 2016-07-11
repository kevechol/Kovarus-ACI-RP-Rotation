import re

from .feature import Feature
from .vrf import VRF
from .cisco_secret import CiscoSecret
from .nxcli import *
import nxos_utils


class OSPFSession(Feature):
    '''
    Use this class to configure the OSPF feature.
    '''

    def __init__(self, Instance=None, vrf='default'):
        self._name = 'ospf'
        if Instance == None:
            raise ValueError, 'Instance Name is Null.' 
        self.Instance = Instance
        self.OSPFInterface.Instance = self.Instance
        self.set_vrf(vrf)


    def _run_cfg_at_router_ospf_level(self, cmds):
        '''
        Run the given list of commands at router ospf config level.

        Arguments:
        cmds: List of commands to be configured at router ospf config level.

        Returns: True on success
        '''

        string = 'router ospf %s' % self.Instance
        if self.vrf.get_name() != 'default':
            if not self.vrf.exists():
                self.vrf.create()
            string += ' ; vrf %s' % self.vrf.get_name()
        string += ' ; %s' % cmds
        return NXCLI._run_cfg(string)


    def set_Instance(self, Instance):
        self.Instance = Instance


    def set_vrf(self, vrf):
        '''
        Set the VRF (Virtual Routing and Forwarding) context for subsequent API
        calls on this OSPFSession object. Any configuration done on this 
        OSPFSession object will be applied to this VRF.
        
        Arguments:
            vrf: VRF name (string) or the VRF ID (int).

        Returns: Nothing
        '''

        if type(vrf) in [int, str]:
            self.vrf = VRF(vrf)
        elif isinstance(vrf, VRF):
            self.vrf = vrf
        else:
            raise ValueError, ('Invalid argument type for vrf, acceptable types'
                    ' are VRF, int and str')


    def start(self):
        '''
        Arguments: None

        Returns: True on success

        '''

        if self.is_shutdown():
            return self._run_cfg_at_router_ospf_level('no shutdown')

        if not self.is_enabled():
            self.enable()

        return self._run_cfg_at_router_ospf_level('')


    def shutdown(self):
        '''
        Shutdown the OSPF routing process.  All existing OSPF configurations will 
        be preserved.

        Arguments: None

        Returns: True on success

        '''

        return self._run_cfg_at_router_ospf_level('shutdown')


    def is_shutdown(self):
        '''
        Check if the OSPF routing process is shutdown.

        Arguments: None

        Returns: 
            True if the OSPF process is enabled and shutdown.
            False if the OSPF process is running or if OSPF is not enabled.

        '''

        if self.is_enabled():
            output = nxos_utils.cli_ex('show run ospf | include shutdown')
            rows = output.split('\n')
            for row in rows:
                if row.strip() == 'shutdown':
                    return True
        return False


    def cfg_router_id(self, router_id, **kwargs):
        '''
        Specify the IP address to use as router-id.  To remove this
        configuration set the optional 'no' argument to True.

        Arguments:
            router_id: A string in dotted quad format ('A.B.C.D') representing
                the IP Address of the router.

        Optional Arguments:
            no: A boolean, set to True to remove the router-id.

        Returns: True on success

        '''

        cmd = NXCLI._add_no_if_present(NXCLI._read_arg(router_id, 'router_id',
            'router-id %', {str: 'socket.inet_aton(router_id)'}), kwargs)
        return self._run_cfg_at_router_ospf_level(cmd)


    def cfg_distance(self, dist, **kwargs):
        '''
        Configure administrative distance for this OSPFv2 instance.
        To set the distances back to the default set the optional 'no' argument
        to True.

        Arguments:
            dist: Distance for ospf routes, an integer ranging from 1 to
                255.

        Optional Arguments:
            no: Set to True to set distances back to the default values.

        Returns: True on success

        '''

        cmd = NXCLI._add_no_if_present('distance', kwargs)
        cmd += NXCLI._read_arg(dist, 'dist', ' %', {int:
            'dist >= 1 and dist <= 255'})

        return self._run_cfg_at_router_ospf_level(cmd)


    def log_adjacency_changes(self, **kwargs):
        '''
        Log a message for neighbor up/down event. To disable this behavior set
        the optional 'no' argument to True.

        Optional Arguments:
            no: A boolean, set to True to disable this feature.

        Returns: True on success

        '''

        cmd = NXCLI._add_no_if_present('log-adjacency-changes', kwargs)
        return self._run_cfg_at_router_ospf_level(cmd)

    
    def cfg_maximum_paths(self, max, **kwargs):
        '''
        Configures the maximum number of parallel routes that the OSPF
        can support.  To restore the default number of parallel
        routes, set the optional 'no' argument to True.

        Arguments:
            max: Maximum number of parallel routes that an IP routing protocol
                installs in a routing table. The range is from 1 to 64

        Optional Arguments:
            no: Set to True to restore the default number of parallel routes

        Returns: True on success

        '''

        cmd = NXCLI._add_no_if_present(NXCLI._read_arg(max, 'max',
            'maximum-paths %', {int: 'max >= 1 and max <= 64'}), kwargs)

        return self._run_cfg_at_router_ospf_level(cmd)


    class OSPFInterface(object):

        def __init__(self, if_name, area, **kwargs):
            self.if_name = NXCLI._read_arg(if_name, 'if_name', ' %', {str:None})
            self.area = NXCLI._read_arg(area, 'area', ' %', {str:None})


        def _run_cfg_at_interface_level(self, cmds):
            '''
            Run the given list of commands at interface config level.

            Arguments:
                cmds: List of commands to be configured at interface level.

            Returns: True on success

            '''

            string = 'interface %s' % self.if_name
            string += ' ; %s' % cmds
            # print string
            return NXCLI._run_cfg(string)


        def add(self):
            '''
            Add this interface to OSPFv2 instance and area.

            Arguments:
                None.

            Optional Arguments:
                None.

            Returns: True on success

            '''

            cmd = 'ip router ospf %s area %s' % (self.Instance,self.area)
            return self._run_cfg_at_interface_level(cmd)


        def cfg_ospf_cost(self, ospf_cost=60, **kwargs):
            '''
            Configure OSPFv2 cost for this interface.

            Arguments:
                priority: ip ospf cost (int). Acceptable Range 1 to 65535.

            Optional Arguments:
                no: A boolean, set to True to remove the ip ospf config.

            Returns: True on success

            '''

            cmd = NXCLI._add_no_if_present(NXCLI._read_arg(ospf_cost, 'ospf_cost',
                'ip ospf cost %', 
                {int: 'ospf_cost >= 0 and ospf_cost <= 65535'}), kwargs)
            return self._run_cfg_at_interface_level(cmd)


        def cfg_hello_interval(self, hello_interval=60, **kwargs):
            '''
            Configure OSPFv2 hello interval for this interface.

            Arguments:
                priority: ip ospf hello interval (int). Acceptable Range 1 to 65535.

            Optional Arguments:
                no: A boolean, set to True to remove the ip ospf hello interval config.

            Returns: True on success

            '''

            cmd = NXCLI._add_no_if_present(NXCLI._read_arg(hello_interval, 'hello_interval',
                'ip ospf hello-interval %', 
                {int: 'hello_interval >= 1 and hello_interval <= 65535'}), kwargs)
            return self._run_cfg_at_interface_level(cmd)


        def cfg_dead_interval(self, dead_interval=60, **kwargs):
            '''
            Configure OSPFv2 dead interval for this interface.

            Arguments:
                priority: ip ospf dead interval (int). Acceptable Range 1 to 65535.

            Optional Arguments:
                no: A boolean, set to True to remove the ip ospf dead interval config.

            Returns: True on success

            '''

            cmd = NXCLI._add_no_if_present(NXCLI._read_arg(dead_interval, 'dead_interval',
                'ip ospf dead-interval %', 
                {int: 'dead_interval >= 1 and dead_interval <= 65535'}), kwargs)
            return self._run_cfg_at_interface_level(cmd)


        def cfg_ospf_priority(self, ospf_priority=60, **kwargs):
            '''
            Configure OSPFv2 priority for this interface. Priority is used to determine
            DR election in area.

            Arguments:
                priority: ip ospf priority (int). Acceptable Range 0 to 255.

            Optional Arguments:
                no: A boolean, set to True to remove the ip ospf priority config.

            Returns: True on success

            '''

            cmd = NXCLI._add_no_if_present(NXCLI._read_arg(ospf_priority, 'ospf_priority',
                'ip ospf priority %', 
                {int: 'ospf_priority >= 0 and ospf_priority <= 255'}), kwargs)
            return self._run_cfg_at_interface_level(cmd)


        def cfg_mtu_ignore(self, **kwargs):
            '''
            Configure OSPFv2 to ignore any IP MTU mismatch with a neighbor.

            Arguments: None

            Optional Arguments:
                no: A boolean, set to True to remove the ip ospf mtu-ignore
                config.

            Returns: True on success

            '''

            cmd = NXCLI._add_no_if_present('ip ospf mtu-ignore', kwargs)

            return self._run_cfg_at_interface_level(cmd)


        def cfg_passive_interface(self, **kwargs):
            '''
            Supress OSPF routing updates on this interface.

            Arguments: None

            Optional Arguments:
                no: A boolean, set to True to remove the ip ospf passive-interface 
                config.

            Returns: True on success

            '''

            cmd = NXCLI._add_no_if_present('ip ospf passive-interface', kwargs)

            return self._run_cfg_at_interface_level(cmd)


        def shutdown(self, **kwargs):
            '''
            Shutdown the OSPF on this interface.  All existing OSPF 
            configurations will be preserved.

            Arguments: None

            Optional Arguments:
                no: A boolean, set to True to remove the ip ospf shutdown config.

            Returns: True on success

            '''

            cmd = NXCLI._add_no_if_present('ip ospf shutdown', kwargs)

            return self._run_cfg_at_interface_level(cmd)

