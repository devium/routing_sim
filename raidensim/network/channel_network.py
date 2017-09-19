import math
import random
from typing import Callable

import networkx as nx
import time

from raidensim.config import NetworkConfiguration
from raidensim.dijkstra_weighted import dijkstra_path
from raidensim.network.node import FullNode
from raidensim.network.node import Node
from raidensim.network.path_finding_helper import PathFindingHelper


class ChannelNetwork(object):
    max_id = 2 ** 32
    max_distance_fraction = 1 / 3
    max_distance = max_distance_fraction * max_id

    def __init__(self):
        self.G = nx.Graph()
        self.node_by_id = dict()
        self.nodeids = []
        self.nodes = []
        self.helpers = []

    def generate_nodes(self, config: NetworkConfiguration):
        # full nodes
        for i in range(config.num_nodes):
            uid = random.randrange(self.max_id)
            fullness = config.fullness_dist.random()
            max_initiated_channels = config.get_max_initiated_channels(fullness)
            max_accepted_channels = config.get_max_accepted_channels(fullness)
            max_channels = config.get_max_channels(fullness)
            deposit_per_channel = config.get_channel_deposit(fullness)
            node = FullNode(
                self,
                uid,
                fullness,
                max_initiated_channels,
                max_accepted_channels,
                max_channels,
                deposit_per_channel
            )
            self.node_by_id[uid] = node

        self.nodeids = sorted(self.node_by_id.keys())
        self.nodes = [self.node_by_id[_uid] for _uid in self.nodeids]

    def generate_helpers(self, config):
        for i in range(config.ph_num_helpers):
            center = random.randrange(self.max_id)
            min_range = int(config.ph_min_range_fr * self.max_id)
            max_range = int(config.ph_max_range_fr * self.max_id)
            range_ = random.randrange(min_range, max_range)
            self.helpers.append(PathFindingHelper(self, range_, center))

    def connect_nodes(self, open_strategy='closest_fuller'):
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
            if not node.channels:
                print("not connected", node)
                del_nodes.append(node)
                self.nodeids.remove(node.uid)
                del self.node_by_id[node.uid]
            elif len(node.channels) < 2:
                print("weakly connected", node)

        self.nodes = [node for node in self.nodes if node not in del_nodes]

    def add_edge(self, A, B):
        assert isinstance(A, Node)
        assert isinstance(B, Node)
        if A.uid < B.uid:
            self.G.add_edge(A, B)
        else:
            self.G.add_edge(B, A)

    def ring_distance(self, node_a: int, node_b: int):
        return min((node_a - node_b) % self.max_id, (node_b - node_a) % self.max_id)

    def get_closest_node_ids(self, target_id: int, filter: Callable[[Node], bool]=None):
        filtered_nodeids = [n for n in self.nodeids if not filter or filter(self.node_by_id[n])]
        return sorted(filtered_nodeids, key=lambda n: self.ring_distance(n, target_id))

    @staticmethod
    def _get_path_cost_function_constant_fees(value, hop_cost=1):
        def cost_func_fast(a, b, _account):
            sign = 1 if a.uid < b.uid else -1
            capacity = _account[a.uid] + sign * _account['balance']
            assert capacity >= 0
            if capacity < value:
                return None
            return hop_cost

        return cost_func_fast

    @staticmethod
    def _get_path_cost_function_net_balance_fees(value):
        def cost_func_fees(a, b, _account):
            sign = 1 if a.uid < b.uid else -1
            # positive balance = larger uid owes smaller uid
            balance_a = sign * _account['balance']
            capacity = _account[a.uid] + balance_a
            if capacity < value:
                return None

            # Sigmoid function.
            return 1 - 1 / (1 + math.exp(-balance_a))

        return cost_func_fees

    @staticmethod
    def _get_path_cost_function_imbalance_fees(value):
        def cost_func_fees(a, b, _account):
            sign = 1 if a.uid < b.uid else -1
            capacity = _account[a.uid] + sign * _account['balance']
            if capacity < value:
                return None

            # Positive imbalance <=> a has a higher capacity than b.
            imbalance = _account[a.uid] - _account[b.uid] + sign * 2 * _account['balance']
            imbalance -= 2 * value
            # Sigmoid function.
            return 1 - 1 / (1 + math.exp(-imbalance))

        return cost_func_fees

    def find_path_global(self, source: Node, target: Node, value, path_cost_mode='constant'):
        if path_cost_mode == 'constant':
            path_cost_func = self._get_path_cost_function_constant_fees(value)
        elif path_cost_mode == 'net-balance':
            path_cost_func = self._get_path_cost_function_net_balance_fees(value)
        elif path_cost_mode == 'imbalance':
            path_cost_func = self._get_path_cost_function_imbalance_fees(value)
        else:
            raise ValueError('Unsupported fee model.')
        try:
            path = dijkstra_path(
                self.G, source, target, path_cost_func
            )
            return path
        except nx.NetworkXNoPath:
            return None

    def find_path_with_helper(self, source: Node, target: Node, value):
        """
        Find a path to the target using pathfinding helpers that know about channel balances in
        the target address sector.
        """
        assert isinstance(source, Node)
        assert isinstance(target, Node)

        helpers = (helper for helper in self.helpers if helper.is_in_range(target))

        # Assume direct entrypoint into target sector.
        for helper in helpers:
            print('Trying to route through helper {} +/- {} to {}.'.format(
                helper.center, int(helper.range / 2), target.uid
            ))
            path = helper.find_path(source, target, value)
            if path:
                return path, helper

        return None, None

    def do_transfer(self, path, value):
        for i in range(len(path) - 1):
            node_a = path[i]
            node_b = path[i + 1]
            cv1 = node_a.channels[node_b.uid]
            cv1.balance -= value
