import math
from itertools import cycle
from typing import List, Tuple

import networkx as nx
import os
from matplotlib import pyplot as plt

from raidensim.network.channel_network import ChannelNetwork
from raidensim.network.node import Node
from raidensim.types import Path


def calc_positions(nodes, max_id, min_fullness, max_fullness):
    """helper to position nodes on a 2d plane as a circle"""
    positions = dict()
    _range = float(max_fullness - min_fullness)

    def scale(node):
        # high deposits to the center
        factor = (node.fullness - min_fullness) / _range  # 1 for max deposit
        return 2 / (factor + 1)

    for node in nodes:
        rad = 2 * math.pi * node.uid / float(max_id)
        x, y = math.sin(rad), math.cos(rad)
        s = scale(node)
        positions[node] = x * s, y * s
    return positions


def calc3d_positions(cn, hole_radius, dist_pdf):
    """"
    Helper to position nodes in 3d.
    Nodes are again distributed on rings, their address determining the position on that ring.
    The fuller nodes are (more channels, higher deposits) the higher these nodes are positioned.
    The dist_pdf is expected to be the fullness probability-density function so that nodes are
    evenly distributed on a surface that corresponds to their fullness distribution.
    """
    positions = []
    max_fullness = max(n.fullness for n in cn.nodes)
    min_fullness = min(n.fullness for n in cn.nodes)
    pdf_scale = 1.0 / max(dist_pdf([n.fullness for n in cn.nodes]))
    range_ = float(max_fullness - min_fullness)

    for node in cn.nodes:
        # Put x,y on circle of radius 1.
        rad = 2 * math.pi * node.uid / float(cn.MAX_ID)
        x, y = math.sin(rad), math.cos(rad)

        # Height above ground (light client =~0, full node up to 1).
        h = (node.fullness - min_fullness) / range_

        # Adjust radius to evenly distribute nodes on the 3D surface.
        r = dist_pdf(h) * pdf_scale
        # Make hole at top by moving higher nodes out a bit (min radius = hole_radius).
        r = (1 - hole_radius) * r + hole_radius
        x *= r
        y *= r
        positions.append([x, y, h])

    bi_edges = {frozenset({a, b}) for a, b in cn.edges}
    return positions, list(bi_edges)


def calc_sector_angles(max_id, center, width):
    # Start angle and end angle.
    sangle = 90 - (center + width / 2) / float(max_id) * 360
    eangle = 90 - (center - width / 2) / float(max_id) * 360
    return sangle, eangle


def draw2d(
        cn: ChannelNetwork,
        paths: List[Path] = None,
        highlighted_nodes: List[List[Node]] = None,
        helper_highlight=None,
        kademlia_center: int=0,
        kademlia_buckets: List[Tuple[int,int]]=None,
        draw_labels: bool=False,
        heatmap_attr: str=None,
        filepath: str=None
):
    from matplotlib.patches import Wedge
    from colorsys import hsv_to_rgb
    edge_color = '#eeeeee'

    max_fullness = max(n.fullness for n in cn.nodes)
    min_fullness = min(n.fullness for n in cn.nodes)
    pos = calc_positions(cn.nodes, cn.MAX_ID, min_fullness, max_fullness)

    plt.clf()
    fig = plt.gcf()
    fig.set_size_inches(12, 12)
    ax = fig.add_subplot(111)
    ax.axis('off')

    for helper in cn.helpers:
        # Angles start at (1,0) ccw, node IDs at (0,1) cw.
        sangle, eangle = calc_sector_angles(cn.MAX_ID, helper.center, helper.range)

        # Magic numbers to make colors and radius distinct but deterministic.
        color = hsv_to_rgb(helper.center / 100.0 % 1, 0.9, 0.5)
        radius = helper.center / 1000.0 % 0.3 + 2.1

        if helper == helper_highlight:
            color = (0.3, 1.0, 0)
        alpha = 0.6 if helper == helper_highlight else 0.2
        ax.add_artist(Wedge((0, 0), radius, sangle, eangle, color=color, alpha=alpha))

    if heatmap_attr:
        heatmap_values = [abs(cn[a][b][heatmap_attr]) for a, b in cn.edges]
        max_ = max(heatmap_values)
        colors = [x / max_ * 100 for x in heatmap_values]
        nx.draw_networkx(
            cn,
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
            cn, pos, edge_color=edge_color, node_size=1, with_labels=False, ax=ax, arrows=False
        )
    if paths:
        edges = []
        for path in paths:
            for i in range(len(path) - 1):
                edges.append((path[i], path[i+1]))
        nx.draw_networkx_edges(cn, pos, edgelist=edges, edge_color='r', arrows=False)

    if draw_labels:
        labels = {node: node.uid for node in cn.nodes}
        nx.draw_networkx_labels(cn, pos, labels, font_size=6)

    if highlighted_nodes:
        colors = cycle(['r', 'b', 'c', 'g'])
        for highlighted_node_set in highlighted_nodes:
            nx.draw_networkx_nodes(
                cn, pos, nodelist=highlighted_node_set, node_size=12, node_color=next(colors)
            )

    if kademlia_buckets:
        colors = cycle(['r', 'b', 'c', 'g'])
        for bucket in kademlia_buckets:
            lcenter = kademlia_center - bucket[0] - (bucket[1] - bucket[0]) // 2
            rcenter = kademlia_center + bucket[0] + (bucket[1] - bucket[0]) // 2
            width = bucket[1] - bucket[0]

            color = next(colors)
            sangle, eangle = calc_sector_angles(cn.MAX_ID, lcenter, width)
            ax.add_artist(Wedge((0, 0), 2, sangle, eangle, color=color, alpha=0.1))
            sangle, eangle = calc_sector_angles(cn.MAX_ID, rcenter, width)
            ax.add_artist(Wedge((0, 0), 2, sangle, eangle, color=color, alpha=0.1))

    if filepath:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        fig.savefig(filepath)
    else:
        plt.show()
