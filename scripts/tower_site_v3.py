# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Pinned site/roof/access increment; isolated build, validation and render phases."""
import argparse
import json
import math
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from review import digest, require, compare_reports, validate_cameras
from tower_structure_v1 import MeshBuilder
import tower_site_geometry_v3 as geo

PREFIX='OTW Tokyo Tower site v3 / '
COLLECTION='OTW Tokyo Tower site v3'
FEATURE='otw:jp:tokyo:minato:tokyo-tower'
OLD='OTW Tokyo Tower structure / '
PORTAL_MESH={'Photo based main deck / '+g for g in ('wall','frame','silver','rubber')}
CHANGED_MESH={OLD+'foottown-metal',OLD+'foottown-roof',OLD+'stairs-guards'}|PORTAL_MESH
ADDED={PREFIX+g for g in geo.MATERIALS}
CONFIG=ROOT/'areas/tokyo-tower/tower-site-v3-input.json'


def read(path):return json.loads(path.read_text(encoding='utf-8'))
def write(path,value):path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
def points(mesh):return [tuple(v.co) for v in mesh.vertices],[tuple(p.vertices) for p in mesh.polygons]


def components(vertices,faces):
    parent=list(range(len(vertices)))
    def find(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]];i=parent[i]
        return i
    for f in faces:
        for i in f[1:]:parent[find(i)]=find(f[0])
    groups={}
    for f in faces:groups.setdefault(find(f[0]),[]).append(f)
    for fs in groups.values():
        ids=sorted({i for f in fs for i in f});remap={j:i for i,j in enumerate(ids)}
        vs=[vertices[i] for i in ids]
        yield vs,[tuple(remap[i] for i in f) for f in fs]


def bounds(v):return [(min(p[k] for p in v),max(p[k] for p in v)) for k in range(3)]


def edit_mesh(name,vertices,faces):
    """Only bounded disconnected solids are removed/cut; other vertices retained."""
    b=MeshBuilder();removed=0
    for vs,fs in components(vertices,faces):
        (xl,xh),(yl,yh),(zl,zh)=bounds(vs)
        remove=False
        if name==OLD+'foottown-metal':
            remove=yl < -29.4 and yh < -29.3 and zl < 5.5 and zh < 5.6
        elif name==OLD+'foottown-roof':
            remove=yl < -29.0 and yh < -28.9 and .05 < zl and zh < 4.5
        elif name==OLD+'stairs-guards':
            remove=xh < -3.90 and zl > 145.0
        elif name in PORTAL_MESH and xh < -8.9 and xl > -9.2 and yl < 5.18 and yh > 3.62 and 145.0 < zl < 147.5:
            require(len(vs)==8 and len(fs)==6,'Portal may cut only pinned wall cuboids')
            # Leave side jamb regions and a header above the opening.
            for ya,yb in ((yl,min(yh,3.62)),(max(yl,5.18),yh)):
                if yb>ya:b.box('mesh',((xl+xh)/2,(ya+yb)/2,(zl+zh)/2),(xh-xl,yb-ya,zh-zl))
            if zh>147.5:
                a,c=max(yl,3.62),min(yh,5.18)
                if c>a:b.box('mesh',((xl+xh)/2,(a+c)/2,(147.5+zh)/2),(xh-xl,c-a,zh-147.5))
            remove=True
        if remove:removed+=1
        else:b.add('mesh',vs,fs)
    require(removed>0,'No bounded edit: '+name)
    return b.groups['mesh'],removed


def open_scene(path):
    import bpy
    bpy.ops.wm.open_mainfile(filepath=str(path),use_scripts=False)
    bpy.context.scene.frame_set(1)


def rotation():
    from mathutils import Matrix
    return Matrix.Rotation(math.radians(geo.ROTATION_DEGREES),4,'Z')


def build(source,out,config):
    import bpy
    from blender_worker import mesh_fingerprint
    open_scene(source)
    require(len(bpy.context.scene.objects)==3361,'Wrong input object count')
    require(bpy.data.collections.get(COLLECTION) is None,'Increment already applied')
    changed={}
    for name,spec in config['tower_objects'].items():
        obj=bpy.data.objects.get(name)
        require(obj and obj.type=='MESH' and mesh_fingerprint(obj.data)==spec['mesh_sha256'],'Pinned tower differs: '+name)
        require(not obj.parent and not obj.constraints and not obj.animation_data,'Unsupported tower transform')
        require(all(abs(obj.matrix_world[r][c]-spec['matrix_world'][r][c])<1e-7 for r in range(4) for c in range(4)),'Pinned tower transform differs')
    for name in CHANGED_MESH:
        obj=bpy.data.objects[name];mesh=obj.data
        require(mesh.users==1 and not mesh.uv_layers and not mesh.shape_keys,'Unsupported edit target: '+name)
        require(not obj.modifiers or (name in PORTAL_MESH and all(m.type=='BEVEL' for m in obj.modifiers)),
                'Unsupported modifiers: '+name)
        require(all(p.material_index==0 and not p.use_smooth for p in mesh.polygons),'Unsupported face attributes')
        data,count=edit_mesh(name,*points(mesh))
        mesh.clear_geometry();mesh.from_pydata(data['vertices'],[],data['faces']);mesh.update()
        changed[name]=count
    collection=bpy.data.collections.new(COLLECTION);bpy.context.scene.collection.children.link(collection)
    collection['otw_feature_id']=FEATURE
    for group,data in geo.geometry().items():
        mat=bpy.data.materials.new(PREFIX+group);mat.use_nodes=True
        color,metal,rough=geo.MATERIALS[group];mat.diffuse_color=color
        shader=mat.node_tree.nodes.get('Principled BSDF')
        for key,val in [('Base Color',color),('Metallic',metal),('Roughness',rough)]:shader.inputs[key].default_value=val
        mesh=bpy.data.meshes.new(PREFIX+group);mesh.from_pydata(data['vertices'],[],data['faces']);mesh.update();mesh.materials.append(mat)
        obj=bpy.data.objects.new(PREFIX+group,mesh);collection.objects.link(obj)
        obj['otw_feature_id']=FEATURE;obj['otw_part_id']='tower-site-v3-'+group
        obj['otw_accuracy']='source-guided relative layout; dimensions and legacy terrain seams inferred'
    for name in set(config['tower_objects'])|ADDED:
        obj=bpy.data.objects[name];obj.matrix_world=rotation()@obj.matrix_world
    bpy.context.view_layer.update()
    # Preserve original unused material datablocks across saving, as in PR61.
    retained=[m.name for m in bpy.data.materials if m.users==0]
    for name in retained:bpy.data.materials[name].use_fake_user=True
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'after.blend'),check_existing=False)
    return dict(ok=True,edited_components=changed,rotated_objects=len(config['tower_objects']),added_objects=sorted(ADDED),retained_unused_materials=retained)


def validate(source,out,config):
    from validate_tower_site_v3 import inspect
    return inspect(source,out,config)


def render(source,out,phase,preview=False):
    from blender_worker import render as scene_render
    cameras=read(ROOT/'areas/tokyo-tower/tower-site-v3-cameras.json')
    if preview:cameras['views']=[v for v in cameras['views'] if v['id'] in ('site-overhead','site-south','roof-equipment','deck-connection')]
    validate_cameras(cameras)
    open_scene(source if phase=='render-before' else out/'after.blend')
    settings=dict(device='OPTIX',width=960 if preview else 1280,height=636 if preview else 848,samples=12 if preview else 32,seed=0)
    result=scene_render(dict(output=str(out),cameras=cameras,settings=settings),phase)
    result['settings']=settings
    result['cameras_sha256']=digest(ROOT/'areas/tokyo-tower/tower-site-v3-cameras.json')
    return result


def main():
    import bpy
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--phase',required=True,choices=['build','validate','render-before','render-after'])
    p.add_argument('--input',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--preview',action='store_true')
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);source=a.input.resolve();out=a.output.resolve()
    out.mkdir(parents=True,exist_ok=True);report=out/(a.phase+'.json');config=read(CONFIG)
    require(not report.exists(),'Refusing to overwrite report')
    require(source!=out/'after.blend' and digest(source)==config['input_sha256'],'Pinned source differs')
    require(bpy.app.version_string=='4.5.1 LTS' and not bpy.context.preferences.filepaths.use_scripts_auto_execute,'Use Blender 4.5.1 with autoexec disabled')
    candidate_hash=digest(out/'after.blend') if a.phase!='build' else None
    if a.phase=='build':
        require(not (out/'after.blend').exists(),'Refusing to overwrite model')
        result=build(source,out,config)
    elif a.phase=='validate':result=validate(source,out,config)
    else:result=render(source,out,a.phase,a.preview)
    require(digest(source)==config['input_sha256'],'Source changed')
    if candidate_hash:require(digest(out/'after.blend')==candidate_hash,'Read-only phase changed candidate')
    result.update(input_sha256=config['input_sha256'],candidate_sha256=digest(out/'after.blend'),source_and_candidate_protected=True,
        blender_version=bpy.app.version_string,code_sha256={name:digest(ROOT/'scripts'/name) for name in
        ['tower_site_v3.py','tower_site_geometry_v3.py','validate_tower_site_v3.py','tower_structure_v1.py','blender_worker.py','review.py']})
    write(report,result);print('OK: '+a.phase)


if __name__=='__main__':main()
