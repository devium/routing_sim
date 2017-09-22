import pytest

from raidensim.network.channel_network import ChannelNetwork
from raidensim.network.config import NetworkConfiguration
from raidensim.network.dist import Distribution
from raidensim.strategy.network_strategies import SimpleNetworkStrategy


class DistinctDistribution(Distribution):
    def __init__(self):
        self.value = 1

    def reset(self):
        self.value = 1

    def random(self):
        self.value = (self.value + 1) % 2
        return self.value


@pytest.fixture
def network_2_nodes():
    config = NetworkConfiguration(
        num_nodes=2,
        fullness_dist=DistinctDistribution(),
        network_strategy=SimpleNetworkStrategy(
            max_initiated_channels=(0, 1),
            deposit=(15, 20)
        )
    )
    return ChannelNetwork(config)

