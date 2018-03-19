from typing import Tuple

from raidensim.network.annulus import Annulus
from raidensim.network.node import Node
from raidensim.strategy.fee_strategy import FeeStrategy
from raidensim.strategy.position_strategy import PositionStrategy


class PriorityStrategy(object):
    def priority(
            self,
            u: Node,
            v: Node,
            e: dict,
            target: Node,
            value: int
    ):
        raise NotImplementedError


class DistancePriorityStrategy(PriorityStrategy):
    """
    Prioritizes hops according to their distance to the target node.
    """
    def __init__(self, position_strategy: PositionStrategy):
        self.position_strategy = position_strategy

    def priority(
            self,
            u: Node,
            v: Node,
            e: dict,
            target: Node,
            value: int
    ):
        return self.position_strategy.distance(v, target)


class NaiveFeePriorityStrategy(PriorityStrategy):
    """
    Prioritizes hops according to their distance to the target node and their channel net balance.
    A high net balance causes higher fees due to the added imbalance.
    Hops that increase distance are only prioritized if no other are available, i.e., low fees
    cannot incentivize hopping backward.
    """
    def __init__(
            self,
            position_strategy: PositionStrategy,
            fee_strategy: FeeStrategy
    ):
        self.position_strategy = position_strategy
        self.fee_strategy = fee_strategy

    def priority(
            self,
            u: Node,
            v: Node,
            e: dict,
            target: Node,
            value: int
    ):
        current_distance = self.position_strategy.distance(u, target)
        new_distance = self.position_strategy.distance(v, target)

        if new_distance > current_distance:
            distance_penalty = 1
        else:
            distance_penalty = 0

        fee = self.fee_strategy.get_fee(u, v, e, value)
        return distance_penalty, new_distance * fee


class DistanceFeePriorityStrategy(PriorityStrategy):
    """
    Calculates the expected remaining fee for a transfer using the respective hop based on distance
    and an assumed average fee per hop of 0.5.
    """
    def __init__(
            self,
            position_strategy: PositionStrategy,
            fee_strategy: FeeStrategy,
            weights: Tuple[float, float]
    ):
        self.position_strategy = position_strategy
        self.fee_strategy = fee_strategy
        self.weights = weights

    def priority(
            self,
            u: Node,
            v: Node,
            e: dict,
            target: Node,
            value: int
    ):
        current_distance = self.position_strategy.distance(u, target)
        new_distance = self.position_strategy.distance(v, target)

        if new_distance > current_distance:
            distance_penalty = 1
        else:
            distance_penalty = 0

        fee = self.fee_strategy.get_fee(u, v, e, value)
        return distance_penalty, new_distance * self.weights[0] + fee * self.weights[1]


class AnnulusPriorityStrategy(PriorityStrategy):
    def __init__(self, annulus: Annulus):
        self.annulus = annulus

    def priority(
            self,
            u: Node,
            v: Node,
            e: dict,
            target: Node,
            value: int
    ):
        # TODO: it might be possible to define a distance metric so that this custom priority
        # strategy can be replaced by a naive distance priority strategy.
        if v == target:
            return -1, 0, 0

        r_v, i_v = self.annulus.node_to_coord[v]
        r_t, i_t = self.annulus.node_to_coord[target]

        # Reference ring: R + 1
        num_slots = 2 ** (self.annulus.max_ring + 1)
        c_v = self.annulus.closest_on((r_v, i_v), self.annulus.max_ring + 1)
        c_t = self.annulus.closest_on((r_t, i_t), self.annulus.max_ring + 1)
        di = self.annulus.ring_distance_signed(c_v, c_t, num_slots)

        half_span = self.annulus.slot_span_on(r_v, self.annulus.max_ring + 1) // 2

        di = abs(di)
        dr = r_t - r_v
        if dr > 0:
            # Tie-breaker for the edge case where an outward hop would likely not get us closer to
            # the target quicker. In this case, prefer inward hops and do some zigzag.
            dr += 1

        dr = abs(dr)

        if di <= half_span:
            return 0, dr, di
        else:
            return 1, di - half_span, dr
