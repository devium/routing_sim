class ChannelView(object):
    """Channel from the perspective of this."""

    def __init__(self, this_node, other_node):
        assert this_node != other_node
        self.this = this_node.uid
        self.partner = self.other = other_node.uid
        if self.this < self.other:
            self._account = this_node.G.edge[this_node][other_node]
        else:
            self._account = this_node.G.edge[this_node][other_node]

    @property
    def balance(self):
        "what other owes self if positive"
        if self.this < self.other:
            return self._account['balance']
        return -self._account['balance']

    @balance.setter
    def balance(self, value):
        if self.this < self.other:
            self._account['balance'] = value
        else:
            self._account['balance'] = -value

    @property
    def deposit(self):
        return self._account[self.this]

    @deposit.setter
    def deposit(self, value):
        assert value >= 0
        self._account[self.this] = value

    @property
    def partner_deposit(self):
        return self._account[self.other]

    @property
    def capacity(self):
        return self.balance + self.deposit

    def __repr__(self):
        return '<Channel({}:{} {}:{} balance:{}>'.format(self.this, self.deposit, self.other,
                                                         self.partner_deposit, self.balance)
