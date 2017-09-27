import math


def sigmoid(value: float):
    """
    Monotonically maps values in [-inf, +inf] to [0, 1].
    0 -> 0.5
    -10 -> ~0
    +10 -> ~1
    """
    return 1 / (1 + math.exp(-value))