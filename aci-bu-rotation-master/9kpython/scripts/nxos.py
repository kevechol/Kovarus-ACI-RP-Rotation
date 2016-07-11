#################################################
#
#      File:   nxos.py
#      Name:   Parag Deshpande
#
#       Description:  Provides interface to create nxos objects.
#
#
#
# Copyright (c) 1985-2013, 2015-2016 by cisco Systems, Inc.
# All rights reserved.
#
#################################################


import hw 
from hw.hwobj import *
from libnxos_ext_api import *
import nxos_utils 
import array
import re
from cli import *
from collections import namedtuple

class Nxos:
    """
    Wrapper class that provides interface to instantiate the interfaces, vlans and modules
    in our system.
    """
    def __init__(self, _type = "InsiemeEOR"):
        self.type = _type
        return

    class Module:
        """
        Instantiate module object. Populates number of units and also the dmod for each unit.
        """

        @classmethod
        def getOnlineFLCList(cls):
            """get list of module numbers that are online."""
            mod_list1 = []
            for i in range(0, 16):
                if py_pfm_is_module_online(i) == 1:
                    mod_list1.append((i+1))

            for i in range(20, 26):
                if py_pfm_is_module_online(i) == 1:
                    mod_list1.append((i+1))

            return mod_list1


        @classmethod
        def getOnlineLineCardList(cls):
            """get list of module numbers that are online."""
            mod_list1 = []
            for i in range(0, 16):
                if py_pfm_is_module_online(i) == 1:
                    mod_list1.append((i+1))

            #for i in range(20, 26):
            #    if py_pfm_is_module_online(i) == 1:
            #        mod_list1.append((i+1))

            return mod_list1

        @classmethod
        def getOnlineModules(cls):
            """ get sorted list of Module objects that are online"""
            slots = cls.getOnlineLineCardList()
            modlist = []
            for slot in slots:
                m = cls(slot)
                modlist.append(m)
            modlist.sort()
            return modlist

        @classmethod
        def getOnlineFLCModules(cls):
            """ get sorted list of Module objects that are online"""
            slots = cls.getOnlineFLCList()
            modlist = []
            for slot in slots:
                m = cls(slot)
                modlist.append(m)
            modlist.sort()
            return modlist


        def get_module_info(self, _mod):
            return (_mod, 2)

        def __init__(self, _mod):
            self.hwMod = HwMod(_mod)
            self.mod = int(_mod)
            self.units = self.hwMod.get_units()
            self.interfaces = {}


    class Interface:
        """
        Instantiate interface object. Interface object is populated with
        ifindex, slot, port, unit, hw port number, layer (l3 or l2)
        For port channel, it gets populated with member ports also.
        """

        def __cmp__(self, other):
            return self.ifindex - other.ifindex

        def __hash__(self):
            return self.ifindex

        def get_if_index_from_if_long_name(self, _longName):
            p = py_im_get_if_index_from_name(_longName)

            if p[0] == 1:
                return p[1]

            return None

        def get_phy_if_hw_details_from_if_name(self, _ifname, _ifindex = None):
            if _ifindex is not None:
                print _ifindex
                (ret, slot, dmod, unit, nxos_port, hw_port, ns_port, hw_usr_port, mac_unit, mac_pid, slice_num, port_on_slice, src_id, ltl) =\
                    py_im_get_hw_info_from_if_name(_ifindex);
                slot = slot + 1
                return (ret, slot, dmod, unit, nxos_port, hw_port, ns_port, hw_usr_port, mac_unit, mac_pid, slice_num, port_on_slice, src_id, ltl)
            return (-1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

        def get_short_if_name(self, _longName):
            sh = None
            if "thernet" in _longName:
                sh = 'Eth' + _longName[8:]

            if "ort-channel" in _longName:
                sh = 'Po' + _longName[12:]

            return sh

        def get_long_if_name(self, _shortName):
            sh = None
            if "Eth" in _shortName or "eth" in _shortName:
                sh = 'Ethernet' + _shortName[3:]

            if "Po" in _shortName or "po" in _shortName:
                sh = 'Port-channel' + _shortName[2:]

            return sh

        def get_layer(self):
            #2 = L2, 3 = L3.
            return self.swLayer

        def __init__(self, _longName = None, _shortName = None, _ifindex = None, _modList = None, _queryHw = True):
            if _longName is not None:
                _ifindex = self.get_if_index_from_if_long_name(_longName = _longName);
                if _ifindex == 0:
                    print "ERROR: %s has an ifindex of 0" % _longName
            elif _shortName is not None:
                _longName = self.get_long_if_name(_shortName)
                _ifindex = self.get_if_index_from_if_long_name(_longName = _longName);
                if _ifindex == 0:
                    print "ERROR: %s has an ifindex of 0" % _shortName
            else:
                _longName = py_im_get_long_name_from_if_index(_ifindex)
                if _ifindex == 0:
                    raise Exception("ERROR: interface obj created manually with ifidx == 0")

            self.longName = _longName

            if _shortName is not None:
                self.shortName = _shortName
            else:
                self.shortName = self.get_short_if_name(_longName)
            
            self.ifindex = _ifindex
            
            self.vdc = 1
            self.members = []
            self.fex = False
            self.vp = 0xffffffff
            self.vif = 0xffffffff
            self.slot = 0
            self.hwIf = None
            self.swLayer = None
            self.dmod = 0
            self.unit = 0
            self.nxos_port = 0
            self.hw_port = 0
            self.ns_port = 0
            self.hw_usr_port = 0
            self.bundle_index = 0
            self.span_dest = 0
            self.rngr = py_im_is_ifindex_ranger_attached(self.ifindex)
            self.is_port_valid = True
            self.slice_num = 0
            self.port_on_slice = 0
            self.src_id = 0
            self.ltl = 0

            #this is true for sat fpc.
            self.nif = False

            #true if interface is port-channel.
            self.pc = False
            (ret, mode) = py_im_get_ifindex_real_port_mode(self.ifindex, 1)
            if ret == 0:
                if mode == 0x02000000:
                    self.nif = True
            #Filter out the inband interfaces "lc-eth", from the init list for consistency check.
            #CSCux25847
            if "lc-eth" in _longName:
                return
            (ret, self.bundle_index) = py_im_get_pc(self.ifindex)
            (ret, self.vp) = py_im_get_vp_from_if_index(self.ifindex)
            (ret, self.vif) = py_im_get_vif_from_if_index(self.ifindex)
            self.span_dest = py_im_is_port_span_dest(self.ifindex)

            (ret, self.swLayer) = py_im_get_ifindex_layermode_list(self.ifindex, self.vdc)
            if ret != 0:
                raise Exception('Retrieving layer mode for ifindex=' + str(self.ifindex) + ' ret=' + str(ret))

            # Check for FEX (102/1/1)
            m = re.search('[a-z,A-Z]+(.*)/(.*)/(.*)', _longName)
            if m is not None and int(m.group(1)) > 32:
                #for fex we don't do any hardware reads..
                self.fex = True

            (ret, self.slot, self.dmod, self.unit, self.nxos_port,
             self.hw_port, self.ns_port, self.hw_usr_port,
             self.mac_unit, self.mac_pid, self.slice_num,
             self.port_on_slice, self.src_id, self.ltl) =\
                self.get_phy_if_hw_details_from_if_name(_ifname=_longName, _ifindex=_ifindex)

            #TODO PD
            if "channel" not in self.longName and not self.fex:
                # chk if unit is not T2 and is not a NS port
                # HwDeviceId.getDevId() returns True if a given unit is T2 unit
                # non NS port will have ns_port value as 255
                # avoid running this check on port-channels or fex interfaces
                # This PD stuff really needs to be moved
                if not py_platform_is_lacrosse(0) and not py_platform_is_davos(0): 
                    hwDeviceId = HwDeviceId(self.slot,self.unit)
                    if ( (hwDeviceId.getDevId() is not True) and (self.ns_port == 255) ):
                        #Ranger unit
                        if ( (self.hw_port !=  5) or
                             (self.hw_port != 21) or
                             (self.hw_port != 25) or
                             (self.hw_port != 29) ) :
                            # dummy port -- for Nagano + Moonshot, 2 unused ports (2/1-2)
                            # need to be avoided
                            self.is_port_valid = False
                            return
            
            #TODO PD
            #for Ranger+ units, hw_port is returned as 5 for ce port, and 
            #21, 25 and 29 for xe ports ; later in the script, in class HwPort
            #it expects hw_port to be consequtive ; since they dont change, 
            #re-setting the hw_port accordingly
            self.rngr = rngr = py_im_is_ifindex_ranger_attached(_ifindex)
            if rngr == True:
                if self.mac_pid == 5:
                    #ce port
                    self.mac_pid = 1
                elif self.mac_pid == 21:
                    #xe port
                    self.mac_pid = 2
                elif self.mac_pid == 25:
                    #xe port
                    self.mac_pid = 3
                elif self.mac_pid == 29:
                    #xe port
                    self.mac_pid = 4
            if "channel" in self.longName:
                # this is port channel. so create member list.
                members = new_uintArray(64)
                r = py_im_get_pc_membership(_ifindex, members, 64)

                for cnt in range(0, r):
                    member_ifidx = uintArray_getitem(members, cnt)
                    i = Nxos.Interface(_ifindex = member_ifidx, _queryHw = _queryHw)
                    if i.fex == True:
                        self.fex = True
                    self.members.append(i)

            self.access_port = py_im_is_ifindex_access_port(_ifindex)
	    self.dot1q_port = py_im_is_ifindex_dot1q_port(_ifindex)
            if "channel" in self.longName:
                self.iftype = IfType.PortChannel
                self.pc = True
            else:
                self.iftype = IfType.Ethernet

            # TODO PD
            if _queryHw == True:
                if self.pc == True:
                    if _modList is None:
                        modnums = Nxos.Module.getOnlineLineCardList()
                        mods = []
                        for mod in modnums:
                            m = Nxos.Module(mod)
                            mods.append(m)
                    else:
                        mods = _modList

                    #get hw parameters for the interface.
                    self.hwIf = HwPort(IfType.PortChannel, self.slot, self.unit, self.rngr, self.hw_port, self.mac_unit, self.mac_pid, _hw_usr_port=self.hw_usr_port, _mods = mods, _slice_num=self.slice_num, _port_on_slice=self.port_on_slice, _src_id=self.src_id, _ltl=self.ltl, _hw_name=self.longName)
                else:
                    #get hw parameters for the interface.
                    if self.fex == False:
                        self.hwIf = HwPort(IfType.Ethernet, self.slot, self.unit, self.rngr, self.hw_port, 
                        self.mac_unit, self.mac_pid, self.ns_port, _hw_usr_port=self.hw_usr_port,
                        _slice_num=self.slice_num, _port_on_slice=self.port_on_slice, _src_id=self.src_id, _ltl=self.ltl, _hw_name=self.longName)
                    else:
                        self.hwIf = HwPort(IfType.Fex, self.slot, self.unit, self.rngr, self.hw_port, 
                        self.mac_unit, self.mac_pid, self.ns_port, _hw_usr_port=self.hw_usr_port,
                        _slice_num=self.slice_num, _port_on_slice=self.port_on_slice, _src_id=self.src_id, _ltl=self.ltl, _hw_name=self.longName)
                return



        def get_if_index_from_if_long_name(self, _longName):
            p = py_im_get_if_index_from_name(_longName)

            if p[0] == 1:
                return p[1]

            return None

        def get_phy_if_hw_details_from_if_name(self, _ifname, _ifindex = None):
            if _ifindex is not None:
                (ret, slot, dmod, unit, nxos_port, hw_port, ns_port, 
                 hw_usr_port, mac_unit, mac_pid, slice_num, port_on_slice, src_id, ltl) = py_im_get_hw_info_from_if_name(_ifindex);
                slot = slot + 1
                return (ret, slot, dmod, unit, nxos_port, hw_port, ns_port, 
                             hw_usr_port, mac_unit, mac_pid, slice_num, port_on_slice, src_id, ltl)
            return (-1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

        def get_short_if_name(self, _longName):
            sh = None
            if "thernet" in _longName:
                sh = 'Eth' + _longName[8:]

            if "ort-channel" in _longName:
                sh = 'Po' + _longName[12:]

            return sh

        def get_long_if_name(self, _shortName):
            sh = None
            if "Eth" in _shortName or "eth" in _shortName:
                sh = 'Ethernet' + _shortName[3:]

            if "Po" in _shortName or "po" in _shortName:
                sh = 'Port-channel' + _shortName[2:]

            return sh

        def get_layer(self):
            #2 = L2, 3 = L3.
            return self.swLayer

        def get_src_id(self):
            return self.src_id
        
        def get_slice_num(self):
            return self.slice_num
        
        def if_replace_output(_lines, _find_word, _replace_word):
            hw_name = self.hwIf.get_hw_if_name()


        def get_hw_counters(self):
            #print "get hw counters"
            lines = self.hwIf.get_counters()

            #replace hw if name with our nxos name.
            return replace_output(lines, self.hwIf.get_hw_name(), self.shortName)

        # returns counter registers as dictionary: { RIPD4 : 50, etc }
        def get_hw_counters_dict(self):
            return self.hwIf.get_counters_dict()

        def get_hw_counters_snmp(self):
            lines = self.hwIf.get_counters_snmp()

            #replace hw if name with our nxos name.
            return replace_output(lines, self.hwIf.get_hw_name(), self.shortName)

        def get_hw_counters_snmp_dict(self):
            return self.hwIf.get_counters_snmp_dict()

        def get_sw_vlan_membership(self, _ifindex):
            vlans = new_uintArray(4096)
            cnt = py_im_get_ifindex_oper_vlans(_ifindex, vlans, 4096)
            return cnt, vlans

        def is_access_port(self):
            return self.access_port
	
	def is_dot1q_port(self):
	    return self.dot1q_port

        def is_ns_attached(self):
            if not self.is_po():
                return self.ns_port != 0 and self.ns_port != 255
            if len(self.members) > 0:
                return self.members[0].ns_port != 0 and self.members[0].ns_port != 255

        def is_po(self):
            return self.iftype == IfType.PortChannel

        def get_vpl_list(self):
            vlans = new_uintArray(4096)
            peer_vlans = new_uintArray(4096)
            peer_vlan_count = 0

            cnt = py_im_get_ifindex_oper_vlans(self.ifindex, vlans, 4096)

            if (py_mcecm_api_is_pc_mcec(self.ifindex)):
                (err, mcec_num) = py_get_mcec_num(self.ifindex)
                peer_vlan_count = py_get_peer_mcec_up_vlans(mcec_num, peer_vlans, 4096)

            vlan_list = []
            vpl_list = []
            vpl_count = 0

            # operational vlans
            for i in range(0, cnt):
                vlan_id = uintArray_getitem(vlans, i)
                vlan = Nxos.Vlan(vlan_id)
                if (vlan.vnseg):
                    (err, vpl_if_index) = py_if_index_vpl(int(self.ifindex), int(vlan_id))
                    if (vpl_if_index):
                        vlan_list.append(vlan_id)
                        vpl_list.append(vpl_if_index)
                        vpl_count += 1

            # go through up vlans on peer and add it to list if not operational
            # on our end
            for i in range(0, peer_vlan_count):
                vlan_id = uintArray_getitem(peer_vlans, i)
                if vlan_id in vlan_list:
                    continue
                vlan = Nxos.Vlan(vlan_id)
                if (vlan.vnseg):
                    (err, vpl_if_index) = py_if_index_vpl(int(self.ifindex), int(vlan_id))
                    if (vpl_if_index):
                        vlan_list.append(vlan_id)
                        vpl_list.append(vpl_if_index)
                        vpl_count += 1

            return (vpl_count, vlan_list, vpl_list)

        def get_sw_link_state(self):
            (err, state) = py_im_is_ifindex_linkup(self.ifindex)
            return state

        def get_sw_admin_state(self):
            (err, state) = py_im_get_ifindex_admin_status(self.ifindex, self.vdc)
            return state

        def validate_link_state(self):
            if self.hwIf.get_hw_link_state() == self.get_sw_link_state():
                return 0

            return -1

        def validateL3LifSettings(self):
            failures = []
            swLayer = self.swLayer

            # for admin down ports we will ignore checks as many configs are
            # done in pre cfg state.
            if self.get_sw_admin_state() == 2:
                return (True, failures)
            ''' 
            # Individual tests
            def _validateL3Vlan(self):
                if (swLayer == 3 and self.hwIf.getPortVid() != 0xfff) :
                    return False

                if (swLayer == 2 and self.hwIf.getPortVid() == 0xfff):
                    return False

                if (swLayer == 2 and self.hwIf.getPortVid() != 0xfff):
                    return False

                return True

            def _validateCmlFlags(self):
                _rc = True

                if (self.hwIf.getPortVid() == 0xfff):
                    _hwVlanTable = HwVlan(4095)
                    _vlanProfilePtr = _hwVlanTable.getVlanProfilePtr(self.slot, self.unit)
                    _hwVlanProfile = HwVlanProfile(self.slot, self.unit, _vlanProfilePtr)

                    if (_hwVlanProfile.getLearnDisable() == 1):
                        return True
                    else:
                        return False

                if ( self.hwIf.getCmlNewBits() != 0 ):
                    _rc = False

                if ( self.hwIf.getCmlMoveBits() != 0 ):
                    _rc = False
                return _rc

            def _validateV4EnableBits(self):
                _rc = True
                if ( self.hwIf.getIpv4L3EnableBits() != 1 ):
                    _rc = False

                if ( self.hwIf.getIpv4McEnableBits() != 1 ):
                    _rc = False

                check_mod = cli('show module')
                if not re.search('N3K',check_mod):
                   if ( self.hwIf.getIpmcDoVlanBits() != 1 ):
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
                #validate stg state only if link is up.
                if self.get_sw_link_state() == 0:
                    return True
                
                # TODO PD
                if self.rngr:
                    for rngMbr in self.hwIf.rangerMemberPorts:
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
            '''

            # get hw parameters for the interface.
            (ret, self.slot, self.dmod, self.unit, self.nxos_port, self.hw_port, self.ns_port, 
             self.hw_usr_port, self.mac_unit, self.mac_pid, self.slice_num, self.port_on_slice, self.src_id, self.ltl) = \
            self.get_phy_if_hw_details_from_if_name(_ifname=self.longName,
                                                    _ifindex=self.ifindex)

            # TODO PD
            self.rngr = rngr = py_im_is_ifindex_ranger_attached(self.ifindex)               
            if rngr == True:                                                    
                if self.mac_pid == 5:                                           
                    #ce port                                                    
                    self.mac_pid = 1                                            
                elif self.mac_pid == 21:                                        
                    #xe port                                               
                    self.mac_pid = 2                                          
                elif self.mac_pid == 25:                                        
                    #xe port                                                
                    self.mac_pid = 3                                        
                elif self.mac_pid == 29:                                    
                    #xe port                                                    
                    self.mac_pid = 4                                            


            self.hwIf = HwPort(IfType.Ethernet, self.slot, self.unit, self.rngr,
                               self.hw_port, self.mac_unit, self.mac_pid, self.ns_port, 
                               self.hw_usr_port, _slice_num = self.slice_num, _port_on_slice = self.port_on_slice, 
                               _src_id = self.src_id, _ltl=self.ltl, _hw_name=self.longName)


            self.sourceTrunkMap = HwSourceTrunkMap(self.slot, self.unit, self.dmod, self.hw_port)
            self.hwL3iif = HwL3Iif(self.slot, self.unit, self.sourceTrunkMap.getL3iifIndex())
            self.hwStgState = HwStgState(self.slot, self.unit, 0)

            # Run the battery of tests!
            _rc = True
            
            if (self.swLayer != 3):
                failures.append('Error: Port is found on swLayer %d, needs to be 3 for L3' \
                                                        % (swLayer))
                _rc = False


            if (self.hwIf.validate_l3_intf() == False):
                print 'Consistency Check Failed for %s' % (self.longName)
                failures.append('Validation of L3 Intf failed')
                _rc = False
            else:
                print 'Consistency Check passed for %s' % (self.longName)

            '''
            # Check if the vlan is programmed at 4095
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

            """
            # Check that VPN ID is correct
            if ( _validateVpnId(self) == False ):
                failures.append("v4 VPN validation failed")
                _rc = False
                """
            '''

            return (_rc, failures)

    class Vlan:
        """
        Instantiate Vlan object. Vlan gets populated with  vlan number.
        All other information must be pulled using get_xxx() apis.
        """
        def __init__(self, _vlan):
            self.vlan = _vlan
            self.vlan_str = str(_vlan)
            self.hwVlan = HwVlan(_vlan)
            self.vnseg = py_vlan_mgr_sdb_get_vlan_segment_id(1, int(self.vlan));
            # self.is_bd = not py_bd_mgr_is_sw_bd_vlan (int(self.vlan));
            # self.vni = py_sw_bd_to_vni_id(1, int(self.vlan));
 

        def get_hw_vlan_membership(self, _modList = None, _egr = False):
            return self.hwVlan.get_vlan_membership(_modList, _egr = _egr)

        def get_cli_sw_vlan_membership(self):
            """gets sorted list of interface short names that are part of the vlan
               this state is obtained from the show command.
               cli command used: show vlan
            """
            y = getVlanDict(self.vlan_str)
            if y is None or self.vlan_str not in y.keys() or y[self.vlan_str] is None:
                return None

            if 'Ports' not in y[self.vlan_str].keys():
                return None

            ports_str = y[self.vlan_str]['Ports']
            ports = strtolist(ports_str)

            #we flatten port channels.
            for i in ports:
                if "Po" in i or "po" in i or "channel" in i:
                   ifs = Nxos.Interface(_shortName=i)
                   if ifs is not None:
                       for mif in ifs.members:
                           #INSIEME_TODO Slow...
                           if mif.shortName not in ports:
                               ports.append(mif.shortName)

            #list of ports.
            ports.sort()
            return ports

        def get_if_list_and_module_list_from_port_name_list(_listOfPorts):
            ifList = []
            modList = []
            for port in _listofPorts:
               ifs = Nxos.Interface(_shortName=port)
               ifList.append(ifs)
               if ifs.slot != 0:
                   tmods.append(ifs.slot)


            #make module list unique and then create modules objects..
            if tmods is not None:
                umods = set(tmods)
                for slot in umods:
                    x = Nxos.Module(slot)
                    modList.append(x)

            return (ifList, modList)


        def filter_interfaces_for_vlan_memb(self, intf):
            # NIF ports
            if intf.nif:
                return False
            # FEX PC 
            if intf.pc and intf.fex: 
                return False
            # FEX member ports
            if intf.bundle_index != 0 and intf.fex:
                return False
            # Skip SPAN ports
            if not intf.fex and intf.span_dest == 1:
                return False
            # Skip invalid ports
            if not intf.hwIf:
                return False
            return True

        def validate_hw_vlan_membership(self, _mods = None, vlan_active = True, intfList = []):
            return self.hwVlan.validate_vlan_membership(_mods, vlan_active, intfList)

        def validate_vlan_membership(self, _mods = None):
            ports = self.get_cli_sw_vlan_membership()
            mod = []
            ok = []
            nok = []
            ifList = []
            if ports is None:
                return ([], [])

            vlan_act = isVlanInActiveState(self.vlan_str)

            #For FEX hifs we need to add all mods of Fabric PO
            if _mods == None:
                _mods = []
                for port in ports:
                   ifs = Nxos.Interface(_shortName=port)
                   if "Po" in port and ifs.fex == False:
                       #ignore port channel as members are included.
                       continue
                   ifList.append(ifs)
                    
                   if ifs.fex == False:
                       _mods.append(ifs.slot)
                   else:
                       nifMods = new_uintArray(16)
                       numMods = new_uintArray(1)
                   
                       if ifs.pc == True and ifs.fex == True:
                           # fetch the ifindex of one of the member ports of the HIF PC
                           # py_get_fport_mods_for_hif will use that to get the mod	
	                   ifindex = ifs.members[0].ifindex 
                       else: 
                           ifindex = ifs.ifindex
 	
                       rc = py_get_fport_mods_for_hif(ifindex, nifMods, numMods)
                       _mods.append(uintArray_getitem(nifMods, 0))


                #make module list unique and then create modules objects..
                if _mods is not None:
                    umods = set(_mods)
                    for slot in umods:
                        x = Nxos.Module(slot)
                        mod.append(x)
            
            ifList = filter(self.filter_interfaces_for_vlan_memb, ifList)
              
            (ok, nok) = self.validate_hw_vlan_membership(mod, vlan_act, ifList)
 
            return (ok, nok)

        def get_if_index_list_from_hw_vlan_membership(self, _mods = None, _egr = False):
            """ goes thru modules in _mods and obtains the interfaces part of this vlan.
                Converts the hw port number to if index and returns sorted short if name list.
                if  _mods is None, it will check across all online modules.
            """
            ifindexList = []

            if _mods == None:
                mods = Nxos.Module.getOnlineModules()
            else:
                mods = _mods

            modInfo = {}
            for mod in mods:
                modInfo[mod.mod] = mod

            return self.get_hw_vlan_membership(_modList = mods, _egr = _egr)

        def get_hw_stp_state(self, _modList):
            self.hwVlan.get_hw_stp_state(self, _modList = _modList)
            return

        def validate_vlan_spanning_tree_state(self):
            #Unfortunately this is coming from show command and not binary data.
            stp_dict = getShowSpanningTreeDict(self.vlan)
            if stp_dict is None or self.vlan not in stp_dict.keys():
                return ([],[])


            #get hardware.

            ifList = []
            modList = []
            sw_output = {}
            sw_output_vp = {}
            mods = []
            if 'Interface_info' not in stp_dict[(self.vlan)].keys():
                return ([],[])

            for i in stp_dict[(self.vlan)]['Interface_info'].keys():
                ifs = Nxos.Interface(_shortName = i)

                #fex interface not supported.
                #if ifs.fex == True:
                #    continue
                #For FEX Hif POs all mods of the NIF will be checked and for Hif interfaces 
                #only the first NIF PO member will be checked
                if "Po" in i:
                    for mif in ifs.members:
                        if mif.fex == False:
                            sw_output.setdefault((mif.slot, mif.hwIf.get_unit()), {})
                            sw_output[(mif.slot, mif.hwIf.get_unit())][mif.hwIf.get_hw_port()] \
                            = (mif, stp_dict[(self.vlan)]['Interface_info'][i]['Status'])
                            mods.append(mif.slot)
                        else:
                            nifMods = new_uintArray(16)
                            numMods = new_uintArray(1)
                            rc = py_get_fport_mods_for_hif(mif.ifindex, nifMods, numMods)
                            nifMod = uintArray_getitem(nifMods, 0)
                            sw_output_vp.setdefault((nifMod, mif.hwIf.get_unit()), {})
                            sw_output_vp[(nifMod, mif.hwIf.get_unit())][ifs.vp] \
                            = (ifs, stp_dict[(self.vlan)]['Interface_info'][i]['Status'])
                            mods.append(nifMod)
                            break
                else:
                    if ifs.fex == False:
                        sw_output.setdefault((ifs.slot, ifs.hwIf.get_unit()), {})
                        sw_output[(ifs.slot, ifs.hwIf.get_unit())][ifs.hwIf.get_hw_port()] \
                        = (ifs, stp_dict[(self.vlan)]['Interface_info'][i]['Status'])
                        mods.append(ifs.slot)
                    else:
                        nifMods = new_uintArray(16)
                        numMods = new_uintArray(1)
			# FEX HIF PC member interfaces configured in access mode and 
                        # in LACP 'I' state do not have VP VLAN Membership configured. 
			if ifs.is_access_port() == True and isInterfaceinLacpIState(ifs.longName):
			                continue
                        rc = py_get_fport_mods_for_hif(ifs.ifindex, nifMods, numMods)
                        nifMod = uintArray_getitem(nifMods, 0)
                        sw_output_vp.setdefault((nifMod, ifs.hwIf.get_unit()), {})
                        sw_output_vp[(nifMod, ifs.hwIf.get_unit())][ifs.vp] \
                        = (ifs, stp_dict[(self.vlan)]['Interface_info'][i]['Status'])
                        mods.append(nifMod)    
                        
            if mods is not None:
                umods = set(mods)
                for slot in umods:
                    x = Nxos.Module(slot)
                    modList.append(x)
            
            # Got the SW state, pass that in to the HW to validate
            return self.hwVlan.validate_stp_state(modList, sw_output, sw_output_vp)
    #####################################
    #
    # checks vlan sw intf with mcshow 
    #
    #####################################
        def validate_vlan_mcshow(self):
            mods = Nxos.Module.getOnlineFLCModules()
            all_passed = True

            vlan_id = int(self.vlan_str)
            vlan_passed = True

            stp_dict = getShowSpanningTreeDict(vlan_id)
            intf_dict = {}
            if vlan_id in stp_dict and 'Interface_info' in stp_dict[vlan_id]:
                intf_dict = stp_dict[vlan_id]['Interface_info']
            else:
                print "Warning! Not checking for access port flood list on vlan %d as STP instance does not exist" % vlan_id

	    fwd_ports_info = []
            InfoStruct = namedtuple("InfoStruct", "intf is_po hw_port")
            for intf in intf_dict:
                if intf_dict[intf]['Status'] != 'FWD':
                    continue;
                i = Nxos.Interface(_shortName = intf)
                if i.is_po():
                    for m in i.members:
                        fwd_ports_info.append(InfoStruct(m, True, i.hw_port))
	        elif i.fex == True:
	            nifindexs = new_uintArray(64)
                    num = new_uintArray(1)
	            pc_ifindex = py_get_fpc_ifidx_for_hif ((i.ifindex))
	            r = py_im_get_pc_membership( pc_ifindex,nifindexs,64)
	            for cnt in range(0, r):
                        member_ifidx = uintArray_getitem(nifindexs, cnt)
		        i = Nxos.Interface(_ifindex = member_ifidx)
		        fwd_ports_info.append(InfoStruct(i, False, i.hw_port)) 
                else:
                    fwd_ports_info.append(InfoStruct(i, False, i.hw_port))


            if not fwd_ports_info:
                print "no ports in vlan %d" % vlan_id
                return
            for mod in mods:
                for unit in range(0, mod.units):
                    hwVlan = HwVlang(mod.mod, unit, vlan_id)
                    group = hwVlan.getVlanGroup()
                    hwMcList = HwMcList(mod.mod, unit, group)
                    for fwd_port_info in fwd_ports_info:
                        fwd_port = fwd_port_info[0]
                        hw_name = fwd_port.hwIf.hw_name
                        if fwd_port.slot != mod.mod:
                            #print "skipping slot %d" % fwd_port.slot
                            continue
                        if fwd_port.unit != unit:
                            print "skipping unit %d" % fwd_port.unit
                            continue
                        if hw_name not in hwMcList.nh_list:
                            print "%s not in mc show output slot %d unit %d" % (hw_name, mod.mod, unit)
			    print "VLAN%s\t[FAIL]!!!" % vlan_id
			    vlan_passed=False
            if vlan_passed:
                print "VLAN%s Multicast Group Check\t[PASS]..." % vlan_id 
	        return True
	    else :
		print "VLAN%s Multicast Group Check\t[FAIL]..." % vlan_id
		return False
            
            if all_passed:
                print "\nConsistency Check: PASSED\n"
            else:
                print "\nConsistency Check: FAILED\n"
    
    class Vpc:
        @staticmethod
        def _getShowVpcDict():

            """
            This command parses <show vpc> output and returns various configuration in Dict format.
            There is another get method which deals with the same command but that returns only
            vPC info (getVpcDict)

            """
            ShowVpcDict = {}

            cmd_out=cli_ex('show vpc')
            match = re.search('vPC domain id\s+:\s+({0})'.format(rex.NUM),cmd_out,flags=re.I)
            if match:
                ShowVpcDict['vPC_domain_id'] = match.group(1)

            match = re.search('Peer status\s+:\s+peer adjacency formed ok',cmd_out,flags=re.I)
            match2 = re.search('peer link not configured',cmd_out,flags=re.I)
            if match:
                ShowVpcDict['Peer_status'] = 'peer_adjacency_formed_ok'
            elif match2:
                ShowVpcDict['Peer_status'] = 'peer_link_not_configured'
            else:
                ShowVpcDict['Peer_status'] = 'not_ok'

            match = re.search('vPC keep-alive status\s+:\s+peer is alive',cmd_out,flags=re.I)
            if match:
                ShowVpcDict['vPC_keep-alive_status'] = 'peer_is_alive'
            else:
                ShowVpcDict['vPC_keep-alive_status'] = 'not_alive'

            match = re.search('Configuration consistency status\s+:\s+({0})'.format(rex.ALPHA),cmd_out,flags=re.I)
            if match:
                ShowVpcDict['Configuration_consistency_status'] = match.group(1)

            match = re.search('Per-vlan consistency status\s+:\s+({0})'.format(rex.ALPHA),cmd_out,flags=re.I)
            if match:
                ShowVpcDict['Per-vlan_consistency_status'] = match.group(1)
            match = re.search('Type-2 consistency status\s+:\s+({0})'.format(rex.ALPHA),cmd_out,flags=re.I)
            if match:
                ShowVpcDict['Type-2_consistency_status'] = match.group(1)

            match = re.search('vPC role\s+:\s+({0})'.format(rex.ALPHA),cmd_out,flags=re.I)
            if match:
                ShowVpcDict['vPC_role'] =  match.group(1)

            match = re.search('vPC role\s+:\s+{0},\s+operational\s+({0})'.format(rex.ALPHA),cmd_out,flags=re.I)
            if match:
                ShowVpcDict['vPC_role'] =  match.group(1)

            match = re.search('Number of vPCs configured\s+:\s+({0})'.format(rex.ALPHA),cmd_out,flags=re.I)
            if match:
                ShowVpcDict['Number_of_vPCs_configured'] = match.group(1)

            match = re.search('Peer Gateway\s+:\s+({0})'.format(rex.ALPHA),cmd_out,flags=re.I)
            if match:
                ShowVpcDict['Peer_Gateway'] = match.group(1)

            match = re.search('Dual-active excluded VLANs\s+:\s+([0-9\-]+)',cmd_out,flags=re.I)
            if match:
                ShowVpcDict['Dual-active_excluded_VLANs'] = match.group(1)

            match = re.search('Graceful Consistency Check\s+:\s+({0})'.format(rex.ALPHA),cmd_out,flags=re.I)
            if match:
                ShowVpcDict['Graceful_Consistency_Check'] = match.group(1)

            match = re.search('Auto-recovery status\s+:\s+({0})'.format(rex.ALPHA),cmd_out,flags=re.I)
            if match:
                ShowVpcDict['Auto-recovery_status'] = match.group(1)

            #match = re.search('[0-9]+\s+(Po[0-9]+)\s+([a-z]+)\s+([0-9\-]+)',cmd_out,flags=re.I)
            match = re.search('[0-9]+\s+(Po[0-9]+)\s+([a-z]+)\s+({0})'.format(rex.VLAN_RANGE),cmd_out,flags=re.I)
            if not match:
                match = re.search('[0-9]+\s+(Po[0-9]+)\s+([a-z]+)\s+(-)',cmd_out,flags=re.I)
            if match:
                ShowVpcDict['Peer-link_Port'] = match.group(1)
                ShowVpcDict['Peer-link_Status'] = match.group(2)
                ShowVpcDict['Peer-link_Active_vlans'] = match.group(3)
            return ShowVpcDict

        @staticmethod
        def _getLongName(_shortName):
            sh = None
            if "Eth" in _shortName or "eth" in _shortName:
                sh = 'Ethernet' + _shortName[3:]

            if "Po" in _shortName or "po" in _shortName:
                sh = 'Port-channel' + _shortName[2:]

            return sh

        def __init__(self):
            self._vpcDict = Nxos.Vpc._getShowVpcDict()

        def getPeerLinkName(self):
            if 'Peer-link_Port' in self._vpcDict:
                return Nxos.Vpc._getLongName(self._vpcDict['Peer-link_Port'])
            else:
                return None

        def getPeerLinkMembers(self):
            vpcName = self.getPeerLinkName()
            if vpcName:
                po = Nxos.Interface(vpcName)
                return po.members
            else:
                return None





