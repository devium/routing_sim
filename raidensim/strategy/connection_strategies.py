from typing import Callable

from raidensim.strategy.strategy import NodeConnectionData, ConnectionStrategy
from raidensim.types import Fullness


class BidirectionalConnectionStrategy(ConnectionStrategy):
    def __init__(self, deposit_mapping: Callable[[Fullness], int]):
        self.deposit_mapping = deposit_mapping

    def connect(self, a: NodeConnectionData, b: NodeConnectionData):
        a, a_data = a
        b, b_data = b
        a.setup_channel(b, self.deposit_mapping(a.fullness))
        b.setup_channel(a, self.deposit_mapping(b.fullness))
        a_data['num_initiated_channels'] += 1
        a_data['num_incoming_channels'] += 1
        a_data['num_outgoing_channels'] += 1
        b_data['num_accepted_channels'] += 1
        b_data['num_incoming_channels'] += 1
        b_data['num_outgoing_channels'] += 1
