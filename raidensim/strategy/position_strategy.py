from typing import Union, Iterable

import math

from raidensim.network.lattice import Lattice
from raidensim.network.node import Node


class PositionStrategy(object):
    def _map_node(self, node: Node):
        raise NotImplementedError

    def map(self, nodes: Union[Node, Iterable[Node]]):
        if isinstance(nodes, Node):
            return self._map_node(nodes)
        elif isinstance(nodes, Iterable[Node]):
            return {node: self._map_node(node) for node in nodes}
        else:
            raise ValueError

    def distance(self, a: Node, b: Node):
        raise NotImplementedError


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
    def __init__(self, lattice: Lattice):
        self.lattice = lattice

    def _map_node(self, node: Node) -> (int, int):
        return self.lattice.node_to_coord[node]

    def distance(self, a: Node, b: Node):
        return self.lattice.node_distance(a, b)
