import json
from collections import namedtuple, defaultdict

import bpy

from settings import *


def reset_progress():
    network_mats = [mat for mat in bpy.data.materials if 'Material.Network.' in mat.name]
    for mat in network_mats:
        curve_group = mat.node_tree.nodes['Group.Curve']
        curve_group.inputs[0].default_value = 1
        curve_group.inputs[1].default_value = 0


def animate(animation, progress):
    """
    Returns a tuple for the current mixer values (progress_hidden, progress_active).
    Tuple elements are -1 if unchanged.
    """
    if animation.animation_type == 'show':
        return 1 - progress, -1
    elif animation.animation_type == 'flash':
        return -1, progress
    elif animation.animation_type == 'hide':
        return progress, -1
    else:
        return -1, -1


def on_frame(
        scene,
        animations,
        animation_type_to_length,
        element_type_to_name,
        animate
):
    frame = scene.frame_current
    print('---- Frame {} ----'.format(frame))

    # Find all current animations.
    current_animations = [
        animation for animation in animations
        if animation.start_frame <= frame <=
        animation.start_frame + animation_type_to_length[animation.animation_type]
    ]

    for animation in current_animations:
        # Compute animation progress.
        animation_length = animation_type_to_length[animation.animation_type]
        animation_frame = frame - animation.start_frame
        animation_progress = animation_frame / animation_length

        print(
            animation.animation_type,
            animation.element_type,
            animation.element_id,
            animation_progress
        )

        # Get references to element's material shader mixers.
        mat = bpy.data.materials['Material.Network.{}.{:06d}'.format(
            element_type_to_name[animation.element_type],
            animation.element_id
        )]
        curve_group = mat.node_tree.nodes['Group.Curve']
        hidden_progress_input = curve_group.inputs[0]
        active_progress_input = curve_group.inputs[1]

        # Compute and set mixers.
        hidden_progress, active_progress = animate(animation, animation_progress)
        if hidden_progress > -1:
            hidden_progress_input.default_value = hidden_progress
        if active_progress > -1:
            active_progress_input.default_value = active_progress


def run():
    with open(ANIMATION_FILE) as animation_file:
        animations = json.load(animation_file)

    Animation = namedtuple('Animation', [
        'start_frame',
        'animation_type',
        'element_type',
        'element_id'
    ])

    animations = [Animation(*animation) for animation in animations]

    animation_type_to_length = {
        'show': ANIMATION_LENGTH_SHOW,
        'flash': ANIMATION_LENGTH_FLASH,
        'hide': ANIMATION_LENGTH_HIDE
    }

    element_type_to_name = {
        'node': 'Node',
        'channel': 'Channel'
    }

    bpy.context.scene.frame_set(0)
    reset_progress()

    bpy.app.handlers.frame_change_pre.clear()
    bpy.app.handlers.frame_change_pre.append(
        lambda scene: on_frame(
            scene,
            animations,
            animation_type_to_length,
            element_type_to_name,
            animate
        )
    )


if __name__ == "__main__":
    run()
