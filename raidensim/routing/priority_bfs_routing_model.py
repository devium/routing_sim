import heapq
from typing import Callable, List

from raidensim.network.channel_network import ChannelNetwork
from raidensim.network.node import Node
from raidensim.routing.routing_model import RoutingModel
from raidensim.types import Path


class PriorityBFSRoutingModel(RoutingModel):
    def __init__(
            self,
            priority_model: Callable[[ChannelNetwork, Node, Node, Node, Node], float],
            max_paths=100
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
            node = path[-1]
            visited.add(node)
            if len(path) > 1:
                path_history.append(path)
            if node == target:
                return path, path_history
            if len(path_history) >= self.max_paths:
                return [], path_history

            for partner in node.partners:
                if partner not in visited and node.get_capacity(partner) >= value:
                    new_path = path + [partner]
                    priority = self.priority_model(source.cn, source, node, partner, target)
                    i += 1
                    queue_entry = (priority, len(new_path), i, new_path)
                    heapq.heappush(queue, queue_entry)

        # Node unreachable, likely due to fragmented network or degraded channels.
        return [], path_history

    @staticmethod
    def distance_priority(
            cn, source: 'Node', current: 'Node', next_: 'Node', target: 'Node'
    ) -> float:
        """
        Normalized distance between new node and target node.
        distance == 0 => same node
        distance == 1 => 180 degrees
        """
        return cn.ring_distance(next_, target) / cn.MAX_ID * 2
