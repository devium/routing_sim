import collections
import math
import numpy as np

import matplotlib
import matplotlib.pyplot as plt
import networkx as nx

from scipy.stats import semicircular

plt.ion()  # interactive mode


class ParetoDistribution(object):
    def __init__(self, a, min_value, max_value):
        """
        Pareto distribution according to
        https://docs.scipy.org/doc/numpy/reference/generated/numpy.random.pareto.html
        Values are in the range [min_value, inf) and `a` determines the shape.

        A higher `a` causes a sharper drop-off in distribution (~= poorer network).

        This implementation is artificially bounded by max_value.
        """
        self.a = a
        self.min_value = min_value
        self.max_value = max_value
        np.random.seed(0)

    def random(self):
        return min(np.random.pareto(self.a) + self.min_value, self.max_value)


class CircleDistribution(object):
    def __init__(self, min_value, max_value):
        """Quarter-circle distribution."""
        self.min_value = min_value
        self.max_value = max_value
        np.random.seed(0)

    def random(self):
        return (self.max_value - self.min_value) * abs(semicircular.rvs()) + self.min_value


# DRAWING helpers ##########################################


def calc_postions(cn):
    """helper to position nodes on a 2d plane as a circle"""
    positions = dict()
    max_deposit = max(n.deposit_per_channel for n in cn.nodes)
    min_deposit = min(n.deposit_per_channel for n in cn.nodes)
    _range = float(max_deposit - min_deposit)

    def scale(node):
        # high deposits to the center
        factor = (node.deposit_per_channel - min_deposit) / _range  # 1 for max deposit
        return 2 / (factor + 1)

    for node in cn.nodes:
        rad = 2 * math.pi * node.uid / float(cn.max_id)
        x, y = math.sin(rad), math.cos(rad)
        s = scale(node)
        positions[node] = x * s, y * s
    return positions


def calc3d_positions(cn):
    """"helper to position nodes in 3d as circles"""
    positions = []
    max_deposit = max(n.deposit_per_channel for n in cn.nodes)
    min_deposit = min(n.deposit_per_channel for n in cn.nodes)
    range_ = float(max_deposit - min_deposit)

    for node in cn.nodes:
        # Nodes are distributed on the round surface of a semi-sphere with the flat bit facing
        # down. Light clients are positioned more toward the flat bottom while full nodes are
        # positioned more toward the round top, reducing visual distance to the light clients.

        # Put x,y on circle of radius 1.
        rad = 2 * math.pi * node.uid / float(cn.max_id)
        x, y = math.sin(rad), math.cos(rad)

        # Height above ground (light client =~0, full node up to 1).
        h = (node.deposit_per_channel - min_deposit) / range_

        # Project x and y onto semi-sphere surface.
        # Bound radius so capped nodes don't accumulate at the top.
        r = max(math.sqrt(1 - h * h), 0.05)
        x *= r
        y *= r
        positions.append([x, y, h])

    edges = set()
    for a_idx, node in enumerate(cn.nodes):
        for c in node.channels:
            b_idx = cn.nodeids.index(c.partner)
            edges.add(frozenset({a_idx, b_idx}))
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


class MyColorMap(matplotlib.colors.Colormap):
    def __call__(self, X, alpha=None, bytes=False):
        if isinstance(X, collections.Iterable):
            return [self._map(x) for x in X]
        return self._map(X)

    def _map(self, X):
        if X == 1:
            return (1, 0, 0, 1)
        else:
            return (0.5, 0.5, 0.5, 0.1)


def draw(cn, path=None, helper_highlight=None):
    from matplotlib.patches import Wedge
    from colorsys import hsv_to_rgb
    edge_color = '#eeeeee'
    pos = calc_postions(cn)

    plt.clf()
    fig = plt.gcf()
    ax = fig.add_subplot(111)

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

    nx.draw(cn.G, pos, edge_color=edge_color, node_size=1, ax=ax)
    if path:
        nx.draw_networkx_edges(cn.G, pos, edgelist=path_to_edges(cn, path), edge_color='r')

    plt.show()
    raw_input('press any key')


def draw3d(cn):
    from doplotly import draw
    node_coords, edges = calc3d_positions(cn)
    print len(edges), "edges"
    draw(node_coords, edges)


def export_obj(cn):
    node_coords, edges = calc3d_positions(cn)
    fh = open('blender_export.obj', mode='w')
    for x, y, z in node_coords:
        fh.write('v {} {} {}\n'.format(x, y, z))
    for a_idx, b_idx in edges:
        fh.write('f {} {}\n'.format(a_idx + 1, b_idx + 1))
