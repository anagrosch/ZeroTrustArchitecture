import sys

sys.path.insert(0, '..') # Import the files where the modules are located

from Networking import Networking

#Create an instance of this node
node_2 = Networking(Networking.NODE_CONNECT['2'][0], Networking.NODE_CONNECT['2'][1], 2)

#Start the node2
node_2.start()

debug = False

node_2.debug = debug

#Connect with node 1
node_2.connect_with_node(Networking.NODE_CONNECT['3'][0], Networking.NODE_CONNECT['3'][1]) #node 3
node_2.connect_with_node(Networking.NODE_CONNECT['1'][0], Networking.NODE_CONNECT['1'][0]) #node 1

while(True):

    userInput = input("\nType 'exit' to end the Trust engine...")

    if(userInput == 'exit'):
        break

node_2.stop()
