from itertools import cycle
from typing import Callable

import math

from raidensim.network.node import Node
from raidensim.network.raw_network import RawNetwork
from raidensim.strategy.position_strategy import PositionStrategy
from raidensim.types import Fullness, IntRange


class FilterStrategy(object):
    """
    Strategy pattern used to reject/filter connections between certain nodes.
    """

    def filter(self, raw: RawNetwork, a: Node, b: Node) -> bool:
        raise NotImplementedError


class IdentityFilterStrategy(FilterStrategy):
    """
    Disallows connections from a node to itself.
    """

    def filter(self, raw: RawNetwork, a: Node, b: Node):
        return a != b


class NotConnectedFilterStrategy(FilterStrategy):
    """
    Disallows multiple connections between two nodes.
    """

    def filter(self, raw: RawNetwork, a: Node, b: Node):
        return not raw.has_edge(a, b)


class DistanceFilterStrategy(FilterStrategy):
    """
    Disallows connections above a certain network distance.
    """

    def __init__(self, position_strategy: PositionStrategy, max_distance: int):
        self.position_strategy = position_strategy
        self.max_distance = max_distance

    def filter(self, raw: RawNetwork, a: Node, b: Node):
        return self.position_strategy.distance(a, b) <= self.max_distance


class FullerFilterStrategy(FilterStrategy):
    """
    Disallows connections to emptier nodes (but not from emptier nodes).
    """

    def filter(self, raw: RawNetwork, a: Node, b: Node):
        return a.fullness <= b.fullness


class MinIncomingDepositFilterStrategy(FilterStrategy):
    """
    Disallows connections where the initiating node's deposit is below the accepting node's
    threshold. This threshold is a fixed fraction of the accepting node's own deposit.
    """

    def __init__(self, deposit_mapping: Callable[[Fullness], float], min_incoming_deposit: float):
        self.deposit_mapping = deposit_mapping
        self.min_incoming_deposit = min_incoming_deposit

    def filter(self, raw: RawNetwork, a: Node, b: Node):
        deposit_a = self.deposit_mapping(a.fullness)
        deposit_b = self.deposit_mapping(b.fullness)
        return deposit_a >= self.min_incoming_deposit * deposit_b


class MinMutualDepositFilterStrategy(FilterStrategy):
    """
    Disallows connections where either of the nodes' deposits is below the other node's threshold.
    This threshold is a fixed fraction of the other node's own deposit.
    """

    def __init__(self, deposit_mapping: Callable[[Fullness], float], min_deposit: float):
        self.deposit_mapping = deposit_mapping
        self.min_incoming_deposit = min_deposit

    def filter(self, raw: RawNetwork, a: Node, b: Node):
        deposit_a = self.deposit_mapping(a.fullness)
        deposit_b = self.deposit_mapping(b.fullness)
        return deposit_a >= self.min_incoming_deposit * deposit_b and \
            deposit_b >= self.min_incoming_deposit * deposit_a


class IncomingLimitsFilterStrategy(FilterStrategy):
    """
    Only allows up to a certain number of incoming unidirectional channels.
    Note: This is not the same as accepted channels. Initiating a bidirectional channel also
    creates an incoming channel for the initiating node.
    """

    def __init__(self, max_incoming_channels_mapping: Callable[[Fullness], int]):
        self.max_incoming_channels_mapping = max_incoming_channels_mapping

    def filter(self, raw: RawNetwork, a: Node, b: Node):
        max_incoming_channels = self.max_incoming_channels_mapping(b.fullness)
        return b['num_incoming_channels'] < max_incoming_channels


class AcceptedLimitsFilterStrategy(FilterStrategy):
    """
    Only allows up to a certain number of accepted channels.
    """

    def __init__(self, max_accepted_channels_mapping: Callable[[Fullness], int]):
        self.max_accepted_channels_mapping = max_accepted_channels_mapping

    def filter(self, raw: RawNetwork, a: Node, b: Node):
        max_accepted_channels = self.max_accepted_channels_mapping(b.fullness)
        return b['num_accepted_channels'] < max_accepted_channels


class TotalLimitsFilterStrategy(FilterStrategy):
    """
    Only allows a total number of incoming and outgoing channels for a node, regardless of
    initiator. Each direction counts as a single channel.
    """

    def __init__(self, max_total_channels_mapping: Callable[[Fullness], int]):
        self.max_total_channels_mapping = max_total_channels_mapping

    def filter(self, raw: RawNetwork, a: Node, b: Node):
        a_max_total_channels = self.max_total_channels_mapping(a.fullness)
        b_max_total_channels = self.max_total_channels_mapping(b.fullness)
        return a['num_incoming_channels'] + a['num_outgoing_channels'] < a_max_total_channels and \
               b['num_incoming_channels'] + b['num_outgoing_channels'] < b_max_total_channels


class TotalBidirectionalLimitsFilterStrategy(TotalLimitsFilterStrategy):
    """
    Only allows a total number of bidirectional channels for a node, regardless of initiator. This
    is the same as a unidirectional total limit filter, except that one bidirectional channel
    counts as both an incoming and and outgoing channel.
    """
    def __init__(self, max_total_channels_mapping: Callable[[Fullness], int]):
        TotalLimitsFilterStrategy.__init__(
            self,
            lambda fullness: max_total_channels_mapping(fullness) * 2
        )


class ThresholdFilterStrategy(FilterStrategy):
    """
    Disallows connections between an emptier and a fuller node if their distance is less than the
    emptier node's threshold or greater than the fuller node's threshold.

    This results in a topology where each hop knows whether to proceed downward (to emptier nodes)
    or upward (to fuller nodes). If the target lies within the threshold, hop downward. Else, hop
    upward.

    For example, light clients with just a single channel should have a threshold of 0, only
    connecting upward to fuller nodes.

    Note: This strategy has turned out to be really bad.
    """

    def __init__(self, threshold_mapping: Callable[[Fullness], int]):
        self.threshold_mapping = threshold_mapping

    def filter(self, raw: RawNetwork, a: Node, b: Node):
        emptier, fuller = sorted([a, b], key=lambda u: u.fullness)
        threshold_fuller = self.threshold_mapping(fuller.fullness)
        threshold_emptier = self.threshold_mapping(emptier.fullness)
        distance = fuller.ring_distance(emptier)
        return threshold_emptier < distance < threshold_fuller


class KademliaFilterStrategy(FilterStrategy):
    """
    Attempts to translate the Kademlia network layout into a filter that can be used in a random
    selection strategy.

    Partner nodes are sorted into buckets of exponential distance. Bucket i holds all nodes
    from distance 2**(i-1) to distance 2**i inclusive.

    Buckets can be limited. The lower limit merges all buckets up to that bucket index into a
    single bucket. This prevents buckets of too small a size that are highly unlikely of ever being
    filled. The upper limit skips buckets above a certain index.

    Example: limits (3, 7) will sort nodes in the following buckets:
    (0, 16), [16, 32), [32, 64), [64, 128)

    When connecting to a new node, this new node must fall into the first emptiest bucket.
    """

    def __init__(self, position_strategy: PositionStrategy, bucket_limits: IntRange):
        self.position_strategy = position_strategy
        self.num_buckets_merged = bucket_limits[0]
        self.num_buckets = bucket_limits[1] - bucket_limits[0]

    def _get_bucket(self, a: Node, b: Node) -> int:
        distance = self.position_strategy.distance(a, b)
        return max(0, int(math.log2(distance)) - self.num_buckets_merged)

    def filter(self, raw: RawNetwork, a: Node, b: Node):
        buckets = [0] * self.num_buckets
        target_bucket = self._get_bucket(a, b)
        for partner in raw.neighbors(a):
            buckets[self._get_bucket(a, partner)] += 1
        _, first_emptiest_bucket = min((buckets[i], i) for i in range(self.num_buckets))
        return target_bucket == first_emptiest_bucket


class MicroRaidenServerFilterStrategy(FilterStrategy):
    """
    Allows nodes to only connect to server nodes (fullness > 0).
    """

    def filter(self, raw: RawNetwork, a: Node, b: Node):
        return b.fullness > 0
