import pytest

from raidensim.network.annulus import Annulus
from raidensim.network.node import Node
from raidensim.strategy.routing.next_hop.priority_strategy import AnnulusPriorityStrategy
from raidensim.types import DiskCoord


def test_num_slots():
    annulus = Annulus(10)
    assert annulus.max_ring == 10
    assert annulus.num_ring_slots(3) == 8
    assert annulus.num_ring_slots(10) == 1024
    assert annulus.num_slots == 2047


def test_num_connections_to_even():
    annulus = Annulus(10)

    assert annulus.min_ring == 5

    assert annulus.num_connections_to(8, 8) == 0
    assert annulus.num_connections_to(7, 7) == 0

    # Inward connections.
    assert annulus.num_connections_to(10, 9) == 1
    assert annulus.num_connections_to(10, 8) == 0
    assert annulus.num_connections_to(9, 8) == 2
    assert annulus.num_connections_to(9, 7) == 1
    assert annulus.num_connections_to(9, 6) == 0
    assert annulus.num_connections_to(8, 7) == 4
    assert annulus.num_connections_to(8, 6) == 2
    assert annulus.num_connections_to(8, 5) == 1
    assert annulus.num_connections_to(8, 4) == 0
    assert annulus.num_connections_to(7, 6) == 8
    assert annulus.num_connections_to(7, 5) == 4
    assert annulus.num_connections_to(7, 4) == 0
    assert annulus.num_connections_to(6, 5) == 16
    assert annulus.num_connections_to(6, 4) == 0
    assert annulus.num_connections_to(5, 4) == 0

    # Outward connections.
    assert annulus.num_connections_to(10, 11) == 0
    assert annulus.num_connections_to(9, 10) == 2
    assert annulus.num_connections_to(9, 11) == 0
    assert annulus.num_connections_to(8, 9) == 4
    assert annulus.num_connections_to(8, 10) == 0
    assert annulus.num_connections_to(7, 8) == 8
    assert annulus.num_connections_to(7, 9) == 4
    assert annulus.num_connections_to(7, 10) == 0
    assert annulus.num_connections_to(6, 7) == 16
    assert annulus.num_connections_to(6, 8) == 8
    assert annulus.num_connections_to(6, 9) == 0
    assert annulus.num_connections_to(5, 6) == 32
    assert annulus.num_connections_to(5, 7) == 16
    assert annulus.num_connections_to(5, 8) == 8
    assert annulus.num_connections_to(5, 9) == 0


def test_num_connections_to_odd():
    annulus = Annulus(9)

    assert annulus.min_ring == 4

    assert annulus.num_connections_to(8, 8) == 0
    assert annulus.num_connections_to(7, 7) == 0

    # Inward connections.
    assert annulus.num_connections_to(9, 8) == 1
    assert annulus.num_connections_to(9, 7) == 0
    assert annulus.num_connections_to(8, 7) == 2
    assert annulus.num_connections_to(8, 6) == 1
    assert annulus.num_connections_to(8, 5) == 0
    assert annulus.num_connections_to(7, 6) == 4
    assert annulus.num_connections_to(7, 5) == 2
    assert annulus.num_connections_to(7, 4) == 1
    assert annulus.num_connections_to(7, 3) == 0
    assert annulus.num_connections_to(6, 5) == 8
    assert annulus.num_connections_to(6, 4) == 4
    assert annulus.num_connections_to(6, 3) == 0
    assert annulus.num_connections_to(5, 4) == 16
    assert annulus.num_connections_to(5, 3) == 0
    assert annulus.num_connections_to(4, 3) == 0

    # Outward connections.
    assert annulus.num_connections_to(9, 10) == 0
    assert annulus.num_connections_to(8, 9) == 2
    assert annulus.num_connections_to(8, 10) == 0
    assert annulus.num_connections_to(7, 8) == 4
    assert annulus.num_connections_to(7, 9) == 0
    assert annulus.num_connections_to(6, 7) == 8
    assert annulus.num_connections_to(6, 8) == 4
    assert annulus.num_connections_to(6, 9) == 0
    assert annulus.num_connections_to(5, 6) == 16
    assert annulus.num_connections_to(5, 7) == 8
    assert annulus.num_connections_to(5, 8) == 0
    assert annulus.num_connections_to(4, 5) == 32
    assert annulus.num_connections_to(4, 6) == 16
    assert annulus.num_connections_to(4, 7) == 8
    assert annulus.num_connections_to(4, 8) == 0


def test_ring_span_even():
    annulus = Annulus(10)

    assert annulus.inward_ring_span(10) == 1
    assert annulus.inward_ring_span(9) == 2
    assert annulus.inward_ring_span(8) == 3
    assert annulus.inward_ring_span(7) == 2
    assert annulus.inward_ring_span(6) == 1
    assert annulus.inward_ring_span(5) == 0

    assert annulus.outward_ring_span(10) == 0
    assert annulus.outward_ring_span(9) == 1
    assert annulus.outward_ring_span(8) == 1
    assert annulus.outward_ring_span(7) == 2
    assert annulus.outward_ring_span(6) == 2
    assert annulus.outward_ring_span(5) == 3


def test_ring_span_odd():
    annulus = Annulus(9)

    assert annulus.inward_ring_span(9) == 1
    assert annulus.inward_ring_span(8) == 2
    assert annulus.inward_ring_span(7) == 3
    assert annulus.inward_ring_span(6) == 2
    assert annulus.inward_ring_span(5) == 1
    assert annulus.inward_ring_span(4) == 0

    assert annulus.outward_ring_span(9) == 0
    assert annulus.outward_ring_span(8) == 1
    assert annulus.outward_ring_span(7) == 1
    assert annulus.outward_ring_span(6) == 2
    assert annulus.outward_ring_span(5) == 2
    assert annulus.outward_ring_span(4) == 3


def test_num_inward_connections_even():
    annulus = Annulus(10)

    # Regular rings.
    assert annulus.num_inward_connections(11) == 0
    assert annulus.num_inward_connections(10) == 1
    assert annulus.num_inward_connections(9) == 3
    assert annulus.num_inward_connections(8) == 7
    assert annulus.num_inward_connections(7) == 12
    assert annulus.num_inward_connections(6) == 16
    assert annulus.num_inward_connections(5) == 0

    annulus = Annulus(4)

    # Regular rings.
    assert annulus.num_inward_connections(5) == 0
    assert annulus.num_inward_connections(4) == 1
    assert annulus.num_inward_connections(3) == 2
    assert annulus.num_inward_connections(2) == 0


def test_num_inward_connections_odd():
    annulus = Annulus(9)

    # Regular rings.
    assert annulus.num_inward_connections(10) == 0
    assert annulus.num_inward_connections(9) == 1
    assert annulus.num_inward_connections(8) == 3
    assert annulus.num_inward_connections(7) == 7
    assert annulus.num_inward_connections(6) == 12
    assert annulus.num_inward_connections(5) == 16
    assert annulus.num_inward_connections(4) == 0

    annulus = Annulus(5)

    # Regular rings.
    assert annulus.num_inward_connections(6) == 0
    assert annulus.num_inward_connections(5) == 1
    assert annulus.num_inward_connections(4) == 3
    assert annulus.num_inward_connections(3) == 4
    assert annulus.num_inward_connections(2) == 0


def test_num_outward_connections_even():
    annulus = Annulus(10)

    # Regular rings.
    assert annulus.num_outward_connections(11) == 0
    assert annulus.num_outward_connections(10) == 0
    assert annulus.num_outward_connections(9) == 2
    assert annulus.num_outward_connections(8) == 4
    assert annulus.num_outward_connections(7) == 12
    assert annulus.num_outward_connections(6) == 24
    assert annulus.num_outward_connections(5) == 56


def test_num_outward_connections_odd():
    annulus = Annulus(9)

    # Regular rings.
    assert annulus.num_outward_connections(10) == 0
    assert annulus.num_outward_connections(9) == 0
    assert annulus.num_outward_connections(8) == 2
    assert annulus.num_outward_connections(7) == 4
    assert annulus.num_outward_connections(6) == 12
    assert annulus.num_outward_connections(5) == 24
    assert annulus.num_outward_connections(4) == 56


def test_closest_on():
    annulus = Annulus(10)

    assert annulus.closest_on((8, 159), 6) == 39
    assert annulus.closest_on((8, 160), 6) == 40
    assert annulus.closest_on((7, 0), 5) == 0
    assert annulus.closest_on((7, 6), 5) == 1

    assert annulus.closest_on((5, 15), 8) == 123
    assert annulus.closest_on((5, 15), 7) == 61
    assert annulus.closest_on((5, 18), 8) == 147
    assert annulus.closest_on((5, 18), 6) == 36


def test_slot_span():
    annulus = Annulus(8)

    assert annulus.slot_span_on(4, 8) == 156
    assert annulus.slot_span_range_on((4, 8), 8) == (58, 214)

    assert annulus.slot_span_on(4, 7) == 78
    assert annulus.slot_span_range_on((4, 8), 7) == (29, 107)

    assert annulus.slot_span_on(4, 6) == 38
    assert annulus.slot_span_range_on((4, 8), 6) == (15, 53)

    assert annulus.slot_span_on(5, 8) == 36
    assert annulus.slot_span_range_on((5, 15), 8) == (106, 142)
    assert annulus.slot_span_range_on((5, 16), 8) == (114, 150)

    assert annulus.slot_span_on(5, 7) == 18
    assert annulus.slot_span_range_on((5, 15), 7) == (53, 71)
    assert annulus.slot_span_range_on((5, 16), 7) == (57, 75)

    assert annulus.slot_span_range_on((5, 31), 7) == (117, 7)
    assert annulus.slot_span_range_on((5, 0), 7) == (121, 11)


def test_ring_distance():
    assert Annulus.ring_distance(4, 6, 20) == 2
    assert Annulus.ring_distance(6, 4, 20) == 2
    assert Annulus.ring_distance(19, 3, 20) == 4
    assert Annulus.ring_distance(3, 19, 20) == 4
    assert Annulus.ring_distance(0, 10, 20) == 10
    assert Annulus.ring_distance(10, 0, 20) == 10


def test_ring_distance_signed():
    assert Annulus.ring_distance_signed(4, 6, 20) == 2
    assert Annulus.ring_distance_signed(6, 4, 20) == -2
    assert Annulus.ring_distance_signed(19, 3, 20) == 4
    assert Annulus.ring_distance_signed(3, 19, 20) == -4
    assert Annulus.ring_distance_signed(0, 10, 20) == 10
    assert Annulus.ring_distance_signed(10, 0, 20) == -10
    assert Annulus.ring_distance_signed(0, 11, 21) == -10
    assert Annulus.ring_distance_signed(11, 0, 21) == 10


def test_slot_span_closest():
    for num_rings in [3, 4, 7, 8, 9, 10]:
        annulus = Annulus(num_rings)
        for r in range(annulus.min_ring, annulus.max_ring):
            for rt in range(r + 1, num_rings + 1):
                num_ring_slots = 2 ** r
                num_target_ring_slots = 2 ** rt
                half_span = annulus.slot_span_on(r, rt) // 2
                for i in range(num_ring_slots):
                    slot_span_begin, slot_span_end = annulus.slot_span_range_on((r, i), rt)
                    closest = annulus.closest_on((r, i), rt)
                    assert (closest - half_span + 1) % num_target_ring_slots == slot_span_begin
                    assert (closest + half_span + 1) % num_target_ring_slots == slot_span_end


def test_full_properties():
    for num_rings in [3, 4, 7, 8, 9, 10]:
        annulus = Annulus(num_rings)

        def assert_outward_slot_span_coords(coord: DiskCoord):
            r, i = coord

            if r == annulus.min_ring and num_rings % 2 == 1:
                expected_span_begin, expected_span_end = annulus.slot_span_range_on(coord, r + 1)
                assert expected_span_begin == expected_span_end
                assert annulus.slot_span_on(r, r + 1) == 2 ** (r + 1)
                return

            rj = r
            num_ring_slots = 2 ** rj
            i_min = i
            i_max = i
            while rj < num_rings:
                rj += 1
                ij = annulus.closest_on(coord, rj)
                num_ring_slots *= 2
                right_partner_distances = [
                    (annulus.ring_distance_signed(ij, it, 2 ** rj), it)
                    for (rt, it) in annulus.partner_coords((rj - 1, i_min)) if rt == rj
                ]
                left_partner_distances = [
                    (annulus.ring_distance_signed(ij, it, 2 ** rj), it)
                    for (rt, it) in annulus.partner_coords((rj - 1, i_max)) if rt == rj
                ]

                d_min, i_min = min(right_partner_distances)
                d_max, i_max = max(left_partner_distances)

                expected_span_begin, expected_span_end = annulus.slot_span_range_on(coord, rj)
                assert expected_span_begin == i_min
                assert expected_span_end == (i_max + 1) % num_ring_slots

        for r in range(annulus.min_ring, num_rings + 1):
            for i in range(2 ** r):
                partners = list(annulus.partner_coords((r, i)))
                num_partners = len(partners)
                inward_ring_span = max(r - min(r_p for r_p, i_p in partners), 0)
                outward_ring_span = max(max(r_p for r_p, i_p in partners) - r, 0)

                assert num_partners == annulus.num_connections(r)
                assert inward_ring_span == annulus.inward_ring_span(r)
                assert outward_ring_span == annulus.outward_ring_span(r)
                assert_outward_slot_span_coords((r, i))


def test_priority_strategy():
    annulus = Annulus(9)
    priority_strategy = AnnulusPriorityStrategy(annulus)

    coords = [
        (7, 117), (6, 60), (8, 241), (8, 242), (8, 233), (8, 232), (8, 228), (9, 456), (9, 457),
        (9, 466), (9, 467), (8, 250), (8, 251), (7, 124),
        (7, 10), (7, 11), (6, 62), (7, 118), (7, 119), (7, 122),
        (6, 3), (8, 22), (8, 23),
        (7, 114)
    ]
    nodes = {}
    for i, coord in enumerate(coords):
        node = Node(i, 1)
        nodes[coord] = node
        annulus.add_node(node, coord)

    assert priority_strategy.priority(None, nodes[6, 60], {}, nodes[6, 60], 0) == (-1, 0, 0)
    assert priority_strategy.priority(None, nodes[8, 233], {}, nodes[8, 233], 0) == (-1, 0, 0)

    assert priority_strategy.priority(None, nodes[6, 60], {}, nodes[8, 241], 0) == (0, 3, 2)
    assert priority_strategy.priority(None, nodes[6, 60], {}, nodes[8, 242], 0) == (0, 3, 2)
    assert priority_strategy.priority(None, nodes[6, 60], {}, nodes[8, 233], 0) == (0, 3, 34)
    assert priority_strategy.priority(None, nodes[6, 60], {}, nodes[8, 232], 0) == (1, 3, 3)

    assert priority_strategy.priority(None, nodes[6, 60], {}, nodes[8, 228], 0) == (1, 19, 3)
    assert priority_strategy.priority(None, nodes[8, 233], {}, nodes[8, 228], 0) == (1, 19, 0)

    assert priority_strategy.priority(None, nodes[6, 60], {}, nodes[9, 456], 0) == (1, 20, 4)
    assert priority_strategy.priority(None, nodes[8, 233], {}, nodes[9, 456], 0) == (1, 20, 2)

    assert priority_strategy.priority(None, nodes[6, 60], {}, nodes[9, 457], 0) == (1, 18, 4)
    assert priority_strategy.priority(None, nodes[8, 233], {}, nodes[9, 457], 0) == (1, 18, 2)

    assert priority_strategy.priority(None, nodes[8, 233], {}, nodes[9, 466], 0) == (0, 2, 1)
    assert priority_strategy.priority(None, nodes[8, 233], {}, nodes[9, 467], 0) == (0, 2, 1)

    assert priority_strategy.priority(None, nodes[6, 60], {}, nodes[8, 250], 0) == (0, 3, 34)
    assert priority_strategy.priority(None, nodes[6, 60], {}, nodes[8, 251], 0) == (1, 3, 3)
    assert priority_strategy.priority(None, nodes[7, 124], {}, nodes[8, 250], 0) == (0, 2, 6)
    assert priority_strategy.priority(None, nodes[7, 124], {}, nodes[8, 251], 0) == (1, 3, 2)

    assert priority_strategy.priority(None, nodes[7, 10], {}, nodes[6, 62], 0) == (1, 101, 1)
    assert priority_strategy.priority(None, nodes[7, 11], {}, nodes[6, 62], 0) == (1, 109, 1)

    assert priority_strategy.priority(None, nodes[7, 118], {}, nodes[6, 62], 0) == (1, 45, 1)
    assert priority_strategy.priority(None, nodes[7, 119], {}, nodes[6, 62], 0) == (1, 37, 1)

    assert priority_strategy.priority(None, nodes[7, 122], {}, nodes[6, 62], 0) == (1, 13, 1)

    assert priority_strategy.priority(None, nodes[6, 3], {}, nodes[8, 23], 0) == (1, 3, 3)
    assert priority_strategy.priority(None, nodes[8, 22], {}, nodes[8, 23], 0) == (1, 3, 0)

    assert priority_strategy.priority(None, nodes[6, 60], {}, nodes[7, 114], 0) == (1, 17, 2)
    assert priority_strategy.priority(None, nodes[8, 233], {}, nodes[7, 114], 0) == (1, 17, 1)
