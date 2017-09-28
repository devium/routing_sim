from typing import Callable

from raidensim.strategy.strategy import FilterStrategy, NodeConnectionData
from raidensim.types import Fullness


class IdentityFilterStrategy(FilterStrategy):
    """
    Disallows connections from a node to itself.
    """
    def filter(self, a: NodeConnectionData, b: NodeConnectionData):
        return a[0] != b[0]


class NotConnectedFilterStrategy(FilterStrategy):
    """
    Disallows multiple connections between two nodes.
    """
    def filter(self, a: NodeConnectionData, b: NodeConnectionData):
        return b[0] not in a[0].cn[a[0]]


class DistanceFilterStrategy(FilterStrategy):
    """
    Disallows connections above a certain network distance.
    """
    def __init__(self, max_network_distance: float):
        self.max_network_distance = max_network_distance

    def filter(self, a: NodeConnectionData, b: NodeConnectionData):
        return a[0].ring_distance(b[0]) <= int(self.max_network_distance * a[0].cn.MAX_ID)


class FullerFilterStrategy(FilterStrategy):
    """
    Disallows connections to emptier nodes (but not from emptier nodes).
    """
    def filter(self, a: NodeConnectionData, b: NodeConnectionData):
        return a[0].fullness <= b[0].fullness


class MinIncomingDepositFilterStrategy(FilterStrategy):
    """
    Disallows connections where the initiating node's deposit is below the accepting node's
    threshold.
    """
    def __init__(self, deposit_mapping: Callable[[Fullness], float], min_incoming_deposit: float):
        self.deposit_mapping = deposit_mapping
        self.min_incoming_deposit = min_incoming_deposit

    def filter(self, a: NodeConnectionData, b: NodeConnectionData):
        deposit_a = self.deposit_mapping(a[0].fullness)
        deposit_b = self.deposit_mapping(b[0].fullness)
        return deposit_a >= self.min_incoming_deposit * deposit_b


class IncomingLimitsFilterStrategy(FilterStrategy):
    """
    Only allows up to a certain number of incoming unidirectional channels.
    Note: This is not the same as accepted channels. Initiating a bidirectional channel also
    creates an incoming channel for the initiating node.
    """
    def __init__(self, max_incoming_channels_mapping: Callable[[Fullness], int]):
        self.max_incoming_channels_mapping = max_incoming_channels_mapping

    def filter(self, a: NodeConnectionData, b: NodeConnectionData):
        max_incoming_channels = self.max_incoming_channels_mapping(b[0].fullness)
        return b[1]['num_incoming_channels'] < max_incoming_channels


class AcceptedLimitsFilterStrategy(FilterStrategy):
    """
    Only allows up to a certain number of accepted channels.
    """
    def __init__(self, max_accepted_channels_mapping: Callable[[Fullness], int]):
        self.max_accepted_channels_mapping = max_accepted_channels_mapping

    def filter(self, a: NodeConnectionData, b: NodeConnectionData):
        max_accepted_channels = self.max_accepted_channels_mapping(b[0].fullness)
        return b[1]['num_accepted_channels'] < max_accepted_channels


class TotalLimitsFilterStrategy(FilterStrategy):
    """
    Only allows a total number of incoming and outgoing channels for a node, regardless of
    initiator.
    """
    def __init__(self, max_total_channels_mapping: Callable[[Fullness], int]):
        self.max_total_channels_mapping = max_total_channels_mapping

    def filter(self, a: NodeConnectionData, b: NodeConnectionData):
        max_total_channels = self.max_total_channels_mapping(b[0].fullness)
        num_incoming_channels = b[1]['num_incoming_channels']
        num_outgoing_channels = b[1]['num_outgoing_channels']
        return num_incoming_channels + num_outgoing_channels < max_total_channels


class ThresholdFilterStrategy(FilterStrategy):
    """
    Disallows connections between an emptier and a fuller node if their distance is less than the
    emptier node's threshold or greater than the fuller node's threshold.

    This results in a topology where each hop knows whether to proceed downward (to emptier nodes)
    or upward (to fuller nodes). If the target lies within the threshold, hop downward. Else, hop
    upward.

    For example, light clients with just a single channel should have a threshold of 0, only
    connecting upward to fuller nodes.

    The threshold is relative to the network size, e.g. 1/8 or 1/10, etc.

    Note: This strategy has turned out to be really bad.
    """
    def __init__(self, threshold_mapping: Callable[[Fullness], int]):
        self.threshold_mapping = threshold_mapping

    def filter(self, a: NodeConnectionData, b: NodeConnectionData):
        emptier, fuller = sorted([a[0], b[0]], key=lambda u: u.fullness)
        threshold_fuller = self.threshold_mapping(fuller.fullness) * fuller.cn.MAX_ID
        threshold_emptier = self.threshold_mapping(emptier.fullness) * fuller.cn.MAX_ID
        distance = fuller.ring_distance(emptier)
        return threshold_emptier < distance < threshold_fuller


class MicroRaidenServerFilterStrategy(FilterStrategy):
    """
    Allows nodes to only connect to server nodes (fullness > 0).
    """
    def filter(self, a: NodeConnectionData, b: NodeConnectionData):
        return b[0].fullness > 0
