import pytest

from raidensim.network.network import Network


def test_network_2_nodes(network_2_nodes: Network):
    net = network_2_nodes
    raw = net.raw
    assert raw.number_of_nodes() == 2
    assert raw.number_of_edges() == 2
    a = next(node for node in raw.nodes if node.fullness == 0)
    b = next(node for node in raw.nodes if node.fullness == 1)
    assert raw[a][b]['deposit'] == 15
    assert raw[b][a]['deposit'] == 20


def test_channel_attributes(network_2_nodes: Network):
    net = network_2_nodes
    raw = net.raw
    a = next(node for node in raw.nodes if node.fullness == 0)
    b = next(node for node in raw.nodes if node.fullness == 1)
    assert len(raw.neighbors(a)) == 1
    assert len(raw.neighbors(b)) == 1

    ab, ba = raw.edges[a, b], raw.edges[b, a]
    assert ab['balance'] == 0
    assert ab['net_balance'] == 0
    assert ab['capacity'] == 15
    assert ab['imbalance'] == 5
    assert ba['balance'] == 0
    assert ba['net_balance'] == 0
    assert ba['capacity'] == 20
    assert ba['imbalance'] == -5

    raw.do_transfer([a, b], 2)
    assert ab['balance'] == 2
    assert ab['net_balance'] == 2
    assert ab['capacity'] == 13
    assert ab['imbalance'] == 9
    assert ba['balance'] == 0
    assert ba['net_balance'] == -2
    assert ba['capacity'] == 22
    assert ba['imbalance'] == -9

    raw.do_transfer([b, a], 3)
    assert ab['balance'] == 2
    assert ab['net_balance'] == -1
    assert ab['capacity'] == 16
    assert ab['imbalance'] == 3
    assert ba['balance'] == 3
    assert ba['net_balance'] == 1
    assert ba['capacity'] == 19
    assert ba['imbalance'] == -3
