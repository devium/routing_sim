import bpy
import json
from settings import NETWORK_FILE, SPHERES_NUM_SEGMENTS, SPHERES_NUM_RINGS, SPHERES_SIZE, \
    CHANNELS_RADIUS, CHANNELS_RESOLUTION


def clear_objects():
    del_objs = [obj for obj in bpy.data.objects if 'Object.Network' in obj.name]
    for obj in del_objs:
        bpy.data.objects.remove(obj, do_unlink=True)


def clear_meshes():
    del_meshes = [mesh for mesh in bpy.data.meshes if 'Mesh.Network' in mesh.name]
    for mesh in del_meshes:
        bpy.data.meshes.remove(mesh, do_unlink=True)


def run():
    clear_objects()
    clear_meshes()

    with open(NETWORK_FILE) as network_file:
        network = json.load(network_file)
        nodes = network['nodes']
        channels = network['channels']

        # Create sphere for every node.
        i = 0
        node_objs = []
        for node in nodes:
            bpy.ops.mesh.primitive_uv_sphere_add(
                segments=SPHERES_NUM_SEGMENTS,
                ring_count=SPHERES_NUM_RINGS,
                size=SPHERES_SIZE,
                location=node
            )
            obj = bpy.context.object
            obj.name = 'Object.Network.Node.{:06d}'.format(i)
            obj.data.name = 'Mesh.Network.Node.{:06d}'.format(i)
            node_objs.append(obj)
            i += 1

        # Create tubes along channels.
        i = 0
        for channel in channels:
            nodeA = nodes[channel[0]]
            nodeB = nodes[channel[1]]

            # Create path and extrude circle along that path.
            curve = bpy.data.curves.new('Curve.Network.Channel.{:06d}'.format(i), type='CURVE')
            curve.dimensions = '3D'
            curve.resolution_u = 2
            curve.bevel_depth = CHANNELS_RADIUS
            curve.bevel_resolution = CHANNELS_RESOLUTION
            curve.fill_mode = 'FULL'

            polyline = curve.splines.new('POLY')
            polyline.points.add(1)
            polyline.points[0].co = nodeA + [1]
            polyline.points[1].co = nodeB + [1]

            obj = bpy.data.objects.new('Object.Network.Channel.{:06d}'.format(i), curve)
            bpy.context.scene.objects.link(obj)
            i += 1


if __name__ == "__main__":
    run()
