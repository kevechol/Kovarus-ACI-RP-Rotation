import xmltodict
import json
from device import Device
import sys

def show_intf_mgmt(sw):

    getdata = sw.show('show interface mgmt0')

    show_intf_dict = xmltodict.parse(getdata[1])

    data = show_intf_dict['ins_api']['outputs']['output']['body']['TABLE_interface']['ROW_interface']

    ip = data['eth_ip_addr']
    mask = data['eth_ip_mask']
    name = data['interface']
    speed = data['eth_speed']
    duplex = data['eth_duplex']

    mgmt_dict = { 'IP': ip+'/'+mask, 'name': name, 'speed': speed, 'duplex': duplex}

    return mgmt_dict

def show_hardware(sw):

    getdata = sw.show('show hardware')

    show_hw_dict = xmltodict.parse(getdata[1])

    data = show_hw_dict['ins_api']['outputs']['output']['body']

    hw_dict = {}
    hw_dict['OS Version'] = data['kickstart_ver_str']
    hw_dict['Type'] = data['chassis_id']
    hw_dict['Memory'] = data['memory'] + data['mem_type']
    hw_dict['Hostname'] = data['host_name']
    hw_dict['Bootflash'] = data['bootflash_size']
    hw_dict['Last Reboot Reason'] = data['rr_reason']
    hw_dict['Uptime'] = '{} day(s) {} hour(s) {} minute(s) {} second(s)'.format(data['kern_uptm_days'],data['kern_uptm_hrs'],data['kern_uptm_mins'],data['kern_uptm_secs'])

    ser_nums = {}

    ser_nums_data = show_hw_dict['ins_api']['outputs']['output']['body']['TABLE_slot']['ROW_slot']['TABLE_slot_info']['ROW_slot_info']

    show_hw_dict = xmltodict.parse(getdata[1])

    for each in ser_nums_data:

        if 'serial_num' in each.keys():
            key = each['serial_num']
            ser_nums[key] = each['model_num']

    hw_dict['serial_numbers'] = ser_nums

    return hw_dict

def main():

    switch = Device(ip='172.31.217.134', username='admin', password='cisco123')
    switch.open()

    facts = {}

    intf = show_intf_mgmt(switch)
    facts['mgmt_intf'] = intf

    hw = show_hardware(switch)
    facts.update(hw)

    args = sys.argv

    if len(args) == 1:
        print json.dumps(facts, indent=4)
    else:
        if args[1] in facts.keys():
            print args[1].upper() + ': ' + json.dumps(facts[args[1]],indent=4)
        else:
            print 'Invalid Key. Try again.'

if __name__ == "__main__":
    main()