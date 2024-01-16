# import logging
# import json

# # THIS IS AN EXAMPLE FILE TO WRITE INTO LOG AND PARSE THE LOG

# logging.basicConfig(filename="something.log", level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
# data = {
#                 "term": 21,
#                 "leaderId" : "hi",
#                 "prevLogIndex" : 33,
#                 "entries" : ["new_entries","rwubg","itgnr"]
#             }
# json_data = json.dumps(data)
# # logging.info(json_data)
# logging.debug("Starting Thread for Append RPC from leader to follower ")

# with open("something.log", 'r') as file:
#     for line in file:
#         x = line.split("-")
#         try:
#             y = x[4][1:]
#             log_entry = json.loads(y)
#             # Process the log entry (e.g., print it)
#             print(log_entry)
#         except json.JSONDecodeError as e:
#             # Handle JSON decoding errors if needed
#             print(f"Error decoding JSON: {e}")



import json
import re
from datetime import datetime

log_file_path = 'something.log'

def parse_log_line(line):
    # Define a regular expression to match log entries
    log_pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - (\w+) - (.*)')

    # Use the regular expression to match log entries
    match = log_pattern.match(line)
    if match:
        timestamp_str, log_level, message_str = match.groups()

        # Convert timestamp string to a datetime object
        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')

        try:
            # Parse the message as JSON
            message = json.loads(message_str)
        except json.JSONDecodeError:
            # Handle the case where the message is not valid JSON
            message = {'raw_message': message_str}

        return {'timestamp': timestamp, 'log_level': log_level, 'message': message}
    else:
        print("None")
        return None

def read_log_file(file_path):
    with open(file_path, 'r') as file:
        # Read each line of the log file and parse it
        for line in file:
            log_entry = parse_log_line(line)
            if log_entry:
                print(log_entry)

# Call the function with the path to your log file
read_log_file(log_file_path)
