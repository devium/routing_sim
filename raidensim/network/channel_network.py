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
    MAX_DISTANCE_FRACTION = 1 / 3
    MAX_DISTANCE = MAX_DISTANCE_FRACTION * MAX_ID

    def __init__(self, config: NetworkConfiguration):
        nx.DiGraph.__init__(self)
        self.config = config
        self.node_by_id = dict()
        self.helpers = []

        self.generate_nodes(config)
        # cn.generate_helpers(config)
        self.connect_nodes(config.open_strategy)

    def generate_nodes(self, config: NetworkConfiguration):
        for i in range(config.num_nodes):
            uid = random.randrange(self.MAX_ID)
            fullness = config.fullness_dist.random()
            node = Node(
                self,
                uid,
                fullness,
                config.get_max_initiated_channels(fullness),
                config.get_max_accepted_channels(fullness),
                config.get_max_channels(fullness),
                config.get_channel_deposit(fullness)
            )
            self.add_node(node)

    def generate_helpers(self, config: NetworkConfiguration):
        for i in range(config.ph_num_helpers):
            center = random.randrange(self.MAX_ID)
            min_range = int(config.ph_min_range_fr * self.MAX_ID)
            max_range = int(config.ph_max_range_fr * self.MAX_ID)
            range_ = random.randrange(min_range, max_range)
            self.helpers.append(PathFindingHelper(self, range_, center))

    def connect_nodes(self, open_strategy='bi_closest_fuller'):
        print('Connecting nodes.')
        tic = time.time()
        for i, node in enumerate(self.nodes):
            toc = time.time()
            if toc - tic > 5:
                tic = toc
                print('Connecting node {}/{}'.format(i, len(self.nodes)))
            node.initiate_channels(open_strategy)

        del_nodes = []
        for node in self.nodes:
            if not node.partners:
                print("Not connected: {}. Removing.".format(node))
                del_nodes.append(node)
            elif len(node.partners) < 2:
                print("Weakly connected: {}".format(node))

        self.remove_nodes_from(del_nodes)

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

    def find_path_global(self, source: Node, target: Node, value: int, edge_cost_mode='constant'):
        self._update_edge_costs(edge_cost_mode, value)
        try:
            return nx.dijkstra_path(self, source, target)
        except nx.NetworkXNoPath:
            return None

    def _get_edge_cost_constant(self, a: Node, b: Node):
        return 1

    def _get_edge_cost_net_balance(self, a: Node, b: Node):
        # Sigmoid function.
        return 1 - 1 / (1 + math.exp(-a.get_net_balance(b)))

    def _get_edge_cost_imbalance(self, a: Node, b: Node):
        # Sigmoid function.
        return 1 - 1 / (1 + math.exp(-a.get_imbalance(b)))

    EDGE_COST_MODES = {
        'constant': _get_edge_cost_constant,
        'net-balance': _get_edge_cost_net_balance,
        'imbalance': _get_edge_cost_imbalance,
    }

    def _update_edge_costs(self, edge_cost_mode: str, value: int):
        for a, b in self.edges:
            if a.get_capacity(b) < value:
                self.edges[a,b]['weight'] = None
            else:
                self.edges[a,b]['weight'] = self.EDGE_COST_MODES[edge_cost_mode](self, a, b)

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
            self.edges[a, b]['balance'] += value
