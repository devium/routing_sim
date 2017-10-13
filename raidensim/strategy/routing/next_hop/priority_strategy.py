from typing import Tuple, Union

from raidensim.network.node import Node
from raidensim.network.raw_network import RawNetwork
from raidensim.strategy.fee_strategy import FeeStrategy
from raidensim.strategy.position_strategy import PositionStrategy


class PriorityStrategy(object):
    def priority(
            self,
            raw: RawNetwork,
            source: Node,
            u: Node,
            v: Node,
            e: dict,
            target: Node,
            value: int
    ):
        raise NotImplementedError


class DistancePriorityStrategy(PriorityStrategy):
    """
    Prioritizes hops according to their distance to the target node.
    """
    def __init__(self, position_strategy: PositionStrategy):
        self.position_strategy = position_strategy

    def priority(
            self,
            raw: RawNetwork,
            source: Node,
            u: Node,
            v: Node,
            e: dict,
            target: Node,
            value: int
    ):
        return self.position_strategy.distance(v, target)


class DistanceFeePriorityStrategy(PriorityStrategy):
    """
    Prioritizes hops according to their distance to the target node and their channel net balance.
    A high net balance causes higher fees due to the added imbalance.
    Hops that increase distance are only prioritized if no other are available, i.e., low fees
    cannot incentivize hopping backward.
    """
    def __init__(
            self,
            position_strategy: PositionStrategy,
            fee_strategy: FeeStrategy,
            weights: Tuple[float, float]=(1,1)
    ):
        self.position_strategy = position_strategy
        self.fee_strategy = fee_strategy
        self.weights = weights

    def priority(
            self,
            raw: RawNetwork,
            source: Node,
            u: Node,
            v: Node,
            e: dict,
            target: Node,
            value: int
    ):
        current_distance = self.position_strategy.distance(u, target)
        new_distance = self.position_strategy.distance(v, target)

        if new_distance > current_distance:
            distance_penalty = 1
        else:
            distance_penalty = 0

        fee = self.fee_strategy.get_fee(u, v, e, value)
        return distance_penalty, new_distance ** self.weights[0] * fee ** self.weights[1]
