import pytest

from raidensim.network.network import Network
from raidensim.network.config import NetworkConfiguration
from raidensim.network.dist import Distribution
from raidensim.strategy.creation.join_strategy import SimpleJoinStrategy


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
        join_strategy=SimpleJoinStrategy(
            max_id=max_id,
            max_initiated_channels=(0, 1),
            deposit=(15, 20)
        )
    )
    return Network(config)

