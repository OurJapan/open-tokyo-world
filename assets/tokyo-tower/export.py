# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Extract a pinned, licensed tower subset; never modify the input city scene."""
import argparse,hashlib,json,subprocess,sys,time,math
from pathlib import Path
HERE=Path(__file__).resolve().parent
VIEWS=[('tower',(0,0,165),(430,-550,245),520),('glass-floor',(-6,-12.25,145.1),(3.5,3,2.5),28),('interior',(-5,-12,146.3),(16,1,.5),22)]

def digest_file(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def source_check(path,record):
    if path.stat().st_size!=record['bytes'] or digest_file(path)!=record['sha256']:raise ValueError('Wrong legacy baseline')

def material_check(material,seen=None):
    if not material or not material.use_nodes:raise ValueError('Expected procedural material')
    seen=set() if seen is None else seen
    def walk(tree):
        if tree.as_pointer() in seen:return
        seen.add(tree.as_pointer())
        if tree.animation_data:raise ValueError('Animated material dependency')
        for n in tree.nodes:
            if getattr(n,'image',None):raise ValueError('Image dependency in tower material')
            if n.type=='SCRIPT':raise ValueError('Shader script dependency')
            if getattr(n,'node_tree',None):walk(n.node_tree)
    walk(material.node_tree)

def mesh_hash(obj):
    import struct
    h=hashlib.sha256()
    for v in obj.data.vertices:h.update(struct.pack('<3f',*v.co))
    for f in obj.data.polygons:h.update(struct.pack('<I',len(f.vertices))+struct.pack('<'+'I'*len(f.vertices),*f.vertices)+struct.pack('<I',f.material_index))
    return h.hexdigest()

def build(source,out,scope):
    import bpy
    from mathutils import Vector
    bpy.ops.wm.open_mainfile(filepath=str(source),use_scripts=False)
    original=bpy.context.scene;original.frame_set(1);graph=bpy.context.evaluated_depsgraph_get()
    scene=bpy.data.scenes.new('OurJapan Tokyo Tower licensed subset')
    records={}
    for part in scope['parts']:
        o=original.objects.get(part['object'])
        if not o or o.type!='MESH' or len(o.data.vertices)!=part['vertices']:raise ValueError('Changed source part')
        if o.hide_render:raise ValueError('Selected part is hidden: '+o.name)
        for m in o.data.materials:material_check(m)
        mesh=bpy.data.meshes.new_from_object(o.evaluated_get(graph),preserve_all_data_layers=True,depsgraph=graph)
        mesh.transform(o.matrix_world);mesh.update()
        copy=bpy.data.objects.new(o.name+' / licensed',mesh);scene.collection.objects.link(copy)
        copy['otw_feature_id']=scope['feature_id'];copy['source_object']=o.name;copy['license']='CC-BY-4.0'
        records[copy.name]={'source_object':o.name,'mesh_sha256':mesh_hash(copy),'vertices':len(mesh.vertices),'polygons':len(mesh.polygons)}
    camera=bpy.data.objects.new('Tower review camera',bpy.data.cameras.new('Tower review camera'));scene.collection.objects.link(camera);scene.camera=camera;camera.data.clip_end=2000;camera.data.clip_start=.02
    sun=bpy.data.objects.new('Tower review sun',bpy.data.lights.new('Tower review sun','SUN'));scene.collection.objects.link(sun);sun.data.energy=3;sun.rotation_euler=(.4,-.4,-.3)
    world=bpy.data.worlds.new('Tower neutral world');world.use_nodes=True;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.6,.68,.78,1);scene.world=world
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=16;scene.cycles.seed=0;scene.render.resolution_x=960;scene.render.resolution_y=720;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    (out/'parts.json').write_text(json.dumps(records,indent=2)+'\n')
    _,target,offset,scale=VIEWS[0];target=Vector(target)
    camera.location=target+Vector(offset);camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=scale
    bpy.data.libraries.write(str(out/'tower.blend'),{scene},compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(out/'tower.blend'),use_scripts=False)
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'tower.blend'),compress=True)

def validate(out,scope):
    import bpy,numpy as np
    from mathutils import Vector
    bpy.ops.wm.open_mainfile(filepath=str(out/'tower.blend'),use_scripts=False)
    scene=bpy.context.scene;meshes=[o for o in scene.objects if o.type=='MESH'];parts=json.loads((out/'parts.json').read_text())
    if len(meshes)!=77 or len(bpy.data.scenes)!=1:raise ValueError('Wrong isolated scene count')
    if bpy.data.images or bpy.data.libraries or bpy.data.texts or bpy.data.sounds:raise ValueError('Unexpected external/legacy dependency')
    if {o.get('source_object') for o in meshes}!={p['object'] for p in scope['parts']}:raise ValueError('Part coverage mismatch')
    triangles=0
    for o in meshes:
        if o.modifiers or o.constraints or o.parent or o.animation_data:raise ValueError('Unbaked object dependency')
        if mesh_hash(o)!=parts[o.name]['mesh_sha256']:raise ValueError('Saved mesh mismatch')
        if not all(math.isfinite(c) for v in o.data.vertices for c in v.co):raise ValueError('Invalid vertex')
        for m in o.data.materials:material_check(m)
        o.data.calc_loop_triangles();triangles+=len(o.data.loop_triangles)
    pictures={}
    for name,target,offset,value in VIEWS:
        target=Vector(target);cam=scene.camera;cam.location=target+Vector(offset);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO' if name=='tower' else 'PERSP'
        if name=='tower':cam.data.ortho_scale=value
        else:cam.data.lens=value
        scene.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
        im=bpy.data.images.load(scene.render.filepath);px=np.array(im.pixels[:]);
        if tuple(im.size)!=(960,720) or not np.isfinite(px).all() or px.reshape(-1,4)[:,:3].std()<.01:raise ValueError('Invalid preview')
        bpy.data.images.remove(im);pictures[name]=digest_file(out/(name+'.png'))
    (out/'validation.json').write_text(json.dumps({'ok':True,'blender':bpy.app.version_string,'meshes':len(meshes),'triangles':triangles,'saved_reopened':True,'external_images':0,'libraries':0,'texts':0,'sounds':0,'parts_match':True,'renders':pictures,'limitations':['Not full procedural rebuild','No real-world accuracy or complete topology certification','Modifier evaluation baked at frame 1']},indent=2)+'\n')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);ap.add_argument('--blender',type=Path);ap.add_argument('--phase',choices=['build','validate'])
    a=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None);source=a.input.resolve();out=a.output.resolve();scope=json.loads((HERE/'provenance.json').read_text(encoding='utf8'))
    if a.phase:
        import bpy
        if bpy.app.version!=(4,5,1):raise ValueError('Blender 4.5.1 required')
        if a.phase=='build':build(source,out,scope)
        else:validate(out,scope)
        return
    if not a.blender or not a.blender.is_file():ap.error('Supply Blender executable')
    source_check(source,scope['baseline']);out.mkdir(parents=True,exist_ok=False);record={'ok':False,'started':time.time()}
    try:
        for name,path in {'ASSET-LICENSE.md':HERE/'ASSET-LICENSE.md','NOTICE.md':HERE/'NOTICE.md','provenance.json':HERE/'provenance.json','MIT-LICENSE.txt':HERE.parents[1]/'MIT-LICENSE.txt'}.items():(out/name).write_bytes(path.read_bytes())
        for phase in ['build','validate']:
            with (out/(phase+'.log')).open('w',encoding='utf8') as log:subprocess.run([str(a.blender.resolve()),'--factory-startup','--background','--disable-autoexec','--python-exit-code','1','--python',str(Path(__file__).resolve()),'--','--input',str(source),'--output',str(out),'--phase',phase],stdout=log,stderr=subprocess.STDOUT,timeout=600,check=True)
        source_check(source,scope['baseline']);record['validation']=json.loads((out/'validation.json').read_text());record['ok']=True;record['source_unchanged']=True;record['bytes']=(out/'tower.blend').stat().st_size
        (out/'review.html').write_text('<!doctype html><meta charset="utf-8"><title>東京タワー許諾対象の切り出し</title><style>body{max-width:1000px;margin:32px auto;background:#17212b;color:white;font:18px sans-serif}img{width:100%}a{color:#9df}</style><h1>東京タワー：許諾対象の切り出し</h1><p>既存モデルを変更せず、対象部品の評価済み形状と手続き的材質を独立ファイルへ切り出しました。新しい造形や完全なソース再生成ではありません。</p>'+''.join('<h2>'+n+'</h2><img src="'+n+'.png">' for n,_,_,_ in VIEWS)+'<p>© 2026 ark4ez / OurJapan、対象の独自モデル・材質・本プレビューはCC BY 4.0。寸法・内装・窓の傾斜は推定を含みます。</p><p><a href="ASSET-LICENSE.md">許諾</a> / <a href="NOTICE.md">出典</a> / <a href="provenance.json">対象</a> / <a href="validation.json">検証</a></p>',encoding='utf8')
    except Exception as exc:record['error']=str(exc);raise
    finally:
        record['elapsed_seconds']=time.time()-record['started'];record['exporter_sha256']=digest_file(Path(__file__));(out/'run.json').write_text(json.dumps(record,indent=2)+'\n')

if __name__=='__main__':main()
