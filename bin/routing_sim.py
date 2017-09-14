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

from raidensim.config import NetworkConfiguration
from raidensim.dist import ParetoDistribution, BetaDistribution
from raidensim.draw import plot_channel_imbalances, plot_channel_distribution, \
    plot_channel_balances
from raidensim.network.channel_network import ChannelNetwork
from raidensim.network.node import Node

random.seed(43)
sys.setrecursionlimit(10000)


def test_basic_channel():
    cn = ChannelNetwork()
    a = Node(cn, 1)
    b = Node(cn, 2)
    cn.G.add_edge(a, b)
    channel_ab = a.channel_view(b)
    channel_ba = b.channel_view(a)

    channel_ab.deposit = 10
    channel_ba.deposit = 20
    channel_ab.balance = 2
    assert channel_ba.balance == -2
    assert channel_ab.capacity == 10 + 2
    assert channel_ba.capacity == 20 - 2


def setup_network(config):
    cn = ChannelNetwork()
    cn.generate_nodes(config)
    # cn.generate_helpers(config)
    cn.connect_nodes()
    return cn


def test_basic_network(config):
    cn = setup_network(config)
    draw(cn)


def test_global_pathfinding(config, num_paths=10, value=2):
    config.fullness_dist.reset()
    random.seed(0)

    cn = setup_network(config)
    draw(cn)

    for i in range(num_paths):
        print("-" * 40)
        source, target = random.sample(cn.nodes, 2)

        print('Global path finding:')
        path = cn.find_path_global(source, target, value)
        if path:
            print('Found path of length {}: {}'.format(len(path), path))
        else:
            print('No path found.')
        draw(cn, path)

        # print('Recursive path finding:')
        # contacted, path = cn.find_path_recursively(source, target, value, [5, 10, 20, 50])
        # if path:
        #     print('Found path of length {}: {}'.format(len(path), path))
        # else:
        #     print('No path found.')
        # print('Contacted {} nodes in the process: {}'.format(len(contacted), contacted))
        # draw(cn, path, contacted)

        print('BFS path finding:')
        visited, path = source.find_path_bfs(target.uid, value)
        if path:
            print('Found path of length {}: {}'.format(len(path), path))
        else:
            print('No path found.')
        print('Contacted {} nodes in the process: {}'.format(len(visited), visited))
        draw(cn, path, visited)

        # print('Path finding with helpers.')
        # path, helper = cn.find_path_with_helper(source, target, value)
        # if path:
        #     print(len(path), path)
        # else:
        #     print('No direct path to target sector.')
        # draw(cn, path, None, helper)


def test_balancing(config, num_transfers, transfer_value, path_cost):
    from raidensim.draw import plot_channel_capacities
    import matplotlib.pyplot as plt

    random.seed(0)
    config.fullness_dist.reset()
    cn = setup_network(config)
    max_capacity = config.max_deposit * 2

    fig, axs = plt.subplots(2, 4)
    fig.set_size_inches(16, 8)
    plot_channel_capacities(cn, axs[0][0], max_capacity)
    balance_var_pre = plot_channel_balances(cn, axs[0][1], config.max_deposit)
    imbalance_var_pre = plot_channel_imbalances(cn, axs[0][2], max_capacity)
    plot_channel_distribution(cn, axs[0][3])

    num_channels_uni = sum((len(edges) for edges in cn.G.edge.values()))
    print('Simulating {} transfers between {} nodes over {} bidirectional channels.'.format(
        num_transfers, len(cn.nodes), num_channels_uni // 2
    ))

    failed = 0
    tic = time.time()
    for i in range(num_transfers):
        toc = time.time()
        if toc - tic > 5:
            tic = toc
            print('Transfer {}/{}'.format(i + 1, num_transfers))

        source, target = random.sample(cn.nodes, 2)
        # Repick nodes that cannot send transfers anymore.
        while max(cv.capacity for cv in source.channels.values()) < transfer_value:
            source, target = random.sample(cn.nodes, 2)

        path = cn.find_path_global(source, target, transfer_value, path_cost)
        if not path:
            print('No Path found from {} to {} that could sustain {} token(s).'.format(
                source, target, transfer_value
            ))
            failed += 1
        else:
            cn.do_transfer(path, transfer_value)

    print('Finished. {} transfers failed.'.format(failed))
    plot_channel_capacities(cn, axs[1][0], max_capacity)
    balance_var_post = plot_channel_balances(cn, axs[1][1], config.max_deposit)
    imbalance_var_post = plot_channel_imbalances(cn, axs[1][2], max_capacity)

    # Stats plot (labels only).
    labels = [
        'Nodes: {}'.format(len(cn.nodes)),
        'Channels: {}'.format(num_channels_uni // 2),
        'Transfers: {}'.format(num_transfers),
        '',
        'Top row: initial network state',
        'Bottom row: after {} transfers'.format(num_transfers),
        '',
        'Fee model: {}'.format(path_cost),
        'Failed transfers: {}'.format(failed),
        'Balance variance before: {:.2f}'.format(balance_var_pre),
        'Balance variance after: {:.2f}'.format(balance_var_post),
        'Imbalance variance before: {:.2f}'.format(imbalance_var_pre),
        'Imbalance variance after: {:.2f}'.format(imbalance_var_post)
    ]
    for i, label in enumerate(labels):
        axs[1][3].text(0, 0.95 - i * 0.07, label)

    axs[0][0].set_ylabel('Distribution')
    axs[1][0].set_ylabel('Distribution')
    axs[1][0].set_xlabel('Channel capacity')
    axs[1][1].set_xlabel('Channel balance (abs)')
    axs[1][2].set_xlabel('Channel imbalance')
    axs[0][3].set_xlabel('Channel count per node')
    axs[1][3].axis('off')

    plt.show()


def test_cost_func_fees():
    cost_func = ChannelNetwork._get_path_cost_function_imbalance_fees(1)

    class SimpleNode:
        def __init__(self, uid):
            self.uid = uid

    cost = cost_func(SimpleNode(1), SimpleNode(2), {1: 10, 2: 12, 'balance': 1})  # 0-2
    assert abs(cost - 0.881) < 0.01
    cost = cost_func(SimpleNode(1), SimpleNode(2), {1: 10, 2: 12, 'balance': 3})  # 4-2
    assert abs(cost - 0.119) < 0.01
    cost = cost_func(SimpleNode(2), SimpleNode(1), {1: 10, 2: 12, 'balance': 3})  # -4-2
    assert abs(cost - 0.998) < 0.01
    cost = cost_func(SimpleNode(1), SimpleNode(2), {1: 10, 2: 12, 'balance': -5})  # -12-2
    assert abs(cost - 0.999) < 0.01


def draw(cn, path=None, highlighted_nodes=None, helper_highlight=None):
    from raidensim.draw import draw2d as _draw
    assert isinstance(cn, ChannelNetwork)
    _draw(cn, path, highlighted_nodes, helper_highlight)


##########################################################


if __name__ == '__main__':
    test_basic_channel()
    test_cost_func_fees()
    # test_basic_network()
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
    test_global_pathfinding(config, num_paths=3, value=5)
    # test_balancing(config, num_transfers=10000, transfer_value=1, path_cost='constant')
    # test_balancing(config, num_transfers=10000, transfer_value=1, path_cost='balance')
    # test_balancing(config, num_transfers=10000, transfer_value=1, path_cost='imbalance')
