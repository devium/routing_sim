import numpy as np

from scipy.stats import semicircular


class ParetoDistribution(object):
    def __init__(self, a, min_value, max_value):
        """
        Pareto distribution according to
        https://docs.scipy.org/doc/numpy/reference/generated/numpy.random.pareto.html
        Values are in the range [min_value, inf) and `a` determines the shape.

        A higher `a` causes a sharper drop-off in distribution (~= poorer network).

        This implementation is artificially bounded by max_value.
        """
        self.a = a
        self.min_value = min_value
        self.max_value = max_value
        np.random.seed(0)

    def random(self):
        return min(np.random.pareto(self.a) + self.min_value, self.max_value)


class CircleDistribution(object):
    def __init__(self, min_value, max_value):
        """
        Quarter-circle distribution. Can also be used as the height of a point on the surface of a
        semisphere for an even surface distribution.
        """
        self.min_value = min_value
        self.max_value = max_value
        np.random.seed(0)

    def random(self):
        return (self.max_value - self.min_value) * abs(semicircular.rvs()) + self.min_value
