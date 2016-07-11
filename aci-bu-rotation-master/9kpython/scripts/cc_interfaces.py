###################################################
#
#      File:   cc_interfaces.py
#      Name:   Mark Landgrebe
#
#       Description: Interfaces Consistency Checker
#
#
#
# Copyright (c) 2015 by Cisco Systems, Inc.
# All rights reserved.
#
###################################################

import cli, json, os, re, subprocess, sys

def get_password():
    
    print ("Enter switch password: ")
    sys.stdout.flush()
    password = raw_input('')
    return password

def check_stack():
    
    text = cli.cli("show running-config | grep 'nxapi use-vrf'")
    if text:
	return True
    else:
	return False

def get_show_run_all_output():

    output = cli.cli("show run all")
    with open("/tmp/cli_dump.cmd", "w") as text_file:
        text_file.write(output)

def check_nxapi_enabled():
    
    line = cli.cli("show feature | inc nxapi")
    if "disabled" in line:
        return False
    
    else: 
	return True

class CurlHelper:

    transport = "http"
    server_url = None
    resource_url = None
    accept_header = "Accept:application/json"
    auth_header = "Authorization: Basic Y2lzY286Y2lzY28="
    content_header = "content-type:application/json"
    curl_data = ""

    def __init__ (self,resource_url, ip_addr,
                  transport=None,
                  ):
     
        if resource_url == None:
            log.error("CurlHelper: init failed: resource_url cannot be None")
            return

        if transport:
            CurlHelper.transport = str(transport)

        if ip_addr:
            CurlHelper.ip_addr = str(ip_addr)

        if resource_url:
            self.resource_url = resource_url

        self.server_url = CurlHelper.transport + "://" + CurlHelper.ip_addr + \
                          "/" + self.resource_url

    def set_auth_cookie(self, token):

        CurlHelper.auth_cookie = "APIC-cookie=" + token

def curl_helper (url,ip):

    curl_helper_obj = CurlHelper(url, ip)

    return curl_helper_obj

def aaa_auth(ip, url, payload):
    
    """Authorize the user and set the cookie for later transactions."""
    url_resource = "api/aaaLogin.json"
    chelper = curl_helper(url,ip)
    chelper.curl_data = json.dumps(payload)
    req_netns = check_stack()
    data = ""
    if req_netns:
	try:
            p = subprocess.Popen(["ip", "netns", "exec", "management", "/usr/bin/curl",  "-s", \
                                  "-X", "POST", chelper.server_url, \
                                  "-H", chelper.accept_header, "-H", chelper.auth_header, \
                                  "--insecure", "-1", \
                                  "-d", chelper.curl_data],
                                 stdout=subprocess.PIPE)
	    (output, err) = p.communicate()
	    data = json.loads(output)
        except:
	    print "DME Authentication Request Failed\n"
	    exit(1)
    else:
        try:
            p = subprocess.Popen(["/isan/bin/curl", "-s", \
    			          "-X", "POST", chelper.server_url, \
    			          "-H", chelper.accept_header, "-H", chelper.auth_header, \
    			          "--insecure", "-1", \
    			          "-d", chelper.curl_data],
    			         stdout=subprocess.PIPE)
	    (output, err) = p.communicate()
	    data = json.loads(output)
        except:
	    print "DME Authentication Request Failed\n"
    	    exit(1)

    if isinstance(data, dict) and 'imdata' in data and 'aaaLogin' in data['imdata'][0]:
        token = data['imdata'][0]['aaaLogin']['attributes']['token']
        chelper.set_auth_cookie(token)

def get (ip, url, file_name):
    
    chelper = curl_helper(url,ip)
    req_netns = check_stack()
    data = ""
    if req_netns:
	try:
            p = subprocess.Popen(["ip", "netns", "exec", "management", "/usr/bin/curl",  "-s", 
                                  "-X", "GET", chelper.server_url, \
                                  "-H", chelper.accept_header, "--cookie", chelper.auth_cookie, \
                                  "--insecure", "-1"],
                                 stdout=subprocess.PIPE)
	    (output, err) = p.communicate()
	    data = json.loads(output)
	except:
	    print "Error Retrieving Information From DME\n"
            exit(1)
    else:
        try:
            p = subprocess.Popen(["/isan/bin/curl", "-s",
    			          "-X", "GET", chelper.server_url, \
    			  	  "-H", chelper.accept_header, "--cookie", chelper.auth_cookie, \
    			          "--insecure", "-1"],
    			         stdout=subprocess.PIPE)
	    (output, err) = p.communicate()
	    data = json.loads(output)
        except:
	    print "Error Retrieving Information From DME\n"
	    exit(1)
    
    if isinstance(data, dict) and 'imdata' in data:
        with open(file_name, 'w') as outfile:
            json.dump(data, outfile)
        outfile.close()

    return data

def prepare_cli_lines():

    f = open("/tmp/cli_dump.cmd","r+")
    d = f.readlines()
    f.seek(0)
    flag = 0

    for line in d:
        if "interface port-channel" in line:
            flag = 1

        if "interface Ethernet" in line:
            flag = 1

        if "interface mgmt0" in line:
            break

        if flag == 1:
            f.write(line)

    f.truncate()
    f.close()

def parse_cli():

    fp = open('/tmp/cli_dump.cmd')
    intf = ""
    myList = []
    interfaces = {}
    for line in fp:
        line = line.rstrip('\n').lstrip()
	
	if line.find("interface Ethernet") == 0:
	    if (myList != [] and "." not in intf) and intf != "":
		interfaces[intf] = myList	
            intf = line
	    myList = []
	
        if line.find("interface port-channel") == 0:
            if (myList != [] and "." not in intf) and intf != "":
		interfaces[intf] = myList
	    intf = line
            myList = []

	if line.find("shutdown") == 0:
	    myList.append(line)

	if line.find("no shutdown") == 0:
	    myList.insert(0, line)

        if len(line) == 13 and "no switchport" in line:
            myList.append(line)

        if len(line) == 10 and "switchport" in line:
            myList.append(line)

        if "switchport mode" in line:
            myList.append(line)

        if "switchport trunk allowed vlan" in line:
            myList.append(line)

        if "switchport access" in line:
            myList.append(line)

        if "channel-group" in line and "." not in line:
            arr = line.split()
            line = arr[0] + " " + arr[1]
            myList.append(line)
	
    fp.close()
    interfaces[intf] = myList
    return interfaces

def parse_pcm_gc_json():

    with open('/tmp/intf_channel_groups.json') as json_file:
        pcm_dict = json.load(json_file)
    count = int(pcm_dict["totalCount"])
    pairs = []
    for i in range(0, count):
        children = pcm_dict["imdata"][i]["pcAggrIf"]["children"]
        num_children = len(children)
        for j in range(0, num_children):
            if "pcRsMbrIfs" in children[j]:
                po = str(children[j]["pcRsMbrIfs"]["attributes"]["parentSKey"])
                channel_group = po.replace("po", "channel-group ")
                eth = str(children[j]["pcRsMbrIfs"]["attributes"]["tSKey"])
                interface = eth.replace("eth", "interface Ethernet")
                intf_ch_group_pair = (interface, channel_group)
                pairs.append(intf_ch_group_pair)

    return pairs

def parse_intf_port_channel_json():

    with open('/tmp/intf_channel_groups.json') as json_file:
        pcm_dict = json.load(json_file)
    count = int(pcm_dict["totalCount"])
    
    pos = {}
    myList = []

    for i in range(0, count):
        json_intf = str(pcm_dict["imdata"][i]["pcAggrIf"]["attributes"]["id"])
        py_po = json_intf.replace("po", "interface port-channel")
   
	json_adminst = str(pcm_dict["imdata"][i]["pcAggrIf"]["attributes"]["adminSt"])
	py_adminst = ""
	if json_adminst == "up":
	    py_adminst = "no shutdown"
     
	if json_adminst == "down":
	    py_adminst = "shutdown"

        json_switchport = pcm_dict["imdata"][i]["pcAggrIf"]["attributes"]["layer"]   
        py_switchport = "no switchport"

        if json_switchport == "Layer2":
            py_switchport = "switchport"

	py_mode = ""
	py_trunkVlans = ""
	py_accessVlan = ""

	if py_switchport == "switchport":
	    json_mode = pcm_dict["imdata"][i]["pcAggrIf"]["attributes"]["mode"]

	    if json_mode == "trunk":
		py_mode = "switchport mode trunk"
	 
	    if json_mode == "access":
		py_mode = "switchport mode access"

            json_trunkVlans = pcm_dict["imdata"][i]["pcAggrIf"]["attributes"]["trunkVlans"]
            json_accessVlan = pcm_dict["imdata"][i]["pcAggrIf"]["attributes"]["accessVlan"]
            
	    py_trunkVlans = "switchport trunk allowed vlan " + json_trunkVlans
	    if json_trunkVlans == "":
		py_trunkVlans = py_trunkVlans + "none" 

            py_accessVlan = "switchport access " +  json_accessVlan.replace("-", " ")
	myList.append(py_adminst)
        myList.append(py_switchport)

        if len(py_mode) > 0: 
            myList.append(py_mode)

        if len(py_accessVlan) > 0:
            myList.append(py_accessVlan)

        if len(py_trunkVlans) > 0:
            myList.append(py_trunkVlans)

        pos[py_po] = myList
        myList = []

    return pos

def parse_json():

    with open('/tmp/intf_eths.json') as json_file:
        json_data = json.load(json_file)

    count = int(json_data["totalCount"])
    interfaces = {}
    myList = []

    for i in range(0, count):
        json_intf = str(json_data["imdata"][i]["l1PhysIf"]["attributes"]["id"])
        py_intf = json_intf.replace("eth", "interface Ethernet")
        
	json_adminst = str(json_data["imdata"][i]["l1PhysIf"]["attributes"]["adminSt"])
	py_adminst = ""
	if json_adminst == "up":
	    py_adminst = "no shutdown"

	if json_adminst == "down":
	    py_adminst = "shutdown"

        json_switchport = json_data["imdata"][i]["l1PhysIf"]["attributes"]["layer"] 
	py_switchport = "no switchport"	

        if json_switchport == "Layer2":
            py_switchport = "switchport"
	
        py_mode = ""
	py_trunkVlans = ""
	py_accessVlan = ""

	if py_switchport == "switchport":
	
            json_mode = json_data["imdata"][i]["l1PhysIf"]["attributes"]["mode"]

            if json_mode == "trunk":
                py_mode = "switchport mode trunk"
	    
            if json_mode == "access":
		py_mode = "switchport mode access"
            
	    json_trunkVlans = json_data["imdata"][i]["l1PhysIf"]["attributes"]["trunkVlans"]
            json_accessVlan = json_data["imdata"][i]["l1PhysIf"]["attributes"]["accessVlan"]
	    
            py_trunkVlans = "switchport trunk allowed vlan " + json_trunkVlans
		
	    if json_trunkVlans == "":
		py_trunkVlans = py_trunkVlans + "none"

	    py_accessVlan = "switchport access " +  json_accessVlan.replace("-", " ")

        myList.append(py_adminst)
        myList.append(py_switchport)

        if len(py_mode) > 0: 
            myList.append(py_mode)

        if len(py_accessVlan) > 0:
            myList.append(py_accessVlan)

        if len(py_trunkVlans) > 0:
            myList.append(py_trunkVlans)

        interfaces[py_intf] = myList
        myList = []
    return interfaces

def combine_json_dictionaries():

    po_dict = parse_intf_port_channel_json()
    eth_dict = parse_json()

    po_keys = list(po_dict.keys())
    for k in po_keys:
        try:
	    eth_dict[k] = po_dict[k]
	except ValueError:
	    print "Error Retrieving Information from DME\n"
    	    exit(1)
    return eth_dict

def add_channel_groups(dme_dict):

    intf_cg_pairs = parse_pcm_gc_json()
    for pair in intf_cg_pairs:
       	index = pair[0]
        old_list = dme_dict[index]
    	old_list.append(pair[1])
    	dme_dict[index] = old_list

    return dme_dict

def print_diffs(cli_dict, dme_dict):
    count = 0
    ks = cli_dict.keys()
    if set(ks) != set(dme_dict.keys()):
	print "ERROR: Not All Interfaces Are Present in Both DME and Backend\n"
	return -1
    else:
        for k in ks:
            if cli_dict[k] != dme_dict[k]:
            	if count == 0:
		    print "Inconsistencies:"
            	cliStr = ", ".join(cli_dict[k])
                dmeStr = ", ".join(dme_dict[k])
		
		s1 = "\tRunning Config: " + k
		s2 = "{:<48}".format(s1)
                print s2 + cliStr
                    
                s3 = "\tDME     Config: " + k
                s4 = "{:<48}".format(s3)
		print s4 + dmeStr + "\n"
	        
		count = 1    	

def check_interface_consistency():
    nxapi_status = check_nxapi_enabled()    
    if nxapi_status == False:
	print "Please enable 'feature nxapi' to use this consistency checker"
        return -1

    mgmt_ip = "127.0.0.1"
    get_show_run_all_output()   
    password = get_password() 
   
    aaa_auth(mgmt_ip, "api/aaaLogin.json", { "aaaUser": { "attributes": { "name": "admin", "pwd": password }}})
    get(mgmt_ip, "api/class/l1PhysIf.json", "/tmp/intf_eths.json")
    get(mgmt_ip, "api/class/pcAggrIf.json?rsp-subtree=full", "/tmp/intf_channel_groups.json")
    get(mgmt_ip, "api/class/sys/ethpmPhysIf.json", "/tmp/operational.json")    
    prepare_cli_lines()

    cli_dict = parse_cli()
    dme_dict = combine_json_dictionaries()
    
    comp_dme_dict = add_channel_groups(dme_dict)
    
    ans = cmp(cli_dict, comp_dme_dict)
    print "\nChecking Consistency of All Interfaces for\n\tStatus, Layer, Mode, Access Vlan, Trunk Vlans, Channel Group, \n\tOperational Status, Operational Speed, and Operational Duplex\n" 
    
    p = subprocess.Popen("/isan/python/scripts/cc_operational.py", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, errors = p.communicate()
     
    if output and ans == 0:
       print output
       print "Consistency Check: FAILED\n"
       return False 
    
    if output and ans != 0:
        print_diffs(cli_dict, comp_dme_dict)
        print output
        print "Consistency Check: FAILED\n"
        return False

    if not output and ans != 0:
        print_diffs(cli_dict, comp_dme_dict)
        print "Consistency Check: FAILED\n"
	return False

    else:
        print "Consistency Check: PASSED\n"
        return True
        
check_interface_consistency()
