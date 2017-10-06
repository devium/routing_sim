import math

from raidensim.network.node import Node
from raidensim.strategy.network_strategy import PositionStrategy


class RingPositionStrategy(PositionStrategy):
    def __init__(self, max_id: int, min_fullness: float=0, max_fullness: float=1):
        self.max_id = max_id
        self.min_fullness = min_fullness
        self.max_fullness = max_fullness
        self.range = max_fullness - min_fullness

    def _map_node(self, node: Node) -> (float, float):
        # Position on ring.
        rad = 2 * math.pi * node.uid / self.max_id
        x, y = math.sin(rad), math.cos(rad)

        # Fuller nodes toward center.
        r = 2 / ((node.fullness - self.min_fullness) / self.range + 1)
        return x * r, y * r

    def distance(self, a: Node, b: Node):
        return min((a.uid - b.uid) % self.max_id, (b.uid - a.uid) % self.max_id)


class LatticePositionStrategy(PositionStrategy):
    def __init__(self):
        self.node_to_position = {}
        self.position_to_node = {}

    def add_node(self, node: Node, x: int, y: int):
        self.node_to_position[node] = x, y
        self.position_to_node[x, y] = node

    def get_node(self, x: int, y: int):
        return self.node_to_position[x, y]

    def _map_node(self, node: Node) -> (int, int):
        return self.node_to_position[node]

    def distance(self, a: Node, b: Node):
        pos_ax, pos_ay = self.node_to_position[a]
        pos_bx, pos_by = self.node_to_position[b]
        return abs(pos_ax - pos_bx) + abs(pos_ay - pos_by)
