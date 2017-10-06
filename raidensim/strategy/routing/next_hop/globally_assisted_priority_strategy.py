from raidensim.network.node import Node
from raidensim.network.raw_network import RawNetwork
from raidensim.strategy.position_strategy import PositionStrategy
from raidensim.strategy.routing.next_hop.next_hop_routing_strategy import NextHopRoutingStrategy
from raidensim.strategy.routing.next_hop.priority_strategy import (
    PriorityStrategy,
    DistancePriorityStrategy
)
from raidensim.util import sigmoid


class GloballyAssistedPriorityStrategy(PriorityStrategy):
    """
    This considers both distance and net balance fees but prioritizes nodes additionally using
    globally available network topology. Global routing is also performed using distance-based
    next-hop routing since it probably scales better than Dijkstra.

    Goal: avoid contacting nodes that may be closer but are not properly connected to the
    target node.

    This routing model requires a full view of all open channels and in practice is not suited
    for light clients.
    """
    def __init__(self, position_strategy: PositionStrategy):
        self.position_strategy = position_strategy
        # Nested next-hop routing based on global information. Used with transfer value 0.
        self.global_routing = NextHopRoutingStrategy(DistancePriorityStrategy(position_strategy))

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
        path, _ = self.global_routing.route(raw, v, target, 0)
        num_hops = len(path)
        distance = self.position_strategy.distance(v, target)
        fee = sigmoid(e['net_balance'] + value)
        return distance * fee * num_hops
