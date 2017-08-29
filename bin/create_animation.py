import json
import random
import time
from collections import namedtuple

import os

from raidensim.config import NetworkConfiguration
from raidensim.curve_editor import CurveEditor
from raidensim.dist import BetaDistribution, CircleDistribution
from raidensim.network.channel_network import ChannelNetwork
from raidensim.draw import calc3d_positions

# Network topology parameters.
NUM_NODES = 1000
MIN_CHANNELS = 2
MAX_CHANNELS = 10
TOP_HOLE_RADIUS = 0.2
CHANNELS_POPUP = False

# Animation settings. Base unit = seconds.
ANIMATION_LENGTH = 30.0
TRANSFER_HOP_DELAY = 0.08
SIMULATION_STEP_SIZE = 0.01

POPUP_FREQ_MAX = 1000.0
TRANSFER_FREQ_MAX = 200.0

# Parameters for node fullness distribution (beta distribution). Applet:
# http://homepage.divms.uiowa.edu/~mbognar/applets/beta.html
FULLNESS_BETA_A = 1.1
FULLNESS_BETA_B = 5
# DISTRIBUTION = BetaDistribution(FULLNESS_BETA_A, FULLNESS_BETA_B)
DISTRIBUTION = CircleDistribution()

TRANSFER_ATTEMPTS_MAX = 10
TRANSFER_VALUE = 1

SCRIPT_DIR = os.path.dirname(__file__)
OUTDIR = os.path.abspath(os.path.join(SCRIPT_DIR, '../blender/data'))

Animation = namedtuple('Animation', [
    'time',
    'animation_type',
    'element_type',
    'element_id',
    'transfer_id'
])


class AnimationGenerator(object):
    def __init__(self):
        self.popup_curve = None
        self.transfer_curve = None
        self.cn = None
        self.channel_topology = []
        self.node_to_index = dict()
        self.hidden_nodes = set()
        self.hidden_channels = set()
        self.visible_nodes = set()
        self.visible_channels = set()
        self.animations = []
        self.transfer_id = 0
        self.time = 0.0

        try:
            os.makedirs(OUTDIR)
        except OSError:
            pass
        print('Creating animation for {} nodes.'.format(NUM_NODES))
        self.get_frequency_curves()
        self.generate_network()
        self.reset_network()
        self.generate_animation()

    def get_frequency_curves(self):
        curves_path = os.path.join(OUTDIR, 'curves.json')
        if os.path.exists(curves_path):
            with open(curves_path) as curves_file:
                curve_points = json.load(curves_file)
                popup_curve_points = curve_points['popup']
                transfer_curve_points = curve_points['transfer']
        else:
            popup_curve_points = []
            transfer_curve_points = []

        if CHANNELS_POPUP:
            self.popup_curve = CurveEditor(
                points=popup_curve_points,
                title='Channel Popup Frequency (max = {}).'.format(POPUP_FREQ_MAX),
                xmin=0, xmax=ANIMATION_LENGTH,
                ymin=0, ymax=POPUP_FREQ_MAX
            )

        self.transfer_curve = CurveEditor(
            points=transfer_curve_points,
            title='Transfer Frequency (max = {}).'.format(TRANSFER_FREQ_MAX),
            xmin=0, xmax=ANIMATION_LENGTH,
            ymin=0, ymax=TRANSFER_FREQ_MAX
        )

        with open(curves_path, 'w') as curves_file:
            json.dump(
                {
                    'popup': self.popup_curve.points if CHANNELS_POPUP else popup_curve_points,
                    'transfer': self.transfer_curve.points
                },
                curves_file
            )

    def generate_network(self):
        # Export final network configuration.
        random.seed(0)
        fullness_dist = DISTRIBUTION
        config = NetworkConfiguration(
            num_nodes=NUM_NODES,
            fullness_dist=fullness_dist,
            min_channels=MIN_CHANNELS,
            max_channels=MAX_CHANNELS,
            min_deposit=10,
            max_deposit=200
        )
        self.cn = ChannelNetwork()
        self.cn.generate_nodes(config)
        self.cn.connect_nodes()

        nodes, self.channel_topology = calc3d_positions(
            self.cn, TOP_HOLE_RADIUS, dist_pdf=fullness_dist.get_pdf()
        )
        self.channel_topology = [tuple(channel) for channel in self.channel_topology]

        with open(os.path.join(OUTDIR, 'network.json'), 'w') as network_file:
            json.dump({'nodes': nodes, 'channels': self.channel_topology}, network_file, indent=2)

    def reset_network(self):
        # Revert simulation back to empty network. Build animations from there.
        # Note: this only removes edges from the network graph and doesn't affect recursive
        # routing.
        self.node_to_index = {node: index for index, node in enumerate(self.cn.nodes)}
        if CHANNELS_POPUP:
            self.hidden_nodes = set(range(len(self.cn.nodes)))
            for i, channel in enumerate(self.channel_topology):
                del self.cn.nodes[channel[0]].channels[self.cn.nodeids[channel[1]]]
                del self.cn.nodes[channel[1]].channels[self.cn.nodeids[channel[0]]]
                if self.cn.nodes[channel[0]] in self.cn.G.edge:
                    self.cn.G.remove_edge(self.cn.nodes[channel[0]], self.cn.nodes[channel[1]])
                else:
                    self.cn.G.remove_edge(self.cn.nodes[channel[1]], self.cn.nodes[channel[0]])
                self.hidden_channels.add(i)
        else:
            self.visible_nodes = set(range(len(self.cn.nodes)))
            for i, channel in enumerate(self.channel_topology):
                self.visible_channels.add(i)


    def generate_animation(self):
        # Generate node popup and channel transfer animations.
        print('Generating animation.')
        last_popup = 0.0
        last_transfer = 0.0
        tic = time.time()
        while self.time < ANIMATION_LENGTH:
            toc = time.time()
            if toc - tic > 5:
                tic = toc
                print('Animation progress: {:.2f}/{:.2f}'.format(self.time, ANIMATION_LENGTH))

            if CHANNELS_POPUP:
                channel_popup_freq = self.popup_curve.evaluate(self.time)
                channel_popup_delta = 1.0 / channel_popup_freq if channel_popup_freq else 1e12

                while self.hidden_channels and self.time - last_popup >= channel_popup_delta:
                    last_popup += channel_popup_delta
                    self.create_channels(1, connected_only=bool(self.animations))

            transfer_freq = self.transfer_curve.evaluate(self.time)
            transfer_delta = 1.0 / transfer_freq if transfer_freq else 1e12

            while len(self.visible_nodes) >= 2 and self.time - last_transfer >= transfer_delta:
                last_transfer += transfer_delta
                self.create_transfer()

            self.time += SIMULATION_STEP_SIZE

        print('Last channel popup at {}'.format(last_popup))

        with open(os.path.join(OUTDIR, 'animation.json'), 'w') as animation_file:
            content = {
                'channels_popup': CHANNELS_POPUP,
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
                assert channel not in self.hidden_channels
                return []

            nodes = set(self.channel_topology[channel])
            self.popup_nodes(nodes)
            self.animations.append(Animation(
                time=self.time,
                animation_type='show',
                element_type='channel',
                element_id=channel,
                transfer_id=-1
            ))
            self.hidden_channels.remove(channel)
            self.visible_channels.add(channel)

    def popup_nodes(self, nodes):
        """
        Creates 'show' animations for the given nodes at a certain frame. Only hidden nodes are
        considered.
        """
        assert isinstance(nodes, set)
        nodes &= self.hidden_nodes
        assert not nodes & self.visible_nodes

        for node in nodes:
            self.animations.append(Animation(
                time=self.time,
                animation_type='show',
                element_type='node',
                element_id=node,
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
                channel for channel in self.hidden_channels
                if set(self.channel_topology[channel]) & self.visible_nodes
            ]

            count = min(count, len(connected_hidden_channels))
            new_channels = random.sample(connected_hidden_channels, count)
        else:
            count = min(count, len(self.hidden_channels))
            new_channels = random.sample(self.hidden_channels, count)

        self.popup_channels(new_channels)
        for channel in new_channels:
            node_a = self.cn.nodes[self.channel_topology[channel][0]]
            node_b = self.cn.nodes[self.channel_topology[channel][1]]
            self.cn.add_edge(node_a, node_b)
            node_a.setup_channel(node_b)
            node_b.setup_channel(node_a)

    def create_transfer(self):
        for i in range(TRANSFER_ATTEMPTS_MAX):
            source, target = random.sample(self.visible_nodes, 2)
            path = self.cn.find_path_global(
                self.cn.nodes[source],
                self.cn.nodes[target],
                TRANSFER_VALUE
            )
            if path:
                # Find channel for each hop.
                path_channels = []
                node_b_idx = self.node_to_index[path[0]]
                for j in range(len(path) - 1):
                    node_a_idx = node_b_idx
                    node_b_idx = self.node_to_index[path[j + 1]]
                    hop = {node_a_idx, node_b_idx}
                    hop_channels = [i for i in range(len(self.channel_topology)) if
                                    set(self.channel_topology[i]) == hop]
                    assert len(hop_channels) == 1
                    path_channels.append(hop_channels[0])

                self.flash_route(path_channels)
                self.transfer_id += 1
                break

    def flash_nodes(self, nodes, time_offset=0):
        """
        Creates a 'flash' animation for the given nodes.
        """
        for node in nodes:
            self.animations.append(Animation(
                time=self.time + time_offset,
                animation_type='flash',
                element_type='node',
                element_id=node,
                transfer_id=self.transfer_id
            ))

    def flash_route(self, channels):
        """
        Creates a 'flash' animation for a given route.
        """

        time_offset = 0
        flashed_nodes = set()
        for channel in channels:
            channel_nodes = set(self.channel_topology[channel])
            flashed_nodes = channel_nodes - flashed_nodes
            self.flash_nodes(flashed_nodes, time_offset)
            self.animations.append(Animation(
                time=self.time + time_offset,
                animation_type='flash',
                element_type='channel',
                element_id=channel,
                transfer_id=self.transfer_id
            ))
            time_offset += TRANSFER_HOP_DELAY


if __name__ == '__main__':
    AnimationGenerator()
