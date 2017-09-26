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
from raidensim.routing.priority_bfs_routing_model import (
    PriorityRoutingModel,
    distance_net_balance_priority,
    distance_priority
)
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
        max_network_distance=1/3,
        kademlia_targets_per_cycle=4,
        max_initiated_channels=(2, 8),
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
    distance_priority_routing = PriorityRoutingModel(distance_priority)
    distance_net_balance_priority_routing = PriorityRoutingModel(distance_net_balance_priority)

    # Routing simulation + animation.
    routing_models = [
        constant_global_routing,
        distance_net_balance_priority_routing
    ]
    simulate_routing(config, OUT_DIR, num_paths=3, value=1, routing_models=routing_models)

    # Network scale simulation.
    routing_models = [
        ('priority_distance', distance_priority_routing),
        ('priority_net_balance', distance_net_balance_priority_routing)
    ]
    for name, routing_model in routing_models:
        simulate_balancing(
            config,
            OUT_DIR,
            num_transfers=1000,
            transfer_value=1,
            routing_model=routing_model,
            name=name,
            execute_transfers=True
        )


if __name__ == '__main__':
    run()
