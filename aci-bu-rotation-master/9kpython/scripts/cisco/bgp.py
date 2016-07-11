import re

from .feature import Feature
from .vrf import VRF
from .cisco_secret import CiscoSecret
import nxos_utils
from .nxcli import *

class BGPSession(Feature):
    '''
    Use this class to configure the BGP feature.
    '''

    @staticmethod
    def is_valid_asn(asn):
        if type(asn) is str:
            sub_asns = asn.split('.')
            if len(sub_asns) == 2:
                if (int(sub_asns[0]) >= 1 and int(sub_asns[0]) <= 65535 and 
                        int(sub_asns[1]) >= 0 and int(sub_asns[1]) <= 65535):
                    return True
            elif len(sub_asns) == 1:
                asn = int(asn)
        if isinstance(asn, (int, long)):
            if asn >= 1 and asn <= 4294967295:
                return True
        return False


    @staticmethod
    def _is_valid_asn_list(asn_list):
        if type(asn_list) is str:
            asns = asn_list.split()
            for asn in asns:
                if not BGPSession.is_valid_asn(asn):
                    return False
            return True


    def __init__(self, ASN=None, vrf='default'):
        self._name = 'bgp'
        if ASN != None:
            if not BGPSession.is_valid_asn(ASN):
                raise ValueError, 'Invalid ASN specified.' 
        self.ASN = ASN
        self.set_vrf(vrf)
        self.BGPNeighbor.session_ASN = self.ASN
        if self.is_enabled():
            self._load_all_existing_configs()


    def _load_all_existing_configs(self):
        status, output = nxcli('show running-config bgp')
        rows = output.split('\n')
        for row in rows:
            match = re.match(' *router bgp (\d+)', row)
            if match:
                if self.ASN and self.ASN != int(match.group(1)):
                    raise ValueError, ('BGP Session already exists with ASN '
                            '%s', match.group(1))
                self.ASN = int(match.group(1))
                break


    def _run_cfg_at_router_bgp_level(self, cmds):
        if self.ASN == None:
            raise ValueError, 'Must provide an ASN to configure BGP Session'
        string = 'router bgp %s' % str(self.ASN)
        if self.vrf.get_name() != 'default':
            if not self.vrf.exists():
                self.vrf.create()
            string += ' ; vrf %s' % self.vrf.get_name()
        string += ' ; %s' % cmds
        return NXCLI._run_cfg(string)


    def set_ASN(self, ASN):
        status, output = nxcli('show running-config bgp | include \"router bgp\"')
        if output:
            if output.split()[2] != str(ASN):
                raise Exception("ASN mismatch, please use %s" % output.split()[2])
        self.ASN = ASN


    def _check_for_ASN(self, **kwargs):
        if kwargs.has_key('ASN'):
            self.set_ASN(kwargs['ASN'])


    def set_vrf(self, vrf):
        '''
        Set the VRF (Virtual Routing and Forwarding) context for subsequent API
        calls on this BGPSession object. Any configuration done on this 
        BGPSession object will be applied to this VRF.
        
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
        Start the BGP routing process. If BGP is shutdown this will start it 
        back up. If the BGP feature is disabled this will enable the feature in 
        addition to starting the process.

        Arguments: None

        Returns: True on success

        '''

        if self.is_shutdown():
            return self._run_cfg_at_router_bgp_level('no shutdown')

        if not self.is_enabled():
            self.enable()

        return self._run_cfg_at_router_bgp_level('')


    def shutdown(self):
        '''
        Shutdown the BGP routing process.  All existing BGP configurations will 
        be preserved.

        Arguments: None

        Returns: True on success

        '''

        return self._run_cfg_at_router_bgp_level('shutdown')


    def is_shutdown(self):
        '''
        Check if the BGP routing process is shutdown.

        Arguments: None

        Returns: 
            True if the BGP process is enabled and shutdown.
            False if the BGP process is running or if BGP is not enabled.

        '''

        if self.is_enabled():
            status, output = nxcli('show run bgp | include shutdown')
            rows = output.split('\n')
            for row in rows:
                if row.strip() == 'shutdown':
                    return True
        return False


    def cfg_bestpath(self, **kwargs):
        '''
        Modifies the default best-path selection algorithm. 

        Optional Arguments:
            always_compare_med: a boolean. Set to True to compare the Multi-Exit
                Discriminator (MED) on paths from a different autonomous system 
                (AS). Set to False to remove this configuration.
            compare_router_id: a boolean. Set to True to configure a BGP routing
                process to compare identical routes received from different 
                external peers during the best path selection process and to 
                select the route with the lowest router ID as the best path. Set 
                to False to remove this configuration.
            as_path_multipath_relax: a boolean. Set to True to configure a BGP 
                routing process to consider the different autonomous system (AS)
                paths and load balance multiple paths during best path route 
                selection. Set to False to remove this configuration.
            med_missing_as_worst: a boolean. Set to True to assign the value of 
                infinity to received routes that do not carry the MED attribute,
                making these routes the least desirable. Set to False to remove 
                this configuration.
            med_non_deterministic: a boolean. Set to True to specify that the 
                best-MED path among paths is not picked from the same AS. Set to 
                False to remove this configuration.

        Returns: True on success
        
        '''

        cmd = ''
        if kwargs.has_key('always_compare_med'):
            if kwargs['always_compare_med'] == False:
                cmd += 'no bestpath always-compare-med ;'
            elif kwargs['always_compare_med'] == True:
                cmd += 'bestpath always-compare-med ;'
        if kwargs.has_key('compare_router_id'):
            if kwargs['compare_router_id'] == False:
                cmd += 'no bestpath compare-routerid ;'
            elif kwargs['compare_router_id'] == True:
                cmd += 'bestpath compare-routerid ;'
        if kwargs.has_key('as_path_multipath_relax'):
            if kwargs['as_path_multipath_relax'] == False:
                cmd += 'no bestpath as-path multipath-relax ;'
            elif kwargs['as_path_multipath_relax'] == True:
                cmd += 'bestpath as-path multipath-relax ;'
        if kwargs.has_key('med_missing_as_worst'):
            if kwargs['med_missing_as_worst'] == False:
                cmd += 'no bestpath med missing-as-worst ;'
            elif kwargs['med_missing_as_worst'] == True:
                cmd += 'bestpath med missing-as-worst ;'
        if kwargs.has_key('med_non_deterministic'):
            if kwargs['med_non_deterministic'] == False:
                cmd += 'no bestpath med non-deterministic ;'
            elif kwargs['med_non_deterministic'] == True:
                cmd += 'bestpath med non-deterministic ;'

        return self._run_cfg_at_router_bgp_level(cmd)


    def cfg_cluster_id(self, cluster_id, **kwargs):
        '''
        Sets the cluster ID on a route reflector in a route reflector cluster. 
        To remove the cluster ID, set the optional 'no' argument to True.

        Arguments:
            cluster_id: Cluster ID of this router acting as a route reflector. 
                Can be specified as an integer ranging from 1 to 4294967295 or 
                as a string in dotted format: 'A.B.C.D'.
        
        Optional Arguments:
            no: A boolean, set to True to remove the specified cluster ID.

        Returns: True on success

        '''

        cmd = NXCLI._add_no_if_present(NXCLI._read_arg(cluster_id, 'cluster_id', 
            'cluster-id %', {int: 
                'cluster_id >= 1 and cluster_id <= 4294967295', 
                    str:'socket.inet_aton(cluster_id)'}), kwargs) 

        return self._run_cfg_at_router_bgp_level(cmd)


    def cfg_confederation_identifier(self, id, **kwargs):
        '''
        Specifies a BGP confederation identifier. To remove the confederation 
        identifier, set the optional 'no' argument to True.

        Arguments:
            id: The AS number. Can be specified as an integer ranging from 1 to 
                4294967295 or a string in the following format: 
                '<1-65535>[.<0-65535>]'

        Optional Arguments:
            no: A boolean. Set to True to remove the specified confederation ID.
        
        Usage Guidelines:

            The bgp confederation identifier is used to configure a 
            single autonomous system number to identify a group of smaller 
            autonomous systems as a single confederation. 

            A confederation can be used to reduce the internal BGP (iBGP) mesh 
            by dividing a large single autonomous system into multiple 
            subautonomous systems and then grouping them into a single 
            confederation. The subautonomous systems within the confederation 
            exchange routing information like iBGP peers. External peers 
            interact with the confederation as if it is a single autonomous 
            system.

            Each subautonomous system is fully meshed within itself and has a 
            few connections to other autonomous systems within the 
            confederation. Next hop, Multi Exit Discriminator (MED), and local 
            preference information is preserved throughout the confederation, 
            allowing you to retain a single Interior Gateway Protocol (IGP) for 
            all the autonomous systems. 
        
        Returns: True on success
        
        '''

        cmd = NXCLI._add_no_if_present(NXCLI._read_arg(id, 'id', 
            'confederation identifier %', {int: 'id >= 1 and id <= 4294967295', 
                    str:'BGPSession.is_valid_asn(id)'}), kwargs) 

        return self._run_cfg_at_router_bgp_level(cmd)


    def cfg_confederation_peers(self, peers, **kwargs):
        '''
        Configures subautonomous systems to belong to a single confederation. To 
        remove an autonomous system from the confederation, set the optional 
        'no' argument to True. 

        Arguments:
            peers: A string of space-separated AS numbers where each 
                ASN=<1-4294967295>|<1-65535>[.<0-65535>]  

        Optional arguments:
            no: A boolean, set to True to remove the specified AS numbers from 
                the list of confederation peers.

        Usage Guidelines:

            The bgp confederation peers command is used to configure multiple 
            autonomous systems as a single confederation. The ellipsis (...) in 
            the command syntax indicates that your command input can include 
            multiple values for the as-number argument.

            The autonomous systems specified in this command are visible 
            internally to the confederation. Each autonomous system is fully 
            meshed within itself. The bgp confederation identifier command 
            specifies the confederation to which the autonomous systems belong. 
        
        Returns: True on success
        
        '''
 
        cmd = NXCLI._add_no_if_present(NXCLI._read_arg(peers, 'peers', 
            'confederation peers %', {int: 'peers >= 1 and peers <= 4294967295', 
                    str:'BGPSession.is_valid_asn_list(peers)'}), kwargs) 

        return self._run_cfg_at_router_bgp_level(cmd)


    def enforce_first_as(self, **kwargs):
        '''
        Configures a router to deny an update received from an external BGP 
        (eBGP) peer that does not list its autonomous system (AS) number at the 
        beginning of the AS_PATH in the incoming update. To disable this 
        behavior, set the optional 'no' argument to True.
            
        Optional Arguments:
            no: A boolean, set to True to disable this feature.

        Usage Guidelines:

            The bgp enforce-first-as command is used to deny incoming updates 
            received from eBGP peers that do not list their AS number as the 
            first segment in the AS_PATH attribute. Enabling this command 
            prevents a misconfigured or unauthorized peer from misdirecting 
            traffic (spoofing the local router) by advertising a route as if it 
            was sourced from another autonomous system. 

        Returns: True on success
        
        '''

        cmd = NXCLI._add_no_if_present('enforce-first-as', kwargs)
        return self._run_cfg_at_router_bgp_level(cmd)


    def _cfg_event_history(self, type, args):
        cmd = NXCLI._add_no_if_present('event-history %s ' % type, args)
        cmd += NXCLI._read_arg_from_dict(args, 'size', 'size %', 
                {str:'size in [\'small\', \'medium\', \'large\', \'disable\']'})
        return self._run_cfg_at_router_bgp_level(cmd)


    def cfg_cli_event_history(self, **kwargs): 
        '''
        Enables the NXCLI event history to be saved in a buffer.  It is enabled by
        default.  The default buffer size is 'small'.  Possible sizes are 
        'small', 'medium' and 'large'.

        Optional arguments:
            size: A string, possible values are: 'small', 'medium', 'large', or
                'disable'
            no: A boolean, set to True to stop saving the NXCLI event history.
        
        Returns: True on success
        
        '''
        
        return self._cfg_event_history('cli', kwargs)


    def cfg_events_event_history(self, **kwargs): 
        '''
        Enables the events event history to be saved in a buffer.  It is enabled 
        by default.  The default buffer size is 'small'.  Possible sizes are 
        'small', 'medium' and 'large'.

        Optional arguments:
            size: A string, possible values are: 'small', 'medium', 'large', or
                'disable'
            no: A boolean, set to True to stop saving the events event history.
            
        Returns: True on success
        
        '''
        
        return self._cfg_event_history('events', kwargs)


    def cfg_periodic_event_history(self, **kwargs): 
        '''
        Enables periodic events history to be saved in a buffer.  It is enabled 
        by default.  The default buffer size is 'small'.  Possible sizes are 
        'small', 'medium' and 'large'.

        Optional arguments:
            size: A string, possible values are: 'small', 'medium', 'large', or
                'disable'
            no: A boolean, set to True to stop saving the periodic event 
                history.
            
        Returns: True on success
        
        '''
        
        return self._cfg_event_history('periodic', kwargs)


    def fast_external_fallover(self, **kwargs):
        '''
        Configures the BGP process to immediately reset the session if the link 
        to a directly connected BGP peer goes down. This is enabled by default.  
        To disable this behavior, set the optional 'no' argument to True.

        Optional arguments:
            no: A boolean, set to True to disable this feature.
            
        Returns: True on success
        
        '''

        cmd = NXCLI._add_no_if_present('fast-external-fallover', kwargs)
        return self._run_cfg_at_router_bgp_level(cmd)


    def flush_routes(self, **kwargs):
        '''
        Flush routes in RIB upon controlled restart.  To disable this behavior, 
        set the optional 'no' argument to True.

        Optional arguments:
            no: A boolean, set to True to disable this feature.
            
        Returns: True on success
        
        '''

        cmd = NXCLI._add_no_if_present('flush-routes', kwargs)
        return self._run_cfg_at_router_bgp_level(cmd)


    def graceful_restart(self, **kwargs):
        '''
        Enables graceful restart and graceful restart helper functionality. This 
        is enabled by default.  To disable this behavior set the optional 'no' 
        argument to True.

        Optional arguments:
            no: A boolean, set to True to disable this feature.
            
        Usage Guidelines:

            The graceful-restart command is used to configure or disable the 
            graceful restart capability on a router in a BGP network.  If the 
            graceful restart capability is enabled after a BGP session has been 
            established, you will need to restart the session with a soft or 
            hard reset.

            The default timer values for this feature are optimal for most 
            network deployments. We recommend that they are adjusted only by 
            experienced network operators. When adjusting the timer values, the 
            restart timer should not be set to a value greater than the hold 
            time that is carried in the OPEN message. If consecutive restart 
            operations occur, routes (from a restarting router) that were 
            previously marked as stale will be deleted.

        Returns: True on success
        
        '''

        cmd = NXCLI._add_no_if_present('graceful-restart', kwargs)
        return self._run_cfg_at_router_bgp_level(cmd)


    def cfg_graceful_restart_restart_time(self, time, **kwargs):
        '''
        Configures the maximum time for restart advertised to peers. Default 
        value is 120 seconds.  To remove a previously configured value set the 
        optional 'no' argument to True.

        Arguments:
            time: An integer ranging from 1 to 3600 representing the restart 
                time. 
            
        Optional Arguments:
            no: A boolean, set to True to delete the existing configuration and 
                set back to the default.

        Returns: True on success
        
        '''
        cmd = NXCLI._add_no_if_present(NXCLI._read_arg(time, 'time', 
            'graceful-restart restart-time %', 
            {int: 'time >= 1 and time <= 3600'}), kwargs) 
        
        return self._run_cfg_at_router_bgp_level(cmd)


    def cfg_graceful_restart_stalepath_time(self, time, **kwargs):
        '''
        Configures the maximum time to keep a restarting peer`s stale routes. 
        Default value is 300 seconds. To remove a previously configured value 
        set the optional 'no' argument to True.

        Arguments:
            time: An integer ranging from 1 to 3600 representing the stalepath 
                time.  
            
        Optional Arguments:
            no: A boolean, set to True to delete the existing configuration and 
                set back to the default.
            
        Returns: True on success
        
        '''
        
        cmd = NXCLI._add_no_if_present(NXCLI._read_arg(time, 'time', 
            'graceful-restart stalepath-time %', 
            {int: 'time >= 1 and time <= 3600'}), kwargs) 
        
        return self._run_cfg_at_router_bgp_level(cmd)


    def graceful_restart_helper(self, **kwargs):
        '''
        Configures graceful restart helper mode functionality. To disable this 
        behavior set the optional 'no' argument to True.

        Optional Arguments:
            no: A boolean, set to True to disable this feature.
            
        Usage Guidelines:
            The graceful-restart-helper command is used to configure the local 
            BGP router to support the graceful restart of a remote BGP peer. 
            
        Returns: True on success
        
        '''

        cmd = NXCLI._add_no_if_present('graceful-restart-helper', kwargs)
        return self._run_cfg_at_router_bgp_level(cmd)


    def log_neighbor_changes(self, **kwargs):
        '''
        Log a message for neighbor up/down event. To disable this behavior set 
        the optional 'no' argument to True.

        Optional Arguments:
            no: A boolean, set to True to disable this feature.
            
        Returns: True on success
        
        '''

        cmd = NXCLI._add_no_if_present('log-neighbor-changes', kwargs)
        return self._run_cfg_at_router_bgp_level(cmd)


    def max_as_limit(self, limit, **kwargs):
        '''
        Allow AS-PATH attribute from EBGP neighbor imposing a limit on number of 
        ASes. To disable this behavior set the optional 'no' argument to True.
            
        Arguments:
            limit: An integer ranging from 1 to 512 representing the number of 
                ASes in the AS-PATH attribute.
            
        Optional Arguments:
            no: A boolean, set to True to disable this feature. 
            
        Returns: True on success
        
        '''

        cmd = NXCLI._add_no_if_present(NXCLI._read_arg(limit, 'limit', 
            'maxas-limit %', {int: 'limit >= 1 and limit <=512'}), kwargs)
        return self._run_cfg_at_router_bgp_level(cmd)


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
        return self._run_cfg_at_router_bgp_level(cmd)


    def set_addr_family(self, ip_version, transmission_type):
        '''
        Enable an address-family for use with BGP. Possible address families 
        are: ipv4 unicast, ipv4 multicast, ipv6 unicast and ipv6 multicast.
        This API sets the current address-family for use with APIs that
        configure address-family attributes.

        Arguments:
            ip_version: A string, possible values are 'ipv4' and 'ipv6'.
            transmission_type: A string, possible values are 'unicast' or 
                'multicast'.

        Returns: 
            ValueError if an invalid ip_version or transmission_type is 
                specified.
            True on success.

        '''

        if ip_version in ['ipv4', 'ipv6']:
            self.ip_version = ip_version
        else:
            raise ValueError, 'Invalid IP version specified'
        if transmission_type in ['unicast', 'multicast']:
            self.transmission_type = transmission_type
        else:
            raise ValueError, 'Invalid transmission type specified'


    def _run_cfg_at_router_bgp_addr_fam_level(self, cmds):
        if not (hasattr(self, 'ip_version') and 
                hasattr(self, 'transmission_type')):
            self.ip_version = 'ipv4'
            self.transmission_type = 'unicast'
        string = 'address-family %s %s' % (self.ip_version, 
                self.transmission_type)
        string += ' ; %s' % cmds
        return self._run_cfg_at_router_bgp_level(string)

   
    def cfg_aggregate_address(self, address, **kwargs):
        '''
        Creates a summary address in a Border Gateway Protocol (BGP) routing 
        table. To remove the summary address, set the optional 'no' argument to 
        True.

        Arguments:
            address: A string representing the aggregate IP address and mask in 
                either CIDR notation or dotted quad. E.g. '192.0.2.0/24', 
                '192.0.2.0/255.255.255.0' 

        Optional Arguments:
            advertise_map: A string which specifies the name of the route map 
                used to select attribute information from specific routes. 
                Should be an alphanumeric string up to 63 characters long.
            as_set: A boolean. Set to True to generate the autonomous system set 
                path information and community information from the contributing 
                paths.
            attribute_map: A string which specifies the name of the route map 
                used to set the attribute information for specific routes. 
                Should be an alphanumeric string up to 63 characters long.
            summary_only: A boolean. Set to True to filter all more-specific 
                routes from updates.
            suppress_map: A string which specifies the name of the route map 
                used to conditionally filter more specific routes. Should be an 
                alphanumeric string up to 63 characters.
            no: A boolean. Set to True to remove a summary address.

        Returns: True on success
        
        '''

        cmd = NXCLI._add_no_if_present('aggregate-address %s' % 
                    str(address), kwargs)
        cmd += NXCLI._read_arg_from_dict(kwargs, 'advertise_map', 
                ' advertise-map %', {str:'len(advertise_map) <= 63'}) 
        cmd += NXCLI._read_arg_from_dict(kwargs, 'as_set', ' as-set', 
                {bool:None})
        cmd += NXCLI._read_arg_from_dict(kwargs, 'attribute_map',
                ' attribute-map %', {str:'len(attribute_map) <= 63'})
        cmd += NXCLI._read_arg_from_dict(kwargs, 'summary_only', 
                ' summary-only', {bool:None})
        cmd += NXCLI._read_arg_from_dict(kwargs, 'suppress_map',
                ' suppress-map %', {str:'len(suppress_map) <= 63'})

        return self._run_cfg_at_router_bgp_addr_fam_level(cmd)


    def client_to_client_route_reflection(self, **kwargs):
        '''
            Configures client-to-client route reflection. This feature is 
            enabled by default. This command triggers an automatic soft clear or 
            refresh of BGP neighbor sessions. To disable this feature set the 
            optional 'no' argument to True.

            Optional arguments:
                no: A boolean. Set to True to disable client-to-client route 
                    reflection.

            Returns: True on success

        '''

        cmd = NXCLI._add_no_if_present('client-to-client reflection', kwargs)
        return self._run_cfg_at_router_bgp_addr_fam_level(cmd)


    def cfg_dampening(self, **kwargs):
        '''
        Enable Border Gateway Protocol (BGP) route dampening or change various 
        BGP route dampening factors. To disable the function set the optional 
        'no' argument to True.

        Optional args:
            half_life: Time (in minutes) after which a penalty is decreased. 
                Once the route has been assigned a penalty, the penalty is 
                decreased by half after the half-life period (which is 15 
                minutes by default). The process of reducing the penalty happens
                every 5 seconds. The range of the half-life period is 1 to 45 
                minutes. The default is 15 minutes.
            reuse_limit: Value to start reusing a route, range is from 1 to 
                20000.
            suppress_limit: Value to start suppressing a route, range is from 1 
                to 20000.
            max_suppress_time: Maximum suppress time for a stable route, the 
                range is from 1 to 255.
            route_map: Name of route map that specifies dampening criteria. The 
                name can be any alphanumeric string up to 63 characters.
            no: Set to True to disable the dampening feature.

        Usage Guidelines:
            You can configure route dampening to minimize route flaps 
            propagating through your iBGP network.

        Returns: True on success

        '''

        cmd = NXCLI._add_no_if_present('dampening', kwargs)
        if kwargs.has_key('route_map'):
            cmd += NXCLI._read_arg_from_dict(kwargs, 'route_map', 
                    ' route-map %', {str:None})
        if (kwargs.has_key('half_life') or 
                kwargs.has_key('reuse_limit') or 
                kwargs.has_key('suppress_limit') or 
                kwargs.has_key('max_suppress_time')):
            if kwargs.has_key('route_map'):
                raise AttributeError, ('Can either specify dampening via a'
                        'route_map or half_life attributes, but not both')
                        
            cmd += NXCLI._read_arg_from_dict(kwargs, 'half_life', ' %', 
                    {int:'half_life >= 1 and half_life <= 45'},
                    raise_error_if_not_present=True)
            cmd += NXCLI._read_arg_from_dict(kwargs, 'reuse_limit', 
                    ' %', {int: ('reuse_limit >= 1 and ' 
                        'reuse_limit <= 20000')}, 
                    raise_error_if_not_present=True)
            cmd += NXCLI._read_arg_from_dict(kwargs, 
                    'suppress_limit', ' %', {int: 
                    ('suppress_limit >= 1 and ' 
                            'suppress_limit <= 20000')},
                    raise_error_if_not_present=True)
            cmd += NXCLI._read_arg_from_dict(kwargs, 'max_suppress_time',
                    ' %', {int: ('max_suppress_time >= 1 and  '
                           ' max_suppress_time <= 255')},
                    raise_error_if_not_present=True)

        return self._run_cfg_at_router_bgp_addr_fam_level(cmd)

    
    def set_default_metric(self, metric, **kwargs):
        '''
        Set metric of redistributed routes.  To remove this configuration set 
        the optional 'no' argument to True.

        Arguments:
            metric: The metric, an integer ranging from  0 to 4294967295.

        Optional Arguments:
            no: A boolean, set to True to remove any existing configuration.

        Returns: True on success

        '''

        cmd = NXCLI._add_no_if_present(NXCLI._read_arg(metric, 'metric', 
            'default-metric %', {int: 'metric >= 0 and metric <= 4294967295', 
                long: 'metric >= 0 and metric <= 4294967295'}), kwargs)
        
        return self._run_cfg_at_router_bgp_addr_fam_level(cmd)

    
    def cfg_distance(self, ebgp_dist, ibgp_dist, local_dist, **kwargs):
        '''
        Configure administrative distance for external BGP, internal BGP and 
        local routes. Default values are: eBGP: 20, iBGP: 200, and local: 220. 
        To set the distances back to the default set the optional 'no' argument 
        to True.

        Arguments:
            ebgp_dist: Distance for eBGP routes, an integer ranging from 1 to 
                255.
            ibgp_dist: Distance for iBGP routes, an integer ranging from 1 to 
                255.
            local_dist: Distance for local routes, an integer ranging from 1 to
                255.

        Optional Arguments:
            no: Set to True to set distances back to the default values.

        Returns: True on success

        '''
        
        cmd = NXCLI._add_no_if_present('distance', kwargs)
        cmd += NXCLI._read_arg(ebgp_dist, 'ebgp_dist', ' %', {int: 
            'ebgp_dist >= 1 and ebgp_dist <= 255'})
        cmd += NXCLI._read_arg(ibgp_dist, 'ibgp_dist', ' %', {int:
            'ibgp_dist >= 1 and ibgp_dist <= 255'})
        cmd += NXCLI._read_arg(local_dist, 'local_dist', ' %', {int:
            'local_dist >= 1 and local_dist <= 255'})

        return self._run_cfg_at_router_bgp_addr_fam_level(cmd)


    def cfg_maximum_paths(self, max, **kwargs):
        '''
        Configures the maximum number of parallel routes that the Border Gateway
        Protocol (BGP) can support.  To restore the default number of parallel 
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

        return self._run_cfg_at_router_bgp_addr_fam_level(cmd)


    def cfg_ibgp_maximum_paths(self, max, **kwargs):
        '''
        Configures the maximum number of parallel routes that the interior 
        Border Gateway Protocol (iBGP) can support.  To restore the default 
        number of parallel routes, set the optional 'no' argument to True.
            
        Arguments:
            max: Maximum number of parallel routes that an IP routing protocol 
                installs in a routing table. The range is from 1 to 64.
        
        Optional Arguments:
            no: Set to True to restore the default number of parallel routes

        Returns: True on success

        '''

        cmd = NXCLI._add_no_if_present(NXCLI._read_arg(max, 'max', 
            'maximum-paths ibgp %', {int: 'max >= 1 and max <= 64'}), kwargs)

        return self._run_cfg_at_router_bgp_addr_fam_level(cmd)


    def add_network(self, network, **kwargs):
        '''
        Configures an IP prefix to advertise. To remove the IP prefix to 
        advertise, set the optional 'no' argument to True.

        Arguments:
            network: A string representing the IP prefix in either CIDR notation
                or dotted quad. E.g. '192.0.2.0/24', '192.0.2.0/255.255.255.0' 

        Optional Arguments:
            route-map: Specifies the name of the route-map to modify attributes.
            no: Set to True to remove a network

        Usage Guidelines:
            The IP prefix to advertise is considered for bestpath and 
            advertisement to peers only if a route of equal or more specificity 
            is present in the routing table.

        Returns: True on success
        
        '''

        cmd = NXCLI._add_no_if_present('network %s' % str(network), kwargs)
        cmd += NXCLI._read_arg_from_dict(kwargs, 'route_map', ' route-map %', 
                {str: 'len(route_map) <= 63'})

        return self._run_cfg_at_router_bgp_addr_fam_level(cmd)

    
    def cfg_nexthop_routemap(self, route_map, **kwargs):
        '''
        Specifies that Border Gateway Protocol (BGP) routes are resolved using 
        only next hops whose routes match specific characteristics. To remove 
        the route map, set the optional 'no' argument to True.

        Arguments:
            route_map: Route map name. The name can be any alphanumeric string 
                up to 63 characters.

        Optional Arguments:
            no: A boolean, set to True to remove a route-map

        Usage Guidelines:
            Use this API to configure route policy filtering for next hops.  
            BGP next-hop filtering allows you to specify that when a next-hop 
            address is checked with the RIB, the underlying route for that 
            next-hop address is passed through the route map. If the route map 
            rejects the route, the next-hop address is treated as unreachable.  
            BGP marks all next hops that are rejected by the route policy as 
            invalid and does not calculate the best path for the routes that use
            the invalid next-hop address.

            Returns: True on success

        '''

        cmd = NXCLI._add_no_if_present(NXCLI._read_arg(route_map, 'route_map', 
            'nexthop route-map %', {str: 'len(route_map) <= 63'}), kwargs)

        return self._run_cfg_at_router_bgp_addr_fam_level(cmd)


    def cfg_nexthop_trigger_delay(self, critical_delay=3000, 
            non_critical_delay=10000, **kwargs):
        '''
        Configures Border Gateway Protocol (BGP) to delay for triggering 
        next-hop calculations. To set the trigger delay to the default value set
        the optional 'no' argument to True.

        Arguments:
            critical_delay: An integer specifying the critical next-hop trigger 
                delay in milliseconds. The range is from 1 to 4294967295. The 
                default is 3000.
            non_critical_delay: An integer specifying the noncritical next-hop 
                trigger delay in milliseconds. The range is from 1 to 
                4294967295. The default is 10000.

        Optional Arguments:
            no: Set to True in order to set the trigger delay to the default 
                value.

        Usage Guidelines:
            Use this API to modify when BGP processes next-hop address tracking 
            events. The non-critical delay value must always be set to at least 
            equal or greater than the critical delay value. The delay should be 
            slightly higher than the time it takes for the Interior Gateway 
            Protocol (IGP) to settle into a steady state after some event (IGP 
            convergence time). 
            
        Returns: True on success

        '''

        cmd = NXCLI._add_no_if_present('nexthop trigger-delay', kwargs)
        if not kwargs.has_key('no'):
            cmd += NXCLI._read_arg(critical_delay, 'critical_delay', 
                    ' critical %', {int: 
                        'critical_delay >= 1 and critical_delay <= 4294967295',
                        long: 'critical_delay >= 1 and critical_delay <= 4294967295'})
            cmd += NXCLI._read_arg(non_critical_delay, 'non_critical_delay', 
                    ' non-critical %', {int:
                        'non_critical_delay >= 1 and non_critical_delay \
                                <= 4294967295', 
                        long: 'non_critical_delay >= 1 and non_critical_delay \
                                <= 4294967295'})

        return self._run_cfg_at_router_bgp_addr_fam_level(cmd)


    def redistribute_direct_routes(self, route_map, **kwargs):
        '''
        Injects routes that are directly connected on an interface into the 
        Border Gateway Protocol (BGP). To restore the system to its default 
        condition in which the software does not redistribute routes, set the 
        optional 'no' argument to True. 

        Arguments:
            route_map: An alphanumeric string up to 63 characters specifying the
                identifier of a configured route map. Use a route map to filter 
                which routes are redistributed into BGP.

        Optional Arguments:
            no: A boolean, set to True to remove the configuration.

        Returns: True on success

        '''

        cmd = NXCLI._add_no_if_present(NXCLI._read_arg(route_map, 'route_map', 
            'redistribute direct route-map %', {str: 'len(route_map) <=63'}), 
            kwargs) 
    
        return self._run_cfg_at_router_bgp_addr_fam_level(cmd)
    

    def _redistribute_routes_from_other_protos(self, proto, protocol_tag, 
            route_map, kwargs):

        cmd = NXCLI._add_no_if_present('redistribute %s' % proto, kwargs)
        cmd += NXCLI._read_arg(protocol_tag, 'protocol_tag', ' %', {str:None})
        cmd += NXCLI._read_arg(route_map, 'route_map', ' route-map %', {str: 
            'len(route_map) <= 63'})

        return self._run_cfg_at_router_bgp_addr_fam_level(cmd)


    def redistribute_eigrp_routes(self, instance_tag, route_map, **kwargs):
        '''
        Injects routes from the EIGRP protocol into the Border Gateway Protocol 
        (BGP). To restore the system to its default condition in which the 
        software does not redistribute routes, set the optional 'no' argument to
        True. 

        Arguments:
            instance_tag: Any case-sensitive, alphanumeric string up to 64
                characters.
            route_map: Specifies the identifier of a configured route map. Use a
                route map to filter which routes are redistributed into BGP.

        Optional Arguments:
            no: A boolean, set to True to remove the configuration.

        Returns: True on success

        '''
        
        return self._redistribute_routes_from_other_protos('eigrp', 
                instance_tag, route_map, kwargs)


    def redistribute_isis_routes(self, instance_tag, route_map, **kwargs):
        '''
        Injects routes from the IS-IS protocol into the Border Gateway Protocol 
        (BGP). To restore the system to its default condition in which the 
        software does not redistribute routes, set the optional 'no' argument to
        True. 

        Arguments:
            instance_tag: Any case-sensitive, alphanumeric string up to 64 
                characters.
            route_map: Specifies the identifier of a configured route map. Use a
                route map to filter which routes are redistributed into BGP.

        Optional Arguments:
            no: A boolean, set to True to remove the configuration.

            Returns: True on success

        '''

        return self._redistribute_routes_from_other_protos('isis', instance_tag,
                route_map, kwargs)


    def redistribute_ospf_routes(self, protocol_tag, route_map, **kwargs):
        '''
        Injects routes from the OSPF protocol into the Border Gateway Protocol 
        (BGP). To restore the system to its default condition in which the 
        software does not redistribute routes, set the optional 'no' argument to
        True. 

        Arguments:
            instance_tag: Any case-sensitive, alphanumeric string up to 64
                characters.
            route_map: Specifies the identifier of a configured route map. Use a
                route map to filter which routes are redistributed into BGP.

        Optional Arguments:
            no: A boolean, set to True to remove the configuration.

        Returns: True on success

        '''

        return self._redistribute_routes_from_other_protos('ospf', protocol_tag,
                route_map, kwargs)


    def redistribute_rip_routes(self, instance_tag, route_map, **kwargs):
        '''
        Injects routes from the RIP protocol into the Border Gateway Protocol 
        (BGP). To restore the system to its default condition in which the 
        software does not redistribute routes, set the optional 'no' argument to
        True. 

        Arguments:
            instance_tag: Any case-sensitive, alphanumeric string up to 64
                characters
            route_map: Specifies the identifier of a configured route map. Use a
                route map to filter which routes are redistributed into BGP.

        Optional Arguments:
            no: A boolean, set to True to remove the configuration.

        Returns: True on success

        '''

        return self._redistribute_routes_from_other_protos('rip', instance_tag, 
                route_map, kwargs)


    def redistribute_static_routes(self, route_map, **kwargs):
        '''
        Inject static routes into the Border Gateway Protocol (BGP). To restore 
        the system to its default condition in which the software does not 
        redistribute routes, set the optional 'no' argument to True. 

        Arguments:
            route_map: Specifies the identifier of a configured route map. Use a
                route map to filter which routes are redistributed into BGP.

        Optional Arguments:
            no: A boolean, set to True to remove the configuration.

        Returns: True on success

        '''

        cmd = NXCLI._add_no_if_present(NXCLI._read_arg(route_map, 'route_map', 
            'redistribute static route-map %', {str: 'len(route_map) <=63'}), 
            kwargs) 
    
        return self._run_cfg_at_router_bgp_addr_fam_level(cmd)


    def suppress_inactive(self, **kwargs):
        '''
        Configures the Border Gateway Protocol (BGP) process to advertise active
        routes to a BGP peer only.  To remove the restriction, set the optional 
        'no' argment to True. 
            
        Optional Arguments:
            no: A boolean, set to True to remove the configuration.

        Returns: True on success
        
        '''

        cmd = NXCLI._add_no_if_present('suppress-inactive', kwargs)
        return self._run_cfg_at_router_bgp_addr_fam_level(cmd)



    class BGPNeighbor(object):
        '''
        Use this class to configure a BGP Neighbor. This class is an attribute 
        of the BGPSession class, must have a BGPSession object in order to use
        this class. 
        
        Example:
            bgp = BGPSession(64496)
            bgp.start()
            n1 = bgp.BGPNeighbor('100.1.1.2', ASN = 64497)
        '''
 
        def __init__(self, ip_address, vrf='default', **kwargs):
            '''
            Initializes a BGPNeighbor object with the specified IP address and 
            VRF and returns the new object.

            Arguments:
                ip_address: A string representing the IPv4/IPv6 address or 
                    network in either CIDR notation or dotted quad. E.g. 
                    '192.0.2.0', '192.0.2.0/24', '192.0.2.0/255.255.255.0' 
                vrf: A string or integer representing the VRF that the neighbor 
                    should be configured on.

            Optional Arguments:
                ASN: An integer representing the Autonomous System (AS) that the
                    neighbor is associated with.
                
            Returns: BGPNeighbor object on success

            '''
            
            self.ip_address = str(ip_address)

            if kwargs.has_key('ASN'):
                if BGPSession.is_valid_asn(kwargs['ASN']):
                    self.ASN = kwargs['ASN']
                else:
                    raise ValueError, 'invalid ASN specified'
            self.vrf = VRF(vrf)

        
        def _run_cfg_at_ngbr_level(self, cmds):
            string = 'router bgp %s' % str(self.session_ASN)
            if self.vrf.get_name() != 'default':
                if not self.vrf.exists():
                    self.vrf.create()
                string += ' ; vrf %s' % self.vrf.get_name()
            string += ' ; neighbor %s' % str(self.ip_address)
            if hasattr(self, 'ASN') and self.ASN:
                string += ' remote-as %s' % self.ASN
            string += ' ; %s' % cmds
            return NXCLI._run_cfg(string)


        def add(self):
            '''
            Adds the BGP Neighbor to the BGP configuration.

            Arguments: None

            Returns: True on success

            '''

            return self._run_cfg_at_ngbr_addr_fam_level("")


        def remove(self):
            '''
            Removes the BGP Neighbor from the BGP configuration.

            Arguments: None

            Returns: 
                True on success
                ValueError if the neighbor does not exist

            '''

            if not self.exists():
                raise ValueError, ('Cannot remove BGP Neighbor %s, it does not '
                    'exist.' % str(self.ip_address))
            string = 'router bgp %s' % str(self.session_ASN)
            if self.vrf.get_name() != 'default':
                if not self.vrf.exists():
                    self.vrf.create()
                string += ' ; vrf %s' % self.vrf.get_name()
            string += ' ; no neighbor %s' % str(self.ip_address)
            if hasattr(self, 'ASN') and self.ASN:
                string += ' remote-as %s' % self.ASN
            return NXCLI._run_cfg(string)


        def exists(self):
            '''
            Checks if this BGP Neighbor exists.

            Arguments: None

            Returns:
                True if this BGP Neighbor exists.
                False if this BGP Neighbor does not exist.

            '''

            string = 'show running-config bgp'
            if self.vrf.get_name() != 'default':
                string += ' | begin vrf %s' % self.vrf.get_name()
            status, output = nxcli(string)
            rows = output.split('\n')
            for row in rows:
                match = re.match(' *neighbor %s' % str(self.ip_address), row)
                if match:
                    return True
            return False

        
        def set_description(self, description=None, **kwargs):
            '''
            Sets a descriptive string for this BGP Neighbor.

            Arguments: 
                description: An alphanumeric string up to 80 characters long.

            Optional Arguments:
                no: A boolean. Set to True to remove any existing description.

            Returns: True on success

            '''

            cmd = NXCLI._add_no_if_present('description', kwargs)
            if not kwargs.has_key('no'):
                cmd += NXCLI._read_arg(description, 'description', ' %',
                        {str: 'len(description) <= 80'})
            return self._run_cfg_at_ngbr_level(cmd)
        

        def disable_connected_check(self, **kwargs):
            '''
            Disables the connection verification for the directly connected
            peer.

            Arguments: None

            Optional Arguments:
                no: A boolean. Set to true to enable the connection verification
                    for the directly connected peer.

            Returns: True on success
                
            Usage Guidelines: 
                Use this API to disable a check for an exterior Border Gateway 
                Protocol (eBGP) peer that is directly connected to the local 
                router. BGP triggers a connection check automatically for all 
                eBGP peers that are known to be a single hop away, unles you 
                disable this check with this API. BGP does not bring up sessions
                if the check fails. BGP considers an eBGP peer as a single hop 
                away if the eBGP peer does not have the ebgp-multihop option 
                configured (that is, the time-to-live (TTL) value is one).
            
            '''

            cmd = NXCLI._add_no_if_present('disable-connected-check', kwargs)

            return self._run_cfg_at_ngbr_level(cmd)


        def dont_capability_negotiate(self, **kwargs):
            '''
            Turns off the negotiate capability with this neighbor.

            Arguments: None

            Optional args:
                no: A boolean. Set to True to turn on the negotiate capability 
                    with this neighbor.

            Returns: True on success

            '''

            cmd = NXCLI._add_no_if_present('dont-capability-negotiate', kwargs)

            return self._run_cfg_at_ngbr_level(cmd)


        def dynamic_capability(self, **kwargs):
            '''
            Enables the dynamic capability.

            Arguments: None

            Optional Arguments:
                no: A boolean. Set to True to disable the dynamic capability.

            Returns: True on success

            '''

            cmd = NXCLI._add_no_if_present('dynamic-capability', kwargs)
            return self._run_cfg_at_ngbr_level(cmd)


        def cfg_ebgp_multihop(self, ebgp_ttl=None, **kwargs):
            '''
            Accepts and attempts BGP connections to external peers that reside 
            on networks that are not directly connected.

            Arguments:
                ebgp_ttl: An integer, the multihop TTL value. Acceptable values 
                    are 2-255.
            
            Optional Arguments:
                no: A boolean. Set to true to remove this configuration.

            Returns: True on success

            '''

            cmd = NXCLI._add_no_if_present('ebgp-multihop', kwargs)
            if not kwargs.has_key('no'):
                cmd += NXCLI._read_arg(ebgp_ttl, 'ebgp_ttl', ' %',
                        {int: 'ebgp_ttl >= 2 and ebgp_ttl <= 255'})
            return self._run_cfg_at_ngbr_level(cmd)


        def cfg_local_as(self, ASN=None, **kwargs):
            '''
            Configures a router to appear as a member of a second autonomous 
            system (AS) in addition to the real AS of the device. To remove the 
            local AS configuration, set the optional 'no' argument to True.

            Arguments:
                ASN: A string or integer representing the Autonomous System 
                    Number. If integer, range is from 1 to 4294967295. If 
                    string, it should be in this format: 
                    '<1-4294967295>|<1-65535>[.<0-65535>]'. 
                
            Optional Arguments:
                no_prepend: A boolean. Set to True to prevent prepending the
                    local-as number to any routes received from the external
                    Border Gateway Protocol (eBGP) neighbor.
                replace_as: A boolean. Set to True to prepend only the local-as 
                    number to updates to the eBGP neighbor.
                dual_as: A boolean. Set to True to configure the eBGP neighbor 
                    to establish a peering session using the real autonomous 
                    system number (from the local BGP routing process) or by 
                    using the autonomous-system number.
                no: A boolean. Set to True to remove the local AS configuration.

            Returns: True on success

            '''

            cmd = NXCLI._add_no_if_present('local-as', kwargs)
            if not kwargs.has_key('no'):
                cmd += NXCLI._read_arg(ASN, 'ASN', ' %',
                        {int: 'BGPSession.is_valid_asn(ASN)', str: 
                            'BGPSession.is_valid_asn(ASN)', long:
                            'BGPSession.is_valid_asn(ASN)'})
                cmd += NXCLI._read_arg_from_dict(kwargs, 'no_prepend', 
                        ' no-prepend', {bool:None})
                if kwargs.has_key('no_prepend'):
                    cmd += NXCLI._read_arg_from_dict(kwargs, 'replace_as',
                            ' replace-as', {bool:None})
                    if kwargs.has_key('dual_as'):
                        cmd += NXCLI._read_arg_from_dict(kwargs, 'dual_as',
                                ' dual-as', {bool:None})

            return self._run_cfg_at_ngbr_level(cmd)


        def low_memory_exempt(self, **kwargs):
            '''
            Exempts this Border Gateway Protocol (BGP) neighbor from a 
            low-memory shutdown. To make this BGP neighbor eligible for a 
            low-memory shutdown set the optional 'no' argument to True.
                
            Arguments: None

            Optional Arguments:
                no: A boolean. Set to true to make this BGP neighbor eligible 
                    for a low-memory shutdown.

            Returns: True on success

            '''

            cmd = NXCLI._add_no_if_present('low-memory exempt', kwargs)
            return self._run_cfg_at_ngbr_level(cmd)


        def cfg_password(self, password=None, **kwargs):
            '''
            Configures a password for this Border Gateway Protocol (BGP) 
            neighbor. To remove a password set the optional 'no' argument to
            True.

            Arguments: 
                password: a CiscoSecret object.

            Optional Arguments:
                no: a boolean. Set to True to remove an existing password.

            Returns: True on success.

            '''

            cmd = NXCLI._add_no_if_present('password', kwargs)
            if not kwargs.has_key('no'):
                if (isinstance(password, CiscoSecret) and 
                        password.get_key_type() in (0, 7)):
                    cmd += ' %d %s' % (password.get_key_type(), 
                            password.get_key())
                else: 
                    raise ValueError, ('password must be of type '
                        'cisco.CiscoSecret, got %s(%s)' % 
                        (str(password), str(type(password))))
            return self._run_cfg_at_ngbr_level(cmd)


        def cfg_remote_as(self, ASN=None, **kwargs):
            '''
            Specifies the autonomous system (AS) number for this neighbor. To 
            remove an AS number set the optional 'no' argument to True.

            Arguments:
                ASN: A string or integer representing the Autonomous System 
                    Number. If integer, range is from 1 to 4294967295. If 
                    string, it should be in this format: 
                    '<1-4294967295>|<1-65535>[.<0-65535>]'. 
            Optional Arguments:
                no: A boolean. Set to True to remove an AS number.

            Returns: True on success

            '''

            cmd = NXCLI._add_no_if_present('remote-as', kwargs)
            if not kwargs.has_key('no'):
                cmd += NXCLI._read_arg(ASN, 'ASN', ' %',
                        {int: 'BGPSession.is_valid_asn(ASN)', str:
                            'BGPSession.is_valid_asn(ASN)', long:
                            'BGPSession.is_valid_asn(ASN)'})
            return self._run_cfg_at_ngbr_level(cmd)


        def remove_private_as(self, **kwargs):
            '''
            Removes the private AS number from outbound updates. To include the 
            private AS number in outbound updates set the optional 'no' argument
            to True.

            Arguments: None

            Optional Arguments:
                no: A boolean. Set to True to include the private AS number in 
                    outbound updates.
            
            Returns: True on success.

            '''

            cmd = NXCLI._add_no_if_present('remove-private-as', kwargs)
            return self._run_cfg_at_ngbr_level(cmd)


        def shutdown(self, **kwargs):
            '''
            Administratively shuts down this neighbor. All existing 
            configurations will be preserved. To enable this neighbor set the 
            optional 'no' argument to True.

            Arguments: None

            Optional Arguments:
                no: A boolean. Set to True to enable this neighbor.

            Returns: True on success

            '''

            cmd = NXCLI._add_no_if_present('shutdown', kwargs)
            return self._run_cfg_at_ngbr_level(cmd)


        def cfg_timers(self, keepalive_interval=60, holdtime=180, **kwargs):
            '''
            Configures keepalive and hold timers in seconds. Default values are 
            60 seconds for keepalive and 180 seconds for hold time. To set back 
            to the default values set the optional 'no' argument to True.

            Arguments:
                keepalive_interval: An integer ranging from 0 to 3600.
                holdtime: An integer ranging from 0 3600.
            
            Optional Arguments:
                no: A boolean. Set to True to set the timers back to the 
                    default values.

            Returns: True on success

            '''

            cmd = NXCLI._add_no_if_present('timers', kwargs)
            if not kwargs.has_key('no'):
                cmd += NXCLI._read_arg(keepalive_interval, 'keepalive_interval', 
                        ' %', {int: ('keepalive_interval >= 0 and '
                            'keepalive_interval <= 3600')})
                cmd += NXCLI._read_arg(holdtime, 'holdtime', ' %',
                        {int: 'holdtime >= 0 and holdtime <= 3600'})
            return self._run_cfg_at_ngbr_level(cmd)


        def transport_connection_mode_passive(self, **kwargs):
            '''
            Allows a passive connection setup only. To remove this restriction, 
            set the optional 'no' argument to True.
            
            Arguments: None

            Optional Arguments:
                no: A boolean. Set to True to allow all connection setups.

            Returns: True on success

            '''

            cmd = NXCLI._add_no_if_present('transport connection-mode passive',
                    kwargs)

            return self._run_cfg_at_ngbr_level(cmd)


        def cfg_update_source(self, interface=None, **kwargs):
            '''
            Specify the source of the BGP session and updates. The Cisco NX-OS 
            software allows BGP sessions to use any operational interface for 
            TCP connections. To restore the interface assignment to the closest 
            interface, which is called the best local address, set the optional 
            'no' argument to True.

            Arguments: 
                interface: A string representing an interface on the switch. Can
                    be ethernet, loopback, port-channel or a vlan in either 
                    expanded or short forms. e.g. 'e1/1.2', 'Ethernet1/1.2'

            Optional Arguments:
                no: A boolean, set to True to restore the interface assignment 
                    to the best local address.

            Returns: True on success

            '''

            cmd = NXCLI._add_no_if_present('update-source', kwargs)
            if interface != None:
                cmd += NXCLI._read_arg(interface, 'interface', ' %', {str:None})
            elif not kwargs.has_key('no'):
                raise AttributeError, 'Must specify a value for interface arg'
            return self._run_cfg_at_ngbr_level(cmd)


        def set_addr_family(self, ip_version, transmission_type):
            if ip_version in ['ipv4', 'ipv6']:
                self.ip_version = ip_version
            else:
                raise ValueError, 'Invalid IP version specified'
            if transmission_type in ['unicast', 'multicast']:
                self.transmission_type = transmission_type
            else:
                raise ValueError, 'Invalid transmission type specified'


        def _run_cfg_at_ngbr_addr_fam_level(self, cmds):
            if not (hasattr(self, 'ip_version') and 
                    hasattr(self, 'transmission_type')):
                self.ip_version = 'ipv4'
                self.transmission_type = 'unicast'
            string = 'address-family %s %s' % (self.ip_version, 
                    self.transmission_type)
            string += ' ; %s' % cmds
            return self._run_cfg_at_ngbr_level(string)


        def cfg_advertise_map(self, map, **kwargs):
            '''
            Configures Border Gateway Protocol (BGP) conditional advertisement. 
            To remove BGP conditional advertisement, set the optional 'no' 
            argument to True.

            Arguments:
                map: Route map with match statements that the route must pass 
                    before BGP passes theroute to the next route map. The map is
                    a case-sensitive, alphanumeric string up to 63 characters. 
            
            Optional Arguments:
                exist_map: Specifies a route map with match statements for a 
                    prefix list. A prefix in the BGP table must match a prefix 
                    in the prefix list before BGP will advertise the route. The 
                    exist_map is a case-sensitive, alphanumeric string up to 63
                    characters. 
                non_exist_map: Specifies a route map with match statements for 
                    a prefix list. A prefix in the BGP table must not match a 
                    prefix in the prefix list before BGP will advertise the 
                    route. The non_exist_map is a case-sensitive, alphanumeric 
                    string up to 63 characters. 
                no: A boolean, set to True to remove BGP conditional 
                    advertisement.
            
            Returns: True on success

            '''

            cmd = NXCLI._add_no_if_present(NXCLI._read_arg(map, 'map', 
                'advertise-map %', {str: 'len(map) <= 63'}), kwargs)
            if not (kwargs.has_key('exist_map') or 
                    kwargs.has_key('non_exist_map')):
                raise ValueError, ('Must specify either exist_map or '
                        'non_exist_map')
            if kwargs.has_key('exist_map'):
                cmd += NXCLI._read_arg_from_dict(kwargs, 'exist_map', 
                        ' exist-map %', {str: 'len(exist_map) <= 63'})
            elif kwargs.has_key('non_exist_map'):
                cmd += NXCLI._read_arg_from_dict(kwargs, 'non_exist_map',
                        ' non-exist-map %', {str: 'len(non_exist_map) <= 63'})
            return self._run_cfg_at_ngbr_addr_fam_level(cmd)


        def allow_as_in(self, **kwargs):
            '''
            Configures BGP to accept AS paths with this neighbor`s AS present. 
            To remove this configuration set the optional 'no' argument to True.

            Optional Arguments:
                num_occurrences: Number of occurrences of AS number. 
                    num_occurrences is an integer ranging from 1 to 10.
                no: A boolean, set to True to remove this configuration.

            Returns: True on success

            '''

            cmd = NXCLI._add_no_if_present(NXCLI._read_arg_from_dict(kwargs, 
                'num_occurrences', 'allowas-in %', {int: 
                    'num_occurrences >= 1 and num_occurrences <= 10'}), kwargs)
            return self._run_cfg_at_ngbr_addr_fam_level(cmd)


        def default_originate(self, **kwargs):
            '''
            Originate a default toward this neighbor. To remove this 
            configuration set the optional 'no' argument to True.
            
            Optional Arguments:
                route_map: Name of route-map that specifies criteria for 
                    originating default.
                no: A boolean, set to True to remove this configuration.

            Returns: True on success

            '''

            cmd = NXCLI._add_no_if_present('default-originate', kwargs)
            cmd += NXCLI._read_arg_from_dict(kwargs, 'route_map', ' route-map %', {str: 
                'len(route_map) <= 63'})
            return self._run_cfg_at_ngbr_addr_fam_level(cmd)

        
        def cfg_filter_list_in(self, filter, **kwargs):
            '''
            Apply AS-PATH filter list to incoming routes. To remove this 
            configuration set the optional 'no' argument to True.

            Arguments:
                filter: Name of filter list, an alphanumeric string up to 63 
                    characters.

            Optional Arguments:
                no: A boolean, set to True to remove this configuration.

            Returns: True on success

            '''

            cmd = NXCLI._add_no_if_present(NXCLI._read_arg(filter, 'filter', 
                'filter-list % in', {str: 'len(filter) <= 63'}), kwargs)
            return self._run_cfg_at_ngbr_addr_fam_level(cmd)

 
        def cfg_filter_list_out(self, filter, **kwargs):
            '''
            Apply AS-PATH filter list to outgoing routes. To remove this 
            configuration set the optional 'no' argument to True.

            Arguments:
                filter: Name of filter list, an alphanumeric string up to 63 
                    characters.

            Optional Arguments:
                no: A boolean, set to True to remove this configuration.

            Returns: True on success

            '''

            cmd = NXCLI._add_no_if_present(NXCLI._read_arg(filter, 'filter', 
                'filter-list % out', {str: 'len(filter) <= 63'}), kwargs)
            return self._run_cfg_at_ngbr_addr_fam_level(cmd)
                

        def cfg_maximum_prefix(self, limit=None, **kwargs):
            '''
            Configures the maximum number of prefixes from this neighbor. To 
            remove this configuration set the optional 'no' argument to True.

            Arguments:
                limit: Max prefix limit. An integer ranging from 1 to 300,000.
            
            Optional Arguments:
                threshold: Threshold percentage at which to generate a warning. 
                    An integer ranging from 1 to 100.
                restart_interval: Restart the BGP connection after the limit is 
                    exceeded. An integer ranging from 1 to 65535.
                warning_only: A boolean, set to True to only give a warning 
                    message when the limit is exceeded.
                no: A boolean, set to True to remove this configuration.

            Returns: True on success

            '''

            cmd = NXCLI._add_no_if_present('maximum-prefix', kwargs)
            if not kwargs.has_key('no'):
                cmd += NXCLI._read_arg(limit, 'limit', ' %', {int: 
                    'limit >= 1 and limit <= 300000'})
                cmd += NXCLI._read_arg_from_dict(kwargs, 'threshold', ' %', {int:
                    'threshold >= 1 and threshold <= 100'})
                if kwargs.has_key('restart'):
                    cmd += NXCLI._read_arg_from_dict(kwargs, 'restart', 
                            ' restart %', {int: 
                                'restart >= 1 and restart <= 65535'})
                else:
                    cmd += NXCLI._read_arg_from_dict(kwargs, 'warning_only', 
                            ' warning-only', {bool:None})
            return self._run_cfg_at_ngbr_addr_fam_level(cmd)


        def next_hop_self(self, **kwargs):
            '''
            Set our peering address as nexthop. To remove this configuration set
            the optional 'no' argument to True.

            Optional Arguments:
                no: A boolean, set to True to remove this configuration.

            Returns: True on success

            '''

            cmd = NXCLI._add_no_if_present('next-hop-self', kwargs)
            return self._run_cfg_at_ngbr_addr_fam_level(cmd)


        def next_hop_third_party(self, **kwargs):
            '''
            Compute a third-party nexthop if possible. To remove this 
            configuration set the optional 'no' argument to True.

            Optional Arguments:
                no: A boolean, set to True to remove this configuration.

            Returns: True on success

            '''

            cmd = NXCLI._add_no_if_present('next-hop-third-party', kwargs)
            return self._run_cfg_at_ngbr_addr_fam_level(cmd)


        def cfg_prefix_list_in(self, list, **kwargs):
            '''
            Apply a prefix-list to incoming routes. Set the optional 'no' 
            argument to True to remove this configuration.

            Arguments: 
                list: Name of prefix-list, an alphanumeric string up to 63 
                    characters.
            
            Optional Arguments:
                no: A boolean, set to True to remove this configuration

            Returns: True on success
            
            '''

            cmd = NXCLI._add_no_if_present(NXCLI._read_arg(list, 'list',
                'prefix-list % in', {str: 'len(list) <= 63'}), kwargs)
            return self._run_cfg_at_ngbr_addr_fam_level(cmd)


        def cfg_prefix_list_out(self, list, **kwargs):
            '''
            Apply a prefix-list to outgoing routes. Set the optional 'no' 
            argument to True to remove this configuration.

            Arguments: 
                list: Name of prefix-list, an alphanumeric string up to 63 
                    characters.
            
            Optional Arguments:
                no: A boolean, set to True to remove this configuration

            Returns: True on success
            
            '''

            cmd = NXCLI._add_no_if_present(NXCLI._read_arg(list, 'list',
                'prefix-list % out', {str: 'len(list) <= 63'}), kwargs)
            return self._run_cfg_at_ngbr_addr_fam_level(cmd)


        def cfg_route_map_in(self, map, **kwargs):
            '''
            Apply a route-map to incoming routes. Set the optional 'no' 
            argument to True to remove this configuration.

            Arguments: 
                map: Name of the route-map, an alphanumeric string up to 63 
                    characters.
            
            Optional Arguments:
                no: A boolean, set to True to remove this configuration

            Returns: True on success
            
            '''
            
            cmd = NXCLI._add_no_if_present(NXCLI._read_arg(map, 'map',
                'route-map % in', {str: 'len(map) <= 63'}), kwargs)
            return self._run_cfg_at_ngbr_addr_fam_level(cmd)


        def cfg_route_map_out(self, map, **kwargs):
            '''
            Apply a route-map to outgoing routes. Set the optional 'no' 
            argument to True to remove this configuration.

            Arguments: 
                map: Name of the route-map, an alphanumeric string up to 63 
                    characters.
            
            Optional Arguments:
                no: A boolean, set to True to remove this configuration

            Returns: True on success

            '''

            cmd = NXCLI._add_no_if_present(NXCLI._read_arg(map, 'map',
                'route-map % out', {str: 'len(map) <= 63'}), kwargs)
            return self._run_cfg_at_ngbr_addr_fam_level(cmd)


        def route_reflector_client(self, **kwargs):
            '''
            Configure this neighbor as a route reflector client. To remove this 
            configuration set the optional 'no' argument to True.

            Optional Arguments:
                no: A boolean, set to True to remove this configuration.

            Returns: True on success

            '''

            cmd = NXCLI._add_no_if_present('route-reflector-client', kwargs)
            return self._run_cfg_at_ngbr_addr_fam_level(cmd)


        def send_community(self, **kwargs):
            '''
            Send the Border Gateway Protocol (BGP) community attribute to this 
            neighbor. To revert back to the defaults, set the optional 'no' 
            argument to True. 
            
            Optional Argments:
                no: A boolean, set to True to revert back to the defaults.

            Returns: True on success

            '''

            cmd = NXCLI._add_no_if_present('send-community', kwargs)
            return self._run_cfg_at_ngbr_addr_fam_level(cmd)


        def send_community_extended(self, **kwargs):
            '''
            Send the Border Gateway Protocol (BGP) extended community attribute 
            to this neighbor. To revert back to the defaults, set the optional 
            'no' argument to True. 
            
            Optional Argments:
                no: A boolean, set to True to revert back to the defaults.

            Returns: True on success

            '''

            cmd = NXCLI._add_no_if_present('send-community extended', kwargs)
            return self._run_cfg_at_ngbr_addr_fam_level(cmd)


        def soft_reconfiguration_inbound(self, **kwargs):
            '''
            Configures the switch software to start storing Border Gateway 
            Protocol (BGP) peer updates. To not store received updates, set the 
            optional 'no' argument to True.

            Optional Arguments:
                no: A boolean, set to True to stop storing received updates.

            Returns: True on success

            Usage Guidelines:
            Entering this command starts the storage of updates, which is 
            required to do inbound soft reconfiguration. To use soft 
            reconfiguration, or soft reset, without preconfiguration, both BGP 
            peers must support the soft route refresh capability. 

            '''

            cmd = NXCLI._add_no_if_present('soft-reconfiguration inbound', 
                    kwargs)
            return self._run_cfg_at_ngbr_addr_fam_level(cmd)


        def suppress_inactive(self, **kwargs):
            '''
            Advertises the active routes to a Border Gateway Protocol (BGP) peer
            only. To remove the restriction, set the optional 'no' argument to 
            True.

            Optional Arguments:
                no: A boolean, set to True to remove this restriction.

            Returns: True on success

            '''

            cmd = NXCLI._add_no_if_present('suppress-inactive', kwargs)
            return self._run_cfg_at_ngbr_addr_fam_level(cmd)


