from .nxcli import *
from .interface import *

class System(object):
    ''' class to provide miscellaneous system configuration
    '''

    def _run_cfg (self, cmds):
        return NXCLI._run_cfg (cmds)

    def _run (self, cmds):
        status, output = nxcli(cmds)
        return output


    def set_hostname(self, name=None):
        ''' set the hostname of the switch
        '''
        try: 
            if name:
                return self._run_cfg("hostname " + name)
            else:
                return self._run_cfg("no hostname")
        except Exception as e:
            print("Exception caught:\n" + str(e) + "\n")
            pass


    def get_hostname(self):
        ''' get the hostname of the switch
        '''
        return self._run("show hostname").rstrip()


    def set_banner(self, banner=None):
        if banner:
            return self._run_cfg("banner motd \"" + banner + "\"")
        else:
            return self._run_cfg("no banner motd")


    def get_banner(self):
        return self._run("show banner motd").rstrip("\n")


    def set_password(self, username="admin", password=None, expire=None, role=None, delete=None):
        '''
        set user password and associated options

        Arguments:
            username
            password      "[0 |5 ]WORD"
                          0     Indicates that the password that follows should be in clear text
                          5     Indicates that the password that follows should be encrypted
                          WORD  Password for the user (clear text) (Max Size 64)
            expire        WORD  Expiry in YYYY-MM-DD format (Max Size 10)
            role          where role is one of
        
                          network-admin     System configured role
                          network-operator  System configured role
                          priv-0            Privilege role
                          priv-1            Privilege role
                          priv-10           Privilege role
                          priv-11           Privilege role
                          priv-12           Privilege role
                          priv-13           Privilege role
                          priv-14           Privilege role
                          priv-15           Privilege role
                          priv-2            Privilege role
                          priv-3            Privilege role
                          priv-4            Privilege role
                          priv-5            Privilege role
                          priv-6            Privilege role
                          priv-7            Privilege role
                          priv-8            Privilege role
                          priv-9            Privilege role
                          vdc-admin         System configured role
                          vdc-operator      System configured role
        '''
        pw_cfg=""
        if delete:
            pw_cfg = "no "
        if username :
            pw_cfg += "username " + username
        else:
            raise ValueError, 'username required parameter'

        if password :
            pw_cfg += " password " + password
        if role:
            pw_cfg += " role " + role
        if expire:
            pw_cfg += " expire " + expire
        return self._run_cfg(pw_cfg)
    

    def set_mgmt0_ip(self, address=None, mask=None):
        ''' set the ip4 or ip v6 address and netmask on mgmt0.
        
                 addresss     of the form
                              <ip>                    ie 10.1.1.1
                              <ip>/<no. bits in mask> ie 10.1.1.1/24
                              <ip>/<mask>     ie 10.1.1.1/255.255.255.0
        '''
        m = Interface("mgmt0")
        return m.set_ipaddress(address, mask)


    def get_mgmt0_ip(self):
        ''' get ip address of mgmt0
        '''
        o = self._run("show running-config interface mgmt0 | include ip")
        return (o.split())[2].rstrip()
