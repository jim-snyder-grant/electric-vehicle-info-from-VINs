# extracting information about electric cars from a list of VINs
# python getvin.py [input file] [summary file (.txt)] [detail_file(.csv)]
# needs one input file to exist in the same directory: VIN_List.csv or pass in a filename.  
# The input file is in CSV format, with a header that has at least one field named VIN. Other fields are optional 
# A sample VIN_List.csv file is provided. 
# summary results are printed to the console, as well as to the output_summary file

import requests,json,csv,time, subprocess, argparse;
from requests.exceptions import ConnectTimeout

CHUNKSIZE=40  # NHTSA says they can handle  50 VINs at a time, but why push it?
DEFAULT_DELAY = 2    # NHTSA does rate-limiting, but doesn't document the time. Let's start here, and double if failure
default_input_filename = 'VIN_List.csv'
default_output_summary = 'EV_Counts.txt'
default_output_details = 'EV_Details.csv'
output_headers = ['Make', 'Model', 'ModelYear', 'VIN', 'ElectrificationLevel']

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

counter = dict()
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
        print ('timeout..')
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
        e_level = results.get("ElectrificationLevel", "")
        if (len(e_level) > 0) and e_level != 'Not Applicable':
            counter[e_level] = 1 + counter.get(e_level, 0);
            
            EVs_found += 1;
            row = {\
              'Make':      results.get("Make", "(No Make)"),\
              'Model':	   results.get("Model", "(No Model)"),\
              'ModelYear': results.get("ModelYear", "(No Model Year)"),\
              'VIN':	   results.get("VIN","(NO VIN)"), \
              'ElectrificationLevel': e_level\
              }
            writer.writerow(row)          
    print('Lines Processed: [%d]\r' % (lines_processed), end="")

def print_summary():
    print('Lines Processed: [%d]' % (lines_processed))
    with open(output_summary, 'w') as f:
        for level in counter:
            print(level, ': ', counter[level], file= f)
            print(level, ': ', counter[level])
        Summary = f" Summary: \n EVs found: {EVs_found} \n Non-EVs: {lines_processed - EVs_found}\n Total: {lines_processed} "
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
            if (lines_processed % CHUNKSIZE == CHUNKSIZE-1):
                lookup_vin_and_count_EVs(VINs, writer) 
                VINs = []
                       
        if (lines_processed % CHUNKSIZE != CHUNKSIZE-1):
            # final data of a less than full chunk
            lookup_vin_and_count_EVs(VINs, writer)
            
    except csv.Error as e:
        sys.exit('file {}, line {}: {}'.format(filename, reader.line_num, e))

print_summary()

