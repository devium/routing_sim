import math
import random

import networkx as nx
import time

from raidensim.dijkstra_weighted import dijkstra_path
from raidensim.network.node import FullNode
from raidensim.network.node import Node
from raidensim.network.path_finding_helper import PathFindingHelper


class ChannelNetwork(object):
    max_id = 2 ** 32

    def __init__(self):
        self.G = nx.Graph()
        self.node_by_id = dict()
        self.nodeids = []
        self.nodes = []
        self.helpers = []

    def generate_nodes(self, config):
        # full nodes
        for i in range(config.num_nodes):
            uid = random.randrange(self.max_id)
            fullness = config.fullness_dist.random()
            num_channels = config.get_num_channels(fullness)
            deposit_per_channel = config.get_channel_deposit(fullness)
            node = FullNode(self, uid, fullness, num_channels, deposit_per_channel)
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

    def connect_nodes(self):
        print('Connecting nodes.')
        tic = time.time()
        for i, node in enumerate(self.nodes):
            toc = time.time()
            if toc - tic > 5:
                tic = toc
                print('Connecting node {}/{}'.format(i, len(self.nodes)))
            node.initiate_channels()

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

    def get_closest_node_id(self, target_id, filter=None):
        # Need to filter anyway, so O(n) min search is fine.
        filtered_nodeids = (n for n in self.nodeids if not filter or filter(self.node_by_id[n]))
        closest = min(filtered_nodeids, key=lambda n: self.ring_distance(n, target_id))

        return closest

    def get_closest_node_ids(self, target_id, filter=None):
        "generator"
        cid = self.get_closest_node_id(target_id, filter)
        idx = self.nodeids.index(cid)

        def get_next(idx, inc=1):
            while True:
                idx = (idx + inc) % len(self.nodeids)
                nodeid = self.nodeids[idx]
                if filter(self.node_by_id[nodeid]):
                    return idx, nodeid

        lidx, lid = get_next(idx, inc=-1)
        ridx, rid = get_next(idx, inc=1)
        while True:
            if self.ring_distance(lid, target_id) < self.ring_distance(rid, target_id):
                yield lid
                lidx, lid = get_next(lidx, inc=-1)
            else:
                yield rid
                ridx, rid = get_next(ridx, inc=1)

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

    def find_path_recursively(self, source: Node, target: Node, value, hop_limits=None):
        contacted = set()
        if not hop_limits:
            hop_limits = [100]

        path = None
        for max_hops in hop_limits:  # breath first possible
            print('Attempting to find path with a max of {} hops.'.format(max_hops))
            c, path = source.find_path_recursively(target.uid, value, max_hops)
            contacted |= c
            if path:
                break

        if path:
            assert len(path) == len(set(path))  # no node visited twice
            return contacted, path + [target]

        return contacted, []

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
