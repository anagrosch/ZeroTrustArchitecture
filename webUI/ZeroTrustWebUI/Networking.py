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
        self.expected_node_id = None # expected connection node id
        self.connected_to_node = threading.Event()

        print(f"\n{self.get_node_role(self.id)} STARTED on {self.host}:{self.port}")
    
    #Define a function to extract the name of a node based on it's node.id attribute
    def get_node_role(self,node_id):
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

        for node in self.all_nodes:
            if node.id == node_id:
                target_node = node
                #convert the message to a json object
                json_message = {
                    "senderID": self.id,
                    "messageContent":message
                }
                # Reconnect to node (if needed)
                self.wait_for_connection(node_id)

                # Send the message to the specific node
                self.send_to_node(target_node, json_message)
                print("Message sent to node:", node_id)
                break
        if target_node is None:
            print(f"Node {node_id} not found in inbound or outbound connections.")

    def message_is_from_policy_engine(self, sender_id):
        return sender_id == '3'

    def message_is_from_data_center(self, sender_id):
        return sender_id == '5'

    def process_message_from_policy_engine(self, sender, message):
        print("\nReceived a message from Policy Engine Node")
        self.set_received_message(message)
        self.message_updated.set()

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

    def inbound_node_disconnected(self, node):
        print(f"\n{self.get_node_role(node.id)} DISCONNECTED from {self.get_node_role(self.id)}")

    def outbound_node_disconnected(self, node):
        print(f"\n{self.get_node_role(self.id)} DISCONNECTED from {self.get_node_role(node.id)}")

    def node_message(self, node, data):
        sender_id = node.id  # Get the sender's ID
        message_content = data  # Get the message content

        if "senderID" in message_content:
            message_content = message_content["messageContent"]
            #extract other future message attributes like unique hash, and message intent

        # Process the message based on the sender's ID
        if self.message_is_from_policy_engine(sender_id):
            self.process_message_from_policy_engine(sender_id, message_content)
        elif self.message_is_from_data_center(sender_id):
            self.process_message_from_data_center(sender_id, message_content)
        else:
            print(f"Received a message from an unknown sender ({sender_id}): {message_content}")
        
    def node_disconnect_with_outbound_node(self, node):
        print(f"\n{self.get_node_role(self.id)} wants to disconnect with {node.id}")   
            
    def node_request_to_stop(self):
        print(f"\nStopping the {self.get_node_role(self.id)} node")
        
