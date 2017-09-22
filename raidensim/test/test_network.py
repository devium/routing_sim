import pytest

from raidensim.network.channel_network import ChannelNetwork


def test_network_2_nodes(network_2_nodes: ChannelNetwork):
    network = network_2_nodes
    assert len(network.nodes) == 2
    assert len(network.edges) == 2
    a = next(node for node in network.nodes if node.fullness == 0)
    b = next(node for node in network.nodes if node.fullness == 1)
    assert a.get_deposit(b) == 15
    assert b.get_deposit(a) == 20


def test_channel_attributes(network_2_nodes: ChannelNetwork):
    network = network_2_nodes
    a = next(node for node in network.nodes if node.fullness == 0)
    b = next(node for node in network.nodes if node.fullness == 1)
    assert len(a.partners) == 1
    assert len(b.partners) == 1

    ab, ba = network.edges[a, b], network.edges[b, a]
    assert a.get_balance(b) == 0
    assert a.get_net_balance(b) == 0
    assert a.get_capacity(b) == 15
    assert a.get_imbalance(b) == 5
    assert b.get_balance(a) == 0
    assert b.get_net_balance(a) == 0
    assert b.get_capacity(a) == 20
    assert b.get_imbalance(a) == -5
    assert ab['balance'] == 0
    assert ab['net_balance'] == 0
    assert ab['capacity'] == 15
    assert ab['imbalance'] == 5
    assert ba['balance'] == 0
    assert ba['net_balance'] == 0
    assert ba['capacity'] == 20
    assert ba['imbalance'] == -5

    network.do_transfer([a, b], 2)
    assert a.get_balance(b) == 2
    assert a.get_net_balance(b) == 2
    assert a.get_capacity(b) == 13
    assert a.get_imbalance(b) == 9
    assert b.get_balance(a) == 0
    assert b.get_net_balance(a) == -2
    assert b.get_capacity(a) == 22
    assert b.get_imbalance(a) == -9
    assert ab['balance'] == 2
    assert ab['net_balance'] == 2
    assert ab['capacity'] == 13
    assert ab['imbalance'] == 9
    assert ba['balance'] == 0
    assert ba['net_balance'] == -2
    assert ba['capacity'] == 22
    assert ba['imbalance'] == -9

    network.do_transfer([b, a], 3)
    assert a.get_balance(b) == 2
    assert a.get_net_balance(b) == -1
    assert a.get_capacity(b) == 16
    assert a.get_imbalance(b) == 3
    assert b.get_balance(a) == 3
    assert b.get_net_balance(a) == 1
    assert b.get_capacity(a) == 19
    assert b.get_imbalance(a) == -3
    assert ab['balance'] == 2
    assert ab['net_balance'] == -1
    assert ab['capacity'] == 16
    assert ab['imbalance'] == 3
    assert ba['balance'] == 3
    assert ba['net_balance'] == 1
    assert ba['capacity'] == 19
    assert ba['imbalance'] == -3
