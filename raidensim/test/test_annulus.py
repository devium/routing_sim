import heapq

import pytest

from raidensim.network.annulus import Annulus
from raidensim.types import DiskCoord


def test_num_slots():
    annulus = Annulus(10)
    assert annulus.max_ring == 10
    assert annulus.num_ring_slots(3) == 8
    assert annulus.num_ring_slots(10) == 1024
    assert annulus.num_slots == 2047


def test_num_connections_to_even():
    annulus = Annulus(10)

    assert annulus.capped_ring == 5

    assert annulus.num_connections_to(3, 3) == 0
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
    assert annulus.num_connections_to(7, 4) == 2
    assert annulus.num_connections_to(7, 3) == 1
    assert annulus.num_connections_to(7, 2) == 0
    assert annulus.num_connections_to(6, 5) == 16
    assert annulus.num_connections_to(6, 4) == 8
    assert annulus.num_connections_to(6, 3) == 4
    assert annulus.num_connections_to(6, 2) == 2
    assert annulus.num_connections_to(6, 1) == 1
    assert annulus.num_connections_to(6, 0) == 0

    # Inward ring connections capped by number of available slots.
    assert annulus.num_connections_to(5, 4) == 16
    assert annulus.num_connections_to(5, 3) == 8
    assert annulus.num_connections_to(5, 2) == 4
    assert annulus.num_connections_to(5, 1) == 2
    assert annulus.num_connections_to(5, 0) == 1
    assert annulus.num_connections_to(4, 3) == 8
    assert annulus.num_connections_to(4, 2) == 4
    assert annulus.num_connections_to(4, 1) == 2
    assert annulus.num_connections_to(4, 0) == 1
    assert annulus.num_connections_to(3, 2) == 4
    assert annulus.num_connections_to(3, 1) == 2
    assert annulus.num_connections_to(3, 0) == 1
    assert annulus.num_connections_to(2, 1) == 2
    assert annulus.num_connections_to(2, 0) == 1
    assert annulus.num_connections_to(1, 0) == 1

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

    # Outward connections partially capped by available slots.
    assert annulus.num_connections_to(4, 5) == 32
    assert annulus.num_connections_to(4, 6) == 32
    assert annulus.num_connections_to(4, 7) == 16
    assert annulus.num_connections_to(4, 8) == 0
    assert annulus.num_connections_to(3, 4) == 16
    assert annulus.num_connections_to(3, 5) == 32
    assert annulus.num_connections_to(3, 6) == 32
    assert annulus.num_connections_to(3, 7) == 16
    assert annulus.num_connections_to(3, 8) == 0
    assert annulus.num_connections_to(2, 3) == 8
    assert annulus.num_connections_to(2, 4) == 16
    assert annulus.num_connections_to(2, 5) == 32
    assert annulus.num_connections_to(2, 6) == 32
    assert annulus.num_connections_to(2, 7) == 0
    assert annulus.num_connections_to(1, 2) == 4
    assert annulus.num_connections_to(1, 3) == 8
    assert annulus.num_connections_to(1, 4) == 16
    assert annulus.num_connections_to(1, 5) == 32
    assert annulus.num_connections_to(1, 6) == 32
    assert annulus.num_connections_to(1, 7) == 0
    assert annulus.num_connections_to(0, 1) == 2
    assert annulus.num_connections_to(0, 2) == 4
    assert annulus.num_connections_to(0, 3) == 8
    assert annulus.num_connections_to(0, 4) == 16
    assert annulus.num_connections_to(0, 5) == 32
    assert annulus.num_connections_to(0, 6) == 0


def test_num_connections_to_odd():
    annulus = Annulus(9)

    assert annulus.capped_ring == 5

    assert annulus.num_connections_to(3, 3) == 0
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
    assert annulus.num_connections_to(6, 3) == 2
    assert annulus.num_connections_to(6, 2) == 1
    assert annulus.num_connections_to(6, 1) == 0

    # Inward ring connections capped by number of available slots.
    assert annulus.num_connections_to(5, 4) == 16
    assert annulus.num_connections_to(5, 3) == 8
    assert annulus.num_connections_to(5, 2) == 4
    assert annulus.num_connections_to(5, 1) == 2
    assert annulus.num_connections_to(5, 0) == 1
    assert annulus.num_connections_to(4, 3) == 8
    assert annulus.num_connections_to(4, 2) == 4
    assert annulus.num_connections_to(4, 1) == 2
    assert annulus.num_connections_to(4, 0) == 1
    assert annulus.num_connections_to(3, 2) == 4
    assert annulus.num_connections_to(3, 1) == 2
    assert annulus.num_connections_to(3, 0) == 1
    assert annulus.num_connections_to(2, 1) == 2
    assert annulus.num_connections_to(2, 0) == 1
    assert annulus.num_connections_to(1, 0) == 1

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

    # Outward connections partially capped by available slots.
    assert annulus.num_connections_to(4, 5) == 32
    assert annulus.num_connections_to(4, 6) == 16
    assert annulus.num_connections_to(4, 7) == 8
    assert annulus.num_connections_to(4, 8) == 0
    assert annulus.num_connections_to(3, 4) == 16
    assert annulus.num_connections_to(3, 5) == 32
    assert annulus.num_connections_to(3, 6) == 16
    assert annulus.num_connections_to(3, 7) == 0
    assert annulus.num_connections_to(2, 3) == 8
    assert annulus.num_connections_to(2, 4) == 16
    assert annulus.num_connections_to(2, 5) == 32
    assert annulus.num_connections_to(2, 6) == 16
    assert annulus.num_connections_to(2, 7) == 0
    assert annulus.num_connections_to(1, 2) == 4
    assert annulus.num_connections_to(1, 3) == 8
    assert annulus.num_connections_to(1, 4) == 16
    assert annulus.num_connections_to(1, 5) == 32
    assert annulus.num_connections_to(1, 6) == 0
    assert annulus.num_connections_to(0, 1) == 2
    assert annulus.num_connections_to(0, 2) == 4
    assert annulus.num_connections_to(0, 3) == 8
    assert annulus.num_connections_to(0, 4) == 16
    assert annulus.num_connections_to(0, 5) == 32
    assert annulus.num_connections_to(0, 6) == 0


def test_ring_span_even():
    annulus = Annulus(10)

    assert annulus.inward_ring_span(10) == 1
    assert annulus.inward_ring_span(9) == 2
    assert annulus.inward_ring_span(8) == 3
    assert annulus.inward_ring_span(7) == 4
    assert annulus.inward_ring_span(6) == 5
    assert annulus.inward_ring_span(5) == 5
    assert annulus.inward_ring_span(4) == 4
    assert annulus.inward_ring_span(3) == 3
    assert annulus.inward_ring_span(2) == 2
    assert annulus.inward_ring_span(1) == 1
    assert annulus.inward_ring_span(0) == 0

    assert annulus.outward_ring_span(10) == 0
    assert annulus.outward_ring_span(9) == 1
    assert annulus.outward_ring_span(8) == 1
    assert annulus.outward_ring_span(7) == 2
    assert annulus.outward_ring_span(6) == 2
    assert annulus.outward_ring_span(5) == 3
    assert annulus.outward_ring_span(4) == 3
    assert annulus.outward_ring_span(3) == 4
    assert annulus.outward_ring_span(2) == 4
    assert annulus.outward_ring_span(1) == 5
    assert annulus.outward_ring_span(0) == 5


def test_ring_span_odd():
    annulus = Annulus(9)

    assert annulus.inward_ring_span(9) == 1
    assert annulus.inward_ring_span(8) == 2
    assert annulus.inward_ring_span(7) == 3
    assert annulus.inward_ring_span(6) == 4
    assert annulus.inward_ring_span(5) == 5
    assert annulus.inward_ring_span(4) == 4
    assert annulus.inward_ring_span(3) == 3
    assert annulus.inward_ring_span(2) == 2
    assert annulus.inward_ring_span(1) == 1
    assert annulus.inward_ring_span(0) == 0

    assert annulus.outward_ring_span(9) == 0
    assert annulus.outward_ring_span(8) == 1
    assert annulus.outward_ring_span(7) == 1
    assert annulus.outward_ring_span(6) == 2
    assert annulus.outward_ring_span(5) == 2
    assert annulus.outward_ring_span(4) == 3
    assert annulus.outward_ring_span(3) == 3
    assert annulus.outward_ring_span(2) == 4
    assert annulus.outward_ring_span(1) == 4
    assert annulus.outward_ring_span(0) == 5


def test_num_inward_connections_even():
    annulus = Annulus(10)

    # Regular rings.
    assert annulus.num_inward_connections(11) == 0
    assert annulus.num_inward_connections(10) == 1
    assert annulus.num_inward_connections(9) == 3
    assert annulus.num_inward_connections(8) == 7
    assert annulus.num_inward_connections(7) == 15
    assert annulus.num_inward_connections(6) == 31

    # Rings with connections capped by available slots.
    assert annulus.num_inward_connections(5) == 31
    assert annulus.num_inward_connections(4) == 15
    assert annulus.num_inward_connections(3) == 7
    assert annulus.num_inward_connections(2) == 3
    assert annulus.num_inward_connections(1) == 1
    assert annulus.num_inward_connections(0) == 0

    annulus = Annulus(4)

    # Regular rings.
    assert annulus.num_inward_connections(5) == 0
    assert annulus.num_inward_connections(4) == 1
    assert annulus.num_inward_connections(3) == 3

    # Rings with connections capped by available slots.
    assert annulus.num_inward_connections(2) == 3
    assert annulus.num_inward_connections(1) == 1
    assert annulus.num_inward_connections(0) == 0


def test_num_inward_connections_odd():
    annulus = Annulus(9)

    # Regular rings.
    assert annulus.num_inward_connections(10) == 0
    assert annulus.num_inward_connections(9) == 1
    assert annulus.num_inward_connections(8) == 3
    assert annulus.num_inward_connections(7) == 7
    assert annulus.num_inward_connections(6) == 15
    assert annulus.num_inward_connections(5) == 31

    # Rings with connections capped by available slots.
    assert annulus.num_inward_connections(4) == 15
    assert annulus.num_inward_connections(3) == 7
    assert annulus.num_inward_connections(2) == 3
    assert annulus.num_inward_connections(1) == 1
    assert annulus.num_inward_connections(0) == 0

    annulus = Annulus(5)

    # Regular rings.
    assert annulus.num_inward_connections(6) == 0
    assert annulus.num_inward_connections(5) == 1
    assert annulus.num_inward_connections(4) == 3

    # Rings with connections capped by available slots.
    assert annulus.num_inward_connections(3) == 7
    assert annulus.num_inward_connections(2) == 3
    assert annulus.num_inward_connections(1) == 1
    assert annulus.num_inward_connections(0) == 0


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

    # Rings with connections capped by available slots.
    assert annulus.num_outward_connections(4) == 80
    assert annulus.num_outward_connections(3) == 96
    assert annulus.num_outward_connections(2) == 88
    assert annulus.num_outward_connections(1) == 92
    assert annulus.num_outward_connections(0) == 62


def test_num_outward_connections_odd():
    annulus = Annulus(9)

    # Regular rings.
    assert annulus.num_outward_connections(10) == 0
    assert annulus.num_outward_connections(9) == 0
    assert annulus.num_outward_connections(8) == 2
    assert annulus.num_outward_connections(7) == 4
    assert annulus.num_outward_connections(6) == 12
    assert annulus.num_outward_connections(5) == 24

    # Rings with connections capped by available slots.
    assert annulus.num_outward_connections(4) == 56
    assert annulus.num_outward_connections(3) == 64
    assert annulus.num_outward_connections(2) == 72
    assert annulus.num_outward_connections(1) == 60
    assert annulus.num_outward_connections(0) == 62


def test_closest_on():
    annulus = Annulus(10)

    assert annulus.closest_on((8, 159), 4) == 9
    assert annulus.closest_on((8, 160), 4) == 10
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


def test_full_properties():
    for num_rings in [3, 4, 7, 8, 9, 10]:
        annulus = Annulus(num_rings)

        def assert_outward_slot_span_coords(coord: DiskCoord):
            r, i = coord

            if r > annulus.full_span_ring:
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
            else:
                num_partners = len(
                    {it for (rt, it) in annulus.partner_coords(coord) if rt == r + 1}
                )
                assert num_partners == 2 ** (r + 1)

        for r in range(num_rings + 1):
            for i in range(2 ** r):
                partners = list(annulus.partner_coords((r, i)))
                num_partners = len(partners)
                inward_ring_span = max(r - min(r_p for r_p, i_p in partners), 0)
                outward_ring_span = max(max(r_p for r_p, i_p in partners) - r, 0)

                assert num_partners == annulus.num_connections(r)
                assert inward_ring_span == annulus.inward_ring_span(r)
                assert outward_ring_span == annulus.outward_ring_span(r)
                assert_outward_slot_span_coords((r, i))
