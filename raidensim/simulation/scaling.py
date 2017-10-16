import math
import os
import random
import time
from typing import List, Dict, Union

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

from raidensim.network.network import Network
from raidensim.network.node import Node
from raidensim.network.raw_network import RawNetwork
from raidensim.strategy.fee_strategy import FeeStrategy
from raidensim.strategy.routing.routing_strategy import RoutingStrategy
from raidensim.types import Path


class NetworkStats:
    def __init__(self, net: Network):
        print('Collecting network stats.')

        raw = net.raw
        self.raw = raw
        self.num_nodes = len(raw.nodes)
        self.num_required_channels = net.config.join_strategy.num_required_channels
        bi_edges = {frozenset({a, b}) for a, b in raw.edges}
        self.capacities = [e['capacity'] for e in raw.edges.values()]
        self.net_balances = [abs(raw[a][b]['net_balance']) for a, b in bi_edges]
        self.imbalances = [abs(raw[a][b]['imbalance']) for a, b in bi_edges]
        self.channel_counts = [len(raw[node]) for node in raw.nodes]
        self.channel_distances = [net.config.position_strategy.distance(u, v) for u, v in bi_edges]
        self.channel_distances = [distance for distance in self.channel_distances if distance > 1]
        self.num_channels_uni = len(raw.edges)
        self.num_depleted_channels = sum(1 for e in raw.edges.values() if e['capacity'] == 0)
        self.net_balance_stdev = math.sqrt(
            sum(x ** 2 for x in self.net_balances) / len(self.net_balances)
        )
        self.imbalance_stdev = math.sqrt(
            sum(x ** 2 for x in self.imbalances) / len(self.imbalances)
        )


class SimulationStats:
    name = ''
    num_transfers = 0
    avg_transfer_hops = 0
    avg_contacted = 0
    avg_fee = 0

    def __init__(self):
        self.failed = []
        self.failure_recordings = []


def simulate_scaling(
        net: Network,
        out_dir: str,
        num_transfers: int,
        transfer_value: int,
        fee_strategy: FeeStrategy,
        routing_strategy: RoutingStrategy,
        name: str,
        max_recorded_failures: int,
        execute_transfers=True
):
    """
    Simulates network transfers under the given fee model and plots some statistics.
    """
    net.reset()

    # Baseline data.
    pre_stats = NetworkStats(net)

    # Simulation.
    sim_stats = simulate_transfers(
        net.raw,
        num_transfers,
        transfer_value,
        routing_strategy,
        fee_strategy,
        execute_transfers,
        max_recorded_failures,
        name
    )

    # Post-simulation evaluation.
    post_stats = NetworkStats(net)

    dirpath = os.path.join(out_dir, 'scaling_{}_{}_{}'.format(
        net.config.num_nodes, num_transfers, name
    ))
    os.makedirs(dirpath, exist_ok=True)

    # Plot stuff.
    plot_stats(pre_stats, post_stats, sim_stats, dirpath)

    if net.config.num_nodes < 50000:
        print('Rendering network.')
        net.draw(filepath=os.path.join(dirpath, 'network'))
    else:
        print('Too many nodes to reasonably render. Skipping.')
    plot_depleted_channels(net, transfer_value, dirpath)
    plot_transfer_failures(net, sim_stats.failure_recordings, dirpath)


def simulate_transfers(
        raw: RawNetwork,
        num_transfers: int,
        transfer_value: int,
        routing_strategy: RoutingStrategy,
        fee_strategy: FeeStrategy,
        execute_transfers: bool,
        max_recorded_failures: int,
        name: str
) -> SimulationStats:
    """
    Perform transfers between random nodes.
    """
    num_channels_uni = len(raw.edges)
    print('Simulating {} transfers between {} nodes over {} bidirectional channels.'.format(
        num_transfers, len(raw.nodes), num_channels_uni // 2
    ))

    stats = SimulationStats()
    tic = time.time()
    subtic = tic
    for i in range(num_transfers):
        toc = time.time()
        if toc - subtic > 5:
            # Progress report every 5 seconds.
            subtic = toc
            print('Transfer {}/{}'.format(i + 1, num_transfers))

        source, target = random.sample(raw.nodes, 2)
        # Repick nodes that cannot send or receive transfers anymore.
        while all(e['capacity'] < transfer_value for e in raw[source].values()) and all(
            e['deposit'] - e['net_balance'] + e['imbalance'] < transfer_value
            for e in raw[target].values()
        ):
            source, target = random.sample(raw.nodes, 2)

        path, path_history = routing_strategy.route(raw, source, target, transfer_value)
        if not path:
            print('No Path found from {} to {} that could sustain {} token(s).'.format(
                source, target, transfer_value
            ))
            stats.failed.append(i)
            if len(stats.failure_recordings) < max_recorded_failures:
                stats.failure_recordings.append({
                    'source': source,
                    'target': target,
                    'path_history': path_history
                })
        else:
            stats.avg_fee += get_path_fee(raw, path, fee_strategy, transfer_value)
            if execute_transfers:
                raw.do_transfer(path, transfer_value)
            stats.avg_transfer_hops += len(path)
            stats.avg_contacted += len({node for subpath in path_history for node in subpath})

    toc = time.time()
    num_success = num_transfers - len(stats.failed)
    stats.num_transfers = num_transfers
    stats.name = name
    stats.avg_fee /= num_success
    stats.avg_transfer_hops /= num_success
    stats.avg_contacted /= num_success
    print('Finished after {} seconds. {} transfers failed.'.format(toc - tic, len(stats.failed)))
    return stats


def get_path_fee(
        raw: RawNetwork, path: Path, fee_strategy: FeeStrategy, transfer_value: int
) -> float:
    fee = 0
    for i in range(len(path) - 1):
        u = path[i]
        v = path[i + 1]
        e = raw[u][v]
        fee += fee_strategy.get_fee(u, v, e, transfer_value)
    return fee


def plot_stats(
        pre_stats: NetworkStats,
        post_stats: NetworkStats,
        sim_stats: SimulationStats,
        dirpath: str
):
    print('Plotting stats.')
    max_capacity = max(max(pre_stats.capacities), max(post_stats.capacities))
    max_net_balance = max(max(pre_stats.net_balances), max(post_stats.net_balances))
    max_imbalance = max(max(pre_stats.imbalances), max(post_stats.imbalances))
    max_num_channels = max(pre_stats.channel_counts)
    max_distance = max(pre_stats.channel_distances)

    # Plots.
    fig, axs = plt.subplots(3, 4)
    fig.set_size_inches(18, 10)

    styling = {
        'align': 'left',
        'edgecolor': 'black'
    }
    axs[0][0].hist(
        pre_stats.capacities, bins=range(max_capacity + 2), range=[0, max_capacity], **styling
    )
    axs[1][0].hist(
        post_stats.capacities, bins=range(max_capacity + 2), range=[0, max_capacity], **styling
    )
    axs[0][1].hist(
        pre_stats.net_balances, bins=range(max_net_balance + 2), range=[0, max_net_balance],
        **styling
    )
    axs[1][1].hist(
        post_stats.net_balances, bins=range(max_net_balance + 2), range=[0, max_net_balance],
        **styling
    )
    axs[0][2].hist(
        pre_stats.imbalances, bins=range(max_imbalance + 2), range=[0, max_imbalance], **styling
    )
    axs[1][2].hist(
        post_stats.imbalances, bins=range(max_imbalance + 2), range=[0, max_imbalance], **styling
    )
    axs[0][3].hist(
        pre_stats.channel_counts, bins=range(max_num_channels + 2), **styling
    )
    axs[2][0].hist(
        sim_stats.failed, bins=80, range=[0, sim_stats.num_transfers], edgecolor='black'
    )
    freq, _, _ = axs[2][1].hist(
        pre_stats.channel_distances, bins=range(max_distance + 2), **styling
    )

    # Stats plot (labels only).
    labels = [
        'Simulation name: {}'.format(sim_stats.name),
        'Top row: initial network state',
        'Bottom row: after {} transfers'.format(sim_stats.num_transfers),
        '',
        'Nodes: {}'.format(pre_stats.num_nodes),
        'Channels (unidirectional): {}'.format(pre_stats.num_channels_uni),
        'Required channels/node: {}'.format(pre_stats.num_required_channels),
        'Transfers: {}'.format(sim_stats.num_transfers),
        '',
        'Failed transfers: {}'.format(len(sim_stats.failed)),
        'Average transfer hops: {:.2f}'.format(sim_stats.avg_transfer_hops),
        'Average nodes contacted: {:.2f}'.format(sim_stats.avg_contacted),
        'Average fee: {:.2f}'.format(sim_stats.avg_fee),
        'Balance SD before: {:.2f}'.format(pre_stats.net_balance_stdev),
        'Balance SD after: {:.2f}'.format(post_stats.net_balance_stdev),
        'Imbalance SD before: {:.2f}'.format(pre_stats.imbalance_stdev),
        'Imbalance SD after: {:.2f}'.format(post_stats.imbalance_stdev),
        'Depleted channels: {}'.format(post_stats.num_depleted_channels)
    ]
    for i, label in enumerate(labels):
        axs[1][3].text(0, 0.95 - i * 0.07, label)

    formatter = mtick.EngFormatter()

    axs[0][0].set_ylabel('Distribution')
    axs[1][0].set_ylabel('Distribution')

    axs[1][0].set_xlabel('Channel capacity')
    axs[0][0].xaxis.set_ticks(range(0, max_capacity + 1, 2))
    axs[0][0].xaxis.set_ticks(range(1, max_capacity + 1, 2), minor=True)
    axs[1][0].xaxis.set_ticks(range(0, max_capacity + 1, 2))
    axs[1][0].xaxis.set_ticks(range(1, max_capacity + 1, 2), minor=True)
    axs[0][0].yaxis.set_major_formatter(formatter)
    axs[1][0].yaxis.set_major_formatter(formatter)

    axs[1][1].set_xlabel('Channel net balance (abs)')
    axs[0][1].xaxis.set_ticks(range(0, max_net_balance + 1, 2))
    axs[0][1].xaxis.set_ticks(range(1, max_net_balance + 1, 2), minor=True)
    axs[1][1].xaxis.set_ticks(range(0, max_net_balance + 1, 2))
    axs[1][1].xaxis.set_ticks(range(1, max_net_balance + 1, 2), minor=True)
    axs[0][1].yaxis.set_major_formatter(formatter)
    axs[1][1].yaxis.set_major_formatter(formatter)

    axs[1][2].set_xlabel('Channel imbalance')
    axs[0][2].xaxis.set_ticks(range(0, max_imbalance + 1, 2))
    axs[0][2].xaxis.set_ticks(range(1, max_imbalance + 1, 2), minor=True)
    axs[1][2].xaxis.set_ticks(range(0, max_imbalance + 1, 2))
    axs[1][2].xaxis.set_ticks(range(1, max_imbalance + 1, 2), minor=True)
    axs[0][2].yaxis.set_major_formatter(formatter)
    axs[1][2].yaxis.set_major_formatter(formatter)

    axs[0][3].set_xlabel('Channel count per node')
    axs[0][3].xaxis.set_ticks(range(0, max_num_channels + 1, 2))
    axs[0][3].xaxis.set_ticks(range(1, max_num_channels + 1, 2), minor=True)
    axs[0][3].yaxis.set_major_formatter(formatter)

    axs[2][0].set_xlabel('Transfer #')
    axs[2][0].set_ylabel('Failed transfers')
    axs[2][0].yaxis.set_major_formatter(formatter)

    axs[2][1].set_xlabel('Channel distances > 1')
    axs[2][1].xaxis.set_ticks(range(0, max_distance + 1, 5))
    axs[2][1].xaxis.set_ticks(range(0, max_distance + 1, 1), minor=True)
    axs[2][1].yaxis.set_major_formatter(formatter)

    axs[1][3].axis('off')
    axs[2][2].axis('off')
    axs[2][3].axis('off')

    fig.savefig(os.path.join(dirpath, 'stats'), bbox_inches='tight')


def plot_depleted_channels(net: Network, transfer_value: int, dirpath: str):
    print('Rendering depleted channels.')
    channels = [(u, v) for (u, v), e in net.raw.edges.items() if e['capacity'] < transfer_value]
    net.draw(
        channels=channels, filepath=os.path.join(dirpath, 'depleted_channels'), channel_color='r'
    )


def plot_transfer_failures(
        net: Network, failure_recordings: List[Dict[str, Union[Node, List[Path]]]], dirpath: str
):
    if failure_recordings:
        print('Rendering transfer failures.')
    for i, fail_history in enumerate(failure_recordings):
        source = fail_history['source']
        target = fail_history['target']
        dirpath = os.path.join(dirpath, 'fail_{}_{}'.format(source.uid, target.uid))
        net.draw_gif(source, target, fail_history['path_history'], 100, dirpath)
        dirpath = os.path.dirname(dirpath)
