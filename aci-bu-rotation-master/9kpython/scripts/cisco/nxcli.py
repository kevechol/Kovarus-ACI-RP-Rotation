import copy,datetime,re,sys,socket,shlex,subprocess
import nxos_utils
import xml.etree.ElementTree as xml
import nxos
from hw.hwobj import *
from libbcmshell import *
from libnxos_ext_api import *

def bcm_sdk_shell_all_unit(str=""):
    s = str.strip()
    if s:
        o = ""
        mods = []
        for i in range(0, 15):
            if py_pfm_is_module_online(i) == 1:
                 mods.append(i+1)
                 break

        for i in range(20, 26):
            if py_pfm_is_module_online(i) == 1:
                 mods.append(i+1)
                 break

        units = [0, 1]
        for lc in mods: 
            for unit in units:
                o += runBcmCmd(lc, unit, s)
        st = 0
    return st, o

def nxcli(str="", do_print=False):
    output, cmd = '', str.strip()
    if nxos_utils.DEBUG == 1:
        print "CLI: {0}".format(cmd)
    if cmd:
        cmd = "/isan/bin/vsh -c " + "'%s'" % cmd                                                
        args = shlex.split(cmd)                                                     
        child = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = child.communicate()
        status = child.wait()
    if status:
        raise SyntaxError, 'Error status %d\n%s' % (status, output)
    else:
        if do_print:
            print output
        if error:
            print error
    return status, output

class NXCLI(object):
    '''
        Generic NXCLI base class with useful utils
    '''
    
    def __init__(self, command="", do_print=True):
        self.command = command
        self.do_print = do_print
        self._run()

    def _run(self):
        self.status, self.raw_output = nxcli(self.command, self.do_print)
        if not self.status:
            self.processed_output = str(self.raw_output).split('\n')
            self.parse_specific()

    def _get_indent_pat (self):
        try:
            return self._indent_pat
        except AttributeError:
            self._indent_pat = re.compile ('^\s*')
            return self._indent_pat

    def _get_indent_cnt (self, s):
        m = self._get_indent_pat ().search (s)
        return len (m.group ())

    def _get_indent_level (self, indent_stack, line):
        cur = self._get_indent_cnt (line)
        last = indent_stack[-1]
        delta = 0
        if last == cur:
            return delta
        elif last < cur:
            indent_stack.append (cur)
            return delta + 1
        else:
            while last > cur:
                indent_stack.pop()
                last = indent_stack[-1]
                delta -= 1
            if last == cur:
                return delta
        raise IndentationError, '%d space frond after %d' % (cur, last)

    def key_map (self, key):
        k = key.strip ()
        try:
            return self._key_map[k]
        except:
            return k.replace (' ', '_')

    def _numval (self, v):
        s = v.strip ()
        try:
            return int (s)
        except ValueError:
            return s

    @staticmethod
    def _run_cfg (cmds):
        status, output = nxcli('configure terminal ; %s' % cmds)
        if not status:
            return True
        else:
            print error
            return False

    @staticmethod
    def _read_arg(arg, arg_name, format, arg_type_dict):
        from cisco.bgp import BGPSession
        '''
            Read in an argument for a NXCLI configuration command.

            Keyword arguments:
            arg -- the argument to read in
            arg_name -- the name of the argument used in the calling function
            format -- a string representing the format of the NXCLI configuration
                command using '%' where the arg goes. e.g. 'cli-command %'
            arg_type_dict -- a dictionary where the keys are possible types that 
                the argument can take and the values are a string representing 
                any checks that need to be done for that argument type.
                e.g. {int: 'x < 100', str: 'x.startswith('interface ')'}
            
            Returns:
                A string representation of the arg if it passed the checks.
                None if the argument did not pass the checks.
            
            Examples:

            Read in a string with no validation:
            arg = NXCLI._read_arg(name, 'name', 'name %', {str:None})

            Read in an integer with a boundary condition:
            arg = NXCLI._read_arg(id, 'id', 'switch-id %', {int: 'id < 10'})
            
            Read in an ipaddress as a 32 bit quantity or a string:
            arg = NXCLI._read_arg(hostname, 'hostname', 'hostname %',
                    {int: 'hostname >= 1 and hostname <= 4294967295', 
                        str:'socket.inet_aton(hostname)'})

        '''
        for arg_type in arg_type_dict.keys():
            if type(arg) == arg_type:
                if arg_type_dict[arg_type] is not None:
                    check = re.sub('\\b' + arg_name + '\\b', 'arg', 
                            arg_type_dict[arg_type])
                    try: 
                        ret = eval(check)
                    except socket.error: 
                        raise ValueError, ('%s not valid ip address, got %s' % 
                                (arg_name, str(arg)))
                    else: 
                        if not ret:
                            raise ValueError, ('%s not valid, acceptable '
                                    'values: %s' % (arg_name, 
                                        arg_type_dict[arg_type]))
                if arg_type in (int, long):
                    format = format.replace('%', '%d', 1)
                    return format % arg
                elif arg_type is str:
                    format = format.replace('%', '%s', 1)
                    return format % arg
                elif arg_type is bool:
                    return format
        raise ValueError, ('%s not valid, got %s(%s)' % 
                (arg_name, str(arg), str(type(arg))))

        
    @staticmethod
    def _read_arg_from_dict(args, arg_name, format, arg_type_dict, 
            raise_error_if_not_present=False):
        if args.has_key(arg_name):
            return NXCLI._read_arg(args[arg_name], arg_name, format, arg_type_dict)
        elif raise_error_if_not_present:
            raise AttributeError, 'Expected argument %s not present' % arg_name
        else:
            return ""

    @staticmethod
    def _add_no_if_present(cmd, args):
        if args.has_key('no') and cmd != "":
            return 'no ' + cmd
        else:
            return cmd

    def get_xml_dom_from_cli_output (self, text):
        # sanitize the XML removing [possible] junk before and after
        o = re.sub('.*<\?xml', '<?xml',
            re.sub('</nf:rpc-reply>.*', '</nf:rpc-reply>',
            re.sub('[\n\r]', '', text)))
        # parse the XML tree
        elements = xml.fromstring(o)
        return elements

    def key_value_xml_parser (self, element):
        if element.text:
            k, v = re.sub('{[^{}]*}', '', element.tag), element.text.strip()
            return self.key_map (k), self._numval (v)

    def key_value_colon_parser (self, line):
        k, v = line.split (':')
        return self.key_map (k), self._numval (v)

    def get_output(self):
        return self.processed_output

    def rerun(self):
        self._run()

    def get_command(self):
        return self.command

    def get_status(self):
        return self.status

    def parse_specific(self):
        pass

    def get_raw_output(self):
        return self.raw_output

