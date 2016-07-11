########################################################################
#
#      File:   nxos_utils.py
#
#       Description:  Provides utility funcitons to create nxos objects.
#
#
#
# Copyright (c) 1985-2013, 2015 by cisco Systems, Inc.
# All rights reserved.
#
#######################################################################
#$Id: eor_utils.py,v 1.427 2013/06/24 23:56:03 venksrin Exp $
#ident $Source: /cvsroot/eor/systest/lib/eor_utils.py,v $ $Revision: 1.427 $

# Best Pratices for get() functions:
# 1. Use class rex as much as possible for standard regular expressions
# 2. Use underscore in keys wherever white-space appears in the output header
# 3. Add author name, description of function, sample usage examples and return value
# 4. Use python documentation format for #3 above, so that the documentation for all the functions can be pulled out easily

from nxos import *
import re
import collections
import string
import subprocess
import shlex
import sys, socket
import datetime
import time
import signal
import struct

def signal_handler_sigint(signal, frame):
    #print "user pressed CTRL+C"
    try:
       sys.stdout.close()
    except:
       pass
    try:
       sys.stderr.close()
    except:
       pass
    sys.exit(0)

MASKS=['0.0.0.0','128.0.0.0','192.0.0.0','224.0.0.0','240.0.0.0','248.0.0.0','252.0.0.0','254.0.0.0','255.0.0.0','255.128.0.0','255.192.0.0','255.224.0.0','255.240.0.0','255.248.0.0','255.252.0.0', '255.254.0.0', '255.255.0.0', '255.255.128.0', '255.255.192.0', '255.255.224.0', '255.255.240.0', '255.255.248.0', '255.255.252.0', '255.255.254.0', '255.255.255.0', '255.255.255.128', '255.255.255.192', '255.255.255.224', '255.255.255.240', '255.255.255.248', '255.255.255.252', '255.255.255.254', '255.255.255.255']

DEBUG = 0

def runVshCmdEx(cmd, _shell = False, _stdout = None):
   if DEBUG == 1:
       print "CLI: {0}".format(cmd)
   scmd = "/isan/bin/vsh -c " + "'%s'"%cmd
   args = shlex.split(scmd)
   child = subprocess.Popen(args,stdout = subprocess.PIPE, stderr= subprocess.PIPE)
   output,error = child.communicate()
   status = child.wait()
   return output,error,status

def runVshCmd(cmd, _shell = False, _stdout = None):
   if DEBUG == 1:
       print "CLI: {0}".format(cmd)
   scmd = "/isan/bin/vsh -c " + "'%s'"%cmd
   args = shlex.split(scmd)
   output,error = subprocess.Popen(args,stdout = subprocess.PIPE, stderr= subprocess.PIPE).communicate()
   return output

def cli_ex(cmd):
    return runVshCmd(cmd)

class rex:
   INTERFACE_TYPE="[Ff]ast[Ee]thernet|[Ff][Ee]th|[Gg]igabit[Ee]thernet|[Gg]ig[Ee]|[Ee]thernet|[Ee]th|[Tt]unnel ?|[Ll]oopback ?|[Pp]ort-channel ?|[Oo]verlay ?|[Nn]ull|[Mm]gmt|[Vv]lan ?|[Pp]o ?|[Ll]o ?|[Oo]vl ?|[Vv][Ll]|[Rr]epl|[Rr]eplicator|[Ff]as|[Ss]up-eth"
   INTERFACE_NUMBER="[0-9]+/[0-9]+/[0-9]+|[0-9]+/[0-9]+|[0-9]+/[0-9]+\.[0-9]+|[0-9]+\.[0-9]+|[0-9]+|[0-9]+/[0-9]+/[0-9]+"
#   INTERFACE_NAME="(?:{0})(?:{1})|[Nn]ull".format(INTERFACE_TYPE,INTERFACE_NUMBER)

   INTERFACE_NAME='(?:(?:{0})(?:{1})|(?:[Nn]ull))'.format(INTERFACE_TYPE,INTERFACE_NUMBER)
   INTERFACE_RANGE='(?:(?:{0}-[0-9]+|{0}-{0}|{0}),?)+'.format(INTERFACE_NAME)
   BCM_FP_INTERFACE='([Xx]e([0-9]+))'
   BCM_FP_INTERFACE_RANGE='[Xx]e([0-9]+)-[Xx]e([0-9]+)'

   PHYSICAL_INTERFACE_TYPE="[Ff]ast[Ee]thernet|[Ff][Ee]th|[Gg]igabit[Ee]thernet|[Gg]ig[Ee]|[Gg]i|[Ee]thernet|[Ee]th"
   PHYSICAL_INTERFACE_NUMBER="[0-9]+/[0-9]+/[0-9]+|[0-9]+/[0-9]+|[0-9]+"
   PHYSICAL_INTERFACE_NAME="(?:{0})(?:{1})".format(PHYSICAL_INTERFACE_TYPE,PHYSICAL_INTERFACE_NUMBER)

   PHYSICAL_INTERFACE_RANGE='(?:(?:{0}-[0-9]+|{0}-{0}|{0}),?)+'.format(PHYSICAL_INTERFACE_NAME)

   DEVICE_TYPE='EOR|sTOR|N7K|N5K|N3K|itgen|fanout|UNKNOWN|NA'
   FEX_MODEL='N2148T|N2232P|N2232TM-E|N2248TP-E|N2248T|NB22FJ|NB22HP'
   FEX_INTERFACE_TYPE='{0}[0-9][0-9][0-9]/[0-9]+/[0-9]+'.format(PHYSICAL_INTERFACE_TYPE)
   SWITCH_NAME = '[0-9A-Za-z_-]+'
   #VLAN_RANGE  = '[0-9]+(?:\-[0-9]+)?'

   HEX="[0-9a-fA-F]+"
   HEX_VAL="[x0-9a-fA-F]+"
   MACDELIMITER="[\.:\-]"
   # Following will match the following combinations
   #  Aa.Bb.Cc.Dd.Ee.Ff
   #  Aa-Bb-Cc-Dd-Ee-Ff
   #  Aa:Bb:Cc:Dd:Ee:Ff
   #  AaBb.CcDd.EeFf
   #  AaBb-CcDd-EeFf
   #  AaBb:CcDd:EeFf
   MACADDR=HEX+HEX+MACDELIMITER+HEX+HEX+MACDELIMITER+HEX+HEX+MACDELIMITER+HEX+HEX+MACDELIMITER+HEX+HEX+MACDELIMITER+HEX+HEX+"|"+HEX+HEX+HEX+HEX+MACDELIMITER+HEX+HEX+HEX+HEX+MACDELIMITER+HEX+HEX+HEX+HEX
   IPv4_ADDR="[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+"
   IPv6_ADDR="[0-9A-Fa-f]+:[0-9A-Fa-f:]+"

   LINK_LOCAL_IPv6_ADDR="fe80::[0-9A-Fa-f]+:[0-9A-Fa-f]+:[0-9A-Fa-f]+:[0-9A-Fa-f]+"
   IP_ADDRESS="(?:(?:{0})|(?:{1}))".format(IPv4_ADDR,IPv6_ADDR)
   NETADDR ='{0}/[0-9]+'.format(IPv4_ADDR)
   NUM="[0-9]+"
   BOOL="[01]"
   DECIMAL_NUM="[0-9\.]+"
   ALPHA="[a-zA-Z]+"
   ALPHAUPPER="[A-Z]+"
   ALPHALOWER="[a-z]+"
   ALPHASPECIAL="[a-zA-Z_\-\.#/]+"
   ALPHANUM="[a-zA-Z0-9]+"
   ALPHANUMSPECIAL="[a-zA-Z0-9\-\._/]+"
   SYSMGR_SERVICE_NAME = "[a-zA-Z0-9\-\._ ]+"
   VRF_NAME="[a-zA-Z0-9_\-#]+"
   ALL="?:[.\s]+"
   #
   # Number and time formats
   #
   VLAN_RANGE='(?:(?:{0}-[0-9]+|{0}-{0}|{0}),?)+'.format(NUM)

   DATE = '[0-9]+\-[0-9]+\-[0-9]+'
   U_TIME="[0-9]+\.[0-9]+"
   CLOCK_TIME="[0-9]+[0-9]+:[0-9]+[0-9]+:[0-9]+[0-9]+"
   HH_MM_SS="[0-9]{1,2}:[0-9]{1,2}:[0-9]{1,2}"
   TIME="(?:$U_TIME|$CLOCK_TIME)"
   MONTH="Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
   YEAR="[12]+[0-9][0-9][0-9]"
   UPTIME="(?:\d+[dwmy]\d+[hdwm]|\d+:\d+:\d+|\d+\.\d+)"
   XPTIME="(?:\d+:\d+:\d+|\d+\.\d+|never)"

   LC_STATUS='(?:pwr-?denied|err-?pwd-?dn|pwr-?cycle?d|upgrading|powered-?up|powered-?dn|failure|initializing|testing|ok)'
   LC_MODEL='(?:N7K-F2-?48X[PT]-?\d+[E]*| +|Cortina-Test-LC|N9k-X9636PQ)'
   FC_MODEL='(?:N7K-C[0-9]+-FAB-?\d+|N/A| +)'
   LC_MODULE_TYPE='(?:[0-9]+/[0-9]+ Gbps (?:BASE-T )?Ethernet Module|Cortina-Test-LC|Snowbird|Seymour)'
   FC_MODULE_TYPE='(?:Fabric Module(?: [0-9]+)?|Sierra|Shasta)'
   VLAN_STATUS='active|suspended|act.lshut'

   #Verify_list defined for stimuli classes
   VERIFY_LIST=['none','all','traffic','l2_unicast_pi','l3_unicast_pi','l2_multicast_pi','l3_multicast_pi','l2_unicast_pd','l3_unicast_pd','l2_multicast_pd','l3_multicast_pd','system','exception','vpc_consistency']
   TRIGGER_VERIFY_LIST=['traffic','none','all']


# To be depreceated, use strTolist instead
# Usages strtolist('1,2,3')
#        strtolist('1 2 3')
#        strtolist('1, 2, 3')
# All three will return list of ['1',2,'3']
def strtolist(inputstr,retainint=False):
     inputstr=str(inputstr)
     inputstr=inputstr.strip("[]")
     splitbycomma=inputstr.split(",")
     splitbyspace=inputstr.split()
     if len(splitbycomma) >= 2:
         returnlist=[]
         for elem in splitbycomma:
             elem=elem.strip(" '")
             elem=elem.strip('"')
             if elem.isdigit() and retainint:
                 returnlist.append(int(elem))
             else:
                 returnlist.append(elem)
         return returnlist
     returnlist=[]
     for elem in splitbyspace:
         elem=elem.strip(" '")
         elem=elem.strip('"')
         if elem.isdigit() and retainint:
             returnlist.append(int(elem))
         else:
             returnlist.append(elem)
     return returnlist

def normalizeInterfaceName(log, interface):
     in_type=type(interface)
     pattern1='[Ee]thernet|[Ee]th|[Ee]t'
     pattern2='[Vv]lan|[Vv]l'
     pattern3='[Pp]ort-channel|[Pp]ortchannel|[Pp]o'
     pattern4='[Ll]oopback|[Ll]oop-back|[Ll]o'
     if (in_type == str):
         interface=re.sub(r'(?:{0})((?:{1}))'.format(pattern1,rex.INTERFACE_NUMBER),r'Eth\1',interface)
         interface=re.sub(r'(?:{0})((?:{1}))'.format(pattern2,rex.INTERFACE_NUMBER),r'Vlan\1',interface)
         interface=re.sub(r'(?:{0})((?:{1}))'.format(pattern3,rex.INTERFACE_NUMBER),r'Po\1',interface)
         interface=re.sub(r'(?:{0})((?:{1}))'.format(pattern4,rex.INTERFACE_NUMBER),r'Lo\1',interface)
     if (in_type == list):
         for int in interface:
             tmp=re.sub(r'(?:{0})((?:{1}))'.format(pattern1,rex.INTERFACE_NUMBER),r'Eth\1',int)
             tmp=re.sub(r'(?:{0})((?:{1}))'.format(pattern2,rex.INTERFACE_NUMBER),r'Vlan\1',tmp)
             tmp=re.sub(r'(?:{0})((?:{1}))'.format(pattern3,rex.INTERFACE_NUMBER),r'Po\1',tmp)
             tmp=re.sub(r'(?:{0})((?:{1}))'.format(pattern4,rex.INTERFACE_NUMBER),r'Lo\1',tmp)
             interface[interface.index(int)]=tmp
     if (in_type == tuple):
         int_list=list(interface)
         for int in int_list:
             tmp=re.sub(r'(?:{0})((?:{1}))'.format(pattern1,rex.INTERFACE_NUMBER),r'Eth\1',int)
             tmp=re.sub(r'(?:{0})((?:{1}))'.format(pattern2,rex.INTERFACE_NUMBER),r'Vlan\1',tmp)
             tmp=re.sub(r'(?:{0})((?:{1}))'.format(pattern3,rex.INTERFACE_NUMBER),r'Po\1',tmp)
             tmp=re.sub(r'(?:{0})((?:{1}))'.format(pattern4,rex.INTERFACE_NUMBER),r'Lo\1',tmp)
             int_list[int_list.index(int)]=tmp
         interface=tuple(int_list)
     if (in_type == dict):
         dct={}
         for key in interface.keys():
             int=re.sub(r'(?:{0})((?:{1}))'.format(pattern1,rex.INTERFACE_NUMBER),r'Eth\1',key)
             int=re.sub(r'(?:{0})((?:{1}))'.format(pattern2,rex.INTERFACE_NUMBER),r'Vlan\1',int)
             int=re.sub(r'(?:{0})((?:{1}))'.format(pattern3,rex.INTERFACE_NUMBER),r'Po\1',int)
             int=re.sub(r'(?:{0})((?:{1}))'.format(pattern4,rex.INTERFACE_NUMBER),r'Lo\1',int)
             tmp={int:interface[key]}
             dct.update(tmp)
         interface=dct

     return interface
def convertListToDict(table,columns=[],keys=None,keytype="tuple"):

    # Returns dictionary based on given list & columns
    # If it is a list, each column is a key
    # If it is a list of lists, then first level keys are passed keys argument
    # and columns is second level key

    returnDict = collections.OrderedDict()
    if keys:
        keyIndexes = []
        if "split" in dir(keys):
            keys=keys.split()
        for key in keys:
            keyIndexes.append(columns.index(key))

        valueIndex=-1
        if len(columns) - len(keys) == 1:
            for i in range(len(columns)):
                if not i in keyIndexes:
                   valueIndex=i
                   break

        for row in table:
            key=""
            keyitems=[]
            initial=True
            for keyIndex in keyIndexes:
               interface=""
               temp=re.match(rex.INTERFACE_NAME,row[keyIndex])
               if temp and temp.group(0) == row[keyIndex]:
                   interface=normalizeInterfaceName("",row[keyIndex])
               if initial:
                   if interface == "":
                       key = key + row[keyIndex]
                   else:
                       key = key + interface
                   initial=False
               else:
                   if interface == "":
                       key = key + " " + row[keyIndex]
                   else:
                       key = key + " " + interface
               if interface == "":
                   keyitems.append(row[keyIndex])
               else:
                   keyitems.append(interface)
            if keytype == "tuple" and len(keys) > 1:
                key=tuple(keyitems)
            returnDict[key] = collections.OrderedDict()
            if valueIndex == -1:
                for i in range(len(columns)):
                    if not i in keyIndexes:
                       temp=re.match(rex.INTERFACE_NAME,row[i].strip())
                       if temp and temp.group(0) == row[i].strip():
                          returnDict[key][columns[i]]=normalizeInterfaceName("",row[i].strip())
                       else:
                           returnDict[key][columns[i]] = row[i].strip()
            else:
               temp=re.match(rex.INTERFACE_NAME,row[valueIndex].strip())
               if temp and temp.group(0) == row[valueIndex].strip():
                   returnDict[key]=normalizeInterfaceName("",row[valueIndex].strip())
               else:
                   returnDict[key] = row[valueIndex]
    else:
        #Single level dictionary need to handle 6 different use cases
        #eor_utils.convertListToDict(['x','y','z'],['a','b','c'])
        #eor_utils.convertListToDict([],['a','b','c'])
        #eor_utils.convertListToDict(['x','y'],['a','b','c'])
        #eor_utils.convertListToDict([('x','y','z')],['a','b','c'])
        #eor_utils.convertListToDict([('x','y'),('c','d')],['a','b'])
        #eor_utils.convertListToDict([('x','y'),('c','d')])
        if len(table):
            if len(columns) == len(table) and not re.search('tuple',str(type(table[0]))):
                for key in columns:
                    temp=re.match(rex.INTERFACE_NAME,table[columns.index(key)])
                    if temp and temp.group(0) == table[columns.index(key)]:
                        returnDict[key]=normalizeInterfaceName("",table[columns.index(key)])
                    else:
                        returnDict[key]=table[columns.index(key)]
            elif len(table) == 1 and len(table[0]) == len(columns) and re.search('tuple',str(type(table[0]))):
                for key in columns:
                    temp=re.match(rex.INTERFACE_NAME,table[0][columns.index(key)])
                    if temp and temp.group(0) == table[0][columns.index(key)]:
                        returnDict[key]=normalizeInterfaceName("",table[0][columns.index(key)])
                    else:
                        returnDict[key]=table[0][columns.index(key)]
            elif (len(columns) == 2 or len(columns) == 0)and re.search('tuple',str(type(table[0]))):
                for row in table:
                    if len(row) == 2:
                       temp=re.match(rex.INTERFACE_NAME,row[1])
                       if temp and temp.group(0) == row[1]:
                            returnDict[row[0]]=normalizeInterfaceName("",row[1])
                       else:
                            returnDict[row[0]]=row[1]
                    else:
                       return collections.OrderedDict()
    return returnDict

def getUnwrappedBuffer(buffer,delimiter=" "):

    # Returns a string
    # If output has wrapped lines as follows (port-channel summary)
    # "21    Po21(SU)    Eth      NONE      Eth2/11(P)   Eth2/12(D)
    #  22    Po22(SU)    Eth      NONE      Eth1/1(P)    Eth1/2(P)    Eth1/3(P)
    #                                       Eth1/4(P)
    #  101   Po101(SD)   Eth      NONE      Eth2/1(D)    Eth2/2(D)"
    # This converts to
    # "21    Po21(SU)    Eth      NONE      Eth2/11(P)   Eth2/12(D)
    #  22    Po22(SU)    Eth      NONE      Eth1/1(P)    Eth1/2(P)    Eth1/3(P) Eth1/4(P)
    #  101   Po101(SD)   Eth      NONE      Eth2/1(D)    Eth2/2(D)"
    #
    # This helps to write get procedures with everyoutput being a single line
    # and makes regular expressions seamless independent of wrapped output

    previousline=""
    lines=[]
    returnbuffer = ""
    buffer=re.sub("\r","",buffer)
    for line in buffer.split("\n"):
        wrappedline=re.findall("^[ \t]+(.*)",line,flags=re.I)
        if len(wrappedline) > 0:
           previousline = previousline + delimiter + re.sub("\r\n","",wrappedline[0])
        else:
           if (previousline != ""):
               returnbuffer = returnbuffer + previousline + "\n"
           previousline=re.sub("[\r\n]+","",line)
    if (previousline != ""):
          returnbuffer = returnbuffer + previousline + "\n"
    return returnbuffer

def getVlanMemberList( vlanInfoStr ):
    vlanInfoStart = False

    vlanInfoList = []

    vlanId     = ''
    vlanName   = ''
    vlanStatus = ''
    vlanPorts  = ''

    for line in vlanInfoStr.split("\n"):
        if not line:
            continue

        if line.startswith('---'):
            continue

        if line.startswith( "VLAN Name" ):
            vlanInfoStart = True
            colVlanIdStartIndex     = 0
            colVlanNameStartIndex   = line.find( "Name" )
            colVlanStatusStartIndex = line.find( "Status" )
            colVlanPortsStartIndex  = line.find( "Ports" )
            continue

        if line.startswith( "VLAN Type" ):
           vlanInfoStart = False
           vlanInfoList.append( ( vlanId.strip(), vlanName.strip(), vlanStatus.strip(), vlanPorts.strip(" ,") ))
           break

        if vlanInfoStart == True:
            vlanId     += line[ : colVlanNameStartIndex].strip()
            vlanName   += line[ colVlanNameStartIndex : colVlanStatusStartIndex ].strip()
            vlanStatus += line[ colVlanStatusStartIndex : colVlanPortsStartIndex ].strip()
            vlanPorts  += line[ colVlanPortsStartIndex : ].strip() + ","

    return vlanInfoList

def getVlanDict(vlan):

    cmd = "show vlan id " + vlan
    showoutput=cli_ex(cmd)

#vlanmemberlist=re.findall("("+rex.NUM+")[ \t]+("+rex.ALPHANUM+")[ \t]+("+rex.VLAN_STATUS+")[ \t]+(.*)",getUnwrappedBuffer(showoutput,", "),flags=re.I|re.M)
#vlanmemberlist=re.findall("("+rex.NUM+")[ \t]+(.*)[ \t]+("+rex.VLAN_STATUS+")[ \t]+(.*)",getUnwrappedBuffer(showoutput,", "),flags=re.I|re.M)

    vlanmemberlist = getVlanMemberList( showoutput )
    vlanmemberdict=convertListToDict(vlanmemberlist,['VLAN','Name','Status','Ports'],['VLAN'])
    return vlanmemberdict

"""This scrpit should not contain any thing other than enums"""
class IfType:
       Ethernet = 1
       PortChannel = 2
       Internal = 3
       Cpu = 4
       Fex = 5

class IfMode:
       Nif = 1
       Access = 2
       Trunk = 3



def replace_output(_lines, _find_word, _replace_word):
    hw_name = _find_word
    new_lines = []

    for line in _lines:
        x = re.sub(r'\b%s\b'%(hw_name), _replace_word, line)
        new_lines.append(x)

    return new_lines

class createHwTableObject(object):

    """ Class to parse the broadcom table outputs and convert to dictionary format. Expects the
    input as 'Index: <Row>' where the <Row> is in key value pairs separated by commas"""

    def __init__( self, bcm_cmd_dump ):

       import re

       self.table=collections.OrderedDict()

       table_rows=bcm_cmd_dump.split('\n')
       for row in table_rows:
          if "d chg" in row:
              continue
          if ":" not in row:
                 continue
          if "Private image version" in row:
                 continue

          (row_key, row_value)=row.split(': ')
          (row_key, row_value)=row.split(': ')
          value_row=row_value.rstrip('\r').lstrip('<').rstrip('>')
          self.table[row_key]=collections.OrderedDict()
          for data_params in value_row.split(','):
             if len(data_params) == 0:
                 continue

             try:
                 (data_key,data_value)=data_params.split('=')
             except Exception, err:
                 continue

             self.table[row_key][data_key]=data_value
       #print('Table Data', self.table )

def isVlanInActiveState(vlan):
     cmd = "show vlan id " + vlan
     showoutput=cli_ex(cmd)
     if "active" in showoutput:
         return True
     else:
         return False

def isMCTMemberDown(ifIdx):
     cmd = "show vlan internal info vlan-port-db interface " + str(ifIdx)
     showoutput=cli_ex(cmd)
     lines = showoutput.split('\n')
     for line in lines:
        match = re.search('cfg_flags.*', line)
        if match:
            #Check if port is DOWN due to remote vlan on the 
            #MCT is shutdown.
            if '4' and 'DOWN' and 'TRUNK' in match.group(0):
                for newline in lines:
                    newmatch = re.search('l2_port_mode.*', newline)
                    if newmatch:
                        if '5' in newmatch.group(0):
                            return True
                        else:
                            return False
            elif '1' and 'DOWN' and 'ACCESS' in match.group(0):
                for newline in lines:
                    newmatch = re.search('l2_port_mode.*', newline)
                    if newmatch:
                        if '7' in newmatch.group(0):
                            return True
                        elif '3' in newmatch.group(0):
                            return True
                        else:
                            return False
            else:
                return False

def isNativeVlanIsNotInAllowedVlans(ifIdx):

     finalList = []
     cmd = "show running-config interface " + str(ifIdx) + " all"
     showoutput=cli_ex(cmd)
     lines = showoutput.split('\n')
     for line in lines:
         match = re.search('private-vlan trunk.*vlan', line)
         if match:
             #Check if native vlan is not in allowed vlan list
             if 'native' in match.group(0):
                 nativeVlan = line.split('native vlan')[-1]
                 for newline in lines:
                     newmatch = re.search('private-vlan trunk allowed vlan', newline)
                     if newmatch:
                         if 'none' in newline:
                             return True
                         else:
                             allowedVlans = newline.split('allowed vlan')[-1]
                             x = allowedVlans.split(',')
                             for i in x:
                                 if '-' in i:
                                     list1= range(int(i.split('-')[-2]), int(i.split('-')[-1]) + 1)
                                     finalList.append(list1)				                
                                 else:
                                     finalList.append(int(i))
                             if nativeVlan in finalList:
                                 return False
                             else:
                                 return True
                              

def getSpanningTreeVlanPortStateDict(vlan):
    cmd = "show spanning-tree " + vlan
    showoutput=cli_ex(cmd)
    stplist=re.findall("^([^ \t]+)[ \s]+([^ \t]+)[ \s]+([A-Za-z]+)[ \s]+([0-9]+)[ \s]+\
    ([^ \t]+)[ \s]+([^ \t]+)[ \s\r\n]+",showoutput,flags=re.I|re.M)
    if stplist:
        # if vlan port state is found
        stpdict=convertListToDict(stplist,['vlan','role','state','cost','prio.nbr','type'])
        log.info(" STP state for " + \
        parserutils_lib.argsToCommandOptions(args,arggrammar,log,"str") + " is : " + str(stpdict))
        return stpdict


def getNSPortMappingDict(mod):
    ns_port_dict = {}
    cmd = "slot " + str(mod) + " show hardware internal  ns mac pinning"
    output=cli_ex(cmd)
    lines = output.splitlines()
    for line in lines:
        if line and line[0].isdigit():
            portList = strtolist(line)
            #print portList
            ns_port_dict[portList[0]] = portList[1]
    return ns_port_dict

def getShowSpanningTreeDict( vlan ):
    
    show_stp_dict=collections.OrderedDict()


    # Define the Regexp Patterns to Parse ..

    root_params_pat_non_root='\s+Root ID\s+Priority\s+([0-9]+)\r\n\s+Address\s+({0})\r\n\s+Cost\s+([0-9]+)\r\nPort\s+([0-9]+)\s+\(([a-zA-Z0-9\-]+)\)\r\n\s+Hello Time\s+([0-9]+)\s+sec\s+Max\s+Age\s+([0-9]+)\s+sec\s+Forward\s+Delay\s+([0-9]+)\s+sec\r\n'.format(rex.MACADDR)
    root_params_pat_root='\s+Root ID\s+Priority\s+([0-9]+)\r\n\s+Address\s+({0})\r\n\s+This bridge is the root\r\n\s+Hello Time\s+([0-9]+)\s+sec\s+Max\s+Age\s+([0-9]+)\s+sec\s+Forward\s+Delay\s+([0-9]+)\s+sec\r\n'.format(rex.MACADDR)
    bridge_params_pat='\s+Bridge ID\s+Priority\s+([0-9]+)\s+\(priority\s+([0-9]+)\s+sys-id-ext ([0-9]+)\)\r\n\s+Address\s+({0})\r\n\s+Hello\s+Time\s+([0-9]+)\s+sec\s+Max\s+Age\s+([0-9+)\s+sec\s+Forward Delay\s+([0-9]+) sec\r\n'.format(rex.MACADDR)
    #interface_params_pat='-------\r\n({0})\s+([a-zA-Z]+)\s+([A-Z]+)\s+([0-9]+)\s+([0-9]+).([0-9]+)\s+([\(\)a-zA-Z0-9\s]+)\r'.format(rex.INTERFACE_NAME)
    interface_params_pat='({0})\s+([a-zA-Z]+)\s+([A-Z]+)[\*\s]+([0-9]+)\s+([0-9]+).([0-9]+)\s+'.format(rex.INTERFACE_NAME)


    # Build the command to be executed based on the arguments passed ..
    cmd = 'show spanning-tree '

    cmd = cmd + 'vlan ' + str(vlan)


    show_stp=cli_ex(cmd)

    # Split the output of STP based on VLAN
    show_stp_vlan_split=show_stp.split('VLAN')


    # Iterate over every VLAN block and build the show_stp_dict
    for stp_vlan in show_stp_vlan_split:

      if re.search( '^([0-9]+)', stp_vlan ):

         #removed backslash r
         match=re.search( '^([0-9]+)\n\s+Spanning tree enabled protocol ([a-z]+)', stp_vlan, re.I )
         vlan_id = int(match.group(1))
         stp_mode = match.group(2)
         show_stp_dict[vlan_id]={}
         show_stp_dict[vlan_id]['stp_mode']=stp_mode


         if re.search( root_params_pat_root, stp_vlan, re.I ):
             root_info=re.findall( root_params_pat_root, stp_vlan, re.I )
             show_stp_dict[vlan_id]['root_info']=convertListToDict( root_info, ['Priority','Address', \
                 'Hello Time','Max Age','Forward Delay'], ['Priority','Address'])
             show_stp_dict[vlan_id]['root']=True
         else:
             root_info=re.findall( root_params_pat_non_root, stp_vlan, re.I )
             show_stp_dict[vlan_id]['root_info']=convertListToDict( root_info, ['Priority','Address','Cost', \
                 'Port','Hello Time','Max Age','Forward Delay'], ['Priority','Address','Cost', 'Port'])
             show_stp_dict[vlan_id]['root']=False

         bridge_info=re.findall( bridge_params_pat, stp_vlan, re.I )
         show_stp_dict[vlan_id]['bridge_info']=convertListToDict( root_info, ['Priority','Address', \
                'Hello Time','Max Age','Forward Delay'], ['Priority','Address'])

         intf_info=re.findall( interface_params_pat, stp_vlan, re.I )
         show_stp_dict[vlan_id]['Interface_info']=convertListToDict( intf_info, [ 'Interface', 'Role', 'Status', \
                'Cost', 'Prio', 'Nbr' ] , [ 'Interface' ] )

    # Split the output of STP based on MST
    show_stp_mst_split=show_stp.split('MST')

    for mst_id in show_stp_mst_split:

      if re.search( '^([0-9]+)', mst_id):

         #removed backslash r
         match=re.search( '^([0-9]+)\n\s+Spanning tree enabled protocol ([a-z]+)', mst_id, re.I )
         mst = vlan
         stp_mode = match.group(2)
         show_stp_dict[mst]={}
         show_stp_dict[mst]['stp_mode']=stp_mode


         if re.search( root_params_pat_root, mst_id, re.I ):
             root_info=re.findall( root_params_pat_root, mst_id, re.I )
             show_stp_dict[mst]['root_info']=convertListToDict( root_info, ['Priority','Address', \
                 'Hello Time','Max Age','Forward Delay'], ['Priority','Address'])
             show_stp_dict[mst]['root']=True
         else:
             root_info=re.findall( root_params_pat_non_root, mst_id, re.I )
             show_stp_dict[mst]['root_info']=convertListToDict( root_info, ['Priority','Address','Cost', \
                 'Port','Hello Time','Max Age','Forward Delay'], ['Priority','Address','Cost', 'Port'])
             show_stp_dict[mst]['root']=False

         bridge_info=re.findall( bridge_params_pat, mst_id, re.I )
         show_stp_dict[mst]['bridge_info']=convertListToDict( root_info, ['Priority','Address', \
                'Hello Time','Max Age','Forward Delay'], ['Priority','Address'])

         intf_info=re.findall( interface_params_pat, mst_id, re.I )
         show_stp_dict[mst]['Interface_info']=convertListToDict( intf_info, [ 'Interface', 'Role', 'Status', \
                'Cost', 'Prio', 'Nbr' ] , [ 'Interface' ] )
    return show_stp_dict

def pprint_table(out, table):
    """Prints out a table of data, padded for alignment
    @param out: Output stream (file-like object)
    @param table: The table to print. A list of lists.
    Each row must have the same number of columns. """
    col_paddings = []

    for i in range(len(table[0])):
        col_paddings.append(get_max_width(table, i))

    for row in table:
        # left col
        print >> out, row[0].ljust(col_paddings[0] + 1),
        # rest of the cols
        for i in range(1, len(row)):
            col = format_num(row[i]).rjust(col_paddings[i] + 2)
            print >> out, col,
        print >> out


def validateIP(ip):
    try:
       socket.inet_aton(ip)
       return 0
    except socket.error:
       return 1

def convertIP(ip):
    hexIP = []
    [hexIP.append(hex(int(x))[2:].zfill(2)) for x in ip.split('.')]
    hexIP = "0x" + "".join(hexIP)
    return hexIP

class createEventHistoryTableObject(object):

    """ Class to parse the event history outputs and convert to dictionary format. Expects the
    input as 'Index: <Row>' where the <Row> is in key value pairs separated by commas"""

    def __init__( self, event_history_dump ):

       import re
       time_format = "at %f usecs after %a %b %d %H:%M:%S %Y"

       self.table=[]

       table_rows=event_history_dump.split('\n')
       new = {}
       esq_req_rsp = {}
       esqs = []
       esq_start = []
       req_rsp = True
       for row in table_rows:
          if ":" not in row:
                 continue

          if "FSM:" in row:
              if req_rsp == False:
                  esq_start.append(esq_req_rsp)
                  req_rsp = True
                  esq_req_rsp = {}

              if len(esq_start) > 0:
                  esqs.append(esq_start)
                  esq_start = []

          if "ESQ_START" in row:
              if req_rsp == False:
                  esq_start.append(esq_req_rsp)
                  req_rsp = True
                  esq_req_rsp = {}

              if len(esq_start) > 0:
                  esqs.append(esq_start)

              esq_start = []

          if "ESQ_REQ" in row or "ESQ_RSP" in row:
              old = esq_req_rsp
              esq_req_rsp = {}
              if len(old) > 0:
                  esq_start.append(old)
                  req_rsp = True

          if "usecs after" in row:
              y = row[row.find("at"):]
              t = datetime.datetime.strptime(y, time_format)
              esq_req_rsp['TIME'] = t
              esq_req_rsp['TIME_STRING'] = row

          kvpairs = row.split(',')
          for val in kvpairs:

              x = val.strip(' ').strip('\r').split(':')
              if len(x) != 2:
                  continue

              (tk, tv)=val.split(':')
              row_key = tk.strip(' ')
              row_value = tv.strip(' ')
              req_rsp = False
              esq_req_rsp[row_key]=row_value

       if req_rsp == False:
           esq_start.append(esq_req_rsp)
           esqs.append(esq_start)

       self.table = esqs

def getShortIfName(_longName):
    sh = None
    if "thernet" in _longName:
        sh = 'Eth' + _longName[8:]

    if "ort-channel" in _longName:
        sh = 'Po' + _longName[12:]

    return sh

def getLongIfName(self, _shortName):
    sh = None
    if "Eth" in _shortName or "eth" in _shortName:
        sh = 'Ethernet' + _shortName[3:]

    if "Po" in _shortName or "po" in _shortName:
        sh = 'Port-channel' + _shortName[2:]

    return sh


from libnxos_ext_api import *
def getIfNamesGivenBitmap(modObj, unit, bitmap):
    if bitmap == 0:
        #print "\tNo Ports masked in mod %d"%modObj.mod
        return None
    #print "\tModule %d unit %d" % (modObj.mod, unit)
    names = []
    for i in range(0, 136):
        if (1<<i & bitmap):
            (ret, ifindex) = py_im_get_if_name_and_if_index_from_mod_unit_port(
                                    modObj.hwMod.get_modid()[unit], i)
            #print "ifindex = 0x%x"%ifindex
            longName = py_im_get_long_name_from_if_index(ifindex)
            names.append(getShortIfName(longName))

    return names

def getVxlanMcastGroup(vnseg):
    cmd = 'sh nve vni '
    cmd = cmd + str(vnseg)

    show_nve = cli_ex(cmd)
    lines = show_nve.split('\n')
    for line in lines:
        match = re.search('nve.*([0-9]+)\s+([0-9.]+)\s+.*', line)
        if match:
            return match.group(2)
    return None

def isVniL3(vnseg):
    cmd = 'sh nve vni '
    cmd = cmd + str(vnseg)

    show_nve = cli_ex(cmd)
    if 'L3 ' in show_nve:
        return True
    else:
        return False

def getVxlanVtepIp():
    cmd = 'sh nve int'

    show_nve = cli_ex(cmd)
    lines = show_nve.split('\n')
    for line in lines:
        match = re.search('Source-interface:.*primary:\s*([0-9.]+),\s*secondary:\s*([0-9.]+).*', line)
        if match:
            primary = match.group(1)
            secondary = match.group(2)
            match = re.search('0.0.0.0', secondary)
            if match:
                return primary
            else:
                return secondary
    return None

def getSGOifList(source, group):
    cmd = 'sh ip mroute ' + source + ' ' + group

    oifs = []
    show_ip_mroute = cli_ex(cmd)
    lines = show_ip_mroute.split('\n')
    for line in lines:
        match = re.search('(Ethernet[0-9/]+), uptime.*', line)
        if match:
            oifs.append(match.group(1))
        match = re.search('(port-channel[0-9/]+), uptime.*', line)
        if match:
            oifs.append(match.group(1))

    return oifs

def isInterfaceinLacpIState(interface):
    cmd = 'show port-channel internal info interface ' + interface
    output = cli_ex(cmd)
    if "individual" in output:
       return True
    else:
       return False

def get_asic_type(_mod=1, _unit=0):
    '''Gets the prefix type.'''
    # Since the functions use 0 based mod-number
    if py_platform_is_lacrosse(_mod - 1):
        return 'lac'
    elif py_platform_is_davos(_mod - 1):
        return 'dav'
    else:
        card_index = 0
        f = open('/proc/cmdline', 'r')
        text = f.readline()
        f.close()

        text = text.replace('"', '//')
        text = text.replace('  ', ' ')

        cmd = text.split(' ')
        for vals in cmd:
            if 'dummy_card_index' in vals:
                cardstr = vals.split('=')
                card_index = int(cardstr[1])
            elif 'card_index=' in vals:
                cardstr = vals.split('=')
                card_index = int(cardstr[1])

        if card_index == 21123:
            return 'dav'
        elif card_index == 21121:
            return 'lac'
        elif card_index == 21125:
            return 'dav'
        elif card_index == 21126:
            return 'lac'

        return 'Unknown'


#: struct format lookup for specific word sizes.
STRUCT_FMT = {
    8  : 'B',   # unsigned char
    16 : 'H',   # unsigned short
    32 : 'I',   # unsigned int
}


def int_to_words(int_val, num_words=4, word_size=32):
    '''Divide the integer into words by size'''
    max_int = 2 ** (word_size*num_words) - 1
    max_word_size = 2 ** word_size - 1

    if not 0 <= int_val <= max_int:
        raise IndexError('integer %r is out of bounds!' % hex(int_val))

    words = []
    for _ in range(num_words):
        word = int_val & max_word_size
        words.append(int(word))
        int_val >>= word_size
    words.reverse()

    return words


def int_to_packed(int_val, width=128, word_size=32):
    '''Convert an int to packed structure'''
    num_words = width / word_size
    words = int_to_words(int_val, num_words, word_size)

    try:
        fmt = '!%d%s' % (num_words, STRUCT_FMT[word_size])
        #DEBUG: print 'format:', fmt
    except KeyError:
        raise ValueError('unsupported word size: %d!' % word_size)

    return struct.pack(fmt, *words)


def packed_to_int(packed_int, width=128, word_size=32):
    '''Convert a packed structure to int'''
    num_words = width / word_size

    try:
        fmt = '!%d%s' % (num_words, STRUCT_FMT[word_size])
        #DEBUG: print 'format:', fmt
    except KeyError:
        raise ValueError('unsupported word size: %d!' % word_size)

    words = list(struct.unpack(fmt, packed_int))
    words.reverse()

    int_val = 0
    for i, num in enumerate(words):
        word = num
        word = word << word_size * i
        int_val = int_val | word

    return int_val


def get_ipv4_from_hex(hex_ipv4):
    '''Convert a hex ipv4 value to A.B.C.D'''
    return socket.inet_ntop(socket.AF_INET,
                            struct.pack('!I', int(hex_ipv4, 16)))


def get_ipv6_from_hex(hex_ipv6):
    '''Convert hex ipv6 to network format'''
    return socket.inet_ntop(socket.AF_INET6,
                            int_to_packed(int(hex_ipv6, 16),
                                          width=128,
                                          word_size=32))
