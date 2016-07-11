#!/usr/bin/env python

'''

    Tool used to drain traffic from a nexus device prior to shutting it down

'''

import argparse

def getargs():
    parser = argparse.ArgumentParser()
    parser.add_argument('positional',
                        required=True,
                        action='store',
                        help='This is an example of a positional argument')
    parser.add_argument('-s', '--stuff',
                        required=True,
                        action='store',
                        help='Placeholder for help')
    parser.add_argument('-t', '--test',
                        required=True,
                        action='store',
                        help='more sample help',
                        dest='test_var')
    args = parser.parse_args()
    return args

def overload_ospf(sw):
    # TODO command is 'max-metric router-lsa' on OSPF
    pass

def overload_bgp(sw):
    # TODO find the command to do this in BGP
    pass





def main():
    pass



if __name__ == '__main__':
    main()


