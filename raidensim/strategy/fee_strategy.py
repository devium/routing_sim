import math

from raidensim.network.node import Node


class FeeStrategy(object):
    def get_fee(self, u: Node, v: Node, e: dict, value: int) -> float:
        raise NotImplementedError


class SigmoidNetBalanceFeeStrategy(FeeStrategy):
    @staticmethod
    def sigmoid(value: float):
        """
        Monotonically maps values in [-inf, +inf] to [0, 1].
        0 -> 0.5
        -10 -> ~0
        +10 -> ~1
        """
        return 1 / (1 + math.exp(-value))

    def get_fee(self, u: Node, v: Node, e: dict, value: int) -> float:
        return self.sigmoid(e['net_balance'] + value)


class CapacityFeeStrategy(FeeStrategy):
    def get_fee(self, u: Node, v: Node, e: dict, value: int) -> float:
        return value - e['capacity']
