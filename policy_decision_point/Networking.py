'''

Class that extends the p2pnetwork class to add application specific implementation details.
Handles how communication happens between the access proxy, trust engine, policy engine, and data center.
Uses peer to peer communication without involvement of a centralized server for establishing connections.

'''
import threading
import json

from p2pnetwork.node import Node
import TrustAlgorithm as ta

class Networking(Node):
    # Define a dictionary of the node roles based on their node.id attributes
    NODE_ROLE = {
        '1': 'Access Proxy Node',
        '2': 'Trust Engine Node',
        '3': 'Policy Engine Node',
        '4': 'Web UI',
        '5': 'Data Center Node'
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

        # Received message handling
        self.received_message = dict()
        self.message_updated = threading.Event()

        # Node connection handling
        self.expected_node_id = None  # expected connection node id
        self.connected_to_node = threading.Event()

        print(f"\n{self.get_node_role(self.id)} STARTED on {self.host}:{self.port}")
    
    #Define a function to extract the name of a node based on it's node.id attribute
    def get_node_role(self, node_id):
        return self.NODE_ROLE.get(node_id,'UNKNOWN ROLE')

    def set_received_message(self, message):
        self.received_message.update(message)  # Setter method to initialize the variable with the message

    def del_received_message_item(self, key):
        self.received_message.pop(key)

    # Wait for received_message to be updated
    def wait_for_message(self):
        self.message_updated.clear() #ensure event not set
        self.message_updated.wait(timeout=20)
        self.message_updated.clear()

    # Wait for node to be connected to Data Center
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

        # Send message through inbound connection if needed
        if target_node is None:
            print(f"Node {node_id} not found in inbound or outbound connections.")

    def message_is_from_access_proxy(self, sender_id):
        return sender_id == '1'

    def message_is_from_trust_engine(self, sender_id):
        return sender_id == '2'

    def message_is_from_data_center(self, sender_id):
        return sender_id == '5'

    def process_message_from_access_proxy(self, sender, message):
        print(f"\nReceived a message from Access Proxy Node [{sender}]: {message.get('intent')}")
        # If this node is trust engine, check if the intent is 'request_trust_score'
        if message.get('intent') == 'request_trust_score':
            user_id = message.get('user_id')

            # Get user data from data center
            data = {
                'user_id': user_id,
                'intent': 'request_user_data'
            }

            # Ensure connection is up & send message
            self.wait_for_connection('5')
            self.send_message_to_node('5', data)

            # Get user data from Data Center
            self.wait_for_message()
            user_data = self.received_message.get('user_data')

            # Send message
            data = {'intent': 'request_loc_configs'}
            self.send_message_to_node('5', data)

            # Get policy data from Data Center
            self.wait_for_message()
            ta_data_str = self.received_message.get('ta_data')
            ta_data = json.loads(ta_data_str) #convert json string to dict

            #get the trust score for this user_id using the trust algorithm
            user_trust_score = ta.calculate_overall_trust_score(user_data, ta_data)
            print(f"Performing Trust Evaluation for the Subject({user_id})...")
            print(f"Subject({user_id}) Trust Score: {user_trust_score}")
            print(f"Sending the subject's trust score to Policy Engine for policy validation...")

            new_id = user_data.get('new_id')
            user_auth_data = user_data.get('latest_data')
            data = {
                'user_id': user_id,
                'new_id': new_id,
                'user_auth_data': user_auth_data,
                'intent': 'request_access_decision',
                'user_trust_score': user_trust_score
            }

            # Ensure connection is up & send message
            self.wait_for_connection('3')
            self.send_message_to_node('3',data)

            # Clear received message dictionary
            self.del_received_message_item('user_data')
            self.del_received_message_item('ta_data')

    def make_access_decision(self, user_role, user_trust_score, sign_in_risk):
        # Get policy configuration data from data center
        data = {'intent': 'request_threshold_configs'}

        # Ensure connection is up & send message
        self.wait_for_connection('5')
        self.send_message_to_node('5', data)

        # Get policy data from Data Center
        self.wait_for_message()
        configs_str = self.received_message.get('policy_data')
        policy_configs = json.loads(configs_str) #convert json string to dict

        admin_threshold = policy_configs.get('admin_threshold')
        approver_threshold = policy_configs.get('approver_threshold')
        security_viewer_threshold = policy_configs.get('security_viewer_threshold')
        sign_in_risk_threshold = policy_configs.get('sign_in_risk_threshold')

        # Clear received message dictionary
        self.del_received_message_item('policy_data')

        # Initialize verdict
        verdict = 1

        # Determine access decision based on user trust score and role-specific thresholds
        if user_role == 'Approver' and user_trust_score < approver_threshold:
            verdict = 0
        elif user_role == 'Security Viewer' and user_trust_score < security_viewer_threshold:
            verdict = 0
        elif user_role == 'Policy Administrator' and user_trust_score < admin_threshold:
            verdict = 0

        # Determine access decision based on sign-in risk threshold
        if sign_in_risk < sign_in_risk_threshold:
            verdict = 0

        return verdict


    def process_message_from_trust_engine(self, sender, message):
        print(f"\nReceived a message from Trust Engine Node [{sender}]")
        #if this node is a policy engine then check if the message intent is 'request_access_decision'
        if message.get('intent') == 'request_access_decision':
            user_id = message.get('user_id')
            user_trust_score = message.get('user_trust_score')
            print(f"Received a Request for Access Decision from Trust Engine for User {user_id}")
            print(f"Current Subject's Trust Score: {user_trust_score}")
            print(f"Checking against security policies...")

             # Retrieving user_role from user_identity_data
            user_role = message.get('user_role')
            print(f"User Role: {user_role}")

            # Retrieving sign_in_risk from user_auth_data
            user_auth_data = message.get('user_auth_data')
            sign_in_risk = user_auth_data.get('sign_in_risk')
            print(f"Sign In Risk: {sign_in_risk}")

            # Call the access decision script /function here to return the verdict
            verdict = self.make_access_decision(user_role,user_trust_score,sign_in_risk)
            print(f"Policy Engine Verdict: {verdict}")

            # Send access decision to WebUI
            self.wait_for_connection('4')
            self.send_message_to_node('4', {'access_decision': verdict})

             # Prepare the access decision data
            new_id  = message.get('new_id')
            access_decision_data = {
                'ID': new_id,
                'user_id': user_id,
                'intent': 'request_access_decision',
                'user_trust_score': user_trust_score,
                'access_decision': verdict
            }

            # Send access decision to DataCenter to update log
            self.wait_for_connection('5')
            self.send_message_to_node('5', access_decision_data)

    def process_message_from_data_center(self, sender, message):
        print("\nReceived data from Data Center Node")
        self.set_received_message(message)
        self.message_updated.set()

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
        elif self.message_is_from_data_center(sender_id):
            self.process_message_from_data_center(sender_id, message_content)
        else:
            print(f"Received a message from an unknown sender ({sender_id}): {message_content}")
        
    def node_disconnect_with_outbound_node(self, node):
        print(f"\n{self.get_node_role(self.id)} wants to disconnect with {node.id}")   
            
    def node_request_to_stop(self):
        print(f"\nStopping the {self.get_node_role(self.id)} node")
        
