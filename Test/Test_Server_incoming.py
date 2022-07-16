import unittest
from unittest import mock
import time
import logging
import threading
import sys
sys.path.insert(1, '../src')
import Server

FORMAT = 'UTF-8'
HEADER = 64

ASK_MASTER_MESSAGE = "Your master?"
VOTE_MASTER_MESSAGE = "vote = "

WAIT_PING_TIME = 15

DEFAULT_SERVER_LIST = ["127.0.0.7", "127.0.0.8", "127.0.0.9"]
PAUSE = 1
LONG_PAUSE = 2

logging.basicConfig(
    format='%(threadName)s:%(message)s',
    level=logging.DEBUG,
)

"""
Note:
The test will take some time, because the connection has to be
based on different timings to ensure connections with delays.
To reduce the time the test need to evaluate, you may want to
decrease the timeouts here and in the 'Server.py'.
(For example: MASTER_VOTE_TIMEOUT : 30 -> MASTER_VOTE_TIMEOUT : 10)
But remember to postpone!
"""

@mock.patch('socket.socket', autospec=True)
class Test_handle_client(unittest.TestCase):

    s = None

    def setUp(self):
        self.s = Server.Server("127.0.0.9")

    def tearDown(self):
        self.s.close()
        del self.s


    def test_ask_master_message(self, mock_socket):
        # copied from Client.py to reproduce the message format
        message = ASK_MASTER_MESSAGE.encode(FORMAT)
        msg_length = len(message)
        send_length = str(msg_length).encode(FORMAT)
        send_length += b' ' * (HEADER - len(send_length))
        mock_socket.recv.side_effect = [send_length, message]

        self.s.handle_client(mock_socket, ("127.0.0.7", 26450))
        self.assertEqual(self.s.requests, ["127.0.0.7"])

    def test_ping_message(self, mock_socket):
        # copied from Client.py to reproduce the message format
        message = "ip = 127.0.0.7".encode(FORMAT)
        msg_length = len(message)
        send_length = str(msg_length).encode(FORMAT)
        send_length += b' ' * (HEADER - len(send_length))
        mock_socket.recv.side_effect = [send_length, message]

        self.s.handle_client(mock_socket, ("127.0.0.7", 26450))
        self.assertEqual(self.s.ping_targets, {"127.0.0.7" : 1})

    @mock.patch.object(Server.Server, "handle_votes")
    def test_vote_master_message(self, mock_votes, mock_socket):
        # copied from Client.py to reproduce the message format
        message = VOTE_MASTER_MESSAGE.encode(FORMAT)
        msg_length = len(message)
        send_length = str(msg_length).encode(FORMAT)
        send_length += b' ' * (HEADER - len(send_length))
        mock_socket.recv.side_effect = [send_length, message]

        self.s.handle_client(mock_socket, ("127.0.0.7", 26450))
        mock_votes.assert_called()

@mock.patch('socket.socket', autospec=True)
class Test_handle_votes(unittest.TestCase):

    s = None

    def setUp(self):
        self.s= Server.Server("127.0.0.9")
        self.s.server_list = list(DEFAULT_SERVER_LIST)
        self.s.network = ["127.0.0.9", "127.0.0.8", "127.0.0.7"]
        self.s.votes = []
        self.s.master_server = None

    def tearDown(self):
        self.s.close()
        del self.s

    def test_one_vote_out_of_three(self, mock_socket):
        thread = threading.Thread(target=self.s.handle_votes, args = ("127.0.0.9", mock_socket))
        thread.start()
        thread.join()

        self.assertIsNone(self.s.master_server)

    def test_two_votes_out_of_five(self, mock_socket):
        self.s.add_server_to_list("127.0.0.6")
        self.s.add_server_to_list("127.0.0.5")
        self.s.network = ["127.0.0.9", "127.0.0.8", "127.0.0.7", "127.0.0.6", "127.0.0.5"]

        thread = threading.Thread(target=self.s.handle_votes, args = ("127.0.0.9", mock_socket))
        thread.start()
        time.sleep(PAUSE)
        threading.Thread(target=self.s.handle_votes, args = ("127.0.0.7", mock_socket)).start()
        thread.join()

        self.assertIsNone(self.s.master_server)

    @mock.patch.object(Server.Server, "ping_check")
    def test_three_votes_out_of_five(self, mock_ping, mock_socket):
        self.s.add_server_to_list("127.0.0.6")
        self.s.add_server_to_list("127.0.0.5")
        self.s.network = ["127.0.0.9", "127.0.0.8", "127.0.0.7", "127.0.0.6", "127.0.0.5"]

        thread = threading.Thread(target=self.s.handle_votes, args = ("127.0.0.9", mock_socket))
        thread.start()
        time.sleep(PAUSE)
        threading.Thread(target=self.s.handle_votes, args = ("127.0.0.7", mock_socket)).start()
        time.sleep(PAUSE)
        threading.Thread(target=self.s.handle_votes, args = ("127.0.0.8", mock_socket)).start()
        thread.join()
        logging.debug(self.s.master_server)
        self.assertIsNotNone(self.s.master_server)
        mock_ping.assert_called()

    @mock.patch.object(Server.Server, "ping_check")
    def test_three_votes_out_of_three(self, mock_ping, mock_socket):
        thread = threading.Thread(target=self.s.handle_votes, args = ("127.0.0.9", mock_socket))
        thread.start()
        time.sleep(PAUSE)
        threading.Thread(target=self.s.handle_votes, args = ("127.0.0.7", mock_socket)).start()
        time.sleep(PAUSE)
        threading.Thread(target=self.s.handle_votes, args = ("127.0.0.8", mock_socket)).start()
        thread.join()

        self.assertIsNotNone(self.s.master_server)
        mock_ping.assert_called()

    def test_invalid_votes(self, mock_socket):
        thread = threading.Thread(target=self.s.handle_votes, args = ("127.0.0.9", mock_socket))
        thread.start()
        time.sleep(PAUSE)
        threading.Thread(target=self.s.handle_votes, args = ("127.0.0.9", mock_socket)).start()
        time.sleep(LONG_PAUSE)
        threading.Thread(target=self.s.handle_votes, args = ("127.0.0.9", mock_socket)).start()
        thread.join()

        self.assertIsNone(self.s.master_server)

class Test_ping_check_with_three(unittest.TestCase):

    s = None

    def setUp(self):
        self.s= Server.Server("127.0.0.9")
        self.s.server_list = list(DEFAULT_SERVER_LIST)
        self.s.network = ["127.0.0.9", "127.0.0.8", "127.0.0.7"]
        self.s.ping_targets = {"127.0.0.9" : 1, "127.0.0.8" : 1, "127.0.0.7" : 1}

    def tearDown(self):
        self.s.close()
        del self.s

    def test_one_out_of_three_offline(self):
        thread = threading.Thread(target=self.s.ping_check, args = ())
        thread.start()
        time.sleep(PAUSE)
        time.sleep(WAIT_PING_TIME)
        self.s.ping_lock.acquire()
        self.s.ping_targets["127.0.0.8"] = 1
        self.s.ping_lock.release()
        time.sleep(WAIT_PING_TIME)

        self.assertTrue(self.s.server_online)
        self.s.server_online = False
        thread.join()

    def test_two_out_of_three_offline(self):
        thread = threading.Thread(target=self.s.ping_check, args = ())
        thread.start()
        time.sleep(2 * WAIT_PING_TIME + PAUSE)

        self.assertFalse(self.s.server_online)
        thread.join()

class Test_ping_check_with_five(unittest.TestCase):

    s = None

    def setUp(self):
        self.s= Server.Server("127.0.0.9")
        self.s.server_list = list(DEFAULT_SERVER_LIST)
        self.s.add_server_to_list("127.0.0.6")
        self.s.add_server_to_list("127.0.0.5")
        self.s.network = ["127.0.0.9", "127.0.0.8", "127.0.0.7", "127.0.0.6", "127.0.0.5"]
        self.s.ping_targets = {"127.0.0.9" : 1, "127.0.0.8" : 1, "127.0.0.7" : 1, "127.0.0.6" : 1, "127.0.0.5" : 1}

    def tearDown(self):
        self.s.close()
        del self.s

    def test_two_out_of_five_offline(self):
        thread = threading.Thread(target=self.s.ping_check, args = ())
        thread.start()
        time.sleep(PAUSE)
        time.sleep(WAIT_PING_TIME)
        self.s.ping_lock.acquire()
        self.s.ping_targets["127.0.0.8"] = 1
        self.s.ping_targets["127.0.0.7"] = 1
        self.s.ping_lock.release()
        time.sleep(WAIT_PING_TIME)

        self.assertTrue(self.s.server_online)
        self.s.server_online = False
        thread.join()

    def test_three_out_of_five_offline(self):
        thread = threading.Thread(target=self.s.ping_check, args = ())
        thread.start()
        time.sleep(PAUSE)
        time.sleep(WAIT_PING_TIME)
        self.s.ping_lock.acquire()
        self.s.ping_targets["127.0.0.8"] = 1
        self.s.ping_lock.release()
        time.sleep(WAIT_PING_TIME)

        self.assertFalse(self.s.server_online)
        thread.join()

class Test_ping_check_other_occurences(unittest.TestCase):

    s = None

    def setUp(self):
        self.s= Server.Server("127.0.0.9")
        self.s.server_list = list(DEFAULT_SERVER_LIST)
        self.s.network = ["127.0.0.9", "127.0.0.8", "127.0.0.7"]
        self.s.ping_targets = {"127.0.0.9" : 1, "127.0.0.8" : 1, "127.0.0.7" : 1}

    def tearDown(self):
        self.s.close()
        del self.s

    def test_new_server(self):
        self.s.add_server_to_list("127.0.0.6")

        thread = threading.Thread(target=self.s.ping_check, args = ())
        thread.start()
        time.sleep(PAUSE)
        time.sleep(WAIT_PING_TIME)
        self.s.ping_lock.acquire()
        self.s.ping_targets["127.0.0.8"] = 1
        self.s.ping_targets["127.0.0.7"] = 1
        self.s.ping_targets["127.0.0.6"] = 1
        self.s.ping_lock.release()
        time.sleep(WAIT_PING_TIME)

        self.assertTrue(self.s.server_online)
        self.assertEqual(self.s.network, ["127.0.0.9", "127.0.0.8", "127.0.0.7", "127.0.0.6"])
        self.s.server_online = False
        thread.join()

    def test_shutdown(self):
        thread = threading.Thread(target=self.s.ping_check, args = ())
        thread.start()
        time.sleep(PAUSE)
        self.s.shutdown()
        time.sleep(PAUSE)

        self.assertFalse(self.s.server_online)
        thread.join()
