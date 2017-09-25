#!/usr/bin/env python

"""
Network Backbone:

- Nodes connnect in a Kademlia style fashion but not strictly
- Light clients connect to full nodes

Tests:
- Test nodes doing a recursive path lookup
- Test nodes maintaining a view on the capacity up to n hops distance
- Test global path finding helper
- Count number of messages
- Count success rate
- Compare path length

Implement:
- Creation of the Network + storage/load of it
- power distribution of capacity
- flexible framework to simulate

Todo:
* variation of channel deposits
* preference for channel partners with similar deposits
* add light clients
* visualize deposits, light clients
* variation of capacities
* imprecise kademlia for sybill attacks prevention and growth of network
* locally cached neighbourhood capacity
* simulate availabiliy of nodes
* stats on global and recursive path finding

* calc the number of messages sent for global, locally cached and recursive routing
* 3d visualization of the network (z-axis being the deposits)


Interactive:
* rebalancing fees, fee based routing

"""
import os

from raidensim.network.config import NetworkConfiguration
from raidensim.network.dist import (
    ParetoDistribution,
    BetaDistribution,
    MicroRaidenDistribution,
    CircleDistribution
)
from raidensim.routing.global_routing_model import GlobalRoutingModel
from raidensim.routing.priority_bfs_routing_model import PriorityBFSRoutingModel
from raidensim.simulation import simulate_routing, simulate_balancing

from raidensim.strategy.network_strategies import RaidenNetworkStrategy, MicroRaidenNetworkStrategy

SCRIPT_DIR = os.path.dirname(__file__)
OUT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '../out'))


NETWORK_CONFIG_RAIDEN_NETWORK = NetworkConfiguration(
    num_nodes=100,
    # fullness_dist=CircleDistribution(),
    # fullness_dist=ParetoDistribution(5, 0, 1),
    fullness_dist=BetaDistribution(0.5, 2),
    network_strategy=RaidenNetworkStrategy(
        min_incoming_deposit=0.2,
        max_network_distance=1/3,
        max_initiated_channels=(2, 10),
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
    constant_routing = GlobalRoutingModel(GlobalRoutingModel.fee_model_constant)
    net_balance_routing = GlobalRoutingModel(GlobalRoutingModel.fee_model_net_balance)
    imbalance_routing = GlobalRoutingModel(GlobalRoutingModel.fee_model_imbalance)
    bfs_routing = PriorityBFSRoutingModel(PriorityBFSRoutingModel.distance_priority)

    routing_models = [
        constant_routing,
        bfs_routing
    ]
    simulate_routing(config, OUT_DIR, num_paths=4, value=5, routing_models=routing_models)
    # simulate_balancing(
    #     config,
    #     OUT_DIR,
    #     num_transfers=1000,
    #     transfer_value=1,
    #     routing_model=constant_routing,
    #     name='constant'
    # )
    # simulate_balancing(
    #     config,
    #     OUT_DIR,
    #     num_transfers=1000,
    #     transfer_value=1,
    #     routing_model=net_balance_routing,
    #     name='net-balance'
    # )
    # simulate_balancing(
    #     config,
    #     OUT_DIR,
    #     num_transfers=1000,
    #     transfer_value=1,
    #     routing_model=imbalance_routing,
    #     name='imbalance'
    # )

if __name__ == '__main__':
    run()
