from Networking import Networking

#Create an instance of this node
node_3 = Networking(Networking.NODE_CONNECT['3'][0], Networking.NODE_CONNECT['3'][1], 3)

#Start the node
node_3.start()

debug = False
node_3.debug = debug

node_3.connect_with_node(Networking.NODE_CONNECT['1'][0], Networking.NODE_CONNECT['1'][1]) #node 1
node_3.connect_with_node(Networking.NODE_CONNECT['2'][0], Networking.NODE_CONNECT['2'][1]) #node 2
node_3.connect_with_node(Networking.NODE_CONNECT['4'][0], Networking.NODE_CONNECT['4'][1]) #node 4
node_3.connect_with_node(Networking.NODE_CONNECT['5'][0], Networking.NODE_CONNECT['5'][1]) #node 4

#Start a loop to keep sending messages between node 1 and node 2
while True:

    userInput = input("\nType 'exit' to stop the policy engine")

    if userInput == 'exit':
        break

node_3.stop()
