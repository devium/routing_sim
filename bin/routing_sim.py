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

from raidensim.network.config import NetworkConfiguration, MicroRaidenNetworkConfiguration
from raidensim.network.dist import ParetoDistribution, BetaDistribution, Distribution

from raidensim import simulate_routing, simulate_balancing

SCRIPT_DIR = os.path.dirname(__file__)
OUT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '../out'))

NETWORK_CONFIG_RAIDEN_NETWORK = {
    'num_nodes': 200,
    # 'fullness_dist': CircleDistribution(),
    # 'fullness_dist': ParetoDistribution(5, 0, 1),
    'fullness_dist': BetaDistribution(0.5, 2),
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
    # 'server_fullness_dist': CircleDistribution(),
    # 'server_fullness_dist': ParetoDistribution(5, 0, 1),
    'server_fullness_dist': BetaDistribution(0.5, 2),
    'client_fraction': 0.95,
    'min_max_initiated_channels': 1,
    'max_max_initiated_channels': 3,
    'min_max_accepted_channels': 100,
    'max_max_accepted_channels': 100,
    'min_deposit': 1,
    'max_deposit': 1
}


def run():
    config = NetworkConfiguration(**NETWORK_CONFIG_RAIDEN_NETWORK)
    # config = NetworkConfiguration(**NETWORK_CONFIG_MICRORAIDEN)
    simulate_routing(config, OUT_DIR, num_paths=1, value=5)
    simulate_balancing(
        config, OUT_DIR, num_transfers=10000, transfer_value=1, fee_model='constant'
    )
    # simulate_balancing(
    #     config, OUT_DIR, num_transfers=10000, transfer_value=1, fee_model='net-balance'
    # )
    # simulate_balancing(
    #     config, OUT_DIR, num_transfers=10000, transfer_value=1, fee_model='imbalance'
    # )

if __name__ == '__main__':
    run()
