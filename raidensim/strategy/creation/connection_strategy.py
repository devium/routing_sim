from typing import Callable

from raidensim.network.node import Node
from raidensim.network.raw_network import RawNetwork
from raidensim.types import Fullness


class ConnectionStrategy(object):
    def connect(self, raw: RawNetwork, a: Node, b: Node):
        raise NotImplementedError


class BidirectionalConnectionStrategy(ConnectionStrategy):
    def __init__(self, deposit_mapping: Callable[[Fullness], int]):
        self.deposit_mapping = deposit_mapping

    def connect(self, raw: RawNetwork, a: Node, b: Node):
        raw.setup_channel(a, b, self.deposit_mapping(a.fullness))
        raw.setup_channel(b, a, self.deposit_mapping(b.fullness))
        a['num_initiated_channels'] += 1
        a['num_incoming_channels'] += 1
        a['num_outgoing_channels'] += 1
        b['num_accepted_channels'] += 1
        b['num_incoming_channels'] += 1
        b['num_outgoing_channels'] += 1
