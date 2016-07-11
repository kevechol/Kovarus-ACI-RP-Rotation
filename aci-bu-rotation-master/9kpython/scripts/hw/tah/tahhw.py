#################################################
#
#      File:   tahhw.py
#      Name:   Connor Lange (colange)
#
#      Description: This file contains all the Tahoe 
#                   specific code used for the CCs
#
#
# Copyright (c) 1985-2013, 2015-2016 by Cisco Systems, Inc.
# All rights reserved.
#
#################################################

import sys,re,os,collections
from nxos_utils import *
from sets import Set
import nxos
import json
import cli
import tahoe
import operator

class TahHwMod:
    def __init__(self, _mod, _units = None):
        self.mod = _mod
        self.units = 1
        self.modid = {}
        self.modid[0] = 1

    def get_modid(self):
        return self.modid
 
    def get_mod(self):
        return self.mod

    def get_units(self):
        return self.units

    def get_all_hg_ports(self):                              
        raise Exception("Error: not implemented for Tahoe")

class TahHwPort:
    def __init__(self, _type, _chassis_slot, _unit, _rangerPC, _hw_port, \
            _mac_unit, _mac_pid, _ns_port, _hw_usr_port, _mods, \
            _rng100Gport, _slice_num, _port_on_slice, _src_id, _ltl, _hw_name, _slice_offset):
        self.mod = _chassis_slot
        self.unit = _unit
        self.hw_port = _hw_port
        self.ns_port = _ns_port
        self.hw_usr_port = _hw_usr_port
        self.hwMemberTables = {} 
        self.hwPcTables = {} 
        self.hwMemberPorts = {} 
        self.hwPortTable = None 
        self.hw_mask_int = None 
        self.hw_name = _hw_name 
        self.isRanger = _rangerPC
        self.rangerMemberPorts = None 
        self.mac_unit = _mac_unit
        self.mac_pid = _mac_pid
        self.slice_num = _slice_num
        self.port_on_slice = _port_on_slice
        self.src_id = _src_id
        self.ltl = _ltl
        self.slice_offset = _slice_offset
        
        #if _type == IfType.Ethernet:
        #    self.hw_name = ""
        #elif _type == IfType.Internal:
        #    self.hw_name = ""
        if _type == IfType.Cpu:
            self.hw_name = "cpu0"
        if _type == IfType.Fex:
            self.hw_name = ""
            return


        # get the members programmed.
        if _type == IfType.PortChannel:
            # _mods must have been given for it.
            for m in _mods:
                for u in range(0, m.units):
                    pass

    def get_hw_port(self):
        return self.hw_port

    def get_hwMemberPorts(self):
        return self.hwMemberPorts

    def get_unit(self):
        return self.unit

    def get_hw_name(self):
        return self.hw_name

    def get_isRanger(self):
        return False

    def get_rangerMemberPorts(self):
        return []

    # BCM ports have ns_port as 255
    def is_nsport(self):
        return False

    def get_hw_mask_int(self):
        raise Exception("Error: not implemented for Tahoe")

    
    def get_counters_dict(self):
        raise Exception("Error: not implemented for Tahoe")
    
    def get_counters_snmp(self):
        raise Exception("Error: not implemented for Tahoe")

    def get_counters_snmp_dict(self):
        raise Exception("Error: not implemented for Tahoe")

    def get_if_hw_name(self):
        raise Exception("Error: not implemented for Tahoe")

    def get_hw_link_state(self):
        if self.isRanger:
            return self.rangerPort.get_hw_link_state()
        cmd = "show interface %s" % self.hw_name
        output = runVshCmd(cmd)
        line = output.split('\n')[0]

        if line is not None and "up" in line:
            return 1

        return 0

    def getPortVid(self):
        return 4095

    def getIpv4L3EnableBits(self):
        return 1

    def getIpv4McEnableBits(self):
        return 0

    def getIpmcDoVlanBits(self):
        return 1

    def getVntagBits(self):
        raise Exception("Error: not implemented for Tahoe")

    def getMymodidBits(self):
        raise Exception("Error: not implemented for Tahoe")

    def getCmlNewBits(self):
        raise Exception("Error: not implemented for Tahoe")

    def getCmlMoveBits(self):
        raise Exception("Error: not implemented for Tahoe") 

    def getVTEnable(self):
            raise Exception("Error: not implemented for Tahoe")

    def get_intf_info(self):
        '''Python handler to return lif's phy_intf_id for an interface'''

        cmd = 'show system internal eltm info interface %s' % (self.hw_name)
        output = runVshCmd(cmd)
        lines = output.split("\n") 
        for line in lines:
            line = line.strip()
            if 'LIF = ' in line:
                (NULL, NULL, text) = line.partition("LIF = ")
                (lif_intf_id, NULL, text) = text.partition(" ")
            if 'ipv4_en' in line:
                (NULL, NULL, text) = line.partition("ipv4_en = ")
                (ipv4_en, NULL, text) = text.partition(",");
            if 'ipv4_mcast_en' in line:
                (NULL, NULL, text) = line.partition("ipv4_mcast_en = ")
                (ipv4_mcast_en, NULL, text) = text.partition(",");
            if 'ipv6_en' in line:
                (NULL, NULL, text) = line.partition("ipv6_en = ")
                (ipv6_en, NULL, text) = text.partition(",");
            if 'ipv6_mcast_en' in line:
                (NULL, NULL, text) = line.partition("ipv6_mcast_en = ")
                (ipv6_mcast_en, NULL, text) = text.partition(" ");

        ret_values = [int(lif_intf_id),int(ipv4_en),int(ipv4_mcast_en),int(ipv6_en),int(ipv6_mcast_en)]

        return ret_values 

    def validate_l3_intf(self):
        '''Python handler for interface hw table consistency checker'''
        DEFAULT_L3_VLAN = 4095
        ETHPM_LTL_BASE = 6145

        pass_check = True

        bdclass = tahoe.Bd(_print_out = 0)
        ifclass = tahoe.Interface(_print_out = 0)

        [lif_intf_id, ipv4_en, ipv4_mcast_en, ipv6_en, ipv6_mcast_en] = self.get_intf_info() 
        [ltl_from_ethpm, dpid, unit, slice, port_on_slice, src_id] = \
                        [self.ltl, self.hw_port, self.unit, self.slice_num, self.port_on_slice, self.src_id]

        expected_ltl = ETHPM_LTL_BASE - ltl_from_ethpm

        ## Get Pif entry from slice and src_id
        pif_info = ifclass.get_pif(slice, src_id)
       
        if len(pif_info) == 0:
            print 'Error: Could not find pif from src-id'
            pass_check = False
            return pass_check
      
        print '=========================================' 
        print 'Pif entry for interface %s' % (self.hw_name)
        print pif_info[0]

        try:
            pif_niv_idx = pif_info[0]['niv_idx']
        except KeyError:
            pif_niv_idx = 0
        if pif_niv_idx != expected_ltl:
            print "LTL is incorrect. Expected %d. Programmed %d" % \
                    (expected_ltl, pif_niv_idx)
            pass_check = False
        try:
            pif_default_vlan = pif_info[0]['default_vlan']
        except KeyError:
            pif_default_vlan = 0
        if pif_default_vlan != DEFAULT_L3_VLAN:
            print 'L3 mismatch: vlan should be %d' % DEFAULT_L3_VLAN
            pass_check = False

        ## Get list of VIF entries
        ## if the pif entry is a fex fabric port,
        ## we'll have a list of vif entries here, one for each HIF
        ## for normal ports, we should get only one with svif=4095
        vif = ifclass.get_vif(slice, pif_niv_idx)

        if len(vif) == 0:
            print 'Error: Could not find pif from niv_idx'
            pass_check = False
            return pass_check 

        if len(vif) > 1:
            print "Port is a fabric port connected to Fex"
            print "  No support for FEX i/f as of now"
            ## TODO: Handle FEX HIF i/f..
            pass_check = False
            return pass_check 
        else:
            print '========================================='
            print 'VifTable entry for interface %s' % (self.hw_name)
            print vif[0]
        try:
            vif[0]['valid']
        except KeyError:
            print 'Error: vif is not valid'
            pass_check = False
            return pass_check 
        try:
            key_vif = vif[0]['key_vif']
        except KeyError:
            key_vif = 0
        if key_vif != 4095:
            print 'Error: viftable key_vif %d is not set to svif 4095' % key_vif
            print 'Okay if fex intf'


        ##Get the vifstate entry from the vif data
        try:
            lif = vif[0]['data_vif']
        except KeyError:
            lif = 0
        vifstate = ifclass.get_vifstate(slice, lif)

        if len(vifstate) <= 0:
            print 'Error: Could not find vif state entry'
            pass_check = False
            return pass_check 

        print '========================================='
        print 'VifStateTable entry for interface %s' % (self.hw_name)
        print vifstate[0]

        try:
            vifstate_default_vlan = vifstate[0]['info_default_vlan']
        except KeyError:
            vifstate_default_vlan = 0
        if vifstate_default_vlan != DEFAULT_L3_VLAN:
            print 'Error: vifstatetable default vlan is not set to DEFAULT_L3_VLAN for L3'
            pass_check = False
            return pass_check
        try:
            vifstate_src_idx = vifstate[0]['info_src_idx']
            if vifstate[0]['info_src_idx'] != expected_ltl:
                print 'Error: vifstatetable src_idx does not match expected_ltl %d' % \
                                                            (expected_ltl)
                pass_check = False
        except KeyError:
            vifstate_src_idx = 0
        if vifstate_src_idx != expected_ltl:
            print 'Error: vifstatetable src_idx does not match expected_ltl %d' % \
                                                                (expected_ltl)
            pass_check = False

        try:
            ##Get the vlanxlate entry from bd_xlate_idx obtained
            ## from vifstate entry, and the default L3 vlan 4095
            bd_xlate_idx = vifstate[0]['info_bd_xlate_idx']
        except KeyError:
            bd_xlate_idx = 0
        if bd_xlate_idx != expected_ltl:
            print 'Error: vifstatetable bd_xlate_idx does not match expected ltl %d' % \
                                                               (expected_ltl)
            pass_check = False
            return pass_check


        vlanxlate = bdclass.get_vlanxlate(slice, bd_xlate_idx, DEFAULT_L3_VLAN)

        if len(vlanxlate) <= 0:
            print 'Error: Could not find xlate entry from bd_xlate_idx %d and L3 vlan %d' % \
                                        (bd_xlate_idx, DEFAULT_L3_VLAN)
            pass_check = False
            return pass_check 
        else:
            print '========================================='
            print 'VlanXlateTable entry for interface %s, xlate_idx %d' % \
                                        (self.hw_name, bd_xlate_idx)
            print vlanxlate[0]
        try:
            vlanxlate_bd_xlate_idx = vlanxlate[0]['key_bd_xlate_idx']
        except KeyError:
            vlanxlate_bd_xlate_idx = 0
        if vlanxlate_bd_xlate_idx != bd_xlate_idx:
            print 'Error: vlanxlatetable bd_xlate_idx %d does not match vifstatetable bd_xlate_idx' \
                                           % (vlanxlate_bd_xlate_idx, bd_xlate_idx)
            pass_check = False
        try:
            epg_or_bd = vlanxlate[0]['data_epg_or_bd']
        except KeyError:
            epg_or_bd = 0

        if epg_or_bd != lif_intf_id:
            print 'Error: vlanxlatetable epg_or_bd %d does not match intf_id %d we use as L3 BD' \
                                            % (epg_or_bd, lif_intf_id)
            pass_check = False
            return pass_check

        ##Get the BdState entry for the L3 Vif from xlated L3 vlan
        vif_bd = epg_or_bd
        bdstate = bdclass.get_bdstate(slice, vif_bd)

        
        if len(bdstate) <= 0:
            print 'Error: Could not find BD'
            pass_check = False
            return pass_check

        print '========================================='
        print 'BdStateTable entry for interface %s, BD %d' \
                                     % (self.hw_name, vif_bd)
        print bdstate[0]
        
        if ipv4_en:
            try:
                bdstate[0]['ipv4_ucast_en']
            except KeyError:
                print 'Error: ipv4_ucast_en is not set for BD %d' % (vif_bd)
                pass_check = False
        if ipv4_mcast_en:
            try:
                bdstate[0]['ipv4_mcast_en']
            except KeyError:
                print 'Error: ipv4_mcast_en is not set for BD %d' % (vif_bd)
                pass_check = False
        if ipv6_en:
            try:
                bdstate[0]['ipv6_ucast_en']
            except KeyError:
                print 'Error: ipv6_ucast_en is not set for BD %d' % (vif_bd)
                pass_check = False
        if ipv6_mcast_en:
            try:
                bdstate[0]['ipv6_mcast_en']
            except KeyError:
                print 'Error: ipv6_mcast_en is not set for BD %d' % (vif_bd)
                pass_check = False
        try:
            bdstate[0]['is_l3_if']
        except KeyError:
            print 'Error: is_l3_if is not set for BD %d' % (vif_bd)
            pass_check = False

        try:
            bdstate_index = bdstate[0]['index_in_table']
        except KeyError:
             print 'Error: index_in_table not set for BdStateTable'
             pass_check = False
             return pass_check
        if bdstate_index != lif_intf_id:
            print 'Error: BdState entry %d does not match expected L3 lif BD %d' \
                                             % (bdstate_index, lif_intf_id)
            pass_check = False

        ##Use lif as dst_idx to LocalMultiPath Table
        localmultipath = ifclass.get_localmultipath(slice, lif)

        if len(localmultipath) <= 0:
            print 'Error: Could not find LocalMultiPath entry from lif %d' % (lif)
            pass_check = False
            return pass_check

        print '========================================='
        print 'LocalMultiPath entry for interface %s, lif %d' % \
                                    (self.hw_name,lif)
        print localmultipath[0]
        
        try:
            vpc_port_idx_0 = localmultipath[0]['vpc_port_idx_0']
        except KeyError:
            vpc_port_idx_0 = 0
        try:
            vpc_port_idx_1 = localmultipath[0]['vpc_port_idx_1']
        except KeyError:
            vpc_port_idx_1 = 0

        if vpc_port_idx_0 != lif:
            print 'Error: localmultipath vpc_port_idx_0 %d does not match lif %d' \
                                    % (vpc_port_idx_0, lif)
            pass_check = False
        if vpc_port_idx_1 != lif:
            print 'Error: localmultipath vpc_port_idx_1 %d does not match lif %d' \
                                    % (vpc_port_idx_1, lif)
            pass_check = False
        
        ##Get the ucpcmbr ucpcmbr table from lif
        ucpcmbr = ifclass.get_ucpcmbr(slice, lif)
        
        if len(ucpcmbr) <= 0:
            print 'Error: Could not find ucpcmbr entry from lif %d' % (lif)
            pass_check = False
            return pass_check
        
        print '========================================='
        print 'UcPcMbrTable entry for interface %s, lif %d' \
                                   % (self.hw_name, lif)
        print ucpcmbr[0]
       
        ##expected_ovector_idx for ethernet ports uses pif_idx
        ##TODO: Port-channels use slice_port?
        expected_ovector_idx = (slice << self.slice_offset) | (pif_info[0]['index_in_table'])

        try:
            dst_port = ucpcmbr[0]['dst_port']
        except KeyError:
            dst_port = 0
        
        if dst_port != dpid:
            print 'Error: UcPcMbr dst_port %d does not match dpid %d' \
                                   % (dst_port, dpid)
            pass_check = False

        try:
            ovector_idx = ucpcmbr[0]['ovector_idx']
        except KeyError:
            ovector_idx = 0
        if ovector_idx != expected_ovector_idx:
            print 'Error: UcPcMbr ovector_idx %d does not match ' % ovector_idx
            print '    expected ovector_idx %d' % expected_ovector_idx
            pass_check = False
        
        return pass_check


class TahHwVlan:
    def __init__(self, _vlan, slices):
        self.vlan = _vlan
        self.num_slices = slices
        #self.vlan_str = str(_vlan)

    def validate_stp_state(self, _modList, sw_output, sw_output_vp):
        ok = []
        nok = []
        ingress_ports = self.get_vlan_membership(_egr = False)
        egress_ports = self.get_vlan_membership(_egr = True)
        flood_ports = self.get_vlan_flood_membership()

        s1 = Set(ingress_ports)
        s2 = Set(egress_ports)
        s3 = Set(flood_ports)
        
        forwarding_ports = s1 & s2 & s3
        inconsistent_ports = (s1 - s2) | (s2 - s1) | (s3 - s1) | (s1 - s3) | (s3 - s2) | (s2 - s3)
        # Add all ports that are inconsistent in HW to nok
        for inconsistent_port in inconsistent_ports:
            nok.append(nxos.Nxos.Interface(_ifindex = inconsistent_port, _queryHw = False))

        for (mod, unit) in sw_output:
            for h_port in sw_output[(mod, unit)]:
                (interface, stp_state) = sw_output[(mod, unit)][h_port]
                # Interface exists in STP table and in hardware, it better be FWD
                if interface.ifindex in forwarding_ports:
                    if stp_state == "FWD":
                        if interface not in ok:
                            ok.append(interface)
                    else:
                        if interface not in nok:
                            nok.append(interface)
                # It's not in hardware, so it better be in any state except FWD
                else:
                   if stp_state == "FWD":
                       if interface not in nok:
                           nok.append(interface)
                   else:
                       if interface not in ok:
                           ok.append(interface)
        
        return (sorted(ok), sorted(nok))    

    def validate_vlan_membership(self, _modList, vlan_active_in_sw, _nxosIfList):
        mod = [] 
        ok = [] 
        nok = [] 
        xes = {} 
        ifList = [] 
        if _nxosIfList is None:
            return ([], [])

        ingress_ports = self.get_vlan_membership(_egr = False)
        egress_ports = self.get_vlan_membership(_egr = True)
        flood_ports = self.get_vlan_flood_membership()

        s1 = Set(ingress_ports)
        s2 = Set(egress_ports)
        s3 = Set(flood_ports)
        # Force egress membership for NIF ports
        for ifidx in s1:
            try: 
                i = nxos.Nxos.Interface(_ifindex = ifidx, _queryHw = False)
            except:
                continue
                 
            if i.nif or i.ns_port != 255: 
                s2.add(ifidx)
                s3.add(ifidx)
  
        inconsistent_in_hw = (s1 - s2) | (s2 - s1) | (s3 - s1) | (s1 - s3) | (s3 - s2) | (s2 - s3)
        consistent_in_hw = s1 & s2 & s3

        # Only add the ports that are up in SW
        if inconsistent_in_hw and len(inconsistent_in_hw) > 0: 
            for ifidx in inconsistent_in_hw:
                i = nxos.Nxos.Interface(_ifindex = ifidx, _queryHw = False)
                if i.get_sw_link_state() == 1 and i.get_layer() == 2:
                    nok.append(ifidx)

        #  Do a reverse check. i.e. make sure the hardware ports in a
        #  vlan are also there in software.
	nxos_ports = Set()
	for i in _nxosIfList:
            nxos_ports.add(i.ifindex)
	hw_ports = s1 & s2 & s3
	inc_ports = hw_ports - nxos_ports
	for ifidx in inc_ports:
            i = nxos.Nxos.Interface(_ifindex = ifidx, _queryHw = False)
            if i.get_sw_link_state() == 1 and i.get_layer() == 2:
                nok.append(ifidx)
        
        # Cross-check with software. Any (in)consistencies found here are subject 
        # to filtering, re-evaluation at the PI layer, in cc_vlan_memb.py   
        for intf in _nxosIfList:
            if not intf.fex: 
                # if monitor dest port, dont consider it for vlan consistency check
                if intf.span_dest == 1:
                    continue

                # In Software, but not in hw (check both egress and ingress)
                if intf.ifindex not in consistent_in_hw:
                    if intf.get_sw_link_state() == 1 and vlan_active_in_sw:
                        nok.append(intf.ifindex)
                    # Old entry that's aging out
                    else:
                        ok.append(intf.ifindex)

                # In software, and in both egress and ingress in HW
                else:
                    if (vlan_active_in_sw):
                        ok.append(intf.ifindex)
                    else:
                        nok.append(intf.ifindex)
            else:
                # This is FEX
                if intf.ifindex in consistent_in_hw:
                    ok.append(intf.ifindex)
                else:
                    if intf.get_sw_link_state() == 1 and vlan_active_in_sw:
                        nok.append(intf.ifindex)
                    else:
                        ok.append(intf.ifindex)

        return (list(Set(ok)), list(Set(nok)))

    def get_vlan_membership(self, _modList = None, _egr = False):
        intfs = []
            
        for s in range(self.num_slices):
            intfs.extend(self.get_vlan_membership_by_slice(s, _egr))
        return intfs

    def get_vlan_egress_bitmap(self, slice_num, vlan_num):
        table = tahoe.runtahoecmd(True, 1, 1, slice_num, vlan_num,
                                  "rwx_rwepgstatetable")
        try:
            membership = table[0]["ifmbr"]
        except:
            membership = ":".join(['0x00000000'] * 2)

        bitmask = re.sub("0x|:", "", membership)
        #print "#%s: EGRESS %s" % (slice_num, bitmask)
        return bitmask

    def get_vlan_ingress_bitmap(self, slice_num, vlan_num):
        table = tahoe.runtahoecmd(True, 1, 1, slice_num, vlan_num,
                                  "luc_vifvlanmbrtable")
        try:
            membership = table[0]["state_membership"]
        except:
            membership = ':'.join(['0x00000000'] * 8) 

        bitmap = re.sub("0x|:", "", membership)
        #print "#%s: INGRESS %s" % (slice_num, bitmap)
        return bitmap

    def get_vlan_flood_bitmap(self, slice_num, vlan_num):
        table = tahoe.runtahoecmd(True, 1, 1, slice_num, vlan_num,
                                  "qsmt_ovtbl")
        try:
            flood = table[0]["data"]
        except:
            flood = ":".join(["0x00000000"] * 2)
        
        bitmap = re.sub("0x|:", "", flood)
        return bitmap

    def get_vlan_flood_membership_by_slice(self, _slice):
        intfs = []
        vlan_num = self.vlan
        bitmap = self.get_vlan_flood_bitmap(_slice, vlan_num)
        
        val = int(bitmap, 16)
        for offset in range(len(bitmap)*4):
            mask = 1 << offset
            if val & mask:
                intfs.append(tahoe.slice_port_to_if_index(1, 0, _slice, offset))
        return intfs        

    def get_vlan_flood_membership(self):
        intfs = []
        for s in range(self.num_slices):
            intfs.extend(self.get_vlan_flood_membership_by_slice(s))
        return intfs

    def get_vlan_membership_by_slice(self, _slice, _egr = False):
        intfs = [] 
        vlan_num = self.vlan
        # Ingress
        if not _egr: 
            bitmap = self.get_vlan_ingress_bitmap(_slice, vlan_num) 

            for bit in range(len(bitmap)):
                if bitmap[bit] == '1': 
                    intfs.append((_slice, len(bitmap) - (bit + 1))) 
        # Egress
        else: 
            bitmap = self.get_vlan_egress_bitmap(_slice, vlan_num) 
            val = int(bitmap,16) 
            for offset in range(len(bitmap)*4):
                mask = 1 << offset
                if val & mask:
                    intfs.append((_slice, offset))
        
        for i in range(len(intfs)):
            # on Davos, we use slice port for both ingress and egress
            if not _egr or tahoe.is_davos():
                intfs[i] = tahoe.slice_port_to_if_index(1, 0, intfs[i][0], intfs[i][1])
            # rwx_rwepgstatetable is indexed by source port on lacrosse only
            else:
                intfs[i] = tahoe.src_id_to_if_index(1, 0, intfs[i][0], intfs[i][1])

        # Filter out the (slice, slice port) tuples
        # that don't correspond to real ports
        intfs = filter(lambda x: x > 0, intfs)
        return intfs

    def get_vlan_stp_state(self, _modList):    
        raise Exception("Error: not implemented for Tahoe") 

    def getVlanProfilePtr(self, slot, unit):
        return 0

class TahHwTrunkCollection:
    def __init__(self, _modList, _ifIndexes, num_slices=2):
        self.num_slices = num_slices
        self.err_stmts = {}
        self.pc_filter = _ifIndexes

    def populate_hw_mapping(self):
        output = runVshCmd("show int hardware-mapping").split("\n")[13:-1]
        self.hw_map = {}
        for line in output:
            if "VPort" in line:
                continue
            data = re.split("\s+", line)
            if len(data) < 4:
                continue

            if "Po" in line:
                # Map the PO port # into an ifindex
                try:
                    self.hw_map[1536 + int(data[4])] = int(data[1], 16)
                except ValueError as err:
                    print "%s Line: %s" % (str(err), data)
            else:
                # Map the interface
                try:
                    self.hw_map[(int(data[8]), int(data[9]))] = int(data[1], 16)
                except ValueError as err:
                    print "%s Line: %s" % (str(err), data)

    def get_all_port_channels_and_members(self):
        """
        Get all the membership information from software. 
        Return a dictionary keyed by PO ifindex, containing a list 
        of members' ifindices
        """
        # Get the port-channel summary data, but skip the header
        data = cli.cli("show port-channel summary").split("\n")[11:]
        membership = {}
        i = 0
        po_key = ""
        while i < len(data):
            overflow = False
            # Split everything on space, but skip the empty strings
            line = filter(lambda x: x, re.split("\s+", data[i]))
            members = []
            for j in range(len(line)):
                # Skip the type and protocol entries
                # If the members have overflowed to the next line
                # don't skip them
                if not overflow and j in [2,3]:
                    continue
                match = re.search("Eth(\d+/\d+\/?\d*)\s*\(([A-z])\)", line[j])
                if match:
                    # Only get the up ports
                    if match.group(2) in ["P", "p"]:
                        (ret, ifidx) = py_im_get_if_index_from_name("Ethernet%s" % match.group(1))
                        members.append(ifidx)
                    # If there's a member as the first item on a line, 
                    # then we've overflowed a single line; act accordingly
                    if j == 0:
                        overflow = True
                else:
                    # Only match up port-channels
                    match = re.search("Po(\d+)\([A-Z]U\)", line[j])
                    if match: 
                        # We've hit a port-channel entry, reset overflow
                        (ret, ifidx) = py_im_get_if_index_from_name("Port-channel%s" % match.group(1))
                        po_key = ifidx
                        overflow = False
                    # only throw away the key if we aren't overflowing a single line
                    elif not overflow:
                        po_key = ""
            # Create the mapping. No need to sort since members are already sorted
            if po_key != "":
                membership[po_key] = membership.get(po_key, []) + members
            i += 1
        return membership

    def get_all_vpc_port_indices(self, slice_num):
        vpc_port_indices = []
        table = tahoe.runtahoecmdrange(True, 1, 1, slice_num, 1537, 512,
                                       "luc_localmultipathtable")
        num_entries = len(table)
        for i in range(0, num_entries):
            # If the key doesn't exist here, there's some inconsistency
            try:
                vpc_port_idx = int(table[i]["vpc_port_idx_0"], 16)
            except KeyError:
                vpc_port_idx = 0
            if vpc_port_idx > 1536 and vpc_port_idx < 2047:
                vpc_port_indices.append(vpc_port_idx)
        return Set(vpc_port_indices)

    def get_num_paths_from_vpc_port_idx(self, vpc_port_idx, slice_num):
        table = tahoe.runtahoecmd(True, 1, 1, slice_num, vpc_port_idx,
                                  "luc_ucportchannelconfigtable")
        try:
            return int(table[0]["num_paths"], 16)
        except:
            return 0

    def get_base_ptr_from_vpc_port_idx(self, vpc_port_idx, slice_num):
        table = tahoe.runtahoecmd(True, 1, 1, slice_num, vpc_port_idx,
                                  "luc_ucportchannelconfigtable")
        try:
            return int(table[0]["base_ptr"], 16)
        except:
            return -1

    def get_ovector_idx_from_base_ptr(self, base_ptr, slice_num):
        table = tahoe.runtahoecmd(False, 1, 1, slice_num, base_ptr,
                                  "luc_ucportchannelmembertable")
        try:
            return int(table[0]["ovector_idx"], 16)
        except:
            return -1

    def build_not_in_sw_err(self, mod, unit, vpc_port_idx):
        string = "Found hardware inconsistency for: vpc_port_idx %s\n" % vpc_port_idx
        string += "    Module: %s, Unit: %s\n" % (mod, unit)
        return string

    def build_num_paths_err(self, mod, unit, num_paths, pc_ifidx):
        # The py_im_get_Long_name_from_ifindex API is really dumb and requires some pointer 
        # as the second arg
        string = "Found hardware num_paths inconsistencies for:%s\n" % \
                        py_im_get_long_name_from_if_index(pc_ifidx)
        string += "    Module:%d, Unit:%d, Size:%d\n" % (mod, unit, num_paths)
        return string

    def verify_from_pos(self, mod, unit, slice_num, sw_dict):
        po_to_members = {}
        vpc_port_indices = self.get_all_vpc_port_indices(slice_num)
        if not vpc_port_indices:
            return {}

        for vpc_port_idx in vpc_port_indices:
            pc_ifidx = tahoe.vif_to_if_index(vpc_port_idx)
            # This VIF doesn't map to an ifindex (PC not in SW)
            if pc_ifidx == -1:
                self.err_stmts[vpc_port_idx] = self.build_not_in_sw_err(1, 0, vpc_port_idx)
                continue
            # Get the trunk size and base pointer
            num_paths = self.get_num_paths_from_vpc_port_idx(vpc_port_idx, slice_num)
            
            # Check if the PO is in software
            if pc_ifidx not in sw_dict:
                # If it's not in SW, but in HW and has num_paths other than 0
                # then it's an error
                if num_paths != 0:
                    self.err_stmts[pc_ifidx] = self.build_hw_po_diff_err(1, 0, pc_ifidx)
                continue

            # Check that num_paths matches software
            if num_paths != len(sw_dict[pc_ifidx]):
                self.err_stmts[pc_ifidx] = self.build_num_paths_err(1, 0, num_paths, pc_ifidx)
                continue

            base_ptr = self.get_base_ptr_from_vpc_port_idx(vpc_port_idx, slice_num)
            for i in range(0, num_paths):
                ovector_idx = self.get_ovector_idx_from_base_ptr(base_ptr, slice_num)
                
                if tahoe.is_davos():
                    # The slice number is in bits 8 and 9
                    mbr_slice_num = (ovector_idx & 0x180) >> 7
                    src_id = (ovector_idx & 0x7F)
                elif tahoe.is_lacrosse():
                    # The slice number is in bits 7, 8, and 9
                    mbr_slice_num = (ovector_idx & 0x1C0) >> 6
                    src_id = (ovector_idx & 0x3F)
                else:
                    mbr_slice_num = -1
                    src_id = -1
            
                port_on_slice = tahoe.src_id_to_slice_port(1, 0, mbr_slice_num, src_id)
                if port_on_slice == -1:
                    print "Failed to convert src_id %s on slice %s to slice port" % (src_id, mbr_slice_num)

                if vpc_port_idx > 1536:
                    if port_on_slice > -1:
                        if vpc_port_idx not in po_to_members:
                            po_to_members[vpc_port_idx] = [(mbr_slice_num, port_on_slice)]
                        else:
                            po_to_members[vpc_port_idx].append((mbr_slice_num, port_on_slice))
                    base_ptr += 1
        return po_to_members
   
    def get_all_eth_members(self, slice_num):
        table = tahoe.runtahoecmdrange(True, 1, 1, slice_num, 0, 2048, "lua_piftable")
        num_entries = len(table)
        src_id = ""
        niv_idx = ""
        eth_members = []
        for i in range(0, num_entries):
            try:
                niv_idx = int(table[i]["niv_idx"], 16)
                if niv_idx > 1536 and niv_idx < 2047:
                    src_id = int(table[i]["index_in_table"])
                    eth_members.append((slice_num, src_id))
            except:
                continue
        return eth_members

    def get_niv_idx_from_eth_slice_and_src(self, slice_and_src):
        slice_num = slice_and_src[0]
        src_id = slice_and_src[1]
        table = tahoe.runtahoecmd(True, 1, 1, slice_num, src_id, "lua_piftable")
        niv_idx = -1
        try:
            niv_idx = int(table[0]["niv_idx"], 16)
            if niv_idx > 1536:
                return niv_idx
            else:
                return -1
        except:
            return -1

    def get_info_src_idx_from_niv_idx(self, niv_idx, slice_num):
        table = tahoe.runtahoecmd(False, 1, 1, slice_num, niv_idx, "lua_vifstatetable")
        try:
            return int(table[0]["info_src_idx"], 16)
        except:
            return -1

    def verify_from_eths(self, mod, unit, slice_num):
        slices_and_srcs = self.get_all_eth_members(slice_num)
        port_on_slices = []
        for ss in slices_and_srcs:
            # get the slice port from the source ID
            info = py_im_get_hw_info_from_src_id_info(mod, unit, slice_num, ss[1])
            port_on_slices.append(info[9])
        po_to_members = {}

        for slice_and_src, port_on_slice in zip(slices_and_srcs, port_on_slices):
            slice_num = slice_and_src[0]
            niv_idx = self.get_niv_idx_from_eth_slice_and_src(slice_and_src)
            info_src_idx = self.get_info_src_idx_from_niv_idx(niv_idx, slice_num)
            if niv_idx > 1536:
                if niv_idx not in po_to_members:
                    po_to_members[niv_idx] = [(slice_num, port_on_slice)]
                else:
                    po_to_members[niv_idx].append((slice_num, port_on_slice))
        return po_to_members

    def normalize_hw_dict(self, dictionary):
        new_dict = {}
        for vpc_idx in dictionary:
            po_ifidx = tahoe.vif_to_if_index(vpc_idx)
            if po_ifidx == -1:               
                print "Failed to map vpc_index to port-channel name: %s" % vpc_idx
                continue   
                                                                             
            for member in dictionary[vpc_idx]:
                mbr_ifidx = tahoe.slice_port_to_if_index(1, 0, member[0], member[1])
                if mbr_ifidx == -1:
                    print "Failed to map (slice, slice_port): %s to ifindex for %s" % (str(member), py_im_get_long_name_from_if_index(ifindex))
                    continue
                new_dict[po_ifidx] = new_dict.get(po_ifidx, []) + [mbr_ifidx]

        return new_dict

    def convert_ifidx_to_names(self, ifList):
        for i in range(len(ifList)):
            if type(ifList[i]) != int:
                continue
            name = py_im_get_long_name_from_if_index(ifList[i])
            ifList[i] = name
        return ifList

    def build_po_missing_err(self, mod, unit, pc_ifidx):
        name = py_im_get_long_name_from_if_index(pc_ifidx)
        string = "Found missing PO from ingress or egress for %s\n" % name
        string += "   Module:%d, Unit:%d\n" % (mod, unit)
        return string

    def build_member_diff_err(self, mod, unit, pc_ifidx, sw_dict):
        string = "Found hardware member inconsistencies for: %s\n" % \
                                                      py_im_get_long_name_from_if_index(pc_ifidx)
        string += "    Module:%s, Unit:%s\n" % (mod, unit)
        string += "       %s\n" % str(self.convert_ifidx_to_names(sw_dict[pc_ifidx]))
        return string

    def build_sw_po_diff_err(self, mod, unit, pc_ifidx):
        string = "Found PO in software, but missing in hardware: %s\n" % \
                                                      py_im_get_long_name_from_if_index(pc_ifidx)
        string += "    Module:%s, Unit:%s\n" % (mod, unit)
        return string

    def build_hw_po_diff_err(self, mod, unit, pc_ifidx):
        string = "Found PO in hardware, but PO has no up ports in software: %s\n" % \
                                                      py_im_get_long_name_from_if_index(pc_ifidx)
        string += "    Module:%s, Unit:%s\n" % (mod, unit)
        return string

    def build_sw_member_diff_err(self, mod, unit, pc_ifidx, sw_dict):
        string = "Found member inconsistencies between hardware and software for: %s\n" % \
                                                      py_im_get_long_name_from_if_index(pc_ifidx)
        string += "    Module:%s, Unit:%s\n" % (mod, unit)
        string += "       %s\n"  % str(self.convert_ifidx_to_names(sw_dict[pc_ifidx])) 
        return string

    def validate_pc_membership(self, mods, okList, nokList, ok, nok):
        #self.populate_hw_mapping()
        
        sw_dict = self.get_all_port_channels_and_members()
        hw_dict_from_pos = self.normalize_hw_dict(self.get_hw_dict_from_pos(sw_dict))
        hw_dict_from_eths = self.normalize_hw_dict(self.get_hw_dict_from_eths(sw_dict))

        ing_pos = Set(hw_dict_from_eths.keys())
        egr_pos = Set(hw_dict_from_pos.keys())
        sw_pos = Set(sw_dict.keys())
        passed = True

        # Check hardware consistency
        consistent_in_hw = ing_pos & egr_pos
        inconsistent_in_hw = (ing_pos - egr_pos) | (egr_pos - ing_pos)

        for po in inconsistent_in_hw: 
            # Don't double up on errors
            if po not in self.err_stmts:
                self.err_stmts[po] = self.build_po_missing_err(1, 0, po)

        missing_hw_pos = (sw_pos - consistent_in_hw)
        for po in missing_hw_pos:
            # Don't double up on errors
            if po not in self.err_stmts:
                self.err_stmts[po] = self.build_sw_po_diff_err(1, 0, po)

        # Check software <-> hardware consistency
        consistent_pos = consistent_in_hw & sw_pos 
        for po in consistent_pos:
            egr_members = sorted(hw_dict_from_pos[po])
            ing_members = sorted(hw_dict_from_eths[po])
            if ing_members != egr_members:
                if po not in self.err_stmts:
                   self.err_stmts[po] = self.build_member_diff_err(1, 0, po, sw_dict)
            # Compare ingress since egr + ing are the same
            elif ing_members != sw_dict[po]:
                if po not in self.err_stmts:
                    self.err_stmts[po] = self.build_sw_member_diff_err(1, 0, po, sw_dict)
            # Only print the ones we care about
            elif po in self.pc_filter:
                print "No inconsistency found for: %s" % py_im_get_long_name_from_if_index(po)
                print "    Module:%s, Unit:%s" % (1, 0)
                print "     %s\n" % str(self.convert_ifidx_to_names(sw_dict[po]))

        for po in self.err_stmts:
            # Only print the ones we care about
            if po not in self.pc_filter:
                continue
            name = py_im_get_long_name_from_if_index(po)
            # Print the inconsistent ports before the detailed breakdown
            print "Found inconsistencies for %s:" % name
            print "  Module:%d, Unit:%d" % (1, 0)
            if po in sw_dict:
                print "     %s\n" % str(self.convert_ifidx_to_names(sw_dict[po]))
            else:
                print ""
            passed = False

        if passed:
            print "Consistency Check: PASSED\n"
        else:
            print "Consistency Check: FAILED\n"
        print "Following output shows hardware inconsistencies across all modules."
        print "------------------------------------------------------------------"
        for po in self.err_stmts:
            if po in self.pc_filter: 
                print self.err_stmts[po]

    def get_hw_dict_from_eths(self, sw_dict):
        mod = 1
        unit = 0
        hw_dict = self.verify_from_eths(mod, unit, 0)
        next_dict = {}
        for i in range(1, self.num_slices):
            next_dict = self.verify_from_eths(mod, unit, i)
            for key in next_dict:
                hw_dict[key] = hw_dict.get(key, []) + next_dict[key]
        return hw_dict

    def get_hw_dict_from_pos(self, sw_dict):
        #                         mod, unit, slice, sw_dict
        hw_dict = self.verify_from_pos(1, 0, 0, sw_dict)
        #for i in range(1, num_slices):
        #    next_dict = self.verify_from_pos(i)
        #    for key in next_dict:
        #        hw_dict[key] = hw_dict.get(key, []) + next_dict[key]
        return hw_dict

    def get_trunk_members(self, _tg, _tmt):
        raise Exception("Error: not implemented for Tahoe")

class TahHwVlanCollection:
    def __init__(self, _modList):
        raise Exception("Error: not implemented for Tahoe")

class TahHwStgStpCollection:
    def __init__(self, _modList):
        raise Exception("Error: not implemented for Tahoe")

class TahHwTrunk:
    def __init__(self, _tgid):
        raise Exception("Error: not implemented for Tahoe")

    def get_trunk_membership(self, _modList):
        raise Exception("Error: not implemented for Tahoe")

class TahHwSourceTrunkMapModbase:
    def __init__(self, _mod, _unit, _dmod):
        raise Exception("Error: not implemented for Tahoe")

    def getBase(self):
        raise Exception("Error: not implemented for Tahoe")

class TahHwSourceTrunkMap:
    def __init__(self, _mod, _unit, _dmod, _port):
        mod = _mod
        unit = _unit
        dmod = _dmod
        port = _port

    def getVrfId(self):
        raise Exception("Error: not implemented for Tahoe")
        
    def getL3iifIndex(self):
        return None

    def getSvpValid(self):
        raise Exception("Error: not implemented for Tahoe")

    def getSourceVp(self):
        raise Exception("Error: not implemented for Tahoe")
    
    def getTgid(self):
        raise Exception("Error: not implemented for Tahoe")

    def getPortType(self):
        return 'ethernet'
        raise Exception("Error: not implemented for Tahoe")

class TahHwVlanProfile:
    def __init__(self, slot, unit, _vlanProfilePtr):
        slot = slot
        unit = unit
        vlanProfilePtr = _vlanProfilePtr

    def getLearnDisable(self):
        return 0

class TahHwL3Iif:
    def __init__(self, _slot, _unit, _l3iifIndex):
        slot = _slot
        unit = _unit
        l3iifIndex = _l3iifIndex

    def getVpnId(self):
        raise Exception("Error: not implemented for Tahoe")

class TahHwStgState:
    def __init__(self, _slot, _unit, _stgId):
        slot = _slot
        unit = _unit
        stgId = _stgId

    def getStgState(self, _port):
        ## StgState not valid for Tahoe Platforms
        ## Hardcoding this to 3 to pass _validateStgState
        return 3

    def getEgrStgState(self, _port):
        ## StgState not valid for Tahoe Platforms
        ## Hardcoding this to 3 to pass _validateStgState
        return 3

class TahHwEgrMaskModBase:
    def __init__(self, _mod, _unit, _dmod):
        raise Exception("Error: not implemented for Tahoe")

    def getBase(self):
        raise Exception("Error: not implemented for Tahoe")

class TahHwEgrMask:
    def __init__(self, _mod, _unit, _dmod, _port):
        raise Exception("Error: not implemented for Tahoe")

    def getEgrMask(self):
        raise Exception("Error: not implemented for Tahoe")

class TahHwEgrMaskModBaseTable:
    def __init__(self, _mod, _unit):
        raise Exception("Error: not implemented for Tahoe")

    def getMod(self, _base):
        raise Exception("Error: not implemented for Tahoe")

class TahHwEgrMaskTable:
    def __init__(self, _mod, _unit , _slice):
        #raise Exception("Error: not implemented for Tahoe")
        self.If=tahoe.Interface(_mod,_unit,_print_out=0,_change=0)
        self.slice = _slice

    def getAll(self):
        #raise Exception("Error: not implemented for Tahoe")
        names = []
        intfs = []
        for slice in range(0,self.slice):
            rows = self.If.get_vpcprune(_slice=slice)
            for row in rows:
                mask_temp = row['src_if_mask']   
                bitmask = re.sub("0x|:", "", mask_temp)
                val = int(bitmask,16)
                for offset in range(len(bitmask)*4):
                    mask = 1 << offset
                    if val & mask:
			ifIndex = tahoe.slice_port_to_if_index(1, 0, slice, offset)
            		srcIntf = py_im_get_long_name_from_if_index(ifIndex)
            		srcIntf = getShortIfName(srcIntf)
            		print "[%s]" % srcIntf

class TahHwMacEntry:
    def __init__(self, _mod, _unit, _mac):
        raise Exception("Error: not implemented for Tahoe")

    def getHitDA(self):
        raise Exception("Error: not implemented for Tahoe")
        
    def getHitSA(self):
        raise Exception("Error: not implemented for Tahoe")

    def resetHitDA(self):
        raise Exception("Error: not implemented for Tahoe")

    def resetHitSA(self):
        raise Exception("Error: not implemented for Tahoe")
        
#########################################
# VxLAN registers
#########################################
class TahHwVfi:
    def __init__(self, _mod, _unit, _vfi):
        raise Exception("Error: not implemented for Tahoe")

    def getIpmc(self):
        raise Exception("Error: not implemented for Tahoe")

    def getVxlanGroup(self):
        raise Exception("Error: not implemented for Tahoe")

class TahHwDeviceId:                                                  
    def __init__(self, _mod, _unit):                               
        self.mod = _mod
        self.unit = _unit
    
    # This returns True for some BCM stuff. We aren't BCM, return false
    def getDevId(self):                                            
        return False

    def isChipTridentPlus(self):
        return False
                    
class TahHwSourceVp:
    def __init__(self, _mod, _unit, _vp):
        raise Exception("Error: not implemented for Tahoe")

    def getVfi(self):
        raise Exception("Error: not implemented for Tahoe")

    def getSdTagMode(self):
        raise Exception("Error: not implemented for Tahoe")

    def getCMLFlagsNew(self):
        raise Exception("Error: not implemented for Tahoe")

    def getCMLFlagsMove(self):
        raise Exception("Error: not implemented for Tahoe")

class TahVlanXlateEntry:
    def __init__(self, _mod, _unit, _vlan, _dmod, _port, is_trunk):
        raise Exception("Error: not implemented for Tahoe")

    def getSvpValid(self):
        raise Exception("Error: not implemented for Tahoe")

    def getSourceVp(self):
        raise Exception("Error: not implemented for Tahoe")

class TahHwIngDvpTable:
    def __init__(self, _mod, _unit, _vp):
        raise Exception("Error: not implemented for Tahoe")

    def getNHI(self):
        raise Exception("Error: not implemented for Tahoe")

class TahHwIngL3NextHop:
    def __init__(self, _mod, _unit, _nhi):
        raise Exception("Error: not implemented for Tahoe")

    def getTgid(self):
        raise Exception("Error: not implemented for Tahoe")

    def getT(self):
        raise Exception("Error: not implemented for Tahoe")

    def getPort(self):
        raise Exception("Error: not implemented for Tahoe")

    def getMod(self):
        raise Exception("Error: not implemented for Tahoe")

class TahHwMcList:
    def __init__(self, _mod, _unit, _group):
        raise Exception("Error: not implemented for Tahoe")
