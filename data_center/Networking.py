'''

Class that extends the p2pnetwork class to add application specific implementation details.
Handles how communication happens between the access proxy, trust engine, policy engine, and data center.
Uses peer to peer communication without involvement of a centralized server for establishing connections.

'''
import threading

from p2pnetwork.node import Node
from retrieve_data_request import *

class Networking(Node):
    # Define a dictionary of the node roles based on their node.id attributes
    NODE_ROLE = {
        '1':'Access Proxy Node',
        '2':'Trust Engine Node',
        '3':'Policy Engine Node',
        '4':'Web UI',
        '5':'Data Center Node'
    }

    # Define a dictionary of the node [host, port] based on their node.id attributes
    NODE_CONNECT = {
        '1': ['127.0.0.1', 8001],
        '2': ['127.0.0.1', 8002],
        '3': ['127.0.0.1', 8003],
        '4': ['127.0.0.1', 8004],
        '5': ['127.0.0.1', 8005]
    }

    # Python class constructor to initialize the class Networking
    def __init__(self, host, port, id=None, callback=None, max_connections=0):
        super(Networking, self).__init__(host, port, id, callback, max_connections)

        # Node connection handling
        self.expected_node_id = None  # expected connection node id
        self.connected_to_node = threading.Event()

        print(f"\n{self.get_node_role(self.id)} STARTED on {self.host}:{self.port}")
    
    # Define a function to extract the name of a node based on it's node.id attribute
    def get_node_role(self, node_id):
        return self.NODE_ROLE.get(node_id,'UNKNOWN ROLE')

    # Wait for node to be connected
    def wait_for_connection(self, node_id):
        # Check if node is connected
        is_connected = any(node.id == node_id for node in self.all_nodes)

        # Wait for node if not connected
        if not is_connected:
            # Reconnect to node
            self.connect_with_node(self.NODE_CONNECT.get(node_id)[0],
                                   self.NODE_CONNECT.get(node_id)[1])

            # Wait for node to connect
            self.expected_node_id = node_id
            self.connected_to_node.clear() #ensure event not set

            self.connected_to_node.wait(timeout=10)
            self.connected_to_node.clear() #clear when done

    def send_message_to_node(self, node_id, message):
        # Find the specific node by its ID
        target_node = None
        is_outbound = False

        # Convert the message to a json object
        json_message = {
            "senderID": self.id,
            "messageContent": message
        }

        # Check if target node is outbound connected
        for node in self.nodes_outbound:
            if node.id == node_id:
                is_outbound = True
                target_node = node

                # Send the message to the specific node
                self.send_to_node(target_node, json_message)

                print(f"Message sent outbound to: {self.get_node_role(node_id)}")
                break

        # Check if target node is inbound connected
        if not is_outbound:
            # Get inbound-only connection nodes
            inbound_only = list(set(self.nodes_inbound) - set(self.nodes_outbound))
            for node in inbound_only:
                if node.id == node_id:
                    target_node = node

                    # Send the message to the specific node
                    target_node.send(json_message)

                    print(f"Message sent inbound to: {self.get_node_role(node_id)}")
                    break

        if target_node is None:
            print(f"Node {node_id} not found in inbound or outbound connections.")

    def message_is_from_access_proxy(self, sender_id):
        return sender_id == '1'

    def message_is_from_trust_engine(self, sender_id):
        return sender_id == '2'

    def message_is_from_policy_engine(self, sender_id):
        return sender_id == '3'

    def process_message_from_access_proxy(self, sender, message):
        print(f"\nReceived a Data Request from Access Proxy [{sender}]: {message.get('intent')}")

        # Implement logic for adding the access request in the JSON file
        if message.get('intent', '').lower() == 'access request':
            # Add next available ID to access_request
            req_id, existing_data = get_next_access_req_id()
            access_request = {'ID': req_id}
            access_request = {**access_request, **message} #add ID to request beginning

            # Add new access request to JSON file
            existing_data.append(access_request)
            dump_file_with_lock('access_requests.json', existing_data)

        # Update events JSON file with Keycloak events
        elif message.get('intent') == 'store_keycloak_events':
            events = message.get('events')
            store_keycloak_events(events)
            print("Keycloak events updated in json file.")

            # Process event data to yield the auth_data
            process_events(events)

        # Update user data JSON file
        elif message.get('intent') == 'update_user_roles':
            # Load existing data from the file if it exists
            existing_data, __ = load_data_with_lock('user_data.json')

            # Update existing records without overwriting existing roles
            extracted_data = message.get('extracted_data')
            for existing_user in existing_data:
                for new_user in extracted_data:
                    if existing_user['user_id'] == new_user['user_id'] and new_user['user_role'] is not None:
                        existing_user['user_role'] = new_user['user_role']
                        break

            # Combine existing and new data without duplicates
            user_ids_in_file = {user['user_id'] for user in existing_data}
            for new_user in extracted_data:
                if new_user['user_id'] not in user_ids_in_file:
                    existing_data.append(new_user)

            # Store the updated and new data in the JSON file
            dump_file_with_lock('user_data.json', existing_data)

        # Send access requests JSON file to WebUI
        elif message.get('intent') == 'request_access_requests':
            # Load data from JSON file
            __, access_requests = get_next_access_req_id()
            data = {
                'access_requests': access_requests
            }

            # Ensure connection is up & send message
            self.wait_for_connection('4')
            self.send_message_to_node('4', data)

        # Update Policy YAML file
        elif message.get('intent') == 'update_policy_configs':
            data = message.get('data')
            status = update_policy_configurations(data)
            data = {
                'status': status
            }

            # Ensure connection is up & send message
            self.wait_for_connection('4')
            self.send_message_to_node('4', data)


    def process_message_from_trust_engine(self, sender, message):
        print(f"\nReceived a Data Request from Trust Engine Node: [{sender}]: {message.get('intent')}")
        # Return user identity data for user_id
        if message.get('intent') == 'request_user_data':
            user_id = message.get('user_id')

            # Get data for ta calculations
            user = get_user_identity_data_by_id(user_id)
            latest_request = get_latest_access_request(user_id)
            latest_data = get_latest_auth_data(user_id)

            # Get next available access decision ID
            dec_id, __, __ = get_next_access_dec_id()

            user_data = {
                'user': user,
                'latest_request': latest_request,
                'latest_data': latest_data,
                'new_id': dec_id
            }
            data = {'user_data': user_data}

            # Ensure connection is up & send message
            self.wait_for_connection(sender)
            self.send_message_to_node(sender, data)

        # Return policy configuration data
        elif message.get('intent') == 'request_loc_configs':
            # Get policy configurations
            (high_risk_countries, medium_risk_countries, low_risk_countries,
             period_start, period_end) = load_policy_location_configs()

            # Setup data to convert to JSON format
            policy_data = {
                'high_risk_countries': high_risk_countries,
                'medium_risk_countries': medium_risk_countries,
                'low_risk_countries': low_risk_countries,
                'period_start': period_start,
                'period_end': period_end
            }

            # Convert YAML data to JSON format
            json_str = json.dumps(policy_data)
            data = {'ta_data': json_str}

            # Ensure connection is up & send message
            self.wait_for_connection(sender)
            self.send_message_to_node(sender, data)


    def process_message_from_policy_engine(self, sender, message):
        print(f"\nReceived a Data Request from Policy Engine Node: [{sender}]: {message.get('intent')}")
        # Implement logic for adding the access decision in the json file
        if message.get('intent') == 'request_access_decision':
            __, access_decisions, file_path = get_next_access_dec_id()

            # Append the new access decision data to the existing list
            access_decisions.append(message)

            # Write the updated data to the JSON file
            dump_file_with_lock('access_decisions.json', access_decisions)

        # Return policy configuration data for Policy Engine
        elif message.get('intent') == 'request_threshold_configs':
            # Get policy configurations
            (admin_threshold, approver_threshold,
             security_viewer_threshold, sign_in_risk_threshold) = load_policy_threshold_configs()

            policy_data = {
                'admin_threshold': admin_threshold,
                'approver_threshold': approver_threshold,
                'security_viewer_threshold': security_viewer_threshold,
                'sign_in_risk_threshold': sign_in_risk_threshold
            }

            # Convert YAML data to JSON format
            json_str = json.dumps(policy_data)
            data = {'policy_data': json_str}

            # Ensure connection is up & send message
            self.wait_for_connection(sender)
            self.send_message_to_node(sender, data)

    def print_all_nodes(self): #unused but here for convenience
        print("Outbound Nodes:")
        for node in self.nodes_outbound:
            print(f"Outbound Node ID: {node.id}, Host: {node.host}, Port: {node.port}")

        print("\nInbound Nodes:")
        for node in self.nodes_inbound:
            print(f"Inbound Node ID: {node.id}, Host: {node.host}, Port: {node.port}")


    # The methods below are called when events happen in the network

    def outbound_node_connected(self, node):
        print(f"\n{self.get_node_role(self.id)} Connected to {self.get_node_role(node.id)}")
        # Set thread event if expected node connected
        if node.id == self.expected_node_id:
            self.connected_to_node.set()
        
    def inbound_node_connected(self, node):
        print(f"\n{self.get_node_role(node.id)} Connected to {self.get_node_role(self.id)}")
        # Set thread event if expected node connected
        if node.id == self.expected_node_id:
            self.connected_to_node.set()

    def outbound_node_disconnected(self, node):
        print(f"\n{self.get_node_role(self.id)} DISCONNECTED from {self.get_node_role(node.id)}")
        self.connect_with_node(node.host, node.port)

    def inbound_node_disconnected(self, node):
        print(f"\n{self.get_node_role(node.id)} DISCONNECTED from {self.get_node_role(self.id)}")
        self.connect_with_node(node.host, node.port)

    def node_message(self, node, data):
        sender_id = node.id  # Get the sender's ID
        message_content = data  # Get the message content

        if "senderID" in message_content:
            message_content = message_content["messageContent"]
            #extract other future message attributes like unique hash, and message intent

        # Process the message based on the sender's ID
        if self.message_is_from_access_proxy(sender_id):
            self.process_message_from_access_proxy(sender_id, message_content)
        elif self.message_is_from_trust_engine(sender_id):
            self.process_message_from_trust_engine(sender_id, message_content)
        elif self.message_is_from_policy_engine(sender_id):
            self.process_message_from_policy_engine(sender_id, message_content)
        else:
            print(f"Received a message from an unknown sender ({sender_id}): {message_content}")
        
    def node_disconnect_with_outbound_node(self, node):
        print(f"\n{self.get_node_role(self.id)} wants to disconnect with {node.id}")   
            
    def node_request_to_stop(self):
        print(f"\nStopping the {self.get_node_role(self.id)} node")
        
