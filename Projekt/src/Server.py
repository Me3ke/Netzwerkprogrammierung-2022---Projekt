"""
The server class of the application

A server is the main part of the application.
It is supposed to be run in a network of several servers.
In this environment, the network forms a quorum in which a
master server is determined. After that every non-master
server keeps in touch with the corresponding master.
"""
# -*- coding: utf-8 -*-
import socket
import subprocess
import threading
import time
import logging
import select
import os
import datetime
import operator
import Client

HEADER = 64
DEFAULT_SERVER_LIST = ["127.0.0.7", "127.0.0.8", "127.0.0.9"]
FORMAT = 'utf-8'

DISCONNECT_MESSAGE = "!DISCONNECT"
ASK_MASTER_MESSAGE = "Your master?"
SHUTDOWN_MESSAGE = "!SHUTDOWN"
VOTE_MASTER_MESSAGE = "vote = "
MASTER_CONFIRMED_MESSAGE = "The master has been confirmed"
MASTER_DECLINED_MESSAGE = "The master has been declined"
PING_MESSAGE = "ip = "
SERVER_SHUTDOWN_EXCEPTION = "Server Shutdown"

MAXIMUM_NETWORK_ATTEMPTS = 3
MASTER_VOTE_TIMEOUT = 20
INITIAL_NETWORK_SEARCH_TIMEOUT = 10
SEND_PING_TIME = 6
WAIT_PING_TIME = 15

logging.basicConfig(
    #filename='../Example/server.log', filemode='w',
    format='%(threadName)s:%(message)s',
    level=logging.DEBUG,
)

class Server:
    """
    Note:
    A valid network is specified to contain more servers than half of the servers altogether.
    This is because a smaller network can lead to two separate networks with two master servers.
    This will cause inconsistencies all over the place and should be avoided.
    The entirety of servers is stated in the server list that can be manipulated in the console
    (-> Bash.py).
    """

    ip = ""
    port = 0
    server = None
    master_server = None
    ping_lock = None
    server_start_time = 0
    server_online = False
    network_attempts = 0
    votes = []
    network = []
    requests = []
    network_masters = {}
    ping_targets = {}
    server_list = []

    def __init__(self, ip):
        self.server_start_time = datetime.datetime.now()
        self.server_online = True
        uid = subprocess.check_output(['id','-u']).decode(FORMAT).strip()
        self.port = 20000 + (int(uid) - 1000) * 50
        self.ip = ip
        self.r_channel, self.w_channel = os.pipe()
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        self.ping_lock = threading.Lock()
        self.server_list = list(DEFAULT_SERVER_LIST)
        self.server.bind((self.ip, self.port))

    ####################################### Handle incoming connections ################################################

    def start(self):
        """
        Start the server on the given IP and start listening for connections.

        The socket module is used to run a server instance that accepts
        incoming connections and passes them onto threads that handle further actions.
        The method also checks the application's pipe for shutdown commands to decide
        when to shut down the listening.
        In the beginning, another thread is created that determines all available
        servers in the network.

        See also
        --------
        handle_client   : Handle the connection to send and receive messages from a client connection.
        find_network    : Find a network of available servers in the given environment.
        """
        self.server.listen(socket.SOMAXCONN)
        self.server.setblocking(0)
        logging.debug("Server is listening on %s", self.ip)
        find_network_thread = threading.Thread(target=self.find_network, name='Find_Network')
        find_network_thread.start()

        while True:
            try:
                rfds = select.select([self.server.fileno(), self.r_channel],[],[])
                # blocks until either a connection is requested or a shutdown command is written into the pipe
                if self.r_channel in rfds[0]:
                    raise Exception(SERVER_SHUTDOWN_EXCEPTION)
                conn, addr = self.server.accept()
            except KeyboardInterrupt:
                logging.debug("\n server accept has been interrupted by KeyBoardInterrupt")
                # use pipe to terminate all other running threads
                self.shutdown()
                break
            except Exception as err:
                logging.debug(err)
                logging.debug("server accept has been interrupted")
                break
            thread = threading.Thread(target=self.handle_client, args=(conn, addr))
            thread.start()

        self.server.close()
        logging.debug("Server is shutting down")
        #logging.debug(threading.enumerate())

    def handle_client(self, conn, addr):
        """
        Handle the connection to send and recieve messages from a client connection.

        If a connection has been established this method interrogates the message that
        was sent. The first incoming message is always the length of the next message
        with a length of 'HEADER', as mentioned in the Client class. For every received
        message the associated action is performed. As the current connections are only
        from other servers, the connection is canceled after receiving the message.
        In the future, this method may be extended for connections from non-server-client
        instances.

        Parameters
        ----------
        conn : socket object
            usable to send and receive data on the connection.
        addr : tuple of str and int
            the address bound to the socket on the other end of the connection.

        See also
        --------
        Client.send     : Send a message to the connected server.
        handle_ping     : Handle a ping message if the server is the master of the network.
        handle_votes    : Handle a master vote of another server.
        """
        connected = True
        while connected:
            msg_length = conn.recv(HEADER).decode(FORMAT)
            if msg_length:
                msg_length = int(msg_length)
                msg = conn.recv(msg_length).decode(FORMAT)
                if msg == DISCONNECT_MESSAGE:
                    connected = False
                    conn.send("Disconnect received".encode(FORMAT))
                elif msg == ASK_MASTER_MESSAGE:
                    # the requestant is part of the network
                    self.requests.append(addr[0])
                    conn.send(str(self.master_server).encode(FORMAT))
                    connected = False
                elif PING_MESSAGE in str(msg):
                    self.handle_ping(str(msg[5:]), conn)
                    # msg[5:] is the ip address of the requesting server
                    connected = False
                elif VOTE_MASTER_MESSAGE in str(msg):
                    self.handle_votes(str(msg[7:]), conn)
                    # msg[7:] is the ip address of the requesting server
                    connected = False
                else:
                    conn.send("recieved something".encode(FORMAT))
                    connected = False
        conn.close()

    def handle_ping(self, ip, conn):
        """
        Handle a ping message if the server is the master of the network.

        If a server pings to the master, the IP address of the requesting server
        in the ping_target dictionary is set to 1. Because there may be two or more
        threads writing in the dictionary, a lock is required.

        Parameters
        ----------
        conn : socket object
            usable to send and receive data on the connection.
        ip : str
            the IP address of the server that sent the ping message.
        """
        self.ping_lock.acquire()
        self.ping_targets[ip] = 1
        #logging.debug(self.ping_targets)
        self.ping_lock.release()
        conn.send("Ping received".encode(FORMAT))

    def handle_votes(self, ip, conn):
        """
        Handle a master vote of another server.

        This method is called if another server votes this server as master.
        If this vote is the first one this thread will wait for other votes
        in a given time (-> Vote_Check). When enough servers have voted this server as master
        the server is elected master of the network. If this vote is not the first
        one, the thread will wait until the 'Vote_Check' thread has finished and will
        respect the outcome. This works because the 'Vote_Check' thread will terminate
        either through enough votes or because of a timeout (-> MASTER_VOTE_TIMEOUT).
        After a positive outcome of the quorum (a valid master has been elected)
        a new thread is started that will check if the other server in the network
        are online (-> ping_check).

        Parameters
        ----------
        conn : socket object
            usable to send and recieve data on the connection.
        ip : str
            the IP address of the server that sent the ping message.

        See also
        --------
        ping_check      : Check consistently if enough servers in the network are online.
        """
        self.votes.append(ip)
        vote_check_thread = None
        threads = threading.enumerate()
        for t in threads:
            if t.name == 'Vote_Check' and t.is_alive():
                vote_check_thread = t
        if vote_check_thread:
            # if a vote check thread is present, wait until it is finished.
            vote_check_thread.join()
        else:
            #logging.debug("no checker thread active so i will be new one")
            threading.current_thread().name = 'Vote_Check'
            start_time = time.time()
            while int(len(self.votes)) < int(len(self.network)):
                time.sleep(1)
                # wait till everyone has voted or timeout
                if time.time() >=  start_time + MASTER_VOTE_TIMEOUT:
                    break
                # eliminate dublicates in vote list
                self.votes = list(self.eliminate_dublicates(self.votes))

            self.votes = list(self.eliminate_dublicates(self.votes))
            #logging.debug(self.votes)

        if int(len(self.votes)) >= (int(len(self.server_list) / 2) + 1):
            # this check prevents split brain problems
            logging.debug("Master eval successful. Sending info to server now")
            conn.send(MASTER_CONFIRMED_MESSAGE.encode(FORMAT))
            self.master_server = self.ip
            if threading.current_thread().name == 'Vote_Check':
            # Vote_Check thread will be the new Ping_Check thread
                for server in self.network:
                    self.ping_targets[server] = 1
                thread = threading.Thread(target=self.ping_check, args = (), name='Ping_Check')
                thread.start()
        else:
            conn.send(MASTER_DECLINED_MESSAGE.encode(FORMAT))
            logging.debug("Master eval failed. Shutting down server")
            self.shutdown()

    def ping_check(self):
        """
        Check consistently if enough servers in the network are online.

        A ping check thread is set up if the network has elected a master. To
        continuously check, if the network is valid at any given time the method
        uses a dictionary. Initially, all server IP addresses of the network will
        be mapped to '1'. After a specified timeout (-> WAIT_PING_TIME) all values
        in the dictionary will be set to '0'. Now every server has time until the
        next timeout to set its value in the array back to '1'. When a timeout happens
        and a certain amount of servers have not yet responded we assume that these servers
        are offline and therefore the server calculates if the network is still valid.
        This is the case if more than half of the listed servers are online.
        Otherwise, the server will shut down itself. And this will cause the remaining
        servers to shut down aswell; the network has to be restarted.

        See also
        --------
        handle_ping     : Handle a ping message if the server is the master of the network.
        """
        while self.server_online:
            rfds = select.select([self.r_channel], [], [], WAIT_PING_TIME)
            # blocks until the wait ping time expired or a shutdown command is written into the pipe
            if self.r_channel in rfds[0]:
                logging.debug("canceling ping check due to shutdown")
                self.server_online = False
                break
            self.ping_lock.acquire()

            if list(self.ping_targets.values()).count(1) < (int(len(self.server_list) / 2) + 1):
                logging.debug("invalid network, shutting down")
                self.shutdown()
            else:
                for ping_target in self.ping_targets.keys():
                    if ping_target not in self.network:
                        self.network.append(ping_target)
                    self.ping_targets[ping_target] = 0
                self.ping_targets[self.ip] = 1
                #logging.debug(self.ping_targets)
            self.ping_lock.release()

    ####################################### Handle outgoing connections ################################################

    def find_network(self):
        """
        Find a network of available servers in the given environment.

        The environment is restricted by the server list (-> SERVER_LIST).
        It can be manipulated in the console application (-> Bash.py).
        The find_network method is initialized upon starting the server. The
        initial timeout (INITIAL_NETWORK_SEARCH_TIMEOUT) is necessary for the
        user so that all servers can be started at the same time and a network
        can be built immediately.
        After that, the network tries to connect to all servers in the server list
        to determine the network (-> client_thread). Then the method checks if
        this network is a valid one (more than half of the listed servers).
        If this is not the case it will retry up to 3 times (-> MAXIMUM_NETWORK_ATTEMPTS).
        Otherwise, it will check for active masters in the network
        (-> check_network_masters) and will join the active master
        or create its own quorum to elect a new master server (-> calc_master).

        See also
        --------
        Bash.serverlist         : Evaluate the serverlist command and perform the resulting actions.
        client_thread           : Check if the named server is accessible.
        check_network_masters   : Check if there is an active master in the given network.
        calc_master             : Determine the master in the current network.

        Notes
        -----
        The delay to start the client_thread method is important to prevent race conditions.
        Unfortunately the threading.Condition() does not eradicate these. If you catch the
        find_network method and its client_threads being stuck, increasing the delay may
        solve the error.
        """
        time.sleep(INITIAL_NETWORK_SEARCH_TIMEOUT)
        self.network = list(self.server_list)
        self.network_masters = {}
        cond = threading.Condition()
        cond.acquire()
        thread_count = 0
        network_list = self.network
        if self.server_online:
            # check which servers are accessible
            for sip in network_list:
                if sip != self.ip:
                    delay = float(thread_count) / 10 * 2 # handle with care
                    t = threading.Thread(target=self.client_thread, args=(cond, sip, delay))
                    t.start()
                    thread_count += 1
                else:
                    self.network_masters[sip] = str(self.master_server)
            while thread_count > 0:
                cond.wait()
                thread_count -= 1
            cond.release()
            #logging.debug(self.network)

            if len(self.network) < (int(len(self.server_list)/2) + 1):
                # not enough servers in the network, try find_network again
                logging.debug("insufficient server in network, restarting find_network")
                self.retry_find_network()
            else:
                #logging.debug(self.network_masters)
                logging.debug("checking if there is an active master in the network")
                active_master = self.check_network_masters()

                if active_master:
                    # if there is a valid active master in the network the server will join the network
                    if active_master in self.network:
                        self.master_server = active_master
                        self.ping()
                    else:
                        logging.debug("Could not connect to the active master of the network, restarting find_network")
                        self.retry_find_network()
                else:
                    # if there is no valid master in the network, the server assumes that the other servers are
                    # also looking for a network and waits until everyone has found another to ensure stability.
                    start_time = time.time()
                    network_invalid = False
                    logging.debug("waiting for all servers to finish network config")

                    while int(len(self.requests)) < int((len(self.network) - 1)):
                        #logging.debug(self.requests)
                        if time.time() >=  start_time + MASTER_VOTE_TIMEOUT:
                            network_invalid = True
                            break
                        time.sleep(5)

                    if not network_invalid:
                        logging.debug("no valid masters found in network, new master will be calculated now")
                        self.calc_master()
                    else:
                        logging.debug("the given network is not valid, because some servers did not respond in time, restarting find_network")
                        self.retry_find_network()

    def client_thread(self, cond, sip, delay):
        """
        Check if the named server is accessible.

        After waiting for the delay (See -> find_network, Notes) the
        method instantiates a client that connects to a server
        specified by the IP. If the connection fails the server IP
        is removed from the network, which is initially the same as the
        server list (-> SERVER_LIST). Otherwise, the method will
        ask the server for its master and will transfer the information
        into a dictionary (-> network_masters).
        To prevent inconsistencies in the parallel running threads,
        threading.condition() is used as a synchronizing mechanism (lock).

        Parameters
        ----------
        cond  : condition object
            a synchronizing mechanism to prevent inconsistencies in the threads.
        sip   : str
            the IP the created client tries to connect to.
        delay : float
            initial start delay of the thread.

        See also
        --------
        Client          : The client class of the application.
        """
        time.sleep(delay)
        c = Client.Client(self.ip)
        if not c.connect(sip, self.port):
            cond.acquire()
            self.network.remove(sip)
            logging.debug("%s server not found.", sip)
            cond.notify()
            cond.release()
        else:
            master_of_sip = str(c.send(ASK_MASTER_MESSAGE))
            cond.acquire()
            self.network_masters[sip] = master_of_sip
            logging.debug("%s server is available.", sip)
            cond.notify()
            cond.release()

    def check_network_masters(self):
        """
        Check if there is an active master in the given network.

        When a network is established the network masters dictionary
        is filled with the server IP's of the network and their
        corresponding masters. If enough servers of this network
        have a certain master, it is an active master in the network
        and this server can join the network and accept this master
        without another election. This method will determine that.

        Return
        ------
        str
            The IP address of the active master server or 'None'.

        See also
        --------
        find_network    : Find a network of available servers in the given environment.
        """
        master_of_network = None
        masters = self.network_masters.values()
        network_size = len(self.network_masters)
        if operator.countOf(masters, "None") <= int(network_size / 2) :
            for master in masters:
                if master != "None":
                    if operator.countOf(masters, master) > int(network_size / 2):
                        master_of_network = master
        if master_of_network is not None:
            logging.debug('%s is valid master of network', master_of_network)
        return master_of_network

    def calc_master(self):
        """
        Determine the master in the current network.

        The method takes the maximum of the network's IP addresses
        and votes this server as master. Therefore the master will
        be elected unanimously in most use cases.
        To confirm the master, the method will create a client object
        to connect with the master and send a vote message. Only if
        the server gains the majority of votes regarding the
        server list (not the network!) and is accessible, the master
        will be confirmed. After that, a ping connection will be
        established with the master (-> ping).
        In some cases, the server might not get any votes, except for his own.
        This will lead to a server shutdown. If the server is not reachable
        the find_network method will be restarted.

        See also
        --------
        ping            : Validate the connection to the master server throughout the lifetime of the server.
        find_network    : Find a network of available servers in the given environment.
        Client          : The client class of the application.
        """
        master_candidate = max(self.network)
        if master_candidate == self.ip:
            self.votes.append(self.ip)
            rfds = select.select([self.r_channel], [], [], MASTER_VOTE_TIMEOUT)
            # blocks until the master vote time expires or a shutdown command is written into the pipe
            if self.r_channel in rfds[0]:
                logging.debug("server shutdown")
            elif len(self.votes) < 2:
                # if there are more than one vote, a vote check thread will continue the sequence
                self.shutdown()
        else:
            c = Client.Client(self.ip)
            if not c.connect(master_candidate, self.port):
                logging.debug("master candidate is not available anymore, removing network and retry")
                self.requests = []
                self.find_network()
            else:
                message = VOTE_MASTER_MESSAGE + self.ip
                answer = str(c.send(message))
                if answer == MASTER_CONFIRMED_MESSAGE:
                    self.master_server = master_candidate
                    logging.debug("the new master of the network is: %s keeping ping connection", self.master_server)
                    self.ping()
                elif answer == MASTER_DECLINED_MESSAGE:
                    logging.debug("master candidate vote failed. finding new network now")
                    self.requests = []
                    self.find_network()
                else:
                    # should not occur
                    logging.debug(answer)
                    raise Exception("unknown answer")

    def ping(self):
        """
        Validate the connection to the master server throughout the lifetime of the server.

        If the ping method is started, the server network has a valid master and the
        method will last until the server is shut down or the network becomes invalid.
        (Too less servers or master is not accessible).
        It uses a client to periodically connect to the server and confirm the
        reachability of this server to the master and the other way around by
        sending a message containing its IP address.

        See also
        --------
        ping_check      : Check consistently if enough servers in the network are online.
        handle_ping     : Handle a ping message if the server is the master of the network.
        Client          : The client class of the application.
        """
        shutdown = False
        while True:
            try:
                rfds = select.select([self.r_channel], [], [], SEND_PING_TIME)
                # blocks until the send ping time expires or a shutdown command is written into the pipe
                if self.r_channel in rfds[0]:
                    shutdown = True
                    raise Exception(SERVER_SHUTDOWN_EXCEPTION)
                c = Client.Client(self.ip)
                if not c.connect(self.master_server, self.port):
                    raise Exception("Lost connection to master server")
                message = PING_MESSAGE + self.ip
                answer = c.send(message)
                logging.debug(answer)#TODO

            except Exception as err:
                logging.debug(err)
                break

        if not shutdown:
            # master server is not accessible
            logging.debug("starting find network again")
            self.network_attempts = 0
            self.master_server = None
            self.requests = []
            self.find_network()
        else:
            logging.debug("stopped ping connection due to server shutdown")

    ####################################### Getter, setter and miscellaneous ################################################

    def eliminate_dublicates(self, my_list):
        eliminated_dublicates = []
        for element in my_list:
            if element not in eliminated_dublicates:
                eliminated_dublicates.append(element)
        return eliminated_dublicates
    
    def retry_find_network(self):
        self.network_attempts += 1
        if self.network_attempts == MAXIMUM_NETWORK_ATTEMPTS:
            logging.debug("Maximum number of find_network attempts exceeded, shutting down")
            self.shutdown()
        else:
            self.requests = []
            self.find_network()

    def shutdown(self):
        os.write(self.w_channel, str.encode('!'))
        self.server_online = False
        self.master_server = None
        logging.debug(datetime.datetime.now())

    def restart(self):
        self.server_start_time = datetime.datetime.now()
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        self.server_online = True
        self.ping_lock = threading.Lock()
        self.r_channel, self.w_channel = os.pipe()
        self.server_list = list(DEFAULT_SERVER_LIST)
        master_server = None
        network_attempts = 0
        votes = []
        network = []
        requests = []
        network_masters = {}
        ping_targets = {}
        try:
            self.start()
        except socket.error:
            self.server_online = False

    def get_server_list(self):
        return self.server_list

    def get_network(self):
        return self.network

    def get_master(self):
        return self.master_server

    def get_server_start_time(self):
        return self.server_start_time

    def add_server_to_list(self, ip):
        self.server_list.append(ip)

    def remove_server_from_list(self, ip):
        self.server_list.remove(ip)

    def is_online(self):
        return self.server_online

    def close(self):
        # for testing purposes only
        self.server.close()
