import re
import os
import nxos_utils
from .nxcli import *

def set_global_vrf(vrf):
    '''
    Sets the global vrf. Any new sockets that are created (using socket.socket)
    will automatically get set to this vrf (including sockets used by other 
    python libraries).

    Arguments:
        vrf: VRF name (string) or the VRF ID (int).

    Returns: Nothing
    '''

    if type(vrf) is str:
        vrf = VRF.get_vrf_id_by_name(vrf)
    os.environ['DCOS_CONTEXT'] = str(vrf)



def get_global_vrf():
    '''
    Gets the global vrf. Any new sockets that are created (using socket.socket)
    will automatically get set to this vrf (including sockets used by other 
    python libraries).

    Arguments: None

    Returns: VRF ID as an integer.
    '''

    return int(os.environ['DCOS_CONTEXT'])



class VRF(object):
    '''
    Use this object to create/delete a VRF on the switch, add/remove interfaces 
    to a VRF or simply just to check if a VRF exists.
    '''

    @staticmethod
    def _get_vrf_info(search_attribute, search_criteria, return_attribute):
        output = nxos_utils.cli_ex('show vrf')
	#print output
        rows = output.split('\n')
        for row in rows[1:]:
            cols = re.split(' +', row)
            if len(cols) >= 2:
                if cols[search_attribute] == search_criteria:
                    return cols[return_attribute]
        return -1


    @staticmethod
    def get_vrf_id_by_name(target_vrf_name):
        ''' Returns the VRF ID associated with the specified VRF name'''
        vrf_id = int(VRF._get_vrf_info(0, target_vrf_name, 1))
        if vrf_id == -1:
            raise ValueError, 'Invalid VRF name specified'
        else:
            return vrf_id


    @staticmethod
    def get_vrf_name_by_id(target_vrf_id):
        ''' Returns the VRF name associated with the specified VRF ID'''
        vrf_name = VRF._get_vrf_info(1, str(target_vrf_id), 0)
        if vrf_name == -1:
            raise ValueError, 'Invalid VRF id specified'
        else:
            return vrf_name


    def __init__(self, vrf):
        '''
        Initializes a VRF object with the specified VRF name or ID and returns 
        the new object.

        Arguments:
            vrf: VRF name (string) or the VRF ID (int). If the VRF is specified 
                as an integer only VRF values corresponding to an existing VRF 
                will be accepted because it is not possible to create a VRF 
                using an ID.

        Example:
            a. v = VRF('management')
            b. v = VRF(2)

        Returns: VRF object on success

        '''

        if isinstance(vrf, int):
            self.id = vrf
            if not self.exists():
                raise ValueError, 'Specified VRF does not exist'
        elif isinstance(vrf, str):
            self.name = NXCLI._read_arg(vrf, 'vrf', '%', {str:'len(vrf) <= 32'})

   
    def create(self, **args):
        '''
        Creates the VRF

        Arguments: None

        Optional Arguments:
            no: A boolean, set to true to delete the VRF
            
        Example:
            v = VRF('floor1')
            v.create()

        Returns: True on success
        
        '''
        
        if args.has_key('no'):
            if not self.exists():
                raise ValueError, ('Cannot delete VRF %s, it does not exist.' 
                        % self.get_name())
        else:
            if self.exists():
                raise ValueError, ('Cannot create VRF %s, it already exists.' 
                        % self.get_name())

        cmd = NXCLI._add_no_if_present('vrf context %s' % self.get_name(), args)
        return NXCLI._run_cfg(cmd)

    
    def delete(self):
        '''
        Deletes the VRF

        Arguments: None

        Returns: True on success

        Example:
            v = VRF('floor1')
            v.delete()

        '''

        return self.create(no = True)


    def add_interface(self, if_name, **args):
        '''
        Sets the specified interface's VRF membership to this VRF.

        Arguments:
            if_name: A string specifying the interface name

        Optional Arguments:
            no: A boolean, set to True to remove this VRF from the specified 
                interface's VRF membership.

        Returns: True on success

        Example:
            v = VRF('floor1')
            v.create()
            v.add_interface('Ethernet 1/1')

        '''

        if_name = NXCLI._read_arg(if_name, 'if_name', 'interface %', {str:None})
        
        if args.has_key('no'):
            _cmd = '%s ; no vrf member %s' % (if_name, self.name)
        else:
            _cmd = '%s ; no switchport ; vrf member %s' % (if_name, self.name)

        return NXCLI._run_cfg(_cmd)


    def remove_interface(self, if_name):
        '''
        Removes this VRF from the specified interface's VRF membership.

        Arguments:
            if_name: A string specifying the interface name

        Returns: True on success

        Example:
            v = VRF('floor1')
            v.create()
            v.add_interface('Ethernet 1/1')
            v.delete_interface('Ethernet 1/1')

        '''

        return self.add_interface(if_name, no = True)


    def exists(self):
        '''
        Checks if this VRF exists.

        Arguments: None

        Returns: 
            True if this VRF exists.
            False if it doesn't exist.

        Example:
            v = VRF('blahblah')
            if not v.exists():
                v.create()

        '''

        if hasattr(self, 'name'):
            if VRF._get_vrf_info(0, self.name, 0) != -1:
                return True
            else:
                return False
        elif hasattr(self, 'id'):
            if VRF._get_vrf_info(1, str(self.id), 1) != -1:
                return True
            else:
                return False


    def get_name(self):
        '''
        Gets the name of this VRF.

        Arguments: None

        Returns: The name of this VRF as a string.

        Example:
            v = VRF(2)
            v.get_name()

        '''

        if hasattr(self, 'name'):
            return self.name
        else:
            self.name = VRF.get_vrf_name_by_id(self.id)
            return self.name




