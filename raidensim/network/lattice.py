from typing import Iterator, Union, Iterable

import numpy as np

from raidensim.network.node import Node
from raidensim.types import Coord


class Lattice(object):
    def __init__(self, num_dims=2):
        self.num_dims = num_dims
        self.dims = range(self.num_dims)
        self.node_to_coord = {}
        self.coord_to_node = {}
        self.min = np.zeros(num_dims, dtype=int)
        self.max = np.zeros(num_dims, dtype=int)
        self.gaps = set()

    def resize(self, min_: Coord, max_: Coord):
        for dim_i in self.dims:
            # Expand resized dimension in appropriate direction by adding gaps for all remaining
            # dimensions in the expanded region.
            expand_from = None
            expand_to = None
            if min_[dim_i] < self.min[dim_i]:
                expand_from = min_[dim_i]
                expand_to = self.min[dim_i] - 1
                self.min[dim_i] = min_[dim_i]

            if max_[dim_i] > self.max[dim_i]:
                expand_from = self.max[dim_i] + 1
                expand_to = max_[dim_i]
                self.max[dim_i] = max_[dim_i]

            if expand_from is not None:
                dim_gaps = []
                for dim_j in self.dims:
                    if dim_i == dim_j:
                        dim_gaps.append([x for x in range(expand_from, expand_to + 1)])
                    else:
                        dim_gaps.append([x for x in range(self.min[dim_j], self.max[dim_j] + 1)])

                self.gaps |= set(tuple(gap) for gap in self._cartesian_product(*dim_gaps))

    @staticmethod
    def _cartesian_product(*arrays):
        la = len(arrays)
        arr = np.empty([len(a) for a in arrays] + [la], dtype=int)
        for i, a in enumerate(np.ix_(*arrays)):
            arr[..., i] = a
        return arr.reshape(-1, la)

    def add_node(self, node: Node, coord: Coord):
        self.resize(np.minimum(self.min, coord), np.maximum(self.max, coord))
        self.node_to_coord[node] = np.array(coord, dtype=int)
        coord_fixed = tuple(coord)
        self.coord_to_node[coord_fixed] = node

        if coord_fixed in self.gaps:
            self.gaps.remove(coord_fixed)

    @property
    def content(self):
        return np.prod([self.max[dim_i] - self.min[dim_i] for dim_i in self.dims])

    @property
    def density(self):
        return len(self.node_to_coord) / self.content

    @property
    def num_required_channels(self):
        return self.num_dims * 2

    def node_neighbors(self, node: Node) -> Iterator[Node]:
        node_pos = self.node_to_coord.get(node)
        if not node_pos:
            return iter(())
        return self.coord_neighbors(*node_pos)

    def coord_neighbors(self, coord: Coord) -> Iterator[Node]:
        return (
            self.coord_to_node[tuple(coord)] for coord in self.neighbor_coords(coord)
            if tuple(coord) in self.coord_to_node
        )

    def neighbor_coords(self, coord: Coord) -> Iterator[np.array]:
        for dim_i in self.dims:
            unit = np.zeros(self.num_dims, dtype=int)
            unit[dim_i] = 1
            yield coord + unit
            yield coord - unit

    def node_distance(self, a: Node, b: Node):
        acoord = self.node_to_coord[a]
        bcoord = self.node_to_coord[b]
        return self.coord_distance(acoord, bcoord)

    def coord_distance(self, a: Coord, b: Coord):
        return sum(abs(a[dim_i] - b[dim_i]) for dim_i in self.dims)

    def get_free_coord(self) -> Coord:
        if self.gaps:
            return np.array(next(iter(self.gaps)))

        if not self.node_to_coord:
            return np.zeros(self.num_dims, dtype=int)

        # No more gaps. Extend lattice in shortest direction.
        # Tiebreak prefers expansion in positive direction.
        _, dim_min = min((self.max[dim_i] - self.min[dim_i], dim_i) for dim_i in self.dims)
        d_min, _, dir_min = min(
            (abs(dir_extrema[dim_min]), tiebreak, dir)
            for dir_extrema, tiebreak, dir in [(self.min, 1, -1), (self.max, 0, 1)]
        )
        x = self.min.copy()
        x[dim_min] = dir_min * (d_min + 1)

        return x

    @property
    def ascii(self) -> str:
        if self.num_dims != 2:
            return 'ASCII presentation only available in 2D lattices.'

        display = ''
        for y in range(self.max[1], self.min[1] - 1, -1):
            if y == 0:
                display += '0 '
            else:
                display += '  '
            for x in range(self.min[0], self.max[0] + 1, 1):
                display += 'X' if (x, y) in self.coord_to_node else 'O'
            display += '\n'

        if self.min[0] <= 0:
            display += ' ' * (2 - self.min[0]) + '0'

        return display


class WovenLattice(Lattice):
    def __init__(self, num_dims: int, weave_base_factor: int, min_order: int, max_order: int):
        Lattice.__init__(self, num_dims)
        assert weave_base_factor > 0
        assert max_order >= min_order > 0
        self.weave_base_factor = weave_base_factor
        self.min_order = min_order
        self.max_order = max_order

    @property
    def num_required_channels(self):
        return super().num_required_channels + 2 * (self.max_order - self.min_order + 1)

    def coord_neighbors(self, coord: Coord) -> Iterator[Node]:
        lattice_neighbors = Lattice.coord_neighbors(self, coord)
        try:
            while True:
                yield next(lattice_neighbors)
        except StopIteration:
            pass

        # Additional long-range hops.
        hop_dim = sum(coord) % self.num_dims
        order_base = max(2, self.num_dims) * self.weave_base_factor
        for order in range(self.min_order, self.max_order + 1):
            distance = order_base**order
            tcoord = coord.copy()
            tcoord[hop_dim] += distance
            if tuple(tcoord) in self.coord_to_node:
                yield self.coord_to_node[tuple(tcoord)]
            tcoord[hop_dim] -= 2 * distance
            if tuple(tcoord) in self.coord_to_node:
                yield self.coord_to_node[tuple(tcoord)]
