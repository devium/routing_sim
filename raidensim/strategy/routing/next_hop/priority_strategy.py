from typing import Tuple

from raidensim.network.annulus import Annulus
from raidensim.network.hyperbolic_disk import HyperbolicDisk
from raidensim.network.node import Node
from raidensim.network.raw_network import RawNetwork
from raidensim.strategy.fee_strategy import FeeStrategy
from raidensim.strategy.position_strategy import PositionStrategy


class PriorityStrategy(object):
    def priority(
            self,
            raw: RawNetwork,
            source: Node,
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
            raw: RawNetwork,
            source: Node,
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
            raw: RawNetwork,
            source: Node,
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
            raw: RawNetwork,
            source: Node,
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
            raw: RawNetwork,
            source: Node,
            u: Node,
            v: Node,
            e: dict,
            target: Node,
            value: int
    ):
        if v == target:
            return 0, 0, 0

        r_v, i_v = self.annulus.node_to_coord[v]
        r_t, i_t = self.annulus.node_to_coord[target]

        if r_v < r_t:
            half_span = self.annulus.slot_span_on(r_v, r_t) // 2
        else:
            half_span = 0

        closest = self.annulus.closest_on((r_v, i_v), r_t)
        num_slots = 2 ** r_t
        di = self.annulus.ring_distance_signed(closest, i_t, num_slots)
        if di > 0:
            # Closest rounds down to the nearest integer so it favors it <= closest.
            # E.g. 30 and 31 are both equally far from 15 on the next lower ring but closest will
            # be 30.
            di -= 1

        di = abs(di) - half_span
        dr = abs(r_t - r_v)

        # di is negative if the target node lies in the outward span.
        if di < 0:
            return 0, dr, di
        else:
            return 1, di, dr
