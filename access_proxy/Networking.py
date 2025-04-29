'''

Class that extends the p2pnetwork class to add application specific implementation details.
Handles how communication happens between the access proxy, trust engine, policy engine, and data center.
Uses peer to peer communication without involvement of a centralized server for establishing connections.

'''
import threading
from p2pnetwork.node import Node

class Networking(Node):
    # Define a dictionary of the node roles based on their node.id attributes
    NODE_ROLE = {
        '1': 'Access Proxy Node',
        '2': 'Policy Decision Point Node',
        '3': 'Data Center Node',
        '4': 'Web UI'
    }

    # Define a dictionary of the node [host, port] based on their node.id attributes
    NODE_CONNECT = {
        '1': ['127.0.0.1', 8001],
        '2': ['127.0.0.1', 8002],
        '3': ['127.0.0.1', 8003],
        '4': ['127.0.0.1', 8004]
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

    # Send message to selected node
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
                self.wait_for_connection(node_id)
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

    # Notify node of disconnect and reconnect
    def send_disconnect_notice(self, node):
        self.wait_for_connection(node.id) #reconnect with node
        self.send_message_to_node(node.id, {'disconnect': True})

    def message_is_from_policy_decision_point(self, sender_id):
        return sender_id == '2'

    def message_is_from_web_ui(self, sender_id):
        return sender_id == '4'

    def process_message_from_web_ui(self, sender, message):
        # Check if the 'intent' key has the value 'Access Request'
        if message.get('intent', '').lower() == 'access request':
            print(f"\nReceived an Access Request from Web UI [{sender}]")

            # Prepare data to send to Trust Engine (node 2)
            user_id = message.get('user_id')
            intent = 'request_trust_score'

            data = {
                'user_id': user_id,
                'intent': intent
            }

            # Request trust score from Policy Decision Point (node 2)
            self.send_message_to_node('2', data)

            # Forward message to Data Center (node 3) to add request to JSON file
            self.send_message_to_node('3', message)

        # Store Keycloak events to events.json
        elif message.get('intent') == 'store_keycloak_events':
            print(f"\nReceived a Data Request from Web UI [{sender}]: {message.get('intent')}")

            # Prepare data to send to Data Center (node 3)
            events = message.get('cleaned_data')
            intent = message.get('intent')

            data = {
                'events': events,
                'intent': intent
            }
            self.send_message_to_node('3', data)

        # Update user data JSON file
        elif message.get('intent') == 'update_users':
            print(f"\nReceived a Data Request from Web UI [{sender}]: {message.get('intent')}")

            # Prepare data to send to Data Center (node 3)
            extracted_data = message.get('extracted_data')

            data = {
                'extracted_data': extracted_data,
                'intent': 'update_user_roles'
            }
            self.send_message_to_node('3', data)

        # Send access requests log to WebUI
        elif message.get('intent') == 'request_access_requests':
            print(f"\nReceived a Data Request from Web UI [{sender}]: {message.get('intent')}")
            self.send_message_to_node('3', message)

        # Update policy configurations YAML in Data Center
        elif message.get('intent') == 'update_policy_configs':
            print(f"\nReceived a Data Request from Web UI [{sender}]: {message.get('intent')}")
            self.send_message_to_node('3', message)

        else:
            print("The intent is not 'Access Request'/valid request")

    def process_message_from_policy_decision_point(self, sender, message):
        # Forward data from PDP to WebUI
        print(f"\nReceived a data from Policy Decision Point [{sender}]")
        self.send_message_to_node('4', message)

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
        if node.id == '4':
            self.send_disconnect_notice(node)

    def inbound_node_disconnected(self, node):
        print(f"\n{self.get_node_role(node.id)} DISCONNECTED from {self.get_node_role(self.id)}")
        if node.id == '4':
            self.send_disconnect_notice(node)

    def node_message(self, node, data):
        sender_id = node.id  # Get the sender's ID
        message_content = data  # Get the message content

        if "senderID" in message_content:
            message_content = message_content["messageContent"]
            #extract other future message attributes like unique hash, and message intent

        # Process the message based on the sender's ID
        if self.message_is_from_policy_decision_point(sender_id):
            self.process_message_from_policy_decision_point(sender_id, message_content)
        elif self.message_is_from_web_ui(sender_id):
            self.process_message_from_web_ui(sender_id, message_content)
        else:
            print(f"Received a message from an unknown sender ({sender_id}): {message_content}")
        
    def node_disconnect_with_outbound_node(self, node):
        print(f"\n{self.get_node_role(self.id)} wants to disconnect with {node.id}")   
            
    def node_request_to_stop(self):
        print(f"\nStopping the {self.get_node_role(self.id)} node")
        
