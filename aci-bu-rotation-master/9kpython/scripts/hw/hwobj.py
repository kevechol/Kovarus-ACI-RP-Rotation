#################################################
#
#      File:   inshw.py
#      Name:   
#
#      Description: 
#
#
#
# Copyright (c) 1985-2013, 2015 by cisco Systems, Inc.
# All rights reserved.
#
#################################################

import sys,re,os,collections
from nxos_utils import *
import bcm.bcmhw as bcmhw
import tah.tahhw as tahhw

class HwMod:
    def __init__(self, _mod, _units = None):
        asic_type = get_asic_type()
        if asic_type is 'lac':
            self.obj = tahhw.TahHwMod(_mod, _units)
        elif asic_type is 'dav':
            self.obj = tahhw.TahHwMod(_mod, _units)
        # Broadcom is the default 
        else:
            self.obj = bcmhw.BcmHwMod(_mod, _units)
 
    def get_mod(self):
        return self.obj.get_mod()

    def get_modid(self):
        return self.obj.get_modid()

    def get_units(self):
        return self.obj.get_units()
    
    def get_all_hg_ports(self):                              
        return self.obj.get_all_hg_ports()

class HwPort:
    def __init__(self, _type, _chassis_slot, _unit, _rangerPC, _hw_port, _mac_unit, _mac_pid, _ns_port=255, _hw_usr_port=15, _mods = None, _rng100Gport = False, _slice_num = 0, _port_on_slice = 0, _src_id = 0, _ltl = 0, _hw_name=""):
        #print "Type: %s" % _type
        #print "Chassis Slot: %s" % _chassis_slot
        #print "Unit: %s" % _unit
        #print "RangerPC: %s" % _rangerPC
        #print "Hw Port: %s" % _hw_port
        #print "Mac Unit: %s" % _mac_unit
        #print "Mac PID: %s" % _mac_pid
        #print "NS Port: %s" % _ns_port
        #print "Hw USR port: %s" % _hw_usr_port
        #print "Mods: %s" % _mods
        #print "Ranger100G port: %s" % _rng100Gport
        asic_type = get_asic_type()
        if asic_type is 'lac':
            self.obj = tahhw.TahHwPort(_type, _chassis_slot, _unit, _rangerPC, _hw_port, 
                                   _mac_unit, _mac_pid, _ns_port, _hw_usr_port, _mods, _rng100Gport, _slice_num,
                                   _port_on_slice, _src_id, _ltl, _hw_name, _slice_offset=6)
        elif asic_type is 'dav':
            self.obj = tahhw.TahHwPort(_type, _chassis_slot, _unit, _rangerPC, _hw_port, 
                                   _mac_unit, _mac_pid, _ns_port, _hw_usr_port, _mods, _rng100Gport, _slice_num,
                                   _port_on_slice, _src_id, _ltl, _hw_name, _slice_offset=7)
        # Broadcom is the default 
        else:
            self.obj = bcmhw.BcmHwPort(_type, _chassis_slot, _unit, _rangerPC, _hw_port, 
                                   _mac_unit, _mac_pid, _ns_port, _hw_usr_port, _mods, _rng100Gport)

    def get_hw_port(self):
        return self.obj.get_hw_port()

    def get_hw_name(self):
        return self.obj.get_hw_name()

    def get_hwMemberPorts(self):
        return self.obj.get_hwMemberPorts()

    def get_isRanger(self):
        return self.obj.get_isRanger()

    def get_rangerMemberPorts(self):
        return self.obj.get_rangerMemberPorts()

    # BCM ports have ns_port as 255
    def is_nsport(self):
        return self.obj.is_nsport()

    def get_nsport(self):
        return self.obj.get_nsport()

    def get_counters(self):
        return self.obj.get_counters()

    def get_counters_dict(self):
        return self.obj.get_counters_dict()

    def get_counters_snmp(self):
        return self.obj.get_counters_snmp()

    def get_unit(self):
        return self.obj.get_unit()
 
    def get_counters_snmp_dict(self):
        return self.obj.get_counters_snmp_dict()

    def get_hw_mask_int(self):
        return self.obj.get_hw_mask_int()

    def get_if_hw_name(self):
        return self.obj.get_if_hw_name()

    def get_hw_link_state(self):
        return self.obj.get_hw_link_state()

    def getPortVid(self):
        return self.obj.getPortVid()

    def getIpv4L3EnableBits(self):
        return self.obj.getIpv4L3EnableBits()

    def getIpv4McEnableBits(self):
        return self.obj.getIpv4McEnableBits()

    def getIpmcDoVlanBits(self):
        return self.obj.getIpmcDoVlanBits()

    def getVntagBits(self):
        return self.obj.getVntagBits()
        
    def getMymodidBits(self):
        return self.obj.getMymodidBits()

    def getCmlNewBits(self):
        return self.obj.getCmlNewBits()

    def getCmlMoveBits(self):
        return self.obj.getCmlMoveBits()

    def getVTEnable(self):
        return self.obj.getVTEnable()
    
    def validate_l3_intf(self):
        return self.obj.validate_l3_intf()

class HwVlan:
    def __init__(self, _vlan):
        asic_type = get_asic_type()
        if asic_type is 'lac':
            self.obj = tahhw.TahHwVlan(_vlan, slices=6)
        elif asic_type is 'dav':
            self.obj = tahhw.TahHwVlan(_vlan, slices=2)
        else:
            self.obj = bcmhw.BcmHwVlan(_vlan)
    
    def validate_stp_state(self, _modList, sw_output, sw_output_vp):
        return self.obj.validate_stp_state(_modList, sw_output, sw_output_vp)

    def validate_vlan_membership(self, _modList, _vlan_active_in_sw, _nxosIfList):
        return self.obj.validate_vlan_membership(_modList, _vlan_active_in_sw, _nxosIfList) 

    def get_vlan_membership(self, _modList = None, _egr = False):
        return self.obj.get_vlan_membership(_modList, _egr)
 
    def get_aux_vlan_membership(self, is_fex = False):
        return self.obj.get_aux_vlan_membership(is_fex)

    def get_vlan_stp_state(self, _modList):    
        return self.obj.get_vlan_stp_state(_modList)
    
    def getVlanProfilePtr(self, slot, unit):
        return self.obj.getVlanProfilePtr(slot, unit)

class HwTrunkCollection:
    def __init__(self, _modList, _ifIdxs):
        asic_type = get_asic_type()
        if asic_type is 'lac':
            self.obj = tahhw.TahHwTrunkCollection(_modList, _ifIdxs, num_slices=6)
        elif asic_type is 'dav':
            self.obj = tahhw.TahHwTrunkCollection(_modList, _ifIdxs, num_slices=2)
        else:
            self.obj = bcmhw.BcmHwTrunkCollection(_modList)
    
    def get_trunk_members(self, _tg, _tmt):
        return self.obj.get_trunk_members(_tg, _tmt)

    def validate_pc_membership(self, mods, okList, nokList, ok, nok):
        return self.obj.validate_pc_membership(mods, okList, nokList, ok, nok)

class HwVlanCollection:
    def __init__(self, _modList):
        asic_type = get_asic_type()
        if asic_type is 'lac':
            self.obj = tahhw.TahHwVlanCollection(_modList)
        elif asic_type is 'dav':
            self.obj = tahhw.TahHwVlanCollection(_modList)
        else:
            self.obj = bcmhw.BcmHwVlanCollection(_modList)

class HwStgStpCollection:
    def __init__(self, _modList):
        asic_type = get_asic_type()
        if asic_type is 'lac':
            self.obj = tahhw.TahHwStgStpCollection(_modList)
        elif asic_type is 'dav':
            self.obj = tahhw.TahHwStgStpCollection(_modList)
        else:
            self.obj = bcmhw.BcmHwStgStpCollection(_modList)

class HwTrunk:
    def __init__(self, _tgid):
        asic_type = get_asic_type()
        if asic_type is 'lac':
            self.obj = tahhw.TahHwTrunk(_tgid)
        elif asic_type is 'dav':
            self.obj = tahhw.TahHwTrunk(_tgid)
        else:
            self.obj = bcmhw.BcmHwTrunk(_tgid)

    def get_trunk_membership(self, _modList):
        return self.obj.get_trunk_membership(_modList)

class HwSourceTrunkMapModbase:
    def __init__(self, _mod, _unit, _dmod):
        asic_type = get_asic_type()
        if asic_type is 'lac':
            self.obj = tahhw.TahHwSourceTrunkMapModebase(_mod, _unit, _dmod)
        elif asic_type is 'dav':
            self.obj = tahhw.TahHwSourceTrunkMapModebase(_mod, _unit, _dmod)
        else:
            self.obj = bcmhw.BcmHwSourceTrunkMapModebase(_mod, _unit, _dmod)

    def getBase(self):
        return self.obj.getBase()

class HwSourceTrunkMap:
    def __init__(self, _mod, _unit, _dmod, _port):
        asic_type = get_asic_type()
        if asic_type is 'lac':
            self.obj = tahhw.TahHwSourceTrunkMap(_mod, _unit, _dmod, _port)
        elif asic_type is 'dav':
            self.obj = tahhw.TahHwSourceTrunkMap(_mod, _unit, _dmod, _port)
        else:
            self.obj = bcmhw.BcmHwSourceTrunkMap(_mod, _unit, _dmod, _port)

    def getVrfId(self):
        return self.obj.getVrfId()

    def getL3iifIndex(self):
        return self.obj.getL3iifIndex()

    def getSvpValid(self):
        return self.obj.getSvpValid()

    def getSourceVp(self):
        return self.obj.getSourceVp()

    def getTgid(self):
        return self.obj.getTgid()

    def getPortType(self):
        return self.obj.getPortType()

class HwVlanProfile:
    def __init__(self, slot, unit, _vlanProfilePtr):
        asic_type = get_asic_type()
        if asic_type is 'lac':
            self.obj = tahhw.TahHwVlanProfile(slot, unit, _vlanProfilePtr)
        elif asic_type is 'dav':
            self.obj = tahhw.TahHwVlanProfile(slot, unit, _vlanProfilePtr)
        else:
            self.obj = bcmhw.BcmHwVlanProfile(slot, unit, _vlanProfilePtr)

    def getLearnDisable(self):
        return self.obj.getLearnDisable()

class HwL3Iif:
    def __init__(self, _slot, _unit, _l3iifIndex):
        asic_type = get_asic_type()
        if asic_type is 'lac':
            self.obj = tahhw.TahHwL3Iif(_slot, _unit, _l3iifIndex)
        elif asic_type is 'dav':
            self.obj = tahhw.TahHwL3Iif(_slot, _unit, _l3iifIndex)
        else:
            self.obj = bcmhw.BcmHwL3Iif(_slot, _unit, _l3iifIndex)
    def getVpnId(self):
        return self.obj.getVpnId()
        
class HwStgState:
    def __init__(self, _slot, _unit, _stgId):
        asic_type = get_asic_type()
        if asic_type is 'lac':
            self.obj = tahhw.TahHwStgState(_slot, _unit, _stgId)
        elif asic_type is 'dav':
            self.obj = tahhw.TahHwStgState(_slot, _unit, _stgId)
        else:
            self.obj = bcmhw.BcmHwStgState(_slot, _unit, _stgId)

    def getStgState(self, _port):
        return self.obj.getStgState(_port)

    def getEgrStgState(self, _port):
        return self.obj.getEgrStgState(_port)

class HwEgrMaskModBase:
    def __init__(self, _mod, _unit, _dmod):
        asic_type = get_asic_type()
        if asic_type is 'lac':
            self.obj = tahhw.TahHwEgrMaskModBase(_mod, _unit, _dmod)
        elif asic_type is 'dav':
            self.obj = tahhw.TahHwEgrMaskModBase(_mod, _unit, _dmod)
        else:
            self.obj = bcmhw.BcmHwEgrMaskModBase(_mod, _unit, _dmod)

    def getBase(self):
        return self.obj.getBase()

class HwEgrMask:
    def __init__(self, _mod, _unit, _dmod, _port):
        asic_type = get_asic_type()
        if asic_type is 'lac':
            self.obj = tahhw.TahHwEgrMask(_mod, _unit, _dmod, _port)
        elif asic_type is 'dav':
            self.obj = tahhw.TahHwEgrMask(_mod, _unit, _dmod, _port)
        else:
            self.obj = bcmhw.BcmHwEgrMask(_mod, _unit, _dmod, _port)

    def getEgrMask(self):
        return self.obj.getEgrMask()

class HwEgrMaskModBaseTable:
    def __init__(self, _mod, _unit):
        asic_type = get_asic_type()
        if asic_type is 'lac':
            self.obj = tahhw.TahHwEgrMaskModBaseTable(_mod, _unit)
        elif asic_type is 'dav':
            self.obj = tahhw.TahHwEgrMaskModBaseTable(_mod, _unit)
        else:
            self.obj = bcmhw.BcmHwEgrMaskModBaseTable(_mod, _unit)
    
    def getMod(self, _base):
        return self.obj.getMod(_base)

class HwEgrMaskTable:
    def __init__(self, _mod, _unit):
        asic_type = get_asic_type()
        if asic_type is 'lac':
            self.obj = tahhw.TahHwEgrMaskTable(_mod,_unit,6)
        elif asic_type is 'dav':
            self.obj = tahhw.TahHwEgrMaskTable(_mod,_unit,2)
        else:
            self.obj = bcmhw.BcmHwEgrMaskTable(_mod,_unit)
    
    def getAll(self):
        return self.obj.getAll()

class HwMacEntry:
    def __init__(self, _mod, _unit, _mac):
        asic_type = get_asic_type()
        if asic_type is 'lac':
            self.obj = tahhw.TahHwMacEntry(_mod, _unit, _mac)
        elif asic_type is 'dav':
            self.obj = tahhw.TahHwMacEntry(_mod, _unit, _mac)
        else:
            self.obj = bcmhw.BcmHwMacEntry(_mod, _unit, _mac)
    
    def getHitDA(self):
        return self.obj.getHitDA()
        
    def getHitSA(self):
        return self.obj.getHitSA()

    def resetHitDA(self):
        return self.obj.resetHitDA()

    def resetHitSA(self):
        return self.obj.resetHitSA()
        
class HwVfi:
    def __init__(self, _mod, _unit, _vfi):
        asic_type = get_asic_type()
        if asic_type is 'lac':
            self.obj = tahhw.TahHwVfi(_mod, _unit, _vfi)
        elif asic_type is 'dav':
            self.obj = tahhw.TahHwVfi(_mod, _unit, _vfi)
        else:
            self.obj = bcmhw.BcmHwVfi(_mod, _unit, _vfi)
    
    def getIpmc(self):
        return self.obj.getIpmc()

    def getVxlanGroup(self):
        return self.obj.getVxlanGroup()

class HwDeviceId:                                                  
    def __init__(self, _mod, _unit):  
        asic_type = get_asic_type()
        if asic_type is 'lac':
            self.obj = tahhw.TahHwDeviceId(_mod, _unit)
        elif asic_type is 'dav':
            self.obj = tahhw.TahHwDeviceId(_mod, _unit)
        else:
            self.obj = bcmhw.BcmHwDeviceId(_mod, _unit)

    def getDevId(self):                                            
        return self.obj.getDevId()

    def isChipTridentPlus(self):
        return self.obj.isChipTridentPlus()
                    
class HwSourceVp:
    def __init__(self, _mod, _unit, _vp):
        asic_type = get_asic_type()
        if asic_type is 'lac':
            self.obj = tahhw.TahHwSourceVp(_mod, _unit, _vp)
        elif asic_type is 'dav':
            self.obj = tahhw.TahHwSourceVp(_mod, _unit, _vp)
        else:
            self.obj = bcmhw.BcmHwSourceVp(_mod, _unit, _vp)
    
    def getVfi(self):
        return self.obj.getVfi()

    def getSdTagMode(self):
        return self.obj.getSdTagMode()

    def getCMLFlagsNew(self):
        return self.obj.getCMLFlagsNew()

    def getCMLFlagsMove(self):
        return self.obj.getCMLFlagsMove()

class VlanXlateEntry:
    def __init__(self, _mod, _unit, _vlan, _dmod, _port, is_trunk):
        asic_type = get_asic_type()
        if asic_type is 'lac':
            self.obj = tahhw.TahVlanXlateEntry(_mod, _unit, _vlan, _dmod, _port, is_trunk)
        elif asic_type is 'dav':
            self.obj = tahhw.TahVlanXlateEntry(_mod, _unit, _vlan, _dmod, _port, is_trunk)
        else:
            self.obj = bcmhw.BcmVlanXlateEntry(_mod, _unit, _vlan, _dmod, _port, is_trunk)
    
    def getSvpValid(self):
        return self.obj.getSvpValid()

    def getSourceVp(self):
        return self.obj.getSourceVp()

class HwIngDvpTable:
    def __init__(self, _mod, _unit, _vp):
        asic_type = get_asic_type()
        if asic_type is 'lac':
            self.obj = tahhw.TahHwIngDvpTable(_mod, _unit, _vp)
        elif asic_type is 'dav':
            self.obj = tahhw.TahHwIngDvpTable(_mod, _unit, _vp)
        else:
            self.obj = bcmhw.BcmHwIngDvpTable(_mod, _unit, _vp)
    
    def getNHI(self):
        return self.obj.getHNI()

class HwIngL3NextHop:
    def __init__(self, _mod, _unit, _nhi):
        asic_type = get_asic_type()
        if asic_type is 'lac':
            self.obj = tahhw.TahHwIngL3NextHop(_mod, _unit, _nhi)
        elif asic_type is 'dav':
            self.obj = tahhw.TahHwIngL3NextHop(_mod, _unit, _nhi)
        else:
            self.obj = bcmhw.BcmHwIngL3NextHop(_mod, _unit, _nhi)
    
    def getTgid(self):
        return self.obj.getTgid()

    def getT(self):
        return self.obj.getT()

    def getPort(self):
        return self.obj.getPort()

    def getMod(self):
        return self.obj.getMod()

class HwMcList:
    def __init__(self, _mod, _unit, _group):
        asic_type = get_asic_type()
        if asic_type is 'lac':
            self.obj = tahhw.TahHwMcList(_mod, _unit, _group)
        elif asic_type is 'dav':
            self.obj = tahhw.TahHwMcList(_mod, _unit, _group)
        else:
            self.obj = bcmhw.BcmHwMcList(_mod, _unit, _group)
