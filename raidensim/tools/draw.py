import math

from raidensim.network.network import Network


def calc3d_positions(net: Network, hole_radius: float, dist_pdf):
    """"
    Helper to position nodes in 3d.
    Nodes are again distributed on rings, their address determining the position on that ring.
    The fuller nodes are (more channels, higher deposits) the higher these nodes are positioned.
    The dist_pdf is expected to be the fullness probability-density function so that nodes are
    evenly distributed on a surface that corresponds to their fullness distribution.
    """
    positions = []
    max_fullness = max(n.fullness for n in net.raw.nodes)
    min_fullness = min(n.fullness for n in net.raw.nodes)
    pdf_scale = 1.0 / max(dist_pdf([n.fullness for n in net.raw.nodes]))
    range_ = float(max_fullness - min_fullness)

    for node in net.raw.nodes:
        # Put x,y on circle of radius 1.
        rad = 2 * math.pi * node.uid / net.config.max_id
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

    bi_edges = {frozenset({a, b}) for a, b in net.raw.edges}
    return positions, list(bi_edges)
