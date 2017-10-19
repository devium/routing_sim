import time
import json
import os
import random
from collections import namedtuple
from typing import List

import math

from raidensim.network.network import Network
from raidensim.network.node import Node
from raidensim.strategy.creation.join_strategy import MicroRaidenJoinStrategy
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

        self.popup_curve = None
        self.transfer_curve = None
        self.net = None
        self.channels = []
        self.node_to_index = dict()
        self.channel_to_index = dict()
        self.hidden_nodes = set()
        self.hidden_channels = set()
        self.edges = {}
        self.visible_nodes = set()
        self.visible_channels = set()
        self.animations = []
        self.transfer_id = 0
        self.t = 0.0

        try:
            os.makedirs(self.config.out_dir)
        except OSError:
            pass
        print('Creating animation for {} nodes.'.format(self.config.network.num_nodes))
        self.get_frequency_curves()
        self.generate_network()
        self.reset_network()
        self.generate_animation()

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

        if self.config.popup_channels:
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
                    if self.config.popup_channels
                    else popup_curve_points,
                    'transfer': self.transfer_curve.points
                },
                curves_file
            )

    def generate_network(self):
        # Export final network configuration.
        random.seed(0)

        self.net = Network(self.config.network)
        self.node_to_index = {node: index for index, node in enumerate(self.net.raw.nodes)}

        node_pos = self.calc3d_positions()
        self.channels = list(frozenset({u, v}) for u, v, e in self.net.raw.bi_edges)
        self.channel_to_index = {frozenset(c): i for i, c in enumerate(self.channels)}
        channels_indexed = [
            (self.node_to_index[a], self.node_to_index[b]) for a, b in self.channels
        ]

        with open(os.path.join(self.config.out_dir, 'network.json'), 'w') as network_file:
            json.dump({
                'nodes': node_pos,
                'channels': channels_indexed
            }, network_file, indent=2)

    def calc3d_positions(self):
        """"
        Helper to position nodes in 3d.
        Nodes are again distributed on rings, their address determining the position on that ring.
        The fuller nodes are (more channels, higher deposits) the higher these nodes are positioned.
        The dist_pdf is expected to be the fullness probability-density function so that nodes are
        evenly distributed on a surface that corresponds to their fullness distribution.
        """
        positions = []
        max_fullness = max(n.fullness for n in self.net.raw.nodes)
        min_fullness = min(n.fullness for n in self.net.raw.nodes)
        dist_pdf = self.config.network.fullness_dist.get_pdf()
        pdf_scale = 1.0 / max(
            dist_pdf([n.fullness for n in self.net.raw.nodes])
        )
        range_ = float(max_fullness - min_fullness)

        for node in self.net.raw.nodes:
            # Put x,y on circle of radius 1.
            rad = 2 * math.pi * node.uid / self.net.config.max_id
            x, y = math.sin(rad), math.cos(rad)

            # Height above ground (light client =~0, full node up to 1).
            h = (node.fullness - min_fullness) / range_

            # Adjust radius to evenly distribute nodes on the 3D surface.
            r = dist_pdf(h) * pdf_scale
            # Make hole at top by moving higher nodes out a bit (min radius = hole_radius).
            r = (1 - self.config.top_hole_radius) * r + self.config.top_hole_radius
            x *= r
            y *= r
            positions.append([x, y, h])

        return positions

    def reset_network(self):
        # Revert simulation back to an edgeless network. Build animations from there.
        if self.config.popup_channels:
            self.hidden_nodes = set(self.net.raw.nodes)
            self.hidden_channels = self.channels.copy()
            self.edges = dict(self.net.raw.edges)
            self.net.raw.remove_edges_from(list(self.net.raw.edges))
        else:
            self.visible_nodes = set(self.net.raw.nodes)
            self.visible_channels = self.channels.copy()

    def generate_animation(self):
        # Generate node popup and channel transfer animations.
        print('Generating animation.')
        last_popup = 0.0
        last_transfer = 0.0
        tic = time.time()
        while self.t < self.config.animation_length:
            toc = time.time()
            if toc - tic > 5:
                tic = toc
                print('Animation progress: {:.2f}/{:.2f}'.format(
                    self.t, self.config.animation_length
                ))

            if self.config.popup_channels:
                channel_popup_freq = self.popup_curve.evaluate(self.t)
                channel_popup_delta = 1.0 / channel_popup_freq if channel_popup_freq else 1e12

                while self.hidden_channels and self.t - last_popup >= channel_popup_delta:
                    last_popup += channel_popup_delta
                    self.create_channels(1, connected_only=bool(self.animations))

            transfer_freq = self.transfer_curve.evaluate(self.t)
            transfer_delta = 1.0 / transfer_freq if transfer_freq else 1e12

            while len(self.visible_nodes) >= 2 and self.t - last_transfer >= transfer_delta:
                last_transfer += transfer_delta
                self.create_transfer()

            self.t += self.config.simulation_step_size

        print('Last channel popup at {}'.format(last_popup))

        with open(os.path.join(self.config.out_dir, 'animation.json'), 'w') as animation_file:
            content = {
                'channels_popup': self.config.popup_channels,
                'animations': self.animations
            }
            json.dump(content, animation_file, indent=2)

    def popup_channels(self, channels):
        """
        Creates a 'show' animation for the given channels and the associated nodes. Already visible
        nodes or channels are ignored.
        """
        for channel in channels:
            if channel in self.visible_channels:
                return []

            self.popup_nodes(channel)
            self.animations.append(self.Animation(
                time=self.t,
                animation_type='show',
                element_type='channel',
                element_id=self.channel_to_index[channel],
                transfer_id=-1
            ))
            self.hidden_channels.remove(channel)
            self.visible_channels.add(channel)

    def popup_nodes(self, nodes):
        """
        Creates 'show' animations for the given nodes at a certain frame. Only hidden nodes are
        considered.
        """
        nodes &= self.hidden_nodes

        for node in nodes:
            self.animations.append(self.Animation(
                time=self.t,
                animation_type='show',
                element_type='node',
                element_id=self.node_to_index[node],
                transfer_id=-1
            ))
            self.hidden_nodes.remove(node)
            self.visible_nodes.add(node)

    def create_channels(self, count, connected_only=True):
        """
        Creates both the animation and graph topology in the network simulation for new channels.
        """
        if connected_only:
            connected_hidden_channels = [
                channel for channel in self.hidden_channels if channel & self.visible_nodes
            ]

            count = min(count, len(connected_hidden_channels))
            new_channels = random.sample(connected_hidden_channels, count)
        else:
            count = min(count, len(self.hidden_channels))
            new_channels = random.sample(self.hidden_channels, count)

        self.popup_channels(new_channels)
        for a, b in new_channels:
            self.net.raw.add_edge(a, b, **self.edges[a, b])
            self.net.raw.add_edge(b, a, **self.edges[b, a])

    def create_transfer(self):
        for i in range(self.config.transfer_attempts_max):
            if isinstance(self.config.network.join_strategy, MicroRaidenJoinStrategy):
                channel = random.sample(self.visible_channels, 1)
                if channel:
                    self.flash_route(list(channel[0]))
                    self.transfer_id += 1
                    break
            else:
                source, target = random.sample(self.visible_nodes, 2)
                path, _ = self.config.routing_model.route(
                    self.net.raw, source, target, self.config.transfer_value
                )
                if path:
                    # Find channel for each hop.
                    self.flash_route(path)
                    self.transfer_id += 1
                    break

    def flash_nodes(self, nodes: List[Node], time_offset=0):
        """
        Creates a 'flash' animation for the given nodes.
        """
        for node in nodes:
            self.animations.append(self.Animation(
                time=self.t + time_offset,
                animation_type='flash',
                element_type='node',
                element_id=self.node_to_index[node],
                transfer_id=self.transfer_id
            ))

    def flash_route(self, route: List[Node]):
        """
        Creates a 'flash' animation for a given route.
        """
        time_offset = 0
        if route:
            self.flash_nodes([route[0]])
        for i in range(len(route) - 1):
            self.flash_nodes([route[i + 1]], time_offset)
            self.animations.append(self.Animation(
                time=self.t + time_offset,
                animation_type='flash',
                element_type='channel',
                element_id=self.channel_to_index[frozenset([route[i], route[i+1]])],
                transfer_id=self.transfer_id
            ))
            time_offset += self.config.transfer_hop_delay
