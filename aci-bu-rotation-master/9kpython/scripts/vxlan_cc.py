#################################################
#
#      File:   vxlan_cc.py
#      Name:   Vijay Sampath
#
#       Description: vxlan consistency checker
#
#
#
# Copyright (c) 1985-2015 by cisco Systems, Inc.
# All rights reserved.
#
#################################################
import signal
from onxos import *
signal.signal(signal.SIGINT, signal_handler_sigint)
from vxlan_common import *
from libnxos_ext_api import *
from collections import namedtuple

class ConsistencyError(Exception):
    def __init__(self, str):
        self.str = str
    def __str__(self):
        return repr(self.str)

def assertRange(name, mod, unit, val, min, max, str):
    if val < min or val > max:
        print "%s %s %d out of range on mod %d unit %d" % \
              (name, str, val, mod, unit)
        raise ConsistencyError("Consistency error %s" % str);

def assertEqual(name, mod, unit, val, targetVal, str):
    if val != targetVal:
        print "%s %s %d does not match %d on mod %d unit %d" % \
              (name, str, val, targetVal, mod, unit)
        raise ConsistencyError("Consistency error %s" % str);

def assertNotEqual(name, mod, unit, val, targetVal, str):
    if val == targetVal:
        print "%s %s %d matches %d on mod %d unit %d" % \
              (name, str, val, targetVal, mod, unit)
        raise ConsistencyError("Consistency error %s" % str);

def checkVfi(name, mod, unit, vlan_id):
    hwVfi = HwVfi(mod, unit, vlan_id)
    ipmcIdx = hwVfi.getIpmc()
    if ipmcIdx != 7:
        assertRange(name, mod, unit, hwVfi.getIpmc(), 0xffd, 0x1fff, "VFI IPMC")

def checkDeviceID(name,mod,unit):                                             
    hwDeviceId = HwDeviceId(mod,unit)                                       
    return hwDeviceId.getDevId()                                            

#####################################
# validate SOURCE_VP table
#####################################
def checkSourceVp(name, mod, unit, vp, vlan_id, is_mct, is_vpc, is_up):
    hwVp = HwSourceVp(mod, unit, vp)
    assertEqual(name, mod, unit, hwVp.getVfi(), vlan_id, "SOURCE_VP VFI")
    if is_up:
        assertEqual(name, mod, unit, hwVp.getSdTagMode(), 1, "SOURCE_VP SD_TAG_MODE")
    if not is_mct:
        assertEqual(name, mod, unit, hwVp.getCMLFlagsNew(), 8, "SOURCE_VP CML_FLAGS_NEW")
        assertEqual(name, mod, unit, hwVp.getCMLFlagsMove(), 8, "SOURCE_VP CML_FLAGS_MOVE")

#####################################
# validate SOURCE_TRUNK_MAP table
#####################################
def checkSTM(name, mod, unit, vp, dmod, hw_port, is_trunk):
    hwSTM = HwSourceTrunkMap(mod, unit, dmod, hw_port)
    assertEqual(name, mod, unit, hwSTM.getSvpValid(), 1, "SOURCE_TRUNK_MAP SVP_VALID")
    assertEqual(name, mod, unit, hwSTM.getSourceVp(), vp, "SOURCE_TRUNK_MAP SOURCE_VP")
    if is_trunk:
        assertEqual(name, mod, unit, hwSTM.getPortType(), 1, "SOURCE_TRUNK_MAP PORT_TYPE")
    else:
        assertEqual(name, mod, unit, hwSTM.getPortType(), 0, "SOURCE_TRUNK_MAP PORT_TYPE")

#####################################
# validate VLAN_XLATE table
#####################################
def checkVXlate(name, mod, unit, dmod, hw_port, vp, vlan_id, is_trunk):
    #vlan_id = 5  ### hard coded; should be fixed
    if is_trunk:
        hwVXlate = VlanXlateEntry(mod, unit, vlan_id, dmod, hw_port, True)
        #print ("\n vlan %x hw_port %d vp %x" % (vlan_id, hw_port, vp))
        #print("\nt hwVXlate.getSvpValid is %d" % hwVXlate.getSvpValid())
        #print("\nt hwVXlate.getSourceVp is %d" % hwVXlate.getSourceVp())
        #print hwVXlate
    else:
        hwVXlate = VlanXlateEntry(mod, unit, vlan_id, dmod, hw_port, False)
    assertEqual(name, mod, unit, hwVXlate.getSvpValid(), 1, "VLAN_XLATE SVP_VALID")
    assertEqual(name, mod, unit, hwVXlate.getSourceVp(), vp, "VLAN_XLATE SOURCE_VP")

#####################################
# validate ING_L3_NEXT_HOP table
#####################################
def checkIngL3NextHop(name, mod, unit, nhi, dmod, hw_port,  \
                      is_trunk, is_vpc, is_up, is_peer_up):
    hwIngL3NH = HwIngL3NextHop(mod, unit, nhi)
    if is_vpc and not is_up:
        if not is_peer_up:
            # skipping neither me nor peer is up
            return
        mct_ifindex = py_get_mct_ifindex()
        if not py_im_is_port_up(mct_ifindex):
            # mct is not up either, returning
            return
        mct_if_name = py_im_get_long_name_from_if_index(mct_ifindex)
        mct_intf = Nxos.Interface(mct_if_name)

        # VPC will be pointing to MCT
        hw_port = mct_intf.hw_port
        dmod = mct_intf.dmod

    if is_trunk:
        assertEqual(name, mod, unit, hwIngL3NH.getT(), 1, "ING_L3_NEXT_HOP T")
        assertEqual(name, mod, unit, hwIngL3NH.getTgid(), hw_port, "ING_L3_NEXT_HOP TGID")
    else:
        assertEqual(name, mod, unit, hwIngL3NH.getMod(), dmod, "ING_L3_NEXT_HOP MODULE_ID")
        assertEqual(name, mod, unit, hwIngL3NH.getPort(), hw_port, "ING_L3_NEXT_HOP PORT_NM")

#####################################
#
# VXLAN access port consistency
# checker
#
#####################################
def validate_vxlan_port(if_indexes, if_names):
    mods = Nxos.Module.getOnlineModules()
    all_passed = True

    for name in if_names:
        if "." in name:     
            continue
        intf = Nxos.Interface(name, _modList = mods)
        (vlan_cnt, vlan_list, vpl_list) = intf.get_vpl_list()
        if (vlan_cnt == 0):
            continue
        vlan_idx = 0
        intf_passed = True
        is_mct = py_mcecm_api_is_pc_mct(intf.ifindex);
        is_vpc = py_mcecm_api_is_pc_mcec(intf.ifindex);
        is_up = py_im_is_port_up(intf.ifindex);
        is_peer_up = False
        # Check port table
        str = "PORT_TABLE VT_ENABLE"
        try:
            if(not intf.is_po()):
                if(intf.hwIf.getVTEnable() != 1):
                    print "%s %s %d does not match %d" % \
                      (name, str, intf.hwIf.getVTEnable(), 1)
                    raise ConsistencyError("Consistency error %s" % str);
            else:
                for mem_intf in intf.members:
                    if(mem_intf.hwIf.getVTEnable() != 1):
                        print "%s %s %d does not match %d" % \
                          (name, str, mem_intf.hwIf.getVTEnable(), 1)
                        raise ConsistencyError("Consistency error %s" % str);
        except ConsistencyError:
            intf_passed = False
            all_passed = False
            print "%s\t[FAIL]!!!" % name


        if is_vpc:
            is_peer_up = py_mcecm_is_peer_mcec_up(intf.ifindex);
        for vlan_id in vlan_list:
            dot1q = py_vlan_get_oper_original_vlan(intf.ifindex, vlan_id)
            for mod in mods:
                for unit in range(0, mod.units):
                    try:
                        if py_platform_is_fabric_unit(mod.mod - 1, unit):
                            #print("skipping fabric unit %d"%mod.mod)
                            continue
                        checkT2 = checkDeviceID(name,mod.mod,unit)       
                        if checkT2 is not True:             
                            continue
                        # Check VFI table
                        checkVfi(name, mod.mod, unit, vlan_id)

                        # Check SOURCE_VP table
                        di = py_pixm_lib_ifidx_to_di(vpl_list[vlan_idx])
                        if di == 0xffffffff:
                            print "%s VLAN %d LTL not allocated" % (name, vlan_id)
                            raise ConsistencyError("Consistency error LTL")
                        vp = getVxlanVpFromLtl(di)
                        checkSourceVp(name, mod.mod, unit, vp, vlan_id, \
                                      is_mct, is_vpc, is_up)

                        # Check SOURCE_TRUNK_MAP/VLAN_XLATE table
                        if (intf.is_access_port() or intf.is_dot1q_port()) and not intf.is_ns_attached():
                            if intf.is_po():
                                for mem_intf in intf.members:
                                    checkSTM(name, mod.mod, unit, \
                                            vp, mem_intf.dmod, \
                                            mem_intf.hw_port, True)
                            else:
                                checkSTM(name, mod.mod, unit, \
                                            vp, intf.dmod, \
                                            intf.hw_port, False)
                        else:
                            if intf.is_po():
                                for mem_intf in intf.members:
                                    checkVXlate(name, mod.mod, unit, intf.dmod, \
                                        intf.hw_port, vp, dot1q, \
                                        True)
                            else:
                                checkVXlate(name, mod.mod, unit, intf.dmod, \
                                        intf.hw_port, vp, dot1q, \
                                        False)

                        # Check Next Hop
                        hwIngDvp = HwIngDvpTable(mod.mod, unit, vp)
                        nhi = hwIngDvp.getNHI()
                        hwIngL3NH = HwIngL3NextHop(mod.mod, unit, nhi)
                        checkIngL3NextHop(name, mod.mod, unit, nhi, \
                                intf.dmod, intf.hw_port, intf.is_po(),
                                is_vpc, is_up, is_peer_up)

                    except ConsistencyError:
                        intf_passed = False
                        all_passed = False
                        print "%s\t[FAIL]!!!" % name
            vlan_idx += 1
        if vlan_idx and intf_passed:
            print "%s\t[PASS]..." % name

    if all_passed:
        print "\nConsistency Check: PASSED\n"
    else:
        print "\nConsistency Check: FAILED\n"


#####################################
#
# VXLAN vlan consistency checker
#
#####################################
def validate_vxlan_vlan(vlans, vlan_names):
    mods = Nxos.Module.getOnlineFLCModules()
    all_passed = True

    for name in vlan_names:
        vlan_id = int(name)
        vlan_obj = Nxos.Vlan(vlan_id)
        vlan_passed = True

        if vlan_obj.vnseg == 0:
            print "VLAN %d not mapped to vn-segment" % vlan_id
            continue
        stp_dict = getShowSpanningTreeDict(vlan_id)
        intf_dict = {}
        if vlan_id in stp_dict and 'Interface_info' in stp_dict[vlan_id]:
            intf_dict = stp_dict[vlan_id]['Interface_info']
        else:
# TODO: handle the case where show spanning-tree does not have any info
# Need to get list of ports in vlan using a different method
            print "Warning! Not checking for access port flood list on vlan %d as STP instance does not exist" % vlan_id
        mcast_group = getVxlanMcastGroup(vlan_obj.vnseg)
        vtep_ip = getVxlanVtepIp()
        oifs = []
        oif_names = []
        if mcast_group and vtep_ip:
            oif_names = getSGOifList(vtep_ip, mcast_group)

        fwd_ports_info = []
        InfoStruct = namedtuple("InfoStruct", "intf is_po hw_port")

# add spanning tree FWD ports
        for intf in intf_dict:
            if intf_dict[intf]['Status'] != 'FWD':
                continue;
            i = Nxos.Interface(_shortName = intf)
            if i.is_po():
                for m in i.members:
                    #print "%s/%s(%d %d) %s is %s" % (intf, m.shortName, m.dmod, m.hw_port, m.hwIf.get_if_hw_name(), intf_dict[intf]['Status'])
                    fwd_ports_info.append(InfoStruct(m, True, i.hw_port))
            else:
                #print "%s(%d %d) %s is %s" % (intf, i.dmod, i.hw_port, i.hwIf.get_if_hw_name(), intf_dict[intf]['Status'])
                fwd_ports_info.append(InfoStruct(i, False, i.hw_port))

# add ports in sh ip mroute
        for oif_name in oif_names:
            i = Nxos.Interface(oif_name)
            if i.is_po():
                for m in i.members:
                    #print "%s/%s(%d %d) %s is %s" % (intf, m.shortName, m.dmod, m.hw_port, m.hwIf.get_if_hw_name(), intf_dict[intf]['Status'])
                    #fwd_ports.append(m)
                    fwd_ports_info.append(InfoStruct(m, True, i.hw_port))
            else:
                #print "%s(%d %d) %s is %s" % (intf, i.dmod, i.hw_port, i.hwIf.get_if_hw_name(), intf_dict[intf]['Status'])
                #fwd_ports.append(i)
                fwd_ports_info.append(InfoStruct(i, False, i.hw_port))

        if not fwd_ports_info:
            print "no ports in vlan %d" % vlan_id
            return

        for mod in mods:
            for unit in range(0, mod.units):
                try:
                    hwVfi = HwVfi(mod.mod, unit, vlan_id)
                    group = hwVfi.getVxlanGroup()
                    hwMcList = HwMcList(mod.mod, unit, group)
                    for fwd_port_info in fwd_ports_info:
                        fwd_port = fwd_port_info[0]
                        hw_name = fwd_port.hwIf.get_if_hw_name()
                        if fwd_port.slot != mod.mod:
                            #print "skipping slot %d" % fwd_port.slot
                            continue
                        if fwd_port.unit != unit:
                            #print "skipping unit %d" % fwd_port.unit
                            continue
                        if hw_name not in hwMcList.nh_list:
                            print "%s not in mc show output slot %d unit %d" % (hw_name, mod.mod, unit)
                            raise ConsistencyError("Consistency error mc show")
                        else:
                            for nhi in hwMcList.nh_list[hw_name]:
                                nhi -= 400000
                                checkIngL3NextHop(fwd_port.shortName, mod.mod, unit, nhi, \
                                        fwd_port.dmod,
                                        fwd_port_info[2],  #fwd_port.hw_port,
                                        fwd_port_info[1],
                                        False, # is_vpc -> dont care
                                        True,  # is_up
                                        False) # is_peer_up
                            #print "%s is in mc show" % hw_name
                except ConsistencyError:
                        vlan_passed = False
                        all_passed = False
                        print "VLAN%s\t[FAIL]!!!" % name
        if vlan_passed:
            print "VLAN%s Multicast Group Check\t[PASS]..." % name

    if all_passed:
        print "\nConsistency Check: PASSED\n"
    else:
        print "\nConsistency Check: FAILED\n"


