import random

import math

import os

import time
from collections import defaultdict
from typing import List

from raidensim.network.channel_network import ChannelNetwork
from raidensim.network.config import NetworkConfiguration


def simulate_balancing(
        config: NetworkConfiguration,
        out_dir,
        num_transfers: int,
        transfer_value: int,
        fee_model: str
):
    import matplotlib.pyplot as plt

    random.seed(0)
    config.fullness_dist.reset()
    cn = ChannelNetwork(config)

    pre_capacities = get_channel_capacities(cn)
    pre_net_balances = get_channel_net_balances(cn)
    pre_imbalances = get_channel_imbalances(cn)
    nums_channels = get_channel_counts(cn)

    num_channels_uni = len(cn.edges)
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

    os.makedirs(out_dir, exist_ok=True)
    filename = 'balancing_{}_{}_{}.png'.format(config.num_nodes, num_transfers, fee_model)
    fig.savefig(os.path.join(out_dir, filename))


def simulate_transfers(cn: ChannelNetwork, num_transfers: int, value: int, fee_model: str) -> int:
    num_channels_uni = len(cn.edges)
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
        while max(source.get_capacity(partner) for partner in source.partners) < value:
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


def get_channel_counts(cn: ChannelNetwork) -> List[int]:
    return [len(node.partners) for node in cn.nodes]


def get_channel_capacities(cn: ChannelNetwork) -> List[float]:
    return [a.get_capacity(b) for a, b in cn.edges]


def get_channel_net_balances(cn: ChannelNetwork) -> List[float]:
    bi_edges = {frozenset({a, b}) for a, b in cn.edges}
    return [abs(a.get_net_balance(b)) for a, b in bi_edges]


def get_channel_imbalances(cn: ChannelNetwork) -> List[float]:
    bi_edges = {frozenset({a, b}) for a, b in cn.edges}
    return [abs(a.get_imbalance(b)) for a, b, in bi_edges]
