import random
from typing import Union

import networkx as nx
import time

from raidensim.types import Path
from .config import NetworkConfiguration
from raidensim.network.node import Node


class ChannelNetwork(nx.DiGraph):
    MAX_ID = 2 ** 32

    def __init__(self, config: NetworkConfiguration):
        nx.DiGraph.__init__(self)
        self.config = config
        self.helpers = []
        self.generate_nodes()
        self.connect_nodes()

    def generate_nodes(self):
        for i in range(self.config.num_nodes):
            uid = random.randrange(self.MAX_ID)
            fullness = self.config.fullness_dist.random()
            self.add_node(Node(self, uid, fullness))

    def connect_nodes(self):
        print('Connecting nodes.')
        tic = time.time()
        for i, node in enumerate(self.nodes):
            toc = time.time()
            if toc - tic > 5:
                tic = toc
                print('Connecting node {}/{}'.format(i, len(self.nodes)))
            self.config.network_strategy.connect(node)

        connected_nodes = {node for edge in self.edges for node in edge}
        disconnected_nodes = [node for node in self.nodes if node not in connected_nodes]
        if disconnected_nodes:
            print('Removing disconnected nodes: {}'.format(disconnected_nodes))
            self.remove_nodes_from(disconnected_nodes)

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

    def ring_distance(self, u: Union[int, Node], v: Union[int, Node]):
        if isinstance(u, int):
            return min((u - v) % self.MAX_ID, (v - u) % self.MAX_ID)
        elif isinstance(u, Node):
            return self.ring_distance(u.uid, v.uid)
        else:
            raise TypeError('Unsupported type.')

    def do_transfer(self, path: Path, value: int):
        for i in range(len(path) - 1):
            u = path[i]
            v = path[i + 1]
            if u.get_capacity(v) < value:
                print('Warning: Transfer ({} -> {}: {}) exceeds capacity.'.format(u, v, value))
            uv = self[u][v]
            vu = self[v][u]
            uv['balance'] += value
            uv['num_transfers'] += 1
            vu['num_transfers'] += 1
            # Update redundant/cached values for faster Dijkstra routing.
            self.update_channel_cache(u, v, uv, vu)
