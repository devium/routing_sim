import json
import time

import bpy

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


def clear_curves():
    del_curves = [curve for curve in bpy.data.curves if 'Curve.Network' in curve.name]
    for curve in del_curves:
        bpy.data.curves.remove(curve, do_unlink=True)


def run():
    tic = time.time()

    clear_objects()
    clear_meshes()
    clear_curves()

    toc = time.time()
    print('Cleared old objects in {} seconds.'.format(toc - tic))
    tic = toc

    with open(NETWORK_FILE) as network_file:
        network = json.load(network_file)

    nodes = network['nodes']
    channels = network['channels']

    bpy.ops.object.empty_add()
    network = bpy.context.object
    network.name = 'Object.Network'

    # Nodes.
    bpy.ops.object.empty_add()
    nodes_obj = bpy.context.object
    nodes_obj.name = 'Object.Network.Nodes'
    nodes_obj.parent = network

    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=SPHERES_NUM_SEGMENTS,
        ring_count=SPHERES_NUM_RINGS,
        size=SPHERES_SIZE,
        location=(0, 0, 0)
    )
    template = bpy.context.object
    template.name = 'Object.Network.Node.Template'
    template.hide_render = True
    mesh = template.data
    mesh.name = 'Mesh.Network.Node'
    bpy.data.objects.remove(template, do_unlink=True)

    for i, node in enumerate(nodes):
        obj = bpy.data.objects.new('Object.Network.Node.{:06}'.format(i), mesh)
        obj.location = node
        obj.parent = nodes_obj
        bpy.context.scene.objects.link(obj)

    # Channels.
    bpy.ops.object.empty_add()
    channels_obj = bpy.context.object
    channels_obj.name = 'Object.Network.Channels'
    channels_obj.parent = network
    for i, channel in enumerate(channels):
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
        obj.parent = channels_obj
        bpy.context.scene.objects.link(obj)

    bpy.context.scene.update()

    toc = time.time()
    print('Network topology successfully imported in {} seconds.'.format(toc - tic))


if __name__ == "__main__":
    run()
