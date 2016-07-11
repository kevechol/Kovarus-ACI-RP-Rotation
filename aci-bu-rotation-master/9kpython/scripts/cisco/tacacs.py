from .nxcli import NXCLI
from .feature import Feature

class ShTacas (NXCLI):
    '''
        Runs and parses 'show tacacs+ status'
    '''
    def __init__ (self):
        super (ShTacas, self).__init__ ('show tacacs+ status', False)

    def parse_specific (self):
        if self.get_status () == 0:
            indent_stack = [0]
            for opl in self.processed_output:
                if opl.strip ():
                    #level = self._get_indent_level (indent_stack, opl)
                    key, value = self.key_value_colon_parser (opl)
                    self.__dict__[key] = value

class ShTacasServer (NXCLI):
    '''
        Runs and parses 'show tacacs-server'
    '''
    SHMSG_SRV_START = 'following TACACS+ servers are configured:'

    def __init__ (self):
        super (ShTacasServer, self).__init__ ('show tacacs-server', False)
        self._key_map = {
                'available on port': 'port'
                }

    def _get_srv_container (self):
        try:
            return self._servers
        except AttributeError:
            self._servers = {}
            return self._servers

    def server (self, srv):
        '''
           Returns the dictionary for server srv
        '''
        srv_cntnr = self._get_srv_container ()
        try:
            return srv_cntnr[srv]
        except KeyError:
            print 'Server %s not found' % srv
            return None

    def servers (self):
        '''
           Returns the list of configured servers
        '''
        return self._get_srv_container().keys()

    def parse_specific (self):
        if self.get_status () == 0:
            state = 'key-val'
            server = None
            indent_stack = [0]
            for opl in self.processed_output:
                if opl.strip ():
                    level = self._get_indent_level (indent_stack, opl)
                    if state == 'key-val':
                        try:
                            k, v = self.key_value_colon_parser (opl)
                            self.__dict__[k] = v
                        except:
                            state = 'end-key-val'
                    elif state == 'end-key-val':
                        if opl.strip () == self.SHMSG_SRV_START:
                            state = 'server'
                    elif state == 'server':
                        k, v = self.key_value_colon_parser (opl)
                        if level >= 0: # level going up or same
                            if server is None:
                                server = k
                                self._get_srv_container()[server] = {}
                            else:
                                self._get_srv_container()[server][k] = v
                        else: #level dropped... new server
                            server = k
                            self._get_srv_container()[server] = {}
                else:
                    if state == 'key-val':
                        state = 'end-key-val'



class Tacacs (Feature):
    def __init__ (self):
        self._name = 'tacacs+'
        self._show_name = 'tacacs'

    def _show_server_cli_get (self):
        try:
            return self._ssco
        except AttributeError:
            self._ssco = ShTacasServer ()
            return self._ssco

    def _show_cli_get (self):
        try:
            return self._sco
        except AttributeError:
            self._sco = ShTacas ()
            return self._sco

    def _show_status_get (self):
        s = self._show_cli_get()
        if s.get_status () == 20:
            return None
        s.rerun ()
        return s

    def _show_server_get (self):
        s = self._show_server_cli_get ()
        if s.get_status () == 20:
            return None
        if (datetime.datetime.now() - s.timestamp).total_seconds() > 60:
            s.rerun ()
        return s

    def _is_server_configured (self, server):
        return True

    def servers (self):
        '''
            return: List of configured servers
        '''
        return self._show_server_get ().servers ()

    def server (self, s):
        '''
            return: Information for the server s
        '''
        return self._show_server_get ().server (s)

    def distribute (self, **args):
        '''
            start distribution of the TACACS+ configuration
            changes in the CFS region

            args:
              no=True         Stop distribution
            return: True on success
        '''
        if args.has_key ('no'):
            _n = 'no '
        return self._run_cfg ('%stacacs+ distribute' % _n)

    def add_server (self, server, **args):
        '''
            add_server: Adds TACACS+ servers

            To access a remote TACACS+ server, you must configure the
            IP address or the hostname for the TACACS+ server on the 
            Cisco NX-OS device. You can configure up to 64 TACACS+ servers.

            args:
              server          TACACS+ server`s DNS name or its IP address
              port=<1-65535>  TACACS+ server port
              key=CiscoSecret Global TACACS+ server shared secret
              timeout=#       TACACS+ server timeout period in seconds
              no=True         Delets the server

            Returns: True on success

            Example:
              t = Tacacs ()
              t.add_servers ('20.1.2.5', key=CiscoSecret ('Z75ftWs', 7),
                             timeout=60)
              t.add_servers ('FF01::101')

        '''
        cmd = 'tacacs-server host %s' % server
        if args.has_key ('no'):
            cmd = 'no ' + cmd

        if args.has_key ('port'):
            if isinstance (args['port'], int) and args['port'] > 0 \
                    and args['port'] < 65535:
                cmd += ' port %d' % args['port']
            else:
                raise ValueError, 'arg port must be an int <1-65535>' \
                        'got %s(%s)' % (str(args['port']), str(type(
                            args['port'])))

        if args.has_key ('key'):
            if isinstance (args['key'], CiscoSecret) and args['key'].get_key_type (
                    ) in (0, 7):
                cmd += ' key %d %s' % (args['key'].get_key_type (),
                        args['key'].get_key ())
            else:
                raise ValueError, 'arg Key must be of type cisco.CiscoSecret' \
                        'got %s(%s)' % (str(args['key']), str(type(
                            args['key'])))

        if args.has_key ('timeout'):
            if isinstance (args['timeout'], int):
                cmd += ' timeout %d %s' % (args['timeout'].get_key_type (),
                        args['timeout'].get_key ())
            else:
                raise ValueError, 'arg timeout must be of type int' \
                        'got %s(%s)' % (str(args['timeout']), str(type(
                            args['timeout'])))

        return self._run_cfg (cmd)

    def commit (self):
        '''
            (Optional) Applies the TACACS+ configuration changes in the 
            temporary database to the running configuration and distributes 
            TACACS+ configuration to other NX-OS devices in the network 
            that you have enabled CFS configuration distribution for 
            the TACACS+ feature. 
        '''
        return self._run_cfg ('tacacs+ commit')

    def set_key (self, key, **args):
        '''
            Specifies a TACACS+ key for all TACACS+ server.
            You can specify that the key-value in cisco.CiscoSecret object. If the 
            key is in clear text (0) format or is encrypted (7). The 
            Cisco NX-OS software encrypts a clear text key before 
            saving it to the running configuration. The default format 
            is clear text. The maximum length is 63 characters.

            By default, no secret key is configured. 

            args:
              key             shared key
              no=True         Deletes the key

            Example:
              t = Tacacs ()
              t.set_key (CiscoSecret ('Secret'))
        '''
        if args.has_key ('no'):
            _n = 'no '
        if isinstance (key, CiscoSecret) and key.get_key_type (
                ) in (0, 7):
            return self._run_cfg ('%stacacs-server key %d %s' % (
                _n, keyget_key_type (), key.get_key ()))
        else:
            raise ValueError, 'arg Key must be of type cisco.CiscoSecret' \
                    'got %s(%s)' % (str(key), str(type(key)))

    def add_group (self, name, server, **args):
        '''
            You can specify one or more remote AAA servers to 
            authenticate users using server groups. All members of a 
            group must belong to the TACACS+ protocol. The servers 
            are tried in the same order in which you configure them.

            You can configure these server groups at any time but they 
            only take effect when you apply them to an AAA service.

            Optional args:

              deadtime=<1-1440>      Configures the monitoring dead time. 
                                     The default is 0 minutes. The range is 
                                     from 1 through 1440.

                                     Note If the dead-time interval for a 
                                     TACACS+ server group is greater than 
                                     zero (0), that value takes precedence 
                                     over the global dead-time value 

              source_interface='m0'  Configures a source interface to 
                                     access the TACACS+ servers in the 
                                     server group. You can use Ethernet 
                                     interfaces, loopback interfaces, or 
                                     the management interface (mgmt 0). 
                                     The default is the global source 
                                     interface. 

              vrf=<vrf-name>         Specifies the VRF to use to contact
                                     the servers in the server group. 

              no=True                Deletes the group
        '''

        if args.has_key ('no'):
            _n = 'no '
        cmd = '%saaa group server tacacs+ %s\n' % (_n, name)
        if self._is_server_configured (server):
            cmd += 'server %s\n' % server 
        else:
            raise ValueError, 'Server %s not found, (use add_server to  \
                    add server first)' % server

        if args.has_key ('deadtime'):
            if isinstance (args['deadtime'],
                    int) and args['deadtime'] > 0 and args['deadtime'] \
                            <= 1440:
                cmd += 'deadtime %d\n' % args['deadtime']
            else:
                raise ValueError, 'deadtime shd be int between 1-1440 \
                        got %s(%s)' % (str(args['deadtime']), str (
                            type (args['deadtime'])))

        if args.has_key ('source_interface'):
            if isinstance (args['source_interface'], str):
                #i = Interface (args['source_interface'])
                cmd += 'source-interface %s\n' % args['source_interface']
            else:
                raise ValueError, 'src interface not valid \
                    got %s(%s)' % (str(args['source_interface']), str (
                        type (args['source_interface'])))

        if args.has_key ('vrf'):
            if isinstance (args['vrf'], str):
                cmd += 'use-vrf %s\n' % args['vrf']
            else:
                raise ValueError, 'vrf not valid \
                    got %s(%s)' % (str(args['vrf']), str (
                        type (args['vrf'])))

        return self._run_cfg (cmd)

    def src_interface (self, ifname, **args):
        '''
            You can configure a global source interface for TACACS+ 
            server groups to use when accessing TACACS+ servers. 
            To configure a different source interface for a specific 
            TACACS+ server group, use add_group() API. By default, the 
            Cisco NX-OS software uses any available interface.

            args:
              ifname          Src interface
              no=True         Deletes the key
        '''
        if args.has_key ('no'):
            _n = 'no '
        return self._run_cfg ('%sip tacacs source-interface %s' % (_n,
            ifname))

    def directed_request (self, **args):
        '''
            You can configure the switch to allow the user to specify 
            which TACACS+ server to send the authentication request by 
            enabling the directed-request option. By default, a Cisco 
            NX-OS device forwards an authentication request based on 
            the default AAA authentication method. If you enable this 
            option, the user can log in as username@vrfname:hostname, 
            where vrfname is the VRF to use and hostname is the name 
            of a configured TACACS+ server. 

            args:
              no=True         stops it
        '''
        if args.has_key ('no'):
            _n = 'no '
        return self._run_cfg ('%stacacs-server directed-request' % _n)

    def timeout (self, secs, **args):
        '''
            You can set a global timeout interval that the Cisco NX-OS 
            device waits for responses from all TACACS+ servers before 
            declaring a timeout failure. The timeout interval determines 
            how long the Cisco NX-OS device waits for responses from 
            TACACS+ servers before declaring a timeout failure. 

            args:
              secs            timeout interval
              no=True         remove it
        '''
        if args.has_key ('no'):
            _n = 'no '
        return self._run_cfg ('%stacacs-server timeout %d' % (_n, secs))

    def deadtime (self, mins, **args):
        '''
            You can monitor the availability of TACACS+ servers. 
            These parameters include the username and password to use 
            for the server and an idle timer. The idle timer specifies 
            the interval in which a TACACS+ server receives no requests 
            before the Cisco NX-OS device sends out a test packet. You 
            can configure this option to test servers periodically, or 
            you can run a one-time only test. 

            args:
              mins            deadtime
              no=True         remove it
        '''
        if args.has_key ('no'):
            _n = 'no '
        return self._run_cfg ('%stacacs-server dead-time %d' % (_n, mins))

    def test_server (self, host, **args):
        '''
            You can monitor the availability of TACACS+ servers. 
            These parameters include the username and password to use 
            for the server and an idle timer. The idle timer specifies 
            the interval in which a TACACS+ server receives no requests 
            before the Cisco NX-OS device sends out a test packet. You 
            can configure this option to test servers periodically, or 
            you can run a one-time only test. 
        '''
        cmd = 'tacacs-server host %s test' % host

        if args.has_key ('user_name'):
            if isinstance (args['user_name'], str):
                cmd += ' username %s' % args['user_name']
            else:
                raise ValueError, 'invalid user_name \
                    got %s(%s)' % (str(args['user_name']), str (
                        type (args['user_name'])))

        if args.has_key ('password'):
            if isinstance (args['password'], str):
                cmd += ' password %s' % args['password']
            else:
                raise ValueError, 'invalid password \
                    got %s(%s)' % (str(args['password']), str (
                        type (args['password'])))

        if args.has_key ('idle_time'):
            if isinstance (args['idle_time'], int) and args[
                    'idle_time'] > 0 and args['idle_time'] <= 1440:
                cmd += ' idle_time %d' % args['idle_time']
            else:
                raise ValueError, 'idle_time shd be int between 1-1440 \
                    got %s(%s)' % (str(args['idle_time']), str (
                        type (args['idle_time'])))

        return self._run_cfg (cmd)




