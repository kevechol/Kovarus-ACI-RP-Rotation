import httplib
import json
from nxos_utils import runVshCmd
import argparse
import os
import re
from pprint import pprint
import string

def parse_cmdline_args():
    parser = argparse.ArgumentParser(description='Dump REST MOs')
    parser.add_argument('password', metavar='<password>', help='The password for %s' % os.getlogin())
    parser.add_argument('-i', action="store_true", help='Interactive mode')
    parser.add_argument('--dn', metavar="<dn>", help="DN to lookup.")
    args = parser.parse_args()
    return args

def print_common_dns():
    print "Ethernet:         sys/intf/phys-[ethx/y]"
    print "Port-Channel:     sys/intf/aggr-[pox]"
    print "System default:   sys/ethpm/inst"
    print "PO Subinterface:  sys/intf/encrtd-[pox.y]"
    print "Subinterface:     sys/intf/encrtd-[ethx/y.z]"

class MoDumper(object):
    def __init__(self, password):
        # Get MGMT 
        output = runVshCmd("show int mgmt 0")
        m = re.search("Internet Address is ([\d\.]+)", output)
        if not m:
            print "Failed to get mgmt IP. Please check config and try again."
            exit(1) 
        self.mgmt_ip = m.group(1)
        # Get Username
        self.user = os.getlogin()
        # Get password
        self.password = password

    def post_aaa_auth(self):
        """  
        Authenticate and if successfull return cookie else None.
        @mgmt_ip:   Management ip of the switch.
        @user_name: username
        @pwd:       password
        """
        payload = { "aaaUser" : { "attributes" : { "name" : self.user, "pwd" : self.password}}}
        headers = {"Content-type": "application/json", "Accept": "text/plain"}

        url = "http://{0}/api/aaaLogin.json".format(self.mgmt_ip)
        conn = httplib.HTTPConnection(self.mgmt_ip)
        conn.request('POST', url, json.dumps(payload), headers)

        response = conn.getresponse()

        if response.status == 200: 
            return response.getheader( 'set-cookie' )
        else:
            return None

    def get_config_using_rest(self, cookie, rn, full=False):
        """  
        Get MO's info.
        @cookie:  Authentication cookie
        @mgmt_ip: Management IP of the switch
        @data:    DN.
        """

        headers = {'Content-type': 'application/json', 'Accept': 'application/json', 'Cookie': cookie, }

        conn = httplib.HTTPConnection(self.mgmt_ip)

        url = "http://{0}/api/mo/{1}.json".format(self.mgmt_ip, rn)
        if full:
            url += "?rsp-subtree=full"
        conn.request( 'GET', url, json.dumps(rn), headers )

        response = conn.getresponse()

        print url
        data = response.read()
        data = ''.join(filter(lambda x:x in string.printable, data))
        try:
            o = json.loads(data, strict=False)
        except ValueError as e:
            print str(e)
            return {}
        return o
   
    def get_mo_data(self, dn): 
        cookie = self.post_aaa_auth()
        if cookie == None:
            print "Authentication failure !"
        else:
            if dn.endswith("?rsp-subtree=full"):
                dn = dn[:-len("?rsp-subtree=full")]
                data = self.get_config_using_rest(cookie, dn, full=True)
            elif dn.endswith("+"):
                dn = dn[:-1]
                data = self.get_config_using_rest(cookie, dn, full=True)
            else:
                data = self.get_config_using_rest(cookie, dn, full=False)
            return data

    def interactive_mode(self):
        dn = ""
        while True:
            dn = raw_input("DN>> ")
            data = self.get_mo_data(dn)        
            print json.dumps(data, sort_keys=True, indent=3, separators=(',', ': '))

if __name__ == "__main__":
    params = parse_cmdline_args()

    password = params.password
    
    dumper = MoDumper(password)
    
    if params.i:
        print "Interactive Mode:"
        print_common_dns()
        print "Type a DN to query DME\n"
        try:
            dumper.interactive_mode()
        except KeyboardInterrupt:
            exit(0)
    if params.dn:
        try:
            data = dumper.get_mo_data(params.dn)
            print json.dumps(data, sort_keys=True, indent=3, separators=(',', ': '))
        except KeyboardInterrupt:
            exit(0)

        
