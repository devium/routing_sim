import numpy as np

from scipy.stats import semicircular, beta


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
        self.reset()

    def reset(self):
        np.random.seed(0)

    def random(self):
        return min(np.random.pareto(self.a) + self.min_value, self.max_value)


class CircleDistribution(object):
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


class BetaDistribution(object):
    def __init__(self, a, b, min_value=0, max_value=1):
        """
        Beta distribution. You can do pretty much anything with this. Produces values in [0,1]
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
