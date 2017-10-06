import time
from itertools import cycle
from typing import List, Tuple
import matplotlib.pyplot as plt
import networkx as nx
import os

from raidensim.network.config import NetworkConfiguration
from raidensim.network.raw_network import RawNetwork
from raidensim.network.node import Node
from raidensim.types import Path


class Network(object):
    def __init__(self, config: NetworkConfiguration):
        self.config = config
        self.raw = RawNetwork()

        self.raw.generate_nodes(config.num_nodes, config.max_id, config.fullness_dist)
        self.connect_nodes()
        self.raw.remove_isolated()

    def connect_nodes(self):
        print('Connecting nodes.')
        tic = time.time()
        for i, node in enumerate(self.raw.nodes):
            toc = time.time()
            if toc - tic > 5:
                tic = toc
                print('Connecting node {}/{}'.format(i, len(self.raw.nodes)))
            self.config.join_strategy.join(self.raw, node)

    def _calc_sector_angles(self, center, width):
        # Start angle and end angle.
        sangle = 90 - (center + width / 2) / float(self.config.max_id) * 360
        eangle = 90 - (center - width / 2) / float(self.config.max_id) * 360
        return sangle, eangle

    def draw(
            self,
            paths: List[Path] = None,
            highlighted_nodes: List[List[Node]] = None,
            kademlia_center: int=0,
            kademlia_buckets: List[Tuple[int,int]]=None,
            draw_labels: bool=False,
            heatmap_attr: str=None,
            filepath: str=None
    ):
        from matplotlib.patches import Wedge
        edge_color = '#eeeeee'

        pos = self.config.join_strategy.position_strategy.map(self.raw.nodes)

        plt.clf()
        fig = plt.gcf()
        fig.set_size_inches(12, 12)
        ax = fig.add_subplot(111)
        ax.axis('off')

        if heatmap_attr:
            heatmap_values = [
                abs(self.raw[a][b][heatmap_attr]) for a, b in self.raw.edges
            ]
            max_ = max(heatmap_values)
            colors = [x / max_ * 100 for x in heatmap_values]
            nx.draw_networkx(
                self.raw,
                pos,
                edge_color=colors,
                edge_cmap=plt.cm.inferno,
                node_size=1,
                with_labels=False,
                ax=ax,
                arrows=False
            )
        else:
            nx.draw_networkx(
                self.raw,
                pos,
                edge_color=edge_color,
                node_size=1,
                with_labels=False,
                ax=ax,
                arrows=False
            )
        if paths:
            edges = []
            for path in paths:
                for i in range(len(path) - 1):
                    edges.append((path[i], path[i+1]))
            nx.draw_networkx_edges(self.raw, pos, edgelist=edges, edge_color='r', arrows=False)

        if draw_labels:
            labels = {node: node.uid for node in self.raw.nodes}
            nx.draw_networkx_labels(self.raw, pos, labels, font_size=6)

        if highlighted_nodes:
            colors = cycle(['r', 'b', 'c', 'g'])
            for highlighted_node_set in highlighted_nodes:
                nx.draw_networkx_nodes(
                    self.raw,
                    pos,
                    nodelist=highlighted_node_set,
                    node_size=12,
                    node_color=next(colors)
                )

        if kademlia_buckets:
            colors = cycle(['r', 'b', 'c', 'g'])
            for bucket in kademlia_buckets:
                lcenter = kademlia_center - bucket[0] - (bucket[1] - bucket[0]) // 2
                rcenter = kademlia_center + bucket[0] + (bucket[1] - bucket[0]) // 2
                width = bucket[1] - bucket[0]

                color = next(colors)
                sangle, eangle = self._calc_sector_angles(lcenter, width)
                ax.add_artist(Wedge((0, 0), 2, sangle, eangle, color=color, alpha=0.1))
                sangle, eangle = self._calc_sector_angles(rcenter, width)
                ax.add_artist(Wedge((0, 0), 2, sangle, eangle, color=color, alpha=0.1))

        if filepath:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            fig.savefig(filepath)
        else:
            plt.show()

