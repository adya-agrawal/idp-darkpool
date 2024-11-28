from agent.Agent import Agent
from message.Message import Message
import logging
import pandas as pd
import random
from model.MatchingModel import BucketList, create_sorted_lists
from util import util

class ServiceAgent(Agent):
    def __init__(self, id, name, type,
                 random_state=None,
                 msg_fwd_delay=1000000,
                 round_time=pd.Timedelta("10s"),
                 iterations=1,
                 num_clients=10,
                 parallel_mode=1,
                 debug_mode=0,
                 users={}):

        # Base class init.
        super().__init__(id, name, type, random_state)

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        if debug_mode:
            logging.basicConfig()

        # System parameters.
        self.msg_fwd_delay = msg_fwd_delay  # time to forward a peer-to-peer client relay message
        self.round_time = round_time        # default waiting time per round
        self.no_of_iterations = iterations  # number of iterations
        self.parallel_mode = parallel_mode  # parallel

        # Input parameters.
        self.num_clients = num_clients      # number of users per training round
        self.users = users   # the list of user IDs
        # Read keys.
        self.server_key = util.read_key("pki_files/server_key.pem")
        self.system_sk = util.read_sk("pki_files/system_pk.pem")

        # agent accumulation of elapsed times by category of tasks
        self.elapsed_time = {'PLACE': pd.Timedelta(0),
                             'MATCH': pd.Timedelta(0),
                             'REVEAL': pd.Timedelta(0),
                             'EXECUTE': pd.Timedelta(0)
                             }

        self.current_iteration = 1  # Single iteration
        self.current_round = 0
        self.recv_user_orders = []
        self.buy_list = BucketList()
        self.sell_list = BucketList()
        self.total_orders = 0
        self.executed_orders = 0
        self.current_buy_price = None
        self.current_sell_price = None
        self.current_buy_order = None
        self.current_sell_order = None
        self.current_buy_order_origin = None
        self.current_sell_order_origin = None
        self.current_buy_order_status = None
        self.current_sell_order_status = None
        self.current_buy_order_name = None
        self.current_sell_order_name = None
        self.execute_user_orders = []
        self.clients_sent_orders = 0  # Track clients who have sent their orders
        self.dt_protocol_start = None

        # Map the message processing functions
        self.aggProcessingMap = {
            0: self.initialize,      # Receive and sort orders
            1: self.match_orders,    # Match orders in pairs
            2: self.reveal_orders,
            3: self.execute_orders# Execute or move to next pair based on client action
        }

        self.namedict = {
            0: "initialize",
            1: "match orders",
            2: "reveal orders",
            3: "execute orders"
        }

    def kernelStarting(self, startTime):

        if __debug__:
            self.agent_print(f"Initialize: {self.dt_protocol_start}")
        self.kernel.custom_state['srv_place'] = pd.Timedelta(0)
        self.kernel.custom_state['srv_match'] = pd.Timedelta(0)
        self.kernel.custom_state['srv_reveal'] = pd.Timedelta(0)
        self.kernel.custom_state['srv_execute'] = pd.Timedelta(0)

        self.setComputationDelay(0)
        super().kernelStarting(startTime)

    def kernelStopping(self):
        self.kernel.custom_state['srv_place'] += (
                self.elapsed_time['PLACE'] / self.no_of_iterations)
        self.kernel.custom_state['srv_match'] += (
                self.elapsed_time['MATCH'] / self.no_of_iterations)
        self.kernel.custom_state['srv_reveal'] += (
                self.elapsed_time['REVEAL'] / self.no_of_iterations)
        self.kernel.custom_state['srv_execute'] += (
                self.elapsed_time['EXECUTE'] / self.no_of_iterations)

        super().kernelStopping()

    def wakeup(self, currentTime):
        """
        The wakeup function is called at the end of each round to execute
        the appropriate function based on the current round (initialize, match, or execute).
        """
        super().wakeup(currentTime)

        # Check if we should process based on the current round
        if self.current_iteration <= self.no_of_iterations and self.current_round < len(self.aggProcessingMap):
            if __debug__:
                self.agent_print(f"wakeup in iteration {self.current_iteration} at function {self.namedict[self.current_round]}; current time is {currentTime}")
            self.aggProcessingMap[self.current_round](currentTime)
        else:
            if __debug__:
                self.agent_print("All orders processed.")
            self.kernelStopping()  # End simulation when all orders are processed

    def receiveMessage(self, currentTime, msg):
        """Receive client messages (ORDER)."""
        super().receiveMessage(currentTime, msg)

        if msg.body['msg'] == "ORDER":
            new_orders = msg.body['orders']
            self.recv_user_orders.extend(new_orders) # Store received orders
            self.clients_sent_orders += 1
            if self.clients_sent_orders == self.num_clients:
                self.setWakeup(currentTime + pd.Timedelta('1s'))  # Proceed to matching quickly
            if __debug__:
                self.logger.info(f"Received order from client at {currentTime}")
        elif msg.body['msg'] == "MATCH":
            type = msg.body['type']
            if type == "buy":
                self.current_buy_order_status = msg.body['status']
            elif type == "sell":
                self.current_sell_order_status = msg.body['status']
            if __debug__:
                self.agent_print(f"Received match from client {msg.body['order']} {msg.body['type']} {msg.body['status']}")
        elif msg.body['msg'] == "EXECUTE":
            type = msg.body['type']
            if type == "buy":
                self.current_buy_order_name = msg.body['name']
            elif type == "sell":
                self.current_sell_order_name = msg.body['name']
            if __debug__:
                self.agent_print(f"Received execute from client {msg.body['name']} {msg.body['type']} {msg.body['price']}")

    def initialize(self, currentTime):
        """
        This is the first phase where the server expects to receive all orders from clients.
        Once all orders are received, the server sorts them and moves to the matching phase.
        """
        # Initialize custom state properties
        self.dt_protocol_start = pd.Timestamp('now')
        if self.clients_sent_orders < self.num_clients:
            if __debug__:
                self.agent_print(f"Waiting for orders from clients. Received from {self.clients_sent_orders} out of {self.num_clients}")
            for user_id in self.users:
                self.sendMessage(user_id,
                                 Message({"msg": "SEND_ORDERS",  # Message requesting orders
                                          "sender": self.id,
                                          "total": self.num_clients}),
                                 tag="comm_output_server")

            # Wait for the next wakeup to check if orders have been received
            self.setWakeup(currentTime + pd.Timedelta('1s'))  # Adjust timing as necessary
            self.dt_protocol_start = pd.Timestamp('now')
        else:
            # Orders received, sort them and move to the matching phase
            self.recordTime(self.dt_protocol_start, "PLACE")
            self.total_orders = len(self.recv_user_orders)
            self.buy_list, self.sell_list = create_sorted_lists(self.recv_user_orders)
            if __debug__:
                self.agent_print("Buy Orders:")
                current = self.buy_list.head
                while current:
                    print(f"Price: {current.price}, Orders: {current.orders}")
                    current = current.next

                # Iterate through the sell list
                print("Sell Orders:")
                current = self.sell_list.head
                while current:
                    print(f"Price: {current.price}, Orders: {current.orders}")
                    current = current.next

            self.current_round = 1  # Move to matching round
            self.setWakeup(currentTime + pd.Timedelta('1s'))
            self.dt_protocol_start = pd.Timestamp('now')

    def match_orders(self, currentTime):
        dt_protocol_start = pd.Timestamp('now')
        side_to_start = random.choice(["buy", "sell"])

        # Initialize buy and sell prices based on starting side
        if self.current_sell_order is None and self.current_buy_order is None:
            if side_to_start == "buy":
                self.current_buy_price = self.buy_list.head
                self.current_buy_order_origin = "head"
                self.current_sell_price = self.sell_list.tail
                self.current_sell_order_origin = "tail"
            else:
                self.current_buy_price = self.buy_list.tail
                self.current_buy_order_origin = "tail"
                self.current_sell_price = self.sell_list.head
                self.current_sell_order_origin = "head"

        # Handle current price orders
        self.update_current_price('buy')
        self.update_current_price('sell')

        while self.current_buy_price and self.current_sell_price:
            if __debug__:
                self.agent_print(f"Buy Price {self.current_buy_price.price} and Sell Price {self.current_sell_price.price}")
            self.current_buy_order = self.current_buy_price.orders[0]
            self.current_sell_order = self.current_sell_price.orders[0]

            if __debug__:
                self.agent_print(f"In matching, buy order: {self.current_buy_order}, sell order: {self.current_sell_order}")

            # Check for valid price matching
            if self.current_buy_price.price >= self.current_sell_price.price:
                buy_id = self.current_buy_order[0]
                sell_id = self.current_sell_order[0]
                self.sendMessage(buy_id, Message({"msg": "MATCH", "buy_order": self.current_buy_order, "sell_order": self.current_sell_order, "sender": 0}), tag="comm_output_server")
                self.sendMessage(sell_id, Message({"msg": "MATCH", "buy_order": self.current_buy_order, "sell_order": self.current_sell_order, "sender": 0}), tag="comm_output_server")
                self.current_round = 2
                break

            self.handle_price_removal(side_to_start)

        server_comp_delay = pd.Timestamp('now') - dt_protocol_start
        if not self.buy_list.head or not self.sell_list.head:
            self.recordTime(self.dt_protocol_start, "MATCH")
            self.agent_print("######## Iteration completion ########")
            self.agent_print(f"[Server] finished iteration {self.current_iteration} at {currentTime + server_comp_delay}")
            self.agent_print(f"Total orders received {self.total_orders} and orders executed {self.executed_orders}")
            self.current_iteration += 1

        self.setWakeup(currentTime + server_comp_delay + pd.Timedelta('1s'))


    def reveal_orders(self, currentTime):
        """
        Process the matched orders and execute based on the client responses.
        Execute if both buy and sell orders are real. If either is fake, handle accordingly.
        After processing, go back to matching to proceed with the next set of orders.
        """
        dt_protocol_start = pd.Timestamp('now')

        # Ensure both buy and sell statuses are available
        if self.current_buy_order_status is not None and self.current_sell_order_status is not None:
            buy_order_client = self.current_buy_order[0]  # Client name for the buy order
            sell_order_client = self.current_sell_order[0]  # Client name for the sell order

            if self.current_buy_order_status and self.current_sell_order_status:
                # Both orders are real - execute the trade
                if __debug__:
                    self.agent_print(f"Executing trade: Buy {self.current_buy_order} and Sell {self.current_sell_order}")
                self.execute_match(self.current_buy_order, self.current_sell_order, self.current_buy_price, self.current_sell_price)
                self.current_round = 3

            elif self.current_buy_order_status and not self.current_sell_order_status:
                # Buy is real, but sell is fake
                if __debug__:
                    self.agent_print(f"Sell order {self.current_sell_order} is fake. Removing all fake sell orders from {sell_order_client}.")
                self.remove_fake_orders(self.sell_list, sell_order_client)
                self.current_sell_order_status = None
                self.current_sell_order = None
                self.current_round = 1

            elif not self.current_buy_order_status and self.current_sell_order_status:
                # Sell is real, but buy is fake
                if __debug__:
                    self.agent_print(f"Buy order {self.current_buy_order} is fake. Removing all fake buy orders from {buy_order_client}.")
                self.remove_fake_orders(self.buy_list, buy_order_client)
                self.current_buy_order_status = None
                self.current_buy_order = None
                self.current_round = 1

            else:
                # Both orders are fake
                if __debug__:
                    self.agent_print(f"Both buy order {self.current_buy_order} and sell order {self.current_sell_order} are fake. Removing both.")
                self.remove_fake_orders(self.buy_list, buy_order_client)
                self.remove_fake_orders(self.sell_list, sell_order_client)
                self.current_buy_order_status = None
                self.current_sell_order_status = None
                self.current_buy_order = None
                self.current_sell_order = None
                self.current_round = 1

        server_comp_delay = pd.Timestamp('now') - dt_protocol_start
        self.setWakeup(currentTime + server_comp_delay + pd.Timedelta('3s'))

    def execute_match(self, buy_order, sell_order, current_buy_price, current_sell_price):
        self.executed_orders += 2
        buy_id = buy_order[0]
        sell_id = sell_order[0]
        self.sendMessage(buy_id,
                     Message({"msg": "EXECUTE",
                              "buy_order": buy_order,
                              "sell_order": sell_order,
                              "buy_price" : current_buy_price,
                              "sell_price" : current_sell_price,
                              "sender": 0}),
                     tag="comm_output_server")
        self.sendMessage(sell_id,
                         Message({"msg": "EXECUTE",
                                  "buy_order": buy_order,
                                  "sell_order": sell_order,
                                  "buy_price" : current_buy_price,
                                  "sell_price" : current_sell_price,
                                  "sender": 0}),
                         tag="comm_output_server")

    def execute_orders(self, currentTime):
        """
        Process the matched and real orders and execute based on the client responses.
        Execute if both buy and sell order client have been revealed.
        After processing, go back to matching to proceed with the next set of orders.
        """
        # Ensure both buy and sell order names are available
        dt_protocol_start = pd.Timestamp('now')
        if self.current_buy_order_name is not None and self.current_sell_order_name is not None:
            buy_order_client = self.current_buy_order_name  # Client name for the buy order
            sell_order_client = self.current_sell_order_name  # Client name for the sell order
            buy_price = self.current_buy_price.price
            sell_price = self.current_sell_price.price

            # Create a tuple to store the executed order details
            executed_order_tuple = (
                "Buy", buy_order_client, buy_price,
                "Sell", sell_order_client, sell_price
            )

            # Store the executed order details in an array
            self.execute_user_orders.append(executed_order_tuple)
            if __debug__:
                self.agent_print(f"Order executed and stored: {executed_order_tuple}")
            # Remove executed orders from both the buy and sell lists
            if self.current_buy_price.orders:
                self.current_buy_price.orders.pop(0)
            if self.current_sell_price.orders:
                self.current_sell_price.orders.pop(0)

            # Reset order statuses
            self.current_buy_order_status = None
            self.current_sell_order_status = None
            self.current_buy_order = None
            self.current_sell_order = None
            self.current_round = 1
        server_comp_delay = pd.Timestamp('now') - dt_protocol_start
        self.setWakeup(currentTime + server_comp_delay + pd.Timedelta('3s'))

    # ======================== UTIL ========================
    def update_current_price(self, side):
        if side == 'buy' and self.current_buy_price is not None and not self.current_buy_price.orders:
            self.buy_list.remove_price(self.current_buy_price)
            self.current_buy_price = self.buy_list.head if self.current_buy_order_origin == "head" else self.buy_list.tail
        elif side == 'sell' and self.current_sell_price is not None and not self.current_sell_price.orders:
            self.sell_list.remove_price(self.current_sell_price)
            self.current_sell_price = self.sell_list.head if self.current_sell_order_origin == "head" else self.sell_list.tail

    def handle_price_removal(self, side_to_start):
        if side_to_start == "buy":
            if __debug__:
                self.agent_print(f"Removing sell price {self.current_sell_price.price} as it cannot be matched with buy price {self.current_buy_price.price}.")
            next_sell = self.current_sell_price.prev
            self.sell_list.remove_price(self.current_sell_price)
            self.current_sell_price = next_sell
        else:
            if __debug__:
                self.agent_print(f"Removing buy price {self.current_buy_price.price} as it cannot be matched with sell price {self.current_sell_price.price}.")
            next_buy = self.current_buy_price.prev
            self.buy_list.remove_price(self.current_buy_price)
            self.current_buy_price = next_buy

    def remove_fake_orders(self, price_list, client_name):
        """
        Remove all fake orders from the specified price list for the given client.
        """
        current = price_list.head
        while current:
            current.orders = [order for order in current.orders if order[0] != client_name or order[1] is True]
            current = current.next

    def recordTime(self, startTime, categoryName):
        # Accumulate into time log.
        dt_protocol_end = pd.Timestamp('now')
        if __debug__:
            self.agent_print(f"Category name: {categoryName}, end time {dt_protocol_end}")
        self.elapsed_time[categoryName] += dt_protocol_end - startTime

    def agent_print(*args, **kwargs):
        """
        Custom print function that adds a [Server] header before printing.

        Args:
            *args: Any positional arguments that the built-in print function accepts.
            **kwargs: Any keyword arguments that the built-in print function accepts.
        """
        print(*args, **kwargs)
