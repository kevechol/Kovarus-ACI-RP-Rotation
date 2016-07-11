import re
from .nxcli import NXCLI
from .feature import Feature

class shSshKey (NXCLI):
    '''
        Runs and parses 'show ssh key'
    '''
    def __init__ (self):
        super (shSshKey, self).__init__ ('show ssh key', False)
        if self.get_status () == 0:
            match = re.split("\*\*\*\*+", self.raw_output)
            if match:
                self.raw_rsa_output = match[1]
                self.raw_dsa_output = match[2]
                self.rsakeys = self._parse_keys( self.raw_rsa_output )
                self.dsakeys = self._parse_keys( self.raw_dsa_output )



    def _parse_keys(self, raw_text):
        this_key = {}
        this_key["generation date"] = re.findall('[rd]sa\s+Keys generated:(\S+)', raw_text)
        this_key["key"]             = re.findall('ssh-[rd]s[sa]\s+(\S+)', raw_text)
        this_key["bitcount"]        = re.findall('bitcount:(\S+)', raw_text)
        return this_key


class SSH(Feature):

    def __init__ (self):
        self._name = 'ssh'
        self._show_name = 'sshServer'

    def gen_key (self, **args):
        '''
           Generate ssh keys
           
           Arguments:
               key_type
                          dsa          Generate DSA keys
                          rsa          Generate RSA keys\

           Optional Arguments:

               bits       <768-2048>   number of bits
                                       (only for rsa keys)

               force      Force the generation of keys even if previous
                          ones are present

               no         if set, remove ssh key.
        '''

        if args.has_key ('no'):
            cmd = "no "

        cmd = "ssh key"

        if args.has_key ('type'):
            if args['key_type'] == 'dsa':
                cmd += ' dsa'
            elif args['key_type'] == 'rsa':
                cmd += ' rsa'
            elif not args.has_key ('no'):
                raise ValueError, 'Unknown key type: ' +  str(args['key'])
                
        if args.has_key('bits'):
            cmd += str(args['bits'])

        if args.has_key('force'):
            cmd += ' force'

        self._run_cfg(cmd)
        

    def get_keys (self, **args):
        '''
           Generate ssh keys
           
           Optional Arguments:
               key_type
                          dsa          DSA keys
                          rsa          RSA keys
        '''

        if args.has_key ('type'):
            if args['key_type'] == 'dsa':
                return ( shSshKey().dsakeys, )
            elif args['key_type'] == 'rsa':
                return ( shSshKey().rsakeys, )
            else:
                raise ValueError, 'Invalid key type specified.'                 
        else:
            return { 'dsa':shSshKey().dsakeys, 'rsa':shSshKey().rsakeys }



