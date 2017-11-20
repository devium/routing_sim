from typing import Iterator, Tuple

import math
import numpy as np

from raidensim.network.node import Node
from raidensim.types import DiskCoord, PolarCoord


class Annulus:
    def __init__(self, max_ring: int):
        self.max_ring = max_ring
        self.min_ring = max_ring // 2
        self.channels_per_ring = [
            self.num_connections(r) for r in range(self.max_ring, self.min_ring - 1, -1)
        ]

        self.node_to_coord = {}
        self.coord_to_node = {}

    @property
    def num_slots(self) -> int:
        return 2 ** (self.max_ring + 1) - 1

    @staticmethod
    def num_ring_slots(ring: int) -> int:
        return 2 ** ring

    @staticmethod
    def ring_distance(i1: int, i2: int, num_ring_slots: int) -> int:
        di = i1 - i2
        return min(di % num_ring_slots, -di % num_ring_slots)

    @staticmethod
    def ring_distance_signed(i1: int, i2: int, num_ring_slots: int) -> int:
        di = i2 - i1
        half_num_ring_nodes = num_ring_slots // 2
        if di > half_num_ring_nodes:
            di -= num_ring_slots
        elif di < -half_num_ring_nodes:
            di += num_ring_slots
        return di

    def coord_to_polar(self, coord: DiskCoord) -> PolarCoord:
        r, i = coord
        rn = r / self.max_ring
        dtheta = 2 * math.pi / 2 ** r
        theta = (coord[1] + 0.5) * dtheta
        return np.array([rn, theta])

    def rank(self, ring: int) -> int:
        return self.max_ring - ring + 1

    def num_connections_to(self, from_ring: int, to_ring: int) -> int:
        if to_ring < self.min_ring or to_ring > self.max_ring:
            return 0

        if from_ring < to_ring:
            if to_ring > (self.max_ring + from_ring + 1) // 2:
                return 0
            else:
                return 2 ** (self.max_ring - to_ring + 1)
        elif from_ring > to_ring:
            if to_ring > 2 * from_ring - self.max_ring - 2:
                return 2 ** (self.max_ring - 2 * from_ring + to_ring + 1)
            else:
                return 0
        else:
            return 0

    def inward_ring_span(self, from_ring) -> int:
        return min(self.rank(from_ring), from_ring - self.min_ring)

    def outward_ring_span(self, from_ring) -> int:
        return (self.rank(from_ring)) // 2

    def slot_span_on(self, from_ring: int, on_ring: int) -> int:
        if on_ring > from_ring:
            return (
                       2 ** (self.max_ring - 2 * from_ring + on_ring + 1) -
                       2 ** (self.max_ring - on_ring + 1)
                   ) // 3 - 2 ** (on_ring - from_ring) + 2
        else:
            return -1

    def slot_span_range_on(self, coord: DiskCoord, on_ring) -> Tuple[int, int]:
        r, i = coord
        if on_ring > r:
            num_slots = 2 ** on_ring
            pow_rdiff = 2 ** (on_ring - r)
            partial_half_span = 2 ** (self.max_ring - 2 * r + on_ring)
            partial_half_span -= 2 ** (self.max_ring - on_ring)
            partial_half_span //= 3
            begin = pow_rdiff * (i + 1) - partial_half_span - 1
            end = pow_rdiff * i + partial_half_span + 1
            return begin % num_slots, end % num_slots
        else:
            return -1, -1

    def num_inward_connections(self, from_ring: int) -> int:
        rank = self.rank(from_ring)
        return 2 ** rank - 2 ** max(0, rank - from_ring + self.min_ring)

    def num_outward_connections(self, from_ring: int) -> int:
        if from_ring < self.max_ring:
            rank = self.rank(from_ring)
            return 2 ** rank - 2 ** (rank - rank // 2)
        else:
            return 0

    def num_connections(self, from_ring: int) -> int:
        return self.num_inward_connections(from_ring) + self.num_outward_connections(from_ring)

    def ring_recommendation(self, num_channels: int):
        """
        Brute-force iteration over rings from the largest ring inward.
        """
        try:
            dr = next(
                dr for dr, required_channels in enumerate(self.channels_per_ring)
                if required_channels > num_channels
            )
        except StopIteration:
            return self.min_ring

        return self.max_ring - dr + 1

    @staticmethod
    def closest_on(coord: DiskCoord, ring: int) -> int:
        r, i = coord
        if r < ring:
            return 2 ** (ring - r - 1) * (2 * i + 1) - 1
        else:
            return i // 2 ** (r - ring)

    def add_node(self, node: Node, coord: DiskCoord):
        r, i = coord
        assert self.min_ring <= r <= self.max_ring
        assert 0 <= i < 2**r
        self.node_to_coord[node] = np.array(coord, dtype=int)
        coord_fixed = tuple(coord)
        self.coord_to_node[coord_fixed] = node

    def node_distance(self, a: Node, b: Node):
        return self.coord_distance(self.node_to_coord[a], self.node_to_coord[b])

    def coord_distance(self, a: DiskCoord, b: DiskCoord):
        return 1

    def coord_partners(self, coord: DiskCoord) -> Iterator[Node]:
        return (
            self.coord_to_node[tuple(coord)] for coord in self.partner_coords(coord)
            if tuple(coord) in self.coord_to_node
        )

    def partner_coords(self, coord: DiskCoord):
        r, i = coord
        r = int(r)

        # Inward connections.
        rt = r - 1
        it = i
        num_connections = int(2 ** (self.max_ring - r))
        num_ring_slots = int(2 ** rt)

        while num_connections > 0 and rt >= self.min_ring:
            first = (it - num_connections + 1) // 2
            for j in range(first, first + num_connections):
                yield np.array([rt, j % num_ring_slots], dtype=int)
            rt -= 1
            it //= 2
            num_connections //= 2
            num_ring_slots //= 2

        # Outward connections.
        rt = r + 1
        it = i * 2
        rmax = (self.max_ring + r + 1) // 2
        num_connections = int(2 ** (self.max_ring - r))
        num_ring_slots = int(2 ** rt)

        while rt <= rmax:
            first = it - num_connections // 2 + 1
            for j in range(first, first + num_connections):
                yield np.array([rt, j % num_ring_slots])
            rt += 1
            it = 2 * it + 1
            num_connections //= 2
            num_ring_slots *= 2
