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
from raidensim.strategy.position_strategy import PositionStrategy
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
    avg_fee_per_distance = 0

    def __init__(self):
        self.transfer_hops = []
        self.failed = []
        self.failure_recordings = []
        self.fees = []
        self.fees_per_distance = []


def simulate_scaling(
        net: Network,
        out_dir: str,
        num_transfers: int,
        transfer_value: int,
        fee_strategy: FeeStrategy,
        position_strategy: PositionStrategy,
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
        position_strategy,
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
        position_strategy: PositionStrategy,
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

    def channel_filter(u: Node, v: Node, e: dict) -> bool:
        return position_strategy.distance(u, v) == 1

    stats = SimulationStats()
    tic = time.time()
    subtic = tic
    for i in range(num_transfers):
        toc = time.time()
        if toc - subtic > 5:
            # Progress report every 5 seconds.
            subtic = toc
            print('Transfer {}/{}'.format(i + 1, num_transfers))

        source, target = raw.get_available_nodes(transfer_value, channel_filter)

        path, path_history = routing_strategy.route(raw, source, target, transfer_value)
        if path:
            fee = get_path_fee(raw, path, fee_strategy, transfer_value)
            stats.avg_fee += fee
            stats.fees.append((i, fee))

            distance = position_strategy.distance(source, target)
            fee_per_distance = fee / distance
            stats.avg_fee_per_distance += fee_per_distance
            stats.fees_per_distance.append((distance, fee))
            if execute_transfers:
                raw.do_transfer(path, transfer_value)

            stats.transfer_hops.append(len(path))
            stats.avg_transfer_hops += len(path)
            stats.avg_contacted += len({node for subpath in path_history for node in subpath})
        else:
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

    toc = time.time()
    num_success = num_transfers - len(stats.failed)
    stats.num_transfers = num_transfers
    stats.name = name
    stats.avg_fee /= num_success
    stats.avg_fee_per_distance /= num_success
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
    max_transfer_hops = max(sim_stats.transfer_hops)

    # Plots.
    fig, axs = plt.subplots(3, 5)
    fig.set_size_inches(22, 10)

    styling = {
        'align': 'left',
        'edgecolor': 'black'
    }

    def add_labels(ax, labels: List[str], align='right'):
        x = 0.97 if align == 'right' else 0.03
        for line, label in enumerate(labels):
            ax.text(
                x, 0.93 - line * 0.07, label, transform=ax.transAxes, horizontalalignment=align
            )

    formatter = mtick.EngFormatter()

    ax = axs[0][0]
    ax.set_title('Channel capacity before')
    ax.hist(
        pre_stats.capacities, bins=range(max_capacity + 2), range=[0, max_capacity], **styling
    )
    add_labels(ax, ['Depleted: {}'.format(pre_stats.num_depleted_channels)])
    ax.yaxis.set_major_formatter(formatter)
    ax.xaxis.set_ticks(range(0, max_capacity + 1, 5))
    ax.xaxis.set_ticks(range(0, max_capacity + 1, 1), minor=True)

    ax = axs[1][0]
    ax.set_title('Channel capacity after')
    ax.hist(
        post_stats.capacities, bins=range(max_capacity + 2), range=[0, max_capacity], **styling
    )
    add_labels(ax, ['Depleted: {}'.format(post_stats.num_depleted_channels)])
    ax.xaxis.set_ticks(range(0, max_capacity + 1, 5))
    ax.xaxis.set_ticks(range(0, max_capacity + 1, 1), minor=True)
    ax.yaxis.set_major_formatter(formatter)

    ax = axs[0][1]
    ax.set_title('Abs. channel net balance before')
    ax.hist(
        pre_stats.net_balances, bins=range(max_net_balance + 2), range=[0, max_net_balance],
        **styling
    )
    add_labels(ax, ['SD: {:.2f}'.format(pre_stats.net_balance_stdev)])
    ax.xaxis.set_ticks(range(0, max_net_balance + 1, 5))
    ax.xaxis.set_ticks(range(0, max_net_balance + 1, 1), minor=True)
    ax.yaxis.set_major_formatter(formatter)

    ax = axs[1][1]
    ax.set_title('Abs. channel net balance after')
    ax.hist(
        post_stats.net_balances, bins=range(max_net_balance + 2), range=[0, max_net_balance],
        **styling
    )
    add_labels(ax, ['SD: {:.2f}'.format(post_stats.net_balance_stdev)])
    ax.xaxis.set_ticks(range(0, max_net_balance + 1, 5))
    ax.xaxis.set_ticks(range(0, max_net_balance + 1, 1), minor=True)
    ax.yaxis.set_major_formatter(formatter)

    ax = axs[0][2]
    ax.set_title('Channel imbalance before')
    ax.hist(
        pre_stats.imbalances, bins=range(max_imbalance + 2), range=[0, max_imbalance], **styling
    )
    add_labels(ax, ['SD: {:.2f}'.format(pre_stats.imbalance_stdev)])
    ax.xaxis.set_ticks(range(0, max_imbalance + 1, 5))
    ax.xaxis.set_ticks(range(0, max_imbalance + 1, 1), minor=True)
    ax.yaxis.set_major_formatter(formatter)

    ax = axs[1][2]
    ax.set_title('Channel imbalance after')
    ax.hist(
        post_stats.imbalances, bins=range(max_imbalance + 2), range=[0, max_imbalance], **styling
    )
    add_labels(ax, ['SD: {:.2f}'.format(post_stats.imbalance_stdev)])
    ax.xaxis.set_ticks(range(0, max_imbalance + 1, 5))
    ax.xaxis.set_ticks(range(0, max_imbalance + 1, 1), minor=True)
    ax.yaxis.set_major_formatter(formatter)

    ax = axs[0][3]
    ax.set_title('Channel count per node')
    ax.hist(
        pre_stats.channel_counts, bins=range(max_num_channels + 2), **styling
    )
    ax.xaxis.set_ticks(range(0, max_num_channels + 1, 2))
    ax.xaxis.set_ticks(range(0, max_num_channels + 1, 1), minor=True)
    ax.yaxis.set_major_formatter(formatter)

    ax = axs[0][4]
    ax.set_title('Channel distances > 1')
    freq, _, _ = ax.hist(
        pre_stats.channel_distances, bins=range(max_distance + 2), **styling
    )
    ax.xaxis.set_ticks(range(0, max_distance + 1, 10))
    ax.xaxis.set_ticks(range(0, max_distance + 1, 1), minor=True)
    ax.yaxis.set_major_formatter(formatter)

    ax = axs[1][3]
    ax.set_title('Failed transfers over time')
    ax.hist(
        sim_stats.failed, bins=80, range=[0, sim_stats.num_transfers], edgecolor='black'
    )
    add_labels(ax, ['Total: {}'.format(len(sim_stats.failed))])
    ax.yaxis.set_major_formatter(formatter)

    ax = axs[2][0]
    ax.set_title('Fees over time')
    transfer_ids, fees = zip(*sim_stats.fees)
    bin_scale = sim_stats.num_transfers / 80
    fees = [fee / bin_scale for fee in fees]
    ax.hist(transfer_ids, bins=80, weights=fees, **styling)
    add_labels(ax, ['Mean: {:.2f}'.format(sim_stats.avg_fee)])
    ax.yaxis.set_major_formatter(formatter)

    ax = axs[2][1]
    ax.set_title('Fee per distance')
    distances, fees = zip(*sim_stats.fees_per_distance)
    ax.scatter(distances, fees, s=1, marker='+')
    add_labels(ax, ['Mean fee per distance: {:.2f}'.format(sim_stats.avg_fee_per_distance)])
    ax.yaxis.set_major_formatter(formatter)

    ax = axs[2][2]
    ax.set_title('Hops per transfer')
    ax.hist(
        sim_stats.transfer_hops, bins=range(max_transfer_hops + 2), range=[0, max_transfer_hops],
        **styling
    )
    add_labels(ax, ['Mean: {:.2f}'.format(sim_stats.avg_transfer_hops)])
    ax.xaxis.set_ticks(range(0, max_transfer_hops + 1, 5))
    ax.xaxis.set_ticks(range(0, max_transfer_hops + 1, 1), minor=True)
    ax.yaxis.set_major_formatter(formatter)

    # Stats plot (labels only).
    ax = axs[1][4]
    labels = [
        'Simulation name: {}'.format(sim_stats.name),
        '',
        'Nodes: {}'.format(pre_stats.num_nodes),
        'Channels (unidirectional): {}'.format(pre_stats.num_channels_uni),
        'Required channels/node: {}'.format(pre_stats.num_required_channels),
        'Transfers: {}'.format(sim_stats.num_transfers),
        '',
        'Average nodes contacted: {:.2f}'.format(sim_stats.avg_contacted)
    ]
    for line, label in enumerate(labels):
        ax.text(0, 0.95 - line * 0.07, label)

    axs[1][4].axis('off')
    axs[2][3].axis('off')
    axs[2][4].axis('off')

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
