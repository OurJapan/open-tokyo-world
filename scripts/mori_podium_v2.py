"""Recover the lower part of the removed PLATEAU Mori batch, without other tiles."""
import hashlib
from pathlib import Path

TARGET = 'Mori JP podium / stone'
SOURCE_BYTES = 79561
SOURCE_SHA256 = '786c370507eeb819fe004be256d02a995cb08a2cc301bf742e057b1e89b5ed3d'
CUT_HEIGHT = 40.0


def validate_source_bytes(raw):
    if len(raw)!=SOURCE_BYTES or hashlib.sha256(raw).hexdigest()!=SOURCE_SHA256:
        raise ValueError('Podium geometry source differs')


def select_faces(vertices, faces, batch):
    import numpy as np
    if vertices.shape!=(14412,3) or faces.shape!=(4804,3) or batch.shape!=(14412,):
        raise ValueError('Unexpected source archive shape')
    if not np.isfinite(vertices).all() or not np.issubdtype(faces.dtype,np.integer) or faces.min()<0 or faces.max()>=len(vertices):
        raise ValueError('Invalid source geometry')
    selected=faces[(batch[faces]==5).all(axis=1)]
    selected=selected[vertices[selected][:,:,2].max(axis=1)<=CUT_HEIGHT]
    if len(selected)!=667:raise ValueError('Unexpected lower Mori triangle count')
    return selected


def apply(obj, source):
    import bpy
    import numpy as np
    if obj.name!=TARGET or obj.type!='MESH' or obj.data.users!=1 or obj.data.shape_keys:
        raise ValueError('Expected exact single-user legacy podium target')
    if any(abs(obj.matrix_world[r][c]-(1 if r==c else 0))>1e-6 for r in range(4) for c in range(4)):
        raise ValueError('Expected legacy identity transform')
    raw=Path(source).read_bytes()
    validate_source_bytes(raw)
    import io
    with np.load(io.BytesIO(raw),allow_pickle=False) as archive:
        vertices=archive['vertices'];faces=select_faces(vertices,archive['faces'],archive['batch'])
    used,inverse=np.unique(faces,return_inverse=True)
    mesh=bpy.data.meshes.new('OTW Mori source lower podium v2')
    mesh.from_pydata(vertices[used].tolist(),[],inverse.reshape(-1,3).tolist());mesh.update()
    def material(name,color,metal,rough):
        m=bpy.data.materials.new('OTW podium v2 / '+name);m.use_nodes=True;m.diffuse_color=(*color,1)
        p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1)
        p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
        mesh.materials.append(m)
        return m,p
    glass,shader=material('inferred low-level glazing',(0.16,0.25,0.30),0.45,0.16)
    material('inferred terrace surface',(0.34,0.37,0.34),0,0.7)
    material('inferred paving',(0.42,0.43,0.41),0,0.75)
    # Fine neutral courses make the untextured source mass readable; no photos.
    n=glass.node_tree.nodes;l=glass.node_tree.links
    geo=n.new('ShaderNodeNewGeometry');xyz=n.new('ShaderNodeSeparateXYZ');l.new(geo.outputs['Position'],xyz.inputs[0])
    mod=n.new('ShaderNodeMath');mod.operation='MODULO';mod.inputs[1].default_value=5.2;l.new(xyz.outputs['Z'],mod.inputs[0])
    band=n.new('ShaderNodeMath');band.operation='LESS_THAN';band.inputs[1].default_value=0.27;l.new(mod.outputs[0],band.inputs[0])
    color=n.new('ShaderNodeMixRGB');color.inputs[1].default_value=(0.16,0.25,0.30,1);color.inputs[2].default_value=(0.52,0.54,0.53,1)
    l.new(band.outputs[0],color.inputs[0]);l.new(color.outputs[0],shader.inputs['Base Color'])
    for face in mesh.polygons:
        if abs(face.normal.z)>0.7:face.material_index=2 if face.center.z<1 else 1
    obj.data=mesh
    # Bevels on a triangle soup would expose internal triangulation edges.
    for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
    obj.hide_render=False;obj.hide_viewport=False
    obj['otw_geometry_source_sha256']=SOURCE_SHA256
    obj['otw_geometry_source_batch']=5
    obj['otw_part']='source-derived lower podium; materials inferred'
