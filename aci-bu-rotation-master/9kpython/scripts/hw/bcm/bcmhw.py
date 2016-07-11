#################################################
#
#      File:   inshw.py
#      Name:   
#
#      Description: 
#
#
#
# Copyright (c) 1985-2013, 2015,2016 by cisco Systems, Inc.
# All rights reserved.
#
#################################################

import sys,re,os,collections
from nxos_utils import *
from libbcmshell import *
from sets import Set
import nxos

cmd_pfx = {}
cmd_pfx["vp vlan membership"] = "search ing_vp_vlan_membership VLAN="
cmd_pfx["egr vp vlan membership"] = "search egr_vp_vlan_membership VLAN="
cmd_pfx["port counters"] = "show counter all "
cmd_pfx["port stats"] = "show stat "
cmd_pfx["vlan membership"] = "d vlan  "
cmd_pfx["egr vlan membership"] = "d egr_vlan  "
cmd_pfx["vlan info"] = "d chg vlan  "
cmd_pfx["trunk info"] = "d trunk_group "
cmd_pfx["vlan"] = "d vlan "
cmd_pfx["port"] = "d port "
cmd_pfx["srcTrunkMap"] = "d source_trunk_map "
cmd_pfx["srcTrunkMapModbase"] = "d source_trunk_map_modbase "
cmd_pfx["l3egress"] = "l3 egress show"
cmd_pfx["ing_next_hop"] = "d ing_l3_next_hop "
cmd_pfx["stg membership"] = "d vlan_stg "
cmd_pfx["egr stg membership"] = "d egr_vlan_stg "
cmd_pfx["port bitmap"] = "pbmp "
cmd_pfx["vlanProfile"] = "d vlan_profile "
cmd_pfx["l3iif"] = "d l3_iif  "
cmd_pfx["my_station_tcam"] = "d chg my_station_tcam "
cmd_pfx["trunk membership"] = "d trunk_member " 
cmd_pfx["egrMask"] = "d egr_mask "
cmd_pfx["egrMaskModBase"] = "d egr_mask_modbase "
cmd_pfx["egrMaskChg"] = "d chg egr_mask "
cmd_pfx["egrMaskModBaseChg"] = "d chg egr_mask_modbase "
cmd_pfx["searchL2Entry"] = "search l2_entry mac_addr="
cmd_pfx["dumpL2Entry"] = "d l2_entry "
cmd_pfx["modL2Entry"] = "mod l2_entry "
cmd_pfx["vfi"] = "d vfi "
cmd_pfx["source_vp"] = "d source_vp "
cmd_pfx["searchVlanXlate"] = "search vlan_xlate "
cmd_pfx["ingDvpTable"] = "d ing_dvp_table "
cmd_pfx["mc_show"] = "mc show "
cmd_pfx["ns dump"] = "deb hardware internal ns dump "
cmd_pfx["vlan state"] = "mth_lux_slva_DHS_VlanStateTable_memif_data "
from threading import Thread

def find_dmod_dport_in_trunk_member_list(tmembers, dmod, dport):
    if (dmod,dport) in tmembers:
        return True
    return False

class BcmHwMod:
    def __init__(self, _mod, _units = None):
        self.mod = _mod
        self.units = _units
        self.modid = {}
        output = runBcmCmd(self.mod, 0, "show unit")
    
        lines = output.split("\n")
        count = 0
        for line in lines:
            if "Unit" in line:
                count = count + 1
        self.units = count
        for i in range(0, self.units):
            output = runBcmCmd(self.mod, i, "stkm")
            if "module id" not in output:
                continue
            y = re.search("id [0-9]+", output)
            x = int(re.search("[0-9]+", y.group(0)).group(0))
            self.modid[i] = x

    def get_mod(self):
        return self.mod

    def get_modid(self):
        return self.modid

    def get_units(self):
        return self.units

    def get_all_hg_ports(self):                              
        hgports = []                                         
        for unit in range(0, self.units):                    
            lines = runBcmCmd(self.mod, unit, "phy info").split("\n")
            for line in lines:                                       
                if line is None or "hg" not in line:                 
                    continue                                         
                y = re.search(r'\s*hg([0-9]+)\(\s*([0-9]+)\).*', line)
                hgno = int(y.group(1))                                
                bcmport = int(y.group(2))                               
                hgports.append((unit, hgno, bcmport))                   
                                                                         
        return hgports               


def isUnitTomahawk(iftype, mymod, myunit):
    #Fex is not supported on Tomahawk yet 
    if mymod > 32:
        return False
    if iftype == IfType.PortChannel: 
        return False
    str = runBcmCmd(mymod, myunit, "show unit")
    chips = str.splitlines()
    for line in chips:
        unit = int(line.split()[1].strip())
        if ( (unit == myunit) and (line.find("BCM56960") != -1) ):
            # Tomahawk unit
            return True
    return False


"""HwPort class uses bcm interface to obtain port level information.
   Properties:
   hwMemberPorts: dictionary of trunk members seen in hardware for each (module, unit)
"""
class BcmHwPort:
    def __init__(self, _type, _chassis_slot, _unit, _rangerPC, _hw_port, _mac_unit, _mac_pid, _ns_port=255, _hw_usr_port=15, _mods = None, _rng100Gport = False):
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
        self.hw_name = None
        self.isRanger = _rangerPC
        self.rangerMemberPorts = None
        self.mac_unit = _mac_unit
        self.mac_pid = _mac_pid
        self.isTomahawk = isUnitTomahawk(_type, self.mod,self.unit)


        if self.isRanger:
            self.rangerPort = BcmHwPort(IfType.Ethernet, self.mod, self.mac_unit, False, self.mac_pid, 0, 0, _rng100Gport = True)
    
        if _type == IfType.Ethernet:
            if self.isTomahawk:
                out = runBcmCmd(self.mod, self.unit, "phy info")
                port_phyinfo = out.splitlines()
                for line in port_phyinfo:
                    tokens = line.split("(")
                    if (len(tokens) < 2):
                        continue

                    line_port_num = int(tokens[1].split(")")[0].strip())
                    if(line_port_num == self.hw_port):
                        self.hw_name = tokens[0].strip()
            else:
                out = runBcmCmd(self.mod, self.unit, "pbmp port " + str(self.hw_port)).strip().split(' ')
                self.hw_name = out[3]
        elif _type == IfType.Internal:
            if self.isTomahawk:
                out = runBcmCmd(self.mod, self.unit, "phy info")
                port_phyinfo = out.splitlines()
                for line in port_phyinfo:
                    tokens = line.split("(")
                    if (len(tokens) < 2):
                        continue

                    line_port_num = int(tokens[1].split(")")[0].strip())
                    if(line_port_num == self.hw_port):
                        self.hw_name = tokens[0].strip()
            else:
                out = runBcmCmd(self.mod, self.unit, "pbmp port " + str(self.hw_port)).strip().split(' ')
                self.hw_name = out[3]
        elif _type == IfType.Cpu:
            self.hw_name = "cpu0"
        elif _type == IfType.Fex:
            self.hw_name = ""
            return

        if self.isRanger:
            self.hwMemberPorts[(self.mod, self.unit)] = []
            strout = runBcmCmd((self.mod), int(self.unit), cmd_pfx["trunk info"] + str(self.hw_port))
            lines = strout.strip("\n")
            obj = createHwTableObject(strout)
            self.hwPcTables[(self.mod, self.unit)] = []
            self.hwMemberTables[(self.mod, self.unit)] = []
            self.hwPcTables[(self.mod, self.unit)].append( obj )

            #get base ptr and trunk size.
            key = "TRUNK_GROUP.ipipe0[" + str(self.hw_port) + "]"
            base_ptr = obj.table[key]['BASE_PTR']
            bp = int(base_ptr, 16)
            tg_size = (int(obj.table[key]['TG_SIZE'],16) + 1)

            strout = runBcmCmd((self.mod), int(self.unit), cmd_pfx["trunk membership"] + 
                                base_ptr + " " + str(tg_size))
            lines = strout.strip("\n")
            obj = createHwTableObject(strout)
            self.hwMemberTables[(self.mod, self.unit)].append( obj )
            for c in range(0, tg_size):
                bs = str(bp + c)
                key = "TRUNK_MEMBER.ipipe0[" + bs + "]"
                self.hwMemberPorts[(self.mod, self.unit)].append((int(obj.table[key]['PORT_NUM'], 16),
                                    int(obj.table[key]['MODULE_ID'], 16)))
            self.rangerMemberPorts = []
            for (child_port, child_dmod) in self.hwMemberPorts[(self.mod, self.unit)]:
                self.rangerMemberPorts.append(BcmHwPort(IfType.Ethernet, _chassis_slot, 
                                              _unit, False, child_port, 0, 0))    
            out = runBcmCmd(self.mod, self.unit, "pbmp port " + 
                            str(self.rangerMemberPorts[0].hw_port)).strip().split(' ')
            self.hw_name = out[3]
            return


        # get the members programmed.
        if _type == IfType.PortChannel:
            # _mods must have been given for it.
            for m in _mods:
                for u in range(0, m.units):
                    self.hwMemberPorts[(m.mod, u)] = []
                    strout = runBcmCmd((m.mod), int(u), cmd_pfx["trunk info"] + str(self.hw_port))
                    lines = strout.strip("\n")
                    obj = createHwTableObject(strout)
                    if (m.mod, u) not in self.hwPcTables.keys():
                        self.hwPcTables[(m.mod, u)] = []
                        self.hwMemberTables[(m.mod, u)] = []
                    self.hwPcTables[(m.mod, u)].append( obj )
            
                    #get base ptr and trunk size.
                    key = "TRUNK_GROUP.ipipe0[" + str(self.hw_port) + "]"
                    base_ptr = obj.table[key]['BASE_PTR']
                    bp = int(base_ptr, 16)
                    tg_size = (int(obj.table[key]['TG_SIZE'],16) + 1)
                 
                    strout = runBcmCmd((m.mod), int(u), cmd_pfx["trunk membership"] + base_ptr + " " + str(tg_size))
                    lines = strout.strip("\n")
                    obj = createHwTableObject(strout)
                    self.hwMemberTables[(m.mod, u)].append( obj )
                    for c in range(0, tg_size):
                        bs = str(bp + c)
                        key = "TRUNK_MEMBER.ipipe0[" + bs + "]"
                        self.hwMemberPorts[(m.mod, u)].append((int(obj.table[key]['PORT_NUM'], 16), int(obj.table[key]['MODULE_ID'], 16)))
        elif not _rng100Gport:
            # cache the port table for ethernet ports.
            strout = runBcmCmd((self.mod), self.unit, cmd_pfx["port"] + str(self.hw_port))
            lines = strout.strip("\n")
            self.hwPortTable = createHwTableObject(strout)
            if 0 != self.hw_port:            
                self.hw_mask_int = int(runBcmCmd(self.mod, self.unit, cmd_pfx["port bitmap"] + self.hw_name).split()[0], 16)

    def get_isRanger(self):
        return self.isRanger

    def get_rangerMemberPorts(self):
        return self.rangerMemberPorts

    def get_hwMemberPorts(self):
        return self.hwMemberPorts

    def get_hw_mask_int(self):
        return self.hw_mask_int

    def get_hw_name(self):
        return self.hw_name

    def get_hw_port(self):
        return self.hw_port

    def get_unit(self):
        return self.unit
 
    # BCM ports have ns_port as 255
    def is_nsport(self):
        return (self.ns_port != 255)

    def get_nsport(self):
        return (self.ns_port)

    def get_hwport(self):
        return (self.hw_port)

    def get_counters(self):
        if (self.isRanger):
            return self.rangerPort.get_counters()
        strout = runBcmCmd((self.mod), self.unit, cmd_pfx["port counters"] + (self.hw_name))
        lines = strout.split("\n")
        #self.counters = createHwTableObject(strout)

        return lines

    def get_counters_dict(self):
        strout = runBcmCmd((self.mod), self.unit, cmd_pfx["port counters"] + (self.hw_name))
        lines = strout.split("\n")
        counters = collections.OrderedDict()
        #print "#of lines for ", self.longName, " = ", len(lines)
        for line in lines:
            g = re.search(r'([^.]*)[.][A-Za-z0-9()/]+\s*:\s*([0-9,]*)\s*(.*)', line)
            if g is None:   #last line of output has white spaces, ignore
                continue
            #print g.group(1), "=", g.group(2)
            counters[g.group(1)] = int(g.group(2).replace(',', ''))
        return counters

    def get_counters_snmp(self):
        strout = runBcmCmd((self.mod), self.unit, cmd_pfx["port stats"] + (self.hw_name) + " all")
        lines = strout.split("\n")
        #self.counters = createHwTableObject(strout)

        return lines

    def get_counters_snmp_dict(self):
        strout = runBcmCmd((self.mod), self.unit, cmd_pfx["port stats"] + (self.hw_name) + " all")
        lines = strout.split("\n")
        counters = collections.OrderedDict()
        range = len(lines) 
        for line in lines[1:range-1]:
            g = re.match(r'\s*-[.]*', line, re.M)
            if g:         #Ignore lines begin with - which are unsupported counters
                continue     
            g = re.match(r'^SHOW: Statistics for', line, re.M)
            if g:         #Ignore lines begin with - which are unsupported counters
                continue     
            g = re.search(r'\s*([0-9,a-zA-Z]+)\s*([^\s]*)', line)
            if g is None:   #last line of output has white spaces, ignore
                continue
            #print g.group(2), "=", g.group(1)
            numstr = g.group(1).replace(',', '') 
            if numstr.upper().startswith('0X'):
                counters[g.group(2)] = int(numstr, 16) 
            else:
                counters[g.group(2)] = int(numstr)
        return counters

    def get_if_hw_name(self):
        return self.hw_name

    def get_hw_link_state(self):
        if self.isRanger:
            return self.rangerPort.get_hw_link_state()
        output = runBcmCmd(self.mod, self.unit, "ps " + self.hw_name).split("\n")
        for o in output:
            if self.hw_name in o:
                break

        if o is not None and "up" in o:
            return 1
        
        return 0

    def getPortVid(self):
        if self.isRanger:
            return self.rangerMemberPorts[0].getPortVid()
        _portKey = 'PORT.ipipe0[' + str(self.hw_port) + ']'
        return int(self.hwPortTable.table[_portKey]['PORT_VID'], 16)

    def getIpv4L3EnableBits(self):
        if self.isRanger:
            return self.rangerMemberPorts[0].getIpv4L3EnableBits()
        _portKey = 'PORT.ipipe0[' + str(self.hw_port) + ']'
        return int(self.hwPortTable.table[_portKey]['V4L3_ENABLE'])

    def getIpv4McEnableBits(self):
        if self.isRanger:
            return self.rangerMemberPorts[0].getIpv4McEnableBits()
        _portKey = 'PORT.ipipe0[' + str(self.hw_port) + ']'
        return int(self.hwPortTable.table[_portKey]['V4IPMC_ENABLE'])

    def getIpmcDoVlanBits(self):
        if self.isRanger:
            return self.rangerMemberPorts[0].getIpmcDoVlanBits()
        _portKey = 'PORT.ipipe0[' + str(self.hw_port) + ']'
        return int(self.hwPortTable.table[_portKey]['IPMC_DO_VLAN'])

    def getVntagBits(self):
        if self.isRanger:
            return self.rangerMemberPorts[0].getVntagBits()
        _portKey = 'PORT.ipipe0[' + str(self.hw_port) + ']'
        return int(self.hwPortTable.table[_portKey]['DISCARD_IF_VNTAG_PRESENT'])

    def getMymodidBits(self):
        if self.isRanger:
            return self.rangerMemberPorts[0].getMymodidBits()
        _portKey = 'PORT.ipipe0[' + str(self.hw_port) + ']'
        return int(self.hwPortTable.table[_portKey]['MY_MODID'])

    def getCmlNewBits(self):
        if self.isRanger:
            return self.rangerMemberPorts[0].getCmlNewBits()
        _portKey = 'PORT.ipipe0[' + str(self.hw_port) + ']'
        return int(self.hwPortTable.table[_portKey]['CML_FLAGS_NEW'])

    def getCmlMoveBits(self):
        if self.isRanger:
            return self.rangerMemberPorts[0].getCmlMoveBits()
        _portKey = 'PORT.ipipe0[' + str(self.hw_port) + ']'
        return int(self.hwPortTable.table[_portKey]['CML_FLAGS_MOVE'])

    def getVTEnable(self):
        if self.isRanger:
            return self.rangerMemberPorts[0].getVTEnable()
        _portKey = 'PORT.ipipe0[' + str(self.hw_port) + ']'
        return int(self.hwPortTable.table[_portKey]['VT_ENABLE'])

    def validate_l3_intf(self):
        _rc = True

        def _validateL3Vlan(self):
            if (self.getPortVid() != 0xfff) :
                return False

            return True

        def _validateCmlFlags(self):
            _rc = True

            if (self.getPortVid() == 0xfff):
                _hwVlanTable = BcmHwVlan(4095)
                _vlanProfilePtr = _hwVlanTable.getVlanProfilePtr(self.mod, self.unit)
                _hwVlanProfile = BcmHwVlanProfile(self.mod, self.unit, _vlanProfilePtr)

                if (_hwVlanProfile.getLearnDisable() == 1):
                    return True
                else:
                    return False

            if ( self.getCmlNewBits() != 0 ):
                _rc = False

            if ( self.getCmlMoveBits() != 0 ):
                _rc = False
            return _rc

        def _validateV4EnableBits(self):
            _rc = True
            if ( self.getIpv4L3EnableBits() != 1 ):
                _rc = False

            if ( self.getIpv4McEnableBits() != 1 ):
                _rc = False

            check_mod = nxos.cli('show module')
            if not re.search('N3K',check_mod):
               if ( self.getIpmcDoVlanBits() != 1 ):
                   _rc = False

            return _rc


        def _validateRpfSettings(self):
        ## TBD
            print "Rpf Setting failed for port" + self.shortName
            return False

        def _validateVpnId(self):
            ( _, _swVrfId ) = py_eltm_get_ifindex_vrf_id(self.ifindex, self.vdc)
            if ( self.hwL3iif.getVpnId() != _swVrfId ):
                return False
            return True


        def _validateStgState(self):
            #TODO: can't get sw_link_state here? need ifindex to lookup
            #validate stg state only if link is up.
            #if self.get_sw_link_state() == 0:
            #    return True
            
            # TODO PD
            if self.isRanger:
                for rngMbr in self.rangerMemberPorts:
                    if (self.hwStgState.getStgState(rngMbr.hw_port) != 3 ):
                        return False
                    if ( self.hwStgState.getEgrStgState(rngMbr.hw_port) != 3 ):
                        return False
            else:
                if ( self.hwStgState.getStgState(self.hw_port) != 3 ):
                    return False
                if ( self.hwStgState.getEgrStgState(self.hw_port) != 3 ):
                    return False
            return True

        ##TODO: sourceTrunkMap and hwL3iif not used in this check? were causing errors
        #self.sourceTrunkMap = BcmHwSourceTrunkMap(self.mod, self.unit, self.dmod, self.hw_port)
        #self.hwL3iif = BcmHwL3Iif(self.mod, self.unit, self.sourceTrunkMap.getL3iifIndex())
        self.hwStgState = BcmHwStgState(self.mod, self.unit, 0)
        failures = ''


        if ( _validateL3Vlan(self) == False ):
            failures.append("L3 Vlan validation failed")
            _rc = False

        # Check that learning bits are turned off
        if ( _validateCmlFlags(self) == False ):
            failures.append("CML Flags validation failed")
            _rc = False

        # Check that IPv4 is enabled
        if ( _validateV4EnableBits(self) == False ):
            failures.append("v4 Flags validation failed")
            _rc = False

        # Check that STG state is forwarding for Vlan 4095
        if ( _validateStgState(self) == False ):
            failures.append("Stg check failed")
            _rc = False

        print failures

        return _rc 


class BcmHwVlan:
    def __init__(self, _vlan):
        self.vlan = _vlan

    def get_vlan_membership(self, _modList = None, _egr = False):
        output = {} 
        vps = [] 
        egr_vps = [] 
        vlan_id = self.vlan
        for mod in _modList:
            for unit in range(0, mod.units):

                #FM Modid is ZERO and for that we dont check vlan membership.
                if mod.hwMod.get_modid()[unit] == 0:
                    continue

                if _egr == False:
                    vlan_mem_str = runBcmCmd(mod.mod, unit, cmd_pfx["vlan membership"] + str(self.vlan))
                    obj = createHwTableObject(vlan_mem_str)
                    if obj.table.__len__() is 0:
                        return output
                    tagged = obj.table["VLAN.ipipe0[%d]"%vlan_id]['ING_PORT_BITMAP']
                    untagged = tagged

                    hwDeviceId = BcmHwDeviceId(mod.mod,unit)
                    #On Trident Plus platform ing_vp_vlan_membership is not defined.
                    #Hence avoid checking this register in trident plus platform
                    if (hwDeviceId.isChipTridentPlus() is not True):
                        # read up ing_vp_vlan_membership for this vlan.
                        vlan_mem_str = runBcmCmd(mod.mod, unit, cmd_pfx["vp vlan membership"] + str(self.vlan))
                        obj = createHwTableObject(vlan_mem_str)
                        if obj.table.__len__() is not 0:
                            for e in obj.table:
                                vps.append(int(obj.table[e]['VP'], 16))

                else:
                    vlan_mem_str = runBcmCmd(mod.mod, unit, cmd_pfx["egr vlan membership"] + str(self.vlan))
                    obj = createHwTableObject(vlan_mem_str)
                    if obj.table.__len__() is 0:
                        return output
                    tagged = obj.table["EGR_VLAN.epipe0[%d]"%vlan_id]['PORT_BITMAP']
                    untagged = obj.table["EGR_VLAN.epipe0[%d]"%vlan_id]['UT_PORT_BITMAP']

                    hwDeviceId = BcmHwDeviceId(mod.mod,unit)
                    #On Trident Plus platform ing_vp_vlan_membership is not defined.
                    #Hence avoid checking this register in trident plus platform
                    if (hwDeviceId.isChipTridentPlus() is not True):
                        vlan_mem_str = runBcmCmd(mod.mod, unit, cmd_pfx["egr vp vlan membership"] + str(self.vlan))
                        obj = createHwTableObject(vlan_mem_str)
                        if obj.table.__len__() is not 0:
                            for e in obj.table:
                               egr_vps.append(int(obj.table[e]['VP'],16))

                if (mod.mod, unit) not in output.keys():
                    output[(mod.mod,unit)] = []
                output[(mod.mod,unit)] = (tagged, [], untagged, [], vps, egr_vps)

        #get list of xe ports here.
        return output

    def validate_stp_state(self, _modList, sw_output, sw_output_vp):
        (hw_output, hw_egr_output, hw_vp, hw_egr_vp, ns_cbl_state) = self.get_vlan_stp_state(_modList = _modList)

        ok = []
        nok = []
        for (m,u) in sw_output.keys():
            for i in sw_output[(m,u)]:
                (ifs, state) = sw_output[(m,u)][i]
                    
                if ifs.hwIf.get_isRanger():
                    rngOK = True
                    for rng in ifs.hwIf.get_rangerMemberPorts():
                        if (m,u) in hw_output.keys() and rng.hw_port in hw_output[(m,u)].keys() \
                          and state == hw_output[(m,u)][rng.hw_port]:
                            if (m,u) in hw_egr_output.keys() and rng.hw_port in hw_egr_output[(m,u)].keys() \
                              and state == hw_egr_output[(m,u)][rng.hw_port]:
                                pass
                            else:
                               rngOK = False
                        else:
                            rngOK = False
                    if rngOK:
                        ok.append(ifs)
                    else:
                        nok.append(ifs)

                elif ifs.fex == False:
                    if ifs.hwIf.is_nsport():
                        #frontPort = ifs.shortName.split("/")[-1]
                        ns_port = ifs.hwIf.get_nsport()
                        if (m,u) in ns_cbl_state.keys():
                            #get front panel to NS port mapping
                            #ns_port_map_dict = getNSPortMappingDict(m)
                            #if ns_port_map_dict[frontPort]:
                            if ns_port >= 0:
                                #mask = 1 << int(ns_port_map_dict[frontPort])
                                mask = 1 << ns_port
                                cbl_state = int(ns_cbl_state[(m,u)][self.vlan], 16)
                                if state == "FWD":
                                    if cbl_state & mask:
                                        #SW state == FWD and HW state == FWD
                                        ok.append(ifs)
                                    else:
                                        #SW state == FWD and HW state == !FWD
                                        nok.append(ifs)
                                else:
                                    #SW state == !FWD and HW state == FWD
                                    if cbl_state  & mask:
                                        nok.append(ifs)
                                    #SW state == !FWD and HW state == !FWD
                                    else: 
                                        ok.append(ifs)
                        continue

                    if (m,u) in hw_output.keys() and ifs.hwIf.get_hw_port() in hw_output[(m,u)].keys() \
                      and state == hw_output[(m,u)][ifs.hwIf.get_hw_port()]:
                        if (m,u) in hw_egr_output.keys() and ifs.hwIf.get_hw_port() in hw_egr_output[(m,u)].keys() \
                          and state == hw_egr_output[(m,u)][ifs.hwIf.get_hw_port()]:
                            ok.append(ifs)
                        else:
                            nok.append(ifs)
                    else:
                        nok.append(ifs)

        for (m,u) in sw_output_vp.keys():
            for i in sw_output_vp[(m,u)]:
                (ifs, state) = sw_output_vp[(m,u)][i]
                if (m,u) in hw_output.keys() and ifs.vp in hw_vp[(m,u)].keys() and state == hw_vp[(m,u)][(ifs.vp)]:
                    if (m,u) in hw_egr_output.keys() and ifs.vp in hw_egr_vp[(m,u)].keys() \
                      and state == hw_egr_vp[(m,u)][(ifs.vp)]:
                        ok.append(ifs)
                    else:
                        nok.append(ifs)
                else:
                    out = nxos_utils.runVshCmd("show running-config interface " + ifs.shortName)
                    if "switchport mode private-vlan" in out:
                        out = nxos_utils.runVshCmd("show running-config vlan " + str(self.vlan))
                        if "private-vlan" in out:
                            ok.append(ifs)
                        else: 
                            nok.append(ifs)
                    else:
                        nok.append(ifs)

        return (ok, nok)

    def validate_vlan_membership(self, _modList = None, vlan_active_in_sw = False, _intfList = []):
        ing_ifidxs = []
        egr_ifidxs = []
        ing_vps = []
        egr_vps = []
        vlan_id = self.vlan
        nok = []
        ok = []
        output = {}
        for mod in _modList:
            for unit in range(0, mod.units):

                #FM Modid is ZERO and for that we dont check vlan membership.
                if mod.hwMod.get_modid()[unit] == 0:
                    continue

                #ingress
                vlan_mem_str = runBcmCmd(mod.mod, unit, cmd_pfx["vlan membership"] + str(self.vlan))
                obj = createHwTableObject(vlan_mem_str)
                if len(obj.table) == 0:
                    continue
                ing_tagged = obj.table["VLAN.ipipe0[%d]"%vlan_id]['ING_PORT_BITMAP']
                ing_untagged = ing_tagged

                hwDeviceId = BcmHwDeviceId(mod.mod,unit)
                #On Trident Plus platform ing_vp_vlan_membership is not defined.
                #Hence avoid checking this register in trident plus platform
                if (hwDeviceId.isChipTridentPlus() is not True):
                    # read up ing_vp_vlan_membership for this vlan.
                    vlan_mem_str = runBcmCmd(mod.mod, unit, cmd_pfx["vp vlan membership"] + str(self.vlan))
                    obj = createHwTableObject(vlan_mem_str)
                    if obj.table.__len__() is not 0:
                        for e in obj.table:
                            ing_vps.append(int(obj.table[e]['VP'], 16))
                
                #egress
                vlan_mem_str = runBcmCmd(mod.mod, unit, cmd_pfx["egr vlan membership"] + str(self.vlan))
                obj = createHwTableObject(vlan_mem_str)
                if len(obj.table) == 0:
                    continue # continue instead of returning
                egr_tagged = obj.table["EGR_VLAN.epipe0[%d]"%vlan_id]['PORT_BITMAP']
                egr_untagged = obj.table["EGR_VLAN.epipe0[%d]"%vlan_id]['UT_PORT_BITMAP']

                hwDeviceId = BcmHwDeviceId(mod.mod,unit)
                #On Trident Plus platform ing_vp_vlan_membership is not defined.
                #Hence avoid checking this register in trident plus platform
                if (hwDeviceId.isChipTridentPlus() is not True):
                    vlan_mem_str = runBcmCmd(mod.mod, unit, cmd_pfx["egr vp vlan membership"] + str(self.vlan))
                    obj = createHwTableObject(vlan_mem_str)
                    if len(obj.table) != 0:
                        for e in obj.table:
                            egr_vps.append(int(obj.table[e]['VP'],16))

                if (mod.mod, unit) not in output.keys():
                    output[(mod.mod,unit)] = []
                output[(mod.mod,unit)] = (ing_tagged, egr_tagged, ing_untagged, egr_untagged, ing_vps, egr_vps)

        # Get a list of ingress and egress interfaces here
        for (slot,unit) in output.keys():
            mod = BcmHwMod(slot)
            (ing_tag, egr_tag, ing_untag, egr_untag, vps, egr_vps) = output[(slot, unit)]
            for i in range(1,256):
                if ((1<<i) & int(ing_tag, 16)): 
                     (ret, ifindex) = py_im_get_if_name_and_if_index_from_mod_unit_port(mod.get_modid()[unit], i)
                     if ret == 0:
                         ing_ifidxs.append(ifindex)
                if ((1<<i) & int(egr_tag, 16)):
                     (ret, ifindex) = py_im_get_if_name_and_if_index_from_mod_unit_port(mod.get_modid()[unit], i)
                     if ret == 0:
                        egr_ifidxs.append(ifindex)    

            for v in ing_vps: 
                (ret, ifindex) = py_im_get_if_index_from_vp(v)
                if ret == 0:
                    ing_ifidxs.append(ifindex)

            for v in egr_vps:
                (ret, ifindex) = py_im_get_if_index_from_vp(v)
                if ret == 0:
                    egr_ifidxs.append(ifindex)
        
        s1 = Set(ing_ifidxs)
        s2 = Set(egr_ifidxs)

        #  Do a reverse check. i.e. make sure the hardware ports in a
        #  vlan are also there in software.
	nxos_ports = Set()
	for i in _intfList:
            nxos_ports.add(i.ifindex)
	hw_ports = s1 & s2
	inc_ports = hw_ports - nxos_ports
	for ifidx in inc_ports:
            i = nxos.Nxos.Interface(_ifindex = ifidx, _queryHw = False)
            if i.get_sw_link_state() == 1 and i.get_layer() == 2:
                if ( (not i.pc) and (not i.fex)):
                    nok.append(ifidx)
                else:
                    #CSCux32397 Add HifPcs to the intf list since PI doesn't 
                    # pass it down as part of the intf list
                    i = nxos.Nxos.Interface(_ifindex = ifidx, _queryHw = False)
                    _intfList.append(i)


        # Force egress membership for NIF ports
        for ifidx in s1:
            try:
                i = nxos.Nxos.Interface(_ifindex = ifidx, _queryHw = False)
            except:
                continue
            
            if i.nif or i.ns_port != 255:
                s2.add(ifidx)    
     
        # Check hardware 
        inconsistent_in_hw = (s1 - s2) | (s2 - s1)
        consistent_in_hw = s1 & s2

        # Only add the ports that are up in SW
        if inconsistent_in_hw and len(inconsistent_in_hw) > 0:
            for ifidx in inconsistent_in_hw:
                i = nxos.Nxos.Interface(_ifindex = ifidx, _queryHw = False)
                if i.get_sw_link_state() == 1 and i.get_layer() == 2:
                    nok.append(ifidx)

        # Cross-check with software. Any (in)consistencies found here are subject 
        # to filtering, re-evaluation at the PI layer, in cc_vlan_memb.py   
        for intf in _intfList:
            if not intf.fex: 
                # if monitor dest port, dont consider it for vlan consistency check
                if intf.span_dest == 1:
                    continue

                # In Software, but not in hw (check both egress and ingress)
                if intf.ifindex not in consistent_in_hw:
                    if intf.get_sw_link_state() == 1 and vlan_active_in_sw:
                        #Check if this interface is member of MCT, and was down due to
                        # remote vlan is in shutdown mode, #CSCuv84688
                        if isMCTMemberDown(intf.shortName):
                            ok.append(intf.ifindex)
                        else:
                            #Check if native Vlan in private-vlan configuration does not fall
                            #in the allowed vlan range. 
                            #Ideally, ethpm should not add interface to vlan member list in sw
                            #when native vlan is not in allowed vlans list. Bug:CSCux29407
                            #This is a workaround to avoid consistency check failure
                            if isNativeVlanIsNotInAllowedVlans(intf.shortName):
                                ok.append(intf.ifindex)
                            else:
                                nok.append(intf.ifindex)
                    else:
                        ok.append(intf.ifindex)

                # BCM Specific - check Ranger
                if intf.hwIf.obj.isRanger:
                    ranger_ok = True 
                    for rngMb in intf.hwIf.obj.rangerMemberPorts:
                        (ret, ifindex) = py_im_get_if_name_and_if_index_from_mod_unit_port(mod.mod, rngMb.hw_port)
                        if ret == 0:
                            if ifindex in consistent_in_hw:
                                ranger_ok = ranger_ok and True 
                            else:
                                ranger_ok = False
                        else:
                            ranger_ok = False
                    if ranger_ok:
                        ok.append(intf.ifindex)
                    else:
                        if intf.get_sw_link_state() == 1 and vlan_active_in_sw:
                            nok.append(intf.ifindex)
                        else:
                            ok.append(intf.ifindex)
                
                # In software, and in both egress and ingress in HW
                elif intf.ifindex in consistent_in_hw:
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
        
        #print "C: %s, I: %s" % (len(consistent_in_hw), len(inconsistent_in_hw))
        #print "O: %s, N: %s" % (len(ok), len(nok))
        return (list(Set(ok)), list(Set(nok)))


    def get_vlan_stp_state(self, _modList):    
        output = {}
        egr_output = {}
        vp = {}
        egr_vp = {}
        ns_cbl_state = {}
        pi_state_str = {}
        pi_state_str[0]='DIS'
        pi_state_str[1]='BLK'
        pi_state_str[2]='UNK'
        pi_state_str[3]='FWD'
        for mod in _modList:
            output[mod.mod] = {}
            egr_output[mod.mod] = {}
            vp[mod.mod] = {}
            egr_vp[mod.mod] = {}
            ns_cbl_state[mod.mod] = {}
            strout = runBcmCmd(mod.mod, 0, "a")
            chips = strout.splitlines()
            for unit in range(0, mod.units):
                if chips[unit].find("BCM56044_B0") != -1:
                    # Ranger unit
                    continue
                #get vlan stg.
                strout = runBcmCmd(mod.mod, unit, cmd_pfx["vlan info"] + str(self.vlan))
                vlanInfo = createHwTableObject(strout)
                stg_str_id = vlanInfo.table['VLAN.ipipe0[%s]'%(self.vlan)]['STG']
                int_stg_id = int(stg_str_id, 16)
                strout = runBcmCmd(mod.mod, unit, cmd_pfx["stg membership"] + stg_str_id)
                dict = createHwTableObject(strout)
                output[(mod.mod,unit)] = {}
                vp[(mod.mod,unit)] = {}
                egr_vp[(mod.mod,unit)] = {}
                ns_cbl_state[(mod.mod,unit)] = {}
                for i in dict.table['VLAN_STG.ipipe0[%s]'%str(int_stg_id)].keys():
                    if "SP_TREE_PORT" not in i:
                        continue
                    hwport = int(i[12:])
                    hwstate = dict.table['VLAN_STG.ipipe0[%s]'%str(int_stg_id)][i]
                    pi_state = pi_state_str[int(hwstate)]
                    output[(mod.mod,unit)][hwport] = pi_state

                #Process NS CBL status
                cmd1 = "slot " + str(mod.mod) + " " + cmd_pfx["ns dump"] + "asic " + str(unit)
                #Hardcoding the table instance to ingress (1)
                #as both directions have same vlan_label programmed
                cmd  =  cmd1 +  " table 1:" + cmd_pfx["vlan state"] + str(self.vlan)
                show_stp = cli_ex(cmd)
                match = re.search(r'vlan_label=\w\w\w\w\w\w\w\w\w\w\w\w\w\w\w\w\w\w', show_stp)
                if match:
                    cbl_value= match.group().split("=")[-1]
                    ns_cbl_state[(mod.mod,unit)][self.vlan] = cbl_value

                strout = runBcmCmd(mod.mod, unit, cmd_pfx["egr stg membership"] + stg_str_id)
                dict = createHwTableObject(strout)
                egr_output[(mod.mod,unit)] = {}
                for i in dict.table['EGR_VLAN_STG.epipe0[%s]'%str(int_stg_id)].keys():
                    if "SP_TREE_PORT" not in i:
                        continue
                    hwport = int(i[12:])
                    hwstate = dict.table['EGR_VLAN_STG.epipe0[%s]'%str(int_stg_id)][i]
                    pi_state = pi_state_str[int(hwstate)]
                    egr_output[(mod.mod,unit)][hwport] = pi_state

                hwDeviceId = BcmHwDeviceId(mod.mod,unit)
                #On Trident Plus platform ing_vp_vlan_membership is not defined.
                #Hence avoid checking this register in trident plus platform
                if ((hwDeviceId.isChipTridentPlus() is not True)):
                    strout = runBcmCmd(mod.mod, unit, cmd_pfx["vp vlan membership"] + str(self.vlan))
                    dict = createHwTableObject(strout)
                    for i in dict.table:
                        hwstate = dict.table[i]['SP_TREE']
                        pi_state = pi_state_str[int(hwstate)]
                        vp[(mod.mod, unit)][int(dict.table[i]['VP'],16)] = pi_state

                    strout = runBcmCmd(mod.mod, unit, cmd_pfx["egr vp vlan membership"] + str(self.vlan))
                    dict = createHwTableObject(strout)
                    for i in dict.table:
                        hwstate = dict.table[i]['SP_TREE']
                        pi_state = pi_state_str[int(hwstate)]
                        egr_vp[(mod.mod, unit)][int(dict.table[i]['VP'],16)] = pi_state

        return (output,egr_output, vp, egr_vp, ns_cbl_state)

    def getVlanProfilePtr(self, slot, unit):
        _offset = self.vlan

        strout = runBcmCmd(slot, unit, cmd_pfx["vlan"] + str(self.vlan))
        vlanInfo = createHwTableObject(strout)
        return vlanInfo.table['VLAN.ipipe0[%s]'%(self.vlan)]['VLAN_PROFILE_PTR']


class BcmThreadClass(Thread):
    def __init__(self, _mod, _units, _cmd, _table = False):
        self.mod = _mod
        self.units = _units
        self.cmd = _cmd
        self.output = {}
        self.table = _table
        for unit in range(0, _units):      
            self.output[unit] = None    
        Thread.__init__(self)

    def run(self):
        for unit in range(0, self.units):
            info = runBcmCmd(self.mod, unit, self.cmd)
            if self.table == True:
                self.output[unit] = createHwTableObject(info)
            else:
                self.output[unit] = info


"""
Description:
 This captures trunk membership hardware state from all modules and units.
Properties:
 trunks: This is a 2D array index by [module][unit]. It returns the trunk_group
         trunk_member tables.
"""
class BcmHwTrunkCollection:
    def get_trunk_members(self, _tg, _tmt):
        base = int(_tg['BASE_PTR'], 16)
        size = int(_tg['TG_SIZE'], 16) + 1


        members = []
        for i in range(0, size):
            key = "TRUNK_MEMBER.ipipe0[" + str(base + i) + "]"
            dport = int(_tmt[key]['PORT_NUM'], 16)
            dmod = int(_tmt[key]['MODULE_ID'], 16)

            members.append((dmod, dport))

        return members

    def __init__(self, _modList):
        self.trunks = {}
        for mod in _modList:                                                    
            self.trunks[mod.mod] = {}                                            
        tall = []
        for mod in _modList:
            t1 = BcmThreadClass(mod.mod, mod.units, cmd_pfx["trunk info"], _table = True)
            t2 = BcmThreadClass(mod.mod, mod.units, cmd_pfx["trunk membership"], _table = True)
            t1.run()
            t2.run()
            tall.append((t1,t2))

        #for(t1,t2) in tall:
        #   t1.join()
        #   t2.join()

        for (t1,t2) in tall:
            for unit in range(0, t1.units):
                #trunk_group and trunk member table.
                self.trunks[t1.mod][unit] = (t1.output[unit], t2.output[unit])
    
    def validate_pc_membership(self, mods, okList, nokList, ok, nok):
        #make sure all are consistent first. If some are not , then add them to candidate inconsistent list.
        #if they are consistent - add to candidate consistent list.

        cnt = 0
        tginfo = {}
        cand_ok = {}
        cand_nok = {}
        cand_nok_tgsize = {}
        cand_nok_tmembers = {}
        cand_nok_missing = {}

        #Get per trunk information from the hardware.
        for mod in mods:
            strout = runBcmCmd(mod.mod, 0, "a")
            chips = strout.splitlines()
            for unit in range(0, mod.units):
                if chips[unit].find("BCM56044_B0") != -1:
                    # Ranger unit
                    continue
                cnt = cnt + 1

                #trunk group and trunk member table.
                (tgt, tmt) = self.trunks[mod.mod][unit]

                for t in tgt.table:
                    m = re.search('TRUNK_GROUP\.ipipe0\[([0-9]+)\]', t)
                    if m is None:
                        continue

                    tgid = int(m.group(1))

                    # ignore all the shadow trunk PC
                    # we'll cover all the non-shadows anyway...
                    if tgid >= 512:
                        continue

                    members = []
                    memnames = []
                    if tgt.table[t]['RTAG'] == '7':
                        tgsize = int(tgt.table[t]['TG_SIZE'],16) + 1
                        tmembers = self.get_trunk_members(tgt.table[t], tmt.table)
                        tmembers.sort()
                        for (modid,port) in tmembers:
                            (ret, ifindex) = py_im_get_if_name_and_if_index_from_mod_unit_port(modid, port)
                            if ret != 0:
                                ifindex = 0
                            members.append((modid,port))
                            longName = py_im_get_long_name_from_if_index(ifindex)
                            memnames.append(longName)
                    else:
                        tgsize = 0
                        members = None
                        continue

                    if tgid not in tginfo.keys():
                        tginfo[tgid] = []

                    tginfo[tgid].append((mod.mod, unit, tgsize, members, memnames))

       
        #For each trunk make sure hardware state is consistent across all 
        #modules and units (software state is not checked yet.)
        for tgid in tginfo.keys():
            if len(tginfo[tgid]) != cnt:
                #found inconsistent tgid:
                cand_nok_missing[tgid] = tginfo[tgid]
            else:
                tgsize = -1
                failed = False
                for (tmod,tunit,ttgsize,tmembers, tmemnames) in tginfo[tgid]:
                    if tgsize == -1:
                        tgsize = ttgsize
                        members = tmembers
                        continue

                    if tgsize != ttgsize:
                        failed = True
                        cand_nok_tgsize[tgid] = tginfo[tgid]
                        break

                    if members != tmembers:
                        failed = True
                        cand_nok_tmembers[tgid] = tginfo[tgid]
                        break

                if failed == False:
                    cand_ok[tgid] = tginfo[tgid]


        #now we have cand ok and cand nok lists.
        #cand nok - we must publish as is.

        #cand ok list - we must confirm with software to further determine if some need to go into cand nok.
        for tgid in cand_ok.keys():
            (ret, ifindex) = py_im_get_if_name_and_if_index_from_mod_unit_port(0, tgid)
            if ret != 0:
                continue

            ifi = nxos.Nxos.Interface(_ifindex = ifindex, _queryHw = False)

            if len(ifi.members) == 0:
                continue

            tgid = ifi.hw_port
            members = ifi.members

            (tmod, tunit, ttgsize, tmembers, memnames) = cand_ok[tgid][0]

            if len(members) != ttgsize:
                cand_nok_tmembers[tgid]= cand_ok[tgid]
                cand_ok[tgid] = None

            for m in members:
                dmod = m.dmod
                dport = m.hw_port

                x = find_dmod_dport_in_trunk_member_list(tmembers, dmod, dport)
                if x == False:
                    if tgid not in cand_nok_tmembers.keys():
                        cand_nok_tmembers[tgid] = None
                    cand_nok_tmembers[tgid] = cand_ok[tgid]
                    cand_ok[tgid] = None



        if len(nokList) or len(cand_nok_tgsize) or len(cand_nok_tmembers) or len(cand_nok_missing) > 0:
            print "Consistency Check: FAILED"
            py_syslog(1, "CC_PC_MEMBERSHIP: Consistency Check: FAILED")
        else:
            if len(okList):
                print "Consistency Check: PASSED"
                py_syslog(1, "CC_PC_MEMBERSHIP: Consistency Check: PASSED")

            elif len(notsup):
                print "CC not supported on these interfaces. For Fex Port channel use fex-interfaces CC"
                for i in notsup:
                    print i.longName
                sys.exit()
            
        print ""
        #Now we have all that we need let's print it out.
        for (pc, o) in okList:
            if pc.hw_port not in cand_ok.keys():
                continue

            if len(o) > 0:
                print " No inconsistency found for %s:"%pc.longName                                  

            for (pcName, m, u) in o.keys():                                     
                if pcName == pc.longName:
                    print "  Module:%d, Unit:%d" % (m, u)       
                    print "    ", ok[(pcName,m,u)]                     

            print ""                                       

        for (pc, n) in nokList:
            if len(n) > 0:
                print " Found inconsistencies for %s:" % ( pc.longName )       

            for (pcName, m, u) in n.keys():                       
                if pcName == pc.longName:
                    print "  Module:%d, Unit:%d" % (m, u)      
                    print "    ", n[(pcName,m,u)]          

        print ""
        print "Following output shows hardware inconsistencies across all modules."
        print "------------------------------------------------------------------"
        for i in cand_nok_tgsize.keys():
            (ret, ifindex) = py_im_get_if_name_and_if_index_from_mod_unit_port(0, i)
            longName = py_im_get_long_name_from_if_index(ifindex)
            if cand_nok_tgsize[i] is not None:
                print " Found hardware tgsize inconsistencies for:%s" % (longName)
                for (modid, unit, tgsize, members, memnames) in tginfo[i]:
                    print "    Module:%d, Unit:%d, Size:%d" % (modid, unit, tgsize)
                    print ""

        for i in cand_nok_tmembers.keys():
            (ret, ifindex) = py_im_get_if_name_and_if_index_from_mod_unit_port(0, i)
            longName = py_im_get_long_name_from_if_index(ifindex)
            if cand_nok_tmembers[i] is not None:
                print " Found hardware member inconsistencies for:%s" % (longName)
                for (modid, unit, tgsize, members, memnames) in tginfo[i]:
                    print "    Module:%d, Unit:%d, Size:%d" % (modid, unit, tgsize)
                    if memnames is not None and len(memnames):                      
                        print "      ", memnames             
                        print ""

        for i in cand_nok_missing.keys():
            (ret, ifindex) = py_im_get_if_name_and_if_index_from_mod_unit_port(0, i)
            longName = py_im_get_long_name_from_if_index(ifindex)
            if cand_nok_missing[i] is not None:
                print " Found hardware missing inconsistencies for:%s" % (longName)
                for (modid, unit, tgsize, members, memnames) in tginfo[i]:
                    print "    Module:%d, Unit:%d, Size:%d" % (modid, unit, tgsize)
                    if memnames is not None and len(memnames):                      
                        print "      ", memnames             
                        print ""

class BcmHwVlanCollection:
    def __init__(self, _modList):
        self.vlans = {}
        self.egr_vlans = {}
        tall1 = []
        tall2 = []

        for mod in _modList:                                                    
            self.vlans[mod.mod] = {}                                            
            self.egr_vlans[mod.mod] = {}     

        for mod in _modList:
            t1 = BcmThreadClass(mod.mod, mod.units, cmd_pfx["vlan membership"], _table = True)
            t2 = BcmThreadClass(mod.mod, mod.units, cmd_pfx["egr vlan membership"], _table = True)
            t1.start()
            t2.start()
            tall1.append(t1)
            tall2.append(t2)

        for t in tall1:
           t.join()
        for t in tall2:
           t.join()

        for t in tall1:
            for unit in range(0, t.units):
                self.vlans[t.mod][unit] = t.output[unit]

        for t in tall2:
            for unit in range(0, t.units):
                self.egr_vlans[t.mod][unit] = t.output[unit]

class BcmHwStgStpCollection:
    def __init__(self, _modList):
        self.stgs = {}
        self.egr_stgs = {}
        tall1 = []
        tall2 = []
        for mod in _modList:
            t1 = BcmThreadClass(mod.mod, mod.units, cmd_pfx["stg membership"], _table = True)
            t2 = BcmThreadClass(mod.mod, mod.units, cmd_pfx["egr stg membership"], _table = True)
            t1.start()
            t2.start()
            tall1.append(t1)
            tall2.append(t2)

        for t in tall1:
           t.join()
        for t in tall2:
           t.join()

        for t in tall1:
            for unit in range(0, t.units):
                self.stgs[t.mod][unit] = t.output[unit]

        for t in tall2:
            for unit in range(0, t.units):
                self.egr_stgs[t.mod][unit] = t.output[unit]



class BcmHwTrunk:
    def __init__(self, _tgid):
        self.tgid = _tgid

    def get_trunk_membership(self, _modList):
        output = {}
        for mod in _modList:
            for unit in range(0, mod.units):
                output[mod.mod][unit] = runBcmCmd(mod.mod, unit, "%d:"%(unit) + cmd_pfx["trunk info"] + str(self.tgid))
        print output

class BcmHwSourceTrunkMapModbase:
    def __init__(self, _mod, _unit, _dmod):
        strout = runBcmCmd((_mod), _unit, cmd_pfx["srcTrunkMapModbase"] + str(_dmod))
        lines = strout.strip("\n")
        self.offset = _dmod
        self.hwSrcTrunkMap = createHwTableObject(strout)

    def getBase(self):
        _portKey = 'SOURCE_TRUNK_MAP_MODBASE.ipipe0[' + str(self.offset) + ']'
        return int(self.hwSrcTrunkMap.table[_portKey]['BASE'],16)

class BcmHwSourceTrunkMap:
    def __init__(self, _mod, _unit, _dmod, _port):

        # cache the source trunk map table
        hwSrcTrnkMapModbase = BcmHwSourceTrunkMapModbase(_mod, _unit, _dmod)
        _offset = hwSrcTrnkMapModbase.getBase() + _port
        strout = runBcmCmd((_mod), _unit, cmd_pfx["srcTrunkMap"] + str(_offset))
        lines = strout.strip("\n")
        self.offset = _offset
        self.hwSrcTrunkMap = createHwTableObject(strout)

    """ Return the hardware Vrf Id for a given port """
    def getVrfId(self):

        _portKey = 'SOURCE_TRUNK_MAP.ipipe0[' + str(self.offset) + ']'
        return int(self.hwSrcTrunkMap.table[_portKey]['VRF_ID'],16)
        
    def getL3iifIndex(self):
        _portKey = 'SOURCE_TRUNK_MAP.ipipe0[' + str(self.offset) + ']'
        return int(self.hwSrcTrunkMap.table[_portKey]['L3_IIF'], 16)

    def getSvpValid(self):
        _portKey = 'SOURCE_TRUNK_MAP.ipipe0[' + str(self.offset) + ']'
        return int(self.hwSrcTrunkMap.table[_portKey]['SVP_VALID'])
    def getSourceVp(self):
        _portKey = 'SOURCE_TRUNK_MAP.ipipe0[' + str(self.offset) + ']'
        return int(self.hwSrcTrunkMap.table[_portKey]['SOURCE_VP'], 16)
    def getTgid(self):
        _portKey = 'SOURCE_TRUNK_MAP.ipipe0[' + str(self.offset) + ']'
        return int(self.hwSrcTrunkMap.table[_portKey]['TGID'])
    def getPortType(self):
        _portKey = 'SOURCE_TRUNK_MAP.ipipe0[' + str(self.offset) + ']'
        return int(self.hwSrcTrunkMap.table[_portKey]['PORT_TYPE'])

class BcmHwVlanProfile:
    def __init__(self, slot, unit, _vlanProfilePtr):
        self.vlanProfilePtr = _vlanProfilePtr
        strout = runBcmCmd(slot, unit, cmd_pfx['vlanProfile'] + str(_vlanProfilePtr))
        lines = strout.strip("\n")
        self.hwVlanProfile = createHwTableObject(strout)

    def getLearnDisable(self):
        _vlanKey = 'VLAN_PROFILE.ipipe0[' + str(self.vlanProfilePtr) + ']'
        return int(self.hwVlanProfile.table[_vlanKey]['LEARN_DISABLE'])

class BcmHwL3Iif:
    def __init__(self, _slot, _unit, _l3iifIndex):
        self.l3iifIndex = _l3iifIndex
        strout = runBcmCmd(_slot, _unit, cmd_pfx['l3iif'] + str(_l3iifIndex))
        lines = strout.strip("\n")
        self.hwL3Iif = createHwTableObject(strout)

    def getVpnId(self):
        _l3iifKey = 'L3_IIF.ipipe0[' + str(self.l3iifIndex) + ']'
        return int(self.hwL3Iif.table[_l3iifKey]['VRF'], 16)
        
class BcmHwStgState:
    def __init__(self, _slot, _unit, _stgId):
        self.stgId = _stgId
        strout = runBcmCmd(_slot, _unit, cmd_pfx['stg membership'] + str(_stgId))
        lines = strout.strip("\n")
        self.hwStgEntry = createHwTableObject(strout)

        strout = runBcmCmd(_slot, _unit, cmd_pfx['egr stg membership'] + str(_stgId))
        lines = strout.strip("\n")
        self.hwEgrStgEntry = createHwTableObject(strout)

    def getStgState(self, _port):
        _portKey = 'SP_TREE_PORT' + str(_port)
        _stgKey = 'VLAN_STG.ipipe0[' + str(self.stgId) + ']'
        return int(self.hwStgEntry.table[_stgKey][_portKey])

    def getEgrStgState(self, _port):
        _portKey = 'SP_TREE_PORT' + str(_port)
        _stgKey = 'EGR_VLAN_STG.epipe0[' + str(self.stgId) + ']'
        return int(self.hwEgrStgEntry.table[_stgKey][_portKey])

#########################################
# VPC Egress Mask registers
#########################################
class BcmHwEgrMaskModBase:
    def __init__(self, _mod, _unit, _dmod):
        strout = runBcmCmd(_mod, _unit, cmd_pfx["egrMaskModBase"] + str(_dmod))
        lines = strout.strip("\n")
        self.offset = _dmod
        self.hwEgrMaskModBase = createHwTableObject(strout)

    def getBase(self):
        _portKey = 'EGR_MASK_MODBASE.ipipe0[' + str(self.offset) + ']'
        return int(self.hwEgrMaskModBase.table[_portKey]['BASE'], 16)

class BcmHwEgrMask:
    def __init__(self, _mod, _unit, _dmod, _port):
        hwEgrMaskModBase = BcmHwEgrMaskModBase(_mod, _unit, _dmod)
        _offset = hwEgrMaskModBase.getBase() + _port
        strout = runBcmCmd(_mod, _unit, cmd_pfx["egrMask"] + str(_offset))
        lines = strout.strip("\n")
        self.offset = _offset
        self.hwEgrMask = createHwTableObject(strout)

    def getEgrMask(self):
        _portKey = 'EGRESS_MASK.ipipe0[' + str(self.offset) + ']'
        return int(self.hwEgrMask.table[_portKey]['EGRESS_MASK'], 16)

class BcmHwEgrMaskModBaseTable:
    def __init__(self, _mod, _unit):
        strout = runBcmCmd(_mod, _unit, cmd_pfx["egrMaskModBaseChg"])
        lines = strout.strip("\n")
        #self.offset = _dmod
        self.hwEgrMaskModBaseTable = createHwTableObject(strout)

    def getMod(self, _base):
        mods = []
        for key in self.hwEgrMaskModBaseTable.table.keys():
            base = int(self.hwEgrMaskModBaseTable.table[key]['BASE'], 16)
            if base == _base:
                match = re.search('EGR_MASK_MODBASE.*\[(.*)\]', key)
                if match:
                    mod = int(match.group(1))
                    mods.append(mod)
        if len(mods) != 0:
            return mods
        else:
            return None  #Error



class BcmHwEgrMaskTable:
    def __init__(self, _mod, _unit):
        #hwEgrMaskModBase = HwEgrMaskModBase(_mod, _unit, _dmod)
        #_offset = hwEgrMaskModBase.getBase() + _port
        strout = runBcmCmd(_mod, _unit, cmd_pfx["egrMaskChg"])
        lines = strout.strip("\n")
        #self.offset = _offset
        self.hwEgrMaskModBaseTable = BcmHwEgrMaskModBaseTable(_mod, _unit)
        self.hwEgrMaskTable = createHwTableObject(strout)
        self.mod = _mod
        self.unit = _unit
        self.m = nxos.Nxos.Module(_mod)

    def getAll(self):
        dmods = []
        retVal = []
        rows = []
        for key in self.hwEgrMaskTable.table.keys():
            mask = int(self.hwEgrMaskTable.table[key]['EGRESS_MASK'], 16)
            match = re.search('EGRESS_MAS.*\[(.*)\]', key)
            if not match:
                print "Error processing Egr Mask table"
                return None
            index = int(match.group(1))
            base = index & ~0x7f
            port = index & 0x7f
            dmods = self.hwEgrMaskModBaseTable.getMod(base)
            for dmod in dmods:
                row = {'dmod' : dmod,
                       'port' : port,
                       'mask' : mask
                      }
                rows.append(row)
            dict = {}
            #print "dmod = %d port = %d: mask = 0x%x"%(dmod, port, mask)
        for row in rows:
            src_dmod = row['dmod']
            src_port = row['port']
            mask = row['mask']
            intfNames = getIfNamesGivenBitmap(self.m, self.unit, mask)
            if intfNames:
               (ret, ifindex) = py_im_get_if_name_and_if_index_from_mod_unit_port(src_dmod, src_port)
               srcIntf = py_im_get_long_name_from_if_index(ifindex)
               srcIntf = getShortIfName(srcIntf)
               print "\t[Src Port %s]:" % srcIntf,
               print ', '.join(name for name in intfNames)
        return 1


#########################################
# Mac entry registers
#########################################
class BcmHwMacEntry:
    def __init__(self, _mod, _unit, _mac):
        hmac = "0x" + _mac.replace(".","")
        strout = runBcmCmd(_mod, _unit, cmd_pfx["searchL2Entry"] + hmac);
        lines = strout.strip("\n")
        if "Nothing found" in strout:
            self.found = False
            return None
        self.found = True
        self.macEntry = createHwTableObject(strout)
        key = self.macEntry.table.keys()[0]
        match = re.search('L2_ENTRY.*\[(.*)\]', key)
        if not match:
            self.found = False
            return None
        self.base = match.group(1)
        self.hitDA = self.macEntry.table[key]['HITDA']
        self.hitSA = self.macEntry.table[key]['HITSA']
        self.mod = _mod
        self.unit = _unit

    def getHitDA(self):
        if not self.found:
            return 0
        return int(self.hitDA)
        
    def getHitSA(self):
        if not self.found:
            return 0
        return int(self.hitSA)

    def resetHitDA(self):
        if not self.found:
            return False
        strout = runBcmCmd(self.mod, self.unit, cmd_pfx["modL2Entry"] +
                                            self.base + " 1 " + "HITDA=0")


    def resetHitSA(self):
        if not self.found:
            return False
        strout = runBcmCmd(self.mod, self.unit, cmd_pfx["modL2Entry"] +
                                            self.base + " 1 " + "HITSA=0")
        
#########################################
# VxLAN registers
#########################################
class BcmHwVfi:
    def __init__(self, _mod, _unit, _vfi):
        strout = runBcmCmd(_mod, _unit, cmd_pfx["vfi"] + str(_vfi))
        lines = strout.strip("\n")
        self.offset = _vfi
        self.hwVfi = createHwTableObject(strout)

    def getIpmc(self):
        _vfiKey = 'VFI.ipipe0[' + str(self.offset) + ']'
        return int(self.hwVfi.table[_vfiKey]['UUC_INDEX'], 16)

    def getVxlanGroup(self):
        return self.getIpmc() + 0xc000000

class HwVlang:
    def __init__(self, _mod, _unit, _vlan):
        strout = runBcmCmd(_mod, _unit, cmd_pfx["vlan"] + str(_vlan))
        lines = strout.strip("\n")
        self.offset = _vlan
        self.hwVlan = createHwTableObject(strout)

    def getIpmc(self):
        _vlanKey = 'VLAN.ipipe0[' + str(self.offset) + ']'
        return int(self.hwVlan.table[_vlanKey]['UUC_IDX'], 16)

    def getVlanGroup(self):
        return self.getIpmc() + 0x9000000
                                                 
class BcmHwDeviceId:                                                  
    def __init__(self, _mod, _unit):                               
        self.mod = _mod                                            
        self.unit = _unit                                          
    
    def getDevId(self):                                            
        output = runBcmCmd(self.mod, 0, "show unit")          
        lines = output.split("\n")                            
        for line in lines:                                    
            if "Unit" in line:                                
                devId = re.search(r'Unit (\d+) chip ([A-Z0-9_]+)' ,line)
                if devId:                                                  
                    if int(devId.group(1)) == self.unit:        
                        deviceId = devId.group(2)               
                        if re.match("BCM5685",deviceId):
                           return True
                        elif re.match("BCM5684",deviceId):
                           return True
                        elif re.match("BCM5654",deviceId):
                           return True
                        # TH TOR
                        elif re.match("BCM56960_A0", deviceId):
                           return True
                        # TH EOR
                        elif re.match("BCM56960_B0", deviceId):
                           return True
                        continue                               
        return False 

    def isChipTridentPlus(self):
        output = runBcmCmd(self.mod, 0, "show unit")
        lines = output.split("\n")
        for line in lines:
            if "Unit" in line:
                devId = re.search(r'Unit (\d+) chip ([A-Z0-9_]+)' ,line)
                if devId:
                    if int(devId.group(1)) == self.unit:
                        deviceId = devId.group(2)
                        id = re.match("BCM5684",deviceId)
                        id2 = re.match("BCM5654",deviceId)

                        if id or id2:                              
                            return True                            
                        else:                                      
                            continue                               
        return False                                           
                    
class BcmHwSourceVp:
    def __init__(self, _mod, _unit, _vp):
        strout = runBcmCmd(_mod, _unit, cmd_pfx["source_vp"] + str(_vp))
        lines = strout.strip("\n")
        self.offset = _vp
        self.hwVp = createHwTableObject(strout)

    def getVfi(self):
        _key = 'SOURCE_VP.ipipe0[' + str(self.offset) + ']'
        return int(self.hwVp.table[_key]['VFI'], 16)

    def getSdTagMode(self):
        _key = 'SOURCE_VP.ipipe0[' + str(self.offset) + ']'
        return int(self.hwVp.table[_key]['SD_TAG_MODE'], 16)

    def getCMLFlagsNew(self):
        _key = 'SOURCE_VP.ipipe0[' + str(self.offset) + ']'
        return int(self.hwVp.table[_key]['CML_FLAGS_NEW'], 16)

    def getCMLFlagsMove(self):
        _key = 'SOURCE_VP.ipipe0[' + str(self.offset) + ']'
        return int(self.hwVp.table[_key]['CML_FLAGS_MOVE'], 16)

class BcmVlanXlateEntry:
    def __init__(self, _mod, _unit, _vlan, _dmod, _port, is_trunk):
        if is_trunk:
            strout = runBcmCmd(_mod, _unit, cmd_pfx["searchVlanXlate"] + \
                               "VLAN_ID=" + str(_vlan) + " "\
                               "T=1 " + "TGID=" + str(_port));
        else:
            strout = runBcmCmd(_mod, _unit, cmd_pfx["searchVlanXlate"] + \
                               "VLAN_ID=" + str(_vlan) + " "\
                               "T=0 " + "PORT_NUM=" + str(_port) + " " + \
                               "MODULE_ID=" + str(_dmod));
        lines = strout.strip("\n")
        if "Nothing found" in strout:
            self.found = False
            return None
        self.found = True
        self.vlanXlateEntry = createHwTableObject(strout)
        self.key = self.vlanXlateEntry.table.keys()[0]
        match = re.search('VLAN_XLATE.*\[(.*)\]', self.key)
        if not match:
            self.found = False
            return None
        self.base = match.group(1)
        self.mod = _mod
        self.unit = _unit

    def getSvpValid(self):
        if not self.found:
            return 0
        return int(self.vlanXlateEntry.table[self.key]['XLATE:SVP_VALID'])
    def getSourceVp(self):
        if not self.found:
            return 0
        return int(self.vlanXlateEntry.table[self.key]['XLATE:SOURCE_VP'], 16)

class BcmHwIngDvpTable:
    def __init__(self, _mod, _unit, _vp):
        strout = runBcmCmd(_mod, _unit, cmd_pfx["ingDvpTable"] + str(_vp))
        lines = strout.strip("\n")
        self.offset = _vp
        self.hwIDT = createHwTableObject(strout)

    def getNHI(self):
        _key = 'ING_DVP_TABLE.ipipe0[' + str(self.offset) + ']'
        return int(self.hwIDT.table[_key]['NEXT_HOP_INDEX'], 16)

class BcmHwIngL3NextHop:
    def __init__(self, _mod, _unit, _nhi):
        strout = runBcmCmd(_mod, _unit, cmd_pfx["ing_next_hop"] + str(_nhi))
        lines = strout.strip("\n")
        self.offset = _nhi
        self.hwIngNH = createHwTableObject(strout)

    def getTgid(self):
        _key = 'ING_L3_NEXT_HOP.ipipe0[' + str(self.offset) + ']'
        return int(self.hwIngNH.table[_key]['TGID'], 16)
    def getT(self):
        _key = 'ING_L3_NEXT_HOP.ipipe0[' + str(self.offset) + ']'
        return int(self.hwIngNH.table[_key]['T'])
    def getPort(self):
        _key = 'ING_L3_NEXT_HOP.ipipe0[' + str(self.offset) + ']'
        return int(self.hwIngNH.table[_key]['PORT_NUM'], 16)
    def getMod(self):
        _key = 'ING_L3_NEXT_HOP.ipipe0[' + str(self.offset) + ']'
        return int(self.hwIngNH.table[_key]['MODULE_ID'], 16)

class BcmHwMcList:
    def __init__(self, _mod, _unit, _group):
        output = runBcmCmd(_mod, _unit, "mc show group=" + str(_group))
        lines = output.split("\n")
        self.nh_list = collections.OrderedDict()
        for line in lines:
            if "Group " in line:
                continue
            y = re.search("port (..[0-9]+), encap id ([0-9]+)", line)
            if y is None:
                continue
            hw_port_name = y.group(1)
            encap = int(y.group(2))
            if hw_port_name not in self.nh_list:
                self.nh_list[hw_port_name] = []
                self.nh_list[hw_port_name].append(encap)
