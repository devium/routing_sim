import os

from raidensim.network.config import NetworkConfiguration
from raidensim.network.dist import (
    ParetoDistribution,
    BetaDistribution,
    MicroRaidenDistribution,
    CircleDistribution
)
from raidensim.routing.global_routing_model import (
    GlobalRoutingModel,
    imbalance_fee_model,
    net_balance_fee_model,
    constant_fee_model
)
from raidensim.routing.next_hop_routing_model import NextHopRoutingModel
from raidensim.routing.priority_models import (
    DistancePriorityModel,
    DistanceNetBalancePriorityModel,
    GloballyAssistedPriorityModel)
from raidensim.simulation import simulate_routing, simulate_balancing

from raidensim.strategy.network_strategies import RaidenNetworkStrategy, MicroRaidenNetworkStrategy

SCRIPT_DIR = os.path.dirname(__file__)
OUT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '../out'))


NETWORK_CONFIG_RAIDEN_NETWORK = NetworkConfiguration(
    num_nodes=500,
    # fullness_dist=CircleDistribution(),
    # fullness_dist=ParetoDistribution(5, 0, 1),
    fullness_dist=BetaDistribution(0.5, 2),
    network_strategy=RaidenNetworkStrategy(
        min_incoming_deposit=0.2,
        max_network_distance=1/8,
        kademlia_targets_per_cycle=4,
        max_initiated_channels=(4, 10),
        max_accepted_channels=(10, 20),
        deposit=(4, 100)
    )
)


NETWORK_CONFIG_MICRORAIDEN = NetworkConfiguration(
    num_nodes=200,
    # fullness_dist=BetaDistribution(0.95, CircleDistribution()),
    # fullness_dist=ParetoDistribution(0.95, CircleDistribution()),
    fullness_dist=MicroRaidenDistribution(0.95, CircleDistribution()),
    network_strategy=MicroRaidenNetworkStrategy(
        max_initiated_channels=(1, 3),
        deposit=10
    )
)


def run():
    # Network configuration.
    config = NETWORK_CONFIG_RAIDEN_NETWORK
    # config = NETWORK_CONFIG_MICRORAIDEN

    # Routing models.
    constant_global_routing = GlobalRoutingModel(constant_fee_model)
    net_balance_global_routing = GlobalRoutingModel(net_balance_fee_model)
    imbalance_global_routing = GlobalRoutingModel(imbalance_fee_model)
    distance_next_hop_routing = NextHopRoutingModel(DistancePriorityModel())
    distance_net_balance_next_hop_routing = NextHopRoutingModel(DistanceNetBalancePriorityModel())
    assisted_next_hop_routing = NextHopRoutingModel(GloballyAssistedPriorityModel())

    # Routing simulation + animation.
    routing_models = [
        constant_global_routing,
        distance_net_balance_next_hop_routing,
        assisted_next_hop_routing
    ]
    simulate_routing(config, OUT_DIR, num_paths=1, value=1, routing_models=routing_models)

    # Network scale simulation.
    routing_models = [
        # ('next_hop_distance', distance_priority_routing),
        ('next_hop_net_balance', distance_net_balance_next_hop_routing),
        ('next_hop_globally_assisted', assisted_next_hop_routing)
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
