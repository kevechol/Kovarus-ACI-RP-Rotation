from abc import ABCMeta
import re

from .nxcli import NXCLI
from .key import Key
from .section_parser import SectionParser


class ShACL (NXCLI):
    def __init__ (self, proto, name):
        self._name = name
        super (ShACL, self).__init__ ('show %s access-lists %s' % (
            proto, name))
    
    def parse_specific(self):
        k = Key (start=r"^IP access list %s" % self._name)
        spl = SectionParser (self.processed_output, k)
        if spl:
            self.list = [x.strip() for x in spl.sections[0:-1] if x]
        else:
            self.list = []

    def ACEs (self):
        for l in self.list:
            yield l


class ACL (object):
    '''
    A base ACL object, should use IPv4ACL or IPv6ACL to configure each 
    type of ACL appropriately.
    '''
    
    __metaclass__ = ABCMeta
    ace_pat = re.compile (r'^\d+')
    def __init__ (self, proto, name):
        self.proto = proto
        self.name = name
        self._shacl = ShACL (self.proto, self.name)
        #self.load ()
        self.create ()


    def load (self):
        for ace in self._shacl.ACEs ():
            if self.ace_pat.match (ace):
                #self.add_ace_from_string (ace)
                pass
            else:
                #self.add_flags_from_string (ace)
                pass


    def show (self):
        '''
        Show the currently configured entries in this ACL.
        
        Arguments: None

        Returns: Outputs the ACL entries
        '''

        self._shacl.rerun ()
        print self._shacl.get_output ()

    
    def create(self):
        '''
        Create the ACL associated with this object.

        Arguments: None

        Returns: True on success
        '''

        return NXCLI._run_cfg('%s access-list %s' % (self.proto, self.name))

    def delete(self):
        '''
        Delete the ACL associated with this object.

        Arguments: None

        Returns: True on success
        '''

        return NXCLI._run_cfg('no %s access-list %s' % (self.proto, self.name))


    def _add_acl_cfg (self, cfg):
        return NXCLI._run_cfg ('%s access-list %s ; %s' % (
            self.proto, self.name, cfg))


    def _sequence (self, kwargs):
        return NXCLI._read_arg_from_dict (kwargs, 'sequence', '%',
                {int:'sequence >= 1 and sequence <= 4294967295'})


    def set_per_entry_statistic (self, **kwargs):
        '''
        Set the per-entry statistics this ACL. To remove this configuration, set 
        the optional 'no' argument to True.

        Arguments:
            None
        
        Optional Arguments:
            no: A boolean, set to True to remove the per-entry statistics.

        Returns: True on success

        '''
        return self._add_acl_cfg (NXCLI._add_no_if_present (
            'statistics per-entry', kwargs))


    def set_remark (self, remark, **kwargs):
        '''
        Set a remark. To remove a remark, set the optional 'no' argument to 
        True.

        Arguments:
            remark: a string containing the remark
        
        Optional Arguments:
            no: A boolean, set to True to remove a particular remark.
            sequence: an Integer sequence # where the remark will be placed

        Returns: True on success

        '''
        cmd = NXCLI._add_no_if_present(self._sequence(kwargs) + ' remark', 
                kwargs)
        cmd += NXCLI._read_arg(remark, 'remark', ' %', {str: 
            'len(remark) >= 1 and len(remark) <= 100'})
        return self._add_acl_cfg(cmd)


    @staticmethod
    def _parse_ip_for_acl_and_create_str(ip, version=4):
        parsed_ip = re.split('/| ', str(ip))
        cmd = ""

        if str(ip) == 'any':
            cmd += ' any'
        elif len(parsed_ip) == 1:
            cmd += ' host %s' % str(ip)
        else:
            cmd += ' ' + str(ip)

        return cmd


    @staticmethod
    def _parse_port_for_acl_and_create_str(port_qualifier, port):
        valid_qualifier = ['eq', 'gt', 'lt', 'host', 'neg', 'range']
        valid_port = {'bgp':179, 'discard':9, 'exec':512, 'gopher':70, 'klogin':543, 'nntp':119, 'smtp':25, 
                      'telnet':23, 'www':80, 'chargen':19, 'domain':53, 'finger':79, 'hostname':101, 'kshell':544, 
                      'pim-auto-rp':496, 'sunrpc':111, 'time':37, 'cmd':514, 'drip':3949, 'ftp':21,
                      'ident':113, 'login':513, 'pop2':109, 'tacacs':49, 'uucp':540, 'daytime':13, 'echo':7, 'ftp-data':20, 
                      'irc':194, 'lpd':515, 'pop3':110, 'talk':517, 'whois':43}
        cmd = ""
        min_port = None
        max_port = None

        if type(port) is str and valid_port.has_key(port): 
            min_port = valid_port[port]
        if type(port) is list and valid_port.has_key(port[0]) and valid_port.has_key(port[1]): 
            min_port = valid_port[port[0]]
            max_port = valid_port[port[1]]
        if type(port) is list and (0 <= port[0] <= 65535) and (0 <= port[1] <= 65535): 
            min_port = port[0]
            max_port = port[1]
        if type(port) is int and (0 <= port <= 65535):
            min_port = port

        if min_port is None:
            raise AttributeError, 'Invalid port'

        if port_qualifier in valid_qualifier:
            if port_qualifier == 'range':
                cmd += ' range %d %d' % (min_port, max_port)
            else:
                cmd += ' %s %d' % (port_qualifier, min_port)
        else:
            raise AttributeError, 'Invalid port qualifier %s' % port_qualifier

        return cmd

       
    def _permit_or_deny_base(self, type, protocol, source, sport_qualifier, sport, destination, dport_qualifier, dport, kwargs):
        
        cmd = NXCLI._add_no_if_present('%s %s' % (self._sequence(kwargs), type), 
                kwargs)
       
        if (isinstance(self, IPv4ACL)):
            cmd += NXCLI._read_arg(protocol, 'protocol', ' %', {int: 
                'protocol >= 0 and protocol <= 255', str: 
                'protocol in ("ahp", "eigrp", "esp", "gre", "icmp", "igmp", \
                        "ip", "nos", "ospf", "pcp", "pim", "tcp", "udp")'})
            version = 4
        elif (isinstance(self, IPv6ACL)):
            cmd += NXCLI._read_arg(protocol, 'protocol', ' %', {int: 
                'protocol >= 0 and protocol <= 255', str: 
                'protocol in ("icmp", "ipv6", "sctp", "tcp", "udp")'})
            version = 6
        else:
            version = None

        cmd += ACL._parse_ip_for_acl_and_create_str(source, version)
        if sport_qualifier is not None and sport is not None:
            cmd += ACL._parse_port_for_acl_and_create_str(sport_qualifier, sport)
        cmd += ACL._parse_ip_for_acl_and_create_str(destination, version)
        if dport_qualifier is not None and dport is not None:
            cmd += ACL._parse_port_for_acl_and_create_str(dport_qualifier, dport)
        
        if kwargs.has_key('dscp') and kwargs.has_key('precedence'):
            raise AttributeError, 'Cannot specify both dscp and precedence'

        cmd += NXCLI._read_arg_from_dict(kwargs, 'dscp', ' dscp %', 
            {str: 'dscp in ("af11", "af12", "af13", "af21", "af22", "af23", \
            "af31", "af32", "af33", "af41", "af42", "af43", "cs1", "cs2", \
            "cs3", "cs4", "cs5", "cs6", "cs7", "default", "ef")', int: 
            'dscp >= 0 and dscp <= 63'})
        
        if (isinstance(self, IPv4ACL)):
            cmd += NXCLI._read_arg_from_dict(kwargs, 'precedence', ' precedence %',
                {str: 'precedence in ("critical", "flash", "flash-override", \
                        "immediate", "internet", "network", "priority", "routine")', 
                        int: 'precedence >= 0 and precedence <= 7'})
        
        cmd += NXCLI._read_arg_from_dict(kwargs, 'fragments', ' fragments',
            {bool: None})

        if kwargs.has_key('time_range'):
            cmd += ' time-range %s' % kwargs['time_range']

        if kwargs.has_key('packet_length_qualifier') and kwargs.has_key('packet_length'):
            if kwargs['packet_length_qualifier'] in ['eq', 'gt', 'lt', 'neq']:
                cmd += ' packet-length %s %d' % (kwargs['packet_length_qualifier'], kwargs['packet_length'])
            elif kwargs['packet_length_qualifier'] == 'range':
                if len(kwargs['packet_length']) == 2:
                    cmd += ' packet-length range %d %d' % (kwargs['packet_length'][0], kwargs['packet_length'][1])
                else:
                    raise AttributeError, 'Invalid packet length requires two arguments'
            else:
                raise AttributeError, 'Invalid packet length qualifier'

        tcp_match_bits = ['ack', 'established', 'psh', 'syn', 'fin', 'rst', 'urg']
        if protocol == 'tcp' and kwargs.has_key('tcp_match_bit'):
            for bit in kwargs['tcp_match_bit']:
                if bit in tcp_match_bits:
                    cmd += ' %s' % bit
                else:
                    raise AttributeError, 'Invalid tcp bit'

        if protocol != 'tcp' and kwargs.has_key('tcp_match_bit'):
            raise AttributeError, 'Tcp bit not valid for the protocol'
        
        icmp_message_types = [
                'administratively-prohibited', 'host-tos-redirect',
                'net-unreachable', 'router-advertisement', 'alternate-address', 'host-tos-unreachable',
                'network-unknown', 'router-solicitation', 'conversion-error', 'host-unknown', 'no-room-for-option',
                'source-quench', 'dod-host-prohibited', 'host-unreachable', 'option-missing', 'source-route-failed',
                'dod-net-prohibited', 'information-reply', 'time-exceeded', 'information-request', 'packet-too-big',
                'echo', 'parameter-problem', 'timestamp-reply', 'echo-reply', 'mask-reply', 'port-unreachable',
                'timestamp-request', 'mask-request', 'traceroute', 'general-parameter-problem', 'mobile-redirect',
                'precedence-unreachable', 'ttl-exceeded', 'host-isolated', 'net-redirect', 'protocol-unreachable',
                'unreachable', 'host-precedence-unreachable', 'net-tos-redirect', 'reassembly-timeout',
                'host-redirect', 'net-tos-unreachable', 'redirect'
                            ]
        if protocol == 'icmp' and kwargs.has_key('icmp_message_type'):
            if kwargs['icmp_message_type'] in icmp_message_types:
                cmd += ' %s' % kwargs['icmp_message_type'] 
            else:
                raise AttributeError, 'Invalid icmp message type'

        if protocol != 'icmp' and kwargs.has_key('icmp_message_type'):
            raise AttributeError, 'Icmp message type not valid for the protocol'

        return self._add_acl_cfg(cmd)

       
    def delete_entry(self, sequence):
        '''
        Delete a particular entry in this ACL by specifying the sequence number.

        Arguments:
            sequence: An integer ranging from <1-4294967295>.

        Returns: True on success
        '''

        return self._add_acl_cfg('no ' + str(sequence))



class IPv4ACL (ACL):
    '''
    Use this class to configure the IPv4 ACL
    '''
    def __init__ (self, name):
        super (IPv4ACL, self).__init__ ('ip', name)
    
    
    def permit(self, protocol, source, destination, sport_qualifier=None, sport=None, dport_qualifier=None, dport=None, **kwargs):
        '''
        Specify packets to forward. To stop forwarding particular packet types 
        set the optional 'no' argument to True.

        Arguments:
            protocol: An integer ranging from <0-255> representing the protocol
                number, or a string representing the protocol name.
            source: A string representing the source ip address or network in 
                either CIDR notation or dotted quad. E.g. 'any', '192.0.2.0', 
                '192.0.2.0/24', '192.0.2.0 255.255.255.0'. For a network can 
                also specify wildcard bits. E.g. '192.0.2.0 255.0.7.255'
            sport_qualifier: A string that qualifies the source port. 
                Valid qualifiers are: eq, gt, lt, host, neg, range
            sport: A source port or a range of source ports in an array. Port needs
                to be a number or its string representation. Valid string representations
                are: bgp, discard, exec, gopher, klogin, nntp, smtp, telnet, www, chargen,
                domain, finger, hostname, kshell, pim-auto-rp, sunrpc, time, cmd, drip, ftp,
                ident, login, pop2, tacacs, uucp, daytime, echo, ftp-data, irc, lpd, pop3,
                talk, whois
            destination: A string representing the source ip address or network in 
                either CIDR notation or dotted quad. E.g. 'any', '192.0.2.0', 
                '192.0.2.0/24', '192.0.2.0 255.255.255.0'. For a network can 
                also specify wildcard bits. E.g. '192.0.2.0 255.0.7.255'
            dport_qualifier: A string that qualifies the destination port.
                Valid qualifiers are: eq, gt, lt, host, neg, range
            dport: A source port or a range of destination ports in an array. Port needs
                to be a number or its string representation. Valid string representations
                are: bgp, discard, exec, gopher, klogin, nntp, smtp, telnet, www, chargen,
                domain, finger, hostname, kshell, pim-auto-rp, sunrpc, time, cmd, drip, ftp,
                ident, login, pop2, tacacs, uucp, daytime, echo, ftp-data, irc, lpd, pop3,
                talk, whois

        Optional Arguments:
            sequence: an integer ranging from <1-4294967295> where this rule 
                will be placed.
            dscp: An integer ranging from <0-63> or a string represting the type 
                of dscp. Use this to match packets with a particular dscp value.
            fragments: A boolean, set to True to check non-initial fragments.
            precedence: An integer ranging from <0-7> or a string representing 
                the precedence type. Use this to match packets with a particular
                precedence value.
            time_range: A time range name.
            packet_length_qualifier: Match packets based on layer 3 packet length.
                Valid qualifiers are: eq, gt, lt, neq, range
            packet_length: Packet length in between 20 and 9210.
                If qualifier is range, min and max length needs to be provided through
                a list.
            tcp_match_bit: TCP match bits in a list.
                Valid bits are: ack, established, psh, syn, fin, rst, urg
            icmp_message_type: Icmp packet message type.
                Valid message types are: administratively-prohibited, host-tos-redirect,
                net-unreachable, router-advertisement, alternate-address, host-tos-unreachable,
                network-unknown, router-solicitation, conversion-error, host-unknown, no-room-for-option,
                source-quench, dod-host-prohibited, host-unreachable, option-missing, source-route-failed,
                dod-net-prohibited, information-reply, time-exceeded, information-request, packet-too-big,                
                echo, parameter-problem, timestamp-reply, echo-reply, mask-reply, port-unreachable,
                timestamp-request, mask-request, traceroute, general-parameter-problem, mobile-redirect,
                precedence-unreachable, ttl-exceeded, host-isolated, net-redirect, protocol-unreachable,
                unreachable, host-precedence-unreachable, net-tos-redirect, reassembly-timeout, 
                host-redirect, net-tos-unreachable, redirect
            no: A boolean, set to True to stop forwarding particular packet 
                types.
        '''

        return self._permit_or_deny_base('permit', protocol, source, sport_qualifier, sport,
                destination, dport_qualifier, dport, kwargs)


    def deny(self, protocol, source, destination, sport_qualifier=None, sport=None, dport_qualifier=None, dport=None, **kwargs):
        '''
        Specify packets to reject. To stop rejecting particular packet types 
        set the optional 'no' argument to True.

        Arguments:
            protocol: An integer ranging from <0-255> representing the protocol
                number, or a string representing the protocol name.
            source: A string representing the source ip address or network in 
                either CIDR notation or dotted quad. E.g. 'any', '192.0.2.0', 
                '192.0.2.0/24', '192.0.2.0 255.255.255.0'. For a network can 
                also specify wildcard bits. E.g. '192.0.2.0 255.0.7.255'
            sport_qualifier: A string that qualifies the source port.
                Valid qualifiers are: eq, gt, lt, host, neg, range
            sport: A source port or a range of source ports in an array. Port needs
                to be a number or its string representation. Valid string representations
                are: bgp, discard, exec, gopher, klogin, nntp, smtp, telnet, www, chargen,
                domain, finger, hostname, kshell, pim-auto-rp, sunrpc, time, cmd, drip, ftp,
                ident, login, pop2, tacacs, uucp, daytime, echo, ftp-data, irc, lpd, pop3,
                talk, whois
            destination: A string representing the source ip address or network in 
                either CIDR notation or dotted quad. E.g. 'any', '192.0.2.0', 
                '192.0.2.0/24', '192.0.2.0 255.255.255.0'. For a network can 
                also specify wildcard bits. E.g. '192.0.2.0 255.0.7.255'
            dport_qualifier: A string that qualifies the destination port.
                Valid qualifiers are: eq, gt, lt, host, neg, range
            dport: A source port or a range of destination ports in an array. Port needs
                to be a number or its string representation. Valid string representations
                are: bgp, discard, exec, gopher, klogin, nntp, smtp, telnet, www, chargen,
                domain, finger, hostname, kshell, pim-auto-rp, sunrpc, time, cmd, drip, ftp,
                ident, login, pop2, tacacs, uucp, daytime, echo, ftp-data, irc, lpd, pop3,
                talk, whois

        Optional Arguments:
            sequence: an integer ranging from <1-4294967295> where this rule 
                will be placed.
            dscp: An integer ranging from <0-63> or a string represting the type 
                of dscp. Use this to match packets with a particular dscp value.
            fragments: A boolean, set to True to check non-initial fragments.
            precedence: An integer ranging from <0-7> or a string representing 
                the precedence type. Use this to match packets with a particular
                precedence value.
            time-range: A time range name.
            packet_length_qualifier: Match packets based on layer 3 packet length.
                Valid qualifiers are: eq, gt, lt, neq, range
            packet_length: Packet length in between 20 and 9210.
                If qualifier is range, min and max length needs to be provided through
                a list.
            tcp_match_bit: TCP match bits in a list.
                Valid bits are: ack, established, psh, syn, fin, rst, urg
            icmp_message_type: Icmp packet message type.
                Valid message types are: administratively-prohibited, host-tos-redirect,
                net-unreachable, router-advertisement, alternate-address, host-tos-unreachable,
                network-unknown, router-solicitation, conversion-error, host-unknown, no-room-for-option,
                source-quench, dod-host-prohibited, host-unreachable, option-missing, source-route-failed,
                dod-net-prohibited, information-reply, time-exceeded, information-request, packet-too-big,                
                echo, parameter-problem, timestamp-reply, echo-reply, mask-reply, port-unreachable,
                timestamp-request, mask-request, traceroute, general-parameter-problem, mobile-redirect,
                precedence-unreachable, ttl-exceeded, host-isolated, net-redirect, protocol-unreachable,
                unreachable, host-precedence-unreachable, net-tos-redirect, reassembly-timeout, 
                host-redirect, net-tos-unreachable, redirect
            no: A boolean, set to True to stop rejecting particular packet 
                types.

        Returns: True on Success

        '''

        return self._permit_or_deny_base('deny', protocol, source, sport_qualifier, sport,
                destination, dport_qualifier, dport, kwargs)



class IPv6ACL (ACL):
    '''
    Use this class to configure the IPv6 ACL
    '''
    def __init__ (self, name):
        super (IPv6ACL, self).__init__ ('ipv6', name)


    def permit(self, protocol, source, destination, sport_qualifier=None, sport=None, dport_qualifier=None, dport=None, **kwargs):
        '''
        Specify packets to forward. To stop forwarding particular packet types 
        set the optional 'no' argument to True.

        Arguments:
            protocol: An integer ranging from <0-255> representing the protocol
                number, or a string representing the protocol name.
            source: A string representing the source ip network in CIDR 
                notation. E.g. '1:1::1:1/32'. 
            sport_qualifier: A string that qualifies the source port.
                Valid qualifiers are: eq, gt, lt, host, neg, range
            sport: A source port or a range of source ports in an array. Port needs
                to be a number or its string representation. Valid string representations
                are: bgp, discard, exec, gopher, klogin, nntp, smtp, telnet, www, chargen,
                domain, finger, hostname, kshell, pim-auto-rp, sunrpc, time, cmd, drip, ftp,
                ident, login, pop2, tacacs, uucp, daytime, echo, ftp-data, irc, lpd, pop3,
                talk, whois
            destination: A string representing the destination ip network in 
                CIDR notation. E.g. '1:1::1:1/32'. 
            dport_qualifier: A string that qualifies the destination port.
                Valid qualifiers are: eq, gt, lt, host, neg, range
            dport: A source port or a range of destination ports in an array. Port needs
                to be a number or its string representation. Valid string representations
                are: bgp, discard, exec, gopher, klogin, nntp, smtp, telnet, www, chargen,
                domain, finger, hostname, kshell, pim-auto-rp, sunrpc, time, cmd, drip, ftp,
                ident, login, pop2, tacacs, uucp, daytime, echo, ftp-data, irc, lpd, pop3,
                talk, whois

        Optional Arguments:
            sequence: an integer ranging from <1-4294967295> where this rule 
                will be placed.
            dscp: An integer ranging from <0-63> or a string represting the type 
                of dscp. Use this to match packets with a particular dscp value.
            fragments: A boolean, set to True to check non-initial fragments.
            time-range: A time range name.
            packet_length_qualifier: Match packets based on layer 3 packet length.
                Valid qualifiers are: eq, gt, lt, neq, range
            packet_length: Packet length in between 20 and 9210.
                If qualifier is range, min and max length needs to be provided through
                a list.
            tcp_match_bit: TCP match bits in a list.
                Valid bits are: ack, established, psh, syn, fin, rst, urg
            icmp_message_type: Icmp packet message type.
                Valid message types are: administratively-prohibited, host-tos-redirect,
                net-unreachable, router-advertisement, alternate-address, host-tos-unreachable,
                network-unknown, router-solicitation, conversion-error, host-unknown, no-room-for-option,
                source-quench, dod-host-prohibited, host-unreachable, option-missing, source-route-failed,
                dod-net-prohibited, information-reply, time-exceeded, information-request, packet-too-big,                
                echo, parameter-problem, timestamp-reply, echo-reply, mask-reply, port-unreachable,
                timestamp-request, mask-request, traceroute, general-parameter-problem, mobile-redirect,
                precedence-unreachable, ttl-exceeded, host-isolated, net-redirect, protocol-unreachable,
                unreachable, host-precedence-unreachable, net-tos-redirect, reassembly-timeout, 
                host-redirect, net-tos-unreachable, redirect
            no: A boolean, set to True to stop forwarding particular packet 
                types.

        '''

        return self._permit_or_deny_base('permit', protocol, source, sport_qualifier, sport,
                destination, dport_qualifier, dport, kwargs)


    def deny(self, protocol, source, destination, sport_qualifier=None, sport=None, dport_qualifier=None, dport=None, **kwargs):
        '''
        Specify packets to reject. To stop rejecting particular packet types 
        set the optional 'no' argument to True.

        Arguments:
            protocol: An integer ranging from <0-255> representing the protocol
                number, or a string representing the protocol name.
            source: A string representing the source ip network in CIDR 
                notation. E.g. '1:1::1:1/32'. 
            sport_qualifier: A string that qualifies the source port.
                Valid qualifiers are: eq, gt, lt, host, neg, range
            sport: A source port or a range of source ports in an array. Port needs
                to be a number or its string representation. Valid string representations
                are: bgp, discard, exec, gopher, klogin, nntp, smtp, telnet, www, chargen,
                domain, finger, hostname, kshell, pim-auto-rp, sunrpc, time, cmd, drip, ftp,
                ident, login, pop2, tacacs, uucp, daytime, echo, ftp-data, irc, lpd, pop3,
                talk, whois
            destination: A string representing the destination ip network in 
                CIDR notation. E.g. '1:1::1:1/32'. 
            dport_qualifier: A string that qualifies the destination port.
                Valid qualifiers are: eq, gt, lt, host, neg, range
            dport: A source port or a range of destination ports in an array. Port needs
                to be a number or its string representation. Valid string representations
                are: bgp, discard, exec, gopher, klogin, nntp, smtp, telnet, www, chargen,
                domain, finger, hostname, kshell, pim-auto-rp, sunrpc, time, cmd, drip, ftp,
                ident, login, pop2, tacacs, uucp, daytime, echo, ftp-data, irc, lpd, pop3,
                talk, whois

        Optional Arguments:
            sequence: an integer ranging from <1-4294967295> where this rule 
                will be placed.
            dscp: An integer ranging from <0-63> or a string represting the type 
                of dscp. Use this to match packets with a particular dscp value.
            fragments: A boolean, set to True to check non-initial fragments.
            time-range: A time range name.
            packet_length_qualifier: Match packets based on layer 3 packet length.
                Valid qualifiers are: eq, gt, lt, neq, range
            packet_length: Packet length in between 20 and 9210.
                If qualifier is range, min and max length needs to be provided through
                a list.
            tcp_match_bit: TCP match bits in a list.
                Valid bits are: ack, established, psh, syn, fin, rst, urg
            icmp_message_type: Icmp packet message type.
                Valid message types are: administratively-prohibited, host-tos-redirect,
                net-unreachable, router-advertisement, alternate-address, host-tos-unreachable,
                network-unknown, router-solicitation, conversion-error, host-unknown, no-room-for-option,
                source-quench, dod-host-prohibited, host-unreachable, option-missing, source-route-failed,
                dod-net-prohibited, information-reply, time-exceeded, information-request, packet-too-big,                
                echo, parameter-problem, timestamp-reply, echo-reply, mask-reply, port-unreachable,
                timestamp-request, mask-request, traceroute, general-parameter-problem, mobile-redirect,
                precedence-unreachable, ttl-exceeded, host-isolated, net-redirect, protocol-unreachable,
                unreachable, host-precedence-unreachable, net-tos-redirect, reassembly-timeout, 
                host-redirect, net-tos-unreachable, redirect
            no: A boolean, set to True to stop rejecting particular packet 
                types.

        Returns: True on Success

        '''

        return self._permit_or_deny_base('deny', protocol, source, sport_qualifier, sport,
                destination, dport_qualifier, dport, kwargs)




