from onxos import *
from libbcmshell import *

"""
Following functions are available:
  Usage: check_hit_bit_for_mcast_32("227.1.1.1", ["Ethernet2/1","Ethernet3/1"])
  Description: This function clears hit bit and then checks if hit bit got set or not.

"""

def check_mod_unit_mcast_32(_ipaddress, _slot, _unit):
    print "XYZ:", _slot, _unit
    print "search l3_entry_ipv4_multicast IPV4MC:GROUP_IP_ADDR="+_ipaddress

    output = runBcmCmd(_slot, _unit, "search l3_entry_ipv4_multicast IPV4MC:GROUP_IP_ADDR="+_ipaddress)
    print output
    obj = createHwTableObject(output)

    if len(obj.table) != 1:
        print "Failed to obtail info"
        return -1

    for key in obj.table.keys():
        x = re.search('\[[0-9]+\]', key)
        if x is None:
            print "Did not find a key in the mcast table"
            return -1
        ix = x.group(0)[1:-1]
        cmd = "mod l3_entry_ipv4_multicast " + ix + " 1 HIT_1=0 HIT_0=0"
        print "cmd:", cmd
        print runBcmCmd(_slot, _unit, cmd)
        temp_key = key
        break

    print "search l3_entry_ipv4_multicast IPV4MC:GROUP_IP_ADDR="+_ipaddress

    output = runBcmCmd(_slot, _unit, "search l3_entry_ipv4_multicast IPV4MC:GROUP_IP_ADDR="+_ipaddress)
    print output
    obj = createHwTableObject(output)

    if len(obj.table) != 1:
        print "Failed to obtail info"
        return -1

    hit1 = obj.table[temp_key]['HIT_1']
    hit0 = obj.table[temp_key]['HIT_0']

    print "Hit Bits are: hit_0:%s, hit_1:%s"%(hit0,hit1)
      
        


    

# check_hit_bit_for_mcast_32(0xa010101, ["Ethernet2//1", "Ethernet2/2"]
def check_hit_bit_for_mcast_32(_ipaddress, _ifNameList):
    for ifname in _ifNameList:
        print "ifname", ifname
        i = Nxos.Interface(_longName = ifname)
        slot = i.slot
        unit = i.unit

        check_mod_unit_mcast_32(_ipaddress, slot, unit)
        
