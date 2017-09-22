import os

from raidensim.animation.animation_generator import AnimationGenerator
from raidensim.animation.config import AnimationConfiguration
from raidensim.network.config import NetworkConfiguration
from raidensim.network.dist import (
    CircleDistribution,
    ParetoDistribution,
    BetaDistribution,
    MicroRaidenDistribution)
from raidensim.strategy.network_strategies import RaidenNetworkStrategy, MicroRaidenNetworkStrategy

NETWORK_CONFIG_RAIDEN_NETWORK = NetworkConfiguration(
    num_nodes=200,
    fullness_dist=CircleDistribution(),
    # fullness_dist=ParetoDistribution(5, 0, 1),
    # fullness_dist=BetaDistribution(0.5, 2),
    network_strategy=RaidenNetworkStrategy(
        min_incoming_deposit=0.2,
        max_network_distance=1/3,
        max_initiated_channels=(2, 10),
        deposit=(4, 100)
    )
)


NETWORK_CONFIG_MICRORAIDEN = NetworkConfiguration(
    num_nodes=200,
    fullness_dist=MicroRaidenDistribution(0.95, CircleDistribution()),
    network_strategy=MicroRaidenNetworkStrategy(
        max_initiated_channels=(1, 3),
        deposit=10
    )
)

SCRIPT_DIR = os.path.dirname(__file__)
OUT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '../blender/data'))

ANIMATION_CONFIG = AnimationConfiguration(
    out_dir=OUT_DIR,
    network=NETWORK_CONFIG_RAIDEN_NETWORK,
    popup_channels=False,
    animation_length=5,
    transfer_hop_delay=0.08,
    transfer_freq_max=200,
    top_hole_radius=0.2,
    popup_freq_max=200,
    simulation_step_size=0.01,
    transfer_attempts_max=10,
    transfer_value=1
)


def run():
    AnimationGenerator(ANIMATION_CONFIG)


if __name__ == '__main__':
    run()
