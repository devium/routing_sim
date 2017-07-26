"""
Network Backbone:

- Nodes connnect in a Kademlia style fashion but not strictly
- Light clients connect to full nodes

Tests:
- Test nodes doing a recursive path lookup
- Test nodes maintaining a view on the capacity up to n hops distance
- Test global path finding helper
- Count number of messages
- Count success rate
- Compare path length

Implement:
- Creation of the Network + storage/load of it
- power distribution of capacity
- flexible framework to simulate

Todo:
* variation of channel deposits
* preference for channel partners with similar deposits
* add light clients
* visualize deposits, light clients
* variation of capacities
* imprecise kademlia for sybill attacks prevention and growth of network
* locally cached neighbourhood capacity
* simulate availabiliy of nodes
* stats on global and recursive path finding

* calc the number of messages sent for global, locally cached and recursive routing
* 3d visualization of the network (z-axis being the deposits)


Interactive:
* rebalancing fees, fee based routing

"""

import networkx as nx
from dijkstra_weighted import dijkstra_path
import random
import sys
from utils import WeightedDistribution, ParetoDistribution

random.seed(43)
sys.setrecursionlimit(100)


class ChannelView(object):

    "channel from the perspective of this"

    def __init__(self, this_node, other_node):
        assert isinstance(this_node, Node)
        assert isinstance(other_node, Node)
        assert this_node != other_node
        self.this = this_node.uid
        self.partner = self.other = other_node.uid
        if self.this < self.other:
            self._account = this_node.G.edge[this_node][other_node]
        else:
            self._account = this_node.G.edge[this_node][other_node]

    @property
    def balance(self):
        "what other owes self if positive"
        if self.this < self.other:
            return self._account['balance']
        return -self._account['balance']

    @balance.setter
    def balance(self, value):
        if self.this < self.other:
            self._account['balance'] = value
        else:
            self._account['balance'] = -value

    @property
    def deposit(self):
        return self._account[self.this]

    @deposit.setter
    def deposit(self, value):
        assert value >= 0
        self._account[self.this] = value

    @property
    def partner_deposit(self):
        return self._account[self.other]

    @property
    def capacity(self):
        return self.balance + self.deposit

    def __repr__(self):
        return '<Channel({}:{} {}:{} balance:{}>'.format(self.this, self.deposit, self.other,
                                                         self.partner_deposit, self.balance)


class Node(object):

    min_deposit_deviation = 0.5  # accept up to X of own deposit

    def __init__(self, cn, uid, num_channels=0, deposit_per_channel=100):
        assert isinstance(cn, ChannelNetwork)
        self.cn = cn
        self.G = cn.G
        self.uid = uid
        self.num_channels = num_channels
        self.deposit_per_channel = deposit_per_channel
        self.channels = []
        self.min_expected_deposit = self.min_deposit_deviation * self.deposit_per_channel

    def __repr__(self):
        return '<{}({} deposit:{} channels:{}/{})>'.format(
            self.__class__.__name__, self.uid, self.deposit_per_channel,
            len(self.channels), self.num_channels)

    @property
    def partners(self):  # all partners
        return [cv.partner for cv in self.channels]

    @property
    def targets(self):
        """
        geometrical distances with 1/3 of id space as max distance
        """
        distances = [self.cn.max_id / 2**i / 3 for i in range(self.num_channels)]
        return [(self.uid + d) % self.cn.max_id for d in distances]

    def initiate_channels(self):
        # Only accept nodes with a certain minimum deposit per channel.
        def node_filter(node):
            return bool(node.deposit_per_channel > self.min_expected_deposit)

        # Find closest node to target node that fits the filter and isn't already connected to us.
        for target_id in self.targets:
            for attempt, node_id in enumerate(
                    self.cn.get_closest_node_ids(target_id, filter=node_filter)
            ):
                other = self.cn.node_by_id[node_id]
                accepted = other.connect_requested(self) and self.connect_requested(other)
                if accepted:
                    self.cn.add_edge(self, other)
                    self.setup_channel(other)
                    other.setup_channel(self)
                    break
                if attempt > 10:
                    break

    def channel_view(self, other):
        return ChannelView(self, other)

    def setup_channel(self, other):
        assert isinstance(other, Node)
        cv = self.channel_view(other)
        cv.deposit = self.deposit_per_channel
        cv.balance = 0
        self.channels.append(cv)

    def connect_requested(self, other):
        assert isinstance(other, Node)
        if other.deposit_per_channel < self.min_expected_deposit:
            # print "refused to connect", self, other, self.min_expected_deposit
            return
        if other.uid in self.partners:
            return
        if other == self:
            return
        return True

    def _channels_by_distance(self, target_id, value):

        max_id = self.cn.max_id

        def _distance(cv):
            a, b = target_id, cv.partner
            d = abs(a - b)
            if d > max_id / 2:
                d = abs(max_id - d)
            return d

        cvs = sorted(self.channels, lambda a, b: cmp(_distance(a), _distance(b)))
        assert len(cvs) < 2 or _distance(cvs[0]) <= _distance(cvs[-1])
        return [cv for cv in cvs if cv.capacity >= value]

    def find_path_recursively(self, target_id, value, max_hops=50, visited=[]):
        """
        sort channels by distance to target, filter by capacity
        setting a low max_hops allows to implment breath first, yielding in shorter paths
        """
        contacted = 0  # how many nodes have been contacted
        if self in visited:
            return 0, []
        for cv in self._channels_by_distance(target_id, value):
            if cv.partner == target_id:  # if can reach target return [self]
                return 0, [self]
            if len(visited) == max_hops:
                return contacted, []  # invalid
            node = self.cn.node_by_id[cv.partner]
            try:
                c, path = node.find_path_recursively(target_id, value, max_hops, visited + [self])
                contacted += 1 + c
                if path:
                    return contacted, [self] + path
            except RuntimeError:  # recursion limit
                pass
        return contacted, []  # could not find path


class FullNode(Node):
    pass


class LightClient(Node):
    pass


class PathFindingHelper(object):
    def __init__(self, cn, range_, center):
        self.cn = cn
        self.range = range_
        self.center = center

    def is_in_range(self, target):
        assert isinstance(target, Node)

        return abs(target.uid - self.center) <= self.range / 2

    def _get_path_cost_function(self, value, hop_cost=1):
        """
        Same as the global :func:`~ChannelNetwork._get_path_cost_function` except it considers
        nodes outside the helper's range unavailable.
        """

        def cost_func_fast(a, b, _account):
            if not self.is_in_range(a) and not self.is_in_range(b):
                return None

            if a.uid < b.uid:
                capacity = _account['balance'] + _account[a.uid]
            else:
                capacity = - _account['balance'] + _account[a.uid]

            assert capacity >= 0
            if capacity < value:
                return None
            return hop_cost

        return cost_func_fast

    def find_path(self, source, target, value):
        assert isinstance(source, Node)
        assert isinstance(target, Node)
        try:
            path = dijkstra_path(self.cn.G, source, target, self._get_path_cost_function(value))
            return path
        except nx.NetworkXNoPath:
            return None


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


def test_basic_channel():
    cn = ChannelNetwork()
    a = Node(cn, 1)
    b = Node(cn, 2)
    cn.G.add_edge(a, b)
    channel_ab = a.channel_view(b)
    channel_ba = b.channel_view(a)

    channel_ab.deposit = 10
    channel_ba.deposit = 20
    channel_ab.balance = 2
    assert channel_ba.balance == -2
    assert channel_ab.capacity == 10 + 2
    assert channel_ba.capacity == 20 - 2


def setup_network(config):
    cn = ChannelNetwork()
    cn.generate_nodes(config)
    cn.generate_helpers(config)
    cn.connect_nodes()
    draw(cn)
    # export_obj(cn)
    return cn


def test_basic_network(config):
    cn = setup_network(config)
    draw(cn)


def test_global_pathfinding(config, num_paths=10, value=2):
    cn = setup_network(config)
    for i in range(num_paths):
        print "-" * 40
        source, target = random.sample(cn.nodes, 2)

        path = cn.find_path_global(source, target, value)
        print len(path), path
        draw(cn, path)

        contacted, path = cn.find_path_recursively(source, target, value)
        print len(path), path, contacted
        draw(cn, path)

        path, helper = cn.find_path_with_helper(source, target, value)
        if path:
            print len(path), path
        else:
            print 'No direct path to target sector.'
        draw(cn, path, helper)


def draw(cn, path=None, helper_highlight=None):
    from utils import draw as _draw
    assert isinstance(cn, ChannelNetwork)
    _draw(cn, path, helper_highlight)


class ParetoNetworkConfiguration(object):
    num_nodes = 100
    fullness_dist = ParetoDistribution(a=0.8, min_value=1, max_value=100)

    @staticmethod
    def get_num_channels(fullness):
        return int(fullness / 5 + 2)

    @staticmethod
    def get_channel_deposit(fullness):
        return int(fullness * 5.0)

    # pathfinding helpers
    ph_num_helpers = 20
    ph_max_range_fr = 1/8.
    ph_min_range_fr = 1/16.

    def __init__(self, num_nodes):
        self.num_nodes = num_nodes

##########################################################


if __name__ == '__main__':
    test_basic_channel()
    # test_basic_network()
    test_global_pathfinding(ParetoNetworkConfiguration(1000), num_paths=5, value=2)
