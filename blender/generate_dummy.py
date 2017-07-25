import json
import math
import numpy as np
import random
from collections import defaultdict, namedtuple

NUM_NODES = 10
NUM_CHANNELS = 30


def popup_node_with_channel(
        visible_nodes,
        hidden_nodes,
        node_to_unichannels
):
    # First attempt following channels of visible nodes at random.
    i = 0
    while i < 10:
        i += 1
        rand = random.randint(0, len(visible_nodes) - 1)
        rand_visible_node = visible_nodes[rand]
        for unichannel in node_to_unichannels[rand_visible_node]:
            if unichannel.partner in hidden_nodes:
                return unichannel.partner, unichannel.channel

    # Alternatively, attempt finding a channel from a hidden node to a visible one.
    i = 0
    while i < 10:
        i += 1
        rand = random.randint(0, len(hidden_nodes) - 1)
        rand_hidden_node = hidden_nodes[rand]
        for unichannel in node_to_unichannels[rand_hidden_node]:
            if unichannel.partner in visible_nodes:
                return rand_hidden_node, unichannel.channel

    print('No hidden node with connection to visible node found. Giving up.')

    return None, None


def popup_channel(visible_nodes, hidden_channels, channels):
    i = 0
    while i < 10:
        i += 1
        rand = random.randint(0, len(hidden_channels) - 1)
        rand_hidden_channel = hidden_channels[rand]
        channel = channels[rand_hidden_channel]
        if channel[0] in visible_nodes and channel[1] in visible_nodes:
            return rand_hidden_channel

    print('No hidden channel with connection between visible nodes found. Giving up.')

    return None


def flash_channel(visible_channels):
    return random.sample(visible_channels, 1)[0]


def generate_nodes():
    """
    Generate random coordinates on the surface of a sphere.
    """
    nodes = np.random.randn(3, NUM_NODES)
    nodes /= np.linalg.norm(nodes, axis=0)
    return list(nodes.transpose().tolist())


def generate_channels(num_nodes):
    """
    Generate random index pairs to connect nodes via channels.
    """
    channels = set()
    for i in range(NUM_CHANNELS):
        channels.add(frozenset(random.sample(range(num_nodes), 2)))

    return [tuple(channel) for channel in channels]


def generate_animations(num_nodes, channels):
    # Map nodes to their channels.
    Unichannel = namedtuple('UniChannel', ['channel', 'partner'])
    node_to_unichannels = defaultdict(list)
    for i, channel in enumerate(channels):
        node_to_unichannels[channel[0]].append(Unichannel(channel=i, partner=channel[1]))
        node_to_unichannels[channel[1]].append(Unichannel(channel=i, partner=channel[0]))

    Animation = namedtuple('Animation', [
        'start_frame',
        'animation_type',
        'element_type',
        'element_id'
    ])

    # Show nodes through random connections.
    animations = []
    visible_nodes = []
    hidden_nodes = list(range(num_nodes))
    visible_channels = []
    hidden_channels = list(range(len(channels)))
    popup_delay = 10

    first_node = random.randint(0, num_nodes - 1)
    first_animation = Animation(
        start_frame=0,
        animation_type='show',
        element_type='node',
        element_id=first_node
    )
    animations.append(first_animation)
    hidden_nodes.remove(first_node)
    visible_nodes.append(first_node)

    last_frame = 0
    while hidden_nodes or hidden_channels:
        # Find a node with a channel to a visible node.
        node = None
        channel = None
        type = None

        rand = random.randint(0, 2)
        if hidden_nodes and rand == 0:
            node, channel = popup_node_with_channel(
                visible_nodes,
                hidden_nodes,
                node_to_unichannels
            )
            type = 'show'
        elif rand == 1:
            channel = popup_channel(visible_nodes, hidden_channels, channels)
            type = 'show'
        elif visible_channels:
            channel = flash_channel(visible_channels)
            type = 'flash'

        # Create animation.
        if node is not None or channel is not None:
            popup_delay = int(math.ceil(0.95 * popup_delay))
            last_frame = last_frame + popup_delay
        if node is not None:
            node_animation = Animation(
                start_frame=last_frame,
                animation_type=type,
                element_type='node',
                element_id=node
            )
            animations.append(node_animation)
            if type == 'show':
                hidden_nodes.remove(node)
                visible_nodes.append(node)
        if channel is not None:
            channel_animation = Animation(
                start_frame=last_frame,
                animation_type=type,
                element_type='channel',
                element_id=channel
            )
            animations.append(channel_animation)
            if type == 'show':
                hidden_channels.remove(channel)
                visible_channels.append(channel)

    return animations


def run():
    nodes = generate_nodes()
    channels = generate_channels(len(nodes))

    # Write network topography to network file.
    with open('network.json', 'w') as network_file:
        json.dump({'nodes': nodes, 'channels': channels}, network_file, indent=2)

    animations = generate_animations(len(nodes), channels)

    with open('animation.json', 'w') as animation_file:
        json.dump(animations, animation_file, indent=2)


if __name__ == "__main__":
    run()
