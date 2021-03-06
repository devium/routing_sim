import pytest

from raidensim.network.network import Network
from raidensim.network.config import NetworkConfiguration
from raidensim.network.dist import Distribution
from raidensim.strategy.creation.join_strategy import SimpleJoinStrategy
from raidensim.strategy.position_strategy import RingPositionStrategy


class DistinctDistribution(Distribution):
    def __init__(self):
        self.value = 1

    def reset(self):
        self.value = 1

    def random(self):
        self.value = (self.value + 1) % 2
        return self.value


@pytest.fixture
def network_2_nodes() -> Network:
    max_id = 2**32

    config = NetworkConfiguration(
        num_nodes=2,
        max_id=max_id,
        fullness_dist=DistinctDistribution(),
        position_strategy=RingPositionStrategy(max_id),
        join_strategy=SimpleJoinStrategy(
            max_initiated_channels=(0, 1),
            deposit=(15, 20)
        )
    )
    return Network(config)

