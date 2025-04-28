from Networking import Networking

#Create an instance of this node
node_5 = Networking(Networking.NODE_CONNECT['5'][0], Networking.NODE_CONNECT['5'][1], 5)

#Start the node
node_5.start()

debug = False
node_5.debug = debug

node_5.connect_with_node(Networking.NODE_CONNECT['1'][0], Networking.NODE_CONNECT['1'][1]) #node 1
node_5.connect_with_node(Networking.NODE_CONNECT['2'][0], Networking.NODE_CONNECT['2'][1]) #node 2
node_5.connect_with_node(Networking.NODE_CONNECT['3'][0], Networking.NODE_CONNECT['3'][1]) #node 3
node_5.connect_with_node(Networking.NODE_CONNECT['4'][0], Networking.NODE_CONNECT['4'][1]) #node 4

try:
    #Start a loop to keep sending messages between node 1 and node 2
    while True :

        userInput = input("\nType 'exit' to stop the Data Center...")

        if userInput == 'exit':
            break

except KeyboardInterrupt:
    print("\nKeyboard interrupt received. Exiting...")

finally:
    node_5.stop()
