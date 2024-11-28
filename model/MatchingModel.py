class Node:
    def __init__(self, price, order_type, orders):
        self.price = price
        self.order_type = order_type
        self.orders = orders  # list of (person, real/fake)
        self.next = None
        self.prev = None

class BucketList:
    def __init__(self):
        self.head = None
        self.tail = None

    def insert_or_update_node(self, price, order_type, order):
        current = self.head

        while current is not None:
            if current.price == price and current.order_type == order_type:
                current.orders.append(order)
                return
            elif (order_type == 'B' and current.price < price) or (order_type == 'S' and current.price > price):
                break
            current = current.next

        new_node = Node(price, order_type, [order])

        if self.head is None:  # List is empty
            self.head = self.tail = new_node
        elif current is None:  # Insert at the end
            self.tail.next = new_node
            new_node.prev = self.tail
            self.tail = new_node
        elif current.prev is None:  # Insert at the head
            new_node.next = self.head
            self.head.prev = new_node
            self.head = new_node
        else:  # Insert in the middle
            previous = current.prev
            previous.next = new_node
            new_node.prev = previous
            new_node.next = current
            current.prev = new_node

    def remove_price(self, node):
        """
        Remove a node (price level) from the list.
        """
        if node is None:
            return

        if node == self.head and node == self.tail:  # Only one node in the list
            self.head = self.tail = None
        elif node == self.head:  # Node is the head
            self.head = self.head.next
            if self.head is not None:
                self.head.prev = None
        elif node == self.tail:  # Node is the tail
            self.tail = self.tail.prev
            if self.tail is not None:
                self.tail.next = None
        else:  # Node is in the middle
            node.prev.next = node.next
            node.next.prev = node.prev

        node.next = node.prev = None  # Disconnect the node completely

def create_sorted_lists(orders):
    buy_list = BucketList()
    sell_list = BucketList()

    for order in orders:
        price, order_type, order_details = order
        if order_type == 'B':
            buy_list.insert_or_update_node(price, order_type, order_details)
        elif order_type == 'S':
            sell_list.insert_or_update_node(price, order_type, order_details)

    return buy_list, sell_list