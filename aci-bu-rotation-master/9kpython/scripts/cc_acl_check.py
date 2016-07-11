######################################################
#
#      File:   cc_acl_check.py
#      Name:   
#
#      Description: ACL consistency checker routines
#  
#
#
# Copyright (c) 1985-2013, 2015-2016 by cisco Systems, Inc.
# All rights reserved.
#
######################################################

import signal
import onxos
import nxos_utils
from libnxos_ext_api import *
from libbcmshell import *
from port_counters import *
import re
import sys

gIPv4Racl = 21

signal.signal(signal.SIGINT, nxos_utils.signal_handler_sigint)

def cc_validate_single_racl(_ipv4, _ifObject, _aclName, _dir, _ifName):

    if 'in' == _dir:
            output = runBcmCmd(_ifObject.slot, _ifObject.unit,
                                       "d chg source_trunk_map_modbase " +
                                       str(_ifObject.dmod) + " 1")
            obj = nxos_utils.createHwTableObject(output)
            base = obj.table[obj.table.keys()[0]]['BASE']
            ibase = int(base, 16)
	    ientry = ibase + _ifObject.hw_port
	    output1 = runBcmCmd(_ifObject.slot, _ifObject.unit,
			       "d chg source_trunk_map " +
			       str(ientry) + " 1")
	    obj1 = nxos_utils.createHwTableObject(output1)
	    l3iif = obj1.table[obj1.table.keys()[0]]['L3_IIF']
	    output2 = runBcmCmd(_ifObject.slot, _ifObject.unit,
			       "d chg l3_iif " + l3iif + " 1")
	    obj2 = nxos_utils.createHwTableObject(output2)
	    class_id = obj2.table[obj2.table.keys()[0]]['CLASS_ID']
	    label = int(class_id, 16) & 0x7f
#re_pattern = '[ ]+IPV4 RACL \[racl\][ ,0-9]+'
            re_pattern = '[ ]+IPV4 RACL \[racl\]*|[ ]+IPV4 RACL Lite \[racl-lite\]*'
            dirName = 'input'
            qualName = 'InterfaceClassL3'
    else:
        cmd = "d chg egr_port " + str(_ifObject.hw_port) + " 1"
        output = runBcmCmd(_ifObject.slot, _ifObject.unit, cmd)
	obj = nxos_utils.createHwTableObject(output)
	label = int(obj.table[obj.table.keys()[0]]['EGR_PORT_GROUP_ID'])
#re_pattern = '[ ]+Egress IPV4 RACL \[e\-racl\][ ,0-9]+'
        re_pattern = '[ ]+Egress IPV4 RACL \[e\-racl\]*'
        dirName = 'output'
        qualName = 'InterfaceClassPort'

    base = ''
    size = ''
    cmd = "slot " + str(_ifObject.slot) + " show system internal access-list globals"
    output = nxos_utils.runVshCmd(cmd)
    lines = output.split("\n")
    for line in lines:
        mt = re.match(re_pattern, line)
        if mt is None:
            continue

        is_lite = line.find("Lite")
        line = line.strip()
        words = line.split(" ")
        a = []
        for word in words:
            if '' != word:
                a.append(word)

        if 'in' in _dir:
            if is_lite == -1: #racl
                base = a[5]
                size = a[6]
            else:             #racl-lite
                base = a[6]
                size = a[7]
        else:
            base = a[6]
            size = a[7]
        ibase = int(base)
        isize = int(size)
        if isize == 0: #skip racl if size is zero and try to find racl-lite
            continue
        else:   
            break


    output = nxos_utils.runVshCmd("slot " + str(_ifObject.slot) + " show system internal access-list interface " + _ifName + " " + dirName + " entries")


    #cut output of instance info above this instance
    str1 = "INSTANCE 0x"+str(_ifObject.unit+1)
    insts_after = output.split(str1, 1);

    #cut output of instance below this instance
    str1 = "INSTANCE 0x"+str(_ifObject.unit)
    insts = insts_after[0].split(str1, 1);

    if len(insts) >= 2:
        banks = insts[1].split("Bank")
    else:
        return (False, None)

    eids = []

    for bank in banks:
         if 'RACL' not in bank:
             continue

         entries = bank.split("Entries:")
         if len(entries) <= 1:
             continue

         data = entries[1].split()
         for i in data:
             if "L4" in i or "protocol" in i:
                 break
             if _ipv4 == 1:
                 if "IPv6" in i:
                     #print "IPv6 encountered"
                     break
             loc = i.split("(")
             try:
                 eids.append(ibase + (int(loc[0])+1))
             except:
                 continue
         break

    eidInfo = {}
    for eid in eids:
         eidInfo[eid] = {}
         cmd = "fp show entry " + str(eid)
         output = runBcmCmd(_ifObject.slot, _ifObject.unit, cmd)
         lines = output.split("\n")
         accum = False
         for line in lines:
             mt = re.match('^ [A-Z,a-z,0-9]+', line)
             if mt is not None:
                 accum = True
                 key = mt.group(0).strip()
                 eidInfo[eid][key] = []
                 continue

             if accum == True:
                 eidInfo[eid][key].append(line)

    eidLabels = []
    for eidI in eidInfo.keys():
         if qualName not in eidInfo[eidI].keys():
             continue

         classInfos = eidInfo[eidI][qualName]
         for ci in classInfos:
             if "DATA" in ci:
                 words = ci.strip().split('=')
                 if label == int(words[1], 16):
                     eidLabels.append((eidI,label))
                 break

    missing_eids = []
    for eid in eids:
        if (eid,label) not in eidLabels:
            missing_eids.append((eid-ibase-1))

    if len(eidLabels) == len(eids):
       return (True, None)
       print "Consistency Check: SUCCESS"
       print "Information is consistent between hardware and software"
    else:
       return (False, missing_eids)
       print "Consistency Check: FAILED"
       print "Information is not consistent between hardware and software"


def validate_racl(_ifindexList = None, _ifNameList = None):
    """
    testing
    """
    ok = []
    nok = []
    if _ifNameList is None:
        print "Module is not online or doesn't exist"
        return

    print "Validates IPV4 RACLs on up interfaces:"
    listIdx = -1
    for ifname in _ifNameList:
        listIdx += 1
        if "." in ifname:
            nms = ifname.split(".")
            name = nms[0]
            sinumber = nms[1]
            continue
        else:
            name = ifname
            sinumber = ""

        i = onxos.Nxos.Interface(name)
        l = i.get_sw_link_state()
        if l == 0:
            continue

        if i.swLayer == 2:
            continue

        #skip Ranger+ ports
        #if i.dmod == 0:
        if py_im_is_ifindex_ranger_attached(_ifindexList[listIdx]):
            #print "Skipping Ranger+ interface " + ifname
            continue

        #show running interface ethernet x/y"
        output = nxos_utils.runVshCmd("show running-config interface " + ifname)
        lines = output.split("\n")

        #exclude ports that are members of port-channel
        pc_member = 0
        for line in lines:
            line = line.strip()
            if "channel-group" in line:
               pc_member = 1
               break;

        if pc_member == 1:
            #print "Skipping PC member " + name + "\n"
            continue;

        for line in lines:
            line = line.strip()
            if "access-group" in line:
                words = line.split(" ")
                if words[1] == str('port'):
                   aclName = words[3]
                   dir = words[4]
                else:
                   aclName = words[2]
                   dir = words[3]

                (r,missing_eids) = cc_validate_single_racl(1, i, _aclName = aclName, _dir = dir, _ifName = ifname)
                if r == True:
                   ok.append((i, sinumber, dir, None))
                else:
                   nok.append((i, sinumber, dir, missing_eids))

    if len(nok) != 0:
       print "Consistency Check: FAILED"
       onxos.py_syslog(1, "CC_RACL_IPV4: Consistency Check: FAILED")
    else:
       print "Consistency Check: PASSED"
       onxos.py_syslog(1, "CC_RACL_IPV4: Consistency Check: PASSED")

    if len(ok) != 0:
        print ""
        print "Found consistencies for following Interfaces:"
        for (i, sinumber, dir, meids) in ok:
            if "" == sinumber:
                print "  ", i.longName, "(%s)"%dir
            else:
                print "   %s.%s"%(i.longName, sinumber), "(%s)"%dir

    if len(nok) != 0:
        print ""
        print "Found inconsistencies for following Interfaces and EID:"
        for (i, sinumber, dir, meids) in nok:
            if "" == sinumber:
                print "  ", i.longName, "(%s)"%dir, meids
            else:
                print "   %s.%s"%(i.longName, sinumber), "(%s)"%dir, meids


def validate_racl_pc(_ifindexList = None, _ifNameList = None):
    """
    testing
    """
    ok = []
    nok = []
    if _ifNameList is None:
        print "Module is not online or doesn't exist"
        return

    print "Validates IPV4 RACLs on up interfaces:"
    for ifname in _ifNameList:
        if "." in ifname:
            nms = ifname.split(".")
            name = nms[0]
            sinumber = nms[1]
            continue
        else:
            name = ifname
            sinumber = ""

        p = onxos.Nxos.Interface(name)
        l = p.get_sw_link_state()
        if l == 0:
            continue

        if p.swLayer == 2:
            continue

        for i in p.members:
            #show running interface ethernet x/y"
            output = nxos_utils.runVshCmd("show running-config interface " + ifname)
            lines = output.split("\n")

            for line in lines:
                line = line.strip()
                if "access-group" in line:
                    words = line.split(" ")
                    aclName = words[2]
                    dir = words[3]

                    (r,missing_eids) = cc_validate_single_racl(1, i, _aclName = aclName, _dir = dir, _ifName = ifname)
                    if r == True:
                       ok.append((i, sinumber, dir, None))
                    else:
                       nok.append((i, sinumber, dir, missing_eids))

    if len(nok) != 0:
       print "Consistency Check: FAILED"
       onxos.py_syslog(1, "CC_RACL_IPV4: Consistency Check: FAILED")
    else:
       print "Consistency Check: PASSED"
       onxos.py_syslog(1, "CC_RACL_IPV4: Consistency Check: PASSED")

    if len(ok) != 0:
        print ""
        print "Found consistencies for following Interfaces:"
        for (i, sinumber, dir, meids) in ok:
            if "" == sinumber:
                print "  ", i.longName, "(%s)"%dir
            else:
                print "   %s.%s"%(i.longName, sinumber), "(%s)"%dir

    if len(nok) != 0:
        print ""
        print "Found inconsistencies for following Interfaces and EID:"
        for (i, sinumber, dir, meids) in nok:
            if "" == sinumber:
                print "  ", i.longName, "(%s)"%dir, meids
            else:
                print "   %s.%s"%(i.longName, sinumber), "(%s)"%dir, meids

     
def validate_copp():
    
    print "Validating CoPP ACLs..."
    
    pmap_op = nxos_utils.runVshCmd("show policy-map interface control-plane")
    pmap_lines = pmap_op.split("\n")

    acl_op = nxos_utils.runVshCmd("show access-lists summary")
    acl_lines = acl_op.split("\n")

    ok = []
    err = []
    cnt = 0

    #build hash table with key as ACL name and value as No. of ACEs configured
    acl_htbl = {}

    for aline in acl_lines:        
        if "ACL" in aline:
            aline = aline.strip()
            words = aline.split(" ")
            aclName = words[-1]
            continue

        if "Total ACEs Configured:" in aline:
            aline = aline.strip()
            words = aline.split(" ")
            num_ace = words[3]
            acl_htbl[aclName] = int(num_ace)
            
    #check if any acl in pmap_op has 0 ACEs
    for pline in pmap_lines:
        pline = pline.strip()
        if "match access-group name" in pline:
            words = pline.split(" ")
            aclName = words[3]
           
            ace_op = nxos_utils.runVshCmd("show access-lists "+aclName)
            ace_lines = ace_op.split("\n")
            for ace_line in ace_lines:
                ace_line = ace_line.strip()
                words = ace_line.split(" ")
                if words[0].isdigit():
                    cnt +=1
	    
            if acl_htbl[aclName] == 0:
                print "ERROR: Number of ACEs configured for ACL %s is 0"%aclName
                onxos.py_syslog(1,"ERROR: Number of ACEs configured for ACL " + aclName + " is 0")
     
    	    if acl_htbl[aclName] != cnt:
	      	    print "ERROR: Number of ACE entries [%d] does not match Total ACEs configured [%d]"%(cnt,acl_htbl[aclName])
        	    onxos.py_syslog(1,"ERROR: Number of ACE entries ["+ str(cnt) +"] does not match Total ACEs configured ["+ str(acl_htbl[aclName]) +"]")

            if acl_htbl[aclName] == 0 or acl_htbl[aclName] != cnt:
                err.append(aclName)
            else:
                ok.append(aclName)
		
    	    cnt = 0

    if len(err) == 0 and len(ok) != 0:
        print "\nCoPP ACLs consistency check PASSED"
    elif len(err) != 0:
    	print "\nCoPP ACLs consistency check FAILED"
    else:
        print "\nNo CoPP ACLs found"


#######################################START OF ACL CCs FOR TAHOE################################################

re_idx = re.compile("\[([0-9A-Fa-f]+):([0-9A-Fa-f]+):([0-9A-Fa-f]+)\].")
re_acl_name = re.compile("Policies:\s+\w+\((.*)\)")
hex_p = "0x[A-Fa-f0-9]+"	
re_valid = re.compile("valid=(%s)"%hex_p)
re_wide_key = re.compile("entry_v6_lo_wide_key=(%s)"%hex_p)
re_wide_key_msk = re.compile("entry_mask_v6_lo_wide_key=(%s)"%hex_p)
re_if_lbl = re.compile("entry_ce_cmn_if_label=(%s)"%hex_p)
re_bd_lbl = re.compile("entry_ce_cmn_bd_label=(%s)"%hex_p)
re_bd_or_vnid = re.compile("entry_ce_cmn_bd_or_vnid=(%s)"%hex_p)
re_rbacl_lbl = re.compile("entry_ce_cmn_rbacl_label=(%s)"%hex_p)
re_if_lbl_msk = re.compile("entry_mask_ce_cmn_if_label=(%s)"%hex_p)
re_bd_lbl_msk = re.compile("entry_mask_ce_cmn_bd_label=(%s)"%hex_p)
re_bd_or_vnid_msk = re.compile("entry_mask_ce_cmn_bd_or_vnid=(%s)"%hex_p)
re_rbacl_lbl_msk = re.compile("entry_mask_ce_cmn_rbacl_label=(%s)"%hex_p)

TAH_ING_IFACL_LABEL_MASK = 0xFFF
TAH_ING_BD_LABEL_MASK = 0xFFF
TAH_ING_BD_OR_VNID_MASK = 0xFF0000
TAH_ING_RBACL_MASK = 0xFFF
TAH_EGR_IFACL_MASK = 0x3F
TAH_EGR_BD_LABEL_MASK = 0x3FFF

pi_if_lbl = '0x0'
pi_if_lbl_msk = '0x0'
pi_bd_lbl = '0x0'
pi_bd_lbl_msk = '0x0'
pi_rbacl_lbl = '0x0'
pi_rbacl_lbl_msk = '0x0'

debug_on = False

def DEBUG_PRINT(str):
    if debug_on:
        print str		

#####################################################################################################
def get_globals_info(dir, region):

    globals_output = runVshCmd("show system internal access-list globals | grep %s"%region)
    globals_output = globals_output.split("\n")

    if 'in' in dir:
        for line in globals_output:
	    if 'Ingress' in line:
	        glb_line = line.strip()
    	        glb_line = " ".join(glb_line.split())
	        tokens = glb_line.split()
	        base = tokens[3]
	        break

    else:
        for line in globals_output:
	    if 'Egress' in line:
	        glb_line = line.strip()
	        glb_line = " ".join(glb_line.split())
	        tokens = glb_line.split()
	        base = tokens[3]
	        break

    return(base)	

#######################################################################################################
def get_hw_dump_cmd_info(asic_type, tcamDir, sw_index):
   
    if 'ingress' in tcamDir:
        if sw_index < 2048:
            hw_index = sw_index/2
            tbl_no = 0
        else:
            hw_index = (sw_index - 2048)/2
            tbl_no = 1

        if sw_index % 2:
            tbl_name = "tah_%s_acb_actcamkeytable1"%asic_type
        else:
            tbl_name = "tah_%s_acb_actcamkeytable0"%asic_type 

    else:
        tbl_no = 0
        if sw_index < 1024:
            hw_index = sw_index/2
            if sw_index % 2:
                tbl_name = "tah_%s_rwx_rwegtcamkeytable1"%asic_type
            else:
                tbl_name = "tah_%s_rwx_rwegtcamkeytable0"%asic_type

        else:
            hw_index = (sw_index - 1024)/2
            if sw_index % 2:
                tbl_name = "tah_%s_rwx_rwegtcamkeytable3"%asic_type
            else:
                tbl_name = "tah_%s_rwx_rwegtcamkeytable2"%asic_type

    return(tbl_no, tbl_name, hw_index)

########################################################################################
def pi_to_pd_label(slot, lbl_type, lbl_val):

    lbl_output = nxos_utils.runVshCmd(" show hardware access-list labels " + lbl_type + " " + str(lbl_val) + " module " + str(slot))    
   
    lbl_output = lbl_output.split("\n") 
    for line in lbl_output:
        if 'ifacl_label:' in line:
            lbl_line = line.strip()
            lbl_tkns = lbl_line.split()
            pi_if_lbl = lbl_tkns[1]

        if 'ifacl_label_mask:' in line:
            lbl_line = line.strip()
            lbl_tkns = lbl_line.split()
            pi_if_lbl_msk = lbl_tkns[1]
       
        if 'bd_label:' in line:
            lbl_line = line.strip()
            lbl_tkns = lbl_line.split()
            pi_bd_lbl = lbl_tkns[1]

        if 'bd_label_mask:' in line:
            lbl_line = line.strip()
            lbl_tkns = lbl_line.split()
            pi_bd_lbl_msk = lbl_tkns[1]

        if 'rbacl_label:' in line:
            lbl_line = line.strip()
            lbl_tkns = lbl_line.split()
            pi_rbacl_lbl = lbl_tkns[1]

        if 'rbacl_label_mask:' in line:
            lbl_line = line.strip()
            lbl_tkns = lbl_line.split()
            pi_rbacl_lbl_msk = lbl_tkns[1]

    return(pi_if_lbl, pi_if_lbl_msk, pi_bd_lbl, pi_bd_lbl_msk, pi_rbacl_lbl, pi_rbacl_lbl_msk)

###########################################################################################################
def acl_check_label(slot, unit, inst, tcamDir, sw_idx, pi_if_lbl, pi_if_lbl_msk, pi_bd_lbl, pi_bd_lbl_msk,\
                                                                        pi_rbacl_lbl, pi_rbacl_lbl_msk): 
    
    if_lbl = '0x0'
    if_lbl_msk = '0x0'
    bd_lbl = '0x0'
    bd_lbl_msk = '0x0'
    bd_or_vnid = '0x0'
    bd_or_vnid_msk = '0x0'
    rbacl_lbl = '0x0'
    rbacl_lbl_msk = '0x0'

    wide_key = '0x0'
    wide_key_msk = '0x0'

    entry_invalid = True                                                                           
    mismatch = False                  

    asic_type = nxos_utils.get_asic_type()
    if 'Unknown' in asic_type:
        print 'Unknown asic type'
        sys.exit(0)

    #getting tah vmr label info from hw tcam entries
    (tbl_no, tbl_name, hw_idx) = get_hw_dump_cmd_info(asic_type, tcamDir, sw_idx)

    #check wide key
    if 'ingress' in tcamDir:
        hw_dump_wide_key = runVshCmd("debug hardware internal " + asic_type + \
                            " dump asic " + str(unit) + " slice " + str(inst) + " table " + str(tbl_no) + ":" + tbl_name + \
                            " " + str(hw_idx) + " 1 field-per-line | i \"entry_v6_lo_wide_key|entry_mask_v6_lo_wide_key\"")

    else:
        hw_dump_wide_key = runVshCmd("debug hardware internal " + asic_type + \
                            " dump asic " + str(unit) + " slice " + str(inst) + " table " + tbl_name + \
                            " " + str(hw_idx) + " 1 field-per-line | i \"entry_v6_lo_wide_key|entry_mask_v6_lo_wide_key\"")

    for line in hw_dump_wide_key.splitlines():
        if "entry_v6_lo_wide_key" in line:
            match_wide_key = re_wide_key.match(line)
            if match_wide_key:
                wide_key = match_wide_key.group(1)

        if "entry_mask_v6_lo_wide_key" in line:
            match_wide_key_msk = re_wide_key_msk.match(line)
            if match_wide_key_msk:
                wide_key_msk = match_wide_key_msk.group(1)

    if (int(wide_key_msk, 16) == 0) and (int(wide_key, 16) == 1):
        (tbl_no, tbl_name, hw_idx) = get_hw_dump_cmd_info(asic_type, tcamDir, (sw_idx+1))

        if 'ingress' in tcamDir:
            hw_dump_output = runVshCmd("debug hardware internal " + asic_type + \
                            " dump asic " + str(unit) + " slice " + str(inst) + " table " + str(tbl_no) + ":" + tbl_name + \
                            " " + str(hw_idx) + " 1 field-per-line")

        else:
            hw_dump_output = runVshCmd("debug hardware internal " + asic_type + \
                            " dump asic " + str(unit) + " slice " + str(inst) + " table " + tbl_name + \
                            " " + str(hw_idx) + " 1 field-per-line")

    else:
        (tbl_no, tbl_name, hw_idx) = get_hw_dump_cmd_info(asic_type, tcamDir, sw_idx)

        if 'ingress' in tcamDir:
            hw_dump_output = runVshCmd("debug hardware internal " + asic_type + \
                            " dump asic " + str(unit) + " slice " + str(inst) + " table " + str(tbl_no) + ":" + tbl_name + \
                            " " + str(hw_idx) + " 1 field-per-line")

        else:
            hw_dump_output = runVshCmd("debug hardware internal " + asic_type + \
                            " dump asic " + str(unit) + " slice " + str(inst) + " table " + tbl_name + \
                            " " + str(hw_idx) + " 1 field-per-line")

    hw_dump_output = hw_dump_output.split("\n")
    for line in hw_dump_output:

        match_valid = re_valid.match(line)
        match_if_lbl = re_if_lbl.match(line)
        match_bd_lbl = re_bd_lbl.match(line)
        match_bd_or_vnid = re_bd_or_vnid.match(line)
        match_rbacl_lbl = re_rbacl_lbl.match(line)
        match_if_lbl_msk = re_if_lbl_msk.match(line)
        match_bd_lbl_msk = re_bd_lbl_msk.match(line)
        match_bd_or_vnid_msk = re_bd_or_vnid_msk.match(line)
        match_rbacl_lbl_msk = re_rbacl_lbl_msk.match(line)

        if match_valid:
            if int(match_valid.group(1), 16) == 1:
                entry_invalid = False
        
        if match_if_lbl:
            if_lbl = match_if_lbl.group(1)

        if match_if_lbl_msk:
            if_lbl_msk = match_if_lbl_msk.group(1)

        if match_bd_lbl:
            bd_lbl = match_bd_lbl.group(1)

        if match_bd_lbl_msk:
            bd_lbl_msk = match_bd_lbl_msk.group(1)

        if match_bd_or_vnid:
            bd_or_vnid = match_bd_or_vnid.group(1)

        if match_bd_or_vnid_msk:
            bd_or_vnid_msk = match_bd_or_vnid_msk.group(1)

        if match_rbacl_lbl:
            rbacl_lbl = match_rbacl_lbl.group(1)

        if match_rbacl_lbl_msk:
            rbacl_lbl_msk = match_rbacl_lbl_msk.group(1)


    #form appropriate tah vmr labels
    if_lbl = int(if_lbl, 16)
    if_lbl = hex(if_lbl)
    rbacl_lbl = int(rbacl_lbl, 16)
    rbacl_lbl = hex(rbacl_lbl)

    if 'ingress' in tcamDir:
        bd_lbl = int(bd_lbl, 16)
        bd_or_vnid = (int(bd_or_vnid, 16) & TAH_ING_BD_OR_VNID_MASK)
        bd_lbl = bd_lbl | bd_or_vnid
        bd_lbl = hex(bd_lbl)

        if_lbl_msk = (~int(if_lbl_msk, 16) & TAH_ING_IFACL_LABEL_MASK)
        if_lbl_msk = hex(if_lbl_msk)
        rbacl_lbl_msk = (~int(rbacl_lbl_msk, 16) & TAH_ING_RBACL_MASK)
        rbacl_lbl_msk = hex(rbacl_lbl_msk)
        bd_lbl_msk = (~int(bd_lbl_msk, 16) & TAH_ING_BD_LABEL_MASK)
        bd_or_vnid_msk = (~int(bd_or_vnid_msk, 16) & TAH_ING_BD_OR_VNID_MASK)
        bd_lbl_msk = bd_lbl_msk | bd_or_vnid_msk
        bd_lbl_msk = hex(bd_lbl_msk)

    else:
        bd_lbl = int(bd_lbl, 16)
        bd_lbl = hex(bd_lbl)

        if_lbl_msk = (~int(if_lbl_msk, 16) & TAH_EGR_IFACL_MASK)
        if_lbl_msk = hex(if_lbl_msk)
        bd_lbl_msk = (~int(bd_lbl_msk, 16) & TAH_EGR_BD_LABEL_MASK)
        bd_lbl_msk = hex(bd_lbl_msk)


    #check for consistency
    if pi_if_lbl_msk != if_lbl_msk:
        mismatch = True
        DEBUG_PRINT("ifacl_label/mask mismatch for sw_idx %d: if_lbl: %s, hw_if_lbl: %s, if_lbl_msk: %s, hw_if_lbl_msk: %s\n"%\
                (sw_idx, pi_if_lbl, if_lbl, pi_if_lbl_msk, if_lbl_msk))
    else:
        if pi_if_lbl_msk is not '0x0':
            if pi_if_lbl != if_lbl:
                mismatch = True
                DEBUG_PRINT("ifacl_label/mask mismatch for sw_idx %d: if_lbl: %s, hw_if_lbl: %s, if_lbl_msk: %s, hw_if_lbl_msk: %s\n"%\
                                (sw_idx, pi_if_lbl, if_lbl, pi_if_lbl_msk, if_lbl_msk))

    if pi_bd_lbl_msk != bd_lbl_msk:
        mismatch = True
        DEBUG_PRINT("bd_label/mask mismatch for sw_idx %d: bd_lbl: %s, hw_bd_lbl: %s, bd_lbl_msk: %s, hw_bd_lbl_msk: %s\n"%\
                        (sw_idx, pi_bd_lbl, bd_lbl, pi_bd_lbl_msk, bd_lbl_msk))
    else:
        if pi_bd_lbl_msk is not '0x0':
            if pi_bd_lbl != bd_lbl:
                mismatch = True
                DEBUG_PRINT("bd_label/mask mismatch for sw_idx %d: bd_lbl: %s, hw_bd_lbl: %s, bd_lbl_msk: %s, hw_bd_lbl_msk: %s\n"%\
                                (sw_idx, pi_bd_lbl, bd_lbl, pi_bd_lbl_msk, bd_lbl_msk))

    if pi_rbacl_lbl_msk != rbacl_lbl_msk:
        mismatch = True
        DEBUG_PRINT("rbacl_label/mask mismatch for sw_idx %d: rbacl_lbl: %s, hw_rbacl_lbl: %s, rbacl_lbl_msk: %s, hw_rbacl_lbl_msk: %s\n"%\
                (sw_idx, pi_rbacl_lbl, rbacl_lbl, pi_rbacl_lbl_msk, rbacl_lbl_msk))
    else:
        if pi_rbacl_lbl_msk is not '0x0':
            if pi_rbacl_lbl != rbacl_lbl:
                mismatch = True
                DEBUG_PRINT("rbacl_label/mask mismatch for sw_idx %d: rbacl_lbl: %s, hw_rbacl_lbl: %s, rbacl_lbl_msk: %s, hw_rbacl_lbl_msk: %s\n"%\
                                (sw_idx, pi_rbacl_lbl, rbacl_lbl, pi_rbacl_lbl_msk, rbacl_lbl_msk))


    dbg_str = "%s, %s"%(pi_if_lbl, if_lbl)
    DEBUG_PRINT(dbg_str)
    dbg_str = "%s, %s"%(pi_bd_lbl, bd_lbl)
    DEBUG_PRINT(dbg_str)
    dbg_str = "%s, %s"%(pi_rbacl_lbl, rbacl_lbl)
    DEBUG_PRINT(dbg_str)
    DEBUG_PRINT("mask")	
    dbg_str = "%s, %s"%(pi_if_lbl_msk, if_lbl_msk)
    DEBUG_PRINT(dbg_str)
    dbg_str = "%s, %s"%(pi_bd_lbl_msk, bd_lbl_msk)
    DEBUG_PRINT(dbg_str)
    dbg_str = "%s, %s"%(pi_rbacl_lbl_msk, rbacl_lbl_msk)
    DEBUG_PRINT(dbg_str)
    DEBUG_PRINT("\n")

    return(entry_invalid, mismatch)

#######################################################################################################################
def cc_validate_tah_single_racl(is_pacl, _ifObject, _aclName, _dir, _ifName):
        
    slot = _ifObject.slot
    inst = _ifObject.slice_num 	
    unit = _ifObject.unit

    if is_pacl:
        acl_type = 'PACL'
        racl_or_pacl_base = get_globals_info(_dir, "PACL")
    else:
        acl_type = 'RACL'
        racl_or_pacl_base = get_globals_info(_dir, "RACL")

    if 'in' in _dir:
        dirName = "input"
        tcamDir = "ingress"
    else:
        dirName = "output"
        tcamDir = "egress"
    
    acl_output = runVshCmd("show system internal access-list interface " + _ifName + " " + dirName + " entries detail")
    mm_swids = []

    tcam_tkns = acl_output.split("Tcam")

    for tt in tcam_tkns:

        if acl_type not in tt:
            continue

        pi_if_lbl = '0x0'
        pi_if_lbl_msk = '0x0'
        pi_bd_lbl = '0x0'
        pi_bd_lbl_msk = '0x0'
        pi_rbacl_lbl = '0x0'
        pi_rbacl_lbl_msk = '0x0'

        print "Checking %s ..."%_ifName
        tt_temp = tt.split("\n")
        for line in tt_temp:        
            if 'LBL' in line:
                lbl_line = line.strip()
                lbl_tkns = lbl_line.split()
                lbl_type = lbl_tkns[1]
                lbl_val = lbl_tkns[3]
                (pi_if_lbl, pi_if_lbl_msk, pi_bd_lbl, pi_bd_lbl_msk, pi_rbacl_lbl, pi_rbacl_lbl_msk) =\
                                                                pi_to_pd_label(slot, lbl_type, lbl_val)

        bank_tkns = tt.split("Bank")

        for bkt in bank_tkns:

            if acl_type not in bkt:
                continue

            cls_tkns = bkt.split("Class")
		
            for ii in range(0, len(cls_tkns)):
                prot = 'none'
                cls_tkn_lines = cls_tkns[ii].split("\n")
                prot_str = cls_tkn_lines[-1].strip()

                if 'IPv4' in prot_str:
                    prot = 'IPv4'
                elif 'IPv6' in prot_str:
                    prot = 'IPv6'
                elif 'MAC' in prot_str:
                    prot = 'MAC'

                if prot != 'none':
                    match_acl_name = re_acl_name.search(cls_tkns[ii+1])

                    if match_acl_name is None:
                        continue

                    if match_acl_name.group(1) == _aclName:

                        cls_tkn_lines = cls_tkns[ii+1].split("\n")
                        for line in cls_tkn_lines:
                            matches = re_idx.match(line.strip())

                            if matches is None:
                                continue

                            ace = line.strip()
                            ace_tokens = ace.split()
                            offset = matches.group(2)
                            sw_idx = int(racl_or_pacl_base) + int(offset, 16)
                                                                                         
                            #tcam entry labels check
                            (entry_invalid, lbl_mm) = acl_check_label(slot, unit, inst, tcamDir, sw_idx, pi_if_lbl, pi_if_lbl_msk,\
                                                                         pi_bd_lbl, pi_bd_lbl_msk, pi_rbacl_lbl, pi_rbacl_lbl_msk)
                                
                            if entry_invalid == True or lbl_mm == True:
                                mm_swids.append((inst, sw_idx)) 

    if len(mm_swids) == 0:
        return(True, None)
    else:
        return(False, mm_swids)
 
##########################################################################################################################################
def validate_tah_single_vlan_po_svi(is_svi, is_port_ch, slot, intf_id, intf_name, acl_dir, base, _aclName):

    no_acl = True	
    asic_type = nxos_utils.get_asic_type()
    if 'Unknown' in asic_type:
        print 'Unknown asic type'
        sys.exit(0)
	
    DAVOS_NUM_SLICES_PER_ASIC = 2
    LACROSSE_NUM_SLICES_PER_ASIC = 6

    if acl_dir == 'input':
        tcamDir = 'ingress'
    else:
        tcamDir = 'egress'

    mm_swids = [] #mismatch vlans/port channels and sw indices

    if is_svi:
        prt_str = "Checking SVI %s ..."%intf_name
        acl_type1 = 'RACL'
        acl_type2 = 'RACL' 
        acl_op = runVshCmd("show system internal access-list vlan " + intf_id + " " + acl_dir + " entries detail")
    elif is_port_ch:
        prt_str = "Checking %s ..."%intf_name
        acl_type1 = 'RACL'
        acl_type2 = 'PACL' 
        acl_op = runVshCmd("show system internal access-list interface " + intf_id + " " + acl_dir + " entries detail")
    else:
        prt_str = "Checking %s vlan on %s ..."%(intf_name, tcamDir)
        acl_type1 = 'VACL'
        acl_type2 = 'VACL'
        acl_op = runVshCmd("show system internal access-list vlan " + intf_id + " " + acl_dir + " entries detail")

    acl_op_tkns = acl_op.split("INSTANCE")

    if acl_op_tkns != ['']:
        print "%s"%prt_str
        del acl_op_tkns[0]

        for vtk in acl_op_tkns:
    
            vtk_lines = vtk.split("\n")                
            lin_inst = vtk_lines[0].strip()
            lin_inst = int(lin_inst, 0) 					
            if 'dav' in asic_type:
                unit = lin_inst/DAVOS_NUM_SLICES_PER_ASIC
                inst = lin_inst%DAVOS_NUM_SLICES_PER_ASIC
            else:
                unit = lin_inst/LACROSSE_NUM_SLICES_PER_ASIC
                inst = lin_inst%LACROSSE_NUM_SLICES_PER_ASIC
	
            vtk_tcam = vtk.split("Tcam")

            for vtcam in vtk_tcam:

                if acl_type1 not in vtcam and acl_type2 not in vtcam:
                    continue

                pi_if_lbl = '0x0'
                pi_if_lbl_msk = '0x0'
                pi_bd_lbl = '0x0'
                pi_bd_lbl_msk = '0x0'
                pi_rbacl_lbl = '0x0'
                pi_rbacl_lbl_msk = '0x0'

                no_acl = False
                vtcam_lines = vtcam.split("\n")
                for line in vtcam_lines:                    
                    if 'LBL' in line:
                        lbl_line = line.strip()
                        lbl_tkns = lbl_line.split()
                        lbl_type = lbl_tkns[1]
                        lbl_val = lbl_tkns[3]
                        (pi_if_lbl, pi_if_lbl_msk, pi_bd_lbl, pi_bd_lbl_msk, pi_rbacl_lbl, pi_rbacl_lbl_msk) =\
                                                                        pi_to_pd_label(slot, lbl_type, lbl_val)

                vtk_bank = vtcam.split("Bank")

                for vbank in vtk_bank:

                    if acl_type1 not in vbank and acl_type2 not in vbank:
                        continue

                    vtk_cls = vbank.split("Class")
                
                    for ii in range(0, len(vtk_cls)):
                        prot = 'none'
                        vtk_cls_lines = vtk_cls[ii].split("\n")
                        prot_str = vtk_cls_lines[-1].strip()

                        if 'IPv4' in prot_str:
                            prot = 'IPv4'
                        elif 'IPv6' in prot_str:
                            prot = 'IPv6'
                        elif 'MAC' in prot_str:
                            prot = 'MAC'

                        if prot != 'none':
                            if acl_type1 == 'VACL':

                                vtk_cls_lines = vtk_cls[ii+1].split("\n")
                                for line in vtk_cls_lines:
                                    matches = re_idx.match(line.strip())

                                    if matches is None:
                                        continue

                                    ace = line.strip()
                                    ace_tokens = ace.split()
                                    offset = matches.group(2)                        
                                    sw_idx = int(base) + int(offset, 16)

                                    #tcam entry labels check
                                    (entry_invalid, lbl_mm) = acl_check_label(slot, unit, inst, tcamDir, sw_idx, pi_if_lbl, pi_if_lbl_msk,\
                                                                                 pi_bd_lbl, pi_bd_lbl_msk, pi_rbacl_lbl, pi_rbacl_lbl_msk)

                                    if entry_invalid == True or lbl_mm == True:
                                        mm_swids.append((inst, sw_idx)) 
                            
                            else:
                                match_acl_name = re_acl_name.search(vtk_cls[ii+1])

                                if match_acl_name is None:
                                    continue

                                if match_acl_name.group(1) == _aclName:

                                    vtk_cls_lines = vtk_cls[ii+1].split("\n")
                                    for line in vtk_cls_lines:
                                        matches = re_idx.match(line.strip())

                                        if matches is None:
                                            continue

                                        ace = line.strip()
                                        ace_tokens = ace.split()
                                        offset = matches.group(2)                        
                                        sw_idx = int(base) + int(offset, 16)

                                        #tcam entry labels check
                                        (entry_invalid, lbl_mm) = acl_check_label(slot, unit, inst, tcamDir, sw_idx, pi_if_lbl, pi_if_lbl_msk,\
                                                                                     pi_bd_lbl, pi_bd_lbl_msk, pi_rbacl_lbl, pi_rbacl_lbl_msk)

                                        if entry_invalid == True or lbl_mm == True:
                                            mm_swids.append((inst, sw_idx)) 


    if len(mm_swids) == 0:
        return(no_acl, True, None)
    else:
        return(no_acl, False, mm_swids)

##################################################################################################################
def validate_tah_racl(_ifindexList = None, _ifNameList = None):    
    """
    testing
    """
    ok_eth = []
    nok_eth = []
    ok_svi = []
    nok_svi = []
    cc_type = 'CC_RACL'
	
    if _ifNameList is None:
        print "Module is not online or doesn't exist"
        return

    is_pacl = False

    print "Validates IPv4/IPv6 RACLs on up eth and SVI interfaces:\n"
    listIdx = -1
    for ifname in _ifNameList:
        listIdx += 1

        i = onxos.Nxos.Interface(ifname)
        l = i.get_sw_link_state()
        if l == 0:
            continue

        if i.swLayer == 2:
            continue

        #show running interface ethernet x/y"
        output = nxos_utils.runVshCmd("show running-config interface " + ifname)
        lines = output.split("\n")

        #exclude ports that are members of port-channel
        pc_member = 0
        for line in lines:
            line = line.strip()
            if "channel-group" in line:
               pc_member = 1
               break;

        if pc_member == 1:
            continue;

        for line in lines:
            line = line.strip()
            if ("access-group" in line or "traffic-filter" in line) and ("port" not in line):
                words = line.split(" ")
                aclName = words[2]
                dir = words[3]

                if dir == 'in':
                   entryDir = 'ingress'
                else:
                   entryDir = 'egress'
						
                (r, mismatch_entry_sw_ids) = cc_validate_tah_single_racl(is_pacl, i, _aclName = aclName, _dir = dir, _ifName = ifname)
                if r == True:
                   ok_eth.append((i, aclName, entryDir, None))
                else:
                   nok_eth.append((i, aclName, entryDir, mismatch_entry_sw_ids))

    #svi cc check
    is_svi = True			
    is_port_ch = False
    re_svi = re.compile("Vlan(\d+)")
    intf_status_op = nxos_utils.runVshCmd("show interface status up | i Vlan")
    for line_i in intf_status_op.splitlines():
        match_svi = re_svi.match(line_i)

        if match_svi:
            svi_intf = match_svi.group(1)
            svi_rcfg = nxos_utils.runVshCmd("show running-config interface Vlan%s"%svi_intf)

            for line_j in svi_rcfg.splitlines():
                line = line_j.strip()
                if ("access-group" in line or "traffic-filter" in line) and ("port" not in line):
                    words = line.split(" ")
                    aclName = words[2]
                    dir = words[3]

                    if dir == 'in':
                        dirName = 'input'
                        entryDir = 'ingress'
                    else:
                        dirName = 'output'
                        entryDir = 'egress'
            
                    base = get_globals_info(dir, "RACL")
                            
                    #supported on tor only, so slot = 1
                    (no_racl, r, mismatch_entry_sw_ids) = validate_tah_single_vlan_po_svi(is_svi, is_port_ch, 1, svi_intf, \
                                        "Vlan%s"%svi_intf, dirName, base, aclName)

                    if r == True:
                        ok_svi.append(("Vlan%s"%svi_intf, aclName, entryDir, None))
                    else:
                        nok_svi.append(("Vlan%s"%svi_intf, aclName, entryDir, mismatch_entry_sw_ids))
	    
    if (len(nok_eth) + len(nok_svi)) != 0:
       print "Consistency Check: FAILED"
       onxos.py_syslog(1, "CC_RACL_IPv4/IPv6: Consistency Check: FAILED")
    else:
       print "Consistency Check: PASSED"
       onxos.py_syslog(1, "CC_RACL_IPv4/IPv6: Consistency Check: PASSED")

    if (len(ok_eth) != 0) or (len(ok_svi) != 0):
        print ""
        print "Found consistencies for following Interfaces:"
        for (i, aclName, entryDir, mm_swids) in ok_eth:
            print "  ", i.longName, "(%s, %s)"%(aclName, entryDir)

        for (sviName, aclName, entryDir, mm_swids) in ok_svi:
            print "\t%s (%s, %s)"%(sviName, aclName, entryDir) 

    if (len(nok_eth) != 0) or (len(nok_svi) != 0):
        print ""
        print "Found inconsistencies for following interfaces and sw_idx:"
        onxos.py_syslog(1, "%s: Found inconsistencies for following interfaces and sw_idx:"%cc_type)
        for (i, aclName, entryDir, mm_swids) in nok_eth:
            print "  ", i.longName, "(%s, %s)"%(aclName, entryDir), "[inst, sw_idx] %s"%mm_swids
            onxos.py_syslog(1, "%s, %s, %s, [inst, sw_idx] %s"%(i.longName, aclName, entryDir, mm_swids))

        for (sviName, aclName, entryDir, mm_swids) in nok_svi:
            print "\t%s (%s, %s)"%(sviName, aclName, entryDir), "[inst, sw_idx] %s"%mm_swids
            onxos.py_syslog(1, "%s, %s, %s, [inst, sw_idx] %s"%(sviName, aclName, entryDir, mm_swids))
 
######################################################################################################################################    
def validate_tah_pacl(_ifindexList = None, _ifNameList = None):    
    """
    testing
    """
    ok = []
    nok = []
    cc_type = 'CC_PACL'

    if _ifNameList is None:
        print "Module is not online or doesn't exist"
        return

    is_pacl = True

    print "Validates IPv4/IPv6 PACLs on up interfaces:\n"
    listIdx = -1
    for ifname in _ifNameList:
        listIdx += 1
        if "." in ifname:
            nms = ifname.split(".")
            name = nms[0]
            sinumber = nms[1]
            continue
        else:
            name = ifname
            sinumber = ""

        i = onxos.Nxos.Interface(name)
        l = i.get_sw_link_state()
        if l == 0:
            continue

        if i.swLayer == 3:
            continue

        #show running interface ethernet x/y"
        output = nxos_utils.runVshCmd("show running-config interface " + ifname)
        lines = output.split("\n")

        #exclude ports that are members of port-channel
        pc_member = 0
        for line in lines:
            line = line.strip()
            if "channel-group" in line:
               pc_member = 1
               break;

        if pc_member == 1:
            continue;

        for line in lines:
            line = line.strip()
            if ("access-group" in line or "traffic-filter" in line) and ("port" in line):
                words = line.split(" ")
                aclName = words[3]
                if words[0] == 'mac':
                   dir = 'in'
                else:
                   dir = words[4]

                if dir == 'in':
                   entryDir = 'ingress'
                else:
                   entryDir = 'egress'
						
                (r, mismatch_entry_sw_ids) = cc_validate_tah_single_racl(is_pacl, i, _aclName = aclName, _dir = dir, _ifName = ifname)
                if r == True:
                   ok.append((i, sinumber, aclName, entryDir, None))
                else:
                   nok.append((i, sinumber, aclName, entryDir, mismatch_entry_sw_ids))

    if len(nok) != 0:
       print "Consistency Check: FAILED"
       onxos.py_syslog(1, "CC_PACL_IPv4/IPv6: Consistency Check: FAILED")
    else:
       print "Consistency Check: PASSED"
       onxos.py_syslog(1, "CC_PACL_IPv4/IPv6: Consistency Check: PASSED")

    if len(ok) != 0:
        print ""
        print "Found consistencies for following Interfaces:"
        for (i, sinumber, aclName, entryDir, mm_swids) in ok:
            if "" == sinumber:
                print "  ", i.longName, "(%s, %s)"%(aclName, entryDir)
            else:
                print "   %s.%s"%(i.longName, sinumber), "(%s, %s)"%(aclName, entryDir)

    if len(nok) != 0:
        print ""
        print "Found inconsistencies for following interfaces and sw_idx:"
        onxos.py_syslog(1, "%s: Found inconsistencies for following interfaces and sw_idx:"%cc_type)
        for (i, sinumber, aclName, entryDir, mm_swids) in nok:
            if "" == sinumber:
                print "  ", i.longName, "(%s, %s)"%(aclName, entryDir), "[inst, sw_idx] %s"%mm_swids
                onxos.py_syslog(1, "%s, %s, %s, [inst, sw_idx] %s"%(i.longName, aclName, entryDir, mm_swids))
            else:
                print "   %s.%s"%(i.longName, sinumber), "(%s, %s)"%(aclName, entryDir), "[inst, sw_idx] %s"%mm_swids
                onxos.py_syslog(1, "%s.%s, %s, %s, [inst, sw_idx] %s"%(i.longName, sinumber, aclName, entryDir, mm_swids))

##################################################################################################################
def validate_tah_racl_pc(_ifindexList = None, _ifNameList = None):
    """
    testing
    """
    ok = []
    nok = []
    cc_type = 'CC_RACL_PC'

    if _ifNameList is None:
        print "Module is not online or doesn't exist"
        return

    is_port_ch = True
    is_svi = False
	
    print "Validates RACLs on up port channel interfaces:\n"
    for ifname in _ifNameList:
        p = onxos.Nxos.Interface(ifname)
        l = p.get_sw_link_state()
        if l == 0:
            continue

        if p.swLayer == 2:
            continue
        
        output = nxos_utils.runVshCmd("show running-config interface " + ifname)
        lines = output.split("\n")

        for line in lines:
            line = line.strip()
            if ("access-group" in line or "traffic-filter" in line) and ("port" not in line):
                words = line.split(" ")
                aclName = words[2]
                dir = words[3]
	
                if 'in' in dir:
                    dirName = "input"
                    entryDir = "ingress"
                else:
                    dirName = "output"
                    entryDir = "egress"

                base = get_globals_info(dir, "RACL")

                (no_racl, r, mismatch_entry_sw_ids) = validate_tah_single_vlan_po_svi(is_svi, is_port_ch, p.slot, ifname, ifname, dirName, base, aclName)

                if no_racl == False:
                    if r == True:
                       ok.append((p, aclName, entryDir, None))
                    else:
                       nok.append((p, aclName, entryDir, mismatch_entry_sw_ids))

    if len(nok) != 0:
       print "Consistency Check: FAILED"
       onxos.py_syslog(1, "CC_RACL_PORT_CH_IPv4/IPv6: Consistency Check: FAILED")
    else:
       print "Consistency Check: PASSED"
       onxos.py_syslog(1, "CC_RACL_PORT_CH_IPv4/IPv6: Consistency Check: PASSED")

    if len(ok) != 0:
        print ""
        print "Found consistencies for following Interfaces:"
        for (i, aclName, dir, mm_swids) in ok:
            print "  ", i.longName, "(%s, %s)"%(aclName, dir)

    if len(nok) != 0:
        print ""
        print "Found inconsistencies for following interfaces and sw_idx:"
        onxos.py_syslog(1, "%s: Found inconsistencies for following interfaces and sw_idx:"%cc_type)
        for (i, aclName, dir, mm_swids) in nok:
            print "  ", i.longName, "(%s, %s)"%(aclName, dir), "[inst, sw_idx] %s"%mm_swids
            onxos.py_syslog(1, "%s, %s, %s, [inst, sw_idx] %s"%(i.longName, aclName, dir, mm_swids))

####################################################################################################################################
def validate_tah_pacl_pc(_ifindexList = None, _ifNameList = None):
    """
    testing
    """
    ok = []
    nok = []
    cc_type = 'CC_PACL_PC'

    if _ifNameList is None:
        print "Module is not online or doesn't exist"
        return

    is_port_ch = True
    is_svi = False

    print "Validates PACLs on up port channel interfaces:\n"
    for ifname in _ifNameList:
        if "." in ifname:
            nms = ifname.split(".")
            name = nms[0]
            sinumber = nms[1]
            continue
        else:
            name = ifname
            sinumber = ""

        p = onxos.Nxos.Interface(name)
        l = p.get_sw_link_state()
        if l == 0:
            continue

        if p.swLayer == 3:
            continue
        
        output = nxos_utils.runVshCmd("show running-config interface " + ifname)
        lines = output.split("\n")

        for line in lines:
            line = line.strip()
            if ("access-group" in line or "traffic-filter" in line) and ("port" in line):
                words = line.split(" ")
                aclName = words[3]
                if words[0] == 'mac':
                   dir = 'in'
                else:
                   dir = words[4]

                if 'in' in dir:
                    dirName = "input"
                    entryDir = "ingress"
                else:
                    dirName = "output"
                    entryDir = "egress"

                base = get_globals_info(dir, "PACL")

                (no_pacl, r, mismatch_entry_sw_ids) = validate_tah_single_vlan_po_svi(is_svi, is_port_ch, p.slot, ifname, ifname, dirName, base, aclName)

                if no_pacl == False:
                    if r == True:
                       ok.append((p, sinumber, aclName, entryDir, None))
                    else:
                       nok.append((p, sinumber, aclName, entryDir, mismatch_entry_sw_ids))

    if len(nok) != 0:
       print "Consistency Check: FAILED"
       onxos.py_syslog(1, "CC_PACL_PORT_CH_IPv4/IPv6: Consistency Check: FAILED")
    else:
       print "Consistency Check: PASSED"
       onxos.py_syslog(1, "CC_PACL_PORT_CH_IPv4/IPv6: Consistency Check: PASSED")

    if len(ok) != 0:
        print ""
        print "Found consistencies for following Interfaces:"
        for (i, sinumber, aclName, dir, mm_swids) in ok:
            if "" == sinumber:
                print "  ", i.longName, "(%s, %s)"%(aclName, dir)
            else:
                print "   %s.%s"%(i.longName, sinumber), "(%s, %s)"%(aclName, dir)

    if len(nok) != 0:
        print ""
        print "Found inconsistencies for following interfaces and sw_idx:"
        onxos.py_syslog(1, "%s: Found inconsistencies for following interfaces and sw_idx:"%cc_type)
        for (i, sinumber, aclName, dir, mm_swids) in nok:
            if "" == sinumber:
                print "  ", i.longName, "(%s, %s)"%(aclName, dir), "[inst, sw_idx] %s"%mm_swids
                onxos.py_syslog(1, "%s, %s, %s, [inst, sw_idx] %s"%(i.longName, aclName, dir, mm_swids))
            else:
                print "   %s.%s"%(i.longName, sinumber), "(%s, %s)"%(aclName, dir), "[inst, sw_idx] %s"%mm_swids
                onxos.py_syslog(1, "%s.%s, %s, %s, [inst, sw_idx] %s"%(i.longName, sinumber, aclName, dir, mm_swids))

##################################################################################################################
def validate_tah_vacl():
    '''
    Testing VACLs on active VLANs
    '''
    print "Testing VACLs on active VLANs ...\n"
  
    ok = []
    nok = []	
    is_port_ch = False
    is_svi = False
    cc_type = 'CC_VACL'

    #currently supported only on tor
    modNum = 1 

    ing_base = get_globals_info("in", "VACL")
    egr_base = get_globals_info("out", "VACL")

    mm_vlans = []   #vlans with vacl mismatch    

    vlans_w_plcy = []   #list of vlans with policy applied

    vlan_filter_op = nxos_utils.runVshCmd("show vlan filter")
    
    vl_tkns = vlan_filter_op.split("\n")
    for line in vl_tkns:
        if 'Configured' in line:
            vl_line = line.strip()
            vl_list = vl_line.split("Configured on VLANs:")[1] 
            vl_list = vl_list.strip()
            vlans = vl_list.split(',')
            for vl in vlans:
                if vl.isdigit():
                    vlans_w_plcy.append(int(vl))
                else:
                    vl_start = int(vl.split('-')[0])
                    vl_end = int(vl.split('-')[1])
                    vlans_w_plcy.extend(list(range(vl_start,vl_end+1)))  

    for vlan in vlans_w_plcy:
        vlan_id = str(vlan)
        vlan_name = "VLAN%d"%vlan

        (no_vacl, rv_ing, mm_ing_sw_ids) = validate_tah_single_vlan_po_svi(is_svi, is_port_ch, modNum, vlan_id, vlan_name, 'input', ing_base, "")
        (no_vacl, rv_egr, mm_egr_sw_ids) = validate_tah_single_vlan_po_svi(is_svi, is_port_ch, modNum, vlan_id, vlan_name, 'output', egr_base, "")

        if no_vacl == False:
            if rv_ing == True and rv_egr == True:
                ok.append(vlan_id)

            if rv_ing == False:
                nok.append((vlan_id, 'Ingress', mm_ing_sw_ids))
            if rv_egr == False:
                nok.append((vlan_id, 'Egress', mm_egr_sw_ids))

    if len(nok) != 0:
       print "Consistency Check: FAILED"
       onxos.py_syslog(1, "CC_VACL: Consistency Check: FAILED")
    else:
       print "Consistency Check: PASSED"
       onxos.py_syslog(1, "CC_VACL: Consistency Check: PASSED")

    if len(ok) != 0:
        print "\nFound consistencies for following VLANs: "
        for idx in range(0, len(ok)-1):
            print "%s,"%(ok[idx]),

        print "%s\n"%(ok[len(ok)-1])

    if len(nok) != 0:
        print "Found inconsistencies for following VLANs and sw_idx:\n"
        onxos.py_syslog(1, "%s: Found inconsistencies for following interfaces and sw_idx:"%cc_type)
        for (vlan, entryDir, mm_swids) in nok:
            print "VLAN %s\n"%vlan
            print "\t", mm_swids, " (%s)\n"%entryDir
            onxos.py_syslog(1, "VLAN %s, [inst, sw_idx] %s, %s"%(vlan, mm_swids, entryDir))
        
#######################################END OF ACL CCs FOR TAHOE################################################


