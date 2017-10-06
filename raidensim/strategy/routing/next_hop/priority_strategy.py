from raidensim.network.node import Node
from raidensim.network.raw_network import RawNetwork
from raidensim.strategy.position_strategy import PositionStrategy
from raidensim.util import sigmoid


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
    ) -> float:
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
    ) -> float:
        return self.position_strategy.distance(v, target)


class DistanceNetBalancePriorityStrategy(PriorityStrategy):
    """
    Prioritizes hops equally according to their distance to the target node and their channel net
    balance. A high net balance causes higher fees due to the added imbalance.
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
    ) -> float:
        distance = self.position_strategy.distance(v, target)
        fee = sigmoid(e['net_balance'] + value)
        return distance * fee


