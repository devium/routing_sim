from typing import Iterator, Tuple

import math
import numpy as np

from raidensim.network.node import Node
from raidensim.types import DiskCoord, PolarCoord


class Annulus:
    def __init__(self, max_ring: int):
        self.max_ring = max_ring

        # Annulus-specific constants.
        self.capped_ring = (max_ring + 1) // 2
        self.full_span_ring = (max_ring - 1) // 2

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
        if from_ring < to_ring:
            if to_ring > self.capped_ring:
                if to_ring > (self.max_ring + from_ring + 1) // 2:
                    return 0
                else:
                    return 2 ** (self.max_ring - to_ring + 1)
            else:
                return 2 ** to_ring
        elif from_ring > to_ring:
            if to_ring > 2 * from_ring - self.max_ring - 2:
                if from_ring > self.capped_ring:
                    return 2 ** (self.max_ring - 2 * from_ring + to_ring + 1)
                else:
                    return 2 ** to_ring
            else:
                return 0
        else:
            return 0

    def inward_ring_span(self, from_ring) -> int:
        return min(self.rank(from_ring), from_ring)

    def outward_ring_span(self, from_ring) -> int:
        return (self.rank(from_ring)) // 2

    def slot_span_on(self, from_ring: int, on_ring: int) -> int:
        if on_ring > from_ring:
            if from_ring > self.full_span_ring:
                return (
                           2 ** (self.max_ring - 2 * from_ring + on_ring + 1) -
                           2 ** (self.max_ring - on_ring + 1)
                       ) // 3 - 2 ** (on_ring - from_ring) + 2
            else:
                # Spans entire outward annulus.
                return 2 ** on_ring
        else:
            return -1

    def slot_span_range_on(self, coord: DiskCoord, on_ring) -> Tuple[int, int]:
        r, i = coord
        if on_ring > r:
            if r > self.full_span_ring:
                num_slots = 2 ** on_ring
                from_ = 2 ** (on_ring - r) * (i + 1) + (
                    2 ** (self.max_ring - on_ring) - 2 ** (self.max_ring - 2 * r + on_ring)
                ) // 3 - 1
                to_ = from_ + self.slot_span_on(r, on_ring)
                return from_ % num_slots, to_ % num_slots
            else:
                # Spans entire outward annulus.
                return 0, 0
        else:
            return -1, -1

    def num_inward_connections(self, from_ring) -> int:
        if from_ring > self.capped_ring:
            return max(2 ** (self.rank(from_ring)) - 1, 0)
        else:
            return 2 ** from_ring - 1

    def num_outward_connections(self, from_ring) -> int:
        if from_ring < self.max_ring:
            rank = self.rank(from_ring)
            if from_ring < self.capped_ring:
                return 2 ** (self.capped_ring + 1) - 2 ** (from_ring + 1) + \
                       2 ** (self.rank(self.capped_ring)) - 2 ** (rank - rank // 2)
            else:
                return 2 ** rank - 2 ** (rank - rank // 2)
        else:
            return 0

    def num_connections(self, from_ring) -> int:
        return self.num_inward_connections(from_ring) + self.num_outward_connections(from_ring)

    @staticmethod
    def closest_on(coord: DiskCoord, ring: int) -> int:
        r, i = coord
        if r < ring:
            return 2 ** (ring - r - 1) * (2 * i + 1) - 1
        else:
            return i // 2 ** (r - ring)

    def add_node(self, node: Node, coord: DiskCoord):
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
        num_connections = min(num_connections, num_ring_slots)

        while num_connections > 0:
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
            capped_num_connections = min(num_connections, num_ring_slots)
            first = it - capped_num_connections // 2 + 1
            for j in range(first, first + capped_num_connections):
                yield np.array([rt, j % num_ring_slots])
            rt += 1
            it = 2 * it + 1
            num_connections //= 2
            num_ring_slots *= 2
