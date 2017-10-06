from itertools import cycle
from typing import Callable

import math

from raidensim.network.node import Node
from raidensim.network.raw_network import RawNetwork
from raidensim.strategy.position_strategy import PositionStrategy
from raidensim.types import Fullness


class FilterStrategy(object):
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
        return b not in raw[a]


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
    threshold.
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
    Disallows connections where the initiating node's deposit is below the accepting node's
    threshold.
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
    initiator.
    """

    def __init__(self, max_total_channels_mapping: Callable[[Fullness], int]):
        self.max_total_channels_mapping = max_total_channels_mapping

    def filter(self, raw: RawNetwork, a: Node, b: Node):
        max_total_channels = self.max_total_channels_mapping(b.fullness)
        num_incoming_channels = b['num_incoming_channels']
        num_outgoing_channels = b['num_outgoing_channels']
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
    Attempts to translate the KademliaSelectionStrategy into a filter, so a random selection
    strategy with a Kademlia filter results in approximately the same network as a Kademlia
    selection strategy.
    """

    def __init__(
            self, position_strategy: PositionStrategy, max_distance: int, skip: int, tolerance: int
    ):
        self.position_strategy = position_strategy
        targets_per_cycle = int(math.log(max_distance, 2)) + 1
        distances = [int(2 ** i) for i in range(skip, targets_per_cycle)]
        self.buckets = [(max(0, d - tolerance), d + tolerance) for d in distances]

    def filter(self, raw: RawNetwork, a: Node, b: Node):
        """
        Preserve the following properties:
        - Kademlia produces target IDs at exponentially increasing distances.
        - Nodes have to be within a certain tolerance of these distances, aka bucket.
        - Insertion order into the buckets follows distance, cycling.
        - Valid example buckets: [2,1,1,1], [1,1,1,0]
        - Invalid example buckets: [0,0,1,0], although this might happen if nodes go offline.
        - Leaky buckets (as invalid example above) have to be refilled from closest to furthest.
        => New nodes have to be in the left-most bucket with minimum amount of nodes.
        """
        # Cycle through buckets and assign partners to them. The first bucket running out of valid
        # partners will be the new target bucket.
        partner_distances = sorted(
            (self.position_strategy.distance(a, partner), i) for i, partner in enumerate(raw[a])
        )
        bucket = None
        try:
            for bucket in cycle(self.buckets):
                i = next(
                    i for i, (distance, _) in enumerate(partner_distances)
                    if bucket[0] <= distance < bucket[1]
                )
                del partner_distances[i]
        except StopIteration:
            pass
        return bucket[0] <= self.position_strategy.distance(a, b) < bucket[1]


class MicroRaidenServerFilterStrategy(FilterStrategy):
    """
    Allows nodes to only connect to server nodes (fullness > 0).
    """

    def filter(self, raw: RawNetwork, a: Node, b: Node):
        return b.fullness > 0
