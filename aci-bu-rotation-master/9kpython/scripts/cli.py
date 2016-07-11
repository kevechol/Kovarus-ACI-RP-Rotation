import subprocess
import shlex
import xmltodict
import json
from errors import *


def cli(cmd):
    '''
    Execute CLI commands. Takes CLI command string and returns show command output in a plain string form.

    Arguments:
        cmd: Single CLI command or a Batch of CLI commands. Delimiter for mutlple CLI
             commands is space + semi-colon. Configuration commands need to be in a 
             fully qualified form. 
             For example, configure terminal ; interface ethernet1/1 ; no shutdown
    
    Returns:
        string: CLI output string for show commands and an empty string for configuration
                commands.

    Raises:
        cli_syntax_error: CLI command is not a valid NXOS command.
        cmd_exec_error: Execution of CLI command is not successful. 

    '''
    args = ["/isan/bin/vsh", "-c", cmd]
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output,error = p.communicate()
    if p.returncode == 0:
        return output
    else:
        msg = "{0}{1}".format(output, error)
        if p.returncode == 16:
            raise cli_syntax_error(msg)
        else:
            raise cmd_exec_error(msg)

def clip(cmd):
    '''
    Execute CLI commands. Takes CLI command string and prints show command output string.

    Arguments:
        cmd: Single CLI command or a Batch of CLI commands. Delimiter for mutlple CLI
             commands is space + semi-colon. Configuration commands need to be in a 
             fully qualified form. 
             For example, configure terminal ; interface ethernet1/1 ; no shutdown
    
    Returns:
        string: Printed CLI output for show commands.

    Raises:
        cli_syntax_error: CLI command is not a valid NXOS command.
        cmd_exec_error: Execution of CLI command is not successful. 

    '''
    args = ["/isan/bin/vsh", "-c", cmd]
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output,error = p.communicate()
    if p.returncode == 0:
        print output
    else:
        msg = "{0}{1}".format(output, error)
        if p.returncode == 16:
            raise cli_syntax_error(msg)
        else:
            raise cmd_exec_error(msg)

def clid(cmd):
    '''
    Execute CLI commands. Takes CLI command string and returns show command output in a json form.

    Arguments:
        cmd: Single CLI command or a Batch of CLI commands. Delimiter for mutlple CLI
             commands is space + semi-colon. Configuration commands need to be in a 
             fully qualified form. 
             For example, configure terminal ; interface ethernet1/1 ; no shutdown
    
    Returns:
        string: JSON formatted output of show commands.

    Raises:
        cli_syntax_error: CLI command is not a valid NXOS command.
        cmd_exec_error: Execution of CLI command is not successful. 

    '''
    args = ["/isan/bin/vsh", "-c", "%s | xml" % cmd]
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    xml_output,error = p.communicate()
    if p.returncode == 0:
        start_index = xml_output.find("<__readonly__>")
        end_index = xml_output.find("</__readonly__>")
        if start_index == -1 or end_index == -1:
            raise structured_output_not_supported_error(cmd)
        else:
            o = xmltodict.parse(xml_output[start_index:end_index + 15])
            json_output = json.dumps(o["__readonly__"])
            return json_output
    else:
        msg = "{0}{1}".format(xml_output, error)
        if p.returncode == 16:
            raise cli_syntax_error(msg)
        else:
            raise cmd_exec_error(msg)

