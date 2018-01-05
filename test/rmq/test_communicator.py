import unittest
import uuid

from plum import rmq
from plum.rmq import utils
import plum.rmq
import plum.rmq.launch
import plum.test_utils
from test.test_rmq import _HAS_PIKA
from test.util import TestCaseWithLoop

if _HAS_PIKA:
    import pika.exceptions

@unittest.skipIf(not _HAS_PIKA, "Requires pika library and RabbitMQ")
class TestCommunicator(TestCaseWithLoop):
    def setUp(self):
        super(TestCommunicator, self).setUp()

        self.connector = rmq.RmqConnector('amqp://guest:guest@localhost:5672/', loop=self.loop)
        self.exchange_name = "{}.{}".format(self.__class__.__name__, uuid.uuid4())

        self.communicator = rmq.RmqCommunicator(
            self.connector, exchange_name=self.exchange_name)

        self.connector.connect()
        # Run the loop until until both are ready
        plum.run_until_complete(self.communicator.initialised_future())

    def tearDown(self):
        # Close the connector before calling super because it will
        # close the loop
        self.connector.close()
        super(TestCommunicator, self).tearDown()

    def test_rpc_send(self):
        MSG = {'test': 5}
        RESPONSE = 'response'
        messages_received = plum.Future()

        class Receiver(plum.Receiver):
            def on_rpc_receive(self, msg):
                messages_received.set_result(msg)
                return RESPONSE

            def on_broadcast_receive(self, msg):
                pass

        receiver = Receiver()
        self.communicator.register_receiver(receiver, 'receiver')

        # Send and make sure we get the message
        future = self.communicator.rpc_send('receiver', MSG)
        result = plum.run_until_complete(messages_received, self.loop)
        self.assertEqual(result, MSG)

        # Now make sure we get the response
        response = plum.run_until_complete(future)
        self.assertEqual(response, RESPONSE)