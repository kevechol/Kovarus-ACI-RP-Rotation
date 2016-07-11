#################################################
#
#      File:   cc_vlan_memb.py
#      Name:   Parag Deshpande
#
#       Description: Vlan membership consistency checker
#
#
#
# Copyright (c) 1985-2013, 2015 by cisco Systems, Inc.
# All rights reserved.
#
#################################################


import signal
from onxos import *
from collections import namedtuple

signal.signal(signal.SIGINT, signal_handler_sigint)

from sets import Set
import nxos_utils
import time
from hw.hwobj import *
import copy

cmd_pfx = {}
cmd_pfx["vlan xlate"] = "search vlan_xlate "
cmd_pfx["source vp"] = "d SOURCE_VP "
cmd_pfx["egress port"] = "d egr_port "
cmd_pfx["egress dvp"] = "d egr_dvp_attribute "
cmd_pfx["enable filter bitmap"] = "d chg ing_en_efilter_bitmap"

def _is_pvlan_port_in_prim_stp(port, stp_str):
    if port in stp_str:
        return True
    else:
        return False

def _is_vlan_active(vlan):
    out = nxos_utils.runVshCmd("show vlan id " + str(vlan))
    if "active" in out:
        return True
    else:
        return False

def _is_private_vlan(vlan):
    out = nxos_utils.runVshCmd("show running-config vlan " + str(vlan))
    if "private-vlan" in out:
        return True
    else:
        return False

def is_pvlan_port_and_vlan(ifidx, vlan):
    # We have to use some input string for this API to hold the output
    intf_name = py_im_get_long_name_from_if_index(ifidx)
    out = nxos_utils.runVshCmd("show running-config interface " + \
            intf_name)

    if "switchport mode private-vlan" in out and _is_private_vlan(vlan):
        return True
    else:
        return False

def get_prom_port_vlan_mappings(pvlan_port, prim_vlan):
    m_vlans = []
    ret_vlans = []
    cmd = "terminal width 200 ; show run int " + pvlan_port
    out = nxos_utils.runVshCmd(cmd)
    lines = out.split("\n")
    for line in lines:
        if "mapping trunk" in line or "private-vlan mapping" in line or "association trunk" in line:
            m_vlans = re.findall(r'\d+', line)
            if int(m_vlans[0]) != prim_vlan:
                m_vlans = []
                continue
            range_val = re.findall(r'\d+-\d+', line)
            for r in range_val:
                t = re.findall(r'\d+', r)
                lo=t[0]
                hi=t[1]
                lo = int(lo) +1
                hi = int(hi)
                while lo < hi:
                    m_vlans.append(lo)
                    lo = lo+1
            break;
    for v in m_vlans:
        ret_vlans.append(int(v))
    return ret_vlans


def validate_vlan_membership(_vlanList = None, _vlanNames = None, _hwLeaks = True):
    try:
        do_validate_vlan_membership(_vlanList, _vlanNames, _hwLeaks)
    except Exception, err:
        print "Consistency checker had a problem:", err
        py_syslog(1, "CC_VLAN_MEMBERSHIP: Consistency Check: ABORTED. Please retry!")

def do_validate_vlan_membership(_vlanList = None, _vlanNames = None, _hwLeaks = True):
    """
    Validates vlan membership in the hardware. This can be done two ways.
    Validate Software state in hardware (_reverse = False)
    Validate Hardware state in software (_reverse = True)
    This ignores down ports or ports that doesnt have vlan operational in software.
    It checks for sw link state when ignoring down ports.
    """
    okList = []
    nokList = []
    nokListHw = []
    vlist = []
    asic_type = nxos_utils.get_asic_type()
    if asic_type is 'dav' or asic_type is 'lac':
        print "Checks: Port membership of Vlan in vifvlanmbr, rwepgstate and qsmt_ovtbl tables"
    else :
        print "Checks: Port membership of Vlan in vlan and egr_vlan table"

    print "Ports configured as \"switchport monitor\" will be skipped\n"

    for vlan in _vlanList:
        ok = []
        nok = []

        v = Nxos.Vlan(vlan)
        (ok, nok) = v.validate_vlan_membership()
        vlan_act = isVlanInActiveState(v.vlan_str)

        vlans = new_uintArray(4097)
        stp_dict = getShowSpanningTreeDict(vlan)

        if (len(stp_dict) == 0):
            # We're mutating this list, so we must 0
            for ifindex in copy.deepcopy(ok):
                try:
                    i = Nxos.Interface(_ifindex = ifindex, _queryHw = False)
                except TypeError:
                    print "Failed to create NXOS interface with ifidx: %s" % ifindex
                    continue

                #fex interface not supported.
                if i.fex == True:
                    continue

                # if monitor dest port, dont consider it for vlan consistency check
                if i.span_dest == 1:
                    continue

                # VLAN 1 is programmed in NIF ports for initial handshake
			    # Ignore for consistency check.
			    # When ports are enabled, (stp_dict != 0 ), STP is not enabled
                # for NIF ports and will ignore them for cc check 
                if i.nif == True and vlan == 1:
                    continue

                #get oper vlans and check if this vlan is present. if not then we have inconsistency.
                py_im_get_ifindex_oper_vlans_ordered(i.ifindex, vlans)

                if uintArray_getitem(vlans, vlan) == 1 or vlan_act == False:
                    ok.append(i.ifindex)
                elif i.get_sw_link_state() == 1 and i.get_layer() == 2 and vlan_act:
                    if not isNativeVlanIsNotInAllowedVlans(i.shortName):
                        nok.append(i.ifindex)
        else:
            # Run membership consistency only for FWD ports
            for if_shName in stp_dict[vlan]['Interface_info'].keys():

                i = Nxos.Interface(_shortName = if_shName, _queryHw = False)

                # Remove port from ok,nok list if port not in forwarding state
                if stp_dict[vlan]['Interface_info'][if_shName]['Status'] != 'FWD':
                    #print if_shName
                    if len(i.members) == 0:
                         for okIfidx in ok:
                             if okIfidx == i.ifindex:
                                 ok.remove(okIfidx)
                         for nokIfidx in nok:
                             if nokIfidx == i.ifindex:
                                 nok.remove(nokIfidx)
                    else:
                         for member in i.members:
                             for okIfidx in ok:
                                 if okIfidx == member.ifindex:
                                     ok.remove(okIfidx)
                             for nokIfidx in nok:
                                 if nokIfidx == member.ifindex:
                                     nok.remove(nokIfidx)
                         continue

                    #fex interface not supported.
                    if i.fex == True:
                        continue

                    #Po members are included in ok/nok list
                    if "Po" in i.shortName:
                        for x in i.members:
                            stp_dict[vlan]['Interface_info'][x.shortName]={}
                            stp_dict[vlan]['Interface_info'][x.shortName]['Status']='FWD'
                        continue

                    #get oper vlans and check if this vlan is present. if not then we have inconsistency.
                    py_im_get_ifindex_oper_vlans_ordered(i.ifindex, vlans)

                    if uintArray_getitem(vlans, vlan) == 1:
                        #print "%s is getting added to OK" % i.longName
                        ok.append(i.ifindex)
                    else:
                       #ignore down port.
                       if i.get_sw_link_state() == 1 and i.get_layer() == 2:
                           nok.append(i.ifindex)

                       nokListHw.append((v,nok))
        
        # Remove MCT ports for Vxlan vlans
        # For Vxlan on Tahoe boxes, MCT is removed from Vxlan vlan flood list to prevent 
        # sending the native copy, so skip MCT ports on Vxlan vlans for Tah platforms
        if((v.vnseg!= 0) and ((asic_type is 'lac') or (asic_type is 'dav'))):
            mct_ifidx = py_get_mct_ifindex()
            mct_if_name = py_im_get_long_name_from_if_index(mct_ifidx)
            try:
                mct_i = Nxos.Interface(mct_if_name)
            except TypeError:
                continue
            if "Po" in mct_i.shortName:
                for memb in mct_i.members:
                    if memb.ifindex in nok:
                        nok.remove(memb.ifindex)
                        ok.append(memb.ifindex)
            else:
                nok.remove(mct_i.ifindex)
                ok.append(mct_i.ifindex)
                
        # Remove PVLAN ports.
        pvlan_ports = []
        for ifidx in nok:
            if is_pvlan_port_and_vlan(ifidx, vlan):
                pvlan_ports.append(ifidx)
        for ifidx in ok:
            if ifidx in pvlan_ports:
                continue
            elif is_pvlan_port_and_vlan(ifidx, vlan):
                pvlan_ports.append(ifidx)
        for ifidx in pvlan_ports:
            if ifidx in nok:
                nok.remove(ifidx)
            if ifidx in ok:
                ok.remove(ifidx)
	    #v.validate_vlan_mcshow ()	

        if len(ok) > 0:
            okList.append((v,ok))

        if len(nok) > 0:
            nokList.append((v,nok))

    if len(nokList) > 0:
        print "Consistency Check: FAILED"
        py_syslog(1, "CC_VLAN_MEMBERSHIP: Consistency Check: FAILED")
    elif len(okList) > 0:
        print "Consistency Check: PASSED"
        py_syslog(1, "CC_VLAN_MEMBERSHIP: Consistency Check: PASSED")
    else:
        print "No members found for vlan:", vlan


    okdone = Set()
    nokdone = Set()
    for (v,okIfidxs) in okList:
        print " Vlan:%d, Hardware state consistent for:"%v.vlan
        for ifidx in sorted(okIfidxs):
            longName = py_im_get_long_name_from_if_index(ifidx)
            if longName is not '':
                if longName not in okdone:
                    print "  ", longName
                    okdone.add(longName)


    for (v,nokIfidxs) in nokList:
        print " Vlan:%d, Hardware state inconsistent for:"%v.vlan
        for ifidx in sorted(nokIfidxs):
            longName = py_im_get_long_name_from_if_index(ifidx)
            
            if longName is not '':
                if longName not in nokdone:
                     print "  ", longName
                     nokdone.add(longName)
    #except Exception, err:
    #print "Consistency checker had a problem:", err
    #py_syslog(1, "CC_VLAN_MEMBERSHIP: Consistency Check: ABORTED. Please retry!")


def is_prom_port(ifname):
    out = nxos_utils.runVshCmd("show running-config interface " + ifname)
    if "promiscuous" in out:
        return True
    else:
        return False
def validate_xlate_fex(_vif, _port, _vp, _slot):
    output = runBcmCmd(_slot, 0, cmd_pfx["vlan xlate"] + "VIF:SRC_VIF=" + str(_vif) + " VIF:TGID=" + str(_port))
    obj = createHwTableObject(output)
    if len(obj.table) == 0:
        return False
    for i in obj.table:
        if int(obj.table[i]["VIF:SOURCE_VP"],16) != _vp or obj.table[i]["VIF:SVP_VALID"] != "1":
            return False

        return True

    return False
 
def validate_nif_ports_fex(_if, _slot):
    output = runBcmCmd(_slot, 0, cmd_pfx["enable filter bitmap"])
    obj = createHwTableObject(output)
    ret = []
    if len(obj.table) == 0:
        return False

    for i in obj.table:
        bitmap = int(obj.table[i]["BITMAP"], 16)
        break

    if _if is not None:
        p = _if
        for i in p.members:
            #if i.pc == True:
            #    continue

            port = i.hw_port
            if i.slot != _slot:
                continue
            output = runBcmCmd(i.slot, 0, cmd_pfx["egress port"] + str(port) + " 1")
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

            if (bitmap & i.hwIf.get_hw_mask_int()):
                return False


    return True


  
def validate_source_vp_fex(_vp, _slot):
    if (_vp==None):
          return False;
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
        if int(obj.table[j]['COMMON:EN_EFILTER']) != 2:
            return False

    return True

def validate_pvlan_membership(_vlanList = None, _vlanNames = None, _hwLeaks = True):
    iso=0
    comm=0
    non_oper=0
    prom_ports = []
    iso_ports = []
    comm_ports = []

    prim_vlan = _vlanList[0]
    iso_vlan = []
    comm_vlan = []
    port_vlan_memb = {}

    l_p_vlan = 0
    l_s_vlan = 0

    out = nxos_utils.runVshCmd("show vlan private-vlan")
    lines = out.split("\n")

    # if vlan provided is not primary vlan then get primary vlan first
    for line in lines:
        vlans = re.findall(r'\d+ ', line)
        if len(vlans) != 2:
            continue
        if prim_vlan == int(vlans[0]):
            break;
        if prim_vlan == int(vlans[1]):
            prim_vlan = int(vlans[0])
            break;

    if not _is_vlan_active(prim_vlan):
        print "Primary vlan not active.."
        return

    stp_dict = getShowSpanningTreeDict(prim_vlan)
    if stp_dict is None or prim_vlan not in stp_dict.keys():
        print "No Spanning tree instance running on primary vlan..."
        return

    for line in lines:
        new_pair = 0
        vlans = re.findall(r'\d+ ', line)
        if len(vlans) == 0 and l_p_vlan == 0:
            continue
        if len(vlans) == 1:
            continue
        if len(vlans) != 0:
            l_p_vlan = int(vlans[0])
            l_s_vlan = int(vlans[1])
            new_pair = 1

        if (l_p_vlan != prim_vlan):
            continue

        if (new_pair == 1):
            if "isolated" in line:
                iso = 1
                comm = 0
                non_oper = 0
                iso_vlan.append(l_s_vlan)
            elif "community" in line:
                comm = 1
                iso = 0
                non_oper = 0
                comm_vlan.append(l_s_vlan)
            elif "non-operational" in line:
                non_oper = 1
                continue

        if (non_oper == 1):
            continue

        s = line.find('Eth')
        ps = line[s:]
        all_ports = ps.split(',')
        for port in all_ports:
            port = port.strip()
            if len(port) < 1:
                continue
            if is_prom_port(port):
                prom_ports.append(port)
            elif iso == 1:
                iso_ports.append(port)
            elif comm == 1:
                comm_ports.append(port)

            if port in port_vlan_memb.keys():
                vlan_exists = next((x for x in port_vlan_memb[port] \
                                    if x == l_p_vlan), None)
                if vlan_exists == None: #Add primary once
                    port_vlan_memb[port].append(l_p_vlan)
                port_vlan_memb[port].append(l_s_vlan)
            else:
                port_vlan_memb[port] = [l_p_vlan]
                port_vlan_memb[port].append(l_s_vlan)

    prom_ports=set(prom_ports)
    iso_ports=set(iso_ports)
    comm_ports=set(comm_ports)
    iso_vlan=set(iso_vlan)
    comm_vlan=set(comm_vlan)

    tmp = []
    for iv in iso_vlan:
        if _is_vlan_active(iv):
            tmp.append(iv)
    iso_vlan=tmp
    tmp=[]
    for cv in comm_vlan:
        if _is_vlan_active(cv):
            tmp.append(cv)
    comm_vlan=tmp
    tmp=[]

    mod = []
    mod_fex = []
    slots = []
    slots_1 = []
    slots_2 = []
    p_vlan=0
    iface=0
    iso_hw_vl_in = {}
    iso_hw_vl_out = {}
    comm_hw_vl_in = {}
    comm_hw_vl_out = {}
    iso_hw_vl_stg = {}
    iso_hw_vl_stg_fex = {}
    comm_hw_vl_stg = {}
    comm_hw_vl_stg_fex = {}

    prom_hw_ifs={}
    iso_hw_ifs = {}
    comm_hw_ifs = {}
    mvlans = []

    stp_str = nxos_utils.runVshCmd("show spanning-tree vlan " + str(prim_vlan))

    for port in prom_ports:
        if len(port) < 1:
            continue
        iface = Nxos.Interface(_shortName=port)
        if iface.get_sw_link_state() == 0:
            "\t Interface is down"
            continue
        if iface.fex == False and "Po" in port:
            continue
        if iface.fex == False:
            slots.append(iface.slot)
        else:
            slots_1.append(iface.slot)
        prom_hw_ifs[port] = iface

    for port in iso_ports:
        iface = Nxos.Interface(_shortName=port)
        if iface.get_sw_link_state() == 0:
            "\t Interface is down"
            continue
        if iface.fex == False and "Po" in port:
            continue
        if iface.fex == False:
            slots.append(iface.slot)
        else:
            slots_1.append(iface.slot)
        iso_hw_ifs[port] = iface

    for port in comm_ports:
        iface = Nxos.Interface(_shortName=port)
        if iface.get_sw_link_state() == 0:
            "\t Interface is down"
            continue
        if iface.fex == False and "Po" in port:
            continue
        if iface.fex == False:
            slots.append(iface.slot)
        else:
            slots_1.append(iface.slot)
        comm_hw_ifs[port] = iface

    print "\nPulling vlan membership information from HW.... "

    slots = set(slots)
    slots_1 = set(slots_1)
    for slot in slots:
        x = Nxos.Module(slot)
        mod.append(x)
    out = nxos_utils.runVshCmd("show fex detail | grep Active")
    for line in out.split():
        #if(not line.find('Eth')):
        if ("Eth" in line) :
            iface = Nxos.Interface(_shortName=line)
            slots_2.append(iface.slot)
    
    slots_2 = set(slots_2)
    for slot_fex in slots_2:
        x_fex=Nxos.Module(slot_fex)
        mod_fex.append(x_fex)
    p_vlan=Nxos.Vlan(prim_vlan)
    prim_hw_vl_in = p_vlan.get_hw_vlan_membership(_modList = mod, _egr = False)
    prim_hw_vl_out = p_vlan.get_hw_vlan_membership(_modList = mod, _egr = True) 
    prim_vlan_hw_stg = p_vlan.hwVlan.get_vlan_stp_state(_modList = mod)
    prim_vlan_hw_stg_fex = p_vlan.hwVlan.get_vlan_stp_state(_modList = mod_fex)
    for iv in iso_vlan:
        iv=int(iv)
        vlan=Nxos.Vlan(iv)
        iso_hw_vl_in[iv] = vlan.get_hw_vlan_membership(_modList = mod, _egr = False)
        iso_hw_vl_out[iv] = vlan.get_hw_vlan_membership(_modList = mod, _egr = True)
        iso_hw_vl_stg[iv] = vlan.hwVlan.get_vlan_stp_state(_modList = mod)
        iso_hw_vl_stg_fex[iv] = vlan.hwVlan.get_vlan_stp_state(_modList = mod_fex)
    for iv in comm_vlan:
        iv=int(iv)
        vlan=Nxos.Vlan(iv)
        comm_hw_vl_in[iv] = vlan.get_hw_vlan_membership(_modList = mod, _egr = False)
        comm_hw_vl_out[iv] = vlan.get_hw_vlan_membership(_modList = mod, _egr = True)
        comm_hw_vl_stg[iv] = vlan.hwVlan.get_vlan_stp_state(_modList = mod)
        comm_hw_vl_stg_fex[iv] = vlan.hwVlan.get_vlan_stp_state(_modList = mod_fex)

    print "\nPerforming Consistency check..."
    cc_fail=0
    valid_in = False
    valid_out = False
    for port in prom_ports:
        if len(port) < 1:
            continue
        print port +" (prom):- "
        if port in prom_hw_ifs.keys():
            iface = prom_hw_ifs[port]
        else:
            print "No HW object found. continuing.."
            continue
        if port.count("/")==2:
            #add here for fex 
            vp=iface.vp
            temp_port = port.split("/")

    	    out = nxos_utils.runVshCmd("show fex " + temp_port[0].split("h")[1] +" | grep Active")
            for line in out.split():
                #if(not line.find('Eth')):
                if ("Eth" in line) :
                	i = Nxos.Interface(_shortName=line)
                	slot=i.slot
            		unit = i.hwIf.get_unit()
            if _is_pvlan_port_in_prim_stp(port, stp_str):
                (hw_in, hw_out, hw_vp_in, hw_vp_out, ns_cbl_state) = prim_vlan_hw_stg_fex
                if (hw_vp_out[(slot,unit)]) in hw_vp_out.keys():
                       if (hw_vp_out[(slot,unit)][vp]) in hw_vp_out.keys():
                           valid_out = True
                else : 
                       valid_out = False 
                if (hw_vp_in[(slot,unit)]) in hw_vp_in.keys():
                       if (hw_vp_in[(slot,unit)][vp]) in hw_vp_in.keys():
                           valid_in = True
                else : 
                       valid_in = False 

                if valid_out and (not validate_source_vp_fex(vp,slot) )and (hw_vp_out[(slot,unit)][vp]) != "FWD":
                     print "\tFAILED - Primary vlan not allowed in OUT direction."
                     cc_fail=1
                elif valid_in and  (not validate_source_vp_fex(vp,slot) )and (hw_vp_in[(slot,unit)][vp]) != "FWD":
                     print "\tFAILED - Primary vlan not allowed in IN direction."
                     cc_fail=1
            else :
                print "\tPort not part of primary vlan. Skipping..."
            
            if (valid_in or valid_out) and (not validate_source_vp_fex(vp,slot) ):
                    print "\tFAILED - Primary vlan not allowed in OUT direction."
                    cc_fail=1
            for iv in  iso_vlan:
                iv = int(iv)
                vlan=Nxos.Vlan(iv)
                (hw_in, hw_out, hw_vp_in, hw_vp_out, ns_cbl_state) = iso_hw_vl_stg_fex[iv]
                if (hw_vp_out[(slot,unit)]) in hw_vp_out.keys():
                       if (hw_vp_out[(slot,unit)][vp]) in hw_vp_out.keys():
                           valid_out = True
                else : 
                       valid_out = False 
                if (hw_vp_in[(slot,unit)]) in hw_vp_in.keys():
                       if (hw_vp_in[(slot,unit)][vp]) in hw_vp_in.keys():
                           valid_in = True
                else : 
                       valid_in = False 
                if valid_out and (hw_vp_out[(slot,unit)][vp]) != "FWD":
                    print "\tFAILED - Primary vlan not allowed in OUT direction."
                    print "\tFAILED - STP state inconsistent in Primary vlan in OUT direction."
                    cc_fail=1
                elif valid_in and (hw_vp_in[(slot,unit)][vp]) != "FWD":
                    print "\tFAILED - STP state inconsistent in Primary vlan in IN direction."
                    cc_fail=1
            for iv in  comm_vlan:
                iv = int(iv)
                vlan=Nxos.Vlan(iv)
                (hw_in, hw_out, hw_vp_in, hw_vp_out, ns_cbl_state) = comm_hw_vl_stg_fex[iv]
                if (hw_vp_out[(slot,unit)]) in hw_vp_out.keys():
                       if (hw_vp_out[(slot,unit)][vp]) in hw_vp_out.keys():
                           valid_out = True
                else : 
                       valid_out = False 

                if valid_out and (hw_vp_out[(slot,unit)][vp]) != "FWD":
                    print "\tFAILED - STP state inconsistent in Community vlan " + str(iv) +  " in OUT direction."
                    cc_fail=1
            if(cc_fail == 0):        
                print "\tPASSED - Primary vlan allowed in both directions."
                print "\tPASSED - All isolated vlans allowed only in OUT direction"
                print "\tPASSED - All community vlans allowed only in OUT direction"
        else:
            mvlans = set(port_vlan_memb[port])
            if _is_pvlan_port_in_prim_stp(port, stp_str):
                slot=iface.slot
                unit = iface.hwIf.get_unit()
                (tb, ts, ub, us, vps, evps) = prim_hw_vl_in[(slot, unit)]
                (tb2, ts2, ub2, us2, vps2, evps2) = prim_hw_vl_out[(slot, unit)]
                (hw_in, hw_out, hw_vp_in, hw_vp_out, ns_cbl_state) = prim_vlan_hw_stg
                if (iface.hwIf.get_hw_mask_int() & int(tb,16)) == 0:
                    cc_fail=1
                    print "\tFAILED - Primary vlan not allowed in IN direction."
                if (iface.hwIf.get_hw_mask_int() & int(tb2,16)) == 0:
                    cc_fail=1
                    print "\tFAILED - Primary vlan not allowed in OUT direction."
                if (iface.is_access_port() and ((iface.hwIf.get_hw_mask_int() & long(ub2,16)) == 0)):
                    cc_fail = 1
                    print "\tFAILED - Primary vlan " + str(iv) + " not in UT BMP in OUT direction"
                if (hw_in[(slot,unit)][iface.hwIf.get_hw_port()]) != stp_dict[prim_vlan]['Interface_info'][port]['Status']:
                    cc_fail=1
                    print "\tFAILED - STP state inconsistent in Primary vlan in IN direction."
                if (hw_out[(slot,unit)][iface.hwIf.get_hw_port()]) != stp_dict[prim_vlan]['Interface_info'][port]['Status']:
                    cc_fail=1
                    print "\tFAILED - STP state inconsistent in Primary vlan in OUT direction."
                if cc_fail == 0:
                    print "\tPASSED - Primary vlan allowed in both directions."
                cc_fail=0
            else:
                print "\tPort not part of primary vlan. Skipping..."
            for iv in  iso_vlan:
                iv = int(iv)
                if iv not in mvlans:
                    continue
                (tb, ts, ub, us, vps, evps) = iso_hw_vl_in[iv][(slot, unit)]
                (tb2, ts2, ub2, us2, vps2, evps2)= iso_hw_vl_out[iv][(slot, unit)]
                (hw_in, hw_out, hw_vp_in, hw_vp_out, ns_cbl_state) = iso_hw_vl_stg[iv]
                if (iface.hwIf.get_hw_mask_int() & long(tb,16)):
                    cc_fail =1
                    print "\tFAILED - Isolated vlan: " + str(iv) +" allowed in IN direction"
                if (iface.hwIf.get_hw_mask_int() & long(tb2,16)) == 0:
                    cc_fail = 1
                    print "\tFAILED - Isolate vlan " + str(iv) +  " not allowed in OUT direction."
                if (iface.is_access_port() and ((iface.hwIf.get_hw_mask_int() & long(ub2,16)) == 0)):
                    cc_fail = 1
                    print "\tFAILED - Isolated vlan " + str(iv) + " not in UT BMP in OUT direction"
                if (hw_out[(slot,unit)][iface.hwIf.get_hw_port()]) != stp_dict[prim_vlan]['Interface_info'][port]['Status']:
                    cc_fail=1
                    print "\tFAILED - STP state inconsistent in Isolate vlan " + str(iv) +  " in OUT direction."
            if cc_fail == 0:
                print "\tPASSED - All isolated vlans allowed only in OUT direction"
            for iv in  comm_vlan:
                iv = int(iv)
                if iv not in mvlans:
                    continue
                (tb, ts, ub, us, vps, evps) = comm_hw_vl_in[iv][(slot, unit)]
                (tb2, ts2, ub2, us2, vps2, evps2)= comm_hw_vl_out[iv][(slot, unit)]
                (hw_in, hw_out, hw_vp_in, hw_vp_out, ns_cbl_state) = comm_hw_vl_stg[iv]
                if (iface.hwIf.get_hw_mask_int() & int(tb,16)):
                    cc_fail =1
                    print "\tFAILED -  Community vlan " + str(iv) +  " allowed in IN direction."
                if (iface.hwIf.get_hw_mask_int() & int(tb2,16)) == 0:
                    cc_fail = 1
                    print "\tFAILED -  Community vlan " + str(iv) +  " not allowed in OUT direction."
                if (iface.is_access_port() and ((iface.hwIf.get_hw_mask_int() & long(ub2,16)) == 0)):
                    cc_fail = 1
                    print "\tFAILED - Community vlan " + str(iv) + " not in UT BMP in OUT direction"
                if (hw_out[(slot,unit)][iface.hwIf.get_hw_port()]) != stp_dict[prim_vlan]['Interface_info'][port]['Status']:
                    cc_fail=1
                    print "\tFAILED - STP state inconsistent in Community vlan " + str(iv) +  " in OUT direction."
            if cc_fail == 0:
                print "\tPASSED - All community vlans allowed only in OUT direction"


    cc_fail=0
    mvlans=[]
    valid_out = False 
    valid_in = False 
    for port in iso_ports:
        print port + "(iso):"
        if port in iso_hw_ifs.keys():
            iface = iso_hw_ifs[port]
        else:
            print "No HW object found. continuing.."
            continue
        if port.count("/")==2 and iface.vp !=0: # add vp in check
            #add here for fex 

            vp=iface.vp
            temp_port = port.split("/")
            slots = []
            units = []
    	    out = nxos_utils.runVshCmd("show fex " + temp_port[0].split("h")[1] +" | grep Active")
            for line in out.split():
               # if(not line.find('Eth')): # replace it with has
                if ("Eth" in line) :
                	i = Nxos.Interface(_shortName=line)
                	slots.append(i.slot) # array of slots
            		units.append(i.hwIf.get_unit())
            slots = set(slots)
            units = set (units)
            # for of (slot, unit)
            for slot in slots:
              for unit in units:
                if _is_pvlan_port_in_prim_stp(port, stp_str):
                    (hw_in, hw_out, hw_vp_in, hw_vp_out, ns_cbl_state) = prim_vlan_hw_stg_fex
                    valid_out = False # --- reset valid_out and valid_in for each iteration 
                    cc_fail=0
                    valid_in = False # --- reset valid_out and valid_in for each iteration 
                    if (hw_vp_out[(slot,unit)]) in hw_vp_out.keys():
                        if (hw_vp_out[(slot,unit)][vp]) in hw_vp_out[(slot,unit)].keys():
                            valid_out = True
                    else : 
                        valid_out = False 
                    if (hw_vp_in[(slot,unit)]) in hw_vp_in.keys():
                        if (hw_vp_in[(slot,unit)][vp]) in hw_vp_in[(slot,unit)].keys():
                            valid_in = True
                    else : 
                        valid_in = False 
                    if (valid_out):
                        print "\tFAILED vp out key missing for Slot, Unit"
                        cc_fail=1
                    elif (valid_in):
                        print "\tFAILED vp in key missing for slot , unit"
                        cc_fail=1
                    elif (valid_in and not validate_source_vp_fex(vp, slot)):
                        print "\tFAILED COMMON_EN_FILTER is not set for vp"
                        cc_fail=1
                    elif (hw_vp_out[(slot,unit)][vp] != "FWD"):
                        print "\tFAILED Primary vlan not allowed in OUT direction"
                        cc_fail=1
                    elif (hw_vp_in[(slot,unit)] and hw_vp_in[(slot,unit)][vp] == "FWD"):
                        print "\tFAILED Primary vlan allowed in IN direction"
                        cc_fail=1

                else :
                    print "\tPort not part of primary vlan. Skipping..."
            
                if (valid_out or valid_in) and (not validate_source_vp_fex(vp,slot) ):
                        cc_fail=1
                for iv in  iso_vlan:
                    iv = int(iv)
                    vlan=Nxos.Vlan(iv)
                    (hw_in, hw_out, hw_vp_in, hw_vp_out, ns_cbl_state) = iso_hw_vl_stg_fex[iv]
                    valid_out = False
                    valid_in = False 
                    if (hw_vp_out[(slot,unit)]) in hw_vp_out.keys():
                        if (hw_vp_out[(slot,unit)][vp]) in hw_vp_out[(slot,unit)].keys():
                            valid_out = True
                    else : 
                        valid_out = False 
                    if (hw_vp_in[(slot,unit)]) in hw_vp_in.keys():
                        if (hw_vp_in[(slot,unit)][vp]) in hw_vp_in[(slot,unit)].keys():
                            valid_out = True
                    else : 
                        valid_out = False 
                    if valid_in and (hw_vp_in[(slot,unit)][iface.vp]) != "FWD":
                        print "\tFAILED - STP state inconsistent in Primary vlan in IN direction."
                        cc_fail=1
                    elif valid_out and (hw_vp_out[(slot,unit)][iface.vp]) == "FWD":
                        print "\tFAILED - STP state inconsistent in Primary vlan in out direction."
                        cc_fail=1
                        # check if present in out directio


                for iv in  comm_vlan:
                    iv = int(iv)
                    vlan=Nxos.Vlan(iv)
                    (hw_in, hw_out, hw_vp_in, hw_vp_out, ns_cbl_state) = comm_hw_vl_stg_fex[iv]
                    valid_out = False 
                    valid_in = False 
                    if (hw_vp_out[(slot,unit)]) in hw_vp_out.keys():
                        if (hw_vp_out[(slot,unit)][vp]) in hw_vp_out[(slot,unit)].keys():
                            valid_out = True
                    else : 
                        valid_out = False 
                    if (hw_vp_in[(slot,unit)]) in hw_vp_in.keys():
                        if (hw_vp_in[(slot,unit)][vp]) in hw_vp_in[(slot,unit)].keys():
                            valid_out = True
                    else : 
                        valid_out = False 
                    if valid_out and (hw_vp_out[(slot,unit)][iface.vp]) == "FWD":
                        print "\tFAILED - STP state inconsistent in Community vlan " + str(iv) +  " in OUT direction."
                        cc_fail=1
                    # in direction check == fwd 
                    elif valid_in and (hw_vp_in[(slot,unit)][iface.vp]) == "FWD":
                        print "\tFAILED - STP state inconsistent in Community vlan " + str(iv) +  " in IN direction."
                        cc_fail=1

            if(cc_fail==0):
                print "\tPASSED - Primary vlan allowed in only in OUT direction "
                print "\tPASSED - All CFG isolated vlans allowed only in IN direction"
                print "\tPASSED - None of the community vlans allowed only in any direction"
        else:
            mvlans = set(port_vlan_memb[port])
            if _is_pvlan_port_in_prim_stp(port, stp_str) and iface.fex==False:
                slot=iface.slot
                unit = iface.hwIf.get_unit()
                (tb, ts, ub, us, vps, evps) = prim_hw_vl_in[(slot, unit)]
                (tb2, ts2, ub2, us2, vps2, evps2) = prim_hw_vl_out[(slot, unit)]
                (hw_in, hw_out, hw_vp_in, hw_vp_out, ns_cbl_state) = prim_vlan_hw_stg
                if (iface.hwIf.get_hw_mask_int() & int(tb,16)):
                    cc_fail=1
                    print "\tFAILED - Primary vlan allowed in IN direction"
                if (iface.hwIf.get_hw_mask_int() & int(tb2,16)) == 0:
                    cc_fail=1
                    print "\tFAILED - Primary vlan not allowed in OUT direction."
                if (iface.is_access_port() and ((iface.hwIf.get_hw_mask_int() & long(ub2,16)) == 0)):
                    cc_fail = 1
                    print "\tFAILED - Primary vlan " + str(iv) + " not in UT BMP in OUT direction"
                if (hw_out[(slot,unit)][iface.hwIf.get_hw_port()]) != stp_dict[prim_vlan]['Interface_info'][port]['Status']:
                    cc_fail=1
                    print "\tFAILED - STP state inconsistent in Primary vlan in OUT direction."
                if cc_fail == 0:
                    print "\tPASSED - Primary vlan allowed only in OUT direction"
                cc_fail=0
            else:
                print "\tPort not part of primary vlan. Skipping..."
            for iv in  iso_vlan:
                iv = int(iv)
                if iv not in mvlans:
                    continue
                (tb, ts, ub, us, vps, evps) = iso_hw_vl_in[iv][(slot, unit)]
                (tb2, ts2, ub2, us2, vps2, evps2)= iso_hw_vl_out[iv][(slot, unit)]
                (hw_in, hw_out, hw_vp_in, hw_vp_out, ns_cbl_state) = iso_hw_vl_stg[iv]

                vlan_mbr = next((x for x in port_vlan_memb[port] if int(x) == iv),\
                             None)

                if vlan_mbr == None:
                    if (iface.hwIf.get_hw_mask_int() & int(tb, 16)):
                        cc_fail = 1
                        print "\tFAILED - Non-Config Iso vlan " + str(iv) + \
                              " Allowed in IN direction"
                    if (iface.hwIf.get_hw_mask_int() & int(tb2,16)):
                        cc_fail = 1
                        print "\tFAILED - Non-config Iso vlan " + str(iv) + \
                              " Allowed in OUT direction"
                    if (hw_in[(slot,unit)][iface.hwIf.get_hw_port()]) == "FWD":
                        cc_fail = 1
                        print "\tFAILED - Non-config Iso vlan " + str(iv) + \
                              " Forwarding in IN direction."
                    if (hw_out[(slot,unit)][iface.hwIf.get_hw_port()]) == "FWD":
                        cc_fail = 1
                        print "\tFAILED - Non-config Iso vlan " + str(iv) + \
                              " Forwarding in OUT direction."
                else:
                    if (iface.hwIf.get_hw_mask_int() & int(tb,16)) == 0:
                        cc_fail = 1
                        print "\tFAILED - Iso vlan " + str(iv) + \
                            " not allowed in IN direction"
                    if (iface.hwIf.get_hw_mask_int() & int(tb2,16)):
                        cc_fail = 1
                        print "\tFAILED - Iso vlan " + str(iv) + \
                              " allowed in OUT direction"

                    if (iface.is_access_port() and \
                            (iface.hwIf.get_hw_mask_int() & long(ub2,16))):
                        cc_fail = 1
                        print "\tFAILED - Isolated vlan " + str(iv) + \
                               " allowed in UT BMP in OUT direction"
                    if (hw_in[(slot,unit)][iface.hwIf.get_hw_port()]) != "FWD":
                        cc_fail=1
                        print "\tFAILED - Not FWD in Isolate vlan " + str(iv) + \
                              " in IN direction."
            if cc_fail == 0:
                print "\tPASSED - All CFG isolated vlans allowed only in IN direction"
            for iv in  comm_vlan:
                iv = int(iv)
                if iv not in mvlans:
                    continue
                (tb, ts, ub, us, vps, evps) = comm_hw_vl_in[iv][(slot, unit)]
                (tb2, ts2, ub2, us2, vps2, evps2)= comm_hw_vl_out[iv][(slot, unit)]
                if (iface.hwIf.get_hw_mask_int() & int(tb,16)):
                    cc_fail =1
                    print "\tFAILED - Community vlan " + str(iv) +" allowed in IN direction"
                if (iface.hwIf.get_hw_mask_int() & int(tb2,16)):
                    cc_fail = 1
                    print "\tFAILED - Community vlan " + str(iv) +" allowed in OUT direction"
            if cc_fail == 0:
                print "\tPASSED - None of the community vlans allowed in any direction"

    cc_fail=0
    mvlans=[]
    valid_out = False
    valid_in = False
    for port in comm_ports:
        print port + "(comm):"
        if port in comm_hw_ifs.keys():
            iface = comm_hw_ifs[port]
        else:
            print "No HW object found. continuing.."
            continue
        if port.count("/")==2 and iface.vp != 0:
            #add here for fex 

            vp=iface.vp
            temp_port = port.split("/")
            slots = []
            units = []
    	    out = nxos_utils.runVshCmd("show fex " + temp_port[0].split("h")[1] +" | grep Active")
            for line in out.split():
                #if(not line.find('Eth')):
                if ("Eth" in line) :
                	i = Nxos.Interface(_shortName=line)
                	slots.append(i.slot) # array of slots
            		units.append(i.hwIf.get_unit())
            slots = set(slots)
            units = set (units)
            # for of (slot, unit)
            for slot in slots :
              for unit in units :
                if _is_pvlan_port_in_prim_stp(port, stp_str):
                    (hw_in, hw_out, hw_vp_in, hw_vp_out, ns_cbl_state) = prim_vlan_hw_stg_fex
                    valid_out = False # --- reset valid_out and valid_in for each iteration 
                    valid_in = False # --- reset valid_out and valid_in for each iteration 
                    cc_fail=0
                    if (hw_vp_out[(slot,unit)]) in hw_vp_out.keys():
                        if (hw_vp_out[(slot,unit)][vp]) in hw_vp_out[(slot,unit)].keys():
                                valid_out = True
                    else : 
                        valid_out = False 
                    if (hw_vp_in[(slot,unit)]) in hw_vp_in.keys():
                        if (hw_vp_in[(slot,unit)][vp]) in hw_vp_in[(slot,unit)].keys():
                            valid_in = True
                    else : 
                        valid_in = False 
                    if (valid_out):
                        print "\tFAILED vp out key missing for Slot, Unit"
                        cc_fail=1
                    elif (valid_in):
                        print "\tFAILED vp in key missing for slot , unit "
                        cc_fail=1
                    elif (valid_in and not validate_source_vp_fex(vp, slot)):
                        print "\tFAILED COMMON_EN_FILTER is not set for vp"
                        cc_fail=1
                    elif (hw_vp_out[(slot,unit)][vp] != "FWD"):
                        print "\tFAILED Primary vlan not allowed in OUT direction"
                        cc_fail=1
                    elif (hw_vp_in[(slot,unit)] and hw_vp_in[(slot,unit)][vp] == "FWD"):
                        print "\tFAILED Primary vlan allowed in IN direction"
                        cc_fail=1
                else :
                    print "\tPort not part of primary vlan. Skipping..."
            
                if (valid_out or valid_in) and  (not validate_source_vp_fex(vp,slot) ):
                        cc_fail = 1
                for iv in  iso_vlan:
                    iv = int(iv)
                    vlan=Nxos.Vlan(iv)
                    (hw_in, hw_out, hw_vp_in, hw_vp_out, ns_cbl_state) = iso_hw_vl_stg_fex[iv]
                    valid_out = False 
                    valid_in = False 
                    if (hw_vp_out[(slot,unit)]) in hw_vp_out.keys():
                        if (hw_vp_out[(slot,unit)][vp]) in hw_vp_out[(slot,unit)].keys():
                            valid_out = True
                    else : 
                        valid_out = False 
                    if (hw_vp_in[(slot,unit)]) in hw_vp_in.keys():
                        if (hw_vp_in[(slot,unit)][vp]) in hw_vp_in[(slot,unit)].keys():
                            valid_in = True
                    else : 
                        valid_in = False 
                    if (valid_out)and (hw_vp_out[(slot,unit)][vp]) == "FWD":
                        print "\tFAILED - STP state inconsistent in Primary vlan in OUT direction."
                        cc_fail = 1
                    elif (valid_in) and (hw_vp_in[(slot,unit)][vp]) == "FWD":
                        print "\tFAILED - STP state inconsistent in Primary vlan in IN direction."
                        cc_fail = 1
                for iv in  comm_vlan:
                    iv = int(iv)
                    vlan=Nxos.Vlan(iv)
                    (hw_in, hw_out, hw_vp_in, hw_vp_out, ns_cbl_state) = comm_hw_vl_stg_fex[iv]
                    valid_out = False 
                    valid_in = False 
                    if (hw_vp_out[(slot,unit)]) in hw_vp_out.keys():
                        if (hw_vp_out[(slot,unit)][vp]) in hw_vp_out[(slot,unit)].keys():
                            valid_out = True
                    else : 
                        valid_out = False 
                    if (hw_vp_in[(slot,unit)]) in hw_vp_in.keys():
                        if (hw_vp_in[(slot,unit)][vp]) in hw_vp_in[(slot,unit)].keys():
                            valid_in = True
                    else : 
                        valid_in = False 
                    if (valid_out )and (hw_vp_out[(slot,unit)][vp]) != "FWD":
                        print "\tFAILED - STP state inconsistent in Community vlan " + str(iv) +  " in OUT direction."
                        cc_fail = 1
                    elif (valid_out )and (hw_vp_in[(slot,unit)][vp]) != "FWD":
                        print "\tFAILED - STP state inconsistent in Community vlan " + str(iv) +  " in IN direction."
                        cc_fail = 1
                    # check for in direction
            if(cc_fail ==0):
                print "\tPASSED - Primary vlan allowed only in OUT direction"
                print "\tPASSED - None of the isolated vlans allowed only in any direction" 
                print "\tPASSED - All CFG community vlans allowed in both direction"
        else:
            mvlans = set(port_vlan_memb[port])
            if _is_pvlan_port_in_prim_stp(port, stp_str) and iface.fex == False:
                slot=iface.slot
                unit = iface.hwIf.get_unit()
                (tb, ts, ub, us, vps, evps) = prim_hw_vl_in[(slot, unit)]
                (tb2, ts2, ub2, us2, vps2, evps2) = prim_hw_vl_out[(slot, unit)]
                (hw_in, hw_out, hw_vp_in, hw_vp_out, ns_cbl_state) = prim_vlan_hw_stg
                if (iface.hwIf.get_hw_mask_int() & int(tb,16)):
                    cc_fail=1
                    print "\tFAILED - Primary vlan allowed in IN direction"
                if (iface.hwIf.get_hw_mask_int() & int(tb2,16)) == 0:
                    cc_fail=1
                    print "\tFAILED - Primary vlan not allowed in OUT direction"
                if (iface.is_access_port() and ((iface.hwIf.get_hw_mask_int() & long(ub2,16))  == 0)):
                    cc_fail = 1
                    print "\tFAILED - Primary vlan " + str(iv) + " not in UT BMP in OUT direction"
                if (hw_out[(slot,unit)][iface.hwIf.get_hw_port()]) != stp_dict[prim_vlan]['Interface_info'][port]['Status']:
                    cc_fail=1
                    print "\tFAILED - STP state inconsistent in Primary vlan in OUT direction."
                if cc_fail == 0:
                    print "\tPASSED - Primary vlan allowed only in OUT direction."
                cc_fail=0
            else:
                print "\tPort not part of primary vlan. Skipping..."
            for iv in  iso_vlan:
                iv = int(iv)
                if iv not in mvlans:
                    continue
                (tb, ts, ub, us, vps, evps) = iso_hw_vl_in[iv][(slot, unit)]
                (tb2, ts2, ub2, us2, vps2, evps2)= iso_hw_vl_out[iv][(slot, unit)]
                if (iface.hwIf.get_hw_mask_int() & int(tb,16)):
                    cc_fail =1
                    print "\tFAILED - Isolated vlan " + str(iv) + " allowed in IN direction."
                if (iface.hwIf.get_hw_mask_int() & int(tb2,16)):
                    cc_fail = 1
                    print "\tFAILED - Isolated vlan " + str(iv) + " allowed in OUT direction."
                if (iface.hwIf.get_hw_mask_int() & long(ub2,16)):
                    cc_fail = 1
                    print "\tFAILED - Isolated vlan " + str(iv) + " UT BMP allowed in OUT direction"
            if cc_fail == 0:
                print "\tPASSED - None of the isolated vlans allowed in any direction"
            for iv in  comm_vlan:
                iv = int(iv)
                if iv not in mvlans:
                    continue
                (tb, ts, ub, us, vps, evps) = comm_hw_vl_in[iv][(slot, unit)]
                (tb2, ts2, ub2, us2, vps2, evps2)= comm_hw_vl_out[iv][(slot, unit)]
                (hw_in, hw_out, hw_vp_in, hw_vp_out, ns_cbl_state) = comm_hw_vl_stg[iv]
                vlan_mbr = next((x for x in port_vlan_memb[port] if x == iv), None)
                if (iface.hwIf.get_hw_mask_int() & int(tb,16)) == 0 and vlan_mbr != None:
                    cc_fail =1
                    print "\tFAILED - Community vlan " + str(iv) + "not allowed in IN direction"

                if (iface.hwIf.get_hw_mask_int() & int(tb2,16)) == 0 and vlan_mbr != None:
                    cc_fail = 1
                    print "\tFAILED - Community vlan " + str(iv) + "not allowed in OUT direction"

                if (iface.is_access_port() and ((iface.hwIf.get_hw_mask_int() & long(ub2,16))  == 0)):
                    cc_fail = 1
                    print "\tFAILED - Community vlan " + str(iv) + " not in UT BMP in OUT direction"

                if (hw_in[(slot,unit)][iface.hwIf.get_hw_port()]) != stp_dict[prim_vlan]['Interface_info'][port]['Status'] and vlan_mbr != None:
                    cc_fail=1
                    print "\tFAILED - STP state inconsistent in Community vlan " + str(iv) +  " in IN direction."
                if (hw_out[(slot,unit)][iface.hwIf.get_hw_port()]) != stp_dict[prim_vlan]['Interface_info'][port]['Status'] and vlan_mbr != None:
                    cc_fail=1
                    print "\tFAILED - STP state inconsistent in Community vlan " + str(iv) +  " in OUT direction."
            if cc_fail == 0:
                print "\tPASSED - All CFG community vlans allowed in both directions"


