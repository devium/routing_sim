import math
import random
from typing import Callable, List, Union

import networkx as nx
import time

from .config import NetworkConfiguration
from raidensim.network.node import Node
from raidensim.network.path_finding_helper import PathFindingHelper


class ChannelNetwork(nx.DiGraph):
    MAX_ID = 2 ** 32

    def __init__(self, config: NetworkConfiguration):
        nx.DiGraph.__init__(self)
        self.config = config
        self.helpers = []
        self.generate_nodes()
        # cn.generate_helpers(config)
        self.connect_nodes()

    def generate_nodes(self):
        for i in range(self.config.num_nodes):
            uid = random.randrange(self.MAX_ID)
            fullness = self.config.fullness_dist.random()
            self.add_node(Node(self, uid, fullness))

    def generate_helpers(self, config: NetworkConfiguration):
        for i in range(config.ph_num_helpers):
            center = random.randrange(self.MAX_ID)
            min_range = int(config.ph_min_range_fr * self.MAX_ID)
            max_range = int(config.ph_max_range_fr * self.MAX_ID)
            range_ = random.randrange(min_range, max_range)
            self.helpers.append(PathFindingHelper(self, range_, center))

    def connect_nodes(self):
        print('Connecting nodes.')
        tic = time.time()
        for i, node in enumerate(self.nodes):
            toc = time.time()
            if toc - tic > 5:
                tic = toc
                print('Connecting node {}/{}'.format(i, len(self.nodes)))
            self.config.network_strategy.connect(node)

        connected_nodes = {node for edge in self.edges for node in edge}
        disconnected_nodes = [node for node in self.nodes if node not in connected_nodes]
        if disconnected_nodes:
            print('Removing disconnected nodes: {}'.format(disconnected_nodes))
            self.remove_nodes_from(disconnected_nodes)

    def update_channel_cache(self, a: Node, b: Node):
        ab = self.edges.get((a, b))
        ba = self.edges.get((b, a))
        if ab is not None and ba is not None:
            net_balance = ab['balance'] - ba['balance']
            ab['net_balance'] = net_balance
            ba['net_balance'] = -net_balance
            deposit_a = ab['deposit']
            deposit_b = ba['deposit']
            ab['capacity'] = deposit_a - net_balance
            ba['capacity'] = deposit_b + net_balance
            imbalance = deposit_b - deposit_a + 2 * net_balance
            ab['imbalance'] = imbalance
            ba['imbalance'] = -imbalance

    def ring_distance(self, a: Union[int, Node], b: Union[int, Node]):
        if isinstance(a, int):
            return min((a - b) % self.MAX_ID, (b - a) % self.MAX_ID)
        elif isinstance(a, Node):
            return self.ring_distance(a.uid, b.uid)
        else:
            raise TypeError('Unsupported type.')

    def get_closest_nodes(self, target_id: int, filter_: Callable[[Node], bool]=None):
        filtered_nodes = [n for n in self.nodes if not filter_ or filter_(n)]
        return sorted(filtered_nodes, key=lambda n: self.ring_distance(n.uid, target_id))

    @staticmethod
    def _get_edge_cost_constant(a: Node, b: Node, attrs: dict, value: int):
        return 1

    @staticmethod
    def _get_edge_cost_net_balance(a: Node, b: Node, attrs: dict, value: int):
        # Sigmoid function.
        return 1 / (1 + math.exp(-(attrs['net_balance'] + value)))

    @staticmethod
    def _get_edge_cost_imbalance(a: Node, b: Node, attrs: dict, value: int):
        # Sigmoid function.
        return 1 / (1 + math.exp(attrs['imbalance'] - 2 * value))

    def find_path_global(self, source: Node, target: Node, value: int, edge_cost_mode='constant'):
        edge_cost_modes = {
            'constant': self._get_edge_cost_constant,
            'net-balance': self._get_edge_cost_net_balance,
            'imbalance': self._get_edge_cost_imbalance,
        }

        edge_cost_detail = edge_cost_modes[edge_cost_mode]

        def edge_cost(a: Node, b: Node, attrs: dict):
            # Faster condition first.
            if attrs['capacity'] > value:
                return edge_cost_detail(a, b, attrs, value)
            return None

        try:
            return nx.dijkstra_path(self, source, target, weight=edge_cost)
        except nx.NetworkXNoPath:
            return None

    def find_path_with_helper(self, source: Node, target: Node, value):
        """
        Find a path to the target using pathfinding helpers that know about channel balances in
        the target address sector.
        """
        helpers = (helper for helper in self.helpers if helper.is_in_range(target))

        # FIXME: inter-sector routing
        # Assume direct entry point into target sector.
        for helper in helpers:
            print('Trying to route through helper {} +/- {} to {}.'.format(
                helper.center, int(helper.range / 2), target.uid
            ))
            path = helper.find_path(source, target, value)
            if path:
                return path, helper

        return None, None

    def do_transfer(self, path: List[Node], value: int):
        for i in range(len(path) - 1):
            a = path[i]
            b = path[i + 1]
            if a.get_capacity(b) < value:
                print('Warning: Transfer ({} -> {}: {}) exceeds capacity.'.format(a, b, value))
            ab = self.edges[a, b]
            ab['balance'] += value
            # Update redundant/cached values for faster Dijkstra routing.
            self.update_channel_cache(a, b)
