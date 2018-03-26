import os

from raidensim.animation.animation_generator import AnimationGenerator
from raidensim.animation.config import AnimationConfiguration
from raidensim.network.annulus import Annulus
from raidensim.network.config import NetworkConfiguration
from raidensim.network.dist import (
    BetaDistribution,
    MicroRaidenDistribution,
    ConstantDistribution
)

from raidensim.strategy.creation.join_strategy import (
    MicroRaidenJoinStrategy,
    SmartAnnulusJoinStrategy
)
from raidensim.strategy.fee_strategy import ConstantFeeStrategy
from raidensim.strategy.position_strategy import RingPositionStrategy, AnnulusPositionStrategy
from raidensim.strategy.routing.global_routing_strategy import GlobalRoutingStrategy

MAX_ID = 2**32
POSITION_STRATEGY = RingPositionStrategy(MAX_ID)

ANNULUS_MAX_RING = 7
ANNULUS_MAX_NODES = 2 ** (ANNULUS_MAX_RING + 1) - 2 ** (ANNULUS_MAX_RING // 2)
ANNULUS = Annulus(ANNULUS_MAX_RING)
NUM_NODES = ANNULUS_MAX_NODES

ANNULUS_NETWORK_CONFIG = NetworkConfiguration(
    num_nodes=NUM_NODES,
    max_id=MAX_ID,
    fullness_dist=ConstantDistribution(1),
    position_strategy=AnnulusPositionStrategy(ANNULUS),
    join_strategy=SmartAnnulusJoinStrategy(ANNULUS)
)

MICRORAIDEN_NETWORK_CONFIG = NetworkConfiguration(
    num_nodes=300,
    max_id=MAX_ID,
    fullness_dist=MicroRaidenDistribution(0.9, BetaDistribution(0.5, 2)),
    position_strategy=RingPositionStrategy(MAX_ID),
    join_strategy=MicroRaidenJoinStrategy(
        max_initiated_channels=(1, 4),
        deposit=10
    )
)


SCRIPT_DIR = os.path.dirname(__file__)
OUT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '../blender/data'))

ANIMATION_CONFIG = AnimationConfiguration(
    out_dir=OUT_DIR,
    network=ANNULUS_NETWORK_CONFIG,
    routing_model=GlobalRoutingStrategy(ConstantFeeStrategy()),
    popup_channels=True,
    animation_length=10,
    transfer_hop_delay=0.2,
    transfer_freq_max=100,
    top_hole_radius=0.2,
    popup_freq_max=100,
    simulation_step_size=0.01,
    transfer_attempts_max=10,
    transfer_value=1
)


def run():
    AnimationGenerator(ANIMATION_CONFIG)


if __name__ == '__main__':
    run()
