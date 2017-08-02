import json
from collections import namedtuple, defaultdict

import bpy

from settings import ANIMATION_FILE, TRANSFER_COLORS, ANIMATION_LENGTH_SHOW, \
    ANIMATION_LENGTH_FLASH, ANIMATION_LENGTH_HIDE


def reset_progress(except_=None):
    if not except_:
        except_ = set()
    network_mats = [
        mat for mat in bpy.data.materials
        if 'Material.Network.' in mat.name and
        mat.name[17:] not in except_
    ]

    objs = [
        obj for obj in bpy.data.objects
        if 'Object.Network.' in obj.name and
        obj.name[15:] not in except_
    ]

    for obj in objs:
        obj.hide = True
        obj.hide_render = True

    for mat in network_mats:
        curve_group = mat.node_tree.nodes['Group.Curve']
        curve_group.inputs[0].default_value = 1
        curve_group.inputs[1].default_value = 0

    print('Reset {} materials.'.format(len(network_mats)))


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
        self.last_frame = -2

        bpy.app.handlers.frame_change_pre.clear()
        bpy.app.handlers.frame_change_pre.append(self.on_frame)
        self.on_frame(bpy.context.scene)

    def on_frame(self, scene):
        """
        Main objective: avoid Blender state changes. Update each material at most once.
        """
        time = scene.frame_current / scene.render.fps
        frame_time = 1 / scene.render.fps
        print('---- Frame {} @{:.3}s ----'.format(scene.frame_current, time))

        if scene.frame_current == self.last_frame:
            return

        if scene.frame_current - self.last_frame == 1:
            diff_only = True
        else:
            diff_only = False
        self.last_frame = scene.frame_current

        # Find all current animations.
        if diff_only:
            current_animations = [
                animation for animation in self.animations if animation.time <= time <=
                animation.time + self.animation_type_to_length[animation.animation_type]
                + frame_time
            ]
            print('Advancing one frame. {} running animations.'.format(len(current_animations)))
        else:
            current_animations = [
                animation for animation in self.animations if animation.time <= time
            ]
            print('Jumping frame. Replaying {} animations.'.format(len(current_animations)))

        type_to_id_to_mat_update = defaultdict(dict)
        for animation in current_animations:
            # Compute animation progress.
            animation_length = self.animation_type_to_length[animation.animation_type]
            animation_progress = (time - animation.time) / animation_length
            animation_progress = max(0.0, min(1.0, animation_progress))

            # Compute and set progress inputs for mixers.
            hidden_progress, active_progress = animate(animation, animation_progress)

            type_to_id_to_mat_update[animation.element_type][animation.element_id] = (
                hidden_progress, active_progress, animation.transfer_id
            )

        if not diff_only:
            # Reset materials that have not been updated.
            except_ = {
                '{}.{:06d}'.format(self.element_type_to_name[element_type], element_id)
                for element_type, id_to_mat_update in type_to_id_to_mat_update.items()
                for element_id in id_to_mat_update.keys()
            }
            print('Avoided reset on {} updated materials.'.format(len(except_)))
            reset_progress(except_)

        # Time for actual updates.
        num_updates = 0
        for element_type, id_to_mat_update in type_to_id_to_mat_update.items():
            for element_id, (
                    hidden_progress,
                    active_progress,
                    transfer_id
            ) in id_to_mat_update.items():
                # Get references to element's material shader mixers.
                name = '{}.{:06d}'.format(
                    self.element_type_to_name[element_type], element_id
                )
                mat = bpy.data.materials['Material.Network.' + name]
                obj = bpy.data.objects['Object.Network.' + name]
                curve_group = mat.node_tree.nodes['Group.Curve']
                hidden_progress_input = curve_group.inputs[0]
                active_progress_input = curve_group.inputs[1]
                transfer_color_input = mat.node_tree.nodes['Group.Active'].inputs[0]

                if hidden_progress > -1:
                    hidden_progress_input.default_value = hidden_progress
                if hidden_progress > 0.99:
                    obj.hide = True
                    obj.hide_render = True
                else:
                    obj.hide = False
                    obj.hide_render = False
                if active_progress > -1:
                    active_progress_input.default_value = active_progress
                if transfer_id > -1:
                    color_idx = transfer_id % len(self.transfer_colors)
                    transfer_color_input.default_value = self.transfer_colors[color_idx]

                num_updates += 1

        print('Performed {} updates.'.format(num_updates))


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
