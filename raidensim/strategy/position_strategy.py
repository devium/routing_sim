from typing import Union, Iterable, Tuple

import math

import numpy as np

from raidensim.network.hyperbolic_disk import HyperbolicDisk
from raidensim.network.lattice import Lattice
from raidensim.network.node import Node
from raidensim.types import FloatRange


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

    def label(self, a: Node) -> str:
        return a.uid

    @property
    def plot_limits(self) -> Tuple[FloatRange, FloatRange]:
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

    def distance(self, a: Node, b: Node) -> int:
        return min((a.uid - b.uid) % self.max_id, (b.uid - a.uid) % self.max_id)

    @property
    def plot_limits(self) -> Tuple[FloatRange, FloatRange]:
        return (-2, 2), (-2, 2)


class LatticePositionStrategy(PositionStrategy):
    def __init__(self, lattice: Lattice):
        self.lattice = lattice

    def _map_node(self, node: Node) -> np.array:
        return self.lattice.node_to_coord[node]

    def distance(self, a: Node, b: Node) -> int:
        return self.lattice.node_distance(a, b)

    @property
    def plot_limits(self) -> Tuple[FloatRange, FloatRange]:
        min_, max_ = self.lattice.min, self.lattice.max
        if self.lattice.num_dims < 2:
            return (min_[0] - 1, max_[0] + 1), (-0.5, 0.5)
        else:
            return (min_[0] - 1, max_[0] + 1), (min_[1] - 1, max_[1] + 1)


class HyperbolicPositionStrategy(PositionStrategy):
    def __init__(self, disk: HyperbolicDisk):
        self.disk = disk

    def _map_node(self, node: Node) -> np.array:
        coord = self.disk.node_to_coord[node]
        r, theta = self.disk.coord_to_polar(coord)
        r /= self.disk.radius
        return np.array([math.cos(theta) * r, math.sin(theta) * r])

    def distance(self, a: Node, b: Node) -> float:
        return self.disk.node_distance(a, b)

    def label(self, a: Node) -> str:
        return self.disk.node_to_coord[a][1]

    @property
    def plot_limits(self) -> Tuple[FloatRange, FloatRange]:
        return (-1.1, 1.1), (-1.1, 1.1)