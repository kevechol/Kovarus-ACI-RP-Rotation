#!/bin/env python

import sys, socket, select

cmd = ''
for i in range(1, len(sys.argv)):
    cmd += sys.argv[i] + ' '

target = sys.argv[len(sys.argv) - 1]
server_address = "/isan/vdc_1/virtual-instance/{0}/rootfs/home/admin/cliserver.sock".format(target)

s = None
try:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(server_address)
except:
    print "virtual-service {0} not available".format(target)
    sys.exit(1)

#print cmd
try:
    s.send(cmd)
    ready = select.select([s], [], [], 10)
    if ready[0]:
        print s.recv(4096)
    else:
        print 'virtual-service {0} not available. Try again later.'.format(target)
except:
    print "virtual-servcie {0} internal error".format(target)
