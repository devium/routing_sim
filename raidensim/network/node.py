from raidensim.network.channel_view import ChannelView


class Node(object):

    min_deposit_deviation = 0.5  # accept up to X of own deposit

    def __init__(self, cn, uid, num_channels=0, deposit_per_channel=100):
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
                    print(
                        'Failed to find a target node for node {} at {}.'
                        .format(self.uid, target_id)
                    )
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