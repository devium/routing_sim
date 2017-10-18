import bisect
import random
from itertools import cycle
from typing import Iterator, Callable, Union

import math
import numpy as np

from raidensim.network.lattice import WovenLattice
from raidensim.network.node import Node
from raidensim.network.raw_network import RawNetwork
from raidensim.strategy.position_strategy import PositionStrategy, LatticePositionStrategy
from .filter_strategy import FilterStrategy


class SelectionStrategy(object):
    def __init__(self, filter_strategies: Iterator[FilterStrategy]):
        self.filter_strategies = filter_strategies

    def match(self, raw: RawNetwork, a: Node, b: Node):
        return all(filter_strategy.filter(raw, a, b) for filter_strategy in self.filter_strategies)

    def targets(self, raw: RawNetwork, node: Node) -> Iterator[Node]:
        raise NotImplementedError


class CachedNetworkSelectionStrategy(SelectionStrategy):
    """
    Maintains a sorted cache of all node IDs and a mapping from node ID to Node.
    """
    def __init__(self, filter_strategies: Iterator[FilterStrategy]):
        # FIXME: This doesn't work anymore with nodes joining the network incrementally.
        SelectionStrategy.__init__(self, filter_strategies)

        # Cached network information.
        self.cached_raw = None
        self.nodes = []
        self.node_ids_sorted = []
        self.node_id_to_node = {}

    def _update_network_cache(self, raw: RawNetwork):
        # Not an issue with constant-node networks.
        if self.cached_raw == raw:
            return

        # Nodes shuffled for easy random sampling.
        self.nodes = list(raw.nodes)
        random.shuffle(self.nodes)
        self.node_id_to_node = {node.uid: node for node in raw.nodes}
        self.node_ids_sorted = sorted(node.uid for node in raw.nodes)
        self.cached_raw = raw

    def targets(self, raw: RawNetwork, node: Node) -> Iterator[Node]:
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
            skip: int,
            filter_strategies: Iterator[FilterStrategy]
    ):
        self.max_id = max_id
        CachedNetworkSelectionStrategy.__init__(self, filter_strategies)
        targets_per_cycle = int(math.log(max_distance, 2)) + 1
        self.distances = [int(2 ** i) for i in range(skip, targets_per_cycle)]

    def _ring_distance(self, a: int, b: int):
        return min((a - b) % self.max_id, (b - a) % self.max_id)

    def targets(self, raw: RawNetwork, node: Node) -> Iterator[Node]:
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
    def targets(self, raw: RawNetwork, node: Node) -> Iterator[Node]:
        self._update_network_cache(raw)
        i_start = random.randint(0, len(self.nodes) - 1)
        for i in range(i_start, i_start + len(self.nodes)):
            other = self.nodes[i % len(self.nodes)]
            if self.match(raw, node, other):
                yield other


class ExclusionSelectionStrategy(CachedNetworkSelectionStrategy):
    """
    Sped-up version of a cached selection strategy that removes nodes from the local cache that
    pass any exclusion criteria. For example: permanently exclude nodes that have reached their
    maximum channel count.

    Exclusions can be reset in case a node becomes available again.
    """
    def __init__(
            self,
            filter_strategies: Iterator[FilterStrategy],
            exclusion_criteria: Iterator[Callable[[RawNetwork, Node], bool]]
    ):
        CachedNetworkSelectionStrategy.__init__(self, filter_strategies)
        self.exclusion_criteria = exclusion_criteria
        self.pending_excludes = []

    def _update_exclusions(self):
        for exclude in reversed(sorted(self.pending_excludes)):
            del self.nodes[exclude]
        self.pending_excludes.clear()

    def _check_exclusion(self, raw: RawNetwork, node: Union[Node, int]) -> bool:
        if isinstance(node, Node):
            self._check_exclusion(raw, self.nodes.index(node))
        elif isinstance(node, int):
            node_idx = node
            node = self.nodes[node_idx]
            if any(exclude(raw, node) for exclude in self.exclusion_criteria):
                self.pending_excludes.append(node_idx)
                return True
            else:
                return False
        else:
            raise ValueError

    def reset_exclusions(self):
        # Trigger cache rebuild on next update.
        self.cached_raw = None


class RandomExclusionSelectionStrategy(ExclusionSelectionStrategy):
    def targets(self, raw: RawNetwork, node: Node) -> Iterator[Node]:
        self._update_network_cache(raw)
        self._update_exclusions()

        if self._check_exclusion(raw, node):
            return

        i_start = random.randint(0, len(self.nodes) - 1)
        for i in range(i_start, i_start + len(self.nodes)):
            other = self.nodes[i % len(self.nodes)]
            if not self._check_exclusion(raw, i % len(self.nodes)) and \
                    self.match(raw, node, other):
                yield other


class RandomAuxLatticeSelectionStrategy(SelectionStrategy):
    def __init__(self, lattice: WovenLattice, filter_strategies: Iterator[FilterStrategy]):
        SelectionStrategy.__init__(self, filter_strategies)
        self.lattice = lattice

    def targets(self, raw: RawNetwork, node: Node) -> Iterator[Node]:
        aux_neighbors = list(self.lattice.aux_node_neighbors(node))
        random.shuffle(aux_neighbors)
        return (target for target in aux_neighbors if self.match(raw, node, target))
