# electric-vehicle-info-from-VINs
Input: one or many VINs. Output: summary and detailed information on any electric vehicles

This code was written to answer the question 'How many electric vehicles are registered in my town'
The assessor's office could download data with all the VINs into a CSV file. 
The NHTSA provides a web service to get detailed info associated with one or more VINs. 
That service is rate-limited, so the code takes a short break after processing each chunk. 
A summary and a detailed file are output. 
See code in getvin.py for details
