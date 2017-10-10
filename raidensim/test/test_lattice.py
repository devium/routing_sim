import pytest

from raidensim.network.lattice import Lattice
from raidensim.network.node import Node


def test_gaps():
    lattice = Lattice()
    nodes = [Node(i, 0) for i in range(10)]

    # 0 X
    #   0
    lattice.add_node(nodes[0], 0, 0)
    assert len(lattice.coord_to_node) == 1
    assert len(lattice.gaps) == 0

    # 0 XX
    #   0
    lattice.add_node(nodes[1], 1, 0)
    assert len(lattice.coord_to_node) == 2
    assert len(lattice.gaps) == 0

    #   OX
    # 0 XX
    #   0
    lattice.add_node(nodes[2], 1, 1)
    assert len(lattice.coord_to_node) == 3
    assert len(lattice.gaps) == 1
    assert (0, 1) not in lattice.coord_to_node

    #   XOOOX
    # 0 OOOXX
    #      0
    lattice.add_node(nodes[3], -3, 1)
    assert len(lattice.coord_to_node) == 4
    assert len(lattice.gaps) == 6
    assert all(
        coord not in lattice.coord_to_node
        for coord in [(-2, 1), (-1, 1), (0, 1), (-3, 0), (-2, 0), (-1, 0)]
    )

    #   XOOOXOOO
    # 0 OOOXXOOO
    #   OOOOOOOO
    #   OOOOOOOX
    #      0
    lattice.add_node(nodes[4], 4, -2)
    assert len(lattice.coord_to_node) == 5
    assert len(lattice.gaps) == 6 + 6 + 8 + 7

    print('\n' + lattice.draw_ascii())


def test_free_coords():
    lattice = Lattice()
    nodes = [Node(i, 0) for i in range(10)]

    assert lattice.get_free_coord() == (0, 0)

    lattice.add_node(nodes[0], 0, 0)
    assert lattice.get_free_coord() == (1, 0)

    lattice.add_node(nodes[1], 1, 0)
    assert lattice.get_free_coord() == (0, 1)

    lattice.add_node(nodes[2], 0, 1)
    assert len(lattice.gaps) == 1
    assert (1, 1) in lattice.gaps
    assert lattice.get_free_coord() == (1, 1)

    lattice.add_node(nodes[3], 1, 1)
    assert len(lattice.gaps) == 0
    assert lattice.get_free_coord() == (-1, 0)

    lattice.add_node(nodes[4], -1, 0)
    assert len(lattice.gaps) == 1
    assert (-1, 1) in lattice.gaps
    assert lattice.get_free_coord() == (-1, 1)

    lattice.add_node(nodes[5], -1, 1)
    assert len(lattice.gaps) == 0
    assert lattice.get_free_coord() == (0, -1)

    lattice.add_node(nodes[6], 0, -1)

    print('\n' + lattice.draw_ascii())


def test_nodes_at_distance():
    lattice = Lattice()
    for x in range(-2, 2):
        for y in range(-2, 2):
            lattice.add_node(Node(y * 4 + x, 0), x, y)

    print('\n' + lattice.draw_ascii())

    nodes = lattice.get_nodes_at_distance((-2, 0), 2)
    coords = [lattice.node_to_coord[node] for node in nodes]
    assert len(coords) == 4
    assert all(coord in coords for coord in [(-1, 1), (0, 0), (-1, -1), (-2, -2)])

    nodes = lattice.get_nodes_at_distance((-1, -1), 1)
    coords = [lattice.node_to_coord[node] for node in nodes]
    assert len(coords) == 4
    assert all(coord in coords for coord in [(-2, -1), (-1, 0), (0, -1), (-1, -2)])

    nodes = lattice.get_nodes_at_distance((1, -1), 3)
    coords = [lattice.node_to_coord[node] for node in nodes]
    assert len(coords) == 4
    assert all(coord in coords for coord in [(-1, -2), (-2, -1), (-1, 0), (0, 1)])
