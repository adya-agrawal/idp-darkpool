from agent.Agent import Agent
from agent.idp_auction.ServiceAgent import ServiceAgent as ServiceAgent
from message.Message import Message
from util.aes import aes

import logging
import pandas as pd
import random


from util import util

class ClientAgent(Agent):

    def __str__(self):
        return "[client]"

    def __init__(self, id, name, type, random_state, iterations=1):

        # Set logger
        super().__init__(id, name, type, random_state)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)


        """Read keys."""
        # Read system-wide pk
        self.system_pk = util.read_pk(f"pki_files/system_pk.pem")

        # sk is used to establish pairwise secret with neighbors' public keys
        self.key = util.read_key(f"pki_files/client{self.id}.pem")
        self.secret_key = self.key.d

        self.orders = []

        # Accumulate this client's run time information by step.
        self.elapsed_time = {'PLACE': pd.Timedelta(0),
                             'MATCH': pd.Timedelta(0),
                             'EXECUTE': pd.Timedelta(0),
                             }

        # Iteration counter
        self.no_of_iterations = iterations
        self.current_iteration = 1
        self.current_base = 0
        self.sent_orders = False
        self.order_status = {}
        self.total_orders = 0
        self.matched_orders = 0
        self.executed_orders = 0
        self.dt_protocol_start = None

        # State flag
        self.setup_complete = False
        self.aes = aes()
        self.aes_key = None



    # Simulation lifecycle messages.
    def kernelStarting(self, startTime):

        # Initialize custom state properties into which we will later accumulate results.
        # To avoid redundancy, we allow only the first client to handle initialization.
        if self.id == 1:
            self.kernel.custom_state['clt_place'] = pd.Timedelta(0)
            self.kernel.custom_state['clt_match'] = pd.Timedelta(0)
            self.kernel.custom_state['clt_execute'] = pd.Timedelta(0)

        # Find the PPFL service agent, so messages can be directed there.
        self.serviceAgentID = self.kernel.findAgentByType(ServiceAgent)
        self.setComputationDelay(0)

        # Request a wake-up call as in the base Agent.  Noise is kept small because
        # the overall protocol duration is so short right now.  (up to one microsecond)
        super().kernelStarting(startTime +
                               pd.Timedelta(self.random_state.randint(low=0, high=1000), unit='ns'))

    def kernelStopping(self):

        # Accumulate into the Kernel's "custom state" this client's elapsed times per category.
        # Note that times which should be reported in the mean per iteration are already so computed.
        # These will be output to the config (experiment) file at the end of the simulation.
        if self.id == 1:
            self.kernel.custom_state['clt_place'] += (
                    self.elapsed_time['PLACE'] / self.no_of_iterations)
            self.kernel.custom_state['clt_match'] += (
                    self.elapsed_time['MATCH'] / self.no_of_iterations)
            self.kernel.custom_state['clt_execute'] += (
                    self.elapsed_time['EXECUTE'] / self.no_of_iterations)
            self.agent_print(f"Total executed Orders on Client side: {self.executed_orders}")
        super().kernelStopping()

    # Simulation participation messages.
    def wakeup(self, currentTime):
        super().wakeup(currentTime)
        dt_wake_start = pd.Timestamp('now')

    def receiveMessage(self, currentTime, msg):
        super().receiveMessage(currentTime, msg)

        if msg.body['msg'] == "SEND_ORDERS":
            self.dt_protocol_start = pd.Timestamp('now')
            if not self.sent_orders:
                self.send_orders(currentTime,msg.body['total'])
            self.recordTime(self.dt_protocol_start, 'PLACE')
            self.dt_protocol_start = pd.Timestamp('now')

        elif msg.body['msg'] == "MATCH":
            self.match_orders(msg.body['buy_order'],msg.body['sell_order'])
            if (self.matched_orders == self.total_orders):
                self.recordTime(self.dt_protocol_start, 'MATCH')

        elif msg.body['msg'] == "EXECUTE":
            self.execute_orders(msg.body['buy_order'],msg.body['sell_order'],msg.body['buy_price'],msg.body['sell_price'])
            self.recordTime(self.dt_protocol_start, 'EXECUTE')

    ###################################
    # Round logics
    ###################################
    def send_orders(self, currentTime, total):
        aes_key = self.aes.generate_aes_key()
        total_orders = 8
        # Randomly determine the number of real orders (between 5 and 7)
        num_real = random.randint(5, 7)
        # The remaining orders will be fake (so total - num_real will give the number of fake orders)
        num_fake = total_orders - num_real
        price_buy = random.randint(99, 101)
        price_sell = random.randint(98, 100)
        if self.id <= total / 2:
            buy_sell = 'B'
            price = price_buy
        else:
            buy_sell = 'S'
            price = price_sell
        client_name = self.name
        status_true = True  # Indicating the order is real
        status_false = False

        # Encrypt the client name and status
        encrypted_name = self.aes.encrypt_with_aes(aes_key, client_name)
        encrypted_status_true = self.aes.encrypt_with_aes(aes_key, str(status_true))
        encrypted_status_false = self.aes.encrypt_with_aes(aes_key, str(status_false))
        orders = []
        for order_id in range(0, num_real):
            order = (price, buy_sell, (self.id, encrypted_name, encrypted_status_true))
            orders.append(order)
        for order_id in range(0, num_fake):
            order = (price, buy_sell, (self.id, encrypted_name, encrypted_status_false))
            orders.append(order)
        self.total_orders = len(orders)
        self.aes_key = aes_key
        # Send the orders to the server
        self.sendMessage(self.serviceAgentID,
                         Message({"msg": "ORDER",
                                  "iteration": self.current_iteration,
                                  "orders": orders,
                                  }),
                         tag="comm_order_generation")
        self.sent_orders = True

    def match_orders(self, order1, order2):
        # Function to send the execution message
        def send_execution_message(order, type):
            id, encrypted_name, encrypted_status = order

            status = self.aes.decrypt_with_aes(self.aes_key, encrypted_status)
            status = True if status == "True" else False
            # Send message to server to indicate whether the order was real or not
            self.sendMessage(self.serviceAgentID,
                             Message({
                                 "msg": "MATCH",
                                 "iteration": self.current_iteration,
                                 "order": order,
                                 "type": type,
                                 "status": status  # Send decrypted status back to server
                             }),
                             tag="comm_order_match")

        client_name_order_1 = self.aes.decrypt_with_aes(self.aes_key, order1[1])
        client_name_order_2 = self.aes.decrypt_with_aes(self.aes_key, order2[1])
        if client_name_order_1 is not None and client_name_order_1 == self.name:  # Check if the agent name matches
            send_execution_message(order1, "buy")
        elif client_name_order_2 is not None and client_name_order_2 == self.name:  # Check if the agent name matches
            send_execution_message(order2, "sell")

    def execute_orders(self, order1, order2, buy_price, sell_price):
        # Function to send the name reveal message
        def send_execution_message(name, type, price):
            self.sendMessage(self.serviceAgentID,
                             Message({
                                 "msg": "EXECUTE",
                                 "iteration": self.current_iteration,
                                 "name": name,
                                 "type": type,
                                 "price" : price,
                                 "status": True  # Send decrypted status back to server
                             }),
                             tag="comm_order_execute")

        client_name_order_1 = self.aes.decrypt_with_aes(self.aes_key, order1[1])
        client_name_order_2 = self.aes.decrypt_with_aes(self.aes_key, order2[1])
        if client_name_order_1 is not None and client_name_order_1 == self.name:
            self.executed_orders += 1
            send_execution_message(client_name_order_1, "buy", buy_price)
        elif client_name_order_2 is not None and client_name_order_2 == self.name:
            self.executed_orders += 1
            send_execution_message(client_name_order_2, "sell", sell_price)


    # ======================== UTIL ========================
    def recordTime(self, startTime, categoryName):
        dt_protocol_end = pd.Timestamp('now')
        self.elapsed_time[categoryName] += dt_protocol_end - startTime

    def agent_print(*args, **kwargs):
        """
        Custom print function that adds a [Server] header before printing.

        Args:
            *args: Any positional arguments that the built-in print function accepts.
            **kwargs: Any keyword arguments that the built-in print function accepts.
        """
        print(*args, **kwargs)
