from raidensim.network.node import Node

from raidensim.routing.next_hop_routing_model import NextHopRoutingModel, PriorityModel
from raidensim.util import sigmoid


class DistancePriorityModel(PriorityModel):
    """
    Prioritizes hops according to their (normalized) distance to the target node.
    """
    def priority(
            self, cn, source: Node, u: Node, v: Node, e: dict, target: Node, value: int
    ) -> float:
        """
        Normalized distance between new node and target node.
        distance == 0 => same node
        distance == 1 => 180 degrees
        """
        return cn.ring_distance(v, target) / cn.MAX_ID * 2


class DistanceNetBalancePriorityModel(PriorityModel):
    """
    Prioritizes hops equally according to their distance to the target node and their channel net
    balance. A high net balance causes higher fees due to the added imbalance.
    """
    def priority(
            self, cn, source: Node, u: Node, v: Node, e: dict, target: Node, value: int
    ) -> float:
        distance = cn.ring_distance(v, target) / cn.MAX_ID * 2
        fee = sigmoid(e['net_balance'] + value)
        return distance * fee


class GloballyAssistedPriorityModel(PriorityModel):
    """
    This considers both distance and net balance fees but prioritizes nodes additionally using
    globally available network topology. Global routing is also performed using distance-based
    next-hop routing since it probably scales better than Dijkstra.

    Goal: avoid contacting nodes that may be closer but are not properly connected to the
    target node.

    This routing model requires a full view of all open channels and in practice is not suited
    for light clients.
    """
    def __init__(self):
        # Nested next-hop routing based on global information. Used with transfer value 0.
        self.global_routing = NextHopRoutingModel(DistancePriorityModel())

    def priority(
            self, cn, source: Node, u: Node, v: Node, e: dict, target: Node, value: int
    ) -> float:
        path, _ = self.global_routing.route(v, target, 0)
        num_hops = len(path)
        distance = cn.ring_distance(v, target) / cn.MAX_ID * 2
        fee = sigmoid(e['net_balance'] + value)
        return distance * fee * num_hops
