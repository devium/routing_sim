import random
from typing import Callable

from raidensim.network.lattice import WovenLattice
from raidensim.network.node import Node
from raidensim.network.raw_network import RawNetwork
from raidensim.strategy.creation.filter_strategy import (
    IdentityFilterStrategy,
    NotConnectedFilterStrategy,
    MicroRaidenServerFilterStrategy,
    DistanceFilterStrategy,
    FullerFilterStrategy,
    AcceptedLimitsFilterStrategy,
    MinIncomingDepositFilterStrategy,
    TotalBidirectionalLimitsFilterStrategy,
    KademliaFilterStrategy)
from raidensim.strategy.position_strategy import RingPositionStrategy
from .connection_strategy import (
    ConnectionStrategy,
    BidirectionalConnectionStrategy,
    LatticeConnectionStrategy
)
from .selection_strategy import (
    SelectionStrategy,
    FirstMatchSelectionStrategy,
    RandomAuxLatticeSelectionStrategy,
    RandomSelectionStrategy)
from raidensim.types import Fullness, IntRange


def linear_int(min_: int, max_: int, fullness: float) -> int:
    return int((max_ - min_) * fullness + min_)


def linear_float(min_: float, max_: float, fullness: float) -> float:
    return (max_ - min_) * fullness + min_


class JoinStrategy(object):
    """
    Strategy pattern to define how a new node should join an existing network, i.e., target
    selection, preconditions, and connection type.
    """

    def join(self, raw: RawNetwork, node: Node):
        raise NotImplementedError

    @property
    def num_required_channels(self):
        raise NotImplementedError


class DefaultJoinStrategy(JoinStrategy):
    """
    Joins nodes by attempting to initiate a number of channels relative to their fullness.
    Targets and connection type are determined by external strategies.
    """
    def __init__(
            self,
            initiated_channels_mapping: Callable[[Fullness], int],
            selection_strategy: SelectionStrategy,
            connection_strategy: ConnectionStrategy
    ):
        self.initiated_channels_mapping = initiated_channels_mapping
        self.selection_strategy = selection_strategy
        self.connection_strategy = connection_strategy

    def join(self, raw: RawNetwork, node: Node):
        max_initiated_channels = self.initiated_channels_mapping(node.fullness)
        targets = None
        if node['num_initiated_channels'] < max_initiated_channels:
            targets = self.selection_strategy.targets(raw, node)

        try:
            while node['num_initiated_channels'] < max_initiated_channels:
                target = next(targets)
                self.connection_strategy.connect(raw, node, target)
        except StopIteration:
            pass

    @property
    def num_required_channels(self):
        return 0


class SimpleJoinStrategy(DefaultJoinStrategy):
    """
    Randomly and bidirectionally connects nodes using a linear mapping from fullness to the number
    of initiated channels per node and the size of its deposit.
    """
    def __init__(
            self,
            max_initiated_channels: IntRange,
            deposit: IntRange
    ):
        def initiated_channels_mapping(fullness: Fullness):
            return linear_int(*max_initiated_channels, fullness)

        def deposit_mapping(fullness: Fullness):
            return linear_int(*deposit, fullness)

        filter_strategies = [
            IdentityFilterStrategy(),
            NotConnectedFilterStrategy()
        ]

        DefaultJoinStrategy.__init__(
            self,
            initiated_channels_mapping=initiated_channels_mapping,
            selection_strategy=FirstMatchSelectionStrategy(filter_strategies=filter_strategies),
            connection_strategy=BidirectionalConnectionStrategy(deposit_mapping)
        )


class RaidenKademliaJoinStrategy(DefaultJoinStrategy):
    """
    Builds a Kademlia-like network over nodes positioned by their ID on a ring.
    """
    def __init__(
            self,
            max_id: int,
            min_partner_deposit: float,
            kademlia_bucket_limits: IntRange,
            max_initiated_channels: IntRange,
            max_accepted_channels: IntRange,
            deposit: IntRange
    ):
        def initiated_channels_mapping(fullness: Fullness):
            return linear_int(*max_initiated_channels, fullness)

        def accepted_channels_mapping(fullness: Fullness):
            return linear_int(*max_accepted_channels, fullness)

        def deposit_mapping(fullness: Fullness):
            return linear_int(*deposit, fullness)

        position_strategy = RingPositionStrategy(max_id)

        filter_strategies = [
            IdentityFilterStrategy(),
            NotConnectedFilterStrategy(),
            KademliaFilterStrategy(position_strategy, kademlia_bucket_limits),
            FullerFilterStrategy(),
            AcceptedLimitsFilterStrategy(accepted_channels_mapping),
            MinIncomingDepositFilterStrategy(deposit_mapping, min_partner_deposit)
        ]

        selection_strategy = FirstMatchSelectionStrategy(filter_strategies=filter_strategies)

        DefaultJoinStrategy.__init__(
            self,
            initiated_channels_mapping=initiated_channels_mapping,
            selection_strategy=selection_strategy,
            connection_strategy=BidirectionalConnectionStrategy(deposit_mapping)
        )


class MicroRaidenJoinStrategy(DefaultJoinStrategy):
    """
    Joins nodes using unidirectional channels positioned on a ring. All channels have equal
    deposits and only client nodes (fullness == 0) initiate random amounts of channels.
    """

    def __init__(self, max_initiated_channels: IntRange, deposit: int):
        def initiated_channels_mapping(fullness: Fullness):
            if fullness == 0:
                return random.randint(*max_initiated_channels)
            else:
                return 0

        def deposit_mapping(fullness: Fullness):
            return deposit

        filter_strategies = [
            IdentityFilterStrategy(),
            NotConnectedFilterStrategy(),
            MicroRaidenServerFilterStrategy()
        ]

        selection_strategy = RandomSelectionStrategy(filter_strategies=filter_strategies)

        DefaultJoinStrategy.__init__(
            self,
            initiated_channels_mapping=initiated_channels_mapping,
            selection_strategy=selection_strategy,
            connection_strategy=BidirectionalConnectionStrategy(deposit_mapping)
        )


class RaidenLatticeJoinStrategy(DefaultJoinStrategy):
    """
    Joins nodes in a regular lattice, independent of their UID. Lattice channels are mandatory but
    auxiliary long-distance channels are dependent on the node's fullness.
    """

    def __init__(
            self,
            lattice: WovenLattice,
            max_initiated_aux_channels: IntRange,
            max_accepted_aux_channels: IntRange,
            deposit: IntRange
    ):
        self.lattice = lattice

        def initiated_channels_mapping(fullness: Fullness):
            return linear_int(*max_initiated_aux_channels, fullness)

        def accepted_channels_mapping(fullness: Fullness):
            return linear_int(*max_accepted_aux_channels, fullness)

        def deposit_mapping(fullness: Fullness):
            return linear_int(*deposit, fullness)

        self.lattice_connection_strategy = LatticeConnectionStrategy(deposit_mapping)

        filter_strategies = [
            AcceptedLimitsFilterStrategy(accepted_channels_mapping)
        ]

        selection_strategy = RandomAuxLatticeSelectionStrategy(self.lattice, filter_strategies)

        DefaultJoinStrategy.__init__(
            self,
            initiated_channels_mapping=initiated_channels_mapping,
            selection_strategy=selection_strategy,
            connection_strategy=BidirectionalConnectionStrategy(deposit_mapping)
        )

    def join(self, raw: RawNetwork, node: Node):
        coord = self.lattice.get_free_coord()
        self.lattice.add_node(node, coord)

        neighbors = list(self.lattice.coord_neighbors(coord))
        neighbors = [neighbor for neighbor in neighbors if (node, neighbor) not in raw.edges]
        for partner in neighbors:
            self.lattice_connection_strategy.connect(raw, node, partner)

        DefaultJoinStrategy.join(self, raw, node)

    @property
    def num_required_channels(self):
        return self.lattice.num_required_channels
