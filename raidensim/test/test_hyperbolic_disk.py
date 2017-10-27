import math
import pytest

import numpy as np

from raidensim.network.hyperbolic_disk import HyperbolicDisk


def test_coord_to_polar():
    disk = HyperbolicDisk(4, 1)

    r, theta = disk.coord_to_polar([4, 0])
    assert math.isclose(r, 1)
    assert math.isclose(theta, 0)

    r, theta = disk.coord_to_polar([4, 4])
    assert math.isclose(r, 1)
    assert math.isclose(theta, 0.5 * math.pi)

    r, theta = disk.coord_to_polar([3, 2])
    assert math.isclose(r, 0.75)
    assert math.isclose(theta, 0.5 * math.pi)

    r, theta = disk.coord_to_polar([4, 9])
    assert math.isclose(r, 1)
    assert math.isclose(theta, 1.125 * math.pi)

    r, theta = disk.coord_to_polar([1, 1])
    assert math.isclose(r, 0.25)
    assert math.isclose(theta, math.pi)


def test_coord_distance():
    disk = HyperbolicDisk(4, 1)

    assert math.isclose(disk.coord_distance([4, 0], [3, 0]), math.cosh(0.25))
    assert math.isclose(disk.coord_distance([4, 6], [0, 0]), math.cosh(1))
    assert math.isclose(disk.coord_distance([3, 4], [2, 2]), math.cosh(0.25))
    assert math.isclose(disk.coord_distance([3, 3], [0, 0]), math.cosh(0.75))
    assert math.isclose(disk.coord_distance([3, 7], [3, 6]), disk.coord_distance([3, 6], [3, 7]))
    assert math.isclose(disk.coord_distance([3, 7], [3, 6]), disk.coord_distance([3, 6], [3, 5]))
    assert disk.coord_distance([4, 7], [4, 8]) < disk.coord_distance([4, 7], [4, 9])
    assert disk.coord_distance([4, 7], [4, 9]) < 2 * disk.coord_distance([4, 7], [4, 8])


def test_inner_partners():
    disk = HyperbolicDisk(5, 2)
    partners = list(disk.inner_partner_coords([4, 15]))
    assert len(partners) == 13
    expected = [
        [0, 0],
        [1, 1],
        [1, 0],
        [2, 3],
        [2, 0],
        [3, 7],
        [3, 0],
        [3, 6],
        [3, 1],
        [4, 0],
        [4, 14],
        [4, 1],
        [4, 13]
    ]
    assert all(np.array_equal(partners[i], expected[i]) for i in range(len(expected)))

    disk = HyperbolicDisk(5, 4)
    partners = list(disk.inner_partner_coords([4, 15]))
    assert len(partners) == 9
    expected = [
        [0, 0],
        [1, 1],
        [1, 0],
        [2, 3],
        [2, 0],
        [3, 7],
        [3, 0],
        [4, 0],
        [4, 14]
    ]
    assert all(np.array_equal(partners[i], expected[i]) for i in range(len(expected)))

    disk = HyperbolicDisk(5, 8)
    partners = list(disk.inner_partner_coords([4, 15]))
    assert len(partners) == 6
    expected = [
        [0, 0],
        [1, 1],
        [1, 0],
        [2, 0],
        [3, 7],
        [3, 0]
    ]
    assert all(np.array_equal(partners[i], expected[i]) for i in range(len(expected)))


def test_outer_partners():
    disk = HyperbolicDisk(5, 4)
    partners = list(disk.outer_partner_coords([3, 5]))
    assert len(partners) == 10
    expected = [
        [4, 10],
        [4, 11],
        [4, 9],
        [4, 12],
        [4, 8],
        [5, 20],
        [5, 21],
        [5, 19],
        [5, 22],
        [5, 18]
    ]
    assert all(np.array_equal(partners[i], expected[i]) for i in range(len(expected)))


def test_partner_count():
    disk = HyperbolicDisk(6, 16)

