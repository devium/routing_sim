import random
import time
from itertools import cycle
from typing import List, Tuple, Callable

import imageio
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge
import networkx as nx
import os

from raidensim.network.config import NetworkConfiguration
from raidensim.network.raw_network import RawNetwork
from raidensim.network.node import Node
from raidensim.types import Path


class Network(object):
    def __init__(self, config: NetworkConfiguration):
        self.config = config

        random.seed(0)
        self.raw = RawNetwork()
        self.join_nodes()
        self.raw.remove_isolated()

    def join_nodes(self):
        print('Joining nodes.')
        tic = time.time()
        for i in range(self.config.num_nodes):
            toc = time.time()
            if toc - tic > 5:
                tic = toc
                print('Joining node {}/{}'.format(i, self.config.num_nodes))

            uid = random.randrange(self.config.max_id)
            fullness = self.config.fullness_dist.random()
            node = Node(uid, fullness)
            self.raw.add_node(node)
            self.config.join_strategy.join(self.raw, node)

    def reset(self):
        print('Resetting network.')
        random.seed(0)
        self.raw.reset_channels()

    def _calc_sector_angles(self, center, width):
        # Start angle and end angle.
        sangle = 90 - (center + width / 2) / float(self.config.max_id) * 360
        eangle = 90 - (center - width / 2) / float(self.config.max_id) * 360
        return sangle, eangle

    def draw(
            self,
            paths: List[Path] = None,
            highlighted_nodes: List[List[Node]] = None,
            node_color_mapping: Callable[[Node], int] = None,
            channel_color_mapping: Callable[[Node, Node], int] = None,
            kademlia_center: int=0,
            kademlia_buckets: List[Tuple[int,int]]=None,
            draw_labels: bool=False,
            heatmap_attr: str=None,
            filepath: str=None
    ):
        pos = self.config.position_strategy.map(self.raw.nodes)

        plt.clf()
        fig = plt.gcf()
        fig.set_size_inches(12, 12)
        ax = fig.add_subplot(111)
        ax.axis('off')

        colors = ['r', 'g', 'b', 'c']
        color_cycle = cycle(colors)

        node_color = 'grey'
        if node_color_mapping:
            default_color = node_color
            node_color = []
            for node in self.raw.nodes:
                mapping = node_color_mapping(node)
                if mapping == -1:
                    node_color.append(default_color)
                else:
                    node_color.append(colors[mapping % len(colors)])

        edge_color = 'lightgrey'
        if channel_color_mapping:
            default_color = edge_color
            edge_color = []
            for u, v in self.raw.edges:
                mapping = channel_color_mapping(u, v)
                if mapping == -1:
                    edge_color.append(default_color)
                else:
                    edge_color.append(colors[mapping % len(colors)])

        if heatmap_attr:
            heatmap_values = [
                abs(self.raw[a][b][heatmap_attr]) for a, b in self.raw.edges
            ]
            max_ = max(max(heatmap_values), 1)
            color = [x / max_ * 100 for x in heatmap_values]
            nx.draw_networkx(
                self.raw,
                pos,
                node_color=node_color,
                edge_color=color,
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
                node_color=node_color,
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
            nx.draw_networkx_edges(self.raw, pos, edgelist=edges, edge_color='b', arrows=False)

        if draw_labels:
            labels = {node: node.uid for node in self.raw.nodes}
            nx.draw_networkx_labels(self.raw, pos, labels, font_size=5)

        if highlighted_nodes:
            for highlighted_node_set in highlighted_nodes:
                nx.draw_networkx_nodes(
                    self.raw,
                    pos,
                    nodelist=highlighted_node_set,
                    node_size=8,
                    node_color=next(color_cycle)
                )

        if kademlia_buckets:
            for bucket in kademlia_buckets:
                lcenter = kademlia_center - bucket[0] - (bucket[1] - bucket[0]) // 2
                rcenter = kademlia_center + bucket[0] + (bucket[1] - bucket[0]) // 2
                width = bucket[1] - bucket[0]

                color = next(color_cycle)
                sangle, eangle = self._calc_sector_angles(lcenter, width)
                ax.add_artist(Wedge((0, 0), 2, sangle, eangle, color=color, alpha=0.1))
                sangle, eangle = self._calc_sector_angles(rcenter, width)
                ax.add_artist(Wedge((0, 0), 2, sangle, eangle, color=color, alpha=0.1))

        if filepath:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            fig.savefig(filepath)
        else:
            plt.show()

    def draw_gif(
            self,
            source: Node,
            target: Node,
            path_history: List[Path],
            max_frames: int,
            dirpath: str,
            channel_color_mapping: Callable[[Node, Node], int] = None,
    ):
        visited = {source}
        gif_filenames = []

        for isp, subpath in enumerate(path_history):
            visited |= set(subpath)
            if isp > max_frames - 1:
                break
            filename = 'step_{:04d}.png'.format(isp)
            gif_filenames.append(filename)
            self.draw(
                [subpath], [visited, [source, target]],
                filepath=os.path.join(dirpath, filename),
                channel_color_mapping=channel_color_mapping
            )

        filename = 'animation.gif'
        with imageio.get_writer(
                os.path.join(dirpath, filename), mode='I', fps=3
        ) as writer:
            for filename in gif_filenames:
                image = imageio.imread(os.path.join(dirpath, filename))
                writer.append_data(image)
