from raidensim.strategy.strategy import NetworkStrategy
from .dist import Distribution


class NetworkConfiguration(object):
    def __init__(
            self,
            num_nodes: int,
            fullness_dist: Distribution,
            network_strategy: NetworkStrategy
    ):
        self.num_nodes = num_nodes
        self.fullness_dist = fullness_dist
        self.network_strategy = network_strategy

    # Path-finding helpers
    ph_num_helpers = 20
    ph_max_range_fr = 1 / 8.
    ph_min_range_fr = 1 / 16.
