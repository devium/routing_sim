import os

from raidensim.network.config import NetworkConfiguration
from raidensim.network.dist import (
    ParetoDistribution,
    BetaDistribution,
    MicroRaidenDistribution,
    CircleDistribution
)
from raidensim.strategy.routing.global_routing_strategy import (
    GlobalRoutingStrategy,
    imbalance_fee_model,
    net_balance_fee_model,
    constant_fee_model
)
from raidensim.strategy.routing.next_hop.next_hop_routing_strategy import NextHopRoutingStrategy
from raidensim.strategy.routing.next_hop.priority_strategy import (
    DistancePriorityStrategy,
    DistanceNetBalancePriorityStrategy
)
from raidensim.strategy.routing.next_hop.globally_assisted_priority_strategy import \
    GloballyAssistedPriorityStrategy
from raidensim.simulation import simulate_routing, simulate_balancing

from raidensim.strategy.creation.join_strategy import (
    RaidenRingJoinStrategy,
    MicroRaidenJoinStrategy
)

SCRIPT_DIR = os.path.dirname(__file__)
OUT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '../out'))


MAX_ID = 2**32


NETWORK_CONFIG_RAIDEN_NETWORK = NetworkConfiguration(
    num_nodes=200,
    max_id=MAX_ID,
    # fullness_dist=CircleDistribution(),
    # fullness_dist=ParetoDistribution(5, 0, 1),
    fullness_dist=BetaDistribution(0.5, 2),
    join_strategy=RaidenRingJoinStrategy(
        max_id=MAX_ID,
        min_partner_deposit=0.2,
        max_distance=int(1/4 * MAX_ID),
        kademlia_skip=22,
        max_initiated_channels=(1, 10),
        max_accepted_channels=(6, 14),
        deposit=(4, 100)
    )
)


NETWORK_CONFIG_MICRORAIDEN = NetworkConfiguration(
    num_nodes=200,
    max_id=MAX_ID,
    # fullness_dist=BetaDistribution(0.95, CircleDistribution()),
    # fullness_dist=ParetoDistribution(0.95, CircleDistribution()),
    fullness_dist=MicroRaidenDistribution(0.95, CircleDistribution()),
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

    position_strategy = config.join_strategy.position_strategy

    # Routing models.
    constant_global_routing = GlobalRoutingStrategy(constant_fee_model)
    net_balance_global_routing = GlobalRoutingStrategy(net_balance_fee_model)
    imbalance_global_routing = GlobalRoutingStrategy(imbalance_fee_model)
    distance_next_hop_routing = NextHopRoutingStrategy(DistancePriorityStrategy(position_strategy))
    distance_net_balance_next_hop_routing = NextHopRoutingStrategy(
        DistanceNetBalancePriorityStrategy(position_strategy)
    )
    assisted_next_hop_routing = NextHopRoutingStrategy(
        GloballyAssistedPriorityStrategy(position_strategy)
    )

    # Routing simulation + animation.
    routing_models = [
        # constant_global_routing,
        distance_next_hop_routing,
        # distance_net_balance_next_hop_routing,
        # assisted_next_hop_routing
    ]
    simulate_routing(
        config, OUT_DIR, num_sample_nodes=20, num_paths=1, value=1, routing_models=routing_models
    )

    # Network scaling simulation.
    routing_models = [
        ('next_hop_distance', distance_next_hop_routing),
        ('next_hop_net_balance', distance_net_balance_next_hop_routing),
        # ('next_hop_globally_assisted', assisted_next_hop_routing)
    ]
    for name, routing_model in routing_models:
        simulate_balancing(
            config,
            OUT_DIR,
            num_transfers=10000,
            transfer_value=1,
            routing_model=routing_model,
            name=name,
            execute_transfers=True
        )


if __name__ == '__main__':
    run()
