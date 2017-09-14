from raidensim.network.channel_view import ChannelView
import heapq


class Node(object):

    min_deposit_deviation = 0.5  # accept up to X of own deposit

    def __init__(self, cn, uid, fullness=0, num_channels=0, deposit_per_channel=100):
        self.cn = cn
        self.G = cn.G
        self.uid = uid
        self.fullness=fullness
        self.num_channels = num_channels
        self.deposit_per_channel = deposit_per_channel
        self.channels = {}
        self.min_expected_deposit = self.min_deposit_deviation * self.deposit_per_channel

    def __repr__(self):
        return '<{}({} deposit:{} channels:{}/{})>'.format(
            self.__class__.__name__, self.uid, self.deposit_per_channel,
            len(self.channels), self.num_channels)

    @property
    def partners(self):  # all partners
        return self.channels.keys()

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
            reasons = []
            for attempt, node_id in enumerate(
                    self.cn.get_closest_node_ids(target_id, filter=node_filter)
            ):
                other = self.cn.node_by_id[node_id]
                accepted1, reason1 = other.connect_requested(self)
                accepted2, reason2 = self.connect_requested(other)
                reasons.append(reason1 if not accepted1 else reason2)
                if accepted1 and accepted2:
                    self.cn.add_edge(self, other)
                    self.setup_channel(other)
                    other.setup_channel(self)
                    break
                if attempt > 10:
                    print(
                        'Failed to find a target node for node {} at {}. Reasons: {}'
                        .format(self.uid, target_id, reasons)
                    )
                    break

    def channel_view(self, other):
        return ChannelView(self, other)

    def setup_channel(self, other):
        assert isinstance(other, Node)
        assert other.uid not in self.channels
        cv = self.channel_view(other)
        cv.deposit = self.deposit_per_channel
        cv.balance = 0
        self.channels[other.uid] = cv

    def connect_requested(self, other):
        assert isinstance(other, Node)
        if other.deposit_per_channel < self.min_expected_deposit:
            # print "refused to connect", self, other, self.min_expected_deposit
            return False, 'Deposit of {} too low.'.format(other.uid)
        if other.uid in self.partners:
            return False, 'Already connected.'
        if other == self:
            return False, 'Cannot connect to self.'
        return True, 'OK'

    def _channels_by_distance(self, target_id, value):
        partners = sorted(
            self.channels.keys(), key=lambda partner: self.cn.ring_distance(target_id, partner)
        )
        return [partner for partner in partners if self.channels[partner].capacity >= value]

    def find_path_recursively(self, target_id, value, max_hops=50, visited=None):
        """
        sort channels by distance to target, filter by capacity
        setting a low max_hops allows to implement breadth first, yielding shorter paths
        """
        contacted = {self}  # which nodes have been contacted
        if visited is None:
            visited = []
        if self in visited:
            return set(), []
        for partner in self._channels_by_distance(target_id, value):
            node = self.cn.node_by_id[partner]
            if partner == target_id:  # if can reach target return [self]
                return {node}, [self]
            if len(visited) == max_hops:
                return contacted, []  # invalid
            try:
                contacted.add(node)
                c, path = node.find_path_recursively(target_id, value, max_hops, visited + [self])
                contacted |= c
                if path:
                    return contacted, [self] + path
            except RuntimeError:  # recursion limit
                pass
        return contacted, []  # could not find path

    def find_path_bfs(self, target_id, value):
        """
        Modified BFS using a distance-to-target-based priority queue instead of a normal queue.
        Queue elements are paths prioritized by their distance from the target.
        """
        i = 0
        queue = [(self.cn.ring_distance(self.uid, target_id), i, [self])]
        visited = {self}

        while queue:
            distance, order, path = heapq.heappop(queue)
            node = path[-1]
            visited.add(node)
            if node.uid == target_id:
                return visited, path

            for cv in node.channels.values():
                partner = self.cn.node_by_id[cv.partner]
                if partner not in visited and cv.capacity >= value:
                    new_path = path + [partner]
                    i += 1
                    queue_entry = (self.cn.ring_distance(cv.partner, target_id), i, new_path)
                    heapq.heappush(queue, queue_entry)

        return visited, []


class FullNode(Node):
    pass


class LightClient(Node):
    pass
