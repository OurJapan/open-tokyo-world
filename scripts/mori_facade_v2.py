"""Unify crown/body glass and add photo-guided central facade strips.

Strip width and face-center directions are estimates. No geometry is moved.
"""
import math
from mori_crown_v2 import CORNER_DEGREES, CENTER
from mori_shape import CROWN_OBJECTS
import mori_crown_material

STRIP_ANGLES = tuple((a+b)/2 % 360 for a,b in zip(CORNER_DEGREES, CORNER_DEGREES[1:]+(CORNER_DEGREES[0]+360,)))
STRIP_HALF_WIDTH = 0.65
GLASS_COLOR = (0.30,0.43,0.48,1.0)
GLASS_VALUES = {'Metallic':0.45,'Roughness':0.16,'Transmission Weight':0.12,'Alpha':1.0}


def on_strip(x,y):
    x-=CENTER[0];y-=CENTER[1]
    return any(abs(-math.sin(math.radians(a))*x+math.cos(math.radians(a))*y)<STRIP_HALF_WIDTH
               and math.cos(math.radians(a))*x+math.sin(math.radians(a))*y>0 for a in STRIP_ANGLES)


def add_strips(material):
    nodes=material.node_tree.nodes;links=material.node_tree.links
    outputs=[n for n in nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output]
    if len(outputs)!=1 or len(outputs[0].inputs['Surface'].links)!=1:
        raise ValueError('Expected one connected active material output')
    output=outputs[0];surface=output.inputs['Surface'].links[0].from_socket
    position=nodes.new('ShaderNodeNewGeometry').outputs['Position']
    center=nodes.new('ShaderNodeVectorMath');center.operation='SUBTRACT'
    links.new(position,center.inputs[0]);center.inputs[1].default_value=(*CENTER,0)
    def scalar(operation,a,b=None):
        n=nodes.new('ShaderNodeMath');n.operation=operation;links.new(a,n.inputs[0])
        if b is not None:
            if isinstance(b,(float,int)):n.inputs[1].default_value=b
            else:links.new(b,n.inputs[1])
        return n.outputs[0]
    def dot(vector):
        n=nodes.new('ShaderNodeVectorMath');n.operation='DOT_PRODUCT'
        links.new(center.outputs['Vector'],n.inputs[0]);n.inputs[1].default_value=vector
        return n.outputs['Value']
    mask=None
    for angle in STRIP_ANGLES:
        a=math.radians(angle)
        lateral=dot((-math.sin(a),math.cos(a),0))
        near=scalar('LESS_THAN',scalar('ABSOLUTE',lateral),STRIP_HALF_WIDTH)
        front=scalar('GREATER_THAN',dot((math.cos(a),math.sin(a),0)),0.0)
        band=scalar('MULTIPLY',near,front)
        mask=band if mask is None else scalar('MAXIMUM',mask,band)
    trim=nodes.new('ShaderNodeBsdfPrincipled');trim.name='OTW central vertical trim'
    trim.inputs['Base Color'].default_value=(0.55,0.57,0.58,1)
    trim.inputs['Metallic'].default_value=0.7;trim.inputs['Roughness'].default_value=0.23
    mix=nodes.new('ShaderNodeMixShader');mix.name='OTW central strip mask'
    links.new(mask,mix.inputs[0]);links.new(surface,mix.inputs[1]);links.new(trim.outputs[0],mix.inputs[2])
    links.new(mix.outputs[0],output.inputs['Surface'])


def apply(obj):
    if obj.name not in CROWN_OBJECTS or obj.type!='MESH' or obj.data.users!=1 or len(obj.data.materials)!=1:
        raise ValueError('Facade v2 requires exact single-user facade meshes with one material')
    if obj.hide_render or any(abs(obj.matrix_world[r][c]-(1 if r==c else 0))>1e-6 for r in range(4) for c in range(4)):
        raise ValueError('Expected visible facade at legacy identity transform')
    if obj.name==mori_crown_material.TARGET:
        mori_crown_material.apply(obj)
    # Copy every material before changing it, including shared mullion materials.
    for i,original in enumerate(list(obj.data.materials)):
        material=original.copy();material.name='OTW facade v2 / '+original.name
        obj.data.materials[i]=material
        if obj.name==mori_crown_material.TARGET:
            shader=material.node_tree.nodes.get('Principled BSDF')
            for key,value in GLASS_VALUES.items():shader.inputs[key].default_value=value
            material.diffuse_color=GLASS_COLOR
            if shader.inputs['Base Color'].is_linked:
                color=shader.inputs['Base Color'].links[0].from_node
                if color.type!='MIX_RGB':raise ValueError('Unexpected crown color source')
                color.inputs[1].default_value=GLASS_COLOR
            else:shader.inputs['Base Color'].default_value=GLASS_COLOR
        add_strips(material)
