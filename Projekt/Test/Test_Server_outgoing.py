import unittest
from unittest import mock
import time
import logging
import threading
import sys
sys.path.insert(1, '../src')
import Server
import Client

FORMAT = 'UTF-8'
HEADER = 64

ASK_MASTER_MESSAGE = "Your master?"
VOTE_MASTER_MESSAGE = "vote = "
MASTER_CONFIRMED_MESSAGE = "The master has been confirmed"
MASTER_DECLINED_MESSAGE = "The master has been declined"
PING_MESSAGE = "ip = "
WAIT_PING_TIME = 15
SEND_PING_TIME = 6
MASTER_VOTE_TIMEOUT = 20
INITIAL_NETWORK_SEARCH_TIMEOUT = 10

DEFAULT_SERVER_LIST = ["127.0.0.7", "127.0.0.8", "127.0.0.9"]
PAUSE = 1

"""
Note:
The test will take some time, because the connection has to be
based on different timings to ensure connections with delays.
To reduce the time the test need to evaluate, you may want to
decrease the timeouts in the 'Server.py'.
(For example: MASTER_VOTE_TIMEOUT : 30 -> MASTER_VOTE_TIMEOUT : 10)
"""

logging.basicConfig(
    format='%(threadName)s:%(message)s',
    level=logging.DEBUG,
)

class Test_check_network_masters(unittest.TestCase):

    s = None

    def setUp(self):
        self.s = Server.Server("127.0.0.9")

    def tearDown(self):
        self.s.close()
        del self.s

    def test_no_master_in_network(self):
        self.s.network_masters = {"127.0.0.9" : None, "127.0.0.8" : None, "127.0.0.7" : None}
        result = self.s.check_network_masters()

        self.assertIsNone(result)

    def test_valid_master_in_network_with_two(self):
        self.s.network_masters = {"127.0.0.9" : None, "127.0.0.8" : "127.0.0.8", "127.0.0.7" : "127.0.0.8"}
        result = self.s.check_network_masters()

        self.assertIsNotNone(result)

    def test_valid_master_in_network_with_three(self):
        self.s.network_masters = {"127.0.0.9" : "127.0.0.8", "127.0.0.8" : "127.0.0.8", "127.0.0.7" : "127.0.0.8"}
        result = self.s.check_network_masters()

        self.assertIsNotNone(result)

    def test_invalid_master_in_network(self):
        self.s.network_masters = {"127.0.0.9" : None, "127.0.0.8" : "127.0.0.8", "127.0.0.7" : None}
        result = self.s.check_network_masters()

        self.assertIsNone(result)

    def test_invalid_and_valid_master_in_network(self):
        self.s.network_masters = {"127.0.0.9" : "127.0.0.8", "127.0.0.8" : "127.0.0.8", "127.0.0.7" : "127.0.0.8", "127.0.0.6" : "127.0.0.6", "127.0.0.5" : "127.0.0.6"}
        result = self.s.check_network_masters()

        self.assertEqual(result, "127.0.0.8")

class Test_calc_master_self(unittest.TestCase):

    s = None

    def setUp(self):
        self.s = Server.Server("127.0.0.9")
        self.s.network = list(DEFAULT_SERVER_LIST)
        self.s.votes = []
        self.master_server = None

    def tearDown(self):
        self.s.close()
        del self.s

    def test_self_master_and_voting(self):
        threading.Thread(target=self.s.calc_master, args = ()).start()
        time.sleep(3)
        self.s.votes.append("127.0.0.8")
        self.s.votes.append("127.0.0.7")
        time.sleep(MASTER_VOTE_TIMEOUT)
        # passes the test if thread terminates
        self.assertEqual(len(threading.enumerate()), 1)

    def test_self_master_and_no_votes(self):
        threading.Thread(target=self.s.calc_master, args = ()).start()
        time.sleep(MASTER_VOTE_TIMEOUT)
        time.sleep(3)
        self.assertFalse(self.s.server_online)

@mock.patch('Client.Client', autospec=True)
class Test_calc_master_other(unittest.TestCase):

    s = None

    def setUp(self):
        self.s = Server.Server("127.0.0.7")
        self.s.network = list(DEFAULT_SERVER_LIST)
        self.s.master_server = None

    def tearDown(self):
        self.s.close()
        del self.s

    @mock.patch.object(Server.Server, "ping")
    def test_master_confirmed(self, mock_ping, mock_client):
        mock_instance = mock_client.return_value
        mock_instance.connect.return_value = True
        mock_instance.send.return_value = MASTER_CONFIRMED_MESSAGE
        self.s.calc_master()
        self.assertEqual(self.s.master_server, max(self.s.network))
        mock_ping.assert_called()

    @mock.patch.object(Server.Server, "find_network")
    def test_master_declined(self, mock_find_network, mock_client):
        mock_instance = mock_client.return_value
        mock_instance.connect.return_value = True
        mock_instance.send.return_value = MASTER_DECLINED_MESSAGE
        self.s.calc_master()
        self.assertEqual(self.s.master_server, None)
        mock_find_network.assert_called()

    @mock.patch.object(Server.Server, "find_network")
    def test_master_not_available(self, mock_find_network, mock_client):
        mock_client.return_value.connect.return_value = False
        self.s.calc_master()
        mock_find_network.assert_called()

@mock.patch('Client.Client', autospec=True)
class Test_client_Thread(unittest.TestCase):

    s = None

    def setUp(self):
        self.s = Server.Server("127.0.0.7")
        self.s.network = list(DEFAULT_SERVER_LIST)
        self.s.network_masters = {}

    def tearDown(self):
        self.s.close()
        del self.s

    def test_server_available(self, mock_client):
        mock_instance = mock_client.return_value
        mock_instance.connect.return_value = True
        mock_instance.send.return_value = None
        cond = threading.Condition()
        delay = 0
        sip = "127.0.0.8"

        self.s.client_thread(cond, sip, delay)
        self.assertEqual(self.s.network_masters[sip], 'None')
        self.assertEqual(len(self.s.network), 3)

    def test_server_not_available(self, mock_client):
        mock_instance = mock_client.return_value
        mock_instance.connect.return_value = False
        cond = threading.Condition()
        delay = 0
        sip = "127.0.0.8"

        self.s.client_thread(cond, sip, delay)
        self.assertEqual(len(self.s.network), 2)

    def test_master_of_sip(self, mock_client):
        mocked_ip = "127.0.0.9"
        mock_instance = mock_client.return_value
        mock_instance.connect.return_value = True
        mock_instance.send.return_value = mocked_ip
        cond = threading.Condition()
        delay = 0
        sip = "127.0.0.8"

        self.s.client_thread(cond, sip, delay)
        self.assertEqual(self.s.network_masters[sip], mocked_ip)
        self.assertEqual(len(self.s.network), 3)

@mock.patch('Client.Client', autospec=True)
class Test_find_network_with_three(unittest.TestCase):

    s = None

    def setUp(self):
        self.s = Server.Server("127.0.0.9")
        self.s.requests = ["127.0.0.8", "127.0.0.7"]
        self.s.network_masters = {}
        self.s.network = []

    def tearDown(self):
        self.s.close()
        del self.s

    @mock.patch.object(Server.Server, "check_network_masters")
    @mock.patch.object(Server.Server, "calc_master")
    def test_three_server_network(self, mock_calc_master, mock_check_network_masters, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.connect.return_value = True
        mock_client_instance.send.side_effect = ['None', 'None']
        mock_check_network_masters.return_value = None

        self.s.find_network()
        self.assertEqual(self.s.network, ["127.0.0.7", "127.0.0.8", "127.0.0.9"])
        mock_calc_master.assert_called()
        mock_check_network_masters.assert_called()

    @mock.patch.object(Server.Server, "retry_find_network")
    def test_not_sufficient_requests(self, mock_retry, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.connect.return_value = True
        mock_client_instance.send.side_effect = ['None', 'None']

        self.s.requests = ["127.0.0.8"]
        self.s.find_network()
        mock_retry.assert_called()

    @mock.patch.object(Server.Server, "ping")
    def test_network_with_active_master(self, mock_ping, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.connect.return_value = True
        mock_client_instance.send.side_effect = ["127.0.0.8", "127.0.0.8"]

        self.s.find_network()
        self.assertEqual(self.s.master_server, "127.0.0.8")
        mock_ping.assert_called()

    @mock.patch.object(Server.Server, "calc_master")
    def test_network_with_invalid_master(self, mock_calc_master, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.connect.return_value = True
        mock_client_instance.send.side_effect = [None, "127.0.0.8"]

        self.s.find_network()
        self.assertIsNone(self.s.master_server)
        mock_calc_master.assert_called()

@mock.patch('Client.Client', autospec=True)
class Test_find_network_with_five(unittest.TestCase):

    s = None

    def setUp(self):
        self.s = Server.Server("127.0.0.9")
        self.s.add_server_to_list("127.0.0.6")
        self.s.add_server_to_list("127.0.0.5")
        self.s.requests = ["127.0.0.8", "127.0.0.7", "127.0.0.5", "127.0.0.6"]
        self.s.network_masters = {}
        self.s.network = []

    def tearDown(self):
        self.s.close()
        del self.s

    @mock.patch.object(Server.Server, "check_network_masters")
    @mock.patch.object(Server.Server, "calc_master")
    def test_five_server_network(self, mock_calc_master, mock_check_network_masters, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.connect.return_value = True
        mock_client_instance.send.side_effect = ['None', 'None', 'None', 'None']
        mock_check_network_masters.return_value = None

        self.s.find_network()
        self.assertEqual(self.s.network, ["127.0.0.7", "127.0.0.8", "127.0.0.9","127.0.0.6", "127.0.0.5"])
        mock_calc_master.assert_called()
        mock_check_network_masters.assert_called()

    @mock.patch.object(Server.Server, "retry_find_network")
    def test_invalid_network(self, mock_retry, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.connect.side_effect = [True, False, False, False]
        mock_client_instance.send.return_value = 'None'

        self.s.find_network()
        mock_retry.assert_called()

    def test_invalid_network_till_shutdown(self, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.connect.side_effect = [True, False, False, False, True,
         False, False, False, True, False, False, False]
        mock_client_instance.send.side_effect = ['None', 'None', 'None']

        self.s.find_network()
        self.assertFalse(self.s.server_online)

@mock.patch('Client.Client', autospec=True)
class Test_ping(unittest.TestCase):

    s = None

    def setUp(self):
        self.s = Server.Server("127.0.0.9")
        self.s.network = list(DEFAULT_SERVER_LIST)
        self.s.master_server = "127.0.0.8"

    def tearDown(self):
        self.s.close()
        del self.s

    def test_shutdown(self, mock_client):
        thread = threading.Thread(target=self.s.ping, args = ())
        thread.start()
        time.sleep(PAUSE)
        self.s.shutdown()
        time.sleep(PAUSE)

        self.assertFalse(self.s.server_online)
        self.assertEqual(len(threading.enumerate()), 1)

    def test_master_available(self, mock_client):
        mock_instance = mock_client.return_value
        mock_instance.connect.return_value = True
        message = PING_MESSAGE + self.s.ip
        thread = threading.Thread(target=self.s.ping, args = ())
        thread.start()
        time.sleep(SEND_PING_TIME + 3)

        mock_instance.send.assert_called_with(message)
        self.s.shutdown()
        time.sleep(PAUSE)
        self.assertFalse(self.s.server_online)

    @mock.patch.object(Server.Server, "find_network")
    def test_master_not_available(self, mock_find_network, mock_client):
        mock_client.return_value.connect.return_value = False
        thread = threading.Thread(target=self.s.ping, args = ())
        thread.start()
        time.sleep(SEND_PING_TIME + 3)

        mock_find_network.assert_called()
        self.s.shutdown()
        time.sleep(PAUSE)
        self.assertFalse(self.s.server_online)

class Test_eliminate_dublicates(unittest.TestCase):

    def Test_eliminate_dublicates(self):
        with_dublicates = [1,2,3,1,1,6,4,6,3,3,4,9,8,8]
        without_dublicates = [1,2,3,4,6,8,9]
        s = Server.Server("127.0.0.9")
        result = list(s.eliminate_dublicates(with_dublicates))
        self.assertItemsEqual(result, without_dublicates)
