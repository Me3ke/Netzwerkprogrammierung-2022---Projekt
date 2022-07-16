"""
Represent the 'main' Class of the application.

The Bash.py is an application that wraps the server application into an
environment, so that the server can run different tasks while performing
background activities to connect with the master server for example.
"""
# -*- coding: utf-8 -*-
import os
import threading
import ipaddress
import subprocess
import Server

NO_IP_SPECIFIED = "no ip specified use help for manual"
NON_VALID_IP = "non valid ip"
WARNING_INVALID_NETWORK = "warning: this operation may cause an invalid network!"
SERVER_HAS_NOT_STARTED = "server has not been started yet or command has not been found"
WRONG_COMMAND = "wrong command usage, use help for manual"
TERMINTATING_SERVER = "stopping server now"
NO_FLAG_SPECIFIED = "no flag specified use help for manual"

server_started = False
server_ip = ""
server = None

def manual():
    """
    Print the application's manual into the console.

    The manual contains all possible commands to manipulate the server.
    Additionally, it provides important information on what to look out for
    dealing with the commands.
    """
    print("This is the manual for the server console application. All commands, their usage and their"
            + " behaviour are listed below.\n"
            + "The application also supports all (unix) bash commands. Try 'ls -a' for example.\n"
            + "Note that the spaces between the commands are important for the internal reading!\n"
            + "\n"
            + "use 'quit' or CTRL+C to terminate the application. A running server will be terminated"
            + " as soon as possible.\n"
            + "\n"
            + "use 'start -ip <server ip>' to start a server on the specified IP.\n"
            + "if the specified IP is invalid, or if the IP is not contained in the server list"
            + " within the server object the server will not start!\n"
            + "\n"
            + "use 'status' to see the current status of the server (online or offline)\n"
            + "\n"
            + "All commands listed below will only work if a server was started beforehand\n"
            + "\n"
            + "use 'shutdown' to shutdown the server as soon as possible. The application is"
            + " still running after this command.\n"
            + "\n"
            + "use 'serverlist -list' to list all server IP's within the server's internal server list\n"
            + "use 'serverlist -append <server ip>' to add a server's IP address into the"
            + " server's internal server list\n"
            + "use 'serverlist -remove <server ip>' to remove a server's IP address from the"
            + " server's internal server list\n"
            + "These will only work if the given IP is valid and different from the server's IP"
            + " that is running on this application\n"
            + "Note that removing or adding a server IP may result in a shutdown of all servers"
            + " within the network to prevent split brain problems!\n"
            + "\n"
            + "use 'master' to print the master server of the network. This will be None"
            + " if there is no master server yet\n"
            + "\n"
            + "use 'network' to print the all IP's that this server is currently connected to."
            + " This maybe empty if the server has not finished its search\n"
            + "\n"
            + "use 'time' to print the time the server came online\n"
            + "\n"
            + "use 'ip' to print the IP of the running server\n"
            + "\n"
            + "use 'help' to see this page again")

def check_ip(ip):
    """
    Check if the IP address is valid.

    The method uses the ipaddress module to verify if the given IP
    leads to a ValueError while initializing the object.

    Parameters
    ----------
    ip : str
        The IP address to be investigated.

    Returns
    -------
    bool
        True if the IP is valid, False otherwise.

    Examples
    --------
    >>> check_ip("127.0.0.7")
    >>> check_ip("123.1.1")
    0   True
    1   False
    """
    try:
        ip_object = ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

def start(command):
    """
    Evaluate the start command and start the server.

    Checks the command line from the input on the required flag '-ip'
    If this is the case the IP is extracted from the input and checked.
    A valid IP address will cause a server object to be instantiated and
    a thread to be created where the server is going to run.
    If the command is not valid, the method will print an error message.

    Parameters
    ----------
    command : list of str
        A list of the input command, that is split between the spaces.

    See Also
    --------
    start_server    : Call the server.start() method to run the server.
    check_ip        : Check if the IP address is valid.
    Server.Server   : Initialize the server.
    """
    global server_started
    global server_ip
    global server

    if not server_started:
        ip = ""
        if len(command) == 1:
            print(NO_IP_SPECIFIED)
        elif len(command) == 3 and command[1] == '-ip':
            ip = command[2]
            if check_ip(ip):
                server_ip = ip
                server_started = True
                server = Server.Server(ip)
                thread = threading.Thread(target=start_server, args=(ip,), name='Server_Main')
                thread.start()
                print("starting server")
            else:
                print(NON_VALID_IP)
        else:
            print(WRONG_COMMAND)
    else:
        print("server has already been started")

def start_server(ip):
    """
    Call the server.start() method to run the server.

    After checking if the valid IP address is contained in the servers
    SERVER_LIST, the server's start method is called to run the server.

    Parameters
    ----------
    ip : str
        The IP address of the server to be started.

    See also
    --------
    Server.start    : Start the server.
    Server.Server   : Initialize the server.
    """
    global server
    global server_started

    if ip in server.get_server_list():
        try:
            server.start()
        except:
            server = None
            server_started = False
    else:
        print("specified IP is not contained in the serverlist. Add it with 'serverlist -append <ip>' and try again.")
        server_started = False

def server_list(command):
    """
    Evaluate the server list command and perform the resulting actions.

    The server_list method evaluates the flags of the command and
    prints what was asked in the command and additionally reports
    if something went wrong or something may cause trouble.

    Parameters
    ----------
    command : list of str
        A list of the input command, that is split between the spaces.

    See also
    --------
    check_ip    : Check if the IP address is valid.
    """
    global server_started
    global server

    if server_started:
        ip = ""
        if len(command) == 1:
            print(NO_FLAG_SPECIFIED)

        elif len(command) == 2 and command[1]=='-list':
            print("listing server list")
            print(server.get_server_list())

        elif len(command) == 3 and command[1]=='-append':
            ip = command[2]
            if check_ip(ip):
                print("adding server " + ip + " to list")
                print(WARNING_INVALID_NETWORK)
                server.add_server_to_list(ip)
            else:
                print(NON_VALID_IP)

        elif len(command) == 3 and command[1]=='-remove':
            ip = command[2]
            if check_ip(ip):
                print("removing server " + ip + " from list")
                print(WARNING_INVALID_NETWORK)
                server.remove_server_from_list(ip)
            else:
                print(NON_VALID_IP)

        else:
            print(WRONG_COMMAND)
    else:
        print(SERVER_HAS_NOT_STARTED)

def main():
    """
    Evaluate commands from the command line.

    Starting a loop with a prompt to read user input.
    This input is analyzed and if needed the corresponding
    methods are called. If the command is not related to the
    server application, the command is passed to the subprocess
    module that executes the bash command, so that all Unix
    shell commands work as well. On Keyboardinterrupt or 'quit'
    command the whole application terminates, killing all server
    threads, etc.

    See also
    --------
    manual      : Print the the application's manual into the console.
    server_list : Evaluate the server list command and perform the resulting actions.
    start       : Call the server.start() method to run the server.
    """
    global server_started
    global server_ip
    global server
    cond = True

    while cond:
        try:
            line = str(input("> Type in any command. Type help for manual \n"))
            os.system("clear")
            command = line.split(' ')
            if server is not None:
                if not server.is_online():
                    server_started = False
                    server = None
            if command[0] == 'help':
                manual()
            elif command[0] == 'debug':
                print(threading.enumerate())
            elif server_started:
                if command[0] == 'quit':
                    print(TERMINTATING_SERVER)
                    server.shutdown()
                    cond = False
                elif command[0] == 'status':
                    print("server online")
                elif command[0] == 'time':
                    print("getting server time online")
                    print(server.get_server_start_time())
                elif command[0] == 'network':
                    print("getting server network")
                    print(server.get_network())
                elif command[0] == 'master':
                    print("getting server master")
                    print(server.get_master())
                elif command[0] == 'shutdown':
                    print(TERMINTATING_SERVER)
                    server.shutdown()
                    server_started = False
                elif command[0] == 'ip':
                    print("server is running on " + server_ip)
                elif command[0] == 'serverlist':
                    server_list(command)
                elif command[0] == 'start':
                    start(command)
                else:
                    try:
                        subprocess.run(command, check = True)
                    except:
                        print("Invalid Command")

            else:
                if command[0] == 'quit':
                    cond = False
                elif command[0] == 'serverlist':
                    server_list(command)
                elif command[0] == 'start':
                    start(command)
                else:
                    try:
                        subprocess.run(command, check = True)
                    except:
                        print(SERVER_HAS_NOT_STARTED)

        except KeyboardInterrupt:
            if server_started:
                print(TERMINTATING_SERVER)
                server.shutdown()
                cond = False
            else:
                cond = False
        except Exception as err:
            print(err)

if __name__ == "__main__":
    main()
