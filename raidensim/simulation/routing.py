import random

import imageio
import shutil

import os

from raidensim.tools import draw2d
from raidensim.network.channel_network import ChannelNetwork
from raidensim.network.config import NetworkConfiguration


def simulate_routing(config: NetworkConfiguration, out_dir, num_paths=10, value=2):
    config.fullness_dist.reset()
    random.seed(0)

    cn = ChannelNetwork(config)
    filename = 'routing_{}.png'.format(config.num_nodes)
    draw2d(cn, filepath=os.path.join(out_dir, filename))
    filename = 'routing_{}_labels.png'.format(config.num_nodes)
    draw2d(cn, draw_labels=True, filepath=os.path.join(out_dir, filename))

    for i in range(num_paths):
        dirpath = os.path.join(out_dir, 'routing_{}_{}'.format(config.num_nodes, i))
        shutil.rmtree(dirpath, ignore_errors=True)
        os.makedirs(dirpath, exist_ok=True)

        print("-" * 40)
        source, target = random.sample(cn.nodes, 2)

        # Global routing (Dijkstra).
        print('Global routing:')
        path = cn.find_path_global(source, target, value)
        if path:
            print('Found path of length {}: {}'.format(len(path), path))
        else:
            print('No path found.')
        filename = 'global.png'
        draw2d(cn, path, [path, [source, target]], filepath=os.path.join(dirpath, filename))

        # Priority-BFS routing.
        print('BFS routing:')
        _, path, path_history = source.find_path_bfs(target, value, priority_model='distance')
        if path:
            print('Found path of length {}: {}'.format(len(path), path))
        else:
            print('No path found.')
        visited = {source}
        gif_filenames = []
        for j, subpath in enumerate(path_history):
            visited |= set(subpath)
            filename = 'bfs_{}.png'.format(j)
            gif_filenames.append(filename)
            draw2d(
                cn, subpath, [visited, [source, target]], filepath=os.path.join(dirpath, filename)
            )
        print('Contacted {} nodes in the process: {}'.format(len(visited), visited))
        filename = 'bfs.png'
        gif_filenames.append(filename)
        draw2d(cn, path, [visited, [source, target]], filepath=os.path.join(dirpath, filename))

        filename = 'bfs_animation.gif'
        with imageio.get_writer(os.path.join(dirpath, filename), mode='I', fps=3) as writer:
            for filename in gif_filenames:
                image = imageio.imread(os.path.join(dirpath, filename))
                writer.append_data(image)

        # print('Path finding with helpers.')
        # path, helper = cn.find_path_with_helper(source, target, value)
        # if path:
        #     print(len(path), path)
        # else:
        #     print('No direct path to target sector.')
        # draw(cn, path, None, helper)
