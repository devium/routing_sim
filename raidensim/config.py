from raidensim.dist import ParetoDistribution, CircleDistribution


class BaseNetworkConfiguration(object):
    num_nodes = 1000
    min_fullness = 0
    max_fullness = 10000
    fullness_dist = None

    def get_num_channels(self, fullness):
        """
        Linear min/max mapping of fullness to channel count.
        """
        min_channels = 2
        max_channels = 5
        return int((max_channels - min_channels) * fullness / self.max_fullness + min_channels)

    def get_channel_deposit(self, fullness):
        """
        Linear min/max mapping of fullness to deposit per channel.
        """
        min_deposit = 10
        max_deposit = 80
        return int((max_deposit - min_deposit) * fullness / self.max_fullness + min_deposit)

    # pathfinding helpers
    ph_num_helpers = 20
    ph_max_range_fr = 1/8.
    ph_min_range_fr = 1/16.


class ParetoNetworkConfiguration(BaseNetworkConfiguration):
    def __init__(self, num_nodes, a, min_fullness=0, max_fullness=1000):
        self.num_nodes = num_nodes
        self.min_fullness = min_fullness
        self.max_fullness = max_fullness
        self.fullness_dist = ParetoDistribution(
            a,
            min_value=self.min_fullness,
            max_value=self.max_fullness
        )


class SemisphereNetworkConfiguration(BaseNetworkConfiguration):
    def __init__(self, num_nodes, min_fullness=0, max_fullness=1000):
        self.num_nodes = num_nodes
        self.min_fullness = min_fullness
        self.max_fullness = max_fullness
        self.fullness_dist = CircleDistribution(
            min_value=self.min_fullness,
            max_value=self.max_fullness
        )

