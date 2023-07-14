# extracting information about electric cars from a list of VINs
# python getvin.py [input file] [summary file (.txt)] [detail_file(.csv)]
# needs one input file to exist in the same directory: VIN_List.csv or pass in a filename.  
# The input file is in CSV format, with a header that has at least one field named VIN. Other fields are optional 
# A sample VIN_List.csv file is provided. 
# summary results are printed to the console, as well as to the output_summary file

# 2023-07-13 Added Primary and Secondary Fuel type to summary

import requests,json,csv,time, subprocess, argparse;
from requests.exceptions import ConnectTimeout

CHUNKSIZE=40  # NHTSA says they can handle  50 VINs at a time, but why push it?
DEFAULT_DELAY = 2    # NHTSA does rate-limiting, but doesn't document the time. Let's start here, and double if failure
default_input_filename = 'VIN_List.csv'
default_output_summary = 'EV_Counts.txt'
default_output_details = 'EV_Details.csv'
output_headers = ['Make', 'Model', 'ModelYear', 'VIN', 'FuelTypePrimary','FuelTypeSecondary','ElectrificationLevel']

parser = argparse.ArgumentParser(description='extracting information about electric cars from a list of VINs')
parser.add_argument('input_filename',
                    help='input filename',
                    nargs='?',
                   default = default_input_filename)
parser.add_argument('summary_filename',
                    help='CSV file name for summary (one  line per type of EV found)',
                     nargs='?',
                   default = default_output_summary)
parser.add_argument('details_filename',
                    help='text file name for details (one  line per EV found)',
                     nargs='?',
                   default = default_output_details)

args = parser.parse_args()
input_filename = args.input_filename
output_summary = args.summary_filename
output_details = args.details_filename
print('using input filename: ',input_filename)

Counter = dict()
lines_processed = 0
EVs_found = 0
             
def lookup_vin_and_count_EVs(VINs, writer):
    global EVs_found
    delay = DEFAULT_DELAY
    r = None
    url = 'https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVINValuesBatch/';
    
    post_fields = {'format': 'json', 'data': ";".join(VINs)};
    try:            
        r = requests.post(url, data=post_fields, timeout = 5*delay);
    except requests.Timeout as err:
        print ('\nTimeout..')
    if (not r):
        print (post_fields['data'])
        time.sleep(delay)
        retries = 4
        while not r and retries > 1:
            delay = delay * 2
            retries -= 1
            print ("Trying again with delay of", delay)
            try:
                r = requests.post(url, data=post_fields, timeout = 5*delay); 
            except requests.Timeout as err:
                print ('timeout on retry')
            time.sleep(delay)    
        if (not retries >1):
            return;
        
    obj = json.loads(r.text);
    for results in obj["Results"]:
        fuel_type_primary = results.get("FuelTypePrimary","")
        fuel_type_secondary = results.get("FuelTypeSecondary","")
        electrification_level = results.get("ElectrificationLevel", "")
      
        if (len(fuel_type_primary) == 0 or fuel_type_primary == 'Not Applicable'):
            Summary_type = "Non-Fuel Vehicle: might be a trailer or a bad VIN"
        else:
            Summary_type = fuel_type_primary
        if (len(fuel_type_secondary) == 0 or fuel_type_secondary == 'Not Applicable'):
            Summary_type += "|"
        else:
            Summary_type += "|" + fuel_type_secondary
        if (len(electrification_level) == 0 or electrification_level == 'Not Applicable'):
            Summary_type += '|'
        else:
            Summary_type += "|" + electrification_level
            EVs_found += 1;
            row = {\
              'Make':      results.get("Make", "(No Make)"),\
              'Model':	   results.get("Model", "(No Model)"),\
              'ModelYear': results.get("ModelYear", "(No Model Year)"),\
              'VIN':	   results.get("VIN","(NO VIN)"), \
              'FuelTypePrimary': fuel_type_primary, \
              'FuelTypeSecondary': fuel_type_secondary, \
              'ElectrificationLevel': electrification_level\
              }
            writer.writerow(row) 
        Counter[Summary_type] = 1 + Counter.get(Summary_type,0)
        if (Counter[Summary_type] == 1):
            print("new summary type: ", Summary_type)    

#        print(results)     
        
    print('Lines Processed: [%d]\r' % (lines_processed), end="")

def print_summary():
    print('Lines Processed: [%d]' % (lines_processed))
    with open(output_summary, 'w') as f:
        for summary_type in Counter:
            print(summary_type, ': ', Counter[summary_type], file= f)
            print(summary_type, ': ', Counter[summary_type])
            
        Summary = f" Summary: \n EVs found: {EVs_found} \n Non-EVs: {lines_processed - EVs_found}\n Total: {lines_processed}"
        print(Summary)
        print(Summary, file=f)
        print("detailed results available in ", output_details)    

# our main function: open input and output files, collect VINs and call worker function for calculation and output
with open(input_filename, newline='') as fin, open(output_details, 'w') as fout:
    #  future work: get any extra fieldnames from input file and add them to putput file
    reader = csv.DictReader(fin)
    writer = csv.DictWriter(fout, fieldnames=output_headers)
    writer.writeheader()
    delay = DEFAULT_DELAY;
    retries = 5
       
    try:
        VINs = []
        for row in reader:
            lines_processed += 1
            VINs.append(row["VIN"]) 
            if (lines_processed % CHUNKSIZE == 0):
                lookup_vin_and_count_EVs(VINs, writer) 
                VINs = []
                       
        if (lines_processed % CHUNKSIZE != CHUNKSIZE-1):
            # final data of a less than full chunk
            lookup_vin_and_count_EVs(VINs, writer)
            
    except csv.Error as e:
        sys.exit('file {}, line {}: {}'.format(filename, reader.line_num, e))

print_summary()

