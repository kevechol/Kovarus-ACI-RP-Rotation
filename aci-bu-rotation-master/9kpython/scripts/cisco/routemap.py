from .nxcli import *

class RouteMap(object):
    '''
    Use this class to create and configure route-map entries.
    '''

    def __init__(self, name, sequence, type='permit'):
        '''
        Initializes a RouteMap object with the specified name, sequence 
        number, and type and returns the new object.

        Arguments:
            name: The name of the route-map, a string.
            sequence: The sequence number of the RouteMap, an integer.
            type: The type of routemap, can be either 'permit' or 'deny'.

        Returns: RouteMap object on success

        '''
        
        self.name = name
        self.type = type
        self.sequence = sequence


    def _run_cfg_at_routemap_level(self, cmds):
        string = 'route-map %s %s %s' % (self.name, self.type, self.sequence)
        string += ' ; %s' % cmds
        return NXCLI._run_cfg(string)


    def create(self, **kwargs):
        '''
        Create the routemap entry associated with this RouteMap object.

        Arguments: None

        Returns: True on success

        '''

        return self._run_cfg_at_routemap_level('')


    def delete(self):
        '''
        Delete the routemap entry associated with this RouteMap object.

        Arguments: None

        Returns: True on success

        '''
        string = 'no route-map %s %s %s' % (self.name, self.type, self.sequence)
        return NXCLI._run_cfg(string)


    def add_description(self, description=None, **kwargs):
        '''
        Add a description to the route-map.

        Arguments:
            description: A string up to 90 characters long.

        Optional Arguments:
            no: A boolean, set to true to remove any existing description.

        Returns: True on success

        '''

        cmd = NXCLI._add_no_if_present('description', kwargs)
        if not kwargs.has_key('no'):
            if description != None:
                cmd += NXCLI._read_arg(description, 'description', 
                                                ' %', {str: 'len(description) <= 90'})
            else:
                raise AttributeError, 'Must specify a value for description arg'
        return self._run_cfg_at_routemap_level(cmd)


    def match_as_number(self, as_number, **kwargs):
        '''
        Match BGP Peer AS Number

        Arguments: 
            as_number: A string in the following format: <AA4>

        Optional Arguments:
            no: A boolean, set to True to remove a BGP peer from the match list

        Returns: True on success

        '''
        
        cmd = NXCLI._add_no_if_present(NXCLI._read_arg(as_number, 'as_number', 
            'match as-number %', {str:None, int:None}), kwargs)
        return self._run_cfg_at_routemap_level(cmd)

    
    def match_as_path_list(self, lists, **kwargs):
        '''
        Match AS path access list(s).

        Arguments:
            lists: A string which is a space separated list of AS path list 
                names
        
        Optional Arguments:
            no: A boolean, set to True to remove an AS path list from the match
                list

        Returns: True on success

        '''

        cmd = NXCLI._add_no_if_present(NXCLI._read_arg(lists, 'lists',
            'match as-number as-path-list %', {str:None}), kwargs)
        return self._run_cfg_at_routemap_level(cmd)


    def match_as_path(self, lists, **kwargs):
        '''
        TODO: What is the difference between above API and this one?
        Match AS path access list(s).

        Arguments:
            lists: A string which is a space separated list of AS path list 
                names
        
        Optional Arguments:
            no: A boolean, set to True to remove an AS path list from the match
                list

        Returns: True on success

        '''

        cmd = NXCLI._add_no_if_present(NXCLI._read_arg(lists, 'lists',
            'match as-path %', {str:None}), kwargs)
        return self._run_cfg_at_routemap_level(cmd)


    def match_community(self, lists, **kwargs):
        '''
        Match BGP community list(s).

        Arguments:
            lists: A string which is a space separated list of community list 
                names

        Optional args:
            exact_match: A boolean, set to True to do exact matching of 
                communities
            no: A boolean, set to True to remove a community list from the 
                match list

        Returns: True on success

        '''

        cmd = NXCLI._add_no_if_present(NXCLI._read_arg(lists, 'lists',
            'match community %', {str:None}), kwargs)
        if kwargs.has_key('exact_match'):
            cmd += NXCLI._read_arg_from_dict(kwargs, 'exact_match', 
                    ' exact-match', {bool:None})
        return self._run_cfg_at_routemap_level(cmd)


    def match_extcommunity(self, lists, **kwargs):
        '''
        Match BGP Extended community list(s).

        Arguments:
            lists: A string which is a space separated list of Extended 
                community list names

        Optional args:
            exact_match: A boolean, set to True to do exact matching of 
                communities
            no: A boolean, set to True to remove a community list from the 
                match list

        Returns: True on success

        '''

        cmd = NXCLI._add_no_if_present(NXCLI._read_arg(lists, 'lists',
            'match extcommunity %', {str:None}), kwargs)
        if kwargs.has_key('exact_match'):
            cmd += NXCLI._read_arg_from_dict(kwargs, 'exact_match', 
                    ' exact-match', {bool:None})
        return self._run_cfg_at_routemap_level(cmd)
    
    
    def match_interface(self, interface, **kwargs):
        '''
        Match first hop interface of route.

        Arguments:
            interface: A string representing an interface on the switch. Can
                be ethernet, loopback, mgmt, port-channel or a vlan in either 
                expanded or short forms. e.g. 'e1/1.2', 'Ethernet1/1.2'
        
        Optional args:
            no: A boolean, set to True to remove an interface from the match 
                list

        Returns: True on success

        '''

        cmd = NXCLI._add_no_if_present(NXCLI._read_arg(interface, 'interface',
            'match interface %', {str:None}), kwargs)
        return self._run_cfg_at_routemap_level(cmd)


    def match_ip_access_list(self, lists, **kwargs):
        '''
        Match IP access list(s).

        Arguments:
            list: A IP access list name.

        Optional args:
            no: A boolean, set to True to remove an IP access list from the 
                match list.

        Returns: True on success

        '''

        cmd = NXCLI._add_no_if_present(NXCLI._read_arg(lists, 'lists',
            'match ip address %', {str:None}), kwargs)
        return self._run_cfg_at_routemap_level(cmd)


    def match_ip_prefix_list(self, lists, **kwargs):
        '''
        Match IP prefix list(s).

        Arguments:
            lists: A string which is a space separated list of IP prefix list 
                names.

        Optional Arguments:
            no: A boolean, set to True to remove an IP prefix list from the 
                match list.

        Returns: True on success

        '''

        cmd = NXCLI._add_no_if_present(NXCLI._read_arg(lists, 'lists',
            'match ip address prefix-list %', {str:None}), kwargs)
        return self._run_cfg_at_routemap_level(cmd)


    def match_ipv6_access_list(self, list, **kwargs):
        '''
        Match IPV6 access list(s).

        Arguments:
            list: A IPV6 access list name.

        Optional args:
            no: A boolean, set to True to remove an IPV6 access list from the 
                match list.

        Returns: True on success

        '''

        cmd = NXCLI._add_no_if_present(NXCLI._read_arg(list, 'list',
            'match ipv6 address %', {str:None}), kwargs)
        return self._run_cfg_at_routemap_level(cmd)


    def match_ipv6_prefix_list(self, lists, **kwargs):
        '''
        Match IPV6 prefix list(s).

        Arguments:
            lists: A string which is a space separated list of IPV6 prefix list 
                names.

        Optional Arguments:
            no: A boolean, set to True to remove an IPV6 prefix list from the 
                match list.

        Returns: True on success

        '''

        cmd = NXCLI._add_no_if_present(NXCLI._read_arg(lists, 'lists',
            'match ipv6 address prefix-list %', {str:None}), kwargs)
        return self._run_cfg_at_routemap_level(cmd)


    def match_packet_length(self, min=None, max=None, **kwargs):
        '''
        Match a range of packet lengths.

        Arguments:
            min: An integer ranging from 0 to 2147483647.
            max: An integer ranging from 0 to 2147483647.

        Optional Arguments:
            no: A boolean, set to True to remove packet length matching.

        Returns: True on success

        '''

        cmd = NXCLI._add_no_if_present('match length', kwargs)
        if min != None:
            cmd += NXCLI._read_arg(min, 'min', ' %', {int: 
            'min >= 0 and min <= 2147483647'})
        elif not kwargs.has_key('no'):
            raise AttributeError, 'Must specify a value for min arg'
        if max != None:
            cmd += NXCLI._read_arg(max, 'max', ' %', {int: 
            'max >= 0 and max <= 2147483647'})
        elif not kwargs.has_key('no'):
            raise AttributeError, 'Must specify a value for max arg'

        return self._run_cfg_at_routemap_level(cmd)


    def match_mac_list(self, lists, **kwargs):
        '''
        Match mac-list(s).

        Arguments:
            lists: A string which is a space separated list of mac-list names.

        Optional Arguments:
            no: A boolean, set to True to remove a mac-list from the match list.

        Returns: True on success

        '''

        cmd = NXCLI._add_no_if_present(NXCLI._read_arg(lists, 'lists',
            'match mac-list %', {str:None}), kwargs)
        return self._run_cfg_at_routemap_level(cmd)


    def match_route_type(self, **kwargs):
        '''
        Match route-type of route.

        Optional Arguments:
            external: A bool, set to True to match external routes (BGP, 
                EIGRP and OSPF type 1/2)
            internal: A bool, set to True to match internal routes (including
                OSPF intra/inter area) 
            level_1: A bool, set to True to match IS-IS level-1 routes
            level_2: A bool, set to True to match IS_IS level-2 routes
            local: A bool, set to True to match locally generated routes
            nssa_external: A boolean, set to True to match Nssa-external routes
                (OSPF type 1/2)
            type_1: A bool, set to True to match OSPF external type 1 routes
            type_2: A bool, set to True to match OSPF external type 2 routes
            intra_area: A bool, set to True to match OSPF intra area route
            inter_area: A bool, set to True to match OSPF inter area route
            no: A bool, set to True to stop matching the route-type of any 
                other parameter that was sent in

        Returns: True on success

        '''

        cmd = NXCLI._add_no_if_present('match route-type', kwargs)

        args_map = { 'external' : 'external', 'internal' : 'internal',
                     'level_1' : 'level-1', 'level_2' : 'level-2',
                     'local' : 'local', 'nssa_external' : 'nssa-external',
                     'inter_area' : 'inter-area', 'intra_area' : 'intra-area',
                     'type_1' : 'type-1', 'type_2' : 'type-2'}

        has_args = 0
        for key in kwargs.keys():
            if kwargs[key]:
                try:
                    cmd += ' %s' % args_map[key]
                    has_args = 1
                except:
                    raise AttributeError, 'Invalid attribute %s' % key

        if not has_args:
            raise AttributeError, 'Must specify at least one route type'

        return self._run_cfg_at_routemap_level(cmd)


    def match_source_protocol(self, lists, **kwargs):
        '''
        Match source protocol.

        Arguments:
            lists: A string which is a space separated list of protocol instance
                names.

        Optional Arguments:
            no: A boolean, set to True to remove a source protocol from the 
                match list.

        Returns: True on success.

        '''

        cmd = NXCLI._add_no_if_present(NXCLI._read_arg(lists, 'lists',
            'match source-protocol %', {str:None}), kwargs)
        return self._run_cfg_at_routemap_level(cmd)


    def match_tag(self, lists, **kwargs):
        '''
        Match tag of route.

        Arguments:
            lists: A string which is a space separated list of tags where each 
                tag is <0-4294967295>.
        
        Optional args:
            no: A boolean, set to True to remove a tag from the match list.

        Returns: True on success.

        '''

        cmd = NXCLI._add_no_if_present(NXCLI._read_arg(lists, 'lists', 
            'match tag %', {str:None}), kwargs)
        return self._run_cfg_at_routemap_level(cmd)


    def match_vlan(self, lists, **kwargs):
        '''
        Match VLAN ID(s).

        Arguments:
            lists: A string which is a comma separated list of VLANs and/or VLAN
                ranges where each VLAN can range from <1-3967, 4048-4093>. e.g. 
                1-5, 10 or 2-5,7-19.
        
        Optional Arguments:
            no: A boolean, set to True to remove a list of VLANs and/or VLAN 
                ranges from the match list.

        Returns: True on success.

        '''

        cmd = NXCLI._add_no_if_present(NXCLI._read_arg(lists, 'lists',
            'match vlan %', {str:None}), kwargs)
        return self._run_cfg_at_routemap_level(cmd)


    def set_as_path_prepend(self, list, **kwargs):
        '''
        Prepend string for a BGP AS-path attribute.

        Arguments:
            list: A string which is a space separated list of ASes where each AS
                is in the following format: <1-4294967295>|<1-65535>[.<0-65535>]

        Optional Arguments:
            no: A boolean, set to True to remove ASes from the prepend string.

        Returns: True on success.

        '''

        cmd = NXCLI._add_no_if_present(NXCLI._read_arg(list, 'list', 
            'set as-path prepend %', {str:None}), kwargs)
        return self._run_cfg_at_routemap_level(cmd)


    def set_as_path_tag(self, **kwargs):
        '''
        Set the tag as an AS-path attribute.

        Arguments: None

        Optional Arguments:
            no: A boolean, set to True to remove this configuration.

        Returns: True on success.

        '''

        cmd = NXCLI._add_no_if_present('set as-path tag', kwargs)
        return self._run_cfg_at_routemap_level(cmd)


    def set_comm_list_delete(self, list, **kwargs):
        '''
        Set BGP community list (for deletion).

        Arguments:
            list: A string up to 63 characters representing a community list 
                name.

        Optional Arguments:
            no: A boolean, set to True to remove this configuration.

        Returns: True on success.

        '''

        cmd = NXCLI._add_no_if_present(NXCLI._read_arg(list, 'list',
            'set comm-list % delete', {str: None}), kwargs)
        return self._run_cfg_at_routemap_level(cmd)



    def set_extcomm_list_delete(self, list, **kwargs):
        '''
        Set BGP External community list (for deletion).

        Arguments:
            list: A string up to 63 characters representing a external community 
                list name.

        Optional Arguments:
            no: A boolean, set to True to remove this configuration.

        Returns: True on success.

        '''

        cmd = NXCLI._add_no_if_present(NXCLI._read_arg(list, 'list',
            'set extcomm-list % delete', {str: None}), kwargs)
        return self._run_cfg_at_routemap_level(cmd)


    def set_forwarding_address(self, **kwargs):
        '''
        Set the forwarding address.

        Arguments: None

        Optional Arguments:
            no: A boolean, set to True to remove this configuration.

        Returns: True on success.

        '''

        cmd = NXCLI._add_no_if_present('set forwarding-address', kwargs)
        return self._run_cfg_at_routemap_level(cmd)


    def set_vrf(self, vrf, **kwargs):
        '''
        Set the VRF for next-hop resolution.

        Arguments: 
            vrf: A string representing an existing VRF on the switch.

        Optional Arguments:
            no: A boolean, set to True to remove a VRF from next-hop resolution.

        Returns: True on success.

        '''
        
        cmd = NXCLI._add_no_if_present(NXCLI._read_arg(vrf, 'vrf', 'set vrf %',
            {str:None}), kwargs)
        return self._run_cfg_at_routemap_level(cmd)

    
    def set_weight(self, weight, **kwargs):
        '''
        Set BGP weight for routing table.

        Arguments:
            weight: An integer ranging from <-65535>

        Optional Arguments:
            no: A boolean, set to True to remove this configuration

        Returns: True on success.

        '''
        
        cmd = NXCLI._add_no_if_present(NXCLI._read_arg(weight, 'weight',
            'set weight %', {int: 'weight >= 0 and weight <= 65535'}), kwargs)
        return self._run_cfg_at_routemap_level(cmd)



