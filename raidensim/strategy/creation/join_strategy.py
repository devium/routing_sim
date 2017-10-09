import random
from typing import Callable

from raidensim.network.lattice import Lattice
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
    TotalLimitsFilterStrategy, TotalBidirectionalLimitsFilterStrategy)
from raidensim.strategy.position_strategy import PositionStrategy, RingPositionStrategy
from .connection_strategy import ConnectionStrategy, BidirectionalConnectionStrategy, \
    LatticeConnectionStrategy
from .selection_strategy import (
    SelectionStrategy,
    KademliaSelectionStrategy,
    RandomSelectionStrategy,
    RandomExcludingSelectionStrategy)
from raidensim.types import Fullness, IntRange


def linear_int(min_: int, max_: int, fullness: float) -> int:
    return int((max_ - min_) * fullness + min_)


def linear_float(min_: float, max_: float, fullness: float) -> float:
    return (max_ - min_) * fullness + min_


class JoinStrategy(object):
    def join(self, raw: RawNetwork, node: Node):
        raise NotImplementedError


class DefaultJoinStrategy(JoinStrategy):
    def __init__(
            self,
            initiated_channels_mapping: Callable[[Fullness], int],
            selection_strategy: SelectionStrategy,
            connection_strategy: ConnectionStrategy,
            position_strategy: PositionStrategy
    ):
        self.initiated_channels_mapping = initiated_channels_mapping
        self.selection_strategy = selection_strategy
        self.connection_strategy = connection_strategy
        self.position_strategy = position_strategy

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
            print('Out of suitable nodes for {}. {}/{} connections unfulfilled'.format(
                node,
                max_initiated_channels - node['num_initiated_channels'],
                max_initiated_channels
            ))


class SimpleJoinStrategy(DefaultJoinStrategy):
    def __init__(
            self,
            max_id: int,
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
            selection_strategy=RandomSelectionStrategy(filter_strategies=filter_strategies),
            connection_strategy=BidirectionalConnectionStrategy(deposit_mapping),
            position_strategy=RingPositionStrategy(max_id)
        )


class RaidenRingJoinStrategy(DefaultJoinStrategy):
    def __init__(
            self,
            max_id: int,
            min_partner_deposit: float,
            position_strategy: PositionStrategy,
            max_distance: int,
            kademlia_skip: int,
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

        filter_strategies = [
            IdentityFilterStrategy(),
            NotConnectedFilterStrategy(),
            DistanceFilterStrategy(position_strategy, max_distance),
            FullerFilterStrategy(),
            AcceptedLimitsFilterStrategy(accepted_channels_mapping),
            MinIncomingDepositFilterStrategy(deposit_mapping, min_partner_deposit)
        ]

        selection_strategy = KademliaSelectionStrategy(
            max_id=max_id,
            max_distance=max_distance,
            skip=kademlia_skip,
            filter_strategies=filter_strategies
        )

        # selection_strategy = RandomSelectionStrategy(filter_strategies=filter_strategies)

        DefaultJoinStrategy.__init__(
            self,
            initiated_channels_mapping=initiated_channels_mapping,
            selection_strategy=selection_strategy,
            connection_strategy=BidirectionalConnectionStrategy(deposit_mapping),
            position_strategy=position_strategy
        )


class MicroRaidenJoinStrategy(DefaultJoinStrategy):
    def __init__(
            self,
            max_id: int,
            max_initiated_channels: IntRange,
            deposit: int
    ):
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

        selection_strategy = RandomSelectionStrategy(
            filter_strategies=filter_strategies
        )

        DefaultJoinStrategy.__init__(
            self,
            initiated_channels_mapping=initiated_channels_mapping,
            selection_strategy=selection_strategy,
            connection_strategy=BidirectionalConnectionStrategy(deposit_mapping),
            position_strategy=RingPositionStrategy(max_id)
        )


class RaidenLatticeJoinStrategy(JoinStrategy):
    def __init__(self, lattice: Lattice, num_shortcut_channels: IntRange, deposit: IntRange):
        self.lattice = lattice

        def deposit_mapping(fullness: Fullness):
            return linear_int(*deposit, fullness)

        def shortcut_mapping(fullness: Fullness):
            return linear_int(*num_shortcut_channels, fullness)

        filter_strategies = [
            IdentityFilterStrategy(),
            NotConnectedFilterStrategy(),
            TotalBidirectionalLimitsFilterStrategy(shortcut_mapping)
        ]

        def exclusion_criterion(raw: RawNetwork, node: Node):
            max_channels = shortcut_mapping(node.fullness) * 2
            return node['num_incoming_channels'] + node['num_outgoing_channels'] >= max_channels

        self.shortcut_mapping = shortcut_mapping
        self.selection_strategy = RandomExcludingSelectionStrategy(
            filter_strategies=filter_strategies,
            exclusion_criteria=[exclusion_criterion]
        )
        self.connection_strategy = BidirectionalConnectionStrategy(deposit_mapping)
        self.lattice_connection_strategy = LatticeConnectionStrategy(deposit_mapping)

    def join(self, raw: RawNetwork, node: Node):
        coord = self.lattice.get_free_coord()
        self.lattice.add_node(node, *coord)
        neighbors = list(self.lattice.coord_neighbors(*coord))
        neighbors = [neighbor for neighbor in neighbors if (node, neighbor) not in raw.edges]
        for partner in neighbors:
            self.lattice_connection_strategy.connect(raw, node, partner)
        try:
            for i in range(self.shortcut_mapping(node.fullness)):
                partner = next(self.selection_strategy.targets(raw, node))
                self.connection_strategy.connect(raw, node, partner)
        except StopIteration:
            pass
