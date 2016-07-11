#################################################
#
#      File:   vxlan_show.py
#      Name:   Vijay Sampath
#
#       Description: vxlan show commands
#
#
#
# Copyright (c) 1985-2015 by cisco Systems, Inc.
# All rights reserved.
#
#################################################

import sys
import signal
from onxos import *

from vxlan_common import *

def log_uncaught_exceptions(ex_cls, ex, tb):
  sys.exit(0)

def show_vxlan(min_vlan = None, max_vlan = None):
   sys.excepthook = log_uncaught_exceptions
   if min_vlan == None:
      min_vlan = 1
   if max_vlan == None:
      max_vlan = 4096

   print "Vlan\t\tVN-Segment"
   print "====\t\t=========="
   for i in range (min_vlan, max_vlan + 1):
      vlan = Nxos.Vlan(i)
      if vlan.vnseg:
         print "%d\t\t%d" % (i, vlan.vnseg)
         sys.stdout.flush()

def show_vxlan_int(if_index_list = None, if_name_list = None):
   sys.excepthook = log_uncaught_exceptions

   print "Interface\tVlan\tVPL Ifindex\tLTL\t\tHW VP"
   print "=========\t====\t===========\t===\t\t====="
   for name in if_name_list:
      if "." in name:
         continue

      if "Eth" not in name and "nnel" not in name:
         continue

      intf = Nxos.Interface(name)
      (cnt, vlan_list, vpl_list) = intf.get_vpl_list()
      for i in range (0, cnt):
         di = py_pixm_lib_ifidx_to_di(vpl_list[i])
         ifidx = vpl_list[i]
         if (di != 0xffffffff):
           if(py_mcecm_api_is_pc_mct(intf.ifindex)):
             # This is an MCT, Vxlan vlans over MCT need to be printed
             mct_syn_ifidx = py_pixm_lib_vlan_to_mct_syn_ifidx(vlan_list[i]);
             if(mct_syn_ifidx != 0):
                 di_mct = py_pixm_lib_ifidx_to_di(mct_syn_ifidx)
                 if (di_mct != 0xffffffff):
                     #print "%-16s%d\t0x%x\t0x%x\t\t%d" % (intf.shortName, vlan_list[i], ifidx, di, getVxlanVpFromLtl(di))
                     #print "%-16s%d\t0x%x\t0x%x\t\t%d%s" % (intf.shortName, vlan_list[i], mct_syn_ifidx, di, getVxlanVpFromLtl(di),"(Alt-MCT)")
                     print "%-16s%d\t0x%x\t0x%x\t\t%d\n%-16s%d\t0x%x\t0x%x\t\t%d%s" % (intf.shortName, vlan_list[i], ifidx, di, getVxlanVpFromLtl(di), intf.shortName, vlan_list[i], mct_syn_ifidx, di_mct, getVxlanVpFromLtl(di_mct),"(Alt-MCT)")
           else:
             print "%-16s%d\t0x%x\t0x%x\t\t%d" % (intf.shortName, vlan_list[i], ifidx, di, getVxlanVpFromLtl(di))
           sys.stdout.flush()
