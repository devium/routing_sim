import heapq
from typing import List

from raidensim.network.channel_network import ChannelNetwork
from raidensim.network.node import Node
from raidensim.routing.routing_model import RoutingModel
from raidensim.types import Path


class PriorityModel(object):
    def priority(
            self,
            cn: ChannelNetwork,
            source: Node,
            u: Node,
            v: Node,
            e: dict,
            target: Node,
            value: int
    ) -> float:
        raise NotImplementedError


class NextHopRoutingModel(RoutingModel):
    def __init__(
            self,
            priority_model: PriorityModel,
            max_paths=10000
    ):
        self.priority_model = priority_model
        self.max_paths=max_paths

    def route(self, source: Node, target: Node, value: int) -> (Path, List[Path]):
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

            for v, e in u.partners.items():
                if v not in visited and e['capacity'] >= value:
                    new_path = path + [v]
                    priority = self.priority_model.priority(
                        source.cn, source, u, v, e, target, value
                    )
                    i += 1
                    queue_entry = (priority, len(new_path), i, new_path)
                    heapq.heappush(queue, queue_entry)

        # Node unreachable, likely due to fragmented network or degraded channels.
        return [], path_history
