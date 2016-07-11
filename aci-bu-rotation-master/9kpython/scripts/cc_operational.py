#!/isan/bin/python
###################################################
#
#      File:   cc_operational.py
#      Name:   Mark Landgrebe
#
#      Description: Operational Functions for CC
#
#
#
# Copyright (c) 2015 by Cisco Systems, Inc.
# All rights reserved.
#
###################################################
from onxos import *
import libnxos_ext_api
import re, json, cli

def get_all_oper_interfaces_from_cli():
  
    brief_output = cli.cli("show interface brief")
    eths = re.findall('Eth[0-9]+/[0-9]+/{0,1}[0-9]*', brief_output)  
    interfaces = [intf.replace('Eth', 'Ethernet') for intf in eths]
    return interfaces

def get_oper_status(intf_names):
    
    intf_oper_pairs = []   
    for intf_name in intf_names:
        i = Nxos.Interface(intf_name)
	(err, oper_stat) = libnxos_ext_api.py_im_get_ifindex_oper_status(i.ifindex, 1)
	if oper_stat == 0:
	    stat = "unknown"
	
	elif oper_stat == 1:
	    stat = "up"
        
	elif oper_stat == 2:
	    stat = "down"
	
	elif oper_stat == 16:
	    stat = "link-up"
	
	else:
	    stat = "ERROR"
        
	intf_oper_pairs.append(stat)
	
    return intf_oper_pairs

def get_oper_speed(intf_names):
    
    intf_oper_pairs = []
	
    for intf_name in intf_names:
        i = Nxos.Interface(intf_name)
	(err, oper_speed) = libnxos_ext_api.py_im_get_ifindex_oper_speed(i.ifindex, 1)  
        
	if oper_speed == 0:
	    speed = "auto"
	
	elif oper_speed == 100:
	    speed = "100M"

	elif oper_speed == 106:
	    speed = "auto 100M"
	
	elif oper_speed == 120:
	    speed = "auto 100M 1G"

	elif oper_speed == 1000:
	    speed = "1G"

	elif oper_speed == 10000:
	    speed = "10G"

	elif oper_speed == 40000:
	    speed = "40G"

	elif oper_speed == 100000:
	    speed = "100G"

	elif oper_speed == -1:
	    speed = "unknown"
   
	else:
	    speed = "ERROR"

        intf_oper_pairs.append(speed)

    return intf_oper_pairs

def get_oper_duplex(intf_names):
    
    intf_oper_pairs = []
	
    for intf_name in intf_names:
        i = Nxos.Interface(intf_name)
	(err, oper_duplex) = libnxos_ext_api.py_im_get_ifindex_oper_duplex(i.ifindex, 1)
	if oper_duplex == 1:
	    duplex = "half"
	
	elif oper_duplex == 2:
	    duplex = "full"
	
	elif oper_duplex == 3:
	    duplex = "auto"
	
	else:
	    duplex = "ERROR"

	intf_oper_pairs.append(duplex)

    return intf_oper_pairs

def combine_opers_from_cli():

    interfaces = get_all_oper_interfaces_from_cli()
    statuses = get_oper_status(interfaces)
    speeds = get_oper_speed(interfaces)
    duplexes = get_oper_duplex(interfaces)
    all_oper_tuples = zip(statuses, speeds, duplexes)
    opers = [list(tup) for tup in all_oper_tuples]
    oper_dictionary = {}
    for intf, opr in zip(interfaces, opers):
        oper_dictionary["interface " + intf] = opr  
    
    return oper_dictionary

def parse_opers_json():

    with open('/tmp/operational.json') as json_file:
        oper_data = json.load(json_file)
    count = int(oper_data["totalCount"])
    oper_dictionary = {}
    for i in range(0, count):
    	attributes = oper_data["imdata"][i]["ethpmPhysIf"]["attributes"]
    	intf_str = str(attributes["dn"])
    	intf = re.match(r"[^[]*\[([^]]*)\]", intf_str).groups()[0]
    	interface = intf.replace("eth", "interface Ethernet")
    	status = str(attributes["operSt"])
    	speed = str(attributes["operSpeed"])
    	duplex = str(attributes["operDuplex"])
    	oper_dictionary[interface] = [status, speed, duplex]

    return oper_dictionary

def handle_oper_inconsistencies(oper_cli_dict, oper_dme_dict):

    count = 0
    ks = oper_cli_dict.keys()
    if set(ks) != set(oper_dme_dict.keys()):
    	print "ERROR: For Operational Checks, Not All Interfaces Are Present in Both DME and Backend"
    	return False
    else:
    	for k in ks:
            if oper_cli_dict[k] != oper_dme_dict[k]:
            	if count == 0:
		    inconStr = "Operational Inconsistencies:"
		    inconStr_fixed_len = "{:<64}".format(inconStr)
		    print inconStr_fixed_len + "Status, Speed, Duplex" 
                oper_cliStr = ", ".join(oper_cli_dict[k])
                oper_dmeStr = ", ".join(oper_dme_dict[k])

		s1 = "\tRunning Operational Config: " + k
		s2 = "{:<57}".format(s1)
		print s2 + oper_cliStr

		s3 = "\tDME     Operational Config: " + k
		s4 = "{:<57}".format(s3)
		print s4 + oper_dmeStr + "\n"
                
    	        count = 1
	return True

def check_opers_eq():
    
    dme_opers = parse_opers_json()
    pss_opers = combine_opers_from_cli()
   
    ans = cmp(dme_opers, pss_opers)
    if ans == 0:
        return True
    else:
        handle_oper_inconsistencies(pss_opers, dme_opers)
        return False    

check_opers_eq()
