import json
import random
from collections import namedtuple

from raidensim.config import SemisphereNetworkConfiguration
from raidensim.network.channel_network import ChannelNetwork
from raidensim.draw import calc3d_positions

NUM_NODES = 200

# Base unit = seconds.
ANIMATION_LENGTH = 30.0
CHANNEL_POPUP_DELAY_BASE = 0.1
CHANNEL_POPUP_DELAY_DECAY = 0.94
CHANNEL_POPUP_DELAY_MIN = 0.01
TRANSFER_DELAY_BASE = 1.5
TRANSFER_DELAY_DECAY = 0.80
TRANSFER_DELAY_MIN = 0.005
TRANSFER_HOP_DELAY = 0.08
SIMULATION_STEP_SIZE = 0.01

TRANSFER_ATTEMPTS_MAX = 10
TRANSFER_VALUE = 1
TOP_HOLE_RADIUS = 0.2

OUTDIR = 'blender/'


Animation = namedtuple('Animation', [
    'time',
    'animation_type',
    'element_type',
    'element_id',
    'transfer_id'
])


class AnimationGenerator(object):
    def __init__(self):
        # Export final network configuration.
        config = SemisphereNetworkConfiguration(NUM_NODES, 10, 1000)
        self.cn = ChannelNetwork()
        self.cn.generate_nodes(config)
        self.cn.connect_nodes()

        nodes, self.channel_topology = calc3d_positions(self.cn, TOP_HOLE_RADIUS)
        self.channel_topology = [tuple(channel) for channel in self.channel_topology]

        with open(OUTDIR + 'network.json', 'w') as network_file:
            json.dump({'nodes': nodes, 'channels': self.channel_topology}, network_file, indent=2)

        # Revert simulation back to empty network. Build animations from there.
        # Note: this only removes edges from the network graph and doesn't affect recursive
        # routing.
        self.node_to_index = {node: index for index, node in enumerate(self.cn.nodes)}
        self.hidden_nodes = set(range(len(nodes)))
        self.hidden_channels = set()
        self.visible_nodes = set()
        self.visible_channels = set()
        for i, channel in enumerate(self.channel_topology):
            if self.cn.nodes[channel[0]] in self.cn.G.edge:
                self.cn.G.remove_edge(self.cn.nodes[channel[0]], self.cn.nodes[channel[1]])
            else:
                self.cn.G.remove_edge(self.cn.nodes[channel[1]], self.cn.nodes[channel[0]])
            self.hidden_channels.add(i)

        random.seed(43)

        # Generate node popup and channel transfer animations.
        self.animations = []
        self.transfer_id = 0
        self.time = 0.0
        last_speedup = 0.0
        last_popup = 0.0
        last_transfer = 0.0
        max_transfers_reached = None
        channel_popup_delay = CHANNEL_POPUP_DELAY_BASE
        transfer_delay = TRANSFER_DELAY_BASE
        while self.time < ANIMATION_LENGTH:
            if self.time - last_speedup > 1.0:
                last_speedup += 1.0
                channel_popup_delay *= CHANNEL_POPUP_DELAY_DECAY
                channel_popup_delay = max(channel_popup_delay, CHANNEL_POPUP_DELAY_MIN)
                transfer_delay *= TRANSFER_DELAY_DECAY
                transfer_delay = max(transfer_delay, TRANSFER_DELAY_MIN)
                if not max_transfers_reached and transfer_delay == TRANSFER_DELAY_MIN:
                    max_transfers_reached = self.time

            while self.hidden_channels and self.time - last_popup >= channel_popup_delay:
                last_popup += channel_popup_delay
                self.create_channels(1, connected_only=bool(self.animations))

            while len(self.visible_nodes) >= 2 and self.time - last_transfer >= transfer_delay:
                last_transfer += transfer_delay
                self.create_transfer()

            self.time += SIMULATION_STEP_SIZE

        print('Last channel popup at {}'.format(last_popup))
        print('Final channel popup delay: {}'.format(channel_popup_delay))
        print('Final transfer delay: {}'.format(transfer_delay))
        print('Max transfer frequency reached at {}'.format(max_transfers_reached))

        with open(OUTDIR + 'animation.json', 'w') as animation_file:
            json.dump(self.animations, animation_file, indent=2)

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

    def flash_node(self, node, time_offset=0):
        """
        Creates a 'flash' animation for the given node.
        """
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
        if channels:
            self.flash_node(self.channel_topology[channels[0]][0], time_offset)
        for channel in channels:
            time_offset += TRANSFER_HOP_DELAY
            self.flash_node(self.channel_topology[channel][1], time_offset)
            self.animations.append(Animation(
                time=self.time + time_offset,
                animation_type='flash',
                element_type='channel',
                element_id=channel,
                transfer_id=self.transfer_id
            ))


if __name__ == '__main__':
    AnimationGenerator()
