from typing import Callable

from raidensim.strategy.strategy import FilterStrategy, NodeConnectionData
from raidensim.types import Fullness


class IdentityFilterStrategy(FilterStrategy):
    def filter(self, a: NodeConnectionData, b: NodeConnectionData):
        return a[0] != b[0]


class NotConnectedFilterStrategy(FilterStrategy):
    def filter(self, a: NodeConnectionData, b: NodeConnectionData):
        return b[0] not in a[0].cn[a[0]]


class DistanceFilterStrategy(FilterStrategy):
    def __init__(self, max_network_distance: float):
        self.max_network_distance = max_network_distance

    def filter(self, a: NodeConnectionData, b: NodeConnectionData):
        return a[0].ring_distance(b[0]) <= int(self.max_network_distance * a[0].cn.MAX_ID)


class FullerFilterStrategy(FilterStrategy):
    def filter(self, a: NodeConnectionData, b: NodeConnectionData):
        return a[0].fullness <= b[0].fullness


class MinIncomingDepositFilterStrategy(FilterStrategy):
    def __init__(self, deposit_mapping: Callable[[Fullness], float], min_incoming_deposit: float):
        self.deposit_mapping = deposit_mapping
        self.min_incoming_deposit = min_incoming_deposit

    def filter(self, a: NodeConnectionData, b: NodeConnectionData):
        deposit_a = self.deposit_mapping(a[0].fullness)
        deposit_b = self.deposit_mapping(b[0].fullness)
        return deposit_a >= self.min_incoming_deposit * deposit_b


class IncomingLimitsFilterStrategy(FilterStrategy):
    def __init__(self, max_incoming_channels_mapping: Callable[[Fullness], int]):
        self.max_incoming_channels_mapping = max_incoming_channels_mapping

    def filter(self, a: NodeConnectionData, b: NodeConnectionData):
        max_incoming_channels = self.max_incoming_channels_mapping(b[0].fullness)
        return b[1]['num_incoming_channels'] < max_incoming_channels


class AcceptedLimitsFilterStrategy(FilterStrategy):
    def __init__(self, max_accepted_channels_mapping: Callable[[Fullness], int]):
        self.max_accepted_channels_mapping = max_accepted_channels_mapping

    def filter(self, a: NodeConnectionData, b: NodeConnectionData):
        max_accepted_channels = self.max_accepted_channels_mapping(b[0].fullness)
        return b[1]['num_accepted_channels'] < max_accepted_channels


class TotalLimitsFilterStrategy(FilterStrategy):
    def __init__(self, max_total_channels_mapping: Callable[[Fullness], int]):
        self.max_total_channels_mapping = max_total_channels_mapping

    def filter(self, a: NodeConnectionData, b: NodeConnectionData):
        max_total_channels = self.max_total_channels_mapping(b[0].fullness)
        num_incoming_channels = b[1]['num_incoming_channels']
        num_outgoing_channels = b[1]['num_outgoing_channels']
        return num_incoming_channels + num_outgoing_channels < max_total_channels


class MicroRaidenServerFilterStrategy(FilterStrategy):
    def filter(self, a: NodeConnectionData, b: NodeConnectionData):
        return b[0].fullness > 0
