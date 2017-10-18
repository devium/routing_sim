import random
from typing import Tuple, Callable, Iterator

import networkx as nx
import time

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
        self.frozen_edges = []

    @property
    def bi_edges(self) -> Iterator[Tuple[Node, Node, dict]]:
        return ((u, v, uv) for u, v, uv in self.edges(data=True) if u.uid < v.uid)

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
        num_bi_channels = len(self.edges) // 2
        tic = time.time()
        for i, (u, v, uv) in enumerate(self.bi_edges):
            toc = time.time()
            if toc - tic > 5:
                tic = toc
                print('Resetting channel {}/{}'.format(i, num_bi_channels))

            vu = self[v][u]
            uv['balance'] = 0
            vu['balance'] = 0
            self.update_channel_cache(u, v, uv, vu)

    def freeze_random_nodes(self, num_nodes: int):
        """
        Freeze all incoming edges of a set of random nodes.
        """
        self.unfreeze_nodes()
        freeze_nodes = random.sample(self.nodes, num_nodes)
        self.frozen_edges += [
            edge for node in freeze_nodes for edge in self.out_edges(node, data=True)
        ]
        self.frozen_edges += [
            edge for node in freeze_nodes for edge in self.in_edges(node, data=True)
        ]
        self.remove_edges_from(self.frozen_edges)
        self.remove_nodes_from(freeze_nodes)

    def unfreeze_nodes(self):
        self.add_edges_from(self.frozen_edges)
        self.frozen_edges = []

    def get_available_nodes(
            self, transfer_value: int, channel_filter: Callable[[Node, Node, dict], bool]=None
    ) -> Tuple[Node, Node]:
        for i in range(1000):
            source, target = random.sample(self.nodes, 2)
            if any(
                True for u, v, e in self.out_edges(source, data=True) if channel_filter(u, v, e)
            ) and any(
                e['capacity'] >= transfer_value
                for u, v, e in self.out_edges(source, data=True)
                if not channel_filter or channel_filter(u, v, e)
            ) and any(
                True for u, v, e in self.in_edges(target, data=True) if channel_filter(u, v, e)
            ) and any(
                e['deposit'] - e['net_balance'] + e['imbalance'] >= transfer_value
                for u, v, e in self.in_edges(target, data=True)
                if not channel_filter or channel_filter(u, v, e)
            ):
                return source, target
        raise ValueError('Max attempts of finding transfer nodes reached.')

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
            self.update_channel_cache(u, v, uv, vu)
