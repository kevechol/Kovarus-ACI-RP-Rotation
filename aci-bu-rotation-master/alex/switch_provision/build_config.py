import argparse
import build_l2_config as l2

# Grab arguments for script using argparse.
def getargs():
    '''
    :return: Returns argument values.
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--portmap',
                        required=True,
                        action='store',
                        help='Portmap file')
    args = parser.parse_args()

    return args

# If you don't use getargs(), nothing will ever come of getargs!

def main():
    args = getargs()

    l2.xlsxtocsv(args.portmap)
    l2.main()

if __name__ == '__main__':
    main()