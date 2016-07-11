#################################################
#
#      File:   mac.py
#      Name:   Vijay Sampath
#
#       Description: test l2fm clear-hit-bit {da | sa} module <mod> [unit <unit>]
#
#
#
# Copyright (c) 1985-2015 by cisco Systems, Inc.
# All rights reserved.
#
#################################################

import re
from nxos import *
from onxos import *
import nxos_utils
from libnxos_ext_api import py_pixm_lib_ifidx_to_di
import tahoe

############################################################
# handler called from C code
#   _stringList[0]: "clearda"|"clearsa"|"showda"|"showsa"
#   _stringList[1]: mac
#   _modList[0]:    mod
#   _modList[1]:    unit (optional)
############################################################


def mac_hit(_intList, _stringList):
    if not _stringList or not _intList:
        print "Error in parameters"
        return

    show = False
    da = False
    sa = False
    if "show" in _stringList[0]:
        show = True
    elif not "clear in _stringList[0]":
        print "Error in parameters. show or clear required."
        return

    if "da" in _stringList[0]:
        da = True
    elif "sa" in _stringList[0]:
        sa = True
    else:
        print "Error in parameters. da or sa required."
        return

    mac = _stringList[1]
    mod = _intList[0]
    unitPassed = False
    if len(_intList) == 2:
        unit = _intList[1]
        unitPassed = True
    if py_pfm_is_module_online(mod-1) != 1:
        print "Module %d is not online"%mod
        return
    modObj = Nxos.Module(mod)
    if unitPassed:
        if unit >= modObj.units:
            print "Invalid unit %d for module %d"%(unit, mod)
            return
        units = [unit]
    else:
        units = []
        for unit in range(0, modObj.units):
            units.append(unit)
    for unit in units:
        macHw = HwMacEntry(mod, unit, mac)
        if not macHw.found:
            print "mac %s not found in module %d unit %d"%(mac, mod, unit)
            return
        if show and da:
            print "HITDA = %d in module %d unit %d"%(macHw.getHitDA(), mod, unit)
            continue
        if show and sa:
            print "HITSA = %d in module %d unit %d"%(macHw.getHitSA(), mod, unit)
            continue
        # Clear
        if (da):
            if macHw.getHitDA() == 0:
                print "HITDA Already 0 in mod %d unit %d"%(mod, unit)
            else:
                print "resetting HITDA in mod %d unit %d"%(mod, unit)
                macHw.resetHitDA()
                macHw = HwMacEntry(mod, unit, mac)
                if not macHw.found:
                    print "not found!"
                    return
                print "\tcurrent HITDA (after reset) = %d"%macHw.getHitDA()
        else:
            if macHw.getHitSA() == 0:
                print "HITSA Already 0 in mod %d unit %d"%(mod, unit)
            else:
                print "resetting HITSA in mod %d unit %d"%(mod, unit)
                macHw.resetHitSA()
                macHw = HwMacEntry(mod, unit, mac)
                if not macHw.found:
                    print "not found!"
                    return
                print "\tcurrent HITSA (after reset) = %d"%macHw.getHitSA()


def get_l2_sw_entries():
    '''Parse output of show mac address-table'''
    # Match '*' or '+' or ' ' then vlan digits, then mac, then interface
    match_string = '\s*(?:\*|\+|\s?)\s*?(\d+).*({0}).*({1}|(?i)vpc.*|(?i)nve.*)'.format(
                   nxos_utils.rex.MACADDR,
                   nxos_utils.rex.INTERFACE_NAME)
    mac_vlan_dict = {}
    vxlan_mac_vlan_dict = {}
    output = nxos_utils.runVshCmd("show mac address-table")
    lines = output.split("\n")
    for line in lines:
        line = line.strip()
        # SVI vPC Peer gateway vdc mac is not stored in dleft/hw, 
        # so no need to verify these macs
        if "static" in line and "vPC Peer-Link" in line:
            continue
        m = re.match(match_string, line)
        peer_id = 0
        if m:
            # Save the mac address
            # (convert from HHHH.HHHH.HHHH to integer form)
            try:
                entry = m.groups()
                vlan = int(entry[0])
                mac_addr = int('0x' + ''.join(entry[1].split('.')), 16)
                interface = entry[2].strip()
                if "nve" in interface:
                    # TODO : Get this ip str from regex
                    ip_str = interface.split("(")[1].split(")")[0]
                    parts = ip_str.split(".")
                    ip_num = (int(parts[0]) << 24) + (int(parts[1]) << 16) + (int(parts[2]) << 8) + int(parts[3])
                    peer_id = py_nve_peer_id_from_peer_ip(ip_num);
            except IndexError:
                print 'Incomplete match'
                continue
            #CSCux08388 For vxlan case, vdc mac will be present in SW against SVI interface
            #Need to skip CC check for them as they wont be in HW
            if "Vlan" in interface:
                continue
            mac_vlan_dict[(mac_addr, vlan)] = interface
            if "nve" in interface and peer_id != 0:
                vxlan_mac_vlan_dict[(mac_addr, vlan)] = peer_id
                #print "mac addr: " + str(hex(mac_addr)) + ",vlan: " + str(vlan) + ",intf " + ip_str + "ip num: "+ str(hex(ip_num))+",peer_id = "+str(peer_id)

        else:
            continue
    return mac_vlan_dict,vxlan_mac_vlan_dict

def get_l2_dleft_entries(module=1):
    '''Get L2 entries from dleft table'''
    cmd = 'slot {0} quoted '.format(module) +\
        '"sh hardware internal tah sdk-l2 entries"'
    match_string =\
            'DstNivIdx:\s*(\d*).*DstIdx:\s*(\d*).*MacAddress:\s*({0})'.format(
            nxos_utils.rex.MACADDR, nxos_utils.rex.HEX)
    match_string += '.*BD:\s*(\d*).*FPX: (\d+).*?Tile: (\d+).*?Index: (\d+).*?'
    match_string += 'Ocam: (\d+).*?TcamIndex: (\d+)'
    dleft_dict = {}

    # Get output of "show mac address-table". All l2 entries here must be in
    # dleft and the hardware.
    output = nxos_utils.runVshCmd(cmd)
    lines = output.split("\n")
    for line in lines:
        line = line.strip()

        m = re.match(match_string, line)
        if m:
            # Should get the entry as:
            # (niv_idx, mac_address, vlan_hex, fpx, tile, index)
            try:
                entry = m.groups()
                mac_addr = int('0x' + ''.join(entry[2].split(':')), 16)
                vlan = int(entry[3])

                dleft_dict[(mac_addr, vlan)] =\
                    {'niv_idx': int(entry[0]),
                     'ltl': int(entry[1]),
                     'fpx': int(entry[4]),
                     'tile': int(entry[5]),
                     'index': int(entry[6]),
                     'ocam' : int(entry[7]),
                     'tcam_index' : int(entry[8])}
            except IndexError:
                print 'Incomplete match'
                continue
        else:
            continue
    return dleft_dict


def get_l2_hw_entries(module, slice = 0):
    '''Read the entries in the HW and return a dictionary
       indexed by (mac, vlan). For now only for slice 0'''
    hw_dict = {}
    fp = tahoe.Fpx(_mod=module, _unit=0,
                   _print_out=0, _change=True)
    hw_list = fp.get_l2(slice)  
    hw_tcam_list = fp.get_l2_tcam(slice)

    for entry in hw_list:
	try:
	    mac = entry[tahoe.KEY_L2_ENTRY_MACKEY_MAC_FIELD]
	    vlan = entry[tahoe.KEY_L2_ENTRY_MACKEY_FID_FIELD]
	except KeyError:
	    continue
	# Convert to integers
	mac = int(hw_mac_2_sw_mac(mac), 16)
	vlan = int(vlan, 16)
	# Sanity check, observing some weird vlan numbers
	if vlan > 4096:
	    continue
	hw_dict[(mac, vlan)] =\
	    {'fpx': entry['fpx'],
	     'tile': entry['tile'],
	     'index': entry['index_in_table'],
	     'ocam': 0,
	     'tcam_index': -1}
    for tcam_entry in hw_tcam_list:
	try:
	    tcam_entry['valid']
	except KeyError:
	    continue
	try:
	    key = tcam_entry['key'].split(':')
	    vlan = int(key[1], 16) >> 16 
	    # Sanity check, observing some weird vlan numbers 
	    if vlan > 4096:
		continue
	    mac_0 = int(key[1], 16) & 0x0000ffff
	    mac_str = '0x%x:%s' % (mac_0, key[2])
	    mac = int(hw_mac_2_sw_mac(mac_str), 16)
	    hw_dict[(mac, vlan)] =\
		{'fpx': 0,
		 'tile': 0,
		 'index': -1,
		 'ocam': 1,
		 'tcam_index': tcam_entry['index_in_table']}
	    
	except KeyError:
	    continue
    return hw_dict


def hw_mac_2_sw_mac(mac):
    '''Translate the mac string from HW to regular mac string'''
    # Translate the mac address to an integer value
    # It is stored in hw as:
    # 0x0000abcd:0xefabcdef -> AB:CD:EF:AB:CD:EF
    mac_split = mac.split(':')
    mac_split = [item.split('x')[1]
                 for item in mac_split]
    return '0x' + ''.join(mac_split)


def validate_l2(module_list):
    '''Python handler for L2 entry consistency checker'''
    fail_flag = False
    module = int(module_list[0])
    print 'Fetching SW entries.'
    mac_vlan_dict,vxlan_mac_vlan_dict = get_l2_sw_entries()
    print 'Fetching SDK entries.'
    dleft_dict = get_l2_dleft_entries(module)
    if tahoe.is_davos():
	    num_slices = 2
    elif tahoe.is_lacrosse():
	    num_slices = 6
    else:
	    num_slices = 1
    for x in range(0,num_slices):
	    print 'Fetching HW entries for slice %d.' %x
	    hw_dict = get_l2_hw_entries(module,x)

	    for entry in mac_vlan_dict.keys():
		loop_continue = False
		# Dleft check
		try:
		    entry_dleft = dleft_dict[entry]
		    # If this is an NVE intf, compare the dstidx
		    #print "Intf: " + str(mac_vlan_dict[entry])
		    if "nve" in mac_vlan_dict[entry]:
			#print "Mac  " +str(entry[0]) + ",vlan "+ str(entry[0]) + ",sw idx "+ str(vxlan_mac_vlan_dict[entry])+",sdk "+str(entry_dleft['niv_idx'])
			if (vxlan_mac_vlan_dict[entry] != entry_dleft['niv_idx']):
			    print 'MAC: {0} VLAN: {1} dst index in SW and SDK don"t match'.format(
				    format(entry[0], 'x'), entry[1])
		except KeyError:
		    fail_flag = True
		    loop_continue = True
		    print 'MAC: {0} VLAN: {1} not found in SDK table'.format(
			tahoe.get_mac_from_hex(entry[0]), entry[1])

		# HW table check
		try:
		    entry_hw = hw_dict[entry]
		except KeyError:
		    fail_flag = True
		    loop_continue = True
		    print 'MAC: {0} VLAN: {1} not found in HW table on slice {2}'.format(
			tahoe.get_mac_from_hex(entry[0]), entry[1], x)

		if loop_continue:
		    continue

		# Location check
		if (entry_dleft['ocam']):
		    #Ensure entries are programmed in overflow tcam
		    if(entry_dleft['ocam'] != entry_hw['ocam'] and 
		       entry_dleft['tcam_index'] != entry_hw['tcam_index']):
			fail_flag = True
			print '\nLocation in sw and hw table do not match in tcam'
			print 'Mac={0} VLAN={1}'.format(format(entry[0], 'x'),
							entry[1])
			print 'SDK: ocam {0} tcam_index {1}'.format(
			    entry_dleft['ocam'], entry_dleft['tcam_index'])
			print 'HW: ocam {0} tcam_index {1} slice {2} '.format(
			    entry_hw['ocam'], entry_hw['tcam_index'], x)
		else:
		    if (entry_dleft['fpx'] != entry_hw['fpx'] or
			    entry_dleft['tile'] != entry_hw['tile'] or
			    entry_dleft['index'] != entry_hw['index']):
			fail_flag = True
			print '\nLocation in sw and hw table do not match'
			print 'MAC={0} VLAN={1}'.format(format(entry[0], 'x'),
							entry[1])
			print 'SDK: fp {0} tile {1} index {2}'.format(
			    entry_dleft['fpx'], entry_dleft['tile'],
			    entry_dleft['index'])
			print 'HW: fp {0} tile {1} index {2} slice {3}'.format(
			    entry_hw['fpx'], entry_hw['tile'],
			    entry_hw['index'], x)

	    # Number of entries check
	    #if len(hw_dict.keys()) != len(mac_vlan_dict.keys()):
	    #    print '\nFollowing extra entries present in HW. Minor Failure'
	    #    for key in hw_dict.keys():
	    #        try:
	    #            entry = mac_vlan_dict[key]
	    #        except KeyError:
	    #            print 'MAC: {0}, VLAN: {1} not found in SW table'.format(
	    #                format(key[0], 'x'), key[1])
	    #            continue

    if fail_flag:
	print 'Consistency check: FAILED'
    else:
	print 'Consistency check: PASSED'


def show_interface(_params, _ifNameList):
    if_index = _params[0]
    if_type = _params[1]
    dest_index = py_pixm_lib_ifidx_to_di(if_index)
    print 'IfIndex: {0}'.format(if_index)
    print 'DstIndex: {0}'.format(dest_index)
    print 'IfType: {0}'.format(if_type)
    try:
        tahoe.get_intf_info(_ifNameList[0])
    except:
        pass
