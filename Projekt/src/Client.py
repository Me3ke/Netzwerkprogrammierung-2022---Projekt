"""
The client class of the application.

A client object is instantiated if a server needs
to communicate with another. This server creates a client
that's only purpose is to send the message to the server.
After that, the connection will be canceled and the client delete.
"""
# -*- coding: utf-8 -*-
import socket

HEADER = 64
FORMAT = 'utf-8'
MAX_LENGTH = 2048

class Client:

    client = None
    addr = None
    calling_server = None

    def __init__(self, calling_server):
        self.calling_server = calling_server
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)

    def connect(self, ip, port):
        """
        Connect with a server of the given IP address and the given port number.

        The socket module is used to establish a connection to the IP address.
        If the connection cannot be established, the method evaluates to 'False'.

        Parameters
        ----------
        ip : str
            The IP address of the server that the client wants to connect to.
        port : int
            The port number of the server that the client wants to connect to.

        Returns
        -------
        bool
            True if the server is available, False otherwise.
        """
        self.addr = (ip, port)
        try:
            self.client.connect(self.addr)
            return True
        except socket.error:
            self.client.close()
            return False

    def send(self, msg):
        """
        Send a message to the connected server.

        To evaluate how many bytes the server has to receive
        the methods send the message length first (The length of
        this is capped by HEADER) and then proceed to send the message.
        It will receive an answer from the server that is returned.

        Parameters
        ----------
        msg : str
            the message to be send

        Returns
        -------
        str
            The answer of the server to the send message.
        """
        message = msg.encode(FORMAT)
        msg_length = len(message)
        send_length = str(msg_length).encode(FORMAT)
        send_length += b' ' * (HEADER - len(send_length))
        self.client.send(send_length)
        self.client.send(message)
        return_message = self.client.recv(MAX_LENGTH).decode(FORMAT)
        self.client.close()
        return return_message

    def close(self):
        # for testing purposes only
        self.client.close()