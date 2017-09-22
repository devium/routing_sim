import random

import numpy as np

from scipy.stats import semicircular, beta


class Distribution(object):
    def reset(self):
        raise NotImplementedError

    def random(self):
        raise NotImplementedError

    def get_pdf(self):
        raise NotImplementedError


class ConstantDistribution(Distribution):
    def __init__(self, value):
        self.value = value

    def reset(self):
        pass

    def random(self):
        # Huehuehueh
        return self.value

    def get_pdf(self):
        return lambda x: 1 if x == self.value else 0


class UniformDistribution(Distribution):
    def __init__(self, min_value=0, max_value=1):
        self.min_value = min_value
        self.max_value = max_value
        self.reset()

    def reset(self):
        random.seed(0)

    def random(self):
        return random.uniform(self.min_value, self.max_value)

    def _pdf(self, x):
        if self.min_value <= x <= self.max_value:
            return 1 / (self.max_value - self.min_value)
        else:
            return 0

    def get_pdf(self):
        return self._pdf


class ParetoDistribution(Distribution):
    def __init__(self, a, min_value, max_value):
        """
        Pareto distribution according to
        https://docs.scipy.org/doc/numpy/reference/generated/numpy.random.pareto.html
        Values are in the range [min_value, inf) and `a` determines the shape.

        A higher `a` causes a sharper drop-off in distribution (~= poorer network).

        This implementation is artificially bounded by max_value, potentially leading to peaks
        at max_value.
        """
        self.a = a
        self.min_value = min_value
        self.max_value = max_value
        self.reset()

    def reset(self):
        np.random.seed(0)

    def random(self):
        return min(np.random.pareto(self.a) + self.min_value, self.max_value)


class CircleDistribution(Distribution):
    def __init__(self, min_value=0, max_value=1):
        """
        Quarter-circle distribution. Can also be used as the height of a point on the surface of a
        semisphere for an even surface distribution.
        """
        self.min_value = min_value
        self.max_value = max_value
        self.reset()

    def reset(self):
        np.random.seed(0)

    def random(self):
        return (self.max_value - self.min_value) * abs(semicircular.rvs()) + self.min_value

    def get_pdf(self):
        return lambda x: 2 * semicircular.pdf(x)


class BetaDistribution(Distribution):
    def __init__(self, a, b, min_value=0, max_value=1):
        """
        Beta distribution. You can do pretty much anything with this. Produces values in [0,1].
        """
        self.a = a
        self.b = b
        self.min_value = min_value
        self.max_value = max_value
        self.reset()

    def reset(self):
        np.random.seed(0)

    def random(self):
        return (self.max_value - self.min_value) * beta.rvs(self.a, self.b) + self.min_value

    def get_pdf(self):
        return lambda x: beta.pdf(x, self.a, self.b)


class MicroRaidenDistribution(Distribution):
    def __init__(self, client_fraction, server_fullness_dist):
        self.client_fraction = client_fraction
        self.server_fullness_dist = server_fullness_dist

    def reset(self):
        random.seed(0)
        self.server_fullness_dist.reset()

    def random(self):
        if random.uniform(0, 1) < self.client_fraction:
            return 0
        else:
            return self.server_fullness_dist.random() / 2 + 0.5

    def get_pdf(self):
        return self.server_fullness_dist.get_pdf()
