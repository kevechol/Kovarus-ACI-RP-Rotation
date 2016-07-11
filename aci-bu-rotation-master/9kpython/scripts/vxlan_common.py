#################################################
#
#      File:   vxlan_common.py
#      Name:   Vijay Sampath
#
#       Description: vxlan consistency checker
#  
#
#
# Copyright (c) 1985-2014 by cisco Systems, Inc.
# All rights reserved.
#
#################################################

from onxos import *
from vxlan_common import *

# Vxlan VP = LTL - PIXM_LTL_VPL_POOL_BEGIN_V2 - INSEOR_VPL_VP_MIN
def getVxlanVpFromLtl(ltl):
    return ltl - py_libltlmap_vpl_pool_begin() + py_get_inseor_vpl_vp_min()

