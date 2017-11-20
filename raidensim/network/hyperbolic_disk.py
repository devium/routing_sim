import math
from typing import Iterator

import numpy as np

from raidensim.network.node import Node
from raidensim.types import DiskCoord, PolarCoord, IntRange


class HyperbolicDisk:
    """
    The higher the disk radius, the lower the tangential connectivity of nodes that lie further
    out.
    """

    def __init__(self, rings: IntRange, radius: float):
        self.rings = rings
        self.radius = radius
        self.max_i = 2 ** rings[1]
        self.node_to_coord = {}
        self.coord_to_node = {}

    @property
    def num_slots(self):
        return 2 ** (self.rings[1] + 1) - 2 ** self.rings[0]

    def add_node(self, node: Node, coord: DiskCoord):
        self.node_to_coord[node] = np.array(coord, dtype=int)
        coord_fixed = tuple(coord)
        self.coord_to_node[coord_fixed] = node

    def node_distance(self, a: Node, b: Node):
        return self.coord_distance(self.node_to_coord[a], self.node_to_coord[b])

    def coord_distance(self, a: DiskCoord, b: DiskCoord):
        return self.polar_distance(self.coord_to_polar(a), self.coord_to_polar(b))

    def coord_to_polar(self, coord: DiskCoord) -> PolarCoord:
        r = coord[0] / self.rings[1] * self.radius
        dtheta = 2 * math.pi / 2 ** coord[0]
        theta = coord[1] * dtheta
        return np.array([r, theta])

    def inner_coord_partners(self, coord: DiskCoord) -> Iterator[DiskCoord]:
        """
        Includes partner nodes on the same ring.
        """
        return self.coord_partners(coord, (0, coord[0]))

    def outer_coord_partners(self, coord: DiskCoord) -> Iterator[np.array]:
        return self.coord_partners(coord, (coord[0] + 1, self.rings[1]))

    def coord_partners(self, coord: DiskCoord, rings: IntRange) -> Iterator[Node]:
        return (
            self.coord_to_node[tuple(coord)] for coord in self.partner_coords(coord, rings)
            if tuple(coord) in self.coord_to_node
        )

    def inner_partner_coords(self, coord: DiskCoord) -> Iterator[DiskCoord]:
        """
        Includes partner nodes on the same ring.
        """
        return self.partner_coords(coord, (0, coord[0]))

    def outer_partner_coords(self, coord: DiskCoord) -> Iterator[np.array]:
        return self.partner_coords(coord, (coord[0] + 1, self.rings[1]))

    def partner_coords(self, coord: DiskCoord, rings: IntRange):
        r0, i0 = coord
        for r in range(rings[0], rings[1] + 1):
            ri0 = int(i0 * 2 ** (int(r - r0)))
            num_ring_slots = 2 ** r
            # Check nodes on each ring by stepping outward in both directions from the closest
            # node.
            for di in range(0, num_ring_slots // 2):
                # Exclude the node itself.
                if r == r0 and di == 0:
                    continue

                i1 = (ri0 + di) % num_ring_slots
                i2 = (ri0 - di) % num_ring_slots

                # Distances are no longer symmetric on lower rings, so check both individually.
                num_new_nodes = 0
                if self.coord_distance(coord, [r, i1]) <= self.radius:
                    num_new_nodes += 1
                    yield np.array([r, i1])
                if di == 0:
                    continue
                if self.coord_distance(coord, [r, i2]) <= self.radius:
                    num_new_nodes += 1
                    yield np.array([r, i2])

                if num_new_nodes < 2:
                    # Distances only get bigger from here on.
                    break
            # Check the node on the exact opposite side only if all other nodes on this ring were
            # in range. (Apparently 'else' after a for-loop is a thing.)
            else:
                i1 = (ri0 + num_ring_slots // 2) % num_ring_slots
                if self.coord_distance(coord, [r, i1]) <= self.radius:
                    yield np.array([r, i1])

    @staticmethod
    def polar_distance(a: PolarCoord, b: PolarCoord):
        a_r, a_theta = a
        b_r, b_theta = b

        if math.isclose(a_theta, b_theta):
            return abs(a_r - b_r)

        # Manual hyperbolic function calculation excluding monotonic transformations to save some
        # time.
        # Actual function: acosh(cosh(a_r)*cosh(b_r)-sinh(a_r)*sinh(b_r)*cos(b_theta-a_theta))
        return math.acosh(
            math.cosh(a_r) * math.cosh(b_r) -
            math.sinh(a_r) * math.sinh(b_r) * math.cos(b_theta - a_theta)
        )
