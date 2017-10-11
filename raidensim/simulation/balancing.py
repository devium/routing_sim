import random

import math

import os

import time
from typing import List

import matplotlib.pyplot as plt
import numpy as np
import shutil

from raidensim.network.network import Network
from raidensim.network.raw_network import RawNetwork
from raidensim.strategy.position_strategy import PositionStrategy
from raidensim.strategy.routing.routing_strategy import RoutingStrategy
from raidensim.types import Path
from raidensim.util import sigmoid


def simulate_balancing(
        net: Network,
        out_dir,
        num_transfers: int,
        transfer_value: int,
        routing_model: RoutingStrategy,
        name: str,
        execute_transfers=True,
        max_recorded_fails=5
):
    """
    Simulates network transfers under the given fee model and plots some statistics.
    """
    net.reset()

    # Baseline data.
    pre_capacities = get_channel_capacities(net.raw)
    pre_net_balances = get_channel_net_balances(net.raw)
    pre_imbalances = get_channel_imbalances(net.raw)
    nums_channels = get_channel_counts(net.raw)
    channel_distances = get_channel_distances(net.raw, net.config.position_strategy)

    num_channels_uni = len(net.raw.edges)
    pre_net_balance_stdev = math.sqrt(sum(x**2 for x in pre_net_balances) / len(pre_net_balances))
    pre_imbalance_stdev = math.sqrt(sum(x**2 for x in pre_imbalances) / len(pre_imbalances))

    # Simulation.
    failed, fail_records, avg_length, avg_contacted, avg_fee = simulate_transfers(
        net.raw,
        num_transfers,
        transfer_value,
        routing_model,
        execute_transfers,
        max_recorded_fails
    )

    print('Evaluating simulation.')

    # Post-simulation evaluation.
    post_capacities = get_channel_capacities(net.raw)
    post_net_balances = get_channel_net_balances(net.raw)
    post_imbalances = get_channel_imbalances(net.raw)

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

    # Plots.
    fig, axs = plt.subplots(3, 4)
    fig.set_size_inches(16, 10)

    axs[0][0].hist(pre_capacities, bins=50, edgecolor='black', range=[0, max_capacity])
    axs[1][0].hist(post_capacities, bins=50, edgecolor='black', range=[0, max_capacity])
    axs[0][1].hist(pre_net_balances, bins=50, range=[0, max_net_balance], edgecolor='black')
    axs[1][1].hist(post_net_balances, bins=50, range=[0, max_net_balance], edgecolor='black')
    axs[0][2].hist(pre_imbalances, bins=50, range=[0, max_imbalance], edgecolor='black')
    axs[1][2].hist(post_imbalances, bins=50, range=[0, max_imbalance], edgecolor='black')
    axs[0][3].hist(
        nums_channels, bins=range(max_num_channels + 2), align='left', edgecolor='black'
    )
    axs[2][0].hist(failed, bins=50, range=[0, num_transfers], edgecolor='black')
    freq, _, _ = axs[2][1].hist(channel_distances, bins=50, edgecolor='black')
    # Plot expected 1/d distance distribution for decentralized routing.
    x = np.arange(2, int(max(channel_distances)) + 1)
    y = 2 / x * freq[0]
    axs[2][1].plot(x, y)

    # Stats plot (labels only).
    labels = [
        'Simulation name: {}'.format(name),
        'Top row: initial network state',
        'Bottom row: after {} transfers'.format(num_transfers),
        '',
        'Nodes: {}'.format(len(net.raw.nodes)),
        'Channels: {}'.format(num_channels_uni // 2),
        'Transfers: {}'.format(num_transfers),
        '',
        'Failed transfers: {}'.format(len(failed)),
        'Average transfer hops: {:.2f}'.format(avg_length),
        'Average nodes contacted: {:.2f}'.format(avg_contacted),
        'Average fee (net balance): {:.2f}'.format(avg_fee),
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
    axs[0][3].xaxis.set_ticks(range(0, max_num_channels + 1, 2))
    axs[0][3].xaxis.set_ticks(range(1, max_num_channels + 1, 2), minor=True)
    axs[1][3].axis('off')
    axs[2][0].set_xlabel('Transfer #')
    axs[2][0].set_ylabel('Failed transfers')
    axs[2][1].set_xlabel('Channel distances > 1')
    axs[2][2].axis('off')
    axs[2][3].axis('off')

    dirpath = os.path.join(out_dir, 'balancing_{}_{}_{}'.format(
        net.config.num_nodes, num_transfers, name
    ))
    shutil.rmtree(dirpath, ignore_errors=True)
    os.makedirs(dirpath, exist_ok=True)

    fig.savefig(os.path.join(dirpath, 'stats'), bbox_inches='tight')
    print('Drawing network.')
    net.draw(filepath=os.path.join(dirpath, 'network'))
    if fail_records:
        print('Rendering transfer failures.')
    for i, fail_history in enumerate(fail_records):
        dirpath = os.path.join(dirpath, 'fail_{:02d}'.format(i))
        net.draw_gif(
            fail_history['source'],
            fail_history['target'],
            fail_history['path_history'],
            100,
            dirpath
        )
        dirpath = os.path.dirname(dirpath)
    print('Rendering heat maps.')
    net.draw(heatmap_attr='num_transfers', filepath=os.path.join(dirpath, 'heatmap_transfers'))
    net.draw(heatmap_attr='net_balance', filepath=os.path.join(dirpath, 'heatmap_balance'))


def simulate_transfers(
        raw: RawNetwork,
        num_transfers: int,
        value: int,
        routing_model: RoutingStrategy,
        execute_transfers: bool,
        max_recorded_fails: int
) -> (List[int], float, float, float):
    """
    Perform transfers between random nodes.
    """
    num_channels_uni = len(raw.edges)
    print('Simulating {} transfers between {} nodes over {} bidirectional channels.'.format(
        num_transfers, len(raw.nodes), num_channels_uni // 2
    ))

    failed = []
    fail_records = []
    sum_path_lengths = 0
    sum_contacted = 0
    sum_fees = 0
    tic = time.time()
    subtic = tic
    for i in range(num_transfers):
        toc = time.time()
        if toc - subtic > 5:
            # Progress report every 5 seconds.
            subtic = toc
            print('Transfer {}/{}'.format(i + 1, num_transfers))

        source, target = random.sample(raw.nodes, 2)
        # Repick nodes that cannot send transfers anymore.
        while max(e['capacity'] for e in raw[source].values()) < value:
            source, target = random.sample(raw.nodes, 2)

        path, path_history = routing_model.route(raw, source, target, value)
        if not path:
            print('No Path found from {} to {} that could sustain {} token(s).'.format(
                source, target, value
            ))
            failed.append(i)
            if len(fail_records) < max_recorded_fails:
                fail_records.append({
                    'source': source,
                    'target': target,
                    'path_history': path_history
                })
        else:
            sum_fees += get_net_balance_fee(raw, path, value)
            if execute_transfers:
                raw.do_transfer(path, value)
            sum_path_lengths += len(path)
            sum_contacted += len({node for subpath in path_history for node in subpath})

    toc = time.time()
    num_failed = len(failed)
    num_success = num_transfers - num_failed
    print('Finished after {} seconds. {} transfers failed.'.format(toc - tic, num_failed))
    return (
        failed,
        fail_records,
        sum_path_lengths/num_success,
        sum_contacted/num_success,
        sum_fees/num_success
    )


def get_channel_distances(raw: RawNetwork, position_strategy: PositionStrategy):
    return [
        position_strategy.distance(u, v) for u, v in raw.edges
        if position_strategy.distance(u, v) > 1
    ]


def get_net_balance_fee(raw: RawNetwork, path: Path, value: int) -> float:
    fee = 0
    for i in range(len(path) - 1):
        u = path[i]
        v = path[i + 1]
        e = raw[u][v]
        fee += sigmoid(e['net_balance'] + value)
    return fee


def get_channel_counts(raw: RawNetwork) -> List[int]:
    return [len(raw[node]) for node in raw.nodes]


def get_channel_capacities(raw: RawNetwork) -> List[float]:
    return [e['capacity'] for e in raw.edges.values()]


def get_channel_net_balances(raw: RawNetwork) -> List[float]:
    bi_edges = {frozenset({a, b}) for a, b in raw.edges}
    return [abs(raw[a][b]['net_balance']) for a, b in bi_edges]


def get_channel_imbalances(raw: RawNetwork) -> List[float]:
    bi_edges = {frozenset({a, b}) for a, b in raw.edges}
    return [abs(raw[a][b]['imbalance']) for a, b in bi_edges]
