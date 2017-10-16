import random
from typing import List, Tuple

import shutil

import os

import math

from raidensim.network.network import Network
from raidensim.network.node import Node
from raidensim.strategy.routing.routing_strategy import RoutingStrategy


def simulate_routing(
        net: Network,
        out_dir: str,
        num_sample_nodes: int,
        num_paths: int,
        transfer_value: int,
        routing_strategies: List[Tuple[str, RoutingStrategy]],
        max_gif_frames=20
):
    # Prepare folder.
    dirpath = os.path.join(out_dir, 'routing_{}'.format(net.config.num_nodes))
    shutil.rmtree(dirpath, ignore_errors=True)
    os.makedirs(dirpath, exist_ok=True)

    plot_network(net, dirpath)
    plot_sample_nodes(net, num_sample_nodes, dirpath)
    plot_sample_routes(net, num_paths, routing_strategies, transfer_value, max_gif_frames, dirpath)


def plot_network(net: Network, dirpath: str):
    """
    Plot baseline network.
    """
    print('Plotting network.')
    net.draw(filepath=os.path.join(dirpath, 'network'))
    if len(net.raw.nodes) < 1000:
        net.draw(draw_labels=True, filepath=os.path.join(dirpath, 'network_labels'))


def plot_sample_nodes(net: Network, num_nodes: int, dirpath: str):
    """
    Plot connectivity of a few random sample nodes.
    """
    if num_nodes < 1:
        return

    print('Plotting sample node connectivity of {} random nodes.'.format(num_nodes))

    for i, node in enumerate(random.sample(net.raw.nodes, num_nodes)):
        channels = [(node, partner) for partner in net.raw[node]]

        def node_color(color_node: Node):
            distance = net.config.position_strategy.distance(node, color_node)
            return 1 + int(math.log2(distance)) if distance > 0 else 0

        net.draw(
            channels=channels,
            node_color=node_color,
            channel_color='r',
            filepath=os.path.join(dirpath, 'node_{}'.format(i))
        )


def plot_sample_routes(
        net: Network,
        num_paths: int,
        routing_strategies: List[Tuple[str, RoutingStrategy]],
        transfer_value: int,
        max_gif_frames: int,
        dirpath: str
):
    def channel_filter(u: Node, v: Node, e: dict) -> bool:
        return net.config.position_strategy.distance(u, v) == 1

    for ip in range(num_paths):
        print('Path #{}'.format(ip))
        dirpath = os.path.join(dirpath, 'nodes_{}'.format(ip))
        os.makedirs(dirpath, exist_ok=True)

        source, target = net.raw.get_available_nodes(transfer_value, channel_filter)
        net.draw(highlighted_nodes=[[], [source, target]], filepath=os.path.join(dirpath, 'nodes'))

        for ir, routing_strategy in enumerate(routing_strategies):
            print(routing_strategy[0])
            path, path_history = routing_strategy[1].route(net.raw, source, target, transfer_value)

            dirpath = os.path.join(dirpath, routing_strategy[0])
            os.makedirs(dirpath, exist_ok=True)
            if path:
                print('Found path of length {}: {}'.format(len(path), path))
                filename = 'path.png'
                net.draw(
                    paths=[path],
                    highlighted_nodes=[path, [source, target]],
                    filepath=os.path.join(dirpath, filename)
                )
            else:
                print('No path found.')

            if path_history:
                print('Rendering path evolution.')
                net.draw_gif(source, target, path_history, max_gif_frames, dirpath)

            dirpath = os.path.dirname(dirpath)
        dirpath = os.path.dirname(dirpath)
