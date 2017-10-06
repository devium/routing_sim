from raidensim.strategy.network_strategy import PositionStrategy, NetworkStrategy
from .dist import Distribution


class NetworkConfiguration(object):
    def __init__(
            self,
            num_nodes: int,
            max_id: int,
            fullness_dist: Distribution,
            network_strategy: NetworkStrategy
    ):
        self.num_nodes = num_nodes
        self.max_id = max_id
        self.fullness_dist = fullness_dist
        self.network_strategy = network_strategy
