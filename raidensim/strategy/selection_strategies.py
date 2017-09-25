import bisect
import random
from typing import Dict, Any, Iterable

import math

from raidensim.network.channel_network import ChannelNetwork
from raidensim.network.node import Node
from raidensim.strategy.strategy import SelectionStrategy, NodeConnectionData


class KademliaSelectionStrategy(SelectionStrategy):
    """
    Connects nodes with closer nodes first, increasing the target distance exponentially for each
    new target.

    For each node, a desired target distance is computed. Then, a node is searched that comes
    closest to this distance (in either direction).

    Desired target distance starts at 1 and increases up to `max_network_distance` at the
    `targets_per_cycle - 1`th target. This cycle is repeated until enough connections have been
    established or no more target nodes can be found.

    This results in a network with dense connections in their vicinity and fewer connections to
    more distant nodes.
    """
    def __init__(self, max_network_distance, targets_per_cycle, **kwargs):
        SelectionStrategy.__init__(self, **kwargs)
        self.max_network_distance = max_network_distance
        self.targets_per_cycle=targets_per_cycle

        # Cached network information.
        self.cached_cn = None
        self.node_ids_sorted = []
        self.node_id_to_node = {}

    def _distances(self, max_distance: float) -> Iterable[int]:
        i = 0
        distance_base = max_distance ** (1 / (self.targets_per_cycle - 1))

        while True:
            yield distance_base ** i
            i = (i + 1) % self.targets_per_cycle

    def _update_network_cache(self, cn: ChannelNetwork):
        # Best guess on an up-to-date cache. Not an issue with constant-node networks.
        if len(self.node_ids_sorted) == len(cn.nodes) and self.cached_cn == cn:
            return

        self.node_id_to_node = {node.uid: node for node in cn.nodes}
        self.node_ids_sorted = sorted(node.uid for node in cn.nodes)
        self.cached_cn = cn

    def targets(
            self, node: NodeConnectionData, node_to_connection_data: Dict[Node, Dict[str, Any]]
    ) -> Iterable[NodeConnectionData]:
        self._update_network_cache(node[0].cn)
        max_distance = self.max_network_distance * node[0].cn.MAX_ID
        distances = self._distances(max_distance)
        while True:
            target_id = (node[0].uid + next(distances)) % node[0].cn.MAX_ID
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
                d_left = node[0].cn.ring_distance(self.node_ids_sorted[i_left], target_id)
                d_right = node[0].cn.ring_distance(self.node_ids_sorted[i_right], target_id)
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
                target_data = node_to_connection_data[target]
                if self.match(node, (target, target_data)):
                    break

                if last_iteration:
                    # We made one entire revolution without results. End of generator.
                    raise StopIteration

                if node[0].cn.ring_distance(i_left, i_right) <= 1:
                    # Left and Right are now either the same or 1 node apart. We covered all nodes.
                    last_iteration = True

            yield target, target_data


class RandomSelectionStrategy(SelectionStrategy):
    def targets(
            self, node: NodeConnectionData, node_to_connection_data: Dict[Node, Dict[str, Any]]
    ) -> Iterable[NodeConnectionData]:
        filtered_nodes = {
            other for other in node[0].cn.nodes
            if self.match(node, (other, node_to_connection_data[other]))
        }
        while filtered_nodes:
            other = random.sample(filtered_nodes, 1)[0]
            filtered_nodes.remove(other)
            yield (other, node_to_connection_data[other])
