import bpy
import time

from settings import ANIMATION_DEPTH, TRANSFER_COLOR


def clear_node_groups():
    del_groups = [group for group in bpy.data.node_groups if 'NodeGroup.Network' in group.name]
    for group in del_groups:
        bpy.data.node_groups.remove(group, do_unlink=True)


def clear_materials():
    """
    Delete all materials created by possible previous calls of this script.
    """
    del_mats = [mat for mat in bpy.data.materials if 'Material.Network' in mat.name]
    for mat in del_mats:
        bpy.data.materials.remove(mat, do_unlink=True)


def set_material(data, mat):
    # Sets the first material or creates a new one if required.
    if data.materials:
        data.materials[0] = mat
    else:
        data.materials.append(mat)


def create_material(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True

    mat.use_nodes = True
    nodes = mat.node_tree.nodes

    nodes.remove(nodes['Diffuse BSDF'])
    # Create nodes. Mixer names are used by the animation script.
    progress_frame = nodes.new('NodeFrame')
    curve_frame = nodes.new('NodeFrame')
    mixer_frame = nodes.new('NodeFrame')
    object_info = nodes.new('ShaderNodeObjectInfo')
    index_splitter_hidden_1 = nodes.new('ShaderNodeMath')
    index_splitter_hidden_1.operation = 'MODULO'
    index_splitter_hidden_2 = nodes.new('ShaderNodeMath')
    index_splitter_hidden_2.operation = 'DIVIDE'
    index_splitter_active_1 = nodes.new('ShaderNodeMath')
    index_splitter_active_1.operation = 'DIVIDE'
    # 2 and 3 are needed as a replacement for a floor function.
    index_splitter_active_2 = nodes.new('ShaderNodeMath')
    index_splitter_active_2.operation = 'SUBTRACT'
    index_splitter_active_3 = nodes.new('ShaderNodeMath')
    index_splitter_active_3.operation = 'ROUND'
    index_splitter_active_4 = nodes.new('ShaderNodeMath')
    index_splitter_active_4.operation = 'DIVIDE'
    depth = nodes.new('ShaderNodeValue')
    depth_1 = nodes.new('ShaderNodeMath')
    depth_1.operation = 'SUBTRACT'
    rgb_combiner = nodes.new('ShaderNodeCombineRGB')
    rgb_curve = nodes.new('ShaderNodeRGBCurve')
    rgb_splitter = nodes.new('ShaderNodeSeparateRGB')

    # Cycles nodes.
    output = nodes['Material Output']
    mix_active = nodes.new('ShaderNodeMixShader')
    mix_hidden = nodes.new('ShaderNodeMixShader')
    default_shader = nodes.new('ShaderNodeEmission')
    active_shader = nodes.new('ShaderNodeEmission')
    hidden_shader = nodes.new('ShaderNodeBsdfTransparent')

    # Default values.
    depth.outputs[0].default_value = ANIMATION_DEPTH
    depth_1.inputs[1].default_value = 1
    index_splitter_active_2.inputs[1].default_value = 0.5
    rgb_curve.mapping.curves[0].points[1].location = (1.0, 0.0)
    rgb_curve.mapping.curves[0].points.new(0.15, 1.0)
    rgb_curve.mapping.curves[0].points.new(0.4, 0.4)
    rgb_curve.mapping.curves[0].points.new(0.9, 0.2)
    rgb_curve.mapping.update()

    default_shader.inputs[0].default_value = (0.2, 0.2, 0.2, 1.0)
    active_shader.inputs[0].default_value = TRANSFER_COLOR

    # Names and labels.
    progress_frame.name = 'Frame.Progress'
    progress_frame.label = 'Animation Progress Computation From Pass Index'
    curve_frame.name = 'Frame.Curve'
    curve_frame.label = 'Animation Progress Curve Mapping'
    mixer_frame.name = 'Frame.Mixers'
    mixer_frame.label = 'Shader Mixers'
    depth.name = 'Value.Depth'
    depth.label = 'Animation Depth'
    index_splitter_hidden_1.label = 'Split to Hidden'
    index_splitter_hidden_2.label = 'Hidden Mix Normalizer'
    index_splitter_active_1.label = 'Split to Active'
    index_splitter_active_4.label = 'Active Mix Normalizer'

    mix_active.name = 'Mixer.Active'
    mix_active.label = 'Active Mixer'
    mix_hidden.name = 'Mixer.Hidden'
    mix_hidden.label = 'Hidden Mixer'
    # Position nodes for visibility.
    depth.location = (-1200, 300)
    depth_1.location = (-1200, 200)
    object_info.location = (-1200, 000)
    index_splitter_hidden_1.location = (-1000, 100)
    index_splitter_hidden_2.location = (-400, 100)
    index_splitter_active_1.location = (-1000, 300)
    index_splitter_active_2.location = (-800, 300)
    index_splitter_active_3.location = (-600, 300)
    index_splitter_active_4.location = (-400, 300)
    rgb_combiner.location = (-100, 300)
    rgb_curve.location = (100, 300)
    rgb_splitter.location = (400, 300)

    output.location = (1200, 300)
    mix_active.location = (700, 300)
    mix_hidden.location = (900, 300)

    default_shader.location = (600, 100)
    active_shader.location = (800, 100)
    hidden_shader.location = (1000, 100)

    # Link nodes together.
    links = mat.node_tree.links

    links.new(output.inputs[0], mix_hidden.outputs[0])
    links.new(mix_active.inputs[0], rgb_splitter.outputs[0])
    links.new(mix_active.inputs[1], default_shader.outputs[0])
    links.new(mix_active.inputs[2], active_shader.outputs[0])
    links.new(mix_hidden.inputs[0], rgb_splitter.outputs[1])
    links.new(mix_hidden.inputs[1], mix_active.outputs[0])
    links.new(mix_hidden.inputs[2], hidden_shader.outputs[0])

    links.new(rgb_splitter.inputs[0], rgb_curve.outputs[0])
    links.new(rgb_curve.inputs[1], rgb_combiner.outputs[0])
    links.new(rgb_combiner.inputs[0], index_splitter_active_4.outputs[0])
    links.new(rgb_combiner.inputs[1], index_splitter_hidden_2.outputs[0])
    links.new(index_splitter_active_1.inputs[0], object_info.outputs[1])
    links.new(index_splitter_active_1.inputs[1], depth.outputs[0])
    links.new(index_splitter_active_2.inputs[0], index_splitter_active_1.outputs[0])
    links.new(index_splitter_active_3.inputs[0], index_splitter_active_2.outputs[0])
    links.new(index_splitter_active_4.inputs[0], index_splitter_active_3.outputs[0])
    links.new(index_splitter_active_4.inputs[1], depth_1.outputs[0])
    links.new(index_splitter_hidden_1.inputs[0], object_info.outputs[1])
    links.new(index_splitter_hidden_1.inputs[1], depth.outputs[0])
    links.new(index_splitter_hidden_2.inputs[0], index_splitter_hidden_1.outputs[0])
    links.new(index_splitter_hidden_2.inputs[1], depth_1.outputs[0])
    links.new(depth_1.inputs[0], depth.outputs[0])

    # Assign frames.
    depth.parent = progress_frame
    depth_1.parent = progress_frame
    object_info.parent = progress_frame
    index_splitter_active_1.parent = progress_frame
    index_splitter_active_2.parent = progress_frame
    index_splitter_active_3.parent = progress_frame
    index_splitter_active_4.parent = progress_frame
    index_splitter_hidden_1.parent = progress_frame
    index_splitter_hidden_2.parent = progress_frame

    rgb_combiner.parent = curve_frame
    rgb_curve.parent = curve_frame
    rgb_splitter.parent = curve_frame

    mix_active.parent = mixer_frame
    mix_hidden.parent = mixer_frame

    return mat


def run():
    tic = time.time()
    # Use Cycles renderer because pretty.
    bpy.context.scene.render.engine = 'CYCLES'

    node_material_name = 'Material.Network.Node'
    if node_material_name in bpy.data.materials:
        mat = bpy.data.materials[node_material_name]
    else:
        mat = create_material('Material.Network.Node')
    mesh = bpy.data.meshes['Mesh.Network.Node']
    set_material(mesh, mat)
    for face in mesh.polygons:
        face.use_smooth = True

    channel_material_name = 'Material.Network.Channel'
    if channel_material_name in bpy.data.materials:
        mat = bpy.data.materials[channel_material_name]
    else:
        mat = create_material(channel_material_name)
    channel_objs = [obj for obj in bpy.data.objects if 'Object.Network.Channel.' in obj.name]
    for obj in channel_objs:
        set_material(obj.data, mat)

    toc = time.time()
    print('Shaders successfully set up in {} seconds.'.format(toc - tic))


if __name__ == "__main__":
    run()
