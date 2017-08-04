import json
from collections import namedtuple, defaultdict

import bpy

from settings import ANIMATION_FILE, ANIMATION_LENGTH_SHOW, \
    ANIMATION_LENGTH_FLASH, ANIMATION_LENGTH_HIDE, ANIMATION_DEPTH


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
    return pass_index // ANIMATION_DEPTH / (ANIMATION_DEPTH - 1), \
           pass_index % ANIMATION_DEPTH / (ANIMATION_DEPTH - 1)


def reset_progress(except_=None):
    if not except_:
        except_ = set()

    objs = [
        obj for obj in bpy.data.objects
        if ('Object.Network.Node' in obj.name or 'Object.Network.Channel' in obj.name) and
        obj.name[15:] not in except_
    ]

    for obj in objs:
        obj.hide = True
        obj.hide_render = True
        obj.pass_index = to_pass_index(0, 1)

    print('Reset {} objects.'.format(len(objs)))


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

        self.last_frame = -2

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

        type_to_id_to_mat_update = defaultdict(dict)
        for animation in current_animations:
            # Compute animation progress.
            animation_length = self.animation_type_to_length[animation.animation_type]
            animation_progress = (time - animation.time) / animation_length
            animation_progress = max(0.0, min(1.0, animation_progress))

            # Compute and set progress inputs for mixers.
            active_progress, hidden_progress = animate(animation, animation_progress)

            type_to_id_to_mat_update[animation.element_type][animation.element_id] = (
                active_progress, hidden_progress, animation.transfer_id
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
                    active_progress,
                    hidden_progress,
                    transfer_id
            ) in id_to_mat_update.items():
                # Get references to element's material shader mixers.
                name = '{}.{:06d}'.format(
                    self.element_type_to_name[element_type], element_id
                )
                obj = bpy.data.objects['Object.Network.' + name]
                current_active_progress, current_hidden_progress = from_pass_index(obj.pass_index)

                active_progress = current_active_progress if active_progress == -1 \
                    else active_progress
                hidden_progress = current_hidden_progress if hidden_progress == -1 \
                    else hidden_progress
                if hidden_progress > 0.99:
                    obj.hide = True
                    obj.hide_render = True
                else:
                    obj.hide = False
                    obj.hide_render = False

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
