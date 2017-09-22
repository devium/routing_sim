import heapq
from typing import List, Set


class Node(object):
    """
    Notes:
        * When dealing with channel numbers, these numbers refer to unidirectional channels.
        * "Balance" is the amount of tokens sent from this node to another node. Accordingly,
          a positive balance for node A indicates that A has spent tokens, not gained.
        * Same for "Net balance". If A sent 3 tokens to B, and B sent 1 token to A, A's net balance
          is 2. B's net balance is -2.
        * "Capacity" is the amount of tokens available for spending and takes into account both
          directions of a channel. With the added information that both participants deposited
          5 tokens in their channels, the above example results in capacites 3 and 7 for A and B
          respectively.
        * "Imbalance" is the difference in capacities. On equal deposits this is the same as the
          net balance. Newly created channels always have a net balance of 0 but depending on their
          deposits differ in imbalance.
        * The get_* functions are not optimized for speed and should not be used in performance-
          critical parts of the code (e.g. Dijkstra search). Cache values like these on the graph
          edges for better performance.
    """
    def __init__(self, cn, uid: int, fullness: float):
        self.cn = cn
        self.uid = uid
        self.fullness = fullness

    def __repr__(self):
        return '<{}({}, fullness: {})>'.format(self.__class__.__name__, self.uid, self.fullness)

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
        """
        Difference between capacities. If > 0 then partner a higher capacity.
        Imbalance == Net Balance for equal deposit channels.
        """
        return partner.get_capacity(self) - self.get_capacity(partner)

    def ring_distance(self, other: 'Node') -> int:
        return self.cn.ring_distance(self, other)

    def setup_channel(self, other: 'Node', deposit: int) -> None:
        self.cn.add_edge(
            self,
            other,
            deposit=deposit,
            balance=0,
            capacity=deposit
        )
        self.cn.update_channel_cache(self, other)

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
