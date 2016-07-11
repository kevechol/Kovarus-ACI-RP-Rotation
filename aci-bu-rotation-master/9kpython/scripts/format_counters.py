#!/usr/bin/env python
#
# Copyright (c) 2013, 2015 by cisco Systems, Inc.
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# This script prints interface throughput/packet rate statistics in an
# easy to read list format on NX-OS platforms.  To use:
# 
#       1. Copy script to NX-OS switch bootflash:
#       2. Execute using 'python bootflash:interface_rate.py
# 

from __future__ import division
import sys,re
import xml.etree.ElementTree as ET
from nxos_utils import runVshCmd

def show_counter_table(args):
  # Get interface information in XML format
  print '\nCollecting and processing interface statistics ...\n'
  sys.stdout.flush()
  raw = runVshCmd('show interface | xml')
  raw1 = re.sub(".*No counters available.*\n?","",raw)
  regex = re.compile("]]>]]>")
  fmt = regex.sub('', raw1)
  # Load and parse XML
  tree = ET.ElementTree(ET.fromstring(fmt))
  data = tree.getroot()
 
  # Find and display interface rate information
  if_manager = '{http://www.cisco.com/nxos:1.0:if_manager}'
  table = "{0:16}{1:19}{2:9}{3:9}{4:9}{5:9}{6:9}"
  print '---------------------------------------------------------------------------'
  print table.format("Port", "Description", "Intvl", "Rx Mbps", "Rx %", "Tx Mbps", "Tx %")
  print '---------------------------------------------------------------------------' 
  for i in data.iter(if_manager + 'ROW_interface'):
    try:
      interface = i.find(if_manager + 'interface').text
      bw = int(i.find(if_manager + 'eth_bw').text)
      rx_intvl = i.find(if_manager + 'eth_load_interval1_rx').text
      rx_bps = int(i.find(if_manager + 'eth_inrate1_bits').text)
      rx_mbps = round((rx_bps / 1000000), 1)
      rx_pcnt = round((rx_bps / 1000) * 100 / bw, 1)
      tx_intvl = i.find(if_manager + 'eth_load_interval1_tx').text
      tx_bps = int(i.find(if_manager + 'eth_outrate1_bits').text)
      tx_mbps = round((tx_bps / 1000000), 1)
      tx_pcnt = round((tx_bps / 1000) * 100 / bw, 1)
    except AttributeError as e:
      continue
 
    try:
      desc = i.find(if_manager + 'desc').text[:18]
    except AttributeError as e:
      desc = "N/A"
    
    print table.format(interface, desc, rx_intvl + '/' + tx_intvl, str(rx_mbps), 
                        str(rx_pcnt) + '%', str(tx_mbps), str(tx_pcnt) + '%')
    sys.stdout.flush()
 
  # drop out if we don't want extended counters
  if len(args) >= 1 and args[0] < 1:
    return
 
  # Find and display errors/warnings
  data = tree.getroot()

  ifErrInfo = []
 
  for i in data.iter(if_manager + 'ROW_interface'):
    try:
      errInfo = {}
      errInfo["interface"] = i.find(if_manager + 'interface').text
      errInfo["crc"] = i.find(if_manager + 'eth_crc').text
      errInfo["in_err"] = i.find(if_manager + 'eth_inerr').text
      errInfo["overrun"] = i.find(if_manager + 'eth_overrun').text
      errInfo["underrun"] = i.find(if_manager + 'eth_underrun').text
      errInfo["etype"] = i.find(if_manager + 'eth_bad_eth').text
      errInfo["proto"] = i.find(if_manager + 'eth_bad_proto').text
      errInfo["if_down"]  = i.find(if_manager + 'eth_in_ifdown_drops').text
      errInfo["in_discard"] = i.find(if_manager + 'eth_indiscard').text
      errInfo["out_err"] = i.find(if_manager + 'eth_crc').text
      errInfo["out_discard"] = i.find(if_manager + 'eth_outdiscard').text
      ifErrInfo.append(errInfo)
    except AttributeError as e:
      #print "Exception: (%s) " % interface + str(e)
      pass

  # Find and display first set of error info
  table = "{0:16}{1:>9}{2:>9}{3:>12}{4:>12}{5:>14}" #{7:>8}{8:>8}"
  print '\n------------------------------------ ERRORS -------------------------------'
  print table.format("Port", "Overrun", "Underrun", "Etype Drop", "Proto Drop", "If Down Drop")
  print '---------------------------------------------------------------------------' 
  for intf in ifErrInfo:
    print table.format(intf["interface"], intf["overrun"], intf["underrun"], 
                       intf["etype"], intf["proto"], intf["if_down"])
    sys.stdout.flush()
 
  # Find and display second set of error info
  table = "{0:16}{1:>11}{2:>11}{3:>6}{4:>8}{5:>8}"
  print "\n--------------------------------- ERRORS (con't) ---------------------------"
  print table.format("Port", "RX Discard", "TX Discard", "CRC", "RX Err", "TX Err")
  print '---------------------------------------------------------------------------' 
  for intf in ifErrInfo:
    print table.format(intf["interface"], intf["in_discard"], intf["out_discard"], 
                       intf["crc"], intf["in_err"], intf["out_err"])
    sys.stdout.flush()
 
if __name__ == "__main__":
  # self test
  show_counter_table([1])     
