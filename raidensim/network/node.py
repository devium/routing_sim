import heapq
import math
import random
from typing import List, Set


class Node(object):
    def __init__(
            self,
            cn,
            uid: int,
            fullness: float = 0,
            max_initiated_channels=0,
            max_accepted_channels=0,
            max_channels=0,
            deposit_per_channel=100
    ):
        self.cn = cn
        self.uid = uid
        self.fullness = fullness
        self.max_initiated_channels = max_initiated_channels
        self.max_accepted_channels = max_accepted_channels
        self.max_channels = max_channels
        self.deposit_per_channel = deposit_per_channel
        self.num_initiated_channels = 0
        self.num_accepted_channels = 0

    def __repr__(self):
        return '<{}({}, fullness: {}, channels (ini,acc,max): {}/{}/{})>'.format(
            self.__class__.__name__,
            self.uid,
            self.fullness,
            self.num_initiated_channels,
            self.num_accepted_channels,
            self.max_channels
        )

    @property
    def partners(self) -> List['Node']:
        return self.cn[self]

    def get_deposit(self, partner: 'Node') -> int:
        """Initial on-chain deposit."""
        return self.cn.edges[self, partner]['deposit']

    def get_balance(self, partner: 'Node') -> int:
        """Amount sent to partner."""
        return self.cn.edges[self, partner]['balance']

    def get_net_balance(self, partner: 'Node') -> int:
        """Amount sent to partner minus amount received from partner."""
        return self.get_balance(partner) - partner.get_balance(self)

    def get_capacity(self, partner: 'Node') -> int:
        """Remaining balance to spend, taking into account the partner's balance."""
        return self.get_deposit(partner) - self.get_net_balance(partner)

    def get_imbalance(self, partner: 'Node') -> int:
        """Difference between capacities. If > 0 then self has a higher capacity."""
        return self.get_capacity(partner) - partner.get_capacity(self)

    @staticmethod
    def _node_request_filter_closest_fuller(a: 'Node', b: 'Node') -> bool:
        """
        a decides to connect to b if
        1. not self
        2. not already connected
        3. b's deposit per channel is higher than a's
        4. b is within the maximum channel distance
        """
        # a decides whether to connect to b.
        return a.uid != b.uid and \
            b not in a.partners and \
            b.deposit_per_channel >= a.deposit_per_channel and \
            a.ring_distance(b) < a.cn.MAX_DISTANCE

    @staticmethod
    def _node_accept_filter_closest_fuller(a: 'Node', b: 'Node') -> bool:
        """
        a decides to accept b if
        1. not self
        2. not already connected
        3. b's deposit per channel is at least X% of a's
        4. b is within the maximum channel distance
        """
        return a.uid != b.uid and \
            b not in a.partners and \
            a.num_accepted_channels < a.max_accepted_channels and \
            len(a.partners) < a.max_channels and \
            b.deposit_per_channel > a.cn.config.min_partner_deposit * a.deposit_per_channel and \
            a.ring_distance(b) < a.cn.MAX_DISTANCE

    def ring_distance(self, other: 'Node') -> int:
        return self.cn.ring_distance(self, other)

    def _initiate_channels_closest_fuller(self) -> None:
        # Find target ID, i.e. IDs that are at desirable distances (regardless of actual nodes).
        # Closer targets first, increasing exponentially up to a fraction of ID space.
        # Repeating in cycles.
        cycle_length = math.log(self.cn.MAX_DISTANCE, 2)
        distances = [int(2 ** (i % cycle_length)) for i in range(self.max_initiated_channels)]
        target_ids = [(self.uid + d) % self.cn.MAX_ID for d in distances]

        # Find closest nodes to targets that fit the filter.
        for target_id in target_ids:
            if self.num_initiated_channels >= self.max_initiated_channels or \
                    len(self.partners) >= self.max_channels:
                break

            found = False
            target_nodes = self.cn.get_closest_nodes(
                target_id,
                filter_=lambda other: Node._node_request_filter_closest_fuller(self, other)
            )
            rejected = []
            for attempt, node in enumerate(target_nodes):
                if Node._node_accept_filter_closest_fuller(node, self):
                    self.setup_channel(node)
                    self.num_initiated_channels += 1
                    node.setup_channel(self)
                    node.num_accepted_channels += 1
                    found = True
                    break
                else:
                    rejected.append(node)
                if attempt > 20:
                    break

            if not found:
                print(
                    'Failed to find a target node from {} viable nodes for node {} at {}. '
                    'Rejected by: {}'.format(len(target_nodes), self.uid, target_id, rejected)
                )

    def _initiate_channels_microraiden(self) -> None:
        servers = [
            node for node in self.cn.nodes
            if node.fullness > 0 and
            node.num_accepted_channels < node.max_accepted_channels
        ]
        targets = random.sample(servers, self.max_initiated_channels)

        for target in targets:
            self.cn.add_edge(self, target)
            self.setup_channel(target)
            self.num_initiated_channels += 1
            target.setup_channel(self)
            target.num_accepted_channels += 1

    OPEN_STRATEGIES = {
        'bi_closest_fuller': _initiate_channels_closest_fuller,
        'microraiden': _initiate_channels_microraiden
    }

    def initiate_channels(self, open_strategy: str) -> None:
        self.OPEN_STRATEGIES[open_strategy](self)

    def setup_channel(self, other: 'Node') -> None:
        self.cn.add_edge(self, other, deposit=self.deposit_per_channel, balance=0)

    def close_channel(self, other: 'Node') -> None:
        self.cn.remove_edge(self, other)

    @staticmethod
    def _routing_node_distance_priority(
            cn, source: 'Node', current: 'Node', next_: 'Node', target: 'Node'
    ) -> float:
        """
        Normalized distance between new node and target node.
        distance == 0 => same node
        distance == 1 => 180 degrees
        """
        return cn.ring_distance(next_, target) / cn.MAX_ID * 2

    def find_path_bfs(
            self, target: 'Node', value: int, priority_model='distance', max_paths=100
    ) -> (Set['Node'], List['Node'], List[List['Node']]):
        """
        Modified BFS using a priority queue instead of a normal queue.
        Lower priority value means higher actual priority.
        """
        priority_models = {
            'distance': Node._routing_node_distance_priority
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
            if node == target:
                return visited, path, path_history
            if len(path_history) >= max_paths:
                return visited, [], path_history

            for partner in node.partners:
                if partner not in visited and node.get_capacity(partner) >= value:
                    new_path = path + [partner]
                    priority = priority_fun(self.cn, self, node, partner, target)
                    i += 1
                    queue_entry = (priority, i, new_path)
                    heapq.heappush(queue, queue_entry)

        # Node unreachable, likely due to fragmented network or degraded channels.
        return visited, [], path_history
