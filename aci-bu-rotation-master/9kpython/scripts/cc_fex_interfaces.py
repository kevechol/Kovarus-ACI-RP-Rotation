#################################################
#
#      File:   cc_fex_interfaces.py
#      Name:   Parag Deshpande
#
#       Description: Link state consistency checker
#  
#
#
# Copyright (c) 1985-2013, 2015 by cisco Systems, Inc.
# All rights reserved.
#
#################################################

from onxos import *
from libbcmshell import *
import nxos_utils
import time
from collections import namedtuple
cmd_pfx={}
cmd_pfx["vlan xlate"] = "search vlan_xlate "
cmd_pfx["source vp"] = "d SOURCE_VP "
cmd_pfx["egress port"] = "d egr_port "
cmd_pfx["egress dvp"] = "d egr_dvp_attribute "
cmd_pfx["enable filter bitmap"] = "d chg ing_en_efilter_bitmap"
cmd_pfx["vlan membership"] = "d vlan  "

def is_pvlan_port(_if):
    out = nxos_utils.runVshCmd("show running-config interface " + \
            _if.shortName)

    if "switchport mode private-vlan" in out:
        return True
    else:
        return False

def validate_nif_ports(_if,_unit, _slot):
    max_unit = _unit 
    bitmaps = []
    ret = []
    bitmap = 0

    for x in range(0,max_unit):
        output = runBcmCmd(_slot,x, cmd_pfx["enable filter bitmap"])
        obj = createHwTableObject(output)
        if len(obj.table) == 0:
            pass
            #return False

        for i in obj.table:
            bitmap = int(obj.table[i]["BITMAP"], 16)
            break

        bitmaps.append(bitmap)

    if _if is not None:
        p = _if
        for i in p.members:
            #if i.pc == True:
            #    continue
            port = i.hw_port
            if i.slot != _slot:
                continue
            output = runBcmCmd(i.slot, i.hwIf.get_unit(), cmd_pfx["egress port"] + str(port) + " 1")
            obj = createHwTableObject(output)
            if len(obj.table) == 0:
                return False
            for j in obj.table:
                if int(obj.table[j]['EN_EFILTER']) != 0:
                    return False
                break
            for j in obj.table:
                if int(obj.table[j]['EFP_FILTER_ENABLE']) == 0:
                    return False
                break

            index = i.hwIf.get_unit() 
                
            if (bitmaps[index] & i.hwIf.get_hw_mask_int()):
                return False



    return True


def validate_xlate(_vif, _port, _vp, _slot):
    output = runBcmCmd(_slot, 0, cmd_pfx["vlan xlate"] + "VIF:SRC_VIF=" + str(_vif) + " VIF:TGID=" + str(_port))
    obj = createHwTableObject(output)
    if len(obj.table) == 0:
        return False

    for i in obj.table:
        if int(obj.table[i]["VIF:SOURCE_VP"],16) != _vp or obj.table[i]["VIF:SVP_VALID"] != "1":
            return False

        return True

    return false


def validate_xlate_hif(_vif, _port, _vp, _slot, _intf,isPC):
    vlanSubs = new_uintArray(4096)
    (cnt, vlanSubs) = _intf.get_sw_vlan_membership(_intf.ifindex)
    for r in range(0,cnt):
        vlan_id = uintArray_getitem(vlanSubs, r)
	vlan = Nxos.Vlan(vlan_id)
	if vlan.vnseg == 0:
	    output = runBcmCmd(_slot, 0, cmd_pfx["vlan xlate"] + "VIF:SRC_VIF=" + str(_vif) + " VIF:TGID=" + str(_port)+ " VIF:VLAN=0" )
	    obj = createHwTableObject(output)
    	    leng = len (obj.table)
    	    if len(obj.table) == 0:
	        return False
	    for i in obj.table:
		if int(obj.table[i]["VIF:SOURCE_VP"],16) != _vp or obj.table[i]["VIF:SVP_VALID"] != "1":
	    	    return False
	
                return True
	    return False
        else:
           if (isPC):
	       swvp = py_pixm_lib_ifidx_vlan_to_vp (_intf.bundle_index,vlan_id)
	   else:
	       swvp = py_pixm_lib_ifidx_vlan_to_vp (_intf.ifindex,vlan_id)
	   output = runBcmCmd(_slot, 0, cmd_pfx["vlan xlate"] + "VIF:SRC_VIF=" + str(_vif) + " VIF:TGID=" + str(_port) + " VIF:VLAN=" +str(vlan_id))
	   obj = createHwTableObject(output)
	   if len(obj.table) == 0:
               return False
	   for i in obj.table:
	       if int(obj.table[i]["VIF:SOURCE_VP"],16) != swvp or obj.table[i]["VIF:SVP_VALID"] != "1":
		   return False

	       #return True
       	   
       	   #return False
	          


def validate_source_vp(_vp, _slot, _interface):
    output = runBcmCmd(_slot, 0, cmd_pfx["source vp"] + str(_vp) + " 1")
    obj = createHwTableObject(output)

    if len(obj.table) == 0:
        return False;

    for i in obj.table:
        if int(obj.table[i]["CML_FLAGS_NEW"],16) != 8 or \
        int(obj.table[i]["CML_FLAGS_MOVE"], 16) != 8:
            return False

    output = runBcmCmd(_slot, 0, cmd_pfx["egress dvp"] + str(_vp) + " 1")
    obj = createHwTableObject(output)

    if len(obj.table) == 0:
        return False

    for j in obj.table:
	if int(obj.table[j]['COMMON:EN_EFILTER']) != 0:
	    # For PVLAN, egress vp vlan membership checks will happen 
            if int(obj.table[j]['COMMON:EN_EFILTER']) == 2:
                return is_pvlan_port(_interface)
            return False

    return True

def validate_fex_interfaces(_mods, _ifNameList = None):                    
    try:
        if _ifNameList == None:
            print "Found no interfaces to validate."
            return

        _mods = list(set(_mods))
        for slot in _mods:
            ok = []                                                                      
            nok = [] 
            nokvlans = []
            nifs = []
            ifidxs = []
            hifpos = []
            hifvlans = set()
            print "Fex Interfaces Checks: Vlan Xlate, VP Creation and Learn Flags for Module ", slot
            for name in _ifNameList:                                                    
                if "." in name:
                    continue

                i = Nxos.Interface(name)                                  
                if i.fex == False:
                    continue

                vlans = new_uintArray(4096)
                (cnt, vlans) = i.get_sw_vlan_membership(i.ifindex)		
                for r in range(0, cnt):
                    vlan_id = uintArray_getitem(vlans, r)
                    vlan = Nxos.Vlan(vlan_id)
		    #vlan.validate_vlan_mcshow()
                    hifvlans.add(vlan_id)
                if i.bundle_index != 0:
                    if i.bundle_index not in hifpos:
                        hifpos.append(i.bundle_index)

                        pc = Nxos.Interface(_ifindex=i.bundle_index)
                        #vlan xlate entry is removed for down HIF PCs
                        #hence skip the vlan_xlate check
                        if (pc.vif > 0):
                            #r = validate_xlate(pc.vif, i.hw_port, pc.vp, slot)
                            r = validate_xlate_hif(pc.vif, i.hw_port, pc.vp,
                                    slot,i,True)
                            if r == False:
                                nok.append(pc)                                               
                                continue

                        #vif is present in xlate. now check the source_vp if it matches.
                        #We are still checking even though vif is 0. correcting this #####CSCuv08344
                            r = validate_source_vp(pc.vp, slot, pc )
                            if r == False:                                                    
                                nok.append(pc)                                               
                                continue

                        ok.append(pc)
                    continue
                else:

                    #chk xlate table for svif entry.
                    #similar to Hif PC,disable the check when the port is down
                    #### CSCuv08344
                    if (i.get_sw_link_state() == 1):
                        r = validate_xlate_hif(i.vif, i.hw_port, i.vp, slot,i,False)

                        if r == False:                                                    
                            nok.append(i)                                               
                            continue

                    #vif is present in xlate. now check the source_vp if it matches.
                        r = validate_source_vp(i.vp, slot, i)
                        if r == False:                                                    
                            nok.append(i)                                               
                            continue

                    ok.append(i)

                #validate the corresponding nif pc.
                tgid =  i.hw_port

                ifidx = 0
                (ret, ifidx) = py_im_get_if_name_and_if_index_from_mod_unit_port(i.dmod, i.hw_port)
                if ret == 0: 
                    #add nif pc to
                    if ifidx not in ifidxs:
                        ifidxs.append(ifidx)
                        i = Nxos.Interface(_ifindex = ifidx, _queryHw = True)
                        xx = Nxos.Module(slot)
                        r = validate_nif_ports(i,xx.units,slot)
                        if r == False:
                            nok.append(i)
                        else:
                            ok.append(i) 
   
           #For all vlans check VIRTUAL_PORT_EN
            while hifvlans:
                vlan = hifvlans.pop()
                vlan_str = runBcmCmd(slot, 0, cmd_pfx["vlan membership"] + str(vlan))
                obj = createHwTableObject(vlan_str)
                if obj.table.__len__() is 0:
                    continue
                virten = obj.table["VLAN.ipipe0[%d]"%vlan]['VIRTUAL_PORT_EN']
                if virten == '0':
	            vlanobj = Nxos.Vlan(vlan)
		    if vlanobj.vnseg == 0:
                        nokvlans.append(vlan)
	
            if (len(nok) == 0) and (len(nokvlans) == 0):
                print "Consistency Check: PASSED"
                py_syslog(1, "CC_FEX_INTERFACES: Consistency Check: PASSED")
            else:
                print "Consistency Check: FAILED"
                py_syslog(1, "CC_FEX_INTERFACES: Consistency Check: FAILED")
                if (len(nokvlans) != 0):
                    print "VIRTUAL_PORT_EN disabled for HIF Vlans: "
                    for vlan in nokvlans:
                        print vlan
                
            if len(ok) > 0:                                                              
                print "No inconsistencies found for:"
                for i in ok:                                                             
                    print "  ", i.longName                                              

            if len(nok) > 0:                                                                       
                print "Inconsistencies found for following interfaces:"                
                for i in nok:                                                             
                    print "  ", i.longName                                              
    except Exception, err:
        print "Consistency checker had a problem:", err
        py_syslog(1, "CC_FEX_INTERFACES: Consistency Check: ABORTED. Please retry!")

