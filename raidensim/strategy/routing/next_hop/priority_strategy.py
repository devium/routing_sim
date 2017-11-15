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
        r_v, i_v = self.annulus.node_to_coord[v]
        r_t, i_t = self.annulus.node_to_coord[target]

        # TODO: REMOVE
        if tuple(self.annulus.node_to_coord[v]) == (7, 69):
            print('whoop')

        num_slots = 2 ** r_t

        if r_v < r_t:
            span_begin, span_end = self.annulus.slot_span_range_on((r_v, i_v), r_t)
            half_span = (span_end - span_begin) % num_slots // 2
            if span_begin < span_end:
                in_span = span_begin <= i_t < span_end
            else:
                in_span = span_begin <= i_t or i_t < span_end
        else:
            in_span = False

        di = i_t - self.annulus.closest_on((r_v, i_v), r_t)
        di = min(di % num_slots, -di % num_slots) * 2 ** (self.annulus.max_ring - r_t)

        dr = abs(r_v - r_t)

        if in_span:
            return 0, dr, di
        else:
            return 1, di - half_span, dr
