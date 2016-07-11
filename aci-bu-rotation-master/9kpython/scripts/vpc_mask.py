#################################################
#
#      File:   vpc_mask.py
#      Name:   Vijay Sampath
#
#       Description: show system internal vpcm info mask 
#               (Augment later for VPC Consistency Checker)
#  
#
#
# Copyright (c) 1985-2013 by cisco Systems, Inc.
# All rights reserved.
#
#################################################

import sys,re,os,collections
from nxos import *

def getEgrMaskForModuleForVpcForIntf(mod, vpcIntfName):
    if py_pfm_is_module_online(mod-1) != 1:
        #print "Module %d is not online"%mod
        return None

    m = re.search('Eth[a-z,A-Z]*([0-9]+).*', vpcIntfName)
    if m is None:
        print "Invalid VPC Interface Name %s"%vpcIntfName
        return None
    slot = int(m.group(1))
    if py_pfm_is_module_online(slot-1) != 1:
        print "Module %d is not online"%slot
        return None
    vpcIntf = Nxos.Interface(vpcIntfName)
    hwEgrMasks = []
    m = Nxos.Module(mod)
    for unit in range(0, m.units):
        #print ("mod = %d dmod = %d unit = %d hw_port = %d") % (mod, vpcIntf.dmod, unit, vpcIntf.hw_port)
        hwEgrMask = HwEgrMask(mod, unit, vpcIntf.dmod, vpcIntf.hw_port)
        hwEgrMasks.append(hwEgrMask.getEgrMask())
        #print ("mask for unit %d = 0x%x") % (unit, hwEgrMasks[unit])

    return hwEgrMasks

def printEgrMaskHelper(mod, vpcIntfName, egrMasks):
    intfNames = []
    if py_pfm_is_module_online(mod-1) != 1:
        print "Module %d is not online"%mod
        return
    modObj = Nxos.Module(mod)
    unit = 0
    for mask in egrMasks:
        if not intfNames:
            intfNames = getIfNamesGivenBitmap(modObj, unit, mask)
        else:
            intfNames += getIfNamesGivenBitmap(modObj, unit, mask)
        unit += 1
    
    if not intfNames:
        return
    print "[Src Port %s]:" % getShortIfName(vpcIntfName),
    print ','.join(name for name in intfNames)


def printEgrMaskForModuleForIntf(mod, vpcIntfName):
    if py_pfm_is_module_online(mod-1) != 1:
        print "Module %d is not online"%mod
        return
    egrMasks = getEgrMaskForModuleForVpcForIntf(mod, vpcIntfName)
    if egrMasks is None:
        print("Could not retrieve Egress Masks due to an error.")
        print("Check if the target module and Module that carries the VPC are online")
        return
    printEgrMaskHelper(mod, vpcIntfName, egrMasks)

######################################################
# This prints the egress mask only for all sources for
# a module
######################################################
def printEgrMaskForModule(mod):
    if py_pfm_is_module_online(mod-1) != 1:
        print "Module %d is not online"%mod
        return
    m = Nxos.Module(mod)
    for unit in range(0, m.units):
        hw = HwEgrMaskTable(mod, unit)
        print "Masked ports for Module %d, Unit %d:"%(mod, unit)
        rows = hw.getAll()

######################################################
# This prints the egress mask only for all source ports
# and all modules
######################################################
def printEgrMaskForAllModules():
    mods = Nxos.Module.getOnlineModules()
    for mod in mods:
        printEgrMaskForModule(mod.mod)


######################################################
# Not used in CLI currently - but may be useful later
# This gets the egress mask only for the VPC members
######################################################
def getEgrMaskForAllModulesForVpc():
    mods = Nxos.Module.getOnlineModules()
    hwEgrMasks = {}
    for mod in mods:
        hwEgrMasks[mod.mod] = getEgrMaskForModuleForVpc(mod.mod)

    return hwEgrMasks

######################################################
# Not used in CLI currently - but may be useful later
# This gets the egress mask only for the VPC members
######################################################
def getEgrMaskForModuleForVpc(mod):
    if py_pfm_is_module_online(mod-1) != 1:
        print "Module %d is not online"%mod
        return
    vpc = Nxos.Vpc()
    vpcMembers = vpc.getPeerLinkMembers()
    if not vpcMembers:
        print "NO VPC peer link"
        return

    hwEgrMasks = {}
    for intf in vpcMembers:
        #print "Getting Egress Mask for source port %s"%intf.longName
        hwEgrMasks[intf.longName] = getEgrMaskForModuleForVpcForIntf(mod, intf.longName)

    return hwEgrMasks

######################################################
# Not used in CLI currently - but may be useful later
# This prints the egress mask only for the VPC members
######################################################
def printEgrMaskForModuleForVpc(mod):
    if py_pfm_is_module_online(mod-1) != 1:
        print "Module %d is not online"%mod
        return
    vpc = Nxos.Vpc()
    vpcMembers = vpc.getPeerLinkMembers()
    if not vpcMembers:
        print "NO VPC peer link"
        return
    allEgrMasks = getEgrMaskForModuleForVpc(mod)

    for intf in vpcMembers:
        egrMasks = allEgrMasks[intf.longName]
        if egrMasks is None:
            print("Could not retrieve Egress Masks due to an error.")
            print("Check if the target module and Module that carries the VPC are online")
            return
        printEgrMaskHelper(mod, intf.longName, egrMasks)

######################################################
# Not used in CLI currently - but may be useful later
# This prints the egress mask only for the VPC members
######################################################
def printEgrMaskForAllModulesForVpc():
    vpc = Nxos.Vpc()
    vpcMembers = vpc.getPeerLinkMembers()
    if not vpcMembers:
        print "NO VPC peer link"
        return
    allEgrMasks = getEgrMaskForAllModulesForVpc();

    mods = Nxos.Module.getOnlineModules()
    for intf in vpcMembers:
        for mod in mods:
            egrMasks = allEgrMasks[mod.mod][intf.longName]
            if egrMasks is None:
                print("Could not retrieve Egress Masks due to an error.")
                print("Check if the target module and Module that carries the VPC are online")
                return
            printEgrMaskHelper(mod.mod, intf.longName, egrMasks)

######################################################
# handler called from C code
######################################################
from onxos import *
def show_vpc_mask(_modList, _vpcIntfList = None):
    mod = _modList[0]
    if mod == 0 and not _vpcIntfList:
        printEgrMaskForAllModules()
    elif mod != 0 and not _vpcIntfList:
        printEgrMaskForModule(mod)
    elif mod != 0 and _vpcIntfList:
        printEgrMaskForModuleForIntf(mod, _vpcIntfList[0])
    else:
        print "Don't support print based on source-interface for all modules"
