"""Photo-guided crown appearance; optical values are estimates, not measurements."""
TARGET = 'Mori continuous pearl glass / pearl grey coated glass'
CAP_BASE = 318.32


def is_crown_face(heights):
    return min(heights) >= CAP_BASE-0.001 and max(heights) > CAP_BASE+0.001


def apply(obj):
    if obj.name != TARGET or obj.type != 'MESH' or obj.data.users != 1:
        raise ValueError('Crown material requires the exact single-user facade mesh')
    if len(obj.data.materials) != 1:
        raise ValueError('Unexpected material slots; refusing repeat application')
    original = obj.data.materials[0]
    if not original or not original.use_nodes:
        raise ValueError('Expected node material')
    faces = [p for p in obj.data.polygons if is_crown_face([obj.data.vertices[i].co.z for i in p.vertices])]
    if len(faces) != 1280 or any(p.material_index != 0 for p in faces):
        raise ValueError('Expected five exposed faces on each of 256 crown panes')
    crown = original.copy()
    crown.name = 'OTW Mori crown / pearl grey reflective glass v1'
    shader = crown.node_tree.nodes.get('Principled BSDF')
    if shader is None:
        raise ValueError('Expected Principled BSDF')
    for key, value in {'Metallic':0.45, 'Roughness':0.16, 'Transmission Weight':0.12, 'Alpha':1.0}.items():
        if shader.inputs[key].is_linked:
            raise ValueError('Unexpected linked material input: '+key)
        shader.inputs[key].default_value = value
    obj.data.materials.append(crown)
    for face in faces:
        face.material_index = 1
    # A dedicated UV layer keeps the approved vertices and existing facade UVs.
    # Three crown courses are a photo-guided approximation, not surveyed framing.
    import math
    from mori_crown_v2 import top_height, CENTER
    uv = obj.data.uv_layers.new(name='OTW crown courses v1')
    for face in faces:
        for li in face.loop_indices:
            vi = obj.data.loops[li].vertex_index
            co = obj.data.vertices[vi].co
            top = top_height(math.atan2(co.y-CENTER[1],co.x-CENTER[0]))
            u = 0.0 if vi % 8 in (0,3,4,7) else 1.0
            uv.data[li].uv = (u, max(0.0,min(1.0,(co.z-CAP_BASE)/(top-CAP_BASE))))
    nodes = crown.node_tree.nodes; links = crown.node_tree.links
    tex = nodes.new('ShaderNodeUVMap'); tex.uv_map = uv.name
    split = nodes.new('ShaderNodeSeparateXYZ'); links.new(tex.outputs['UV'],split.inputs[0])
    def math_node(operation, source, value=None):
        n=nodes.new('ShaderNodeMath');n.operation=operation
        links.new(source,n.inputs[0])
        if value is not None:n.inputs[1].default_value=value
        return n.outputs[0]
    courses=math_node('MULTIPLY',split.outputs['Y'],3.0)
    horizontal=math_node('LESS_THAN',math_node('FRACT',courses),0.085)
    vertical=math_node('LESS_THAN',split.outputs['X'],0.06)
    maximum=nodes.new('ShaderNodeMath');maximum.operation='MAXIMUM'
    links.new(horizontal,maximum.inputs[0]);links.new(vertical,maximum.inputs[1])
    color=nodes.new('ShaderNodeMixRGB');color.blend_type='MIX'
    color.inputs[1].default_value=(0.30,0.43,0.48,1)
    color.inputs[2].default_value=(0.075,0.115,0.14,1)
    links.new(maximum.outputs[0],color.inputs[0]);links.new(color.outputs[0],shader.inputs['Base Color'])
    obj.data.update()

