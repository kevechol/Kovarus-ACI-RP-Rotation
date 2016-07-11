#################################################
#
#      File:   cc_my_station_tcam.py
#      Name:   Akshya Gupta
#
#       Description: MY_STATION_TCAM table gw mac
#                    consistency checker
#  
#
#
# Copyright (c) 1985-2013, 2015 by cisco Systems, Inc.
# All rights reserved.
#
#################################################


from onxos import *
from sets import Set
import nxos_utils

BASE_HEX = 16
VRMAC = 0x04000000

def to_hex_str(mac_addr_int):
    """
    Convert a mac address in hex value to ':' separated string
    """
    temp_str = format(mac_addr_int, 'x');
    return ':'.join(s.encode('hex')
                    for s in temp_str.decode('hex'))

def print_error(mac_addr, vlan, module, unit):
    """
    Print error for (mac_addr, vlan) not found in my_station_tcam table
    for unit in the module
    """
    print "MAC: {0} VLAN: {1} not found in module {2} unit {3}".format(
        to_hex_str(mac_addr), vlan, module, unit)


def print_success(mac_addr, vlan, module, unit):
    """
    Print success for (mac_addr, vlan) found in my_station_tcam table
    for unit in the module
    """
    print "MAC: {0} VLAN: {1} consistent in module {2} unit {3}".format(
        to_hex_str(mac_addr), vlan, module, unit)


def get_gwmac_list():
    """
    Creates a list of dictionaries. For each entry, key is a tuple of
    (mac, vlan) and the value contains the local and remote peer status
    and the set flags (node_l2_flags).
    """
    gwmac_list = []
    out = nxos_utils.runVshCmd("show system internal l2fm info gwmacdb")
    lines = out.split("\n")
    for line in lines:
        # Check if the line starts with a valid mac address. Store the mac
        # address if found. Continue otherwise.
        line = line.strip()  # remove preceeding spaces
        m = re.match(nxos_utils.rex.MACADDR, line)
        if m:
            # Save the mac address
            # (convert from HHHH.HHHH.HHHH to integer form)
            mac_addr = int('0x' + ''.join(m.group(0).split('.')), BASE_HEX)
        else:
            continue
        # Obtain uint32 value of node_l2_flags
        node_l2_flags =\
            int(re.search('node_l2_flags 0x({0})'.format(nxos_utils.rex.HEX),
                          line).group(1), BASE_HEX)
        # If node_l2_flags do not lie beyond VRMAC, go to next line
        if not(node_l2_flags & VRMAC):
            continue

        vlan = int(re.search('Vlan ([0-9]+) ', line).group(1))
        peer_states = re.search('St ({0}, {0}), '.format(nxos_utils.rex.ALPHA),
                                line).group(1).split(',')
        local_state = peer_states[0].strip()
        remote_state = peer_states[1].strip()
        list_entry = {'mac_addr': mac_addr, 'vlan': vlan,
                      'node_l2_flags': node_l2_flags,
                      'local_state': local_state, 'remote_state': remote_state}
        gwmac_list.append(list_entry)
    return gwmac_list


def validate_gwmacdb():
    """
    Validates the gwmacdb obtained in the configuration with the one configure
    in all the forwarding asics in system. TODO add support for netapp mode
    """
    gwmac_list = get_gwmac_list()
    miss_count = 0
    # Get the mac dbs on all units
    mod_list = Nxos.Module.getOnlineFLCModules()

    for mod in mod_list:
        # Run for each unit in the mod
        for unit in xrange(0, mod.units):
            tcam_table = HwMacDB(mod.mod, unit)
            miss_flag = False
            for entry in gwmac_list:
                key = (entry['mac_addr'], entry['vlan'])
                if key not in tcam_table.tcam_entry_list:
                    print_error(entry['mac_addr'], entry['vlan'],
                                mod.mod, unit)
                    miss_count += 1
                else:
                    print_success(entry['mac_addr'], entry['vlan'],
                                  mod.mod, unit)

    if miss_count:
        print "Consistency Check: FAILED"
        py_syslog(1, "CC_MY_STATION_TCAM: Consistency Check: FAILED")
    else:
        print "Consistency Check: PASSED"
        py_syslog(1, "CC_MY_STATION_TCAM: Consistency Check: PASSED")
