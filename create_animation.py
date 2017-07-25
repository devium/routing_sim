import json
from collections import namedtuple

from routing_sim import *
from utils import calc3d_positions

NUM_NODES = 100
ANIMATION_DELAY_INITIAL = 10
ANIMATION_DELAY_DECAY = 0.95
ANIMATION_DELAY_MIN = 3
ANIMATION_CHANNEL_HOP_DELAY = 1
TRANSFER_ATTEMPTS_MAX = 10
TRANSFER_DELAY = 20
TRANSFER_VALUE = 0.01

Animation = namedtuple('Animation', [
    'start_frame',
    'animation_type',
    'element_type',
    'element_id'
])


def popup_nodes(hidden_nodes, visible_nodes, start_frame, nodes):
    """
    Creates 'show' animations for the given nodes at a certain frame. Only hidden nodes are
    considered.
    """
    assert isinstance(nodes, set)
    nodes &= hidden_nodes
    assert not nodes & visible_nodes

    animations = []
    for node in nodes:
        animations.append(Animation(
            start_frame=start_frame,
            animation_type='show',
            element_type='node',
            element_id=node
        ))
        hidden_nodes.remove(node)
        visible_nodes.add(node)

    return animations


def popup_channel(
        hidden_nodes,
        visible_nodes,
        hidden_channels,
        visible_channels,
        start_frame,
        channel,
        channels
):
    """
    Creates a 'show' animation for the given channel and the associated nodes. Already visible
    nodes or channels are ignored.
    """
    if channel in visible_channels:
        assert channel not in hidden_channels
        return []

    nodes = set(channels[channel])
    animations = popup_nodes(hidden_nodes, visible_nodes, start_frame, nodes)
    animations.append(Animation(
        start_frame=start_frame,
        animation_type='show',
        element_type='channel',
        element_id=channel
    ))
    hidden_channels.remove(channel)
    visible_channels.add(channel)
    return animations


def flash_channels(channels, start_frame, delay=ANIMATION_CHANNEL_HOP_DELAY):
    """
    Creates a 'flash' animation for a given route.
    """

    frame_offset = 0
    animations = []
    for channel in channels:
        frame_offset += delay
        animations.append(Animation(
            start_frame=start_frame + frame_offset,
            animation_type='flash',
            element_type='channel',
            element_id=channel
        ))

    return animations


def run():
    # Export final network configuration.
    config = BaseNetworkConfiguration(NUM_NODES)
    cn = ChannelNetwork()
    cn.generate_nodes(config)
    cn.connect_nodes()
    nodes, channels = calc3d_positions(cn)
    channels = {frozenset(channel) for channel in channels}
    channels = [tuple(channel) for channel in channels]

    with open('blender/network.json', 'w') as network_file:
        json.dump({'nodes': nodes, 'channels': channels}, network_file, indent=2)

    # Revert simulation back to empty network. Build animations from there.
    # Note: this only removes edges from the network graph and doesn't affect recursive routing.

    node_to_index = {node: index for index, node in enumerate(cn.nodes)}
    hidden_nodes = set(range(len(nodes)))
    hidden_channels = set()
    visible_nodes = set()
    visible_channels = set()
    for i, channel in enumerate(channels):
        cn.G.remove_edge(cn.nodes[channel[0]], cn.nodes[channel[1]])
        hidden_channels.add(i)

    random.seed(43)

    # Generate node popup and channel transfer animations.
    animations = []
    channel = random.sample(hidden_channels, 1)[0]
    animations += popup_channel(
        hidden_nodes,
        visible_nodes,
        hidden_channels,
        visible_channels,
        0,
        channel,
        channels
    )
    node_a = cn.nodes[channels[channel][0]]
    node_b = cn.nodes[channels[channel][1]]
    cn.add_edge(node_a, node_b)
    node_a.setup_channel(node_b)
    node_b.setup_channel(node_a)

    animation_delay = ANIMATION_DELAY_INITIAL
    frame = animation_delay
    last_transfer = 0
    while hidden_channels:
        # Popup new channel that is connected to the existing network.
        connected_hidden_channels = [
            channel for channel in hidden_channels if set(channels[channel]) & visible_nodes
        ]
        channel = random.sample(connected_hidden_channels, 1)[0]
        animations += popup_channel(
            hidden_nodes,
            visible_nodes,
            hidden_channels,
            visible_channels,
            frame,
            channel,
            channels
        )
        node_a = cn.nodes[channels[channel][0]]
        node_b = cn.nodes[channels[channel][1]]
        cn.add_edge(node_a, node_b)
        node_a.setup_channel(node_b)
        node_b.setup_channel(node_a)

        if frame - last_transfer >= TRANSFER_DELAY:
            # Create new transfer.
            for i in range(TRANSFER_ATTEMPTS_MAX):
                source, target = random.sample(visible_nodes, 2)
                path = cn.find_path_global(cn.nodes[source], cn.nodes[target], TRANSFER_VALUE)
                if path:
                    # Find channel for each hop.
                    path_channels = []
                    node_b_idx = node_to_index[path[0]]
                    for j in range(len(path) - 1):
                        node_a_idx = node_b_idx
                        node_b_idx = node_to_index[path[j + 1]]
                        hop = {node_a_idx, node_b_idx}
                        hop_channels = [i for i in range(len(channels)) if set(channels[i]) == hop]
                        assert len(hop_channels) == 1
                        path_channels.append(hop_channels[0])

                    animations += flash_channels(path_channels, frame)
                    last_transfer = frame
                    break

        animation_delay *= ANIMATION_DELAY_DECAY
        animation_delay = int(max(animation_delay, ANIMATION_DELAY_MIN))
        frame += animation_delay

    with open('blender/animation.json', 'w') as animation_file:
        json.dump(animations, animation_file, indent=2)


if __name__ == '__main__':
    run()
