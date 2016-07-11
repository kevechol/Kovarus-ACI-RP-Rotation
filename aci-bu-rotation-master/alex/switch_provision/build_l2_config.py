#!/usr/bin/env python

import csv
from jinja2 import Template
import xlsx2csv
import glob
import build_config

# Convert the configuration workbook to individual CSV files for consumption.

def xlsxtocsv(xlsx_file):
    xlsx2csv.Xlsx2csv(xlsx_file).convert('portmap',sheetid=0)

# Creates a list.
output = []

# Defines a function get_patchplan that accepts a filename.

def get_patchplan(csv_file):
    '''
    Reads a csv file on disk and then transforms it into a format that is used for csv.DictReader later on.
    :param csv_file: CSV file - not explicitly defined, we are just looking for *.csv files
    :return: Returns a dictionary that includes Local Port, VLAN, Description (nicely formatted)
    '''
    for line in csv_file:
        if line['Device']:
            # Creates a dict
            row = {}
            row['LocalPort'] = line['Local Port']
            row["VLAN"] = line['VLAN']
            row["Description"] = line['Device'] + ":" + line['Dest Port'] + ":" + line['Purpose']
            output.append(row)

    # Make sure to return the object, or nothing actually happens.
    return output

# Use glob to find all csv files and for loop it through the export.

def main():

    for filename in glob.glob('portmap/*.csv'):
        with open(filename, 'r') as f:
            # Create a dict from the file.
            csv_file = csv.DictReader(f)

            # Run get_patchplan against the csv file.
            imported_vars = get_patchplan(csv_file)

            # Open the template.
            config_template = Template(open('templates/l2_port_template.j2').read())

            # Render the template with jinja.
            jinja_output =  config_template.render(interfaces=imported_vars)

        # Strip .csv from the file - we don't want to create any silly filenames!
        filename_config = filename.strip( '.csv' )

        # Write the file with filename_config (has .csv stripped), and then add .config to it.
        with open(filename_config+'.config', 'w') as g:
            g.write(jinja_output)

        print 'Writing ' + filename_config + ' successful.'

if __name__ == '__main__':
    main()