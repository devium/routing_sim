from typing import List

from raidensim.types import Path

from raidensim.network.node import Node
from raidensim.network.raw_network import RawNetwork
from raidensim.strategy.routing.next_hop.priority_strategy import PriorityStrategy
from raidensim.strategy.routing.routing_strategy import RoutingStrategy


class GreedyRoutingStrategy(RoutingStrategy):
    """
    Routing based only on local information available to a node. From all partners every node
    simply chooses the one with the highest priority (lowest in numbers).

    Jon Kleinberg also calls this a "myopic" (short-sighted) routing strategy.
    """
    def __init__(self, priority_strategy: PriorityStrategy, max_depth: int=50):
        self.priority_strategy = priority_strategy
        self.max_depth = max_depth

    def route(self, raw: RawNetwork, source: Node, target: Node, value: int) -> (Path, List[Path]):
        u = source
        visited = set()
        path = [u]
        path_history = []
        for i in range(self.max_depth):
            visited.add(u)
            valid_partners = [
                (self.priority_strategy.priority(u, v, e, target, value), tiebreak, v)
                for tiebreak, (v, e) in enumerate(raw[u].items())
                if v not in visited
            ]
            valid_partners = [
                (priority, tiebreak, partner) for priority, tiebreak, partner in valid_partners
                if priority is not None
            ]
            if valid_partners:
                priority, i_v, v = min(valid_partners)
                path.append(v)
            else:
                # Go back.
                if len(path) == 1:
                    return [], path_history
                path = path[:-1]
                v = path[-1]
            path_history.append(path.copy())
            if v == target:
                return path, path_history
            u = v

        return [], path_history
