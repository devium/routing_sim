import math

import networkx as nx
from matplotlib import pyplot as plt
from collections import defaultdict
import numpy as np


def calc_positions(nodes, max_id, min_deposit, max_deposit):
    """helper to position nodes on a 2d plane as a circle"""
    positions = dict()
    _range = float(max_deposit - min_deposit)

    def scale(node):
        # high deposits to the center
        factor = (node.deposit_per_channel - min_deposit) / _range  # 1 for max deposit
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
    The radius function determines the radius of the 3D shape at a certain height/fullness. The
    default is a semisphere-like radius calculation.
    Preferably, the radius calculation should match the fullness distribution to achieve an even
    distribution of nodes on the surface of the resulting shape.
    """
    positions = []
    max_fullness = max(n.fullness for n in cn.nodes)
    min_fullness = min(n.fullness for n in cn.nodes)
    pdf_scale = 1.0 / max(dist_pdf([n.fullness for n in cn.nodes]))
    range_ = float(max_fullness - min_fullness)

    for node in cn.nodes:
        # Put x,y on circle of radius 1.
        rad = 2 * math.pi * node.uid / float(cn.max_id)
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

    edges = set()
    for a_idx, node in enumerate(cn.nodes):
        for c in node.channels.values():
            b_idx = cn.nodeids.index(c.partner)
            edges.add(frozenset({a_idx, b_idx}))
    assert len(edges) == sum((len(node.channels) for node in cn.nodes)) / 2
    return positions, list(edges)


def path_to_edges(cn, path):
    edges = []
    assert len(path) > 1
    for i in range(len(path) - 1):
        a, b = path[i:i + 2]
        if a.uid < b.uid:
            edges.append((a, b))
        else:
            edges.append((b, a))
    return edges


def draw2d(cn, path=None, highlighted_nodes=None, helper_highlight=None):
    from matplotlib.patches import Wedge
    from colorsys import hsv_to_rgb
    edge_color = '#eeeeee'

    max_deposit = max(n.deposit_per_channel for n in cn.nodes)
    min_deposit = min(n.deposit_per_channel for n in cn.nodes)
    pos = calc_positions(cn.nodes, cn.max_id, min_deposit, max_deposit)

    plt.clf()
    fig = plt.gcf()
    fig.set_size_inches(8, 8)
    ax = fig.add_subplot(111)
    ax.axis('off')

    for helper in cn.helpers:
        # Angles start at (1,0) ccw, node IDs at (0,1) cw.
        sangle = 90 - (helper.center + helper.range / 2) / float(cn.max_id) * 360
        eangle = 90 - (helper.center - helper.range / 2) / float(cn.max_id) * 360

        # Magic numbers to make colors and radius distinct but deterministic.
        color = hsv_to_rgb(helper.center / 100.0 % 1, 0.9, 0.5)
        radius = helper.center / 1000.0 % 0.3 + 2.1

        if helper == helper_highlight:
            color = (0.3, 1.0, 0)
        alpha = 0.6 if helper == helper_highlight else 0.2
        ax.add_artist(Wedge((0, 0), radius, sangle, eangle, color=color, alpha=alpha))

    nx.draw_networkx(cn.G, pos, edge_color=edge_color, node_size=1, with_labels=False, ax=ax)
    if path:
        nx.draw_networkx_edges(cn.G, pos, edgelist=path_to_edges(cn, path), edge_color='r')

    if highlighted_nodes:
        nx.draw_networkx_nodes(
            cn.G, pos, nodelist=highlighted_nodes, node_shape='x', node_size=12, node_color='b'
        )

    plt.show()


def plot_channel_distribution(cn, ax):
    num_channels = [len(node.channels) for node in cn.nodes]
    max_ = max(num_channels)
    ax.hist(num_channels, bins=range(max_ + 2), align='left', edgecolor='black')
    ax.xaxis.set_ticks(np.arange(0, max_ + 1, 2))
    ax.xaxis.set_ticks(np.arange(1, max_ + 1, 2), minor=True)
    ax.grid(True)


def plot_channel_capacities(cn, ax, max_, num_bins=50, log=False):
    capacities = [cv.capacity for node in cn.nodes for cv in node.channels.values()]
    ax.hist(
        capacities,
        bins=num_bins,
        edgecolor='black',
        range=[0, max_],
        log=log
    )
    ax.grid(True)


def plot_channel_balances(cn, ax, max_, num_bins=50, log=False):
    balances = defaultdict(int)
    for node in cn.nodes:
        for cv in node.channels.values():
            balances[frozenset([node.uid, cv.partner])] = abs(cv.balance)

    balances = list(balances.values())
    ax.hist(balances, bins=num_bins, range=[0, max_], log=log, edgecolor='black')
    ax.grid(True)

    # Return variance of balances.
    return sum(balance * balance for balance in balances) / len(balances)


def plot_channel_imbalances(cn, ax, max_, num_bins=50, log=False):
    imbalances = defaultdict(int)
    for node in cn.nodes:
        for cv in node.channels.values():
            imbalances[frozenset([node.uid, cv.partner])] = \
                abs(cv.deposit - cv.partner_deposit + 2 * cv.balance)

    imbalances = list(imbalances.values())
    ax.hist(imbalances, bins=num_bins, range=[0, max_], edgecolor='black', log=log)
    ax.grid(True)

    # Return variance of imbalances.
    return sum(imbalance * imbalance for imbalance in imbalances) / len(imbalances)
