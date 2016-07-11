#############################################################################
# Author    :   Rams Ramanujalu
#
# File      :   iethdecode.py
#
# Purpose   :   Ieth hdr decoder
#
# Copyright (c) 2015 by cisco Systems, Inc.
# All rights reserved.
#
#############################################################################

# !/auto/antares/tools/sdktools/sysroot/usr/bin/python
import re
import os
import sys
import binascii

ieth_header_fields = ['pkt_hash[8]:',
                      'src_is_peer[1]:',
                      'tclass[4]:',
                      'cos_de[4]:',
                      'sup_code[5]:',
                      'sup_tx[1]:',
                      'l2_tunnel[1]:',
                      'dst_is_tunnel[1]:',
                      'src_is_tunnel[1]:',
                      'ip_ttl_bypass[1]:',
                      'alt_if_profile[1]:',
                      'span[1]:',
                      'dont_lrn[1]:',
                      'traceroute[1]:',
                      'bd_lo[1]:',
                      'bd_hi[13]:',
                      'outer_bd[9]:',
                      'dst_port[8]:',
                      'dst_chip_lo[2]:',
                      'dst_chip_hi[6]:',
                      'src_port[8]:',
                      'src_chip[8]:',
                      'dst_idx_lo[10]:',
                      'dst_idx_hi[4]:',
                      'src_idx[14]:',
                      'opcode[4]:',
                      'ext_hdr[1]:',
                      'hdr_type[1]:',
                      'sof[8]:']

ieth_field_lengths = ['8',
                      '1',
                      '4',
                      '4',
                      '5',
                      '1',
                      '1',
                      '1',
                      '1',
                      '1',
                      '1',
                      '1',
                      '1',
                      '1',
                      '1',
                      '13',
                      '9',
                      '8',
                      '2',
                      '6',
                      '8',
                      '8',
                      '10',
                      '4',
                      '14',
                      '4',
                      '1',
                      '1',
                      '8']


def byte_to_binary(n):
    return ''.join(str((n & (1 << i)) and 1) for i in reversed(range(8)))


def hex_to_binary(h):
    return ''.join(byte_to_binary(ord(b)) for b in binascii.unhexlify(h))


def get_header_binary(header):
    return hex_to_binary(header)


def decode_ieth_header(header):
    '''The header must be in hex format'''
    num_fields = 0
    pos = 0
    ieth_header_len = 128
    printstr = ""

    if (('0x' in header and len(header) > 34) or
            ('0x' not in header and len(header) > 32)):
        print 'Ieth header length greater than 16 bytes. Try again'
        return

    print 'Ieth Header: 0x{0}'.format(header.zfill(32))
    num_fields = len(ieth_header_fields)

    if num_fields == 0:
        print 'Incorrect header definition'
        return

    print 'iEth header Fields'
    bin_head = bin(int(header, 16))[2:]
    # Make binary header a full 128 bit field
    bin_head = bin_head.zfill(128)
    # print "bin_head={0}\n".format(bin(int(header, 16))[2:])

    while True:
        num_fields = num_fields - 1

        c = int(ieth_field_lengths[num_fields])
        # print "%s \t" % c

        if ieth_header_fields[num_fields] == "dst_idx_hi[4]:":
            printstr = "dst_idx[14]:"
            num_fields = num_fields - 1
            c = c + int(ieth_field_lengths[num_fields])
        elif ieth_header_fields[num_fields] == "dst_chip_hi[6]:":
            printstr = "dst_chip[8]:"
            num_fields = num_fields - 1
            c = c + int(ieth_field_lengths[num_fields])
        elif ieth_header_fields[num_fields] == "bd_hi[13]:":
            printstr = "bd[14]:"
            num_fields = num_fields - 1
            c = c + int(ieth_field_lengths[num_fields])
        else:
            # Do nothing different
            printstr = ieth_header_fields[num_fields]

        print "%s %s" % (printstr, hex(int((bin_head[pos:pos + c]), 2)))
        pos = pos + int(c)
        # print "%d" % pos

        if pos > ieth_header_len:
            print 'Incorrect header length given %d' % pos
            return

        if num_fields == 0:
            # print 'iEth header End'
            return

    return


if __name__ == "__main__":
    i = 1
    header = ""

    # print len(sys.argv)
    while True:
        if i >= len(sys.argv):
            break
        header = header + sys.argv[i]
        i = i + 1

    # print header
    if (len(header) < 32):
        print 'Incorrect length %d. Will Prefix 0\'s\n' % len(header)
        header = header.zfill(32)

    # print 'length %d' % len(header)
    decode_ieth_header(header)
