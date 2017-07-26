import bpy


def clear_materials():
    """
    Delete all materials created by possible previous calls of this script.
    """
    del_mats = [mat for mat in bpy.data.materials if 'Material.Network.' in mat.name]
    for mat in del_mats:
        bpy.data.materials.remove(mat, do_unlink=True)


def clear_node_groups(keep=None):
    """
    Delete all node groups that have been created by previous calls to this script, except the ones
    we intend to keep and want unchanged. The kept groups might have already been changed by the
    Blender user and we do not want to delete those.
    """
    del_node_groups = [
        node_group for node_group
        in bpy.data.node_groups
        if 'NodeGroup.Network' in node_group.name
    ]
    for node_group in del_node_groups:
        if keep is not None and node_group.name in keep:
            continue
        bpy.data.node_groups.remove(node_group, do_unlink=True)


def create_empty_node_group(name):
    """
    Creates a new empty node group if it does not exist yet.
    """
    if name in bpy.data.node_groups:
        node_group = bpy.data.node_groups[name]
    else:
        node_group = bpy.data.node_groups.new(name, 'ShaderNodeTree')
        output = node_group.nodes.new('NodeGroupOutput')
        node_group.outputs.new('NodeSocketShader', 'Shader')
        output.location = (300, 0)

    return node_group


def create_color_node_group(name):
    """
    Creates an empty node group with a color input.
    """
    if name in bpy.data.node_groups:
        node_group = bpy.data.node_groups[name]
    else:
        node_group = bpy.data.node_groups.new(name, 'ShaderNodeTree')
        input_ = node_group.nodes.new('NodeGroupInput')
        output = node_group.nodes.new('NodeGroupOutput')

        node_group.inputs.new('NodeSocketColor', 'Transfer Color')
        node_group.outputs.new('NodeSocketShader', 'Shader')

        input_.location = (-200, 0)
        output.location = (300, 0)

    return node_group


def create_curve_node_group(name):
    """
    Creates a new curve mapping node group if it does not exist yet.
    """
    if name in bpy.data.node_groups:
        node_group = bpy.data.node_groups[name]
    else:
        node_group = bpy.data.node_groups.new(name, 'ShaderNodeTree')
        input_ = node_group.nodes.new('NodeGroupInput')
        combiner = node_group.nodes.new('ShaderNodeCombineRGB')
        curves = node_group.nodes.new('ShaderNodeRGBCurve')
        splitter = node_group.nodes.new('ShaderNodeSeparateRGB')
        output = node_group.nodes.new('NodeGroupOutput')

        node_group.inputs.new('NodeSocketFloatFactor', 'Hidden Progress')
        node_group.inputs.new('NodeSocketFloatFactor', 'Active Progress')
        node_group.outputs.new('NodeSocketFloatFactor', 'Hidden Mix Factor')
        node_group.outputs.new('NodeSocketFloatFactor', 'Active Mix Factor')

        node_group.inputs[0].min_value = 0.0
        node_group.inputs[0].max_value = 1.0
        node_group.inputs[1].min_value = 0.0
        node_group.inputs[1].max_value = 1.0

        curves.mapping.curves[1].points[1].location = (1.0, 0.0)
        curves.mapping.curves[1].points.new(0.25, 1.0)
        curves.mapping.update()

        links = node_group.links
        links.new(combiner.inputs[0], input_.outputs[0])
        links.new(combiner.inputs[1], input_.outputs[1])
        links.new(curves.inputs[1], combiner.outputs[0])
        links.new(splitter.inputs[0], curves.outputs[0])
        links.new(output.inputs[0], splitter.outputs[0])
        links.new(output.inputs[1], splitter.outputs[1])

        input_.location = (-600, 0)
        combiner.location = (-400, 0)
        curves.location = (-200, 0)
        splitter.location = (100, 0)
        output.location = (300, 0)

    return node_group


def create_material(
        name,
        hidden_node_group,
        default_node_group,
        active_node_group,
        curve_node_group
):
    """
    Create the node material that links two shader mixers to three shared node groups. The first
    shader mixer mixes a "default" shader (network element default visibility) with the "active"
    shader (activated state of the network element). The second mixer mixes the result of the first
    with a "hidden" shader (visibility of the element).

    Default shader
                 + => Active mixer
    Active shader                 + => Hidden mixer => Output
                      Hidden Shader

    These two mixers are controlled by the animation script.
    """
    mat = bpy.data.materials.new(name)

    mat.use_nodes = True
    nodes = mat.node_tree.nodes

    # Create nodes. Mixer names are used by the animation script.
    nodes.remove(nodes['Diffuse BSDF'])
    output = nodes['Material Output']
    mix_active = nodes.new('ShaderNodeMixShader')
    mix_active.name = 'Mixer.Active'
    mix_hidden = nodes.new('ShaderNodeMixShader')
    mix_hidden.name = 'Mixer.Hidden'
    hidden_group_node = nodes.new('ShaderNodeGroup')
    hidden_group_node.name = 'Group.Hidden'
    hidden_group_node.node_tree = hidden_node_group
    default_group_node = nodes.new('ShaderNodeGroup')
    default_group_node.name = 'Group.Default'
    default_group_node.node_tree = default_node_group
    active_group_node = nodes.new('ShaderNodeGroup')
    active_group_node.name = 'Group.Active'
    active_group_node.node_tree = active_node_group
    curve_group_node = nodes.new('ShaderNodeGroup')
    curve_group_node.name = 'Group.Curve'
    curve_group_node.node_tree = curve_node_group

    # Position nodes for visibility.
    default_group_node.location = (-400, 300)
    default_group_node.width = 240
    active_group_node.location = (-400, 200)
    active_group_node.width = 240
    mix_active.location = (-100, 300)
    hidden_group_node.location = (-400, 80)
    hidden_group_node.width = 240
    mix_hidden.location = (100, 300)
    curve_group_node.location = (-400, 500)
    curve_group_node.width = 200

    # Link nodes together.
    links = mat.node_tree.links
    links.new(mix_hidden.inputs[0], curve_group_node.outputs[0])
    links.new(mix_active.inputs[0], curve_group_node.outputs[1])
    links.new(mix_active.inputs[1], default_group_node.outputs[0])
    links.new(mix_active.inputs[2], active_group_node.outputs[0])
    links.new(mix_hidden.inputs[1], mix_active.outputs[0])
    links.new(mix_hidden.inputs[2], hidden_group_node.outputs[0])
    links.new(output.inputs[0], mix_hidden.outputs[0])

    # Default mix is "default and not hidden".
    mix_active.inputs[0].default_value = 0
    mix_hidden.inputs[0].default_value = 0

    return mat


def set_material(obj, mat):
    # Sets the first material or creates a new one if required.
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


def shade_smooth(obj):
    # Default faces use flat shading. We want smooth shading.
    for face in obj.data.polygons:
        face.use_smooth = True


def run():
    empty_node_group_names = [
        'NodeGroup.Network.Node.Hidden',
        'NodeGroup.Network.Node.Default',

        'NodeGroup.Network.Channel.Hidden',
        'NodeGroup.Network.Channel.Default',
    ]

    color_node_group_names = [
        'NodeGroup.Network.Node.Active',
        'NodeGroup.Network.Channel.Active'
    ]

    curve_node_group_names = [
        'NodeGroup.Network.Node.Curve',
        'NodeGroup.Network.Channel.Curve'
    ]

    # Use Cycles renderer because pretty.
    bpy.context.scene.render.engine = 'CYCLES'

    # Cleanup from previous calls.
    clear_materials()
    clear_node_groups(keep=empty_node_group_names+color_node_group_names+curve_node_group_names)

    for node_group_name in empty_node_group_names:
        create_empty_node_group(node_group_name)

    for color_group_name in color_node_group_names:
        create_color_node_group(color_group_name)

    for curve_node_group_name in curve_node_group_names:
        create_curve_node_group(curve_node_group_name)

    node_hidden_node_group = bpy.data.node_groups['NodeGroup.Network.Node.Hidden']
    node_default_node_group = bpy.data.node_groups['NodeGroup.Network.Node.Default']
    node_active_node_group = bpy.data.node_groups['NodeGroup.Network.Node.Active']
    node_curve_node_group = bpy.data.node_groups['NodeGroup.Network.Node.Curve']

    channel_hidden_node_group = bpy.data.node_groups['NodeGroup.Network.Channel.Hidden']
    channel_default_node_group = bpy.data.node_groups['NodeGroup.Network.Channel.Default']
    channel_active_node_group = bpy.data.node_groups['NodeGroup.Network.Channel.Active']
    channel_curve_node_group = bpy.data.node_groups['NodeGroup.Network.Channel.Curve']

    # Create node materials for nodes and channels.
    for obj in bpy.data.objects:
        if 'Object.Network.Node' in obj.name:
            i = int(obj.name[-6:])
            shade_smooth(obj)
            mat = create_material(
                'Material.Network.Node.{:06d}'.format(i),
                node_hidden_node_group,
                node_default_node_group,
                node_active_node_group,
                node_curve_node_group
            )
            set_material(obj, mat)
        elif 'Object.Network.Channel' in obj.name:
            i = int(obj.name[-6:])
            mat = create_material(
                'Material.Network.Channel.{:06d}'.format(i),
                channel_hidden_node_group,
                channel_default_node_group,
                channel_active_node_group,
                channel_curve_node_group
            )
            set_material(obj, mat)


if __name__ == "__main__":
    run()
