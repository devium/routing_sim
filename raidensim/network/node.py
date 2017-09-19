import math
import random
from typing import Callable

from raidensim.network.channel_view import ChannelView
import heapq


class Node(object):
    def __init__(
            self,
            cn,
            uid: int,
            fullness:float = 0,
            max_initiated_channels=0,
            max_accepted_channels=0,
            max_channels=0,
            deposit_per_channel=100
    ):
        self.cn = cn
        self.G = cn.G
        self.uid = uid
        self.fullness=fullness
        self.max_initiated_channels = max_initiated_channels
        self.max_accepted_channels = max_accepted_channels
        self.max_channels = max_channels
        self.deposit_per_channel = deposit_per_channel
        self.channels = {}
        self.num_initiated_channels = 0
        self.num_accepted_channels = 0

    def __repr__(self):
        # TODO: make use of initiated/accepted/max
        return '<{}({} deposit:{} channels:{}/{})>'.format(
            self.__class__.__name__, self.uid, self.deposit_per_channel,
            len(self.channels), self.num_initiated_channels)

    @property
    def partners(self):  # all partners
        return self.channels.keys()

    def ring_distance(self, other: 'Node'):
        return self.cn.ring_distance(self.uid, other.uid)

    @staticmethod
    def _node_request_filter_closest_fuller(a: 'Node', b: 'Node'):
        """
        a decides to connect to b if
        1. not self
        2. not already connected
        3. b's deposit per channel is higher than a's
        4. b is within the maximum channel distance
        """
        # a decides whether to connect to b.
        return a.uid != b.uid and \
               b.uid not in a.channels and \
               b.deposit_per_channel >= a.deposit_per_channel and \
               a.ring_distance(b) < a.cn.max_distance

    @staticmethod
    def _node_accept_filter_closest_fuller(a: 'Node', b: 'Node'):
        """
        a decides to accept b if
        1. not self
        2. not already connected
        3. b's deposit per channel is at least X% of a's
        4. b is within the maximum channel distance
        """
        return a.uid != b.uid and \
               b.uid not in a.channels and \
               a.num_accepted_channels < a.max_accepted_channels and \
               len(a.channels) < a.max_channels and \
               b.deposit_per_channel > 0.3 * a.deposit_per_channel and \
               a.ring_distance(b) < a.cn.max_distance

    def _initiate_channels_closest_fuller(self):
        # Find target ID, i.e. IDs that are at desirable distances (regardless of actual nodes).
        # Closer targets first, increasing exponentially up to a fraction of ID space.
        # Repeating in cycles.
        cycle_length = math.log(self.cn.max_distance, 2)
        distances = [int(2**(i % cycle_length)) for i in range(self.max_initiated_channels)]
        target_ids = [(self.uid + d) % self.cn.max_id for d in distances]

        # Find closest nodes to targets that fit the filter.
        for target_id in target_ids:
            if self.num_initiated_channels >= self.max_initiated_channels or \
                    len(self.channels) >= self.max_channels:
                break

            found = False
            target_node_ids = self.cn.get_closest_node_ids(
                target_id,
                filter=lambda other: Node._node_request_filter_closest_fuller(self, other)
            )
            rejected = []
            for attempt, node_id in enumerate(target_node_ids):
                other = self.cn.node_by_id[node_id]
                if Node._node_accept_filter_closest_fuller(other, self):
                    self.cn.add_edge(self, other)
                    self.setup_channel(other)
                    self.num_initiated_channels += 1
                    other.setup_channel(self)
                    other.num_accepted_channels += 1
                    found = True
                    break
                else:
                    rejected.append(other.uid)
                if attempt > 20:
                    break

            if not found:
                print(
                    'Failed to find a target node from {} viable nodes for node {} at {}. '\
                    'Rejected by: {}'
                    .format(len(target_node_ids), self.uid, target_id, rejected)
                )

    def _initiate_channels_microraiden(self):
        servers = [
            node for node in self.cn.nodes if node.fullness > 0 and
            node.num_accepted_channels < node.max_accepted_channels
        ]
        targets = random.sample(servers, self.max_initiated_channels)

        for target in targets:
            self.cn.add_edge(self, target)
            self.setup_channel(target)
            self.num_initiated_channels += 1
            target.setup_channel(self)
            target.num_accepted_channels += 1

    def initiate_channels(self, open_strategy: str):
        if open_strategy == 'closest_fuller':
            self._initiate_channels_closest_fuller()
        elif open_strategy == 'microraiden':
            self._initiate_channels_microraiden()

    def setup_channel(self, other):
        assert isinstance(other, Node)
        assert other.uid not in self.channels
        cv = ChannelView(self, other)
        cv.deposit = self.deposit_per_channel
        cv.balance = 0
        self.channels[other.uid] = cv

    @staticmethod
    def _distance_priority(cn, source_id: int, current: 'Node', next_: 'Node', target_id: int):
        """
        Normalized distance between new node and target node.
        distance == 0 => same node
        distance == 1 => 180 degrees
        """
        return cn.ring_distance(next_.uid, target_id) / cn.max_id * 2

    @staticmethod
    def _highway_priority(cn, source_id: int, current: 'Node', next_: 'Node', target_id: int):
        # Normalized distance [0, 1]
        distance = cn.ring_distance(next_.uid, target_id) / cn.max_id * 2

        # "Highway factor" (0, 1)
        # 0: decreasing fullness
        # 1: increasing fullness
        highway_factor = 1 / (1 + math.exp(-(next_.fullness - current.fullness)))

        # Far away => use highway.
        # Closer => follow shortest distance.
        distance_weight = max(1 - distance * 4, 0)
        priority = distance_weight * (1 - distance) + (1 - distance_weight) * highway_factor

        return 1 - priority

    def find_path_bfs(self, target_id, value, priority_model='distance', max_paths=100):
        """
        Modified BFS using a priority queue instead of a normal queue.
        Lower priority value means higher actual priority.
        """
        priority_models = {
            'distance': Node._distance_priority,
            'highway': Node._highway_priority
        }
        priority_fun = priority_models[priority_model]

        # Insertion order as a priority tie breaker.
        i = 0
        queue = [(0, i, [self])]
        visited = {self}
        path_history = []

        while queue:
            _, _, path = heapq.heappop(queue)
            node = path[-1]
            visited.add(node)
            if len(path) > 1:
                path_history.append(path)
            if node.uid == target_id:
                return visited, path, path_history
            if len(path_history) >= max_paths:
                return visited, [], path_history

            for cv in node.channels.values():
                partner = self.cn.node_by_id[cv.partner]
                if partner not in visited and cv.capacity >= value:
                    new_path = path + [partner]
                    priority = priority_fun(self.cn, self.uid, node, partner, target_id)
                    i += 1
                    queue_entry = (priority, i, new_path)
                    heapq.heappush(queue, queue_entry)

        # Node unreachable, likely due to fragmented network or degraded channels.
        return visited, [], path_history


class FullNode(Node):
    pass


class LightClient(Node):
    pass
