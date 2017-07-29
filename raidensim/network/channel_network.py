import random

import networkx as nx

from raidensim.dijkstra_weighted import dijkstra_path
from raidensim.network.node import Node
from raidensim.network.path_finding_helper import PathFindingHelper
from raidensim.network.node import FullNode


class ChannelNetwork(object):

    max_id = 2**32
    # max_id = 100
    num_channels_per_node = 5  # outgoing

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
            node = FullNode(self, uid, num_channels, deposit_per_channel)
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
        for node in self.nodes[:]:
            node.initiate_channels()
            if not node.channels:
                print "not connected", node
                self.nodeids.remove(node.uid)
                del self.node_by_id[node.uid]
            elif len(node.channels) < 2:
                print "weakly connected", node

    def add_edge(self, A, B):
        assert isinstance(A, Node)
        assert isinstance(B, Node)
        if A.uid < B.uid:
            self.G.add_edge(A, B)
        else:
            self.G.add_edge(B, A)

    def ring_distance(self, node_a, node_b):
        return min((node_a - node_b) % self.max_id, (node_b - node_a) % self.max_id)

    def get_closest_node_id(self, target_id, filter=None):
        # Need to filter anyway, so O(n) min search is fine.
        filtered_nodeids = (n for n in self.nodeids if not filter or filter(self.node_by_id[n]))
        closest = min(filtered_nodeids, key=lambda n:self.ring_distance(n, target_id))

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

    def _get_path_cost_function(self, value, hop_cost=1):
        """
        goal: from all possible paths, choose from the shortes with enough capacity
        """
        def cost_func_fast(a, b, _account):
            # this func should be as fast as possible, as it's called often
            # don't alloc memory
            if a.uid < b.uid:
                capacity = _account['balance'] + _account[a.uid]
            else:
                capacity = - _account['balance'] + _account[a.uid]
            assert capacity >= 0
            if capacity < value:
                return None
            return hop_cost
        return cost_func_fast

    def find_path_global(self, source, target, value):
        assert isinstance(source, Node)
        assert isinstance(target, Node)
        try:
            path = dijkstra_path(self.G, source, target, self._get_path_cost_function(value))
            return path
        except nx.NetworkXNoPath:
            return None

    def find_path_recursively(self, source, target, value):
        assert isinstance(source, Node)
        assert isinstance(target, Node)
        contacted = 0
        for max_hops in (5, 10, 15, 50):  # breath first possible
            c, path = source.find_path_recursively(target.uid, value, max_hops)
            contacted += c
            if path:
                break
        if path:
            assert len(path) == len(set(path))  # no node visited twice
            return contacted, path + [target]
        return contacted, []

    def find_path_with_helper(self, source, target, value):
        """
        Find a path to the target using pathfinding helpers that know about channel balances in
        the target address sector.
        """
        assert isinstance(source, Node)
        assert isinstance(target, Node)

        helpers = (helper for helper in self.helpers if helper.is_in_range(target))

        # Assume direct entrypoint into target sector.
        for helper in helpers:
            # TODO
            print 'Trying to route through helper %d +/- %d to %d.' % (helper.center,
                                                                       int(helper.range / 2),
                                                                       target.uid)
            path = helper.find_path(source, target, value)
            if path:
                return path, helper

        return None, None