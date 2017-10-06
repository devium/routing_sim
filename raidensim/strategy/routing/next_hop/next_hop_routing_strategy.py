import heapq
from typing import List

from raidensim.network.node import Node
from raidensim.network.raw_network import RawNetwork
from raidensim.strategy.routing.next_hop.priority_strategy import PriorityStrategy
from raidensim.strategy.routing.routing_strategy import RoutingStrategy
from raidensim.types import Path


class NextHopRoutingStrategy(RoutingStrategy):
    def __init__(
            self,
            priority_model: PriorityStrategy,
            max_paths=10000
    ):
        self.priority_model = priority_model
        self.max_paths=max_paths

    def route(self, raw: RawNetwork, source: Node, target: Node, value: int) -> (Path, List[Path]):
        """
        Modified BFS using a priority queue instead of a normal queue.
        Lower priority value means higher actual priority.
        """

        # Priority queue ordering:
        # 1. Priority model
        # 2. Path length
        # 3. Insertion order
        i = 0
        queue = [(0, 0, i, [source])]
        visited = {source}
        path_history = []

        while queue:
            _, _, _, path = heapq.heappop(queue)
            u = path[-1]
            visited.add(u)
            if len(path) > 1:
                path_history.append(path)
            if u == target:
                return path, path_history
            if len(path_history) >= self.max_paths:
                return [], path_history

            for v, e in raw[u].items():
                if v not in visited and e['capacity'] >= value:
                    new_path = path + [v]
                    priority = self.priority_model.priority(raw, source, u, v, e, target, value)
                    i += 1
                    queue_entry = (priority, len(new_path), i, new_path)
                    heapq.heappush(queue, queue_entry)

        # Node unreachable, likely due to fragmented network or degraded channels.
        return [], path_history
