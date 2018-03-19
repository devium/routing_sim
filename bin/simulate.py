import datetime
import os

import random

import math

from raidensim.network.annulus import Annulus
from raidensim.network.network import Network

from raidensim.network.config import NetworkConfiguration
from raidensim.network.dist import BetaDistribution, MicroRaidenDistribution
from raidensim.network.lattice import WovenLattice
from raidensim.strategy.fee_strategy import SigmoidNetBalanceFeeStrategy
from raidensim.strategy.position_strategy import (
    LatticePositionStrategy,
    RingPositionStrategy,
    AnnulusPositionStrategy
)
from raidensim.strategy.routing.global_routing_strategy import GlobalRoutingStrategy
from raidensim.strategy.routing.next_hop.greedy_routing_strategy import GreedyRoutingStrategy
from raidensim.strategy.routing.next_hop.priority_strategy import (
    DistancePriorityStrategy,
    DistanceFeePriorityStrategy,
    AnnulusPriorityStrategy)
from raidensim.simulation import simulate_routing, simulate_scaling

from raidensim.strategy.creation.join_strategy import (
    RaidenLatticeJoinStrategy,
    RaidenKademliaJoinStrategy,
    MicroRaidenJoinStrategy,
    FullAnnulusJoinStrategy,
    SmartAnnulusJoinStrategy
)

# =================================================================================================
# Target directory for network renderings and statistics.
SCRIPT_DIR = os.path.dirname(__file__)
OUT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '../out'))
# =================================================================================================

# =================================================================================================
# Useful annulus variables.
ANNULUS_MAX_RING = 9
ANNULUS_MAX_NODES = 2 ** (ANNULUS_MAX_RING + 1) - 2 ** (ANNULUS_MAX_RING // 2)
ANNULUS = Annulus(ANNULUS_MAX_RING)
# =================================================================================================

# =================================================================================================
# Node quantity and failure rate. "Failing" nodes are frozen for the duration of the simulation.
NUM_NODES = int(ANNULUS_MAX_NODES * 0.4)
NODE_FAILURE_RATE = 0.1
MAX_ID = 2**32
# =================================================================================================

# =================================================================================================
# Useful WovenLattice variables.
WEAVE_BASE_FACTOR = 2
MAX_CHANNEL_DISTANCE_ORDER = int(math.log(NUM_NODES, 2 * WEAVE_BASE_FACTOR))
LATTICE = WovenLattice(
    num_dims=2,
    weave_base_factor=WEAVE_BASE_FACTOR,
    min_order=1,
    max_order=max(1, MAX_CHANNEL_DISTANCE_ORDER)
)
# =================================================================================================

# =================================================================================================
# Annulus network configuration.
ANNULUS_NETWORK_CONFIG = NetworkConfiguration(
    num_nodes=NUM_NODES,
    max_id=MAX_ID,
    fullness_dist=BetaDistribution(0.3, 2),
    position_strategy=AnnulusPositionStrategy(ANNULUS),
    join_strategy=SmartAnnulusJoinStrategy(ANNULUS),
    # join_strategy=FullAnnulusJoinStrategy(ANNULUS),
)
# =================================================================================================

# =================================================================================================
# WovenLattice network configuration.
LATTICE_NETWORK_CONFIG = NetworkConfiguration(
    num_nodes=NUM_NODES,
    max_id=MAX_ID,
    fullness_dist=BetaDistribution(0.5, 2),
    position_strategy=LatticePositionStrategy(LATTICE),
    join_strategy=RaidenLatticeJoinStrategy(
        lattice=LATTICE,
        max_initiated_aux_channels=(8, 12),
        max_accepted_aux_channels=(8, 12),
        deposit=(10, 20)
    )
)
# =================================================================================================

# =================================================================================================
# Kademlia network configuration.
KADEMLIA_NETWORK_CONFIG = NetworkConfiguration(
    num_nodes=NUM_NODES,
    max_id=MAX_ID,
    fullness_dist=BetaDistribution(0.5, 2),
    position_strategy=RingPositionStrategy(MAX_ID),
    join_strategy=RaidenKademliaJoinStrategy(
        max_id=MAX_ID,
        min_partner_deposit=0.2,
        kademlia_bucket_limits=(25, 30),
        max_initiated_channels=(1, 12),
        max_accepted_channels=(5, 20),
        deposit=(5, 40)
    )
)
# =================================================================================================

# =================================================================================================
# uRaiden network configuration (many to one).
MICRORAIDEN_NETWORK_CONFIG = NetworkConfiguration(
    num_nodes=NUM_NODES,
    max_id=MAX_ID,
    fullness_dist=MicroRaidenDistribution(0.9, BetaDistribution(0.5, 2)),
    position_strategy=RingPositionStrategy(MAX_ID),
    join_strategy=MicroRaidenJoinStrategy(
        max_initiated_channels=(1,4),
        deposit=10
    )
)
# =================================================================================================


def run():
    # =============================================================================================
    # Target subdirectory timestamping.
    now = datetime.datetime.now()
    now = now.replace(microsecond=0)
    dirpath = os.path.join(OUT_DIR, now.isoformat())
    # =============================================================================================

    # =============================================================================================
    # Active network configuration.
    config = ANNULUS_NETWORK_CONFIG
    # =============================================================================================

    # =============================================================================================
    # Fee model definition.
    fee_strategy = SigmoidNetBalanceFeeStrategy()

    # Routing model definitions.
    global_routing = GlobalRoutingStrategy(fee_strategy)
    distance_greedy_routing = GreedyRoutingStrategy(
        DistancePriorityStrategy(config.position_strategy)
    )
    fee_greedy_routing = GreedyRoutingStrategy(
        DistanceFeePriorityStrategy(config.position_strategy, fee_strategy, (1.0, 0.1))
    )
    annulus_greedy_routing = GreedyRoutingStrategy(AnnulusPriorityStrategy(ANNULUS))

    # Routing model names used in simulation results. Only models contained in this list will be
    # simulated.
    routing_strategies = [
        # ('global', global_routing),
        # ('greedy_distance', distance_greedy_routing),
        # ('greedy_fee_distance', fee_greedy_routing)
        ('greedy_annulus', annulus_greedy_routing)
    ]
    # =============================================================================================

    # =============================================================================================
    # Create network and freeze failing nodes.
    random.seed(0)
    net = Network(config)
    net.raw.freeze_random_nodes(int(NUM_NODES * NODE_FAILURE_RATE))
    # =============================================================================================

    # =============================================================================================
    # Network scaling simulation.
    if True:
        for name, routing_strategy in routing_strategies:
            simulate_scaling(
                net,
                dirpath,
                num_transfers=2000,
                transfer_value=1,
                position_strategy=config.position_strategy,
                routing_strategy=routing_strategy,
                fee_strategy=fee_strategy,
                name=name,
                max_recorded_failures=1,
                credit_transfers=True
            )
    # =============================================================================================

    # =============================================================================================
    # Detailed routing simulations.
    if True:
        simulate_routing(
            net,
            dirpath,
            num_sample_nodes=5,
            num_paths=3,
            transfer_value=1,
            routing_strategies=routing_strategies,
            max_gif_frames=30
        )
    # =============================================================================================


if __name__ == '__main__':
    run()
