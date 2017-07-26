import json
import random
from collections import namedtuple

from routing_sim import ParetoNetworkConfiguration, ChannelNetwork
from utils import calc3d_positions

NUM_NODES = 100
ANIMATION_DELAY_INITIAL = 7.0
ANIMATION_DELAY_DECAY = 0.99
ANIMATION_DELAY_MIN = 3.0
ANIMATION_CHANNEL_HOP_DELAY = 1
TRANSFER_ATTEMPTS_MAX = 10
TRANSFER_DELAY = 10
TRANSFER_VALUE = 0.01
NUM_CHANNELS_PER_POPUP = 2

Animation = namedtuple('Animation', [
    'start_frame',
    'animation_type',
    'element_type',
    'element_id',
    'transfer_id'
])


class AnimationGenerator(object):
    def __init__(self):
        # Export final network configuration.
        config = ParetoNetworkConfiguration(NUM_NODES)
        self.cn = ChannelNetwork()
        self.cn.generate_nodes(config)
        self.cn.connect_nodes()

        nodes, self.channel_topology = calc3d_positions(self.cn)
        self.channel_topology = [tuple(channel) for channel in self.channel_topology]

        with open('blender/network.json', 'w') as network_file:
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
            self.cn.G.remove_edge(self.cn.nodes[channel[0]], self.cn.nodes[channel[1]])
            self.hidden_channels.add(i)

        random.seed(43)

        # Generate node popup and channel transfer animations.
        self.frame = 0
        self.animations = []
        self.create_channels(1, connected_only=False)

        animation_delay = ANIMATION_DELAY_INITIAL
        self.frame = animation_delay
        self.last_transfer = 0
        self.transfer_id = 0
        while self.hidden_channels:
            # Popup new channel that is connected to the existing network.
            self.create_channels(NUM_CHANNELS_PER_POPUP)

            if self.frame - self.last_transfer >= TRANSFER_DELAY:
                # Create new transfer.
                self.create_transfer()

            animation_delay *= ANIMATION_DELAY_DECAY
            animation_delay = max(animation_delay, ANIMATION_DELAY_MIN)
            self.frame += int(animation_delay)

        with open('blender/animation.json', 'w') as animation_file:
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
                start_frame=self.frame,
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
                start_frame=self.frame,
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

                self.flash_channels(path_channels)
                self.last_transfer = self.frame
                self.transfer_id += 1
                break

    def flash_channels(self, channels):
        """
        Creates a 'flash' animation for a given route.
        """

        frame_offset = 0
        for channel in channels:
            frame_offset += ANIMATION_CHANNEL_HOP_DELAY
            self.animations.append(Animation(
                start_frame=self.frame + frame_offset,
                animation_type='flash',
                element_type='channel',
                element_id=channel,
                transfer_id=self.transfer_id
            ))


if __name__ == '__main__':
    AnimationGenerator()
