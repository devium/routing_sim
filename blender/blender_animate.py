import json
from collections import namedtuple

import bpy

from settings import ANIMATION_FILE, TRANSFER_COLORS, ANIMATION_LENGTH_SHOW, \
    ANIMATION_LENGTH_FLASH, ANIMATION_LENGTH_HIDE


def reset_progress():
    bpy.context.scene.frame_set(0)
    network_mats = [mat for mat in bpy.data.materials if 'Material.Network.' in mat.name]
    for mat in network_mats:
        curve_group = mat.node_tree.nodes['Group.Curve']
        curve_group.inputs[0].default_value = 1
        curve_group.inputs[1].default_value = 0


class Animator:
    def __init__(self):
        with open(ANIMATION_FILE) as animation_file:
            animations = json.load(animation_file)

        Animation = namedtuple('Animation', [
            'start_frame',
            'animation_type',
            'element_type',
            'element_id',
            'transfer_id'
        ])

        self.animations = [Animation(*animation) for animation in animations]

        self.animation_type_to_length = {
            'show': ANIMATION_LENGTH_SHOW,
            'flash': ANIMATION_LENGTH_FLASH,
            'hide': ANIMATION_LENGTH_HIDE
        }

        self.element_type_to_name = {
            'node': 'Node',
            'channel': 'Channel'
        }

        self.transfer_colors = TRANSFER_COLORS

        reset_progress()

        bpy.app.handlers.frame_change_pre.clear()
        bpy.app.handlers.frame_change_pre.append(self.on_frame)

    def on_frame(self, scene):
        frame = scene.frame_current
        print('---- Frame {} ----'.format(frame))

        # Find all current animations.
        current_animations = [
            animation for animation in self.animations
            if animation.start_frame <= frame <=
            animation.start_frame + self.animation_type_to_length[animation.animation_type]
        ]

        for animation in current_animations:
            # Compute animation progress.
            animation_length = self.animation_type_to_length[animation.animation_type]
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
                self.element_type_to_name[animation.element_type],
                animation.element_id
            )]
            curve_group = mat.node_tree.nodes['Group.Curve']
            hidden_progress_input = curve_group.inputs[0]
            active_progress_input = curve_group.inputs[1]
            transfer_color_input = mat.node_tree.nodes['Group.Active'].inputs[0]

            # Compute and set progress inputs for mixers.
            hidden_progress, active_progress = animate(animation, animation_progress)
            if hidden_progress > -1:
                hidden_progress_input.default_value = hidden_progress
            if active_progress > -1:
                active_progress_input.default_value = active_progress
            if animation.transfer_id > -1:
                color_idx = animation.transfer_id % len(self.transfer_colors)
                transfer_color_input.default_value = self.transfer_colors[color_idx]


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


def run():
    Animator()


if __name__ == "__main__":
    run()
