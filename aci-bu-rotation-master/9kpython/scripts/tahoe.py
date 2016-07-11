#################################################
# TAGS:'error disable','failed','failure','interface','err-dis',
#      'interface delays', 'sequence delays', 'delay'
#
#      File:   interface.py
#      Name:   Shankar Vaideeswaran
#
#
# Copyright (c) 1985-2013, 2015-2016 by cisco Systems, Inc.
# All rights reserved.
#
#
#################################################

# Function Names:
#

import nxos_utils
from pprint import pprint
import re
import multiprocessing
import copy
import sys
from libnxos_ext_api import *
import socket
import struct
import hw.tah.iethdecode
import os
import time
import subprocess as sp
import pexpect 
import cProfile 
import timeit

# Prints the CLI it uses to get the values.
print_cli = 0

DEFAULT_L3_VLAN = 4095
# Field constants

KEY_NIV_IDX_FIELD = 'key_niv_idx'
KEY_BD_XLATE_IDX_FIELD = 'key_bd_xlate_idx'
KEY_VLAN0_FIELD = 'key_vlan0'
KEY_EPG_OR_BD_FIELD = 'key_epg_or_bd'
KEY_DMAC_FIELD = 'dmac'
KEY_NARROW_DMAC_FIELD = 'key_narrow_dmac'
KEY_RMAC_INDEX_FIELD = 'rmac_index'
KEY_L2_ENTRY_VALID_FIELD = 'tile_entry_l2_entry_mac_entry_mackey_vld'
KEY_L2_ENTRY_MACKEY_MAC_FIELD = 'tile_entry_l2_entry_mac_entry_mackey_mac'
KEY_L2_ENTRY_MACKEY_FID_FIELD = 'tile_entry_l2_entry_mac_entry_mackey_fid'
KEY_VALID_FIELD = 'valid'
PREFIX_TILE_L2_ENTRY_FIELD = 'tile_entry_l2_entry_mac_entry'

KEY_L3_V4_ENTRY_VALID_FIELD = 'tile_entry_v4_hrt_vld'
KEY_L3_V4_ENTRY_TYPE = 'tile_entry_v4_hrt_ip_type'
KEY_L3_V4_ENTRY_IP = 'tile_entry_v4_hrt_host_ip'
KEY_L3_V4_ENTRY_IP_ECMP_FLAG = 'tile_entry_v4_hrt_info_ecmp_fields_ecmp'
PREFIX_TILE_L3_V4_ENTRY_FIELD = 'tile_entry_v4_hrt'

# For TCAM LPM
KEY_V4_VRF = 'l3_tcam_entry_vrf'
KEY_L3_TCAM_IP = 'l3_tcam_entry_host_ip'
# SAME Keys can be used for ipv6 coz they are overloaded
KEY_ECMP_V4 = 'l3_tcam_data_v4_info_info_ecmp_fields_ecmp'
KEY_ECMP_V4_NUM_PATHS = 'l3_tcam_data_v4_info_info_ecmp_fields_ecmpinfo_num_paths'
KEY_ECMP_V4_BASE_PTR = 'l3_tcam_data_v4_info_info_ecmp_fields_ecmpinfo_base'
KEY_V4_L2PTR = 'l3_tcam_data_v4_info_info_nonecmp_fields_l2ptr'
KEY_V4_PREFIX = 'l3_tcam_data_v4_info_match_prefix_len'
KEY_V4_SUP_COPY = 'l3_tcam_data_v4_info_l3_info_l3_standalone_info_ipinfo_sup_copy'
KEY_V4_SA_SUP_REDIRECT = 'l3_tcam_data_v4_info_l3_info_l3_standalone_info_ipinfo_sa_sup_redirect'
KEY_V4_DA_SUP_REDIRECT = 'l3_tcam_data_v4_info_l3_info_l3_standalone_info_ipinfo_da_sup_redirect'
KEY_V4_TTL_DEC_BYPASS = 'l3_tcam_data_v4_info_l3_info_l3_standalone_info_ipinfo_ttl_decrement_bypass'
KEY_V4_SA_DIRECT_CONNECT = 'l3_tcam_data_v4_info_l3_info_l3_standalone_info_ipinfo_sa_direct_connect'
KEY_V4_DEF_ENTRY = 'l3_tcam_data_v4_info_l3_info_l3_standalone_info_ipinfo_default_entry'
KEY_V4_LEARN_INFO = 'l3_tcam_data_v4_info_l3_info_l3_standalone_info_learn_info'
# Section - I
# Helper FUnctions.


def get_changed_value(table, key):
    '''Get the value in table at key. Return 0 if it is not there'''
    try:
        return int(table[key], 16)
    except ValueError:
        return table[key]
    except KeyError:
        return 0


def is_davos():
    """Returns True if this is a Davos platform, false otherwise"""
    asic_type = nxos_utils.get_asic_type()
    if asic_type is 'dav':
        return True
    return False


def is_lacrosse():
    """Returns True if this is a Lacrosse platform, false otherwise"""
    asic_type = nxos_utils.get_asic_type()
    if asic_type is 'lac':
        return True
    return False


def vif_to_if_index(vif):
    """Takes in a vif (1538, etc.) and returns an ifindex"""
    return py_im_get_ifindex_from_vif(vif - 1536 + 1)


def slice_port_to_if_index(mod, unit, slice_num, port_on_slice):
    info = py_im_get_hw_info_from_slice_info(mod, unit, slice_num, port_on_slice)
    # return code
    if info[0] == 0:
        # ifindex
        return info[1]
    else:
        return -1


def src_id_to_if_index(mod, unit, slice_num, src_id):
    """Converts a src id (with a module, unit, and slice num) to its
       corresponding slice port"""
    info = py_im_get_hw_info_from_src_id_info(mod, unit, slice_num, src_id)

    if info[0] == 0:
        # ifindex
        return info[1]
    else:
        return -1


def slice_port_to_src_id(mod, unit, slice_num, slice_port):
    """Converts a port on slice (with a module, unit, and slice num) to its
       corresponding src id"""
    info = py_im_get_hw_info_from_slice_info(mod, unit, slice_num, slice_port)

    if info[0] == 0:
        # src id
        return info[9]
    else:
        return -1


def src_id_to_slice_port(mod, unit, slice_num, src_id):
    info = py_im_get_hw_info_from_src_id_info(mod, unit, slice_num, src_id)

    if info[0] == 0:
        # slice port
        return info[9]
    else:
        return -1


def output_to_dict(output_str='', _target_field=[]):
    '''Parse the output and return a dictionary of results
       _target_field is the list of prefixes in keys that must
       be sifted in the output.'''
    output_list = []
    regex_str = '|'.join(['{0}\S*?'.format(field)
                         for field in _target_field])
    for entry in output_str.split('ENTRY')[1:]:
        pairs = re.match('\s*\[(\d+)\]\s*=\s*\{(.*)\}\s*', entry).groups()

        try:
            key = pairs[0]
            value = pairs[1]
        except IndexError:
            print 'Raw command output improper. Exiting with emtpy'
            return []
        if len(_target_field) == 0:
            value = dict(re.findall(r'(\S+)\s*=\s*(\S+)', value))
        else:
            value = dict(re.findall(r'({0})\s*=\s*(\S+)'.format(regex_str),
                                    value))
        value['index_in_table'] = int(key)
        output_list.append(value)

    return output_list


def convert_dict_to_int(_table=None):
    '''Takes a dictionary and converts all values from hex-string to integer'''
    for entry in _table:
        for key in entry:
            try:
                entry[key] = int(entry[key], 16)
            except ValueError:
                # Value not a hex string, do not change
                continue
            except TypeError:
                # Value already integer, do not change
                continue


def translate_mac(mac_addr=''):
    '''Translate input mac_addr string to tahoe format'''
    if ':' in mac_addr:
        mac = mac_addr.split(':')
        try:
            mac_addr = '0x0000%s%s:0x%s%s%s%s' % (mac[0], mac[1], mac[2],
                                                  mac[3], mac[4], mac[5])
        except IndexError:
            print 'Mac address incomplete. Enter Again\n'
            return ''
    elif '.' in mac_addr:
        mac = mac_addr.split('.')
        try:
            mac_addr = '0x0000%s:0x%s%s' % (mac[0], mac[1], mac[2])
        except IndexError:
            print 'Mac address incomplete. Enter Again\n'
            return ''
    elif mac_addr == '':
        return ''
    else:
        print 'Mac address given in wrong format.\n' +\
              'Enter in AA:AA:AA:AA:AA:AA or AAAA.AAAA.AAAA format\n'
        return ''
    return mac_addr

def get_mac_from_hex(mac_addr=0x0):
    ''' Translate Hex format into human readable format'''
    mac = hex(mac_addr)[2:]
    if 'L' in mac:
	mac = mac[:-1]
    mac = mac.zfill(12)
    mac = ":".join(mac[i:i+2] for i in range(0,len(mac),2))
    return mac[0:17]


def runtahoecmd(_change=True, _mod=1, _unit=0, _slice=0,
                _index=0, _table='lua_piftable', _instance=None):
    '''Run a tahoe non-fpx command.'''
    asic = nxos_utils.get_asic_type(_mod, _unit)
    if 'Unknown' in asic:
        return 'Error'
    if _instance:
        table = '{0}:tah_{1}_{2}'.format(_instance, asic, _table)
    else:
        table = 'tah_{0}_{1}'.format(asic, _table)

    prefix = 'slot %d quoted \"debug hardware internal %s' % (_mod, asic)
    prefix += ' dump asic %d slice %d ' % (_unit, _slice)
    if _change:
        cmd = prefix + 'table %s %d changed \"' % (table, _index)
    else:
        cmd = prefix + "table %s %d \"" % (table, _index)

    if print_cli:
        print cmd

    return output_to_dict(nxos_utils.runVshCmd(cmd))


def runtahoecmdrange(_change=True, _mod=1, _unit=0, _slice=0,
                     _start_index=0, _end_index=0, _table='lua_piftable'):
    '''Run a tahoe non-fpx command with changed option'''
    asic = nxos_utils.get_asic_type(_mod, _unit)
    if 'Unknown' in asic:
        return 'Error'

    prefix = 'slot %d quoted \"debug hardware internal %s dump asic %d slice %d ' % (_mod, asic, _unit, _slice)
    if _change:
        cmd = prefix + 'table tah_%s_%s %d %d changed\"' % (asic, _table, _start_index, _end_index)
    else:
        cmd = prefix + 'table tah_%s_%s %d %d\"' % (asic, _table, _start_index, _end_index)

    if print_cli:
        print cmd
    return output_to_dict(nxos_utils.runVshCmd(cmd))


def runtahoefpxcmd(_change=True, _mod=1, _unit=0, _slice=0,
                   _fp=0, _tile=0, _index=0, _table='fpx_cfg_tile_fp',
                   _target_field=[]):
    '''Run a tahoe fpx command with changed option.'''
    asic = nxos_utils.get_asic_type(_mod, _unit)
    if 'Unknown' in asic:
        return 'Error'

    prefix = 'slot %d quoted \"debug hardware internal %s dump asic %d slice %d ' % (_mod, asic, _unit, _slice)
    if _change:
        cmd = prefix + 'fp %d table %d:tah_%s_%s %d changed\"' % (_fp, _tile, asic, _table, _index)
    else:
        cmd = prefix + 'fp %d table %d:tah_%s_%s %d\"' % (_fp, _tile, asic, _table, _index)

    if print_cli:
        print cmd
    return output_to_dict(nxos_utils.runVshCmd(cmd), _target_field)


def runtahoefpxcmdrange(_change=True, _mod=1, _unit=0, _slice=0,
                        _fp=0, _tile=0, _sid=0, _eid=0,
                        _table='fpx_cfg_tile_fp',
                        _target_field=[]):
    '''Run a tahoe fpx command with changed option.'''
    asic = nxos_utils.get_asic_type(_mod, _unit)
    if 'Unknown' in asic:
        return 'Error'

    prefix = 'slot %d quoted \"debug hardware internal %s dump asic %d slice %d ' % (_mod, asic, _unit, _slice)
    if _change:
        cmd = prefix + 'fp %d table %d:tah_%s_%s %d %d changed \"' % (_fp, _tile, asic, _table, _sid, _eid)
    else:
        cmd = prefix + 'fp %d table %d:tah_%s_%s %d %d \"' % (_fp, _tile, asic, _table, _sid, _eid)

    if print_cli:
        print cmd
    return output_to_dict(nxos_utils.runVshCmd(cmd), _target_field)


def runtahoesetcmd(_change=True, _mod=1, _unit=0, _slice=0,
                   _index=1, _range=1, _table="lua_piftable", _field=None):

    ''' Run a tahoe set command. '''
    asic = nxos_utils.get_asic_type(_mod, _unit)
    if 'Unknown' in asic:
        return 'Error'

    prefix = 'slot %d quoted \"debug hardware internal %s modify asic %d slice %d ' % (_mod, asic, _unit, _slice)
    if _field is not None:
        cmd = prefix + 'table tah_%s_%s %d %d %s\"' % (asic, _table, _index,
                                                       _range, _field)

        if print_cli:
            print cmd
        out = nxos_utils.runVshCmd(cmd)
        if "Cmd exec error." in out:
            print "Command Failed"
            print cmd
            return "Error"
        else:
            print "Set %s in tah_%s_%s" % (_field, asic, _table)
    else:
        print "Unknown Field specified to set."


def tahoe_print(out=None):
    '''Print the passed list of entries in proper format'''

    if out:
        if type(out) is not list:
            # Safety net if the passed value is a table entry
            # instead of a list of entries
            out = [out]
        for entry in out:
            print "ENTRY: {0}".format(entry['index_in_table'])
            if 'fpx' in entry.keys() and 'tile' in entry.keys():
                print 'FPX: {0} TILE: {1}'.format(entry['fpx'],
                                                  entry['tile'])
            entries = (item
                       for item in entry.keys()
                       if item != 'index_in_table' and
                       item != 'fpx' and
                       item != 'tile')
            for items in entries:
                print "\t%s : %s" % (items, entry[items])
    else:
        print "No enteries matched the criterion"


def check_and_print(table, table_name, err_str):
    '''Check if the given table is not empty and print.
       Return "False" on empty'''
    if not table:
        print 'Error:\n{0}'.format(err_str)
        return False

    print '{0}:'.format(table_name)
    tahoe_print(table)
    print '========================================='
    return True


def get_intf_info(_intf_name):
    # Given an interface, output hw table entries
    rv = True

    cmd = 'show system internal ethpm info interface {0}'.format(
          _intf_name) + ' | grep IF_STATIC_INFO'
    output = nxos_utils.runVshCmd(cmd)
    match_str = '.*IF_STATIC_INFO.*dmod=(\d*).*dpid=(\d*)'
    match_str += '.*slice_num=(\d*).*port_on_slice=(\d*).*src_id=(\d*).*'
    m = re.match(match_str, output)

    if m:
        try:
            asic_num = int(m.groups()[0])
            asic_port = int(m.groups()[1])
            slice_num = int(m.groups()[2])
            port_on_slice = int(m.groups()[3])
            src_id = int(m.groups()[4])
        except KeyError:
            print 'Incomplete match in cli output ({0}).'.format(output)
            rv = False
            return rv

    else:
        print 'Improper interface/command'
        rv = False
        return rv

    bdclass = Bd(_print_out=0)
    ifclass = Interface(_unit=asic_num - 1, _print_out=0)
    print 'Asic: {0}'.format(asic_num - 1)
    print 'AsicPort: {0}'.format(asic_port)
    print 'SrcId: {0}'.format(src_id)
    print 'Slice: {0}'.format(slice_num)
    print 'PortOnSlice: {0}'.format(port_on_slice)
    print 'Table entries for interface %s\n' % (_intf_name)
    # Get Pif entry from slice and src_id
    pif_info = ifclass.get_pif(slice_num, src_id)

    err_str = 'Could not find pif from src-id {0}'.format(src_id)
    rv = check_and_print(pif_info, 'PifTable', err_str)
    if not rv:
        return rv

    # niv_idx and dst_idx are same in asic context
    try:
        niv_idx = pif_info[0]['niv_idx']
    except KeyError:
        print 'NIV_INDEX not found in pif_table. Check if port is up'
        rv = False
        return rv

    # Get list of VIF entries
    # if the pif entry is a fex fabric port,
    # we'll have a list of vif entries here, one for each HIF
    # for normal ports, we should get only one with svif=4095
    vif = ifclass.get_vif(slice_num, niv_idx)

    if len(vif) > 1:
        print "Port is a fabric port connected to Fex."
        print "No support for FEX i/f as of now."
        print "Got following entries:"
        tahoe_print(vif)

        # TODO: Handle FEX HIF i/f..
        rv = False
        return rv
    else:
        err_str = 'Could not find niv_idx {0} in vif_table.'.format(
            niv_idx) + 'Check if port is up.'
        rv = check_and_print(vif, 'VifTable', err_str)
        if not rv:
            return rv

    # Get the vifstate entry from the vif data
    lif = vif[0]['data_vif']
    vifstate = ifclass.get_vifstate(slice_num, lif)

    # Get if the interface is L2 or not
    try:
        is_l2_intf = vifstate[0]['info_is_l2_if']
    except KeyError:
        is_l2_intf = 0

    err_str = 'Could not find vif state entry for {0}'.format(lif)
    rv = check_and_print(vifstate, 'VifStateTable', err_str)
    if not rv:
        return rv

    # Get the vlanxlate entry from bd_xlate_idx obtained
    # from vifstate entry, and the default L3 vlan 4095
    bd_xlate_idx = vifstate[0]['info_bd_xlate_idx']
    vlanxlate = bdclass.get_vlanxlate(slice_num, bd_xlate_idx,
                                      vifstate[0]['info_default_vlan'])

    err_str = 'Could not find xlate entry from\nbd_xlate_idx {0}'.format(
        bd_xlate_idx) + 'and L3 vlan {0}'.format(
        vifstate[0]['info_default_vlan'])
    rv = check_and_print(vlanxlate, 'VlanXlateTable', err_str)
    if not rv:
        return rv

    # Get the BdState entry for the L3 Vif from xlated L3 vlan
    vif_bd = vlanxlate[0]['data_epg_or_bd']
    bdstate = bdclass.get_bdstate(slice_num, vif_bd)

    # Get if the interface is L3 or not
    try:
        is_l3_intf = bdstate[0]['is_l3_if']
    except KeyError:
        is_l3_intf = 0

    if is_l3_intf:
        print 'Interface is an L3 interface'
        print '========================================='

    err_str = 'Could not find BD at {0}'.format(
        vlanxlate[0]['data_epg_or_bd'])
    rv = check_and_print(bdstate, 'BdStateTable', err_str)
    if not rv:
        return rv

    # For L2 interface, print the flood tables
    if is_l2_intf:
        dstinfo = bdclass.get_dstinfo(slice_num,
                                      bdstate[0]['flood_dst_ptr'])
        err_str = 'DstInfo table entry not found at flood_dst_ptr {0}'.format(
            bdstate[0]['flood_dst_ptr'])
        rv = check_and_print(dstinfo, 'DstInfoTable', err_str)
        if not rv:
            return rv

    # Local Multipath table
    local_multipath = ifclass.get_localmultipath(slice_num, niv_idx)
    err_str = 'LocalMultipath entry not found at dst_idx {0}'.format(niv_idx)
    rv = check_and_print(local_multipath, 'LocalMultipathTable',
                         err_str)
    if not rv:
        return rv

    # UcPcCfg table
    ucpc_cfg = ifclass.get_ucpccfg(slice_num,
                                   local_multipath[0]['vpc_port_idx_0'])
    err_str = 'UcPcCfg entry not found for vpc_port_idx_0 {0}'.format(
              local_multipath[0]['vpc_port_idx_0'])
    rv = check_and_print(ucpc_cfg, 'UcPcConfigTable', err_str)
    if not rv:
        return rv

    # UcPcMbr table
    ucpc_mbrs = ifclass.get_ucpcmbr(slice_num, ucpc_cfg[0]['base_ptr'],
                                    ucpc_cfg[0]['num_paths'])
    err_str = 'UcPcMbrs entry not found for ucpc_base_ptr {0}'.format(
              ucpc_cfg[0]['base_ptr'])
    rv = check_and_print(ucpc_mbrs, 'UcPcMbrTable', err_str)
    if not rv:
        return rv

    # The ovector_idx in UcPcMbr table must match from the dport table

    # Dport table
    for ucpc_mbr in ucpc_mbrs:
        dport = ifclass.get_dporttbl(slice_num, ucpc_mbr['dst_port'])
        err_str = 'Dport table entry not found for dport {0}'.format(
                  ucpc_mbr['dst_port'])
        rv = check_and_print(dport, 'Dport (asic_port to ovector_idx)',
                             err_str)
    if not rv:
        return rv

    # RWPif table
    rwpif = ifclass.get_rwpif(slice_num, src_id)
    err_str = 'RWPif table entry not found for src_id {0}'.format(src_id)
    rv = check_and_print(rwpif, 'RWPifTable', err_str)
    if not rv:
        return rv

    # RWVif table
    rwvif = ifclass.get_rwvif(slice_num, niv_idx)
    err_str = 'RWVif table entry not found at niv_idx {0}'.format(niv_idx)
    rv = check_and_print(rwvif, 'RWVifTable', err_str)
    if not rv:
        return rv

    # OvectorMap Table
    oport = ifclass.get_ovector_map(slice_num, port_on_slice)
    err_str = 'OvectorMap table entry not found at slice_port {0}'.format(
        port_on_slice)
    rv = check_and_print(oport,
                         'OvectorMapTable (slice_port to src_id map)',
                         err_str)
    if not rv:
        return rv

    # IfProfile Table
    if_profile = ifclass.get_if_profile(slice_num, port_on_slice)
    err_str = 'IfProfile table entry not found at slice_port {0}'.format(
        port_on_slice)
    rv = check_and_print(if_profile,
                         'IfProfileTable',
                         err_str)
    if not rv:
        return rv

    # SrcChip Table
    # Get the zeroth entry here from the single entry list
    src_chip_state = ifclass.get_src_chip_state(slice_num)[0]
    err_str = 'SrcChipState table entry not found for unit {0}'.format(
        asic_num)
    rv = check_and_print(src_chip_state,
                         'SrcChipStateTable',
                         err_str)
    if not rv:
        return rv

    # SrcPortState Table
    # Commenting for now as TORs do not have multiple asic nums
    # offset = src_chip_state['offset0'] if (asic_num - 1) % 2 == 0 \
        # else src_chip_state['offset1']
    return rv


class ParallelTahoeFpx(multiprocessing.Process):
    '''Inherited class for fpx commands'''
    def __init__(self, fp, tile, target_func, kwargs, out_q=None):
        multiprocessing.Process.__init__(self)
        self.target_func = target_func
        self.kwargs = copy.deepcopy(kwargs)
        self.fp = fp
        self.tile = tile
        self.kwargs['_fp'] = fp
        self.kwargs['_tile'] = tile
        self.out_q = out_q

    def run(self):
        '''Main function that is run'''
        result = self.target_func(**self.kwargs)
        result_dict = {'result': result,
                       'fp': self.fp,
                       'tile': self.tile}
        self.out_q.put(result_dict)


class hashcalc:
    __hashdict = {(4, 0): 0xf,     (4, 1): 0x0,     (5, 0): 0x8,     (5, 1): 0x5,
                  (7, 0): 0x11,    (7, 1): 0x9,     (7, 2): 0x65,    (7, 3): 0x4f,
                  (8, 0): 0x31,    (8, 1): 0x2f,    (8, 2): 0x39,    (8, 4): 0xd5,
                  (8, 5): 0x4d,    (8, 6): 0x8d,    (8, 7): 0x9b,    (8, 8): 0x07,
                  (9, 0): 0x79,    (9, 1): 0x137,   (9, 2): 0x10b,   (9, 3): 0x5f,
                  (10, 0): 0x11d,  (10, 1): 0x173,  (10, 2): 0x233,  (10, 3): 0x24f,
                  (11, 0): 0x265,  (11, 1): 0x3af,  (11, 2): 0x307,  (11, 3): 0x49b,
                  (12, 0): 0x683,  (12, 1): 0x80b,  (12, 2): 0x807,  (12, 3): 0x6eb,
                  (13, 0): 0x16f,  (13, 1): 0x54b,  (13, 2): 0x1213, (13, 3): 0x055,
                  (14, 0): 0x6e3,  (14, 1): 0x1ef7, (14, 2): 0x25b,  (14, 3): 0x1153,
                  (15, 0): 0,      (15, 1): 0,      (15, 2): 0,      (15, 3): 0,
                  (16, 0): 0xa097, (16, 1): 0x5b93, (16, 2): 0,      (16, 3): 0}

    def __init__(self):
        return

    def hash_calc(self, key, _hash_degree=14, _hash_sel=0):
        if (_hash_degree, _hash_sel) in self.__hashdict:
            polynomial = self.__hashdict.get((_hash_degree, _hash_sel))
            print '%x' % (polynomial)
        else:
            print 'Unknown polynimial'
            return

        reminder = 0
        polynomial = int(polynomial)
        rmsel = (1 << (_hash_degree - 1))

        for entry in key:
            dsel = 0x80
            while dsel > 0:
                dbit = 0
                rmsb = 0
                if (dsel & entry) != 0:
                    dbit = 1
                if (rmsel & reminder) != 0:
                    rmsb = 1

                reminder = reminder << 1

                if (dbit ^ rmsb):
                    reminder = reminder ^ polynomial

                dsel = dsel >> 1

        reminder = reminder & ~(0xffffffff << _hash_degree)

        print 'Hash Index: %d' % (reminder)
        return reminder


class Fpx:
    '''
    Fpx Related Function defintions.
    '''
    _print_out = True
    __change = True
    __tile_cfg_cache = False

    _tile_cfg = {}

    def __init__(self, _mod=1,  _unit=0, _print_out=True, _change=True):
        self._mod = _mod
        self._unit = _unit
        self._asic = nxos_utils.get_asic_type(_mod, _unit)
        self.__change = _change
        self._print_out = _print_out
        (self.__tile_types, self.__log_tile_types) = self.get_tile_types()
        if 'lac' in self._asic:
            self.__max_fpx = 6
            self.__tiles_per_fp = 4
            self.__depth = 16384
        elif 'dav' in self._asic:
            self.__max_fpx = 11
            self.__tiles_per_fp = 4
            self.__depth = 8192
        else:
            self.__max_fpx = 0
            self.__tiles_per_fp = 0
            self.__depth = 0

    def help(self):
        print '\t\t Table                                    INDEX'
        print '\tget_l2(slice, _mac=\'\', _fid=\'\')       Put mac/fid to search.'
        print '\t                                          (put None for dont-care)'
        print '\tget_tile_entry(slice, fp, tile, index, prefix) '
        print '\tget_fib_tcam_all(slice)'
        print '\tget_fib_tcam_data(slice)'

    def __get_tile_type_string(self, _tile_type=0x0):
        if _tile_type == 0:
            return 'L2'
        elif _tile_type == 1:
            return 'IP'
        elif _tile_type == 2:
            return 'TriePtr'
        elif _tile_type == 3:
            return 'ECMP'
        elif _tile_type == 4:
            return 'RPF'
        elif _tile_type == 5:
            return 'SAINFO'
        elif _tile_type == 6:
            return 'IPSADATAG'
        elif _tile_type == 7:
            return 'L3_IFABRIC'
        elif _tile_type == 8:
            return 'L2_IFABRIC'
        elif _tile_type == 9:
            return 'L3_EXT_IFABRIC'
        elif _tile_type == 10:
            return 'L2_EXT_IFABRIC'
        elif _tile_type == 11:
            return 'PT KEY'
        elif _tile_type == 12:
            return 'PT OFLOW'
        elif _tile_type == 13:
            return 'PT_INFO'
        elif _tile_type == 14:
            return 'PT_EXT_INFO'
        elif _tile_type == 15:
            return 'DCI_VNID'
        elif _tile_type == 16:
            return 'DCI_SCLASS'
        elif _tile_type == 17:
            return 'ECMP GRP'
        elif _tile_type == 18:
            return 'NAT_IPV4'
        elif _tile_type == 19:
            return 'NAT_IPV6'
        elif _tile_type == 20:
            return 'SAINFO_EXT'
        else:
            return 'Unknown'

    def get_tile_types(self):
        cmd = 'slot {0} quoted '.format(self._mod) +\
            '"sh hardware internal tah logical-tile-types"'
        match_string = \
            'FPX: (\d+).*?Tile: (\d+).*?TileType: (.*) .*?LogicalTileType: (.*)'
        tile_type_dict = {}
        log_tile_type_dict = {}

        output = nxos_utils.runVshCmd(cmd)
        lines = output.split("\n")
        for line in lines:
            line = line.strip()

            m = re.match(match_string, line)
            if m:
                try:
                    entry = m.groups()
                    fpx = int(entry[0])
                    tile_num = int(entry[1])
                    tile_type_dict[(fpx, tile_num)] = entry[2]
                    log_tile_type_dict[(fpx, tile_num)] = entry[3]
                except IndexError:
                    print 'Incomplete match'
                    continue
            else:
                continue
        return (tile_type_dict, log_tile_type_dict)

    def get_tile_cfg(self, _slice=0):
        '''Get all tile configuration in all fpx'''
        out_q = multiprocessing.Queue()
        # Since the L2 tile type is 0 and will not show with changed tag
        for fp in range(0, self.__max_fpx):
            processes = []
            for tile in range(0, self.__tiles_per_fp):
                arg_dict = {'_change': False,
                            '_mod': self._mod,
                            '_unit': self._unit,
                            '_slice': _slice,
                            '_index': 0,
                            '_target_field': ['tile_type'],
                            '_table': 'fpx_cfg_tile_fp'}
                processes.append(ParallelTahoeFpx(fp, tile,
                                                  runtahoefpxcmd,
                                                  arg_dict, out_q))
            for p in processes:
                p.start()

            for i in range(0, self.__tiles_per_fp):
                item = out_q.get()
                self._tile_cfg[(item['fp'], item['tile'])] =\
                    item['result'][0]['tile_type']

            for p in processes:
                p.join()

        self.__tile_cfg_cache = True
        return self._tile_cfg

    def __get_tile_type(self, _slice, _fp=0, _tile=0):
        '''Internal only function to get tile type'''
        tile_type = int((self._tile_cfg[(_fp, _tile)]), 16)
        return self.__get_tile_type_string(tile_type)

    @staticmethod
    def get_entries_from_fpx_tile(_change, _mod, _unit, _slice, _fp,
                                  _tile, _sid, _eid, _target_field,
                                  _valid_field):
        '''Wrapper function around runtahoefpxcmdrange for parallel get.
           Returns the list of valid entries from the given tile'''
        ret_entries = []
        # First get the raw entries
        entries = iter(runtahoefpxcmdrange(_change=_change, _mod=_mod,
                                           _unit=_unit, _slice=_slice,
                                           _fp=_fp, _tile=_tile,
                                           _sid=_sid, _eid=_eid,
                                           _table='fpx_fptile',
                                           _target_field=_target_field))
        # Now parse through them to return only valid entries.
        for entry in entries:
            if _valid_field in entry.keys():
                if int(entry[_valid_field], 16) == 1:  # Valid
                    entry['fpx'] = _fp
                    entry['tile'] = _tile
                    entry['index_in_table'] =\
                        int(entry['index_in_table'])
                    ret_entries.append(entry)

        return ret_entries

    def get_l2_entry(self, _slice, _fp, _tile, _index):
        '''Get l2 entry by fp, tile, hash-index on a slice'''

        # If cached use cache.
        if self.__tile_cfg_cache is False:
            self.get_tile_cfg(_slice)

        tile_type = self.__get_tile_type(_slice, _fp, _tile)
        if 'L2' != tile_type:
            if self._print_out:
                print "Tile (%d %d) is not an L2 tile" % (_fp, _tile)
            out = []
        else:
            out = runtahoefpxcmd(self.__change, self._mod, self._unit, _slice, _fp, _tile, _index, "fpx_fptile")
        if self._print_out == 1:
            tahoe_print(out)
        else:
            return out

    # Get all L2 tile entries.
    def get_l2(self, _slice=0, _mac=None, _fid=None):
        fpout = []      # Array of louts.
        entries = []

        # If cached use cache.
        if not(self.__tile_cfg_cache):
            self.get_tile_cfg(_slice)

        out_q = multiprocessing.Queue()

        for fp in range(0, self.__max_fpx):
            processes = []
            num_lists = 0
            for tile in range(0, self.__tiles_per_fp):
                # tile_type = self.__get_tile_type(_slice, fp, tile)
                tile_type = self.__tile_types[(fp, tile)]
                log_tile_type = self.__log_tile_types[(fp, tile)]
                if 'L2' == tile_type and 'L2' == log_tile_type:
                    num_lists += 1
                    args_dict = {'_change': self.__change,
                                 '_mod': self._mod,
                                 '_unit': self._unit,
                                 '_slice': _slice,
                                 '_fp': fp,
                                 '_tile': tile,
                                 '_sid': 0,
                                 '_eid': self.__depth,
                                 '_target_field': [PREFIX_TILE_L2_ENTRY_FIELD],
                                 '_valid_field': KEY_L2_ENTRY_VALID_FIELD}
                    processes.append(ParallelTahoeFpx(fp, tile,
                                                      Fpx.get_entries_from_fpx_tile,
                                                      args_dict, out_q))
            for p in processes:
                p.start()

            for i in range(0, num_lists):
                item = out_q.get()
                entries += item['result']

            for p in processes:
                p.join()

        entries = iter(entries)

        if _mac:
            mac = translate_mac(_mac)
            print "Searching for the mac entry "
            print('{0}: {1}'.format(KEY_L2_ENTRY_MACKEY_MAC_FIELD, mac))
            entries = (item
                       for item in entries
                       if KEY_L2_ENTRY_MACKEY_MAC_FIELD in item.keys()
                       if item[KEY_L2_ENTRY_MACKEY_MAC_FIELD] == mac)
        if _fid:
            print "Searching for the fid entry "
            print('{0}: {1}'.format(KEY_L2_ENTRY_MACKEY_FID_FIELD,
                                    _fid))
            entries = (item
                       for item in entries
                       if KEY_L2_ENTRY_MACKEY_FID_FIELD in item.keys()
                       if int(item[KEY_L2_ENTRY_MACKEY_FID_FIELD], 16) == _fid)

        fpout = list(entries)

        if self._print_out == 1:
            tahoe_print(fpout)
        else:
            return fpout

    def get_l2_tcam(self, _slice=0, _mac=None, _fid=None):
        tcam_out = []
        # First get the raw entries
        tcam_entries = iter(runtahoecmdrange(_change=self.__change,
                                             _mod=self._mod,
                                             _unit=self._unit, _slice=_slice,
                                             _start_index=0, _end_index=4095,
                                             _table='fpa_sttcam'))

        # Now parse through them to return only valid entries.
        for tcam_entry in tcam_entries:
            try:
                valid = int(tcam_entry['valid'], 16)
            except KeyError:
                valid = 0
            if valid == 1:
                tcam_out.append(tcam_entry)
        return tcam_out

    def get_tile_entry(self, _slice=0, _fp=0, _tile=0, _index=0, _prefix=None):
        """ Get tile entry at a given location and filter it based off prefix.
            For example: if l2 entries are needed:
            get_tile_entry(_slice=0, _fp=5, _tile=3, _index=100, _prefix='mac'"""
        fpentry = []
        search_entry = []
        if _prefix:
            search_entry.append(_prefix)
            entry = runtahoefpxcmd(False, self._mod, self._unit,
                                   _slice, _fp, _tile, _index,
                                   'fpx_fptile', search_entry)
            fpentry.append(entry)
            if self._print_out == 1:
                tahoe_print(entry)

        if self._print_out != 1:
            return fpentry

    # Get L3 tile entry. ipv4 entry is of the form "X.X.X.X"
    def get_l3_host_v4(self, _slice=0, ipv4=None):
        fpout = []      # Array of louts.
        entries = []

        # If cached use cache.
        if self.__tile_cfg_cache is False:
            self.get_tile_cfg(_slice)

        out_q = multiprocessing.Queue()

        for fp in range(0, self.__max_fpx):
            processes = []
            num_lists = 0
            for tile in range(0, self.__tiles_per_fp):
                tile_type = self.__get_tile_type(_slice, fp, tile)
                if 'IP' == tile_type:
                    num_lists += 1
                    args_dict = {'_change': False,
                                 '_mod': self._mod,
                                 '_unit': self._unit,
                                 '_slice': _slice,
                                 '_fp': fp,
                                 '_tile': tile,
                                 '_sid': 0,
                                 '_eid': self.__depth,
                                 '_target_field': [PREFIX_TILE_L3_V4_ENTRY_FIELD],
                                 '_valid_field': KEY_L3_V4_ENTRY_VALID_FIELD}
                    processes.append(ParallelTahoeFpx(fp, tile,
                                                      Fpx.get_entries_from_fpx_tile,
                                                      args_dict, out_q))
            for p in processes:
                p.start()
                # Serializing the run for now for stability
                item = out_q.get()
                entries += item['result']

            for p in processes:
                p.join()

        entries = iter(entries)
        entries = (item
                   for item in entries
                   if KEY_L3_V4_ENTRY_TYPE in item.keys()
                   if int(item[KEY_L3_V4_ENTRY_TYPE], 16) == 0
                   if KEY_L3_V4_ENTRY_IP_ECMP_FLAG in item.keys()
                   if int(item[KEY_L3_V4_ENTRY_IP_ECMP_FLAG], 16) == 0)

        if ipv4:
            print '{0}: {1}\n'.format(KEY_L3_V4_ENTRY_IP, ipv4)
            ip_b = ipv4.split('.')
            ipv4_address = '0x%02x%02x%02x%02x' \
                % (int(ip_b[0]), int(ip_b[1]), int(ip_b[2]), int(ip_b[3]))
            entries = (item
                       for item in entries
                       if KEY_L3_V4_ENTRY_IP in item.keys()
                       if item[KEY_L3_V4_ENTRY_IP].strip() == ipv4_address)
        for entry in entries:
            fpout.append(entry)
            if self._print_out == 1:
                tahoe_print(entry)
        if self._print_out != 1:
            return fpout

    def get_fib_tcam_all(self, _slice=0, range_lo=0, range_hi=7):
        lpmout = []
        for i in range(range_lo, range_hi + 1):
            entries = runtahoefpxcmdrange(False, self._mod,
                                          self._unit, _slice, 0, i,
                                          0, 2048, 'fpa_fibtcam')
            entries = (item
                       for item in entries
                       if KEY_VALID_FIELD in item.keys()
                       if int(item[KEY_VALID_FIELD], 16) == 1)

            for entry in entries:
                    entry['tcam_bank'] = i
                    lpmout.append(entry)

        if self._print_out == 1:
            tahoe_print(lpmout)
        else:
            return lpmout

    def get_fib_tcam_data(self, _slice=0, range_lo=0, range_hi=7):
        lpmout = []
        for i in range(range_lo, range_hi + 1):
            entries = runtahoefpxcmdrange(self.__change, self._mod, self._unit,
                                          _slice, 0, i, 0, 2048,
                                          'fpa_fibtcamdata')
            for entry in entries:
                entry['tcam_bank'] = i
                lpmout.append(entry)
        if self._print_out == 1:
            tahoe_print(lpmout)
        else:
            return lpmout


class Interface:
    '''
    Interface specific registers per module, per unit.
    '''
    mod = 1
    unit = 1
    print_out = 1  # Print to console or return to another function.
    changed = True  # Print only changed entries.

    def __init__(self, _mod=1,  _unit=0, _print_out=1, _change=True):
        self.mod = _mod
        self.unit = _unit
        self.print_out = _print_out
        self.changed = _change
        return

    def help(self):
        print '\t\t Table                             \t    INDEX'
        print '\tget_pif(slice, index)              \t  <src_id>.'
        print '\tget_vif(slice, niv_idx)            \t  Search using niv_idx'
        print '\tget_vifprofile(slice, index)       \t'
        print '\tget_vifstate(slice, index)         \t  <niv_idx>.'
        print '\tget_localmultipath(slice, index)   \t  <dst_idx>.'
        print '\tget_ucpccfg(slice, index)          \t  <vpc_port_idx> @ localmp.'
        print '\tget_ucpcmbr(slice, index, num)     \t  <base_ptr> @ ucpccfg. <num_paths> @ ucpccfg.'
        print '\tget_rwpif(slice, index)            \t'
        print '\tget_rwvif(slice, index)'
        print '\tget_rwsrcport(slice, index)'
        print '\tget_rwnivsrcvif(slice, index)'
        print '\tget_rwnivdstvif(slice, index)'
        print '\tget_vpcprune(slice)'
        print '\tget_dporttbl(slice, index)'
        print '\tget_ovector_map(slice, index)       \t <port_on_slice>'
        print '\tget_if_profile(slice, index)       \t <port_on_slice>'
        print '\tget_src_chip_state(slice)'
        print '\tget_vpcbounce(slice)'
        print 'SET FUNCTIONS:'
        print '\tset_pif(slice,index,field)'
        print '\tset_vif(slice,index,field)'
        print '\tset_vifprofile(slice,index,field)'
        print '\tset_vifstate(slice,index,field)'
        print '\tset_ucpccfg(slice, index,field)'
        print '\tset_ucpcmbr(slice, index)'
        print '\tset_vpc_bounce(slice, field)'

    def get_pif(self, _slice=1, _index=0):
        """ Read PIF table. Index is Src_idx """
        out = runtahoecmd(self.changed, self.mod,
                          self.unit, _slice, _index,
                          'lua_piftable')
        if self.print_out == 1:
            tahoe_print(out)
        else:
            convert_dict_to_int(out)
            return out

    def set_pif(self, _slice=1, _index=0, _field=None):
        """ Set PIF table. Index is Src_idx """
        if _field is not None:
            runtahoesetcmd(self.changed, self.mod, self.unit, _slice,
                           _index, 1, 'lua_piftable', _field)

    def get_vif(self, _slice=0, _niv_idx=None):
        """ Read VIF table. Index is niv_idx.Searchable using niv_idx. Pass -1
        to list all entries. """
        vifout = []

        entries = runtahoecmdrange(self.changed, self.mod, self.unit, _slice, 0, 8192, 'lua_viftable')

        # Make iterator
        if _niv_idx:
            if self.print_out == 1:
                print '{0}: {1}'.format(KEY_NIV_IDX_FIELD, hex(_niv_idx))
            entries = (item
                       for item in entries
                       if KEY_NIV_IDX_FIELD in item.keys()
                       if int(item[KEY_NIV_IDX_FIELD], 16) == _niv_idx)
        else:
            print 'Printing all valid entries'
            entries = (item
                       for item in entries
                       if KEY_VALID_FIELD in item.keys()
                       if int(item[KEY_VALID_FIELD], 16) == 0x1)

        for entry in entries:
            vifout.append(entry)

        if self.print_out == 1:
            tahoe_print(vifout)
        else:
            convert_dict_to_int(vifout)
            return vifout

    def set_vif(self, _slice=0, _index=0, _field=None):
        """ Set VIF table. Index is index of the entry in table."""
        if _field is not None:
            runtahoesetcmd(self.changed, self.mod, self.unit, _slice,
                           _index, 1, "lua_viftable", _field)

    def get_vifprofile(self, _slice=0, _index=0):
        ''' Read VIF Profile table. Index is derived from vif_statetbl'''
        out = runtahoecmd(self.changed, self.mod, self.unit, _slice, _index, 'lua_vifprofiletable')
        if self.print_out == 1:
            tahoe_print(out)
        else:
            convert_dict_to_int(out)
            return out

    def set_vifprofile(self, _slice=0, _index=0, _field=None):
        """ Set VIF Profile table. Index is index of the entry in table."""
        if _field is not None:
            runtahoesetcmd(self.changed, self.mod, self.unit, _slice,
                           _index, 1, "lua_vifprofiletable", _field)

    def get_vifstate(self, _slice=0, _index=0):
        ''' Read the VIF state table indexed by niv_index'''
        out = runtahoecmd(self.changed, self.mod, self.unit, _slice, _index, 'lua_vifstatetable')
        if self.print_out == 1:
            tahoe_print(out)
        else:
            convert_dict_to_int(out)
            return out

    def set_vifstate(self, _slice=0, _index=0, _field=None):
        """ Set VIFStateTable. Index is index of the entry in the table. """
        if _field is not None:
            runtahoesetcmd(self.changed, self.mod, self.unit, _slice,
                           _index, 1, "lua_vifstatetable", _field)

    def get_ucpccfg(self, _slice=0, _index=0):
        """ Read UCPortChannelConfig table. index from <dst_idx>"""
        out = runtahoecmd(self.changed, self.mod, self.unit, _slice, _index,
                          'luc_ucportchannelconfigtable')
        if self.print_out == 1:
            tahoe_print(out)
        else:
            convert_dict_to_int(out)
            return out

    def set_ucpccfg(self, _slice=0, _index=0, _field=None):
        ''' Set UCPCconfigtable.
            Index is index of the entry in the table.'''
        if _field is not None:
            runtahoesetcmd(self.changed, self.mod, self.unit, _slice,
                           _index, 1, 'luc_ucportchannelconfigtable',
                           _field)

    def get_ucpcmbr(self, _slice=0, _index=0, _num_entries=1):
        out = runtahoecmdrange(self.changed, self.mod, self.unit,
                               _slice, _index, _num_entries,
                               'luc_ucportchannelmembertable')
        if self.print_out == 1:
            tahoe_print(out)
        else:
            convert_dict_to_int(out)
            return out

    def set_ucpcmbr(self, _slice=0, _index=0, _field=None):
        """ Set UCPCMbrEntry. Index is index of the entry in the table. """
        if _field is not None:
            runtahoesetcmd(self.changed, self.mod, self.unit, _slice,
                           _index, 1, 'luc_ucportchannelmembertable', _field)

    def get_localmultipath(self, _slice=0, _index=0):
        out = runtahoecmd(self.changed, self.mod, self.unit, _slice, _index, 'luc_localmultipathtable')
        if self.print_out == 1:
            tahoe_print(out)
        else:
            convert_dict_to_int(out)
            return out

    def set_localmultipath(self, _slice=0, _index=0, _field=None):
        """ Set Localmultipathtable. Index is index of the entry in the table. """
        if _field is not None:
            runtahoesetcmd(self.changed, self.mod, self.unit, _slice,
                           _index, 1, 'luc_localmultipathtable', _field)

    def get_rwpif(self, _slice=0, _index=0):
        """ Read RW Piftable.Index is derived from Ovector of ucpcmbr."""
        out = runtahoecmd(self.changed, self.mod, self.unit, _slice, _index, 'rwx_rwpiftable')
        if self.print_out == 1:
            tahoe_print(out)
        else:
            convert_dict_to_int(out)
            return out

    def set_rwpif(self, _slice=0, _index=0, _field=None):
        """ Set RWPIF. Index is index of the entry in the table. """
        if _field is not None:
            runtahoesetcmd(self.changed, self.mod, self.unit, _slice,
                           _index, 1, 'rwx_rwpiftable', _field)

    def get_rwvif(self, _slice=0, _index=0):
        out = runtahoecmd(self.changed, self.mod, self.unit, _slice, _index, 'rwx_rwviftable')
        if self.print_out == 1:
            tahoe_print(out)
        else:
            convert_dict_to_int(out)
            return out

    def set_rwvif(self, _slice=0, _index=0, _field=None):
        """ Set RWVIF. Index is index of the entry in the table. """
        if _field is not None:
            runtahoesetcmd(self.changed, self.mod, self.unit, _slice,
                           _index, 1, 'rwx_rwviftable', _field)

    def get_rwsrcport(self, _slice=0, _index=0):
        out = runtahoecmd(self.changed, self.mod, self.unit, _slice, _index, 'rwx_rwsrcporttable')
        if self.print_out == 1:
            tahoe_print(out)
        else:
            convert_dict_to_int(out)
            return out

    def get_rwnivsrcvif(self, _slice=0, _index=0):
        out = runtahoecmd(self.changed, self.mod, self.unit, _slice, _index, 'rwx_rwnivdstviftable')
        if self.print_out == 1:
            tahoe_print(out)
        else:
            convert_dict_to_int(out)
            return out

    def get_vpcprune(self, _slice=0):
        """ Read qsmt vpc prune register """
        out = runtahoecmd(self.changed, self.mod,
                          self.unit, _slice, 0,
                          'qsmt_cfg_vpc_peer')
        if self.print_out == 1:
            tahoe_print(out)
        else:
            convert_dict_to_int(out)
            return out

    def get_dporttbl(self, _slice=0, _index=0):
        """ Read Dport table indexed with asic_port as of now."""
        out = runtahoecmd(self.changed, self.mod,
                          self.unit, _slice, _index,
                          "luc_dporttable")
        if self.print_out == 1:
            tahoe_print(out)
        else:
            convert_dict_to_int(out)
            return out

    def get_ovector_map(self, _slice=0, _index=0):
        ''' Read ovector_map table indexed with port_on_slice.
            gives the src_id (also called oport)'''
        out = runtahoecmd(self.changed, self.mod,
                          self.unit, _slice, _index,
                          'qsx_dhs_ovector_map')
        if self.print_out == 1:
            tahoe_print(out)
        else:
            convert_dict_to_int(out)
            return out

    def get_if_profile(self, _slice=0, _index=0):
        ''' Read if_profile table indexed with port_on_slice.
            gives the niv_index'''
        out = runtahoecmd(self.changed, self.mod,
                          self.unit, _slice, _index,
                          'qsmt_if_profile')
        if self.print_out == 1:
            tahoe_print(out)
        else:
            convert_dict_to_int(out)
            return out

    def get_src_chip_state(self, _slice=0):
        '''Read the src_chip_state table for given unit.'''
        instance = self.unit // 2
        out = runtahoecmd(False, self.mod, self.unit, _slice,
                          0, 'lua_cfg_srcchipstatetable',
                          instance)
        if self.print_out == 1:
            tahoe_print(out)
        else:
            convert_dict_to_int(out)
            return out

    def get_vpcbounce(self, _slice=0):
        out = runtahoecmd(self.changed, self.mod, self.unit, _slice, 0,
                          'luc_cfg_vpc_bounce')
        if self.print_out == 1:
            tahoe_print(out)
        else:
            convert_dict_to_int(out)
            return out

    def set_vpcbounce(self, _slice=0, _field=None):
        """ Set VPC bounce fields. """
        if _field is not None:
            runtahoesetcmd(self.changed, self.mod, self.unit, _slice,
                           0, 1, 'luc_cfg_vpc_bounce', _field)


class Bd:
    '''
    BD specific registers per module, per unit.
    '''
    mod = 1
    unit = 1
    print_out = 1  # Print to console or return to another function.
    changed = True

    def __init__(self, _mod=1,  _unit=0, _print_out=1, _change=True):
        self.mod = _mod
        self.unit = _unit
        self.print_out = _print_out
        self.changed = _change
        return

    def help(self):
        print '\t\t Table                                        INDEX'
        print '\tget_outbdstate(slice, index)                   <outer-bd> '
        print '\tget_bdstate(slice, index)                      <bd>'
        print '\tget_dstinfo(slice, index)                      <flood_dst_ptr> from bdstate table'
        print '\tget_dsbdstate(slice, index)                    <bd>'
        print '\tget_rwepgstate(slice, index)                   <bd>'
        print '\tget_vlanxlate(slice, xlate_id, epg_or_bd)      Search(Put None for dont-care)'
        print '\tget_rwvlanxlate(slice,xlat_id, bd)             Search(Put None for dont-care)'

    def get_outbdstate(self, _slice=0, _index=0):
        out = runtahoecmd(self.changed, self.mod,
                          self.unit, _slice, _index,
                          'lua_outerbdstatetable')
        if self.print_out == 1:
            tahoe_print(out)
        else:
            convert_dict_to_int(out)
            return out

    def get_bdstate(self, _slice=0, _index=0):
        out = runtahoecmd(self.changed, self.mod,
                          self.unit, _slice, _index,
                          'lub_bdstatetable')
        if self.print_out == 1:
            tahoe_print(out)
        else:
            convert_dict_to_int(out)
            return out

    def get_dstinfo(self, _slice=0, _index=0):
        '''Get the entry in dstinfo table'''
        out = runtahoecmd(False, self.mod, self.unit, _slice, _index, 'luc_dstinfotable')
        if self.print_out == 1:
            tahoe_print(out)
        else:
            convert_dict_to_int(out)
            return out

    def get_dstbdstate(self, _slice=0, _index=0):
        '''Get the entry in dstbdstate table'''
        out = runtahoecmd(self.changed, self.mod, self.unit, _slice, 
                        _index, 'luc_dstbdstatetable')
        if self.print_out == 1:
            tahoe_print(out)
        else:
            convert_dict_to_int(out)
            return out

    def get_rwepgstate(self, _slice=0, _index=0):
        out = runtahoecmd(self.changed, self.mod, self.unit, _slice, _index, 'rwx_rwepgstatetable')
        if self.print_out == 1:
            tahoe_print(out)
        else:
            convert_dict_to_int(out)
            return out

    def get_vlanxlate(self, _slice=0, _xlate_id=-1, _key_vlan=None):
        vxlate = []
        entries = runtahoecmdrange(self.changed, self.mod, self.unit, _slice, 0, 32768, 'lua_vlanxlatetable')

        # Make iterator
        if _xlate_id:
            if self.print_out == 1:
                print '{0}: {1}'.format(KEY_BD_XLATE_IDX_FIELD, hex(_xlate_id))
            entries = (item
                       for item in entries
                       if KEY_BD_XLATE_IDX_FIELD in item.keys()
                       if int(item[KEY_BD_XLATE_IDX_FIELD], 16) == _xlate_id)
        if _key_vlan:
            if self.print_out == 1:
                print '{0}: {1}'.format(KEY_VLAN0_FIELD, hex(_key_vlan))
            entries = (item
                       for item in entries
                       if KEY_VLAN0_FIELD in item.keys()
                       if int(item[KEY_VLAN0_FIELD], 16) == _key_vlan)

        if _xlate_id is None and _key_vlan is None:
            print 'Printing all valid entries'
            entries = (item
                       for item in entries
                       if KEY_VALID_FIELD in item.keys()
                       if int(item[KEY_VALID_FIELD], 16) == 0x1)

        # Parsing for the input parameters.
        for entry in entries:
            vxlate.append(entry)

        if self.print_out == 1:
            tahoe_print(vxlate)
        else:
            convert_dict_to_int(vxlate)
            return vxlate

    def get_rwvlanxlate(self, _slice=0, _xlate_id=None, _epg_or_bd=None):
        rwvxlate = []
        entries = runtahoecmdrange(self.changed, self.mod, self.unit,
                                   _slice, 0, 32768, 'rwx_rwvlanxlatetable')

        # Make iterator
        if _xlate_id:
            print '{0}: {1}'.format(KEY_BD_XLATE_IDX_FIELD, hex(_xlate_id))
            entries = (item
                       for item in entries
                       if KEY_BD_XLATE_IDX_FIELD in item.keys()
                       if int(item[KEY_BD_XLATE_IDX_FIELD], 16) == _xlate_id)
        if _epg_or_bd:
            print '{0}: {1}'.format(KEY_EPG_OR_BD_FIELD, hex(_epg_or_bd))
            entries = (item
                       for item in entries
                       if KEY_EPG_OR_BD_FIELD in item.keys()
                       if int(item[KEY_EPG_OR_BD_FIELD], 16) == _epg_or_bd)

        if _xlate_id is None and _epg_or_bd is None:
            print 'Printing all valid entries'
            entries = (item
                       for item in entries
                       if KEY_VALID_FIELD in item.keys()
                       if int(item[KEY_VALID_FIELD], 16) == 0x1)

        for entry in entries:
            rwvxlate.append(entry)

        if self.print_out == 1:
            tahoe_print(rwvxlate)
        else:
            convert_dict_to_int(rwvxlate)
            return rwvxlate


class Gwmac:
    '''
    GWMAC specific registers per module, per unit.
    '''
    mod = 1
    unit = 1
    print_out = 1  # Print to console or return to another function.
    changed = True

    def __init__(self, _mod=1,  _unit=0, _print_out=1, _change=True):
        self.mod = _mod
        self.unit = _unit
        self.print_out = _print_out
        self.changed = _change
        return

    def help(self):
        print '\t\t Table                        \t\t    INDEX'
        print '\tget_infrarmac(slice, index,)    \t <rmac_index> (none lists all'
        print '\tget_ieorsrctep(slice, mac, index)\t Pass None for wildcard'
        print '\tget_tenantrmac(slice, index)    \t <rmac_index> @ bdstate'
        print '\tget_sparekey(slice,mac,rmac_idx)\t Search with mac and rmac_index. Pass None for wildcard.'
        print '\tget_rwrmac(slice, index)        \t <rmac_index> @ rwepgstate'

    def get_infrarmac(self, _slice=0, _index=None):
        ''' Dump infra rmac table at the index. If index is None, dump all
            valid entries. '''
        if _index != None:
            out = runtahoecmd(self.changed, self.mod, self.unit, _slice, 
                              _index, 'lua_infrarmactable')
            if self.print_out == 1:
                tahoe_print(out)
            else:
                return out
        else:
            infrarmac = []
            out = runtahoecmdrange(False, self.mod, self.unit, _slice,
                                       0, 512, 'lua_infrarmactable')

            zero_mac = '00:00:00:00:00:00'
            zero_mac = translate_mac(zero_mac)

            entries = (item
                       for item in out
                       if KEY_DMAC_FIELD in item.keys()
                       if item[KEY_DMAC_FIELD] != zero_mac)

            entries = list(entries)
            if self.print_out == 1:
                tahoe_print(entries)
            else:
                return entries

    def get_ieorsrctep(self, _slice=0, _mac=None, _rmac_idx=None):
        ''' Dump ieor src tep table. If no parameters are specifid, print all
        valid entries '''
        entries = runtahoecmdrange(False, self.mod, self.unit, _slice,
                                   0, 512, 'lua_ieorsrctepkeytable')
        if _mac:
            print '{0}: {1}'.format(KEY_NARROW_DMAC_FIELD, _mac)
            _mac = translate_mac(_mac)
            entries = (item
                       for item in entries
                       if KEY_NARROW_DMAC_FIELD in item.keys()
                       if item[KEY_NARROW_DMAC_FIELD] == _mac)

        if _rmac_idx:
            print '{0}: {1}'.format(KEY_NARROW_RMAC_INDEX_FIELD, hex(_rmac_idx))
            entries = (item
                       for item in entries
                       if KEY_NARROW_RMAC_INDEX_FIELD in item.keys()
                       if int(item[KEY_NARROW_RMAC_INDEX_FIELD], 16) == _rmac_idx)
        if _mac is None and _rmac_idx is None:
            print 'Printing all valid entries.'
            entries = (item
                       for item in entries
                       if KEY_VALID_FIELD in item.keys()
                       if int(item[KEY_VALID_FIELD], 16) == 0x1)
            entries = list(entries)
        if self.print_out == 1:
            tahoe_print(entries)
        else:
            return entries

    def get_tenantrmac(self, _slice=0, _index=0):
        out = runtahoecmd(self.changed, self.mod, self.unit, _slice,
                          _index, 'lub_tenantrmactable')
        if self.print_out == 1:
            tahoe_print(out)
        else:
            return out

    def get_sparekey(self, _slice=0, _mac=None, _rmac_idx=None):
        ''' Search Rmac index using mac and/or rmac_id. All matching entries
            are dumped if one or both fields are not given'''
        sparekey = []
        entries = runtahoecmdrange(False, self.mod, self.unit, _slice,
                                   0, 512, 'lub_sparekeytable')
        if _mac:
            print '{0}: {1}'.format(KEY_DMAC_FIELD, _mac)
            _mac = translate_mac(_mac)
            entries = (item
                       for item in entries
                       if KEY_DMAC_FIELD in item.keys()
                       if item[KEY_DMAC_FIELD] == _mac)

        if _rmac_idx:
            print '{0}: {1}'.format(KEY_RMAC_INDEX_FIELD, hex(_rmac_idx))
            entries = (item
                       for item in entries
                       if KEY_RMAC_INDEX_FIELD in item.keys()
                       if int(item[KEY_RMAC_INDEX_FIELD], 16) == _rmac_idx)

        if _mac is None and _rmac_idx is None:
            print 'Printing all valid entries.'
            entries = (item
                       for item in entries
                       if KEY_VALID_FIELD in item.keys()
                       if int(item[KEY_VALID_FIELD], 16) == 0x1)

        for entry in entries:
            sparekey.append(entry)

        if self.print_out == 1:
            tahoe_print(sparekey)
        else:
            return sparekey

    def get_rwrmac(self, _slice=0, _index=0):
        out = runtahoecmd(self.changed, self.mod, self.unit, _slice, _index, 'rwx_rwtenantrmactable')
        if self.print_out == 1:
            tahoe_print(out)
        else:
            return out


class Stats:
    '''
    Stats registers per module, per unit.
    '''
    mod = 1
    unit = 1
    print_out = 1  # Print to console or return to another function.
    changed = True

    rwx_drop_dict = {0: 'ihdr_src_chip_prune_uc',
                     1: 'ihdr_src_chip_prune_mc',
                     2: 'ihdr_src_chip_prune_fl',
                     3: 'ihdr_if_prune',
                     4: 'vlan_mbr',
                     5: 'same_if_mc',
                     6: 'same_if_uc',
                     7: 'same_vif_uc',
                     8: 'ttl_expire',
                     9: 'bmx_drop',
                     10: 'bmx_flush',
                     11: 'eoferr_first_cell',
                     12: 'vacl_drop',
                     13: 'racl_drop',
                     14: 'rbacl_drop',
                     15: 'sup_drop',
                     16: 'sup_policer_drop',
                     17: 'pif_block_bc',
                     18: 'pif_block_uuc',
                     19: 'pif_block_umc',
                     20: 'mc_dvif_xlate_miss',
                     21: 'uc_dvif_xlate_miss',
                     22: 'outer_vlan_mbr',
                     23: 'vlan_xlate_miss',
                     24: 'outer_vlan_xlate_miss',
                     25: 'mc_met_core_if_prune',
                     26: 'l3_same_if_mc',
                     27: 'ihdr_src_chip_prune_uk',
                     28: 'illegal_rw_op',
                     29: 'aging_drop',
                     30: 'spare',
                     31: 'spare'}

    def __init__(self, _mod=1,  _unit=0, _print_out=1, _change=True):
        self.mod = _mod
        self.unit = _unit
        self.print_out = _print_out
        self.changed = _change
        return

    def help(self):
        print '\t\t Table                        \t\t    INDEX'
        print '\trwx_drop(slice)        Rwx Drop counters.'
        print '\tlux_drop(slice)        Lux drop counters.'
        print '\tsa_bf_drop(slice)      Bloom filter mac learn drops.'
        print '\tmac_learn_count(slice)    Src learn counters.'

    def rwx_drop(self, _slice=0):
        out = runtahoecmdrange(False, self.mod, self.unit,
                               _slice, 0, 32, 'rwx_dhs_drop_count')
        for entry in out:
            print "%s : %s" % (self.rwx_drop_dict[entry['index_in_table']],
                               entry['val'])
        # Zero out all entries after reading.
        if (self.changed):
            print "changed set - so resetting counters."
            runtahoesetcmd(self.changed, self.mod, self.unit, _slice,
                           0, 32, "rwx_dhs_drop_count", 'val=0x0')

    def lux_drop(self, _slice=0):
        out = runtahoecmd(False, self.mod, self.unit,
                               _slice, 0, 'lud_cnt_drop', 0)

        for entry in out:
            value = "".join(val for val in entry['val'].split('0x')[1])
            value = "0x"+value
            print "Drop counter: {0}".format(value)

    def sa_bf_drop(self, _slice=0):
        out = runtahoecmd(False, self.mod, self.unit,
                               _slice, 0, 'fpb_cnt_stm_bf_discard_sa')

        for entry in out:
            print "Bloom Filter discard counter: {0}".format(entry['filtered'])

    def mac_learn_count(self, _slice=0):
        out = runtahoecmd(False, self.mod, self.unit,
                               _slice, 0, 'fpb_cnt_notify_sa')

        for entry in out:
            print "Mac SA Learn Counter: {0}".format(entry['tx'])


If = None
bd = None
gw = None
fp = None
stats = None


def init(change=True):
    '''Init function for basic testing. Not for use with the apis.
       Please init the variables based on need'''
    global If
    global bd
    global gw
    global fp
    global stats
    If = Interface(_mod=1, _unit=0, _print_out=1, _change=change)
    bd = Bd(_mod=1, _unit=0, _print_out=1, _change=change)
    gw = Gwmac(_mod=1, _unit=0, _print_out=1, _change=change)
    fp = Fpx(_mod=1, _unit=0, _print_out=1, _change=change)
    stats = Stats(_mod=1, _unit=0, _print_out=1, _change=change)


def help():
    print 'Inteface class registers: If.<xxx>'
    If.help()

    print 'Bd class registers: bd.<xxx>'
    bd.help()

    print 'Gwmac class registers: gw.<xxx>'
    gw.help()

    print 'Fpx class registers: fp.<xxx>'
    fp.help()

    print 'Stats class register: stats.<xxx>'
    stats.help()


def print_lpm_table(format_str, tcam_all, tcam_data):
    print 'Legend:\n NumP: Number of ecmp paths, MP: ECMP active'
    print 'CC: Copy to SUP, SR: SA SUP Redirect, DR: DA SUP Redirect'
    print 'TD: TTL Decrement, DC: Direct Connect, DE: Default Entry'
    print 'LI: Learn Info'
    print '------------------------------------------------------------------------------'
    print format_str.format('Bank', 'Index', 'Vrf', 'IP/Len', 'Base/L2Ptr', 'NumP', 'MP', 'CC', 'SR', 'DR', 'TD', 'DC', 'DE', 'LI')
    print '------------------------------------------------------------------------------'
    for i, j in zip(tcam_all, tcam_data):
        if int(i[KEY_V4_VRF], 16) == 0:
            vrf = '0x1'
        else:
            vrf = i[KEY_V4_VRF]

        is_ecmp = get_changed_value(j, KEY_ECMP_V4)

        if is_ecmp:
            l2ptr = get_changed_value(j, KEY_ECMP_V4_BASE_PTR)
            num_paths = get_changed_value(j, KEY_ECMP_V4_NUM_PATHS)
        else:
            l2ptr = get_changed_value(j, KEY_V4_L2PTR)
            num_paths = 0

        try:
            print format_str.format(
                i['tcam_bank'],
                i['index_in_table'],
                vrf,
                i[KEY_L3_TCAM_IP] + '/' + str(
                    get_changed_value(j, KEY_V4_PREFIX)),
                hex(l2ptr),
                num_paths,
                is_ecmp,
                get_changed_value(j, KEY_V4_SUP_COPY),
                get_changed_value(j, KEY_V4_SA_SUP_REDIRECT),
                get_changed_value(j, KEY_V4_DA_SUP_REDIRECT),
                get_changed_value(j, KEY_V4_TTL_DEC_BYPASS),
                get_changed_value(j, KEY_V4_SA_DIRECT_CONNECT),
                get_changed_value(j, KEY_V4_DEF_ENTRY),
                get_changed_value(j, KEY_V4_LEARN_INFO))
        except KeyError:
            pass


def show_hardware_internal_lpm_v4():
    '''V4 LPM data is in banks 4-7'''
    fpaobject = Fpx(_print_out=0)
    tcam_all = fpaobject.get_fib_tcam_all(_slice=0, range_lo=4, range_hi=7)
    tcam_data = fpaobject.get_fib_tcam_data(_slice=0, range_lo=4, range_hi=7)
    for entry in tcam_all:
        entry[KEY_L3_TCAM_IP] = nxos_utils.get_ipv4_from_hex(
            entry[KEY_L3_TCAM_IP])
    # Format string for:
    # 'Bank', 'Index', 'Vrf', 'IP/Len', 'Base/L2Ptr', 'NumP', 'MP', 'CC', 'SR', 'DR', 'TD', 'DC', 'DE', 'LI'
    table = '{0:<5}{1:<5}{2:<11}{3:<20}{4:<10}{5:<5}{6:<3}{7:<3}{8:<3}{9:<3}{10:<3}{11:<3}{12:<3}{13:<2}'
    print_lpm_table(table, tcam_all, tcam_data)


def show_hardware_internal_lpm_v6():
    '''V6 LPM data is in banks 0-3'''
    fpaobject = Fpx(_print_out=0)
    tcam_all = fpaobject.get_fib_tcam_all(_slice=0, range_lo=0, range_hi=3)
    # Since the data is replicated 4 times
    tcam_data = fpaobject.get_fib_tcam_data(_slice=0, range_lo=0, range_hi=0)
    # For ipv6, the ipv6 is spread across banks 0-3 (bank 3 having the LSB)
    # So concatenate the ip address and rest of the data has been duplicated
    print len(tcam_all)
    print len(tcam_data)
    jump = len(tcam_all) / 4
    for i in xrange(0, len(tcam_all) / 4):
        # Each value is a hex string
        tcam_all[i][KEY_L3_TCAM_IP] = '0x{0}{1}{2}{3}'.format(
            tcam_all[i + 3 * jump][KEY_L3_TCAM_IP][2:],
            tcam_all[i + 2 * jump][KEY_L3_TCAM_IP][2:],
            tcam_all[i + 1 * jump][KEY_L3_TCAM_IP][2:],
            tcam_all[i][KEY_L3_TCAM_IP][2:])
        tcam_all[i][KEY_L3_TCAM_IP] =\
            nxos_utils.get_ipv6_from_hex(tcam_all[i][KEY_L3_TCAM_IP])

    # Format string for:
    # 'Bank', 'Index', 'Vrf', 'IP/Len', 'Base/L2Ptr', 'NumP', 'MP', 'CC', 'SR', 'DR', 'TD', 'DC', 'DE', 'LI'
    table = '{0:<5}{1:<5}{2:<11}{3:<38}{4:<10}{5:<5}{6:<3}{7:<3}{8:<3}{9:<3}{10:<3}{11:<3}{12:<3}{13:<2}'
    print_lpm_table(table, tcam_all[0:len(tcam_all) / 4], tcam_data)


def decode_ieth(_int_list, _ieth_header_list):
    '''Helper function to decode ieth header'''
    for ieth_header in _ieth_header_list:

        try:
            ieth = format(int(ieth_header, 16), 'X')
            hw.tah.iethdecode.decode_ieth_header(ieth)
        except ValueError:
            print 'Invalid ieth header given. please try again'


