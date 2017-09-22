import random

from raidensim.strategy.connection_strategies import BidirectionalConnectionStrategy
from raidensim.strategy.filter_strategies import (
    IdentityFilterStrategy,
    DistanceFilterStrategy,
    FullerFilterStrategy,
    MinIncomingDepositFilterStrategy,
    MicroRaidenServerFilterStrategy, NotConnectedFilterStrategy)
from raidensim.strategy.selection_strategies import KademliaSelectionStrategy, \
    RandomSelectionStrategy
from raidensim.strategy.strategy import NetworkStrategy
from raidensim.types import Fullness, Range


class SimpleNetworkStrategy(NetworkStrategy):
    def __init__(
            self,
            max_initiated_channels: Range,
            deposit: Range
    ):
        def initiated_channels_mapping(fullness: Fullness):
            return self._linear(*max_initiated_channels, fullness)

        def deposit_mapping(fullness: Fullness):
            return self._linear(*deposit, fullness)

        filter_strategies = [
            IdentityFilterStrategy(),
            NotConnectedFilterStrategy()
        ]

        NetworkStrategy.__init__(
            self,
            initiated_channels_mapping=initiated_channels_mapping,
            selection_strategy=RandomSelectionStrategy(filter_strategies),
            connection_strategy=BidirectionalConnectionStrategy(deposit_mapping)
        )

    @staticmethod
    def _linear(min_: int, max_: int, fullness: float):
        return int((max_ - min_) * fullness + min_)


class RaidenNetworkStrategy(NetworkStrategy):
    def __init__(
            self,
            min_incoming_deposit: float,
            max_network_distance: float,
            max_initiated_channels: Range,
            deposit: Range

    ):
        def initiated_channels_mapping(fullness: Fullness):
            return self._linear(*max_initiated_channels, fullness)

        def deposit_mapping(fullness: Fullness):
            return self._linear(*deposit, fullness)

        filter_strategies = [
            IdentityFilterStrategy(),
            NotConnectedFilterStrategy(),
            DistanceFilterStrategy(max_network_distance),
            FullerFilterStrategy(),
            MinIncomingDepositFilterStrategy(deposit_mapping, min_incoming_deposit)
        ]

        selection_strategy = KademliaSelectionStrategy(
            max_network_distance=max_network_distance,
            filter_strategies=filter_strategies
        )

        NetworkStrategy.__init__(
            self,
            initiated_channels_mapping=initiated_channels_mapping,
            selection_strategy=selection_strategy,
            connection_strategy=BidirectionalConnectionStrategy(deposit_mapping)
        )

    @staticmethod
    def _linear(min_: int, max_: int, fullness: float):
        return int((max_ - min_) * fullness + min_)


class MicroRaidenNetworkStrategy(NetworkStrategy):
    def __init__(
            self,
            max_initiated_channels: Range,
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

        NetworkStrategy.__init__(
            self,
            initiated_channels_mapping=initiated_channels_mapping,
            selection_strategy=selection_strategy,
            connection_strategy=BidirectionalConnectionStrategy(deposit_mapping)
        )
