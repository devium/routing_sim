import sys
import os

simulation_dir = PATH TO SIMULATION BLENDER DIR HERE
os.chdir(simulation_dir)
if simulation_dir not in sys.path:
    sys.path.insert(0, simulation_dir)

import settings
import blender_import
import blender_shade
import blender_animate
import importlib


def reload_modules():
    importlib.reload(settings)
    importlib.reload(blender_import)
    importlib.reload(blender_shade)
    importlib.reload(blender_animate)


def run_all():
    reload_modules()
    blender_import.run()
    blender_shade.run()
    blender_animate.run()
