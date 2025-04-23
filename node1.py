import sys

sys.path.insert(0, '..') # Import the files where the modules are located

from Networking import Networking

#Create an instance of this node
node_1 = Networking(Networking.NODE_CONNECT['1'][0], Networking.NODE_CONNECT['1'][1], 1)

#Start the node
node_1.start()

debug = False

node_1.debug =debug

#Connect with node 2
node_1.connect_with_node(Networking.NODE_CONNECT['2'][0], Networking.NODE_CONNECT['2'][1])
node_1.connect_with_node(Networking.NODE_CONNECT['3'][0], Networking.NODE_CONNECT['3'][1])
node_1.connect_with_node(Networking.NODE_CONNECT['4'][0], Networking.NODE_CONNECT['4'][1])

try:
    #Start a loop to keep sending messages between node 1 and node 2
    while(True):

        userInput = input("\nType 'exit' to stop the Access Proxy...")

        if(userInput == 'exit'):
            break

except KeyboardInterrupt:
    print("\nKeyboard interrupt received. Exiting...")

finally:
    node_1.stop()
