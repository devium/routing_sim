import os

from raidensim.animation.animation_generator import AnimationGenerator
from raidensim.animation.config import AnimationConfiguration
from raidensim.network.config import NetworkConfiguration
from raidensim.network.dist import (
    BetaDistribution,
    MicroRaidenDistribution,
    CircleDistribution
)

from raidensim.strategy.creation.join_strategy import (
    MicroRaidenJoinStrategy,
    RaidenKademliaJoinStrategy
)
from raidensim.strategy.fee_strategy import ConstantFeeStrategy
from raidensim.strategy.position_strategy import RingPositionStrategy
from raidensim.strategy.routing.global_routing_strategy import GlobalRoutingStrategy
from raidensim.strategy.routing.next_hop.priorty_bfs_routing_strategy import PriorityBFSRoutingStrategy
from raidensim.strategy.routing.next_hop.priority_strategy import DistancePriorityStrategy

MAX_ID = 2**32
POSITION_STRATEGY = RingPositionStrategy(MAX_ID)

KADEMLIA_NETWORK_CONFIG = NetworkConfiguration(
    num_nodes=1000,
    max_id=MAX_ID,
    fullness_dist=CircleDistribution(),
    position_strategy=RingPositionStrategy(MAX_ID),
    join_strategy=RaidenKademliaJoinStrategy(
        max_id=MAX_ID,
        min_partner_deposit=0.2,
        kademlia_bucket_limits=(25, 30),
        max_initiated_channels=(1, 8),
        max_accepted_channels=(5, 20),
        deposit=(5, 40)
    )
)

MICRORAIDEN_NETWORK_CONFIG = NetworkConfiguration(
    num_nodes=300,
    max_id=MAX_ID,
    fullness_dist=MicroRaidenDistribution(0.9, BetaDistribution(0.5, 2)),
    position_strategy=RingPositionStrategy(MAX_ID),
    join_strategy=MicroRaidenJoinStrategy(
        max_initiated_channels=(1,4),
        deposit=10
    )
)


SCRIPT_DIR = os.path.dirname(__file__)
OUT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '../blender/data'))

ANIMATION_CONFIG = AnimationConfiguration(
    out_dir=OUT_DIR,
    network=KADEMLIA_NETWORK_CONFIG,
    routing_model=GlobalRoutingStrategy(ConstantFeeStrategy()),
    popup_channels=True,
    animation_length=5,
    transfer_hop_delay=0.2,
    transfer_freq_max=100,
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
