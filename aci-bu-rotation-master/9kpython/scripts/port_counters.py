################################################
#
#      File:   port_counters.py
#      Name:   
#
#      Description: 
#
#
#
# Copyright (c) 1985-2013, 2015-2016 by cisco Systems, Inc.
# All rights reserved.
#
#################################################
import cProfile
from onxos import *
import re
from hw.hwobj import *
from libnxos_ext_api import *
from nxos_utils import *
from tahoe import *
from libbcmshell import *
import array
import sys
import os
import time
import subprocess as sp
import pexpect  
import timeit

# Taken from ACLQOS_TR2_GID_FM_EGR_PORTGRP_ACLS_EID_BASE=4095 + 256
# Need to change if the orginal code changes, in future export this
# nxos variable through swig
# Stat id is fmHGStatIdBase + port# : For HG0 aka Port 1, stat id is 4352
fmHGStatIdBase = 4351

# This id dynamically generated in code, does not change unless
# new entries added. For now fixed the number for Seymor
# Can eb dynamically derived from o/p of
# "show system internal access-list sup-redirect-stats module 4 instance 0"
# Stat id is lcHGStatIdBase + port# : For HG0 aka Port 1, stat id is 4354
lcHGStatIdBase = 4353

fwdRxDropStats = [ 'RDBGC0', 'RDBGC4', 'RDBGC6', 'RDBGC7', 'RDBGC8' ]
fwdTxDropStats = [ 'TDBGC1', 'TDBGC3', 'TDBGC5' ]
rxPktErrorStats = [ 'IUNHGI', 'IUNKOPC', 'RFCS',
                    'RALN', 'RFLR', 'RERPKT', 'RJBR', 'RSCHCRC', 'RUND', 'RMTUE' ]
txPktErrorStats = [ 'TJBR', 'TFCS', 'TRPKT', 'RMTUE', 'TUFL', 'TPCE' ]
rxQOSDropStats = [ 'RDISC', 'DROP_PKT_ING', 'DROP_PKT_IMTR', 'DROP_PKT_YEL', 'DROP_PKT_RED' ]
txQOSDropStats = [ 'MCQ_DROP_PKT(0)', 'MCQ_DROP_PKT(1)', 'MCQ_DROP_PKT(2)',
                   'MCQ_DROP_PKT(3)', 'MCQ_DROP_PKT(4)', 'MCQ_DROP_PKT(5)',
                   'MCQ_DROP_PKT(6)', 'MCQ_DROP_PKT(7)', 'MCQ_DROP_PKT(8)', 'MCQ_DROP_PKT(9)',
                   'UCQ_DROP_PKT(0)', 'UCQ_DROP_PKT(1)', 'UCQ_DROP_PKT(2)',
                   'UCQ_DROP_PKT(3)', 'UCQ_DROP_PKT(4)', 'UCQ_DROP_PKT(5)',
                   'UCQ_DROP_PKT(6)', 'UCQ_DROP_PKT(7)', 'UCQ_DROP_PKT(8)', 'UCQ_DROP_PKT(9)' ]
rxQOSDropStats_Rngr = [ 'RDISC' ]
txQOSDropStats_Rngr = [ 'MCQ_DROP_PKT(0)', 'MCQ_DROP_PKT(1)', 'MCQ_DROP_PKT(2)',
                   'MCQ_DROP_PKT(3)', 'MCQ_DROP_PKT(4)', 'MCQ_DROP_PKT(5)',
                   'MCQ_DROP_PKT(6)', 'MCQ_DROP_PKT(7)', 'MCQ_DROP_PKT(8)', 'MCQ_DROP_PKT(9)',
                   'UCQ_DROP_PKT(0)', 'UCQ_DROP_PKT(1)', 'UCQ_DROP_PKT(2)',
                   'UCQ_DROP_PKT(3)', 'UCQ_DROP_PKT(4)', 'UCQ_DROP_PKT(5)',
                   'UCQ_DROP_PKT(6)', 'UCQ_DROP_PKT(7)' ]


class PersistentVsh(object):
    spawn_args = ["/lc/isan/bin/vsh_lc_tor", "-E vshro#", "-n"]

    def __init__(self):
        env = os.environ
        env["LD_PRELOAD"] = ""
        self.prompt = "vshro#"
        self.proc = pexpect.spawn(" ".join(PersistentVsh.spawn_args))
        self.proc.expect(self.prompt)

    def execute(self, cmd):
        self.proc.sendline(cmd.strip())
        self.proc.expect(self.prompt)
        # Delete the return code
        output = self.proc.before.split("\n")
        # (returncode, data)
        return "\n".join(output[1:])

check_asic_type = nxos_utils.get_asic_type()
if check_asic_type is 'dav' or check_asic_type is 'lac':
    #from vshro import *
    import atexit

    def kill_vsh():
        global p

        p.proc.terminate()


    p = PersistentVsh()
    atexit.register(kill_vsh)

    def runVshCmd(cmd):
        return p.execute(cmd)





def getIntStatsByCategory(stats, counters):
    total = 0
    for stat in stats:
        if(stat in counters):
            total = total + counters[stat]
    return total

def display_counter_buckets_description():
        #print what all counter buckets mean
        print ""
        print "Forward Rx Drops = [",
        for name in fwdRxDropStats:
            print name,
        print "]" 
        print "Forward Tx Drops = [",
        for name in fwdTxDropStats:
            print name,
        print " (excludes expected Multicast drops)]"
        print "ErrorPkt Rx Drops = [",
        for name in rxPktErrorStats:
            print name,
        print "]"
        print "ErrorPkt Tx Drops = [",
        for name in txPktErrorStats:
            print name,
        print "]"
        print "QOS Rx Drops = [",
        for name in rxQOSDropStats:
            print name,
        print "]"
        print "QOS Tx Drops = [",
        for name in txQOSDropStats:
            print name,
        print "]"
        print "RDBGC0 = [ RIPD4 RIPD6 RDISC PDISC ]"
        print "         Use following command for detailed breakup of RDBGC0 counter"
        print "         slot <#> show hardware internal interface indiscard-stats instance <#> asic-port <#>"
        print "RDBGC1 = [ IMBP ]   RDBGC2 = [ RIMDR ]   RDBGC3 = [ RIPD4 ] RDBGC4 = [ RPORTD ]"
        print "RDBGC5 = [ PDISC ]   RDBGC6 = [ RFILDR ]   RDBGC7 = [ RDROP ] RDBGC8 = [ VLANDR ]"
        print "TDBGC1 = [ TIPD6 TIPMCD6 ]   TDBGC3 = [ TPKTD ]   TDBGC5 = [ TIPMCD4 TIPMCD6 ]"
        print ""

def display_cpu_counter_cstat_description():
        #print what all counter buckets mean
        print ""
        print "-" * 52
        print "RDBGC0 = [ RIPD4 RIPD6 RDISC PDISC ]"
        print "         Use following command for detailed breakup of RDBGC0 counter"
        print "         slot <#> show hardware internal interface indiscard-stats instance <#> asic-port <#>"
        print "RDBGC1 = [ IMBP ]   RDBGC2 = [ RIMDR ]   RDBGC3 = [ RIPD4 ] RDBGC4 = [ RPORTD ]"
        print "RDBGC5 = [ PDISC ]   RDBGC6 = [ RFILDR ]   RDBGC7 = [ RDROP ] RDBGC8 = [ VLANDR ]"
        print "TDBGC1 = [ TIPD6 TIPMCD6 ]   TDBGC3 = [ TPKTD ]   TDBGC5 = [ TIPMCD4 TIPMCD6 ]"
        print "-" * 52
        print ""

def display_counters(counters, snmp):
        if len(counters) == 0:    
            print " -----  No counters found  ------"
            return

        print "%-20s" % ' '
        print "Detailed Counters:"

        if snmp:
            print "%-40s" % 'Counter ', "%12s" % 'Value'
            print "-" * 40, "-" * 12
        else:
            print "%-20s" % 'Counter ', "%12s" % 'Value'
            print "-" * 20, "-" * 12

        for key,value in counters.iteritems():
            if value == 0:
                continue
            if snmp:
                print "%-40s" % key, "%12d" % value
            else:
                print "%-20s" % key, "%12d" % value

def port_counters_show_module(_ifIdxList, _ifNameList):                    
    try:
        print "Important Counters/Drops"
        print "-" * 15, "-" * 9, "-" * 9, "-" * 9, "-" * 9, "-" * 9, "-" * 9
        print "%-15s" % 'Interface Name', "%9s" % 'Forward', "%9s" % 'Forward',
        print "%9s" % 'Error Pkt', "%9s" % 'Error Pkt', "%9s" % 'QOS Rx',
        print "%9s" % 'QOS Tx'
        print "%-15s" % ' ', "%9s" % 'RxDrops', "%9s" % 'TxDrops', "%9s" % 'RxDrops',
        print "%9s" % 'TxDrops', "%9s" % 'Drops', "%9s" % 'Drops'

        print "-" * 15, "-" * 9, "-" * 9, "-" * 9, "-" * 9, "-" * 9, "-" * 9
        listIdx = 0
        for name in _ifNameList:                                                    
            #not supporting sub interfaces.
            if "." in name:
                listIdx = listIdx + 1
                continue

            i = Nxos.Interface(name)                                  
            if i is None:
                print " -----  Not a valid port ------"
                return

            if i.is_port_valid == False:
                # most probably the dummy port in Nagano + Moonshot
                listIdx = listIdx + 1
                continue

            # exclude north star ports. Non-NS ports have nspid as 255
            if i.hwIf.is_nsport():
                listIdx = listIdx + 1
                continue

            counters = i.get_hw_counters_dict()                                             
            if len(counters) == 0:                                                    
               print "'%-15s'" % i.longName, "  -----  No counters found  ------"
               return

            fwdRxTotal = getIntStatsByCategory(fwdRxDropStats, counters)
            fwdTxTotal = getIntStatsByCategory(fwdTxDropStats, counters)
            rxErrorPktTotal = getIntStatsByCategory(rxPktErrorStats, counters)
            txErrorPktTotal = getIntStatsByCategory(txPktErrorStats, counters)

            if(_ifIdxList == None):
                rngr = py_im_is_ifindex_ranger_attached(i.get_if_index_from_if_long_name(name))
            else:
                rngr = py_im_is_ifindex_ranger_attached(_ifIdxList[listIdx])

            if(rngr == False):
                rxQOSDropTotal = getIntStatsByCategory(rxQOSDropStats, counters)
                txQOSDropTotal = getIntStatsByCategory(txQOSDropStats, counters)
            else:
                rxQOSDropTotal = getIntStatsByCategory(rxQOSDropStats_Rngr, counters)
                txQOSDropTotal = getIntStatsByCategory(txQOSDropStats_Rngr, counters)

            print "%-15s" % i.longName, "%9d" % fwdRxTotal, "%9d" % fwdTxTotal, "%9d" % rxErrorPktTotal,
            print "%9d" % txErrorPktTotal, "%9d" % rxQOSDropTotal, "%9d" % txQOSDropTotal

            listIdx = listIdx + 1
        print "-" * 15, "-" * 9, "-" * 9, "-" * 9, "-" * 9, "-" * 9, "-" * 9

        if len(_ifNameList) == 1:
            print "Summary view may double count some stats, look at Detailed Counters"
        else:
            print "Summary view may double count some stats, check per port command for Detailed Counters breakup"
        display_counter_buckets_description()

    except:
        pass


def port_counters_tah_clear_module(_ifIdxList, _ifNameList):
    try:        
        listIdx = 0
        for name in _ifNameList:
            #not supporting sub interfaces.
            if "." in name:
                listIdx = listIdx + 1
                continue

            i = Nxos.Interface(name)
            if i is None:
                print " -----  Not a valid port ------"
                return

            if i.is_port_valid == False:
                # most probably the dummy port in Nagano + Moonshot
                listIdx = listIdx + 1
                continue

            clear_tah_port_counters(name, i.get_slice_num(), i.get_src_id())
            listIdx = listIdx + 1
    except:        
        pass


def port_counters_tah_show_module(_ifIdxList, _ifNameList):
    try:   	 
        not_used_drop_codes = {"0","2","17","23","24","27","28","29","30","31","32","33","34","35","36","37","39","42","47","48","49"}
        print "Important Counters/Drops"
        print "-" * 15, "-" * 96
        print "%-15s" % 'Interface Name', "%-96s" %'Drop Reasons for the Interface, See below output for detail if any'
        print "-" * 15, "-" * 96
        a = 95
        print "%-15s" %' ',
        while (a>=0):
            if str(a) in not_used_drop_codes:
                a = a-1
            else:
                print "|%d" %(a/10),;sys.stdout.softspace=False;
                a = a-1
        print ""
        print "%-15s" %' ',
        a = 95
        while (a>=0):
            if str(a) in not_used_drop_codes:
                a = a -1
            else:
                print "|%d" %(a%10),;sys.stdout.softspace=False;
                a = a-1
        print ''
        listIdx = 0
        
	drop_codes_marked_str = []
        for name in _ifNameList:
            #not supporting sub interfaces.
            if "." in name:
                listIdx = listIdx + 1
                continue

            i = Nxos.Interface(name)
            if i is None:
                print " -----  Not a valid port ------"
                return

            if i.is_port_valid == False:
                # most probably the dummy port in Nagano + Moonshot
                listIdx = listIdx + 1
                continue
            
            counters = steps_counters(name, i.get_slice_num(), i.get_src_id())
            if len(counters) == 0:
               print "'%-15s'" % i.longName, "  -----  No counters found  ------"
               return
	    displayString = ''
	    displayString = displayString + ( get_bits_set(counters[2]) )
	    displayString = displayString + ( get_bits_set(counters[1]) )
	    displayString = displayString + ( get_bits_set(counters[0]) )
	    #print "%-15s" % i.longName, "%s" %displayString
	    ttstr = ''
            j = 95
            for s in displayString:
                if str(j) in not_used_drop_codes:
                        j = j - 1
                        continue
                else:
                        if '1' in s:
                                ttstr = ttstr + '|X'
                                if str(j) in drop_codes_marked_str:
                                    j = j-1
                                else:
                                    drop_codes_marked_str.append(str(j))
                                    j = j-1
                        else:
                                ttstr = ttstr + '|.'
                                j = j-1


            print "%-15s"% i.longName, "%s" %ttstr
            listIdx = listIdx + 1
            
        drop_code_strings_dict = get_drop_code_dict()
        print ''
        print "Drop Conditions"
        print "-" * 15, "-" * 96
        print ''
        drop_codes_marked_str.sort()
        for c in drop_codes_marked_str:
                print c +" : "+ drop_code_strings_dict[c]
        print ''
    except:        
        pass
            



def get_bits_set(MaskVal):
    temp = MaskVal.lower().split("0x")
    binary_string = ''
    for s in temp[1]:
        if s is '0':
           binary_string = binary_string + '0000'
        if s is '1':
           binary_string = binary_string + '0001'
        if s is '2':
           binary_string = binary_string + '0010'
        if s is '3':
           binary_string = binary_string + '0011'
        if s is '4':
           binary_string = binary_string + '0100'
        if s is '5':
           binary_string = binary_string + '0101'
        if s is '6':
           binary_string = binary_string + '0110'
        if s is '7':
           binary_string = binary_string + '0111'
        if s is '8':
           binary_string = binary_string + '1000'
        if s is '9':
           binary_string = binary_string + '1001'
        if s is 'a':
           binary_string = binary_string + '1010'
        if s is 'b':
           binary_string = binary_string + '1011'
        if s is 'c':
           binary_string = binary_string + '1100'
        if s is 'd':
           binary_string = binary_string + '1101'
        if s is 'e':
           binary_string = binary_string + '1110'
        if s is 'f':
           binary_string = binary_string + '1111'

    
    return binary_string



def steps_counters( ifname, slice_num, src_id):
    try:
        valA = []
	temp0 = []
	temp1 = []
	temp2 = []
	strcmd = ""
	strcmd = 'debug ha in tah modi as 0 sli '+str(slice_num)+' ta tah_dav_lud_cfg_port_drop_addr 0 1 addr='+str(src_id)
	
	runVshCmd(strcmd)
        strcmd ='debug hardware internal tah dump asic 0 slice '+str(slice_num)+' table tah_dav_lud_sta_port_drop_status'
        strout = runVshCmd(strcmd)
	
        lines = strout.split(" ")
        for line in lines:
                if 'val_0' in line:
                        temp0 = line.split("=")
                        valA.append (temp0[1])
                if 'val_1' in line:
                        temp1 = line.split("=")
                        valA.append (temp1[1])
                if 'val_2' in line:
                        temp2 = line.split("=")
                        valA.append (temp2[1])
	#clear_tah_port_counters(ifname,slice_num,src_id)
        return valA
    except:
        pass

def clear_tah_port_counters(ifname, slice_num, src_id):
    try:
        
        strcmd = ""

        strcmd = 'debug ha in tah modi as 0 sli '+str(slice_num)+' ta tah_dav_lud_cfg_port_drop_addr 0 1 addr='+str(src_id)
        runVshCmd(strcmd)       
        
        strcmd = 'debug ha inter tah modi as 0 sl '+str(slice_num)+' ta tah_dav_lud_cfg_clear_drop 0 1 port_status=1'
        runVshCmd(strcmd)

        strcmd = 'debug ha inter tah modi as 0 sl '+str(slice_num)+' ta tah_dav_lud_cfg_clear_drop 0 1 port_status=0'
        runVshCmd(strcmd)
    except:
        pass


def get_drop_code_dict():
    drop_code_dict = {"0":"TAHOE Ingress DROP_MEM_ERR","1":"TAHOE Ingress DROP_PARSE_ERR",
                  "2":"TAHOE Ingress DROP_EOF_ERR","3":"TAHOE Ingress DROP_OUTER_IDS_G0",
                  "4":"TAHOE Ingress DROP_OUTER_IDS_G1","5":"TAHOE Ingress DROP_OUTER_IDS_G2",
                  "6":"TAHOE Ingress DROP_OUTER_IDS_G3","7":"TAHOE Ingress DROP_OUTER_IDS_G4",
                  "8":"TAHOE Ingress DROP_OUTER_IDS_G5","9":"TAHOE Ingress DROP_OUTER_IDS_G6",
                  "10":"TAHOE Ingress DROP_OUTER_IDS_G7","11":"TAHOE Ingress DROP_OUTER_XLATE_MISS",
                  "12":"TAHOE Ingress DROP_INFRA_ENCAP_SRC_TEP_MISS","13":"TAHOE Ingress DROP_INFRA_ENCAP_TYPE_MISMATCH",
                  "14":"TAHOE Ingress DROP_UC_TENANT_MYTEP_ROUTE_MISS","15":"TAHOE Ingress DROP_TENANT_MYTEP_BRIDGE_MISS",
                  "16":"TAHOE Ingress DROP_ARP_ND_UCAST_MISS","17":"TAHOE Ingress DROP_QIQ_EXPECT_2_QTAGS",
                  "18":"TAHOE Ingress DROP_MC_DVIF_MISS","19":"TAHOE Ingress DROP_SHARD_OVERRIDE_VLAN_XLATE_MISS",
                  "20":"TAHOE Ingress DROP_FCF_CHECK_FAILED","21":"TAHOE Ingress DROP_TTL_EXPIRED",
                  "22":"TAHOE Ingress DROP_SECURITY_GROUP_DENY","23":"TAHOE Ingress DROP_LOOPBACK_OUTER_HEADER_MISMATCH",
                  "24":"TAHOE Ingress DROP_OVERLAYL2_OUTER_HEADER_MISMATCH","25":"TAHOE Ingress DROP_MC_IIC",
                  "26":"TAHOE Ingress DROP_MC_GIPO_MISS","27":"TAHOE Ingress DROP_UC_HIT_NO_PATH",
                  "28":"TAHOE Ingress DROP_UNUSED","29":"TAHOE Ingress DROP_AC_SUP_DROP",
                  "30":"TAHOE Ingress DROP_AC_POL_DROP","31":"TAHOE Ingress DROP_AC_STORM_POL_DROP",
                  "32":"TAHOE Ingress DROP_FAST_CONV_LOOP_PREVENT","33":"TAHOE Ingress DROP_PP_BOUNCE_MYTEP_MISS",
                  "34":"TAHOE Ingress DROP_VLAN_MBR_INPUT","35":"TAHOE Ingress DROP_IEOR_PP_RETURN_PC_2_HG2_MISS",
                  "36":"TAHOE Ingress DROP_IEOR_UPLINK_UC_SAME_IF","37":"TAHOE Ingress DROP_IEOR_SPINE_PROXY_PC_2_HG2_MISS",
                  "38":"TAHOE Ingress DROP_VIF_MISS","39":"TAHOE Ingress DROP_UNEXPECTED_VFT",
                  "40":"TAHOE Ingress DROP_MISSING_VNTAG","41":"TAHOE Ingress DROP_VLAN_XLATE_MISS",
                  "42":"TAHOE Ingress DROP_RBID_FTAG_MISS","43":"TAHOE Ingress DROP_IP_MTU_CHECK_FAILURE",
                  "44":"TAHOE Ingress DROP_UC_RPF_FAILURE","45":"TAHOE Ingress DROP_MC_RPF_FAILURE",
                  "46":"TAHOE Ingress DROP_L3_BINDING_FAILURE","47":"TAHOE Ingress DROP_IP_UNICAST_FIB_MISS",
                  "48":"TAHOE Ingress DROP_FIB_SA","49":"TAHOE Ingress DROP_FIB_DA",
                  "50":"TAHOE Ingress DROP_NSH_NOT_ALLOWED","51":"TAHOE Ingress DROP_SRC_VLAN_MBR",
                  "52":"TAHOE Ingress DROP_NSH_SRC_SW_CHK_FAILED","53":"TAHOE Ingress DROP_L2MP_IIC_FAILED",
                  "54":"TAHOE Ingress DROP_L2MP_ON_CE_BD","55":"TAHOE Ingress DROP_L2MP_ENCAP_FROM_EDGE",
                  "56":"TAHOE Ingress DROP_L2MP_NOENCAP_FROM_CORE","57":"TAHOE Ingress DROP_OUTER_TTL_EXPIRED",
                  "58":"TAHOE Ingress DROP_INCORRECT_VNTAG_TYPE","59":"TAHOE Ingress DROP_L2MP_FTAG_COMP_MISS",
                  "60":"TAHOE Ingress DROP_IPV6_UC_LINK_LOCAL_CROSS_BD","61":"TAHOE Ingress DROP_IPV6_MC_SA_LOCAL_DA_GLOBAL_SVI",
                  "62":"TAHOE Ingress DROP_IPV6_MC_SA_LOCAL_DA_GLOBAL_L3IF","63":"TAHOE Ingress DROP_ROUTING_DISABLED",
                  "64":"TAHOE Ingress DROP_FC_LOOKUP_MISS","65":"TAHOE Ingress DROP_NO_SGT_FROM_CORE",
                  "66":"TAHOE Ingress DROP_IP_SELF_FWD_FAILURE","67":"TAHOE Ingress DROP_ACL_DROP",
                  "68":"TAHOE Ingress DROP_SMAC_MISS","69":"TAHOE Ingress DROP_SECURE_MAC_MOVE",
                  "70":"TAHOE Ingress DROP_NON_SECURE_MAC","71":"TAHOE Ingress DROP_L2_BINDING_FAILURE",
                  "72":"TAHOE Ingress DROP_INNER_IDS_G0","73":"TAHOE Ingress DROP_INNER_IDS_G1",
                  "74":"TAHOE Ingress DROP_INNER_IDS_G2","75":"TAHOE Ingress DROP_INNER_IDS_G3",
                  "76":"TAHOE Ingress DROP_INNER_IDS_G4","77":"TAHOE Ingress DROP_INNER_IDS_G5",
                  "78":"TAHOE Ingress DROP_INNER_IDS_G6","79":"TAHOE Ingress DROP_INNER_IDS_G7",
                  "80":"TAHOE Ingress DROP_INFRA_ENCAP_SRC_TEP_DROP","81":"TAHOE Ingress DROP_SPLIT_HORIZON_CHECK",
                  "82":"TAHOE Ingress DROP_MC_FIB_MISS","83":"TAHOE Ingress DROP_MC_L2_MISS",
                  "84":"TAHOE Ingress DROP_UC_DF_CHECK_FAILURE","85":"TAHOE Ingress DROP_UC_PC_CFG_TABLE_DROP",
                  "86":"TAHOE Ingress DROP_ILLEGAL_EXPL_NULL","87":"TAHOE Ingress DROP_MPLS_LOOKUP_MISS",
                  "88":"TAHOE Ingress DROP_OUTER_CBL_CHECK","89":"TAHOE Ingress DROP_NULL_SHARD_WITH_E_BIT_SET",
                  "90":"TAHOE Ingress DROP_LB_DROP","91":"TAHOE Ingress DROP_NAT_FRAGMENT",
                  "92":"TAHOE Ingress DROP_ILLEGAL_DCE_PKT","93":"TAHOE Ingress DROP_DCI_VNID_XLATE_MISS",
                  "94":"TAHOE Ingress DROP_DCI_SCLASS_XLATE_MISS","95":"TAHOE Ingress DROP_DCI_2ND_UC_TRANSIT"
                  }
    return drop_code_dict




def port_counters_show_interface(_snmpList, _ifNameList):
    try:
        port_counters_show_module(None, _ifNameList)                                      
        ifName = _ifNameList[0]
        snmp = _snmpList[0]
        print "-" * 15, "-" * 9, "-" * 9, "-" * 9, "-" * 9, "-" * 9, "-" * 9
        i = Nxos.Interface(ifName)                                               
        if snmp:
            counters = i.get_hw_counters_snmp_dict()                                                           
        else:
            counters = i.get_hw_counters_dict()                                                           

        display_counters(counters, snmp)

    except:
        pass

def port_counters_get_iis_per_module (module):                                              
    try:
        hwMod = HwMod(module)
        hgports = hwMod.get_all_hg_ports()

        return hgports

    except:
        pass
# Here is the output to parse for valid and invalid entries
# switch# bcm-shell module 24 " fp stat get statid=0x110b t=p"
# Executing  fp stat get statid=0x110b t=p on bcm shell on module 24
# The value is: 0x00
# switch# 
# switch# 
# switch# bcm-shell module 24 " fp stat get statid=0x1100 t=p"
# Executing  fp stat get statid=0x1100 t=p on bcm shell on module 24
# FP(unit 0) Error: bcm_field_stat_get() failed: Entry not found
def getMcastDropCount (fpStatOutput):
    try:
        fp_lines=fpStatOutput.split("\n")
        for fp_line in fp_lines:
            if fp_line is None:   #last line of output has white spaces, ignore
                continue
            g = re.search(r'The value is: ([0-9,a-fA-FxX]+)\s*', fp_line)
            if g is None:
                continue
            numstr = g.group(1).replace(',', '')
            if numstr.upper().startswith('0X'):
                count = int(numstr, 16)
            else:
                count = int(numstr)
            return count
        return 0

    except:
       pass

def getHGMcastDropCount (module, unit, port):
    try:
        statIdBase = 0
        lookupStr = 'SRC & DEST Higig Drop ACL for Port ' + str(port) + ' '
        vshCmd = 'show system internal access-list sup-redirect-stats module ' + str(module) + ' instance ' + str(unit) + ' | include \"' + lookupStr + '\"'
        output = runVshCmd(vshCmd)

        out = output.split(' ')
        for data in out:
            if len(data) == 0:
                continue
            else:
                statIdBase = int(data)
                break

        if 21 <= module <= 26:  #FM
            #fpStatCmd = 'fp stat get statid=' + str(fmHGStatIdBase + port) + ' t=p'
            fpStatCmd = 'fp stat get statid=' + str(statIdBase) + ' t=p'
            fpOutput = runBcmCmd(module, unit, fpStatCmd)
        else:                   #LC
            #fpStatCmd = 'fp stat get statid=' + str(lcHGStatIdBase + port) + ' t=p'
            fpStatCmd = "fp stat get statid=" + str(statIdBase) + " t=p"
            fpOutput = runBcmCmd(module, unit, fpStatCmd)
        mcastDropCount = getMcastDropCount(fpOutput)
        return mcastDropCount
    except:
        pass

def port_counters_show_fabric_ports (module, ports):
    try:
        print "Important Counters/Drops"
        print "-" * 15, "-" * 9, "-" * 9, "-" * 9, "-" * 9, "-" * 9, "-" * 9
        print "%-15s" % 'FabricInterface', "%9s" % 'Forward', "%9s" % 'Forward',
        print "%9s" % 'Error Pkt', "%9s" % 'Error Pkt', "%9s" % 'QOS Rx',
        print "%9s" % 'QOS Tx'
        print "%-15s" % ' ', "%9s" % 'RxDrops', "%9s" % 'TxDrops', "%9s" % 'RxDrops',
        print "%9s" % 'TxDrops', "%9s" % 'Drops', "%9s" % 'Drops'

        print "-" * 15, "-" * 9, "-" * 9, "-" * 9, "-" * 9, "-" * 9, "-" * 9

        for porttuple in ports:
            (unit, hgno, port) = porttuple
            hwIf = HwPort(IfType.Internal, module, unit, False, port, 0, 0)
            counters = hwIf.get_counters_dict()
            if len(counters) == 0:    
                print " -----  No counters found  ------"
                return

            fwdRxTotal = getIntStatsByCategory(fwdRxDropStats, counters)
            fwdTxTotal = getIntStatsByCategory(fwdTxDropStats, counters)
            rxErrorPktTotal = getIntStatsByCategory(rxPktErrorStats, counters)
            txErrorPktTotal = getIntStatsByCategory(txPktErrorStats, counters)
            rxQOSDropTotal = getIntStatsByCategory(rxQOSDropStats, counters)
            txQOSDropTotal = getIntStatsByCategory(txQOSDropStats, counters)
            
            # fwdTxTotal also includes the expected mcast drop counters
            # (packets dropped by HG-HG ACL aka hair pin traffic)
            # get that count and deduct from the fwdTxTotal
            mcastDropCount = getHGMcastDropCount(module, unit, port)
            if fwdTxTotal > mcastDropCount:
                fwdTxTotal = fwdTxTotal - mcastDropCount
            else:
                fwdTxTotal = 0

            portstr = repr(unit) + ' / ' + repr(port) + ' / ' + 'HG' + repr(port-1)

            print "%-15s" % portstr, "%9d" % fwdRxTotal, "%9d" % fwdTxTotal, "%9d" % rxErrorPktTotal,
            print "%9d" % txErrorPktTotal, "%9d" % rxQOSDropTotal, "%9d" % txQOSDropTotal
        print "-" * 15, "-" * 9, "-" * 9, "-" * 9, "-" * 9, "-" * 9, "-" * 9

        if len(ports) == 1:
            print "Summary view may double count some stats, look at Detailed Counters"
        else:
            print "Summary view may double count some stats, check per port command for Detailed Counters breakup"
        display_counter_buckets_description()

    except:
        pass

def port_counters_show_fabric_module (_modList, _ifNameList):
    module = _modList[0]
    port = {}
    ports = port_counters_get_iis_per_module(module)
    print "Counters for Fabric Ports:"
    print "--------------------------"

    if ports is None:    
        print " -----  Unable to find Fabric Ports ------"
        return

    if len(ports) == 0:    
        print " -----  No Fabric Ports ------"
        return
    #print "HG ports are: ", ports
    port_counters_show_fabric_ports(module, ports)

    #CSCuo98784 
    try:
	sys.stdout.close()
    except:
	pass
    try:
	sys.stderr.close()
    except:
	pass
    #end CSCuo98784

def port_counters_show_fabric_interface (_argsList, _ifNameList):
    try:
        module    = _argsList[0]
        unit      = _argsList[1]
        bcmport   = _argsList[2]
        snmp      = _argsList[3]

        hwIf = HwPort(IfType.Internal, module, unit, bcmport)
        if hwIf is None:
            print " -----  Not a valid port ------"
            return

        ports = []
        ports.append( (unit, bcmport-1, bcmport) )
        port_counters_show_fabric_ports(module, ports)
        print "-" * 15, "-" * 9, "-" * 9, "-" * 9, "-" * 9, "-" * 9, "-" * 9, "-" * 9 

        if snmp:
            counters = hwIf.get_counters_snmp_dict()
        else:
            counters = hwIf.get_counters_dict()

        display_counters(counters, snmp)

    except:
        pass

def port_counters_show_cpu_interface (_argsList, _ifNameList):
    try:
        module    = _argsList[0]
        unit      = _argsList[1]

        mods_online = Nxos.Module.getOnlineFLCModules()                     
        mod_present = 0                               
        for mod in mods_online:                                                        
            if mod.mod == module:                                            
                mod_present = 1                       
                break                                                                  

        if mod_present == 0:
            print " -----  Module is not online ------"
            return

        hwIf = HwPort(IfType.Cpu, module, unit, 0)
        if hwIf is None:
            print " -----  Not a valid port ------"
            return

        print "Counters for Module " + repr(module) + ' / ' + ' Unit ' + repr(unit) + ' / ' + 'CPU0'
        counters = hwIf.get_counters_dict()
        display_counters(counters, 0)
        display_cpu_counter_cstat_description()

    except:
        pass

def port_counters_module_is_online(module):
    mods_online = Nxos.Module.getOnlineFLCModules()                     
    if mods_online is None:
        return 0
    for mod in mods_online:                                                        
        if mod.mod == module:                                            
            return 1
    return 0

def port_counters_get_modules_from_obj(modObjlist):
    modlist = []
    mods_online = Nxos.Module.getOnlineFLCModules()                     
    if mods_online is None:
        return modlist
    for mod in mods_online:                                                        
        modlist.append(mod.mod)
    return modlist


def port_counters_clear_interface_one_module (module):
    try:
        _units = Nxos.Module(module).units
        for unit in range(_units):
            runBcmCmd(module, unit, "clear c")

        ports = port_counters_get_iis_per_module (module)
        if ports is None:    
            print " -----  Unable to find Fabric Ports ------"
            return
        if len(ports) == 0:
            return
        for porttuple in ports:
            (unit, hgno, port) = porttuple
            if 21 <= module <= 26:  #FM
                fpStatCmd = 'fp stat set statid=' + str(fmHGStatIdBase + port) + ' t=p val=0'
                #print "KSMURTY: Calling for FM mod/unit/port", module, "/", unit, "/", port, "cmd:", fpStatCmd
                fpOutput = runBcmCmd(module, unit, fpStatCmd)
            else:                   #LC
                fpStatCmd = 'fp stat set statid=' + str(lcHGStatIdBase + port) + ' t=p val=0'
                #print "KSMURTY: Calling for LC mod/unit/port", module, "/", unit, "/", port, "cmd:", fpStatCmd
                fpOutput = runBcmCmd(module, unit, fpStatCmd)

    except:
        pass


def port_counters_clear_interface_all_module (_modList, _ifNameList):
    try:
        module = _modList[0]
        if module == 0:   # means loop thru all FLC modules
           modObjlist = Nxos.Module.getOnlineFLCModules()
           if len(modObjlist) == 0:
               print "No Modules are online"
               return
           modlist = port_counters_get_modules_from_obj(modObjlist)
           if len(modlist) == 0:
               print "No Modules are online"
               return
        else:
           modlist = { module }
           if not port_counters_module_is_online(module):
               print "Module", module, "is not online"
               return

        if len(modlist) == 0:    
            return

        for module in modlist:
            port_counters_clear_interface_one_module(module)
        print ""

    except:
         pass

