import random
import time
from itertools import cycle
from typing import List, Tuple, Callable, Union

import imageio
import matplotlib.pyplot as plt
import networkx as nx
import os
import numpy as np

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
        self.cached_render_pos = None

    def join_nodes(self):
        print('Joining nodes.')
        tic = time.time()
        for i in range(self.config.num_nodes):
            toc = time.time()
            if toc - tic > 5:
                tic = toc
                print('Joining node {}/{}'.format(i, self.config.num_nodes))

            while True:
                uid = random.randrange(self.config.max_id)
                fullness = self.config.fullness_dist.random()
                node = Node(uid, fullness)
                if node not in self.raw:
                    break

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
            nodes: List[Node] = None,
            channels: List[Tuple[Node, Node]] = None,
            paths: List[Path] = None,
            highlighted_nodes: List[List[Node]] = None,
            node_color: Union[Callable[[Node], int], str] = 'grey',
            channel_color: Union[Callable[[Node, Node], int], str] = 'lightgrey',
            labeling_strategy: Callable[[Node], str]=None,
            filepath: str=None
    ) -> bool:
        if not self.cached_render_pos or len(self.cached_render_pos) != self.raw.number_of_nodes():
            self.cached_render_pos = self.config.position_strategy.map(self.raw.nodes)
        first_pos = next(iter(self.cached_render_pos.values()))
        if len(first_pos) > 2:
            print('Warning: Cannot draw networks with rank higher than 2.')
            return False
        elif len(first_pos) == 1:
            for node, pos_value in self.cached_render_pos.items():
                self.cached_render_pos[node] = np.append(pos_value, [0])

        plt.clf()
        fig = plt.gcf()
        fig.set_size_inches(12, 12)
        ax = fig.add_subplot(111)
        ax.axis('off')
        xlim, ylim = self.config.position_strategy.plot_limits
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)

        node_colors = ['grey', 'r', 'g', 'b', 'c']
        node_color_cycle = cycle(node_colors)

        channel_colors = ['lightgrey', 'r', 'g', 'b', 'c']

        if isinstance(node_color, Callable):
            node_color = [node_colors[node_color(u) % len(node_colors)] for u in self.raw.nodes]
        if isinstance(channel_color, Callable):
            channel_color = [
                channel_colors[channel_color(u, v) % len(channel_colors)] for u,v in self.raw.edges
            ]

        nx.draw_networkx_nodes(
            self.raw,
            self.cached_render_pos,
            nodelist=nodes,
            node_color=node_color,
            node_size=1,
            with_labels=False,
            ax=ax
        )

        nx.draw_networkx_edges(
            self.raw,
            self.cached_render_pos,
            edgelist=channels,
            edge_color=channel_color,
            arrows=False,
            ax=ax
        )

        if paths:
            edges = []
            for path in paths:
                for i in range(len(path) - 1):
                    edges.append((path[i], path[i+1]))
            nx.draw_networkx_edges(
                self.raw, self.cached_render_pos, edgelist=edges, edge_color='b', arrows=False,
                ax=ax
            )

        if labeling_strategy:
            labels = {node: labeling_strategy(node) for node in self.raw.nodes}
            nx.draw_networkx_labels(self.raw, self.cached_render_pos, labels, font_size=6)

        if highlighted_nodes:
            for highlighted_node_set in highlighted_nodes:
                nx.draw_networkx_nodes(
                    self.raw,
                    self.cached_render_pos,
                    nodelist=highlighted_node_set,
                    node_size=8,
                    node_color=next(node_color_cycle),
                    ax=ax
                )

        if filepath:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            fig.savefig(filepath)
        else:
            plt.show()

        return True

    def draw_gif(
            self,
            source: Node,
            target: Node,
            path_history: List[Path],
            max_frames: int,
            dirpath: str,
            channel_color: Union[Callable[[Node, Node], int], str] = 'lightgrey',
    ):
        visited = {source}
        gif_filenames = []

        os.makedirs(dirpath, exist_ok=True)
        for isp, subpath in enumerate(path_history):
            visited |= set(subpath)
            if isp > max_frames - 1:
                break
            filename = 'step_{:04d}.png'.format(isp)
            gif_filenames.append(filename)
            if not self.draw(
                channels=[],
                paths=[subpath],
                highlighted_nodes=[visited, [source, target]],
                filepath=os.path.join(dirpath, filename),
                channel_color=channel_color
            ):
                return

        filename = 'animation.gif'
        with imageio.get_writer(
                os.path.join(dirpath, filename), mode='I', fps=3
        ) as writer:
            for filename in gif_filenames:
                image = imageio.imread(os.path.join(dirpath, filename))
                writer.append_data(image)
