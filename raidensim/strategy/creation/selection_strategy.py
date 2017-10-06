import bisect
import random
from itertools import cycle
from typing import Iterable

import math

from raidensim.network.node import Node
from raidensim.network.raw_network import RawNetwork
from .filter_strategy import FilterStrategy


class SelectionStrategy(object):
    def __init__(self, filter_strategies: Iterable[FilterStrategy]):
        self.filter_strategies = filter_strategies

    def match(self, raw: RawNetwork, a: Node, b: Node):
        return all(filter_strategy.filter(raw, a, b) for filter_strategy in self.filter_strategies)

    def targets(self, raw: RawNetwork, node: Node) -> Iterable[Node]:
        raise NotImplementedError


class CachedNetworkSelectionStrategy(SelectionStrategy):
    """
    Maintains a sorted cache of all node IDs and a mapping from node ID to Node.
    """
    def __init__(self, **kwargs):
        SelectionStrategy.__init__(self, **kwargs)

        # Cached network information.
        self.cached_raw = None
        self.nodes = []
        self.node_ids_sorted = []
        self.node_id_to_node = {}

    def _update_network_cache(self, raw: RawNetwork):
        # Best guess on an up-to-date cache. Not an issue with constant-node networks.
        if len(self.nodes) == len(raw.nodes) and self.cached_raw == raw:
            return

        # Nodes shuffled for easy random sampling.
        self.nodes = list(raw.nodes)
        random.shuffle(self.nodes)
        self.node_id_to_node = {node.uid: node for node in raw.nodes}
        self.node_ids_sorted = sorted(node.uid for node in raw.nodes)
        self.cached_raw = raw

    def targets(self, raw: RawNetwork, node: Node) -> Iterable[Node]:
        raise NotImplementedError


class KademliaSelectionStrategy(CachedNetworkSelectionStrategy):
    """
    Connects nodes with closer nodes first, increasing the target distance exponentially for each
    new target.

    For each node, a desired target distance is computed. Then, a node is searched that comes
    closest to this distance (in either direction).

    Desired target distance starts at 1 and increases up to `max_distance` at the
    `targets_per_cycle - 1`th target. This cycle is repeated until enough connections have been
    established or no more target nodes can be found.

    This results in a network with dense connections in their vicinity and fewer connections to
    more distant nodes.
    """

    def __init__(
            self,
            max_id: int,
            max_distance: int,
            skip: int, **kwargs
    ):
        self.max_id = max_id
        CachedNetworkSelectionStrategy.__init__(self, **kwargs)
        targets_per_cycle = int(math.log(max_distance, 2)) + 1
        self.distances = [int(2 ** i) for i in range(skip, targets_per_cycle)]

    def _ring_distance(self, a: int, b: int):
        return min((a - b) % self.max_id, (b - a) % self.max_id)

    def targets(self, raw: RawNetwork, node: Node) -> Iterable[Node]:
        self._update_network_cache(raw)
        distances = cycle(self.distances)
        while True:
            target_id = (node.uid + next(distances)) % self.max_id
            # Find node on or after target ID (ignoring filters).
            i_right = bisect.bisect_left(self.node_ids_sorted, target_id)
            num_nodes = len(self.node_ids_sorted)
            if i_right == num_nodes:
                # We're past the highest node ID. Continue search from the beginning.
                i_right = bisect.bisect_left(self.node_ids_sorted, 0)

            # Closest node to target on the left is at right-1.
            i_left = (i_right - 1) % num_nodes
            last_iteration = False

            while True:
                # Find next closest node (either to left or right).
                d_left = self._ring_distance(self.node_ids_sorted[i_left], target_id)
                d_right = self._ring_distance(self.node_ids_sorted[i_right], target_id)
                if d_left < d_right:
                    i_side = -1
                    i = i_left
                else:
                    i_side = 1
                    i = i_right

                if i_side < 0:
                    i_left = (i_left - 1) % num_nodes
                else:
                    i_right = (i_right + 1) % num_nodes

                target = self.node_id_to_node[self.node_ids_sorted[i]]
                if self.match(raw, node, target):
                    break

                if last_iteration:
                    # We made one entire revolution without results. End of generator.
                    raise StopIteration

                if self._ring_distance(i_left, i_right) <= 1:
                    # Left and Right are now either the same or 1 node apart. We covered all nodes.
                    last_iteration = True

            yield target


class RandomSelectionStrategy(CachedNetworkSelectionStrategy):
    def targets(self, raw: RawNetwork, node: Node) -> Iterable[Node]:
        self._update_network_cache(raw)
        for other in self.nodes:
            if self.match(raw, node, other):
                yield other
