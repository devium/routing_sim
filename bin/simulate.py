import datetime
import os

import random

import math

from raidensim.network.network import Network

from raidensim.network.config import NetworkConfiguration
from raidensim.network.dist import BetaDistribution
from raidensim.network.lattice import WovenLattice
from raidensim.strategy.fee_strategy import SigmoidNetBalanceFeeStrategy, CapacityFeeStrategy
from raidensim.strategy.position_strategy import LatticePositionStrategy
from raidensim.strategy.routing.next_hop.greedy_routing_strategy import GreedyRoutingStrategy
from raidensim.strategy.routing.next_hop.priority_strategy import (
    DistancePriorityStrategy,
    NaiveFeePriorityStrategy,
    DistanceFeePriorityStrategy)
from raidensim.simulation import simulate_routing, simulate_scaling

from raidensim.strategy.creation.join_strategy import RaidenLatticeJoinStrategy

SCRIPT_DIR = os.path.dirname(__file__)
OUT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '../out'))


NUM_NODES = 10000

MAX_ID = 2**32
WEAVE_BASE_FACTOR = 2
MAX_CHANNEL_DISTANCE_ORDER = int(math.log(math.sqrt(NUM_NODES), 2 * WEAVE_BASE_FACTOR)) - 1
LATTICE = WovenLattice(2, WEAVE_BASE_FACTOR, 1, max(1, MAX_CHANNEL_DISTANCE_ORDER))
POSITION_STRATEGY = LatticePositionStrategy(LATTICE)

NETWORK_CONFIG_RAIDEN_NETWORK = NetworkConfiguration(
    num_nodes=NUM_NODES,
    max_id=MAX_ID,
    fullness_dist=BetaDistribution(0.5, 2),
    position_strategy=POSITION_STRATEGY,
    join_strategy=RaidenLatticeJoinStrategy(POSITION_STRATEGY, deposit=(10, 20))
)


def run():
    # Network configuration.
    config = NETWORK_CONFIG_RAIDEN_NETWORK

    fee_strategy = SigmoidNetBalanceFeeStrategy()
    # fee_strategy = CapacityFeeStrategy()

    # Routing models.
    distance_greedy_routing = GreedyRoutingStrategy(
        DistancePriorityStrategy(config.position_strategy)
    )
    fee_greedy_routing = GreedyRoutingStrategy(
        DistanceFeePriorityStrategy(config.position_strategy, fee_strategy, (1.0, 0.1))
    )

    now = datetime.datetime.now()
    now = now.replace(microsecond=0)
    dirpath = os.path.join(OUT_DIR, now.isoformat())

    random.seed(0)
    net = Network(config)

    # Routing simulation + animation.
    routing_strategies = [
        ('greedy_distance', distance_greedy_routing),
        ('greedy_fee_distance', fee_greedy_routing)
    ]

    # Network scaling simulation.
    if True:
        for name, routing_strategy in routing_strategies:
            simulate_scaling(
                net,
                dirpath,
                num_transfers=1000,
                transfer_value=1,
                position_strategy=config.position_strategy,
                routing_strategy=routing_strategy,
                fee_strategy=fee_strategy,
                name=name,
                max_recorded_failures=1,
                execute_transfers=True
            )

    if False:
        simulate_routing(
            net,
            dirpath,
            num_sample_nodes=5,
            num_paths=5,
            transfer_value=1,
            routing_strategies=routing_strategies,
            max_gif_frames=30
        )


if __name__ == '__main__':
    run()
