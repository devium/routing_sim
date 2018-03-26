import time
import json
import os
import random
from collections import namedtuple
from typing import List, Dict, Tuple

from raidensim.network.network import Network
from raidensim.network.node import Node
from raidensim.tools.curve_editor import CurveEditor
from .config import AnimationConfiguration


class AnimationGenerator(object):
    Animation = namedtuple('Animation', [
        'time',
        'animation_type',
        'element_type',
        'element_id',
        'transfer_id'
    ])

    def __init__(self, config: AnimationConfiguration):
        self.config = config

        self.popup_curve: CurveEditor = None
        self.transfer_curve: CurveEditor = None
        self.net: Network = None
        self.node_to_index: Dict[Node, int] = {}
        self.channel_to_index: Dict[Tuple[Node, Node], int] = {}
        self.animations: List[self.Animation] = []
        self.transfer_id = 0
        self.t = 0.0

        try:
            os.makedirs(self.config.out_dir)
        except OSError:
            pass
        print('Creating animation for {} nodes.'.format(self.config.network.num_nodes))
        self.get_frequency_curves()
        self.generate_network()
        self.generate_animation()
        self.store_network()

    def get_frequency_curves(self):
        curves_path = os.path.join(self.config.out_dir, 'curves.json')
        if os.path.exists(curves_path):
            with open(curves_path) as curves_file:
                curve_points = json.load(curves_file)
                popup_curve_points = curve_points['popup']
                transfer_curve_points = curve_points['transfer']
        else:
            popup_curve_points = []
            transfer_curve_points = []

        if self.config.grow_network:
            self.popup_curve = CurveEditor(
                points=popup_curve_points,
                title='Channel Popup Frequency (max = {}).'.format(self.config.popup_freq_max),
                xmin=0, xmax=self.config.animation_length,
                ymin=0, ymax=self.config.popup_freq_max
            )

        self.transfer_curve = CurveEditor(
            points=transfer_curve_points,
            title='Transfer Frequency (max = {}).'.format(self.config.transfer_freq_max),
            xmin=0, xmax=self.config.animation_length,
            ymin=0, ymax=self.config.transfer_freq_max
        )

        with open(curves_path, 'w') as curves_file:
            json.dump(
                {
                    'popup': self.popup_curve.points
                    if self.config.grow_network
                    else popup_curve_points,
                    'transfer': self.transfer_curve.points
                },
                curves_file
            )

    def generate_network(self):
        # Export final network configuration.
        random.seed(0)
        self.net = Network(self.config.network, join_nodes=False)
        if not self.config.grow_network:
            self.net.join_nodes()

    def calc3d_positions(self) -> List[Tuple[int, int, int]]:
        """"
        Helper to position nodes in 3d.
        Nodes are positioned on a 2D plane according to the network's position strategy.
        """
        positions = []

        nodes_ordered = list(zip(*sorted(
            (index, node)
            for node, index in self.node_to_index.items()
        )))[1]
        for node in nodes_ordered:
            # Put x,y on circle of radius 1.
            x, y = self.config.network.position_strategy.map(node)

            # TODO: add some sensible displacement along the z axis.
            z = 0

            positions.append([x, y, z])

        return positions

    def generate_animation(self):
        # Generate node join and channel transfer animations.
        print('Generating animation.')
        last_join = 0.0
        last_transfer = 0.0
        tic = time.time()
        while self.t < self.config.animation_length:
            toc = time.time()
            if toc - tic > 5:
                tic = toc
                print('Animation progress: {:.2f}/{:.2f}'.format(
                    self.t, self.config.animation_length
                ))

            if self.config.grow_network:
                node_join_freq = self.popup_curve.evaluate(self.t)
                node_join_delta = 1.0 / node_join_freq if node_join_freq else 1e12

                while (
                        self.net.raw.number_of_nodes() < self.config.network.num_nodes and
                        self.t - last_join >= node_join_delta
                ):
                    last_join += node_join_delta
                    self.join_node()

            transfer_freq = self.transfer_curve.evaluate(self.t)
            transfer_delta = 1.0 / transfer_freq if transfer_freq else 1e12

            while (
                    self.net.raw.number_of_nodes() >= 2 and
                    self.t - last_transfer >= transfer_delta
            ):
                last_transfer += transfer_delta
                self.create_transfer()

            self.t += self.config.simulation_step_size

        print('Last node join at {}'.format(last_join))

        with open(os.path.join(self.config.out_dir, 'animation.json'), 'w') as animation_file:
            content = {
                'channels_popup': self.config.grow_network,
                'animations': self.animations
            }
            json.dump(content, animation_file, indent=2)

    def store_network(self):
        """
        Stores the final network topology for rendering.
        """
        node_pos = self.calc3d_positions()
        channels_ordered = list(zip(*sorted({
            (index, frozenset((self.node_to_index[u], self.node_to_index[v])))
            for (u, v), index in self.channel_to_index.items()
        })))[1]
        channels_ordered = [tuple(channel) for channel in channels_ordered]

        with open(os.path.join(self.config.out_dir, 'network.json'), 'w') as network_file:
            json.dump({
                'nodes': node_pos,
                'channels': channels_ordered
            }, network_file, indent=2)

    def popup_channels(self, channel_indices: List[int]):
        """
        Creates a 'show' animation for the given channels and the associated nodes. Already visible
        nodes or channels are ignored.
        """
        for channel_index in channel_indices:
            self.animations.append(self.Animation(
                time=self.t,
                animation_type='show',
                element_type='channel',
                element_id=channel_index,
                transfer_id=-1
            ))

    def popup_nodes(self, node_indices: List[int]):
        """
        Creates 'show' animations for the given nodes at a certain frame.
        """
        for node_index in node_indices:
            self.animations.append(self.Animation(
                time=self.t,
                animation_type='show',
                element_type='node',
                element_id=node_index,
                transfer_id=-1
            ))

    def join_node(self):
        """
        Joins a node to the network using the specified join strategy. A popup animation for its
        channels is automatically created.
        """
        node = self.net.join_single_node()
        node_index = len(self.node_to_index)
        self.node_to_index[node] = node_index

        popup_channel_indices: List[int] = []
        for partner in self.net.raw[node]:
            channel_index = len(self.channel_to_index) // 2
            self.channel_to_index[(node, partner)] = channel_index
            self.channel_to_index[(partner, node)] = channel_index
            popup_channel_indices.append(channel_index)

        self.popup_nodes([node_index])
        self.popup_channels(popup_channel_indices)

    def create_transfer(self):
        for i in range(self.config.transfer_attempts_max):
            source, target = random.sample(self.net.raw.nodes, 2)
            path, _ = self.config.routing_model.route(
                self.net.raw, source, target, self.config.transfer_value
            )
            if path:
                # Find channel for each hop.
                self.flash_path(path)
                self.transfer_id += 1
                break

    def flash_nodes(self, node_indices: List[int], time_offset=0):
        """
        Creates a 'flash' animation for the given nodes.
        """
        for node_index in node_indices:
            self.animations.append(self.Animation(
                time=self.t + time_offset,
                animation_type='flash',
                element_type='node',
                element_id=node_index,
                transfer_id=self.transfer_id
            ))

    def flash_path(self, path: List[Node]):
        """
        Creates a 'flash' animation for a given route.
        """
        time_offset = 0

        if path:
            self.flash_nodes([self.node_to_index[path[0]]])
        for i in range(len(path) - 1):
            self.flash_nodes([self.node_to_index[path[i + 1]]], time_offset)
            self.animations.append(self.Animation(
                time=self.t + time_offset,
                animation_type='flash',
                element_type='channel',
                element_id=self.channel_to_index[path[i], path[i+1]],
                transfer_id=self.transfer_id
            ))
            time_offset += self.config.transfer_hop_delay
