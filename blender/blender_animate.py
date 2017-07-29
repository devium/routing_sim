import json
from collections import namedtuple

import bpy

from settings import ANIMATION_FILE, TRANSFER_COLORS, ANIMATION_LENGTH_SHOW, \
    ANIMATION_LENGTH_FLASH, ANIMATION_LENGTH_HIDE


def reset_progress():
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
            'time',
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
        self.on_frame(bpy.context.scene)

    def on_frame(self, scene):
        time = scene.frame_current / scene.render.fps

        reset_progress()

        # Find all current animations.
        current_animations = [
            animation for animation in self.animations if animation.time <= time
        ]

        for animation in current_animations:
            # Compute animation progress.
            animation_length = self.animation_type_to_length[animation.animation_type]
            animation_progress = (time - animation.time) / animation_length
            animation_progress = max(0.0, min(1.0, animation_progress))

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

        mats = (mat for mat in bpy.data.materials if 'Material.Network' in mat.name)
        for mat in mats:
            obj = bpy.data.objects['Object.Network' + mat.name[16:]]
            hidden_progress_input = mat.node_tree.nodes['Group.Curve'].inputs[0]
            hide = hidden_progress_input.default_value > 0.999
            obj.hide = hide
            obj.hide_render = hide


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
