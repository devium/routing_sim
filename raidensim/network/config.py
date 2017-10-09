from raidensim.strategy.creation.join_strategy import JoinStrategy
from raidensim.strategy.position_strategy import PositionStrategy
from .dist import Distribution


class NetworkConfiguration(object):
    def __init__(
            self,
            num_nodes: int,
            max_id: int,
            fullness_dist: Distribution,
            position_strategy: PositionStrategy,
            join_strategy: JoinStrategy
    ):
        self.num_nodes = num_nodes
        self.max_id = max_id
        self.fullness_dist = fullness_dist
        self.position_strategy = position_strategy
        self.join_strategy = join_strategy
