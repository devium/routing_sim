import os

import math
import random

from raidensim.network.network import Network

from raidensim.network.config import NetworkConfiguration
from raidensim.network.dist import (
    ParetoDistribution,
    BetaDistribution,
    MicroRaidenDistribution,
    CircleDistribution
)
from raidensim.network.lattice import Lattice
from raidensim.strategy.position_strategy import LatticePositionStrategy, RingPositionStrategy
from raidensim.strategy.routing.global_routing_strategy import (
    GlobalRoutingStrategy,
    imbalance_fee_model,
    net_balance_fee_model,
    constant_fee_model
)
from raidensim.strategy.routing.next_hop.greedy_routing_strategy import GreedyRoutingStrategy
from raidensim.strategy.routing.next_hop.priority_strategy import (
    DistancePriorityStrategy,
    DistanceNetBalancePriorityStrategy
)
from raidensim.strategy.routing.next_hop.globally_assisted_priority_strategy import \
    GloballyAssistedPriorityStrategy
from raidensim.simulation import simulate_routing, simulate_balancing

from raidensim.strategy.creation.join_strategy import (
    RaidenRingJoinStrategy,
    MicroRaidenJoinStrategy,
    RaidenLatticeJoinStrategy)

SCRIPT_DIR = os.path.dirname(__file__)
OUT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '../out'))


NUM_NODES = 400

MAX_ID = 2**32
# POSITION_STRATEGY = RingPositionStrategy(MAX_ID)

LATTICE = Lattice()
POSITION_STRATEGY = LatticePositionStrategy(LATTICE)

NETWORK_CONFIG_RAIDEN_NETWORK = NetworkConfiguration(
    num_nodes=NUM_NODES,
    max_id=MAX_ID,
    # fullness_dist=CircleDistribution(),
    # fullness_dist=ParetoDistribution(5, 0, 1),
    fullness_dist=BetaDistribution(0.5, 2),
    position_strategy=POSITION_STRATEGY,
    # join_strategy=RaidenRingJoinStrategy(
    #     max_id=MAX_ID,
    #     min_partner_deposit=0.2,
    #     position_strategy=POSITION_STRATEGY,
    #     max_distance=int(1/4 * MAX_ID),
    #     kademlia_skip=22,
    #     max_initiated_channels=(1, 10),
    #     max_accepted_channels=(6, 14),
    #     deposit=(4, 100)
    # )
    join_strategy=RaidenLatticeJoinStrategy(
        POSITION_STRATEGY,
        max_distance=int(math.sqrt(NUM_NODES)),
        num_shortcut_channels=(4, 4),
        deposit=(10, 20)
    )
)

NETWORK_CONFIG_MICRORAIDEN = NetworkConfiguration(
    num_nodes=200,
    max_id=MAX_ID,
    # fullness_dist=BetaDistribution(0.95, CircleDistribution()),
    # fullness_dist=ParetoDistribution(0.95, CircleDistribution()),
    fullness_dist=MicroRaidenDistribution(0.95, CircleDistribution()),
    position_strategy=POSITION_STRATEGY,
    join_strategy=MicroRaidenJoinStrategy(
        max_id=MAX_ID,
        max_initiated_channels=(1, 3),
        deposit=10
    )
)


def run():
    # Network configuration.
    config = NETWORK_CONFIG_RAIDEN_NETWORK
    # config = NETWORK_CONFIG_MICRORAIDEN

    # Routing models.
    constant_global_routing = GlobalRoutingStrategy(constant_fee_model)
    net_balance_global_routing = GlobalRoutingStrategy(net_balance_fee_model)
    imbalance_global_routing = GlobalRoutingStrategy(imbalance_fee_model)
    distance_greedy_routing = GreedyRoutingStrategy(DistancePriorityStrategy(POSITION_STRATEGY))
    distance_net_balance_greedy_routing = GreedyRoutingStrategy(
        DistanceNetBalancePriorityStrategy(POSITION_STRATEGY)
    )

    random.seed(0)
    net = Network(config)

    # Routing simulation + animation.
    routing_models = [
        # constant_global_routing,
        distance_greedy_routing,
        # distance_net_balance_greedy_routing
    ]
    simulate_routing(
        net, OUT_DIR,
        num_sample_nodes=10,
        num_paths=3,
        value=1,
        routing_models=routing_models,
        max_gif_frames=30
    )

    # Network scaling simulation.
    routing_models = [
        ('greedy_distance', distance_greedy_routing),
        # ('greedy_net_balance', distance_net_balance_greedy_routing)
    ]
    for name, routing_model in routing_models:
        simulate_balancing(
            net,
            OUT_DIR,
            num_transfers=1000,
            transfer_value=1,
            routing_model=routing_model,
            name=name,
            max_recorded_fails=1,
            execute_transfers=False
        )


if __name__ == '__main__':
    run()
