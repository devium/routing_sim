import json
from collections import namedtuple, defaultdict

import bpy

from settings import (
    ANIMATION_FILE,
    ANIMATION_LENGTH_SHOW,
    ANIMATION_LENGTH_FLASH,
    ANIMATION_LENGTH_HIDE,
    ANIMATION_DEPTH,
    NODES_DEFAULT_VISIBLE,
    CHANNELS_DEFAULT_VISIBLE,
)


def to_pass_index(active_progress, hidden_progress):
    """
    Map constrained two-dimensional values in [0,1]^2 to a one-dimensional domain by transforming
    them first mapping their values into a limited integer domain {0,1,2,...,c} and then combining
    them using a polynomial:
    a,b in [0,1]
    a_int, b_int = floor(a * (c - 1)), floor(b * (c - 1))
    combined = a_int * c + b_int
    I'm sure there is a name for this kind of mapping.
    """
    active_int = int((ANIMATION_DEPTH - 1) * active_progress)
    hidden_int = int((ANIMATION_DEPTH - 1) * hidden_progress)
    return ANIMATION_DEPTH * active_int + hidden_int


def from_pass_index(pass_index):
    """
    Returns (active_progress, hidden_progress).
    """
    return pass_index // ANIMATION_DEPTH / (ANIMATION_DEPTH - 1), \
           pass_index % ANIMATION_DEPTH / (ANIMATION_DEPTH - 1)


def reset_progress(channels_popup, except_=None):
    if not except_:
        except_ = set()

    node_objs = [
        obj for obj in bpy.data.objects
        if 'Object.Network.Node' in obj.name and obj.name[15:] not in except_
    ]

    channel_objs = [
        obj for obj in bpy.data.objects
        if 'Object.Network.Channel' in obj.name and obj.name[15:] not in except_
    ]

    for obj in node_objs:
        if not channels_popup and NODES_DEFAULT_VISIBLE:
            obj.hide = False
            obj.hide_render = False
            obj.pass_index = to_pass_index(0, 0)
        else:
            obj.hide = True
            obj.hide_render = True
            obj.pass_index = to_pass_index(0, 1)

    for obj in channel_objs:
        if not channels_popup and CHANNELS_DEFAULT_VISIBLE:
            obj.hide = False
            obj.hide_render = False
            obj.pass_index = to_pass_index(0, 0)
        else:
            obj.hide = True
            obj.hide_render = True
            obj.pass_index = to_pass_index(0, 1)

    print('Reset {} objects.'.format(len(node_objs) + len(channel_objs)))


def get_curve_mappings():
    """
    Return curve mapping for (node, channel).
    """
    return (
        bpy.data.materials['Material.Network.Node'].node_tree.nodes['RGB Curves'],
        bpy.data.materials['Material.Network.Channel'].node_tree.nodes['RGB Curves']
    )


def evaluate_curve_discrete(curve, value):
    # We lose precision when converting to discrete progress. We have to take that
    # into account when emulating curve mappings.
    return curve.evaluate(int(value * ANIMATION_DEPTH) / ANIMATION_DEPTH)


class Animator:
    def __init__(self):
        self.channels_popup = True
        with open(ANIMATION_FILE) as animation_file:
            content = json.load(animation_file)
            if isinstance(content, list):
                # Legacy format.
                animations = content
            else:
                self.channels_popup = content['channels_popup']
                animations = content['animations']

        Animation = namedtuple('Animation', [
            'time',
            'animation_type',
            'element_type',
            'element_id',
            'transfer_id'
        ])

        self.animations = [Animation(*animation) for animation in animations]
        if not self.channels_popup:
            self.animations = [
                animation for animation in self.animations
                if animation.animation_type != 'show' and animation.animation_type != 'hide'
            ]

        self.animation_type_to_length = {
            'show': ANIMATION_LENGTH_SHOW,
            'flash': ANIMATION_LENGTH_FLASH,
            'hide': ANIMATION_LENGTH_HIDE
        }

        self.element_type_to_name = {
            'node': 'Node',
            'channel': 'Channel'
        }

        # -2 because -1 to 0 might be mistaken as an incremental update.
        self.last_frame = -2

        node_curve, channel_curve = get_curve_mappings()
        node_curve.mapping.initialize()
        channel_curve.mapping.initialize()

        bpy.app.handlers.frame_change_pre.clear()
        bpy.app.handlers.frame_change_pre.append(self.on_frame)
        self.on_frame(bpy.context.scene)

    def on_frame(self, scene):
        """
        Main objective: avoid Blender state changes. Update each object at most once.
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

        # We need the curve mappings to find out which transfer is currently brightest.
        node_curve, channel_curve = get_curve_mappings()
        type_to_active_curve = {
            'node': node_curve.mapping.curves[0],
            'channel': channel_curve.mapping.curves[0]
        }
        type_to_hidden_curve = {
            'node': node_curve.mapping.curves[1],
            'channel': channel_curve.mapping.curves[1]
        }
        type_to_visible = {
            'node': NODES_DEFAULT_VISIBLE,
            'channel': CHANNELS_DEFAULT_VISIBLE
        }

        type_to_id_to_mat_update = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
        for animation in current_animations:
            # Compute animation progress.
            animation_length = self.animation_type_to_length[animation.animation_type]
            animation_progress = (time - animation.time) / animation_length
            animation_progress = max(0.0, min(1.0, animation_progress))

            # Compute and set progress inputs for mixers.
            active_progress, hidden_progress = animate(animation, animation_progress)

            animation_state = \
                type_to_id_to_mat_update[animation.element_type][animation.element_id]

            if active_progress != -1:
                if animation.transfer_id != animation_state[2]:
                    # If there are multiple active transfers, take the brightest one.
                    curve = type_to_active_curve[animation.element_type]
                    brightness_stored = evaluate_curve_discrete(curve, animation_state[0])
                    brightness_new = evaluate_curve_discrete(curve, active_progress)

                    active_progress = max(
                        (brightness_stored, animation_state[0]),
                        (brightness_new, active_progress)
                    )[1]

                animation_state[0] = active_progress
            if hidden_progress != -1:
                animation_state[1] = hidden_progress
            animation_state[2] = animation.transfer_id

        if not diff_only:
            # Reset objects that have not been updated.
            except_ = {
                '{}.{:06d}'.format(self.element_type_to_name[element_type], element_id)
                for element_type, id_to_mat_update in type_to_id_to_mat_update.items()
                for element_id in id_to_mat_update.keys()
            }
            print('Avoided reset on {} updated objects.'.format(len(except_)))
            reset_progress(self.channels_popup, except_)

        # Time for actual updates.
        num_updates = 0
        for element_type, id_to_mat_update in type_to_id_to_mat_update.items():
            for element_id, (
                    active_progress, hidden_progress, transfer_id
            ) in id_to_mat_update.items():
                # Get references to element's material shader mixers.
                name = '{}.{:06d}'.format(
                    self.element_type_to_name[element_type], element_id
                )
                obj = bpy.data.objects['Object.Network.' + name]
                current_active_progress, current_hidden_progress = from_pass_index(obj.pass_index)

                hide = False
                if active_progress == -1:
                    active_progress = current_active_progress
                if not type_to_visible[element_type]:
                    active_mix = evaluate_curve_discrete(
                        type_to_active_curve[element_type], active_progress
                    )
                    if active_mix < 0.05:
                        hide = True

                if hidden_progress == -1:
                    hidden_progress = current_hidden_progress
                hidden_mix = evaluate_curve_discrete(
                    type_to_hidden_curve[element_type], hidden_progress
                )
                if hidden_mix > 0.95:
                    hide = True

                obj.hide = hide
                obj.hide_render = hide

                obj.pass_index = to_pass_index(active_progress, hidden_progress)

                num_updates += 1

        print('Performed {} updates.'.format(num_updates))


def animate(animation, progress):
    """
    Returns a tuple for the current mixer values (progress_active, progress_hidden).
    Tuple elements are -1 if unchanged.
    """
    if animation.animation_type == 'show':
        return -1, 1 - progress
    elif animation.animation_type == 'flash':
        return progress, -1
    elif animation.animation_type == 'hide':
        return -1, progress
    else:
        return -1, -1


def run():
    Animator()


if __name__ == "__main__":
    run()
