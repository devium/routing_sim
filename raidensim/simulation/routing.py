import random
from typing import List

import imageio
import shutil

import os

import math

from raidensim.network.network import Network
from raidensim.network.node import Node
from raidensim.strategy.creation.join_strategy import DefaultJoinStrategy
from raidensim.strategy.routing.routing_strategy import RoutingStrategy
from raidensim.strategy.creation.filter_strategy import KademliaFilterStrategy


def simulate_routing(
        net: Network,
        out_dir: str,
        num_sample_nodes: int,
        num_paths: int,
        value: int,
        routing_models: List[RoutingStrategy],
        max_gif_frames=20
):
    net.reset()

    # Prepare folder.
    dirpath = os.path.join(out_dir, 'routing_{}'.format(net.config.num_nodes))
    shutil.rmtree(dirpath, ignore_errors=True)
    os.makedirs(dirpath, exist_ok=True)

    # Plot baseline network.
    print('Plotting network.')
    net.draw(filepath=os.path.join(dirpath, 'network'))
    if len(net.raw.nodes) < 1000:
        net.draw(draw_labels=True, filepath=os.path.join(dirpath, 'network_labels'))

    # Plot connectivity of a few random sample nodes.
    if num_sample_nodes > 0:
        print('Plotting sample node connectivity.')

    try:
        if isinstance(net.config.join_strategy, DefaultJoinStrategy):
            kademlia_filter = next(
                filter_ for filter_ in net.config.join_strategy.selection_strategy.filter_strategies
                if isinstance(filter_, KademliaFilterStrategy)
            )
        else:
            kademlia_filter = None
    except StopIteration:
        kademlia_filter = None

    for i, node in enumerate(random.sample(net.raw.nodes, num_sample_nodes)):
        channels = [[node, partner] for partner in net.raw[node]]
        if kademlia_filter:
            net.draw(
                channels,
                kademlia_center=node.uid,
                kademlia_buckets=kademlia_filter.buckets,
                filepath=os.path.join(dirpath, 'node_{}'.format(i))
            )
        else:
            def node_color(color_node: Node):
                distance = net.config.position_strategy.distance(node, color_node)
                return int(math.log2(distance)) if distance > 0 else 0

            net.draw(
                channels,
                node_color_mapping=node_color,
                filepath=os.path.join(dirpath, 'node_{}'.format(i))
            )

    # Perform routing.
    # cn.nodes order is non-deterministic. Sort for reproducible sampling.
    nodes_sorted = sorted(net.raw.nodes, key=lambda node: node.uid)
    for ip in range(num_paths):
        print('Path #{}'.format(ip))
        dirpath = os.path.join(dirpath, 'nodes_{}'.format(ip))
        os.makedirs(dirpath, exist_ok=True)
        source, target = random.sample(nodes_sorted, 2)
        net.draw(highlighted_nodes=[[], [source, target]], filepath=os.path.join(dirpath, 'nodes'))

        for ir, routing_model in enumerate(routing_models):
            routing_name = '{}_{}'.format(ir, routing_model.__class__.__name__)

            print(routing_name)
            path, path_history = routing_model.route(net.raw, source, target, value)

            dirpath = os.path.join(dirpath, routing_name)
            os.makedirs(dirpath, exist_ok=True)
            if path:
                print('Found path of length {}: {}'.format(len(path), path))
                filename = 'path.png'
                net.draw(
                    [path], [path, [source, target]], filepath=os.path.join(dirpath, filename)
                )
            else:
                print('No path found.')

            if path_history:
                print('Rendering path evolution.')
                net.draw_gif(source, target, path_history, max_gif_frames, dirpath)

            dirpath = os.path.dirname(dirpath)
        dirpath = os.path.dirname(dirpath)