# Raiden Network Simulation

## Installation

```
virtualenv env
env/bin/pip install -e .
```

## 2D simulation

```
env/bin/python bin/routing_sim.py
```

## Create rendering using blender

### Create simulation data.
1. Configure the constants in `bin/create_animation.py`.
1. Run

        env/bin/python bin/create_animation.py

1. Check for files `blender/network.json` and `blender/animation.json`.

### Import simulation data into Blender

1. Edit `blender_setup.py` with a global path to the simulation `blender` directory and copy its contents.
1. Configure `blender/settings.py`
1. Create a new blender project.
1. Open a `Python Console` editor.
1. Paste and execute the contents of (1).
1. Execute

        run_all()

   in Blender's Python console.

### Blender Python commands

| Command | Effect |
| --- | --- |
| `reload_modules()` | Reloads the import modules. Required after changes to the `settings.py` or any of the scripts in `blender/`. |
| `blender_import.run()` | Imports network model data from `network.json`. |
| `blender_shade.run()` | Creates the shader setup for the visualization. Existing shader node groups will be kept. |
| `blender_animate.run()` | Imports the animation data from `animation.json` and registers it with the frame handler. |
| `run_all()` | Does all of the above |


### Shaders

The `blender_shade.run()` script creates a single material for each element in the network, i.e., for every node and channel.

These materials use shaders from the Cycles rendering engine. Changes to these materials will be lost on reimport. However, all elements of a certain type (node or channel) share several shader node groups that can be configured:

| Node group | Responsibility |
| --- | --- |
| Default | The default appearance of a network element if it is visible. |
| Active | The appearance of a network element that is currently part of a transfer. It takes as input the color of the current transfer as specified in `blender/settings.py`. |
| Hidden | The appearance of a hidden, i.e. in the simulation non-existing, channel element. This is expected to be a simple transparency shader. |
| Curves | The three node groups above are mixed using two mixers to create the final appearance of a network element. The animation script linearly interpolates animations between their two states. The curve node group can be used to map this linear interpolation to a different curve. The R channel of the curve editor maps the show and hide animations. The G channel maps the flash animation.
