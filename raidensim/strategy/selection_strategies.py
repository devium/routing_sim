import bisect
import random
from typing import Generator, Dict, Any, Iterable

import math

from raidensim.network.channel_network import ChannelNetwork
from raidensim.network.node import Node
from raidensim.strategy.strategy import SelectionStrategy, NodeConnectionData


class KademliaSelectionStrategy(SelectionStrategy):
    def __init__(self, max_network_distance, **kwargs):
        SelectionStrategy.__init__(self, **kwargs)
        self.max_network_distance = max_network_distance

        # Cached network information.
        self.node_ids_sorted = []
        self.node_id_to_node = {}

    @staticmethod
    def _distances(max_distance) -> Iterable[int]:
        cycle_length = int(math.log(max_distance, 2))
        i = 0
        while True:
            yield 2 ** i
            i = (i + 1) % cycle_length

    def _update_network_cache(self, cn: ChannelNetwork):
        # Best guess on an up-to-date cache. Not an issue with constant-node networks.
        if len(self.node_ids_sorted) == len(cn.nodes):
            return

        self.node_id_to_node = {node.uid: node for node in cn.nodes}
        self.node_ids_sorted = sorted(node.uid for node in cn.nodes)

    def targets(
            self, node: NodeConnectionData, node_to_connection_data: Dict[Node, Dict[str, Any]]
    ) -> Iterable[NodeConnectionData]:
        self._update_network_cache(node[0].cn)
        max_distance = int(self.max_network_distance * node[0].cn.MAX_ID)
        distances = self._distances(max_distance)
        while True:
            target_id = (node[0].uid + next(distances)) % node[0].cn.MAX_ID
            # Find node on or after target ID (ignoring filters).
            i_start = bisect.bisect_left(self.node_ids_sorted, target_id)
            if i_start == len(self.node_ids_sorted):
                # We're past the highest node ID. Continue search from the beginning.
                i_start = bisect.bisect_left(self.node_ids_sorted, 0)

            # Find first node after the first potential target that matches the filters.
            i = i_start
            while True:
                target = self.node_id_to_node[self.node_ids_sorted[i]]
                target_data = node_to_connection_data[target]
                if self.match(node, (target, target_data)):
                    break

                i = (i + 1) % len(self.node_ids_sorted)
                if i == i_start:
                    # We made one entire revolution without results. End of generator.
                    raise StopIteration

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
