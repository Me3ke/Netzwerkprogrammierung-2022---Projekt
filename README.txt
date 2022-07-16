Netzwerk Programmierung - Abschluss Projekt SoSe 2020
                    15.07.2022
                   Maiko Möbius

This application provides an example behavior for server networks.
To stay in sync and prevent the, so called, split-brain-problem, server
need a master assigned that keeps the server data up to date. To ensure
a flawless process the master is elected by a quorum. Every server bases
it's vote on a deterministic property. If the votes make up more than half
of the server altogether, a new master has been found.

This file features some theoretical background of how the program works and
guides the reader through different possibilities that this app features.

The program consists of three folders:
    The test folder where the main functions of the program are tested.
    The source folder (src) which posses the main entry point to create a server.
    The example folder that contains an example of how the servers are going to behave.

Note: This application works on linux operating systems only!

For a default server start-up, move to the src directory and execute the 'Bash.py' file.
Now a promt will appear that will ask for input. You can type in 'help' to view all
possibilities with this program, but mainly you want to start a server.
Upon start the server will try to connect to all servers in the server's list. All
available server on this list will form a network that will then elect a master.
These masters use a client to exchange messages between them. Currently the server
will only accept known messages from other server, but it can easily expanded to
edit messages from 'real' clients as well.
If a master is elected all servers in the network will periodically send a message
to the master to ensure the connection between them. The master however will keep track
all server in the network. If more then half of the listed server fail, the master will
shutdown the network, so that there is no possibility that another network can form itself
to elect a second master. The prompt also includes all shell commands. For more information
check the documententation in 'Bash.py'

The Test directory can be used to see how functions on the server are respoding on different inputs.
To execute all tests, navigate to the Test directory and type in 
"python3 -m unittest Test_Server_outgoing.py && python3 -m unittest Test_Server_incoming.py && python3 -m unittest Test_Client.py"
or all of them seperatly. The tests are splitted as implied in the Server.py file, to make it clearer.

The example file will start three processes with each controlling one server. These will build a network
and the server will be shut down and rebooted in succession to see how the network behaves.
to start the example file move to the Example folder and execute the 'Example.py'. It is
recommended to direct the server's output into a file. Consider the note in the 'Example.py'.

The notes in all files are always useful hints why the program might not work!

The requirements.txt contains all 3rd Party module information.