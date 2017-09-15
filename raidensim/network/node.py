import math
from typing import Callable

from raidensim.network.channel_view import ChannelView
import heapq


class Node(object):
    def __init__(self, cn, uid, fullness=0, num_channels=0, deposit_per_channel=100):
        self.cn = cn
        self.G = cn.G
        self.uid = uid
        self.fullness=fullness
        self.num_channels = num_channels
        self.deposit_per_channel = deposit_per_channel
        self.channels = {}

    def __repr__(self):
        return '<{}({} deposit:{} channels:{}/{})>'.format(
            self.__class__.__name__, self.uid, self.deposit_per_channel,
            len(self.channels), self.num_channels)

    @property
    def partners(self):  # all partners
        return self.channels.keys()

    def ring_distance(self, other: 'Node'):
        return self.cn.ring_distance(self.uid, other.uid)

    @staticmethod
    def _node_request_filter(a: 'Node', b: 'Node'):
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
    def _node_accept_filter(a: 'Node', b: 'Node'):
        """
        a decides to accept b if
        1. not self
        2. not already connected
        3. b's deposit per channel is at least X% of a's
        4. b is within the maximum channel distance
        """
        return a.uid != b.uid and \
               b.uid not in a.channels and \
               b.deposit_per_channel > 0.3 * a.deposit_per_channel and \
               a.ring_distance(b) < a.cn.max_distance

    def initiate_channels(self):
        # Find target ID, i.e. IDs that are at desirable distances (regardless of actual nodes).
        # Closer targets first, increasing exponentially up to a fraction of ID space.
        # Repeating in cycles.
        cycle_length = math.log(self.cn.max_distance, 2)
        distances = [int(2**(i % cycle_length)) for i in range(self.num_channels)]
        target_ids = [(self.uid + d) % self.cn.max_id for d in distances]

        # Find closest nodes to targets that fit the filter.
        for target_id in target_ids:
            found = False
            target_node_ids = self.cn.get_closest_node_ids(
                target_id, filter=lambda other: Node._node_request_filter(self, other)
            )
            rejected = []
            for attempt, node_id in enumerate(target_node_ids):
                other = self.cn.node_by_id[node_id]
                if Node._node_accept_filter(other, self):
                    self.cn.add_edge(self, other)
                    self.setup_channel(other)
                    other.setup_channel(self)
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

    def setup_channel(self, other):
        assert isinstance(other, Node)
        assert other.uid not in self.channels
        cv = ChannelView(self, other)
        cv.deposit = self.deposit_per_channel
        cv.balance = 0
        self.channels[other.uid] = cv

    def find_path_bfs(self, target_id, value, max_paths=100):
        """
        Modified BFS using a distance-to-target-based priority queue instead of a normal queue.
        Queue elements are paths prioritized by their distance from the target.
        """
        i = 0
        queue = [(self.cn.ring_distance(self.uid, target_id), i, [self])]
        visited = {self}
        path_history = []

        while queue:
            distance, order, path = heapq.heappop(queue)
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
                    i += 1
                    queue_entry = (self.cn.ring_distance(cv.partner, target_id), i, new_path)
                    heapq.heappush(queue, queue_entry)

        return visited, [], path_history


class FullNode(Node):
    pass


class LightClient(Node):
    pass
