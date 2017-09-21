import os

from raidensim.animation.animation_generator import AnimationGenerator
from raidensim.animation.config import AnimationConfiguration
from raidensim.network import NetworkConfiguration, MicroRaidenNetworkConfiguration
from raidensim.network.dist import (
    CircleDistribution,
    ParetoDistribution,
    BetaDistribution
)

NETWORK_CONFIG_RAIDEN_NETWORK = {
    'num_nodes': 200,
    'fullness_dist': CircleDistribution(),
    # 'fullness_dist': ParetoDistribution(5, 0, 1),
    # 'fullness_dist': BetaDistribution(1.1, 5),
    'min_max_initiated_channels': 2,
    'max_max_initiated_channels': 10,
    'min_max_accepted_channels': 100,
    'max_max_accepted_channels': 100,
    'min_max_channels': 102,
    'max_max_channels': 110,
    'min_deposit': 4,
    'max_deposit': 100,
    'min_partner_deposit': 0.2
}

NETWORK_CONFIG_MICRORAIDEN = {
    'num_nodes': 200,
    'server_fullness_dist': CircleDistribution(),
    'client_fraction': 0.95,
    'min_max_initiated_channels': 1,
    'max_max_initiated_channels': 3,
    'min_max_accepted_channels': 100,
    'max_max_accepted_channels': 100,
    'min_deposit': 1,
    'max_deposit': 1
}

ANIMATION_CONFIG = {
    'popup_channels': False,
    'animation_length': 5,
    'transfer_hop_delay': 0.08,
    'transfer_freq_max': 200,
    'top_hole_radius': 0.2,
    'popup_freq_max': 200,
    'simulation_step_size': 0.01,
    'transfer_attempts_max': 10,
    'transfer_value': 1
}

SCRIPT_DIR = os.path.dirname(__file__)
OUT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '../blender/data'))


def run():
    network_config = NetworkConfiguration(**NETWORK_CONFIG_RAIDEN_NETWORK)
    # network_config = MicroRaidenNetworkConfiguration(**NETWORK_CONFIG_MICRORAIDEN)
    animation_config = AnimationConfiguration(
        out_dir=OUT_DIR,
        network=network_config,
        **ANIMATION_CONFIG
    )
    AnimationGenerator(animation_config)


if __name__ == '__main__':
    run()
