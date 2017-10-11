from typing import List

from raidensim.types import Path

from raidensim.network.node import Node
from raidensim.network.raw_network import RawNetwork
from raidensim.strategy.routing.next_hop.priority_strategy import PriorityStrategy
from raidensim.strategy.routing.routing_strategy import RoutingStrategy


class GreedyRoutingStrategy(RoutingStrategy):
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
                (self.priority_strategy.priority(raw, source, u, v, e, target, value), i_v, v)
                for i_v, (v, e) in enumerate(raw[u].items())
                if v not in visited and e['capacity'] >= value
            ]
            if not valid_partners:
                # Go back.
                if len(path) == 1:
                    return [], path_history
                path = path[:-1]
                v = path[-1]
            else:
                priority, i_v, v = min(valid_partners)
                path.append(v)
            path_history.append(path.copy())
            if v == target:
                return path, path_history
            u = v

        return [], path_history
