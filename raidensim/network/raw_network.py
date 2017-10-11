import networkx as nx

from raidensim.types import Path
from raidensim.network.node import Node


class RawNetwork(nx.DiGraph):
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
    """

    def __init__(self):
        nx.DiGraph.__init__(self)

    def remove_isolated(self):
        connected_nodes = {node for edge in self.edges for node in edge}
        isolated_nodes = [node for node in self.nodes if node not in connected_nodes]
        if isolated_nodes:
            print('Removing isolated nodes: {}'.format(isolated_nodes))
            self.remove_nodes_from(isolated_nodes)

    def setup_channel(self, u: Node, v: Node, deposit: int) -> None:
        e = {
            'deposit': deposit,
            'balance': 0,
            'capacity': deposit,
            'num_transfers': 0
        }
        self.add_edge(u, v, **e)
        self.update_channel_cache(u, v)

    def close_channel(self, other: Node) -> None:
        self.remove_edge(self, other)

    def reset_channels(self):
        bi_edges = {frozenset({u, v}) for u, v in self.edges}
        for u, v in bi_edges:
            uv = self[u][v]
            vu = self[v][u]
            uv['balance'] = 0
            vu['balance'] = 0
            self.update_channel_cache(u, v, uv, vu)

    def update_channel_cache(self, u: Node, v: Node, uv: dict=None, vu: dict=None):
        if uv is None:
            uv = self[u].get(v)
        if vu is None:
            vu = self[v].get(u)
        if uv is not None and vu is not None:
            net_balance = uv['balance'] - vu['balance']
            uv['net_balance'] = net_balance
            vu['net_balance'] = -net_balance
            deposit_a = uv['deposit']
            deposit_b = vu['deposit']
            uv['capacity'] = deposit_a - net_balance
            vu['capacity'] = deposit_b + net_balance
            imbalance = deposit_b - deposit_a + 2 * net_balance
            uv['imbalance'] = imbalance
            vu['imbalance'] = -imbalance

    def do_transfer(self, path: Path, value: int):
        for i in range(len(path) - 1):
            u = path[i]
            v = path[i + 1]
            uv = self[u][v]
            vu = self[v][u]
            if uv['capacity'] < value:
                print('Warning: Transfer ({} -> {}: {}) exceeds capacity.'.format(u, v, value))
            uv['balance'] += value
            uv['num_transfers'] += 1
            vu['num_transfers'] += 1
            # Update redundant/cached values for faster Dijkstra routing.
            self.update_channel_cache(u, v, uv, vu)
