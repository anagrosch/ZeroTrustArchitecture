import json
import os.path
from Networking import Networking

#Create an instance of this node
node_4 = Networking(Networking.NODE_CONNECT['4'][0], Networking.NODE_CONNECT['4'][1], 4)

#Start the node2
node_4.start()

debug = False
node_4.debug = debug

#Connect with node 1
node_4.connect_with_node(Networking.NODE_CONNECT['1'][0], Networking.NODE_CONNECT['1'][1]) #node 1
node_4.connect_with_node(Networking.NODE_CONNECT['3'][0], Networking.NODE_CONNECT['3'][1]) #node 3
node_4.wait_for_connection('3')

# Request current access requests log from Data Center
data_request = {'intent': 'request_access_requests'}
node_4.send_message_to_node('1', data_request)

node_4.wait_for_message() #wait for data center to return data
access_requests = node_4.received_message.get('access_requests')  # get data

# Check if data received, or if timeout triggered
if access_requests:
    # Create local copy of access requests JSON file
    file_path = os.path.abspath(os.path.join(os.getcwd(), 'access_requests.json'))

    with open(file_path, 'w') as file:
        json.dump(access_requests, file, indent=4)
    print("access_requests.json created locally")
else:
    print("Failed to receive access requests from data center")

# Clear received message dictionary
node_4.del_received_message_item('access_requests')
node_4.stop()
