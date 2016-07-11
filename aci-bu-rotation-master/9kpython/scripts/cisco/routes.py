from .key import Key
from .line_parser import LineParser
from .section_parser import SectionParser
from .nxcli import *
import nxos_utils


class Routes(object):
    egressKey = None
    l3intKey = None
    l3tableKey = None
    l3defipKey = None
    vshHeadKey = None
    arpKey = None
    fwmIntVlanKey = None
    validHops = {'100000': ('Drop', 'Null0'), 
            '100002': ('Receive', 'sup-eth1'), 
            '100003': ('Attached', 'sup-hi'),
            '200000': ('ECMP', 'sup-hi')}
    hopEntries = {'Drop': '100000', 'Receive': '100002', 'Attached': '100003'}

    def __init__(self):
        self.data = []

    def __get_arp_key(self):
        if self.arpKey is None:
            self.arpKey = Key([[r"(\d+.\d+.\d+.\d+)\s+\S+\s+(\S+)\s+(\S+)",
                              "many"]])
        return self.arpKey
        
    def __get_egress_key(self):
        if self.egressKey is None:
            self.egressKey = Key([[r"(\d+)\s+(\S+)\s+(\d+)\s+(\d+)\s+(\S+)\s+(\S+)",
                                 "many"]])
        return self.egressKey

    def __get_l3_int_key(self):
        if self.l3intKey is None:
            self.l3intKey = Key([[r"\d+\s+(\d+)\s+\d+\s+\d+\s+(\d+)\s+(\S+)",
                                "many"]])
        return self.l3intKey

    def __get_l3_table_key(self):
        if self.l3tableKey is None:
            self.l3tableKey = Key([[r"\d+\s+\d+\s+(\S+)\s+\S+\s+(\S+)\s+\S+\s+"
                                    "\S+\s+\S+\s+\S+", "many"]])
        return self.l3tableKey

    def __get_l3_defip_key(self):
        if self.l3defipKey is None:
            self.l3defipKey = Key([[r"\d+\s+\d+\s+(\S+)\/(\S+)\s+\S+\s+(\S+)\s"
                                    "+\d+\s+\d+\s+\d+\s+\d+\s+\S+", "many"]])
        return self.l3defipKey

    def __get_vsh_head_key(self):
        if self.vshHeadKey is None:
            self.vshHeadKey = Key([[r"(\S+)/(\S+)\s+(\S+)\s+(\S+)", "once"]])
        return self.vshHeadKey

    def __get_fwm_int_vlan_key(self):
        if self.fwmIntVlanKey is None:
            self.fwmIntVlanKey = Key([[r"\S+:\s+iftype\s+\S+\s+if_index\s+\S+"
                                       "\s+int-vlan\s+(\d+)\s+l3iif\s+(\S+)\s"
                                       "+", "once"]])
        return self.fwmIntVlanKey

    def __get_eltm_int_vlan_key(self):
        if self.eltmIntVlanKey is None:
            self.eltmIntVlanKey = Key([[r"\S+\s+=\s+INTF VLAN\s+,\s+bd\s+=\s+(\d+)\S+", "once"]])
        return self.eltmIntVlanKey

    def __get_eltm_intf_key(self):
        if self.eltmIntfKey is None:
            self.eltmIntfKey = Key([[r"\S+\s+=\s+INTF LIF\s+,\s+LIF\s+=\s+(\d+)\s+\S+"
                                     "\s+LTL\s+=\s+\d+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+", "once"]])
        return self.eltmIntfKey

    def __get_arp_table(self):
        return NXCLI('show ip arp').get_output()

    def __get_l3_l3_table(self):     
        return bcm_sdk_shell_all_unit('l3 l3table show')
        
    def __get_l3_defip(self):
        return bcm_sdk_shell_all_unit('l3 defip show')
        
    def __get_l3_egress(self):
        return bcm_sdk_shell_all_unit('l3 egress show')

    def __get_l3_intf(self):
        return bcm_sdk_shell_all_unit('l3 intf show')

    def __get_vsh_routes(self):
        return NXCLI('show forwarding ip route vrf all').get_output()

    def __rib_route(self):
        return NXCLI('show ip route').get_raw_output()

    def __parse_arp_table(self):
        arpEntry = []
        arpData = self.__get_arp_table()
        aKey = self.__get_arp_key()
        aParser = LineParser(arpData,aKey)
        data = aParser.get_data(aKey)
        for d in data:
            addr,mac,intf = d
            arpEntry.append([addr,mac,intf])
        return arpEntry

    def __parse_l3_egress(self):
        egressEntry = {}
        status,output = self.__get_l3_egress()
        l3Egress = output.split("\n")
        eKey = self.__get_egress_key()
        eParser = LineParser(l3Egress,eKey)
        data = eParser.get_data(eKey)
        intfData = self.__parse_l3_intf()
        for d in data:
            entry,mac,vlan,intf,port,value = d
            # if port is a digit then display the port directly
            try:
                port = int(port)
                if port != 0:
                    if type(port) is int:
                        port = "{0}/{1}".format("Ethernet1",port)
                egressEntry[entry] = [mac,vlan,intf,port]
            except ValueError:
                vlan,mac1 = intfData[intf]
                vlan = "Vlan" + vlan
                egressEntry[entry] = [mac,vlan,intf,vlan]
        return egressEntry
  
    def __parse_l3_intf(self):
        intfData = {}
        status,output = self.__get_l3_intf()
        l3Intf = output.split("\n")
        iKey = self.__get_l3_int_key()
        iParser = LineParser(l3Intf,iKey)
        data = iParser.get_data(iKey)
        for d in data:
            intf,vlan,mac = d
            intfData[intf] = [vlan,mac]
        return intfData

    def __parse_l3_table(self):
        routes = []
        egressEntry = self.__parse_l3_egress()
        intfData = self.__parse_l3_intf()
        status,output = self.__get_l3_l3_table()
        l3table = output.split("\n")
        key = self.__get_l3_table_key()
        lineParser = LineParser(l3table,key)
        data = lineParser.get_data(key)
        for d in data:
            addr,nexthop = d
            if nexthop in self.validHops:
                routes.append([addr,'32',nexthop])
            else:
                macAddr,vlan,intf,port = egressEntry[nexthop]
                routes.append([addr,'32',port])

        return routes

    def __parse_l3_defip(self):
        routes = []
        egressEntry = self.__parse_l3_egress()
        intfData = self.__parse_l3_intf()
        status,output = self.__get_l3_defip()
        l3defip = output.split("\n")
        key = self.__get_l3_defip_key()
        lineParser = LineParser(l3defip,key)
        data = lineParser.get_data(key)
        for d in data:
            addr,prefix,nexthop = d
            #routes.append([addr,prefix,nexthop])
            if nexthop in self.validHops:
                routes.append([addr,prefix,nexthop])
            else:
                macAddr,vlan,intf,port = egressEntry[nexthop]
                routes.append([addr,prefix,port])
  
        return routes

    def __parse_vsh_routes(self):
        routes = []
        # vsh routes
        fibRoute = self.__get_vsh_routes()
        key = Key(start=r"^\d+.\d+.\d+.\d+/\d+")
        sections = SectionParser(fibRoute,key).get_sections()
        headKey = self.__get_vsh_head_key()
        for d in sections:
            head,body = d
            lineParser = LineParser([head],headKey)
            addr,prefix,nexthop,intf =  lineParser.get_datum(headKey)
            try:
                nexthop = self.hopEntries[nexthop]
                #print "intf={0} nexthop={1}".format(intf, nexthop)
            except KeyError:
                cmd = "{0} {1}".format("show system internal eltm info interface", intf)
                eltmInfo = NXCLI(cmd).get_raw_output()
                intfKey = self.__get_eltm_int_vlan_key()
                eltmInfoParser = LineParser([eltmInfo], intfKey)
                lif = eltmInfoParser.get_datum(intfKey)
                #print "intf={0} lif={1}".format(intf, lif)
                nexthop = lif 
            routes.append([addr,prefix,nexthop])
            for j in body:
               print j
        return routes

    def verify_route(self,route=""):
        return self.verify_routes()

    def show_arp_table(self):
        return nxos_utils.cli_ex('show ip arp')

    def show_vsh_routes(self):
        return nxos_utils.cli_ex('show forwarding ip route vrf all')

    def show_hw_routes(self):
        hwRoutes = 0
        routeTable = []
        l3TableRoutes = self.__parse_l3_table()
        l3DefipRoutes = self.__parse_l3_defip()
        for l3t in l3TableRoutes:
            routeTable.append(l3t)
        for l3d in l3DefipRoutes:
            routeTable.append(l3d)

        intf = []
        print "------------------+------------------+---------------------"
        print "Prefix            | Next-hop         | Interface"
        print "------------------+------------------+---------------------"
        for i in routeTable:
            addr,prefix,nexthop = i
            intf = []
            #fix the below for null
            try:
                nexthop, intf = self.validHops[nexthop]
            except KeyError:
                intf = nexthop
  
            ipaddr = '{0}/{1}'.format(addr,prefix)
            print '{0:<20}{2:<20}{3:<20}'.format(ipaddr,prefix,nexthop,intf)
            hwRoutes += 1
        return hwRoutes

    def verify_routes(self):
        vshRoutes = []
        l3TableRoutes = []
        l3DefipRoutes = []

        # vsh routes
        vshRoutes = self.__parse_vsh_routes()
        # hw routes
        l3TableRoutes = self.__parse_l3_table()
        l3DefipRoutes = self.__parse_l3_defip()

        routesFound = 0
        routesNotFound = []
        for vr in vshRoutes:
            if vr in l3TableRoutes:
                routesFound += 1
            elif vr in l3DefipRoutes:
                routesFound += 1
            else:
                routesNotFound.append(vr)

        print
        print "Routes verified and found: ", routesFound
        print
        if len(routesNotFound) > 0:
            print "Routes not found: "
            for i in routesNotFound:
                addr,prefix,nexthop = i
                intf = []
                ipaddr = '{0}/{1}'.format(addr, prefix)
                print '{0:<20}{1:<20}'.format(ipaddr, nexthop)
        return routesFound, len(routesNotFound)

    def verify_arp_table(self):
        arpTable = []
        l3TableRoutes = []
        l3DefipRoutes = []
        l3Egress = []
        iparpCount = 0
        found = 0
        verified = 0
        notverified = 0
        intfData = {}

        # arp entries
        arpTable = self.__parse_arp_table()

        # hw routes
        l3TableRoutes = self.__parse_l3_table()
        l3DefipRoutes = self.__parse_l3_defip()
        l3Egress = self.__parse_l3_egress()
        l3Intf = self.__parse_l3_intf()
        #do a reverse lookup on the l3 egress table and get the port
        for d in l3Egress:
            mac,vlan,intf,port = l3Egress[d]
            intfData[intf] = [mac,port]
            intfData[d] = [mac,port]

        #if sub interface verify the vlan for the sub-intf with the l3 intf 
        #vlan
        for d in arpTable:
            addr, mac, intf = d
            # handle the dead beef mac
            found = 0
            nexthop = ""
            for l3t in l3TableRoutes:
                if found == 0:
                    ip, prefix, nh = l3t
                    if addr == ip:
                        found = 1
                        nexthop = nh
            if found == 0:
                for l3d in l3DefipRoutes:
                    if found == 0:
                        ip, prefix, nh = l3d
                        if addr == ip:
                            found = 1
                            nexthop = nh
            if found == 0:
                raise ValueError, 'Entry for addr not found in HW'
            if nexthop == "":
                raise ValueError, 'HW table entry not found'
            else:
                try:
                    macAddr, port = intfData[nexthop]
                except KeyError:
                    macAddr = ''
                    port = ''
                print "mac address:" + macAddr

                if mac.replace(".","") == macAddr.replace(":","") :
                    verified += 1
                    print "Arp entry for " + addr, mac, intf + " found in HW"
                else:
                    notverified += 1
                    print ("Arp entry for " + addr, mac, intf + " not found in"
                           " HW")
        return verified, notverified

    def __build_route(self, srcIp="", prefix="", mask="", intf= "", nexthop="",
                      nhMask="", nhPrefix="", tag = "", routePref = ""):
        route = "ip route " + srcIp

        if prefix != "":
            route += "/" + prefix
        elif mask != "":
            route += " " + mask

        if intf != "":
            # check if vlan or port-channel and verify they are created
            s, o  = nxcli("show running-config interface " + str(intf))
            if s == 0:
                route += " " + intf
            else:
                raise ValueError, 'interface %s is not created' % intf
                route = ""
                return route

        if nexthop != "" :
            route += " " + nexthop

        if nhPrefix != "":
            route += "/" + nhPrefix
        elif nhMask != "":
            route += " " + nhMask

        if tag != "":
            route += " tag " + str(tag)

        if routePref != "":
            route += " " + str(routePref)
        
        return route


    def add_route(self, srcIp="", prefix="", mask="", intf="", nexthop="", 
                  nhMask="", nhPrefix="", tag="", routePref="", vrf="default"):

        confStr = "config t ; "

        if vrf != "default":
            confStr += "vrf context " + vrf + " ; "
        if srcIp == "":
            raise ValueError, 'IP address not given to add route'
 
        route = self.__build_route(srcIp, prefix, mask, intf, nexthop, nhMask,
                                   nhPrefix,tag,routePref)

        confStr += route + " ; " + "end ;"

        print "Vrf: " + vrf
        print "Route to be added: " + route

        return nxos_utils.cli_ex(confStr)

    def delete_route(self, srcIp="", prefix="", mask="", intf="", nexthop="", 
                     nhMask="", nhPrefix="", tag="", routePref="", 
                     vrf="default"):

        confStr = "config t ;"
        if vrf != "default":
            confStr += "vrf context " + vrf + " ; "

        if srcIp == "":
            raise ValueError, 'IP address not given to add route'

        route = self.__build_route(srcIp, prefix, mask, intf, nexthop, nhMask,
                                   nhPrefix, tag, routePref)

        confStr += "no " + route + " ; " + "end ;"

        print "Vrf: " + vrf
        print "Route to be deleted: " + route

        return nxos_utils.cli_ex(confStr)


