import unittest
from unittest import mock
import socket
import sys
sys.path.insert(1, '../src')
import Client

FORMAT = 'UTF-8'
ASK_MASTER_MESSAGE = "Your master?"
PORT = 26450

@mock.patch('socket.socket.connect')
class Test_connect(unittest.TestCase):

    c = None

    def setUp(self):
        self.c = Client.Client("127.0.0.9")

    def tearDown(self):
        self.c.close()
        del self.c

    def test_default(self, mock_connect):
        mock_connect.return_value = True
        result = self.c.connect("127.0.0.7", PORT)
        self.assertTrue(result)

    def test_target_not_available(self, mock_connect):
        mock_connect.side_effect=socket.error
        result = self.c.connect("127.0.0.7", PORT)
        self.assertFalse(result)

class Test_send(unittest.TestCase):

    @mock.patch('socket.socket', autospec=True)
    def test_send_ask_master(self, mock_socket):
        mock_instance = mock_socket.return_value
        mock_instance.recv.return_value = "127.0.0.7".encode(encoding = FORMAT)
        mock_instance.connect.return_value = True
        c = Client.Client("127.0.0.9")
        result = c.connect("127.0.0.7", PORT)
        result = c.send(ASK_MASTER_MESSAGE)
        self.assertEqual(result, "127.0.0.7")
