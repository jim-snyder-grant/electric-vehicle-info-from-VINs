# extracting information about electric cars from a list of VINs
# python getvin.py
# needs one input file to exist in the same directory: VIN_List.csv. The name can be edited below. 
# The input file is in CSV format, with a header that has at least one field named VIN. Other fields are optional 
# A sample VIN_List.csv file is provided. 
# summafry results are printed to the console, as well as to the output_summary file

import requests,json,csv,time, subprocess;

CHUNKSIZE=40  # NHTSA says they can handle  50 VINs at a time, but why push it?
input_filename = 'VIN_List.csv'
output_summary = 'EV_Counts.txt'
output_details = 'EV_Details.csv'
output_headers = ['Make', 'Model', 'ModelYear', 'VIN', 'ElectrificationLevel']

counter = dict()
lines_processed = 0
EVs_found = 0
             
def lookup_vin_and_count_EVs(VINs, writer):
    global EVs_found
    url = 'https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVINValuesBatch/';
    post_fields = {'format': 'json', 'data': ";".join(VINs)};
                
    r = requests.post(url, data=post_fields);
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
# our main function: open input and output files, collect VINs and call worker function for calculation and output
with open(input_filename, newline='') as fin, open(output_details, 'w') as fout:
    #  future work: get any extra fieldnames from input file and add them to putput file
    reader = csv.DictReader(fin)
    writer = csv.DictWriter(fout, fieldnames=output_headers)
    writer.writeheader()
       
    try:
        VINs = []
        for row in reader:
            lines_processed += 1
            VINs.append(row["VIN"]) 
            if (lines_processed % CHUNKSIZE == CHUNKSIZE-1):
                lookup_vin_and_count_EVs(VINs, writer)
                VINs = []
                time.sleep(4)   # NHTSA does rate-limiting. I guess a 4 second pause is enough           
        if (lines_processed % CHUNKSIZE != CHUNKSIZE-1):
            # final data of a less than full chunk
            lookup_vin_and_count_EVs(VINs, writer)
            
    except csv.Error as e:
        sys.exit('file {}, line {}: {}'.format(filename, reader.line_num, e))
print('Lines Processed: [%d]' % (lines_processed))

with open(output_summary, 'w') as f:
    for level in counter:
        print(level, ': ', counter[level], file= f)
        print(level, ': ', counter[level])
    Summary = f" Summary: \n EVs found: {EVs_found} \n Non-EVs: {lines_processed - EVs_found}\n Total: {lines_processed} "
    print(Summary)
    print(Summary, file=f)
    print("detailed results available in ", output_details)    
