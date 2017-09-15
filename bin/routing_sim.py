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

import random
import sys

import time

import math

import os

from raidensim.config import NetworkConfiguration
from raidensim.dist import ParetoDistribution, BetaDistribution
from raidensim.draw import draw2d
from raidensim.network.channel_network import ChannelNetwork
from raidensim.network.node import Node
from raidensim.stat import get_channel_capacities, get_channel_net_balances, \
    get_channel_imbalances, get_channel_distribution

random.seed(43)
sys.setrecursionlimit(10000)

SCRIPT_DIR = os.path.dirname(__file__)
OUT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '../out'))


def setup_network(config):
    cn = ChannelNetwork()
    cn.generate_nodes(config)
    # cn.generate_helpers(config)
    cn.connect_nodes()
    return cn


def simulate_pathfinding(config, num_paths=10, value=2):
    config.fullness_dist.reset()
    random.seed(0)

    cn = setup_network(config)
    filename = 'routing_{}.png'.format(config.num_nodes)
    draw2d(cn, filepath=os.path.join(OUT_DIR, filename))

    for i in range(num_paths):
        print("-" * 40)
        source, target = random.sample(cn.nodes, 2)

        print('Global path finding:')
        path = cn.find_path_global(source, target, value)
        if path:
            print('Found path of length {}: {}'.format(len(path), path))
        else:
            print('No path found.')
        filename = 'routing_{}_{}_global.png'.format(config.num_nodes, i)
        draw2d(cn, path, [path, [source, target]], filepath=os.path.join(OUT_DIR, filename))

        # print('Recursive path finding:')
        # contacted, path = cn.find_path_recursively(source, target, value, [5, 10, 20, 50])
        # if path:
        #     print('Found path of length {}: {}'.format(len(path), path))
        # else:
        #     print('No path found.')
        # print('Contacted {} nodes in the process: {}'.format(len(contacted), contacted))
        # draw(cn, path, contacted)

        print('BFS path finding:')
        _, path, path_history = source.find_path_bfs(target.uid, value)
        if path:
            print('Found path of length {}: {}'.format(len(path), path))
        else:
            print('No path found.')
        visited = {source}
        for j, subpath in enumerate(path_history):
            visited |= set(subpath)
            filename = 'routing_{}_{}_bfs_{}.png'.format(config.num_nodes, i, j)
            draw2d(
                cn, subpath, [visited, [source, target]], filepath=os.path.join(OUT_DIR, filename)
            )
        print('Contacted {} nodes in the process: {}'.format(len(visited), visited))
        filename = 'routing_{}_{}_bfs.png'.format(config.num_nodes, i)
        draw2d(cn, path, [visited, [source, target]], filepath=os.path.join(OUT_DIR, filename))

        # print('Path finding with helpers.')
        # path, helper = cn.find_path_with_helper(source, target, value)
        # if path:
        #     print(len(path), path)
        # else:
        #     print('No direct path to target sector.')
        # draw(cn, path, None, helper)


def simulate_balancing(
        config: NetworkConfiguration, num_transfers: int, transfer_value: int, fee_model: str
):
    import matplotlib.pyplot as plt

    random.seed(0)
    config.fullness_dist.reset()
    cn = setup_network(config)

    pre_capacities = get_channel_capacities(cn)
    pre_net_balances = get_channel_net_balances(cn)
    pre_imbalances = get_channel_imbalances(cn)
    nums_channels = get_channel_distribution(cn)

    num_channels_uni = sum((len(edges) for edges in cn.G.edge.values()))
    pre_net_balance_stdev = math.sqrt(sum(x**2 for x in pre_net_balances) / len(pre_net_balances))
    pre_imbalance_stdev = math.sqrt(sum(x**2 for x in pre_imbalances) / len(pre_imbalances))

    failed = simulate_transfers(cn, num_transfers, transfer_value, fee_model)

    post_capacities = get_channel_capacities(cn)
    post_net_balances = get_channel_net_balances(cn)
    post_imbalances = get_channel_imbalances(cn)

    post_net_balance_stdev = math.sqrt(
        sum(x**2 for x in post_net_balances) / len(post_net_balances)
    )
    post_imbalance_stdev = math.sqrt(
        sum(x**2 for x in post_imbalances) / len(post_imbalances)
    )

    max_capacity = max(pre_capacities + post_capacities)
    max_net_balance = max(pre_net_balances + post_net_balances)
    max_imbalance = max(pre_imbalances + post_imbalances)
    max_num_channels = max(nums_channels)

    fig, axs = plt.subplots(2, 4)
    fig.set_size_inches(16, 8)

    axs[0][0].hist(pre_capacities, bins=50, edgecolor='black', range=[0, max_capacity])
    axs[1][0].hist(post_capacities, bins=50, edgecolor='black', range=[0, max_capacity])
    axs[0][1].hist(pre_net_balances, bins=50, range=[0, max_net_balance], edgecolor='black')
    axs[1][1].hist(post_net_balances, bins=50, range=[0, max_net_balance], edgecolor='black')
    axs[0][2].hist(pre_imbalances, bins=50, range=[0, max_imbalance], edgecolor='black')
    axs[1][2].hist(post_imbalances, bins=50, range=[0, max_imbalance], edgecolor='black')
    axs[0][3].hist(nums_channels, bins=range(max_num_channels + 2), align='left', edgecolor='black')
    axs[0][3].xaxis.set_ticks(range(0, max_num_channels + 1, 2))
    axs[0][3].xaxis.set_ticks(range(1, max_num_channels + 1, 2), minor=True)

    # Stats plot (labels only).
    labels = [
        'Nodes: {}'.format(len(cn.nodes)),
        'Channels: {}'.format(num_channels_uni // 2),
        'Transfers: {}'.format(num_transfers),
        '',
        'Top row: initial network state',
        'Bottom row: after {} transfers'.format(num_transfers),
        '',
        'Fee model: {}'.format(fee_model),
        'Failed transfers: {}'.format(failed),
        'Balance SD before: {:.2f}'.format(pre_net_balance_stdev),
        'Balance SD after: {:.2f}'.format(post_net_balance_stdev),
        'Imbalance SD before: {:.2f}'.format(pre_imbalance_stdev),
        'Imbalance SD after: {:.2f}'.format(post_imbalance_stdev)
    ]
    for i, label in enumerate(labels):
        axs[1][3].text(0, 0.95 - i * 0.07, label)

    axs[0][0].set_ylabel('Distribution')
    axs[1][0].set_ylabel('Distribution')
    axs[1][0].set_xlabel('Channel capacity')
    axs[1][1].set_xlabel('Channel net balance (abs)')
    axs[1][2].set_xlabel('Channel imbalance')
    axs[0][3].set_xlabel('Channel count per node')
    axs[1][3].axis('off')

    os.makedirs(OUT_DIR, exist_ok=True)
    filename = 'balancing_{}_{}_{}.png'.format(config.num_nodes, num_transfers, fee_model)
    fig.savefig(os.path.join(OUT_DIR, filename))


def simulate_transfers(cn: ChannelNetwork, num_transfers: int, value: int, fee_model: str) -> int:
    num_channels_uni = sum((len(edges) for edges in cn.G.edge.values()))
    print('Simulating {} transfers between {} nodes over {} bidirectional channels.'.format(
        num_transfers, len(cn.nodes), num_channels_uni // 2
    ))

    failed = 0
    tic = time.time()
    for i in range(num_transfers):
        toc = time.time()
        if toc - tic > 5:
            # Progress report every 5 seconds.
            tic = toc
            print('Transfer {}/{}'.format(i + 1, num_transfers))

        source, target = random.sample(cn.nodes, 2)
        # Repick nodes that cannot send transfers anymore.
        while max(cv.capacity for cv in source.channels.values()) < value:
            source, target = random.sample(cn.nodes, 2)

        path = cn.find_path_global(source, target, value, fee_model)
        if not path:
            print('No Path found from {} to {} that could sustain {} token(s).'.format(
                source, target, value
            ))
            failed += 1
        else:
            cn.do_transfer(path, value)

    print('Finished. {} transfers failed.'.format(failed))
    return failed


if __name__ == '__main__':
    # fullness_dist = ParetoDistribution(5, 0, 1)
    fullness_dist = BetaDistribution(0.5, 2)
    config = NetworkConfiguration(
        num_nodes=100,
        fullness_dist=fullness_dist,
        min_channels=2,
        max_channels=10,
        min_deposit=4,
        max_deposit=100
    )
    simulate_pathfinding(config, num_paths=3, value=5)
    # simulate_balancing(config, num_transfers=10000, transfer_value=1, fee_model='constant')
    # simulate_balancing(config, num_transfers=10000, transfer_value=1, fee_model='net-balance')
    # simulate_balancing(config, num_transfers=10000, transfer_value=1, fee_model='imbalance')
