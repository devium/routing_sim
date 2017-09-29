import random
from typing import List

import imageio
import shutil

import os

from raidensim.routing.routing_model import RoutingModel
from raidensim.strategy.filter_strategies import KademliaFilterStrategy
from raidensim.tools import draw2d
from raidensim.network.channel_network import ChannelNetwork
from raidensim.network.config import NetworkConfiguration


def simulate_routing(
        config: NetworkConfiguration,
        out_dir: str,
        num_sample_nodes: int,
        num_paths: int,
        value: int,
        routing_models: List[RoutingModel],
        max_gif_frames=20
):
    # Setup network.
    config.fullness_dist.reset()
    random.seed(0)
    cn = ChannelNetwork(config)

    # Prepare folder.
    dirpath = os.path.join(out_dir, 'routing_{}'.format(config.num_nodes))
    shutil.rmtree(dirpath, ignore_errors=True)
    os.makedirs(dirpath, exist_ok=True)

    # Plot baseline network.
    print('Plotting network.')
    draw2d(cn, filepath=os.path.join(dirpath, 'network'))
    draw2d(cn, draw_labels=True, filepath=os.path.join(dirpath, 'network_labels'))

    # Plot connectivity of a few random sample nodes.
    if num_sample_nodes > 0:
        print('Plotting sample node connectivity.')

    try:
        kademlia_filter = next(
            filter_ for filter_ in config.network_strategy.selection_strategy.filter_strategies
            if isinstance(filter_, KademliaFilterStrategy)
        )
    except StopIteration:
        kademlia_filter = None

    for i, node in enumerate(random.sample(cn.nodes, num_sample_nodes)):
        channels = [[node, partner] for partner in node.partners]
        if kademlia_filter:
            draw2d(
                cn,
                channels,
                kademlia_center=node.uid,
                kademlia_buckets=kademlia_filter.buckets,
                filepath=os.path.join(dirpath, 'node_{}'.format(i))
            )
        else:
            draw2d(cn, channels, filepath=os.path.join(dirpath, 'node_{}'.format(i)))

    # Perform routing.
    # cn.nodes order is non-deterministic. Sort for reproducible sampling.
    nodes_sorted = sorted(cn.nodes, key=lambda node: node.uid)
    for ip in range(num_paths):
        print('Path #{}'.format(ip))
        dirpath = os.path.join(dirpath, 'nodes_{}'.format(ip))
        os.makedirs(dirpath, exist_ok=True)
        source, target = random.sample(nodes_sorted, 2)
        draw2d(
            cn, highlighted_nodes=[[], [source, target]], filepath=os.path.join(dirpath, 'nodes')
        )

        for ir, routing_model in enumerate(routing_models):
            routing_name = '{}_{}'.format(ir, routing_model.__class__.__name__)

            print(routing_name)
            path, path_history = routing_model.route(source, target, value)

            dirpath = os.path.join(dirpath, routing_name)
            os.makedirs(dirpath, exist_ok=True)
            if path:
                print('Found path of length {}: {}'.format(len(path), path))
                filename = 'path.png'
                draw2d(
                    cn, [path], [path, [source, target]], filepath=os.path.join(dirpath, filename)
                )
            else:
                print('No path found.')

            if path_history:
                # Plot path evolution.
                gif_filenames = []
                visited = {source}
                num_wrong_turns = 0
                for isp in range(len(path_history) - 1):
                    prev = path_history[isp]
                    curr = path_history[isp + 1]
                    if prev != curr[:-1]:
                        num_wrong_turns += 1
                    visited |= set(prev)

                print('Took {} wrong turn(s).'.format(num_wrong_turns))
                print('Contacted {} distinct nodes in the process: {}'.format(
                    len(visited), visited)
                )

                visited = {source}
                for isp, subpath in enumerate(path_history):
                    visited |= set(subpath)
                    if isp > max_gif_frames - 1:
                        break
                    filename = 'step_{:04d}.png'.format(isp)
                    gif_filenames.append(filename)
                    draw2d(
                        cn, [subpath], [visited, [source, target]],
                        filepath=os.path.join(dirpath, filename)
                    )

                filename = 'animation.gif'
                with imageio.get_writer(
                        os.path.join(dirpath, filename), mode='I', fps=3
                ) as writer:
                    for filename in gif_filenames:
                        image = imageio.imread(os.path.join(dirpath, filename))
                        writer.append_data(image)

            dirpath = os.path.dirname(dirpath)
        dirpath = os.path.dirname(dirpath)