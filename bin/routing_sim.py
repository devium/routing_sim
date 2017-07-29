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

from raidensim.config import ParetoNetworkConfiguration
from raidensim.network.channel_network import ChannelNetwork
from raidensim.network.node import Node

random.seed(43)
sys.setrecursionlimit(100)


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
    cn.generate_helpers(config)
    cn.connect_nodes()
    draw(cn)
    # export_obj(cn)
    return cn


def test_basic_network(config):
    cn = setup_network(config)
    draw(cn)


def test_global_pathfinding(config, num_paths=10, value=2):
    cn = setup_network(config)
    for i in range(num_paths):
        print "-" * 40
        source, target = random.sample(cn.nodes, 2)

        path = cn.find_path_global(source, target, value)
        print len(path), path
        draw(cn, path)

        contacted, path = cn.find_path_recursively(source, target, value)
        print len(path), path, contacted
        draw(cn, path)

        path, helper = cn.find_path_with_helper(source, target, value)
        if path:
            print len(path), path
        else:
            print 'No direct path to target sector.'
        draw(cn, path, helper)


def test_balancing(config):
    pass


def draw(cn, path=None, helper_highlight=None):
    from raidensim.draw import draw2d as _draw
    assert isinstance(cn, ChannelNetwork)
    _draw(cn, path, helper_highlight)


##########################################################


if __name__ == '__main__':
    test_basic_channel()
    # test_basic_network()
    test_global_pathfinding(ParetoNetworkConfiguration(1000, 0.6), num_paths=5, value=2)
