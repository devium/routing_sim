from raidensim.dist import ParetoDistribution, CircleDistribution


class BaseNetworkConfiguration(object):
    num_nodes = 1000
    min_fullness = 0
    max_fullness = 10000
    min_channels = 3
    max_channels = 10
    min_deposit = 10
    max_deposit = 100
    fullness_dist = None

    def get_num_channels(self, fullness):
        """
        Linear min/max mapping of fullness to channel count.
        """
        return int((self.max_channels - self.min_channels) * fullness /
                   self.max_fullness + self.min_channels)

    def get_channel_deposit(self, fullness):
        """
        Linear min/max mapping of fullness to deposit per channel.
        """
        return int((self.max_deposit - self.min_deposit) * fullness /
                   self.max_fullness + self.min_deposit)

    # pathfinding helpers
    ph_num_helpers = 20
    ph_max_range_fr = 1 / 8.
    ph_min_range_fr = 1 / 16.


class ParetoNetworkConfiguration(BaseNetworkConfiguration):
    def __init__(
            self,
            num_nodes,
            a,
            min_fullness=0,
            max_fullness=1000,
            min_channels=2,
            max_channels=10,
            min_deposit=10,
            max_deposit=100
    ):
        self.num_nodes = num_nodes
        self.min_fullness = min_fullness
        self.max_fullness = max_fullness
        self.min_channels = min_channels
        self.max_channels = max_channels
        self.min_deposit = min_deposit
        self.max_deposit = max_deposit
        self.fullness_dist = ParetoDistribution(
            a,
            min_value=self.min_fullness,
            max_value=self.max_fullness
        )


class SemisphereNetworkConfiguration(BaseNetworkConfiguration):
    def __init__(
            self,
            num_nodes,
            min_fullness=0,
            max_fullness=1000,
            min_channels=2,
            max_channels=10,
            min_deposit=10,
            max_deposit=100
    ):
        self.num_nodes = num_nodes
        self.min_fullness = min_fullness
        self.max_fullness = max_fullness
        self.min_channels = min_channels
        self.max_channels = max_channels
        self.min_deposit = min_deposit
        self.max_deposit = max_deposit
        self.fullness_dist = CircleDistribution(
            min_value=self.min_fullness,
            max_value=self.max_fullness
        )
