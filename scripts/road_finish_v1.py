# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Local road finish candidate: original geometry and outside-region shader retained."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
TARGETS={'asphalt 15s road detail':'asphalt','asphalt_7 unified road':'asphalt','gutter 15s road detail':'gutter','parking mapped land use':'parking','pavement_0 unified road':'pavement','pavement_7 unified road':'pavement','paint_0 unified road':'paint','paint_7 unified road':'paint'}
SOURCE_SHA='df71be6c9b2e606a7ec277f15285bc92123a712d0069d7c413ab5d210d7cc9c3'
INNER=150.;OUTER=220.
def write(p,r):p.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8388608),b''):h.update(b)
 return h.hexdigest()
def snapshot():
 import bpy,blender_worker as worker,tower_foottown_v2 as detail
 from validate_tower_foottown import protected_metadata
 empty={o.name:'inherited empty mesh' for o in bpy.context.scene.objects if o.type=='MESH' and not len(o.data.vertices)}
 result=worker.validate({'features':{'features':[],'legacy_empty_objects':empty}})
 assert result['ok'],result['errors']
 saved=detail.CHANGED,detail.ADDED;detail.CHANGED=set();detail.ADDED=set()
 try:result['metadata']=protected_metadata()
 finally:detail.CHANGED,detail.ADDED=saved
 result['materials']={m.name:worker.material_fingerprint(m) for m in bpy.data.materials}
 result['slots']={o.name:[m.name if m else None for m in o.data.materials] for o in bpy.data.objects if o.type=='MESH'}
 result['data_counts']={k:len(getattr(bpy.data,k)) for k in ['objects','meshes','materials','images','cameras','lights','actions','collections']}
 result['lights']={o.name:[o.data.type,list(o.data.color),o.data.energy] for o in bpy.data.objects if o.type=='LIGHT'}
 return json.loads(json.dumps(result,ensure_ascii=False))

def finish(original,kind):
 import bpy
 mat=original.copy();mat.name='OTW Road finish v1 / '+original.name;mat['otw_finish_kind']=kind
 nt=mat.node_tree;nodes=nt.nodes;links=nt.links
 def node(type,name):n=nodes.new(type);n.name='OTW finish / '+name;return n
 output=next(n for n in nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output)
 assert len(output.inputs['Surface'].links)==1
 source=output.inputs['Surface'].links[0].from_socket
 geo=node('ShaderNodeNewGeometry','world position');xyz=node('ShaderNodeSeparateXYZ','XY');links.new(geo.outputs['Position'],xyz.inputs[0]);xy=node('ShaderNodeCombineXYZ','ground coordinates')
 links.new(xyz.outputs['X'],xy.inputs['X']);links.new(xyz.outputs['Y'],xy.inputs['Y'])
 length=node('ShaderNodeVectorMath','radius');length.operation='LENGTH';links.new(xy.outputs[0],length.inputs[0])
 mask=node('ShaderNodeMapRange','bounded finish');mask.clamp=True;mask.inputs['From Min'].default_value=INNER;mask.inputs['From Max'].default_value=OUTER;mask.inputs['To Min'].default_value=1.;mask.inputs['To Max'].default_value=0.;links.new(length.outputs['Value'],mask.inputs['Value'])
 shader=node('ShaderNodeBsdfPrincipled','surface');shader.inputs['Roughness'].default_value={'asphalt':.84,'parking':.84,'pavement':.78,'gutter':.82,'paint':.68}[kind]
 noise=node('ShaderNodeTexNoise','fine aggregate');noise.inputs['Scale'].default_value={'asphalt':150.,'parking':150.,'pavement':90.,'gutter':75.,'paint':120.}[kind];noise.inputs['Detail'].default_value=2.;links.new(geo.outputs['Position'],noise.inputs['Vector'])
 ramp=node('ShaderNodeValToRGB','tone');colors={'asphalt':(.035,.052),'parking':(.042,.061),'pavement':(.19,.23),'gutter':(.13,.17),'paint':(.65,.78)}[kind]
 for e,c in zip(ramp.color_ramp.elements,colors):e.color=(c,c,c,1)
 links.new(noise.outputs['Fac'],ramp.inputs[0]);links.new(ramp.outputs['Color'],shader.inputs['Base Color'])
 bump=node('ShaderNodeBump','microtexture');bump.inputs['Strength'].default_value=.25;bump.inputs['Distance'].default_value=.0015 if kind in ['asphalt','parking'] else .0008;links.new(noise.outputs['Fac'],bump.inputs['Height'])
 if kind in ['pavement','gutter']:
  brick=node('ShaderNodeTexBrick','paving joints');links.new(geo.outputs['Position'],brick.inputs['Vector']);brick.inputs['Scale'].default_value=1.;brick.inputs['Brick Width'].default_value=.6 if kind=='pavement' else .5;brick.inputs['Row Height'].default_value=.3 if kind=='pavement' else .25;brick.inputs['Mortar Size'].default_value=.006 if kind=='pavement' else .003;brick.inputs['Mortar Smooth'].default_value=.003
  brick.inputs['Color1'].default_value=(colors[0],colors[0],colors[0],1);brick.inputs['Color2'].default_value=(colors[1],colors[1],colors[1],1);brick.inputs['Mortar'].default_value=(.11,.11,.11,1) if kind=='pavement' else (.10,.10,.10,1)
  links.new(brick.outputs['Color'],shader.inputs['Base Color'])
  joint=node('ShaderNodeBump','recessed joints');joint.invert=True;joint.inputs['Strength'].default_value=.35;joint.inputs['Distance'].default_value=.002;links.new(brick.outputs['Fac'],joint.inputs['Height']);links.new(bump.outputs['Normal'],joint.inputs['Normal']);links.new(joint.outputs['Normal'],shader.inputs['Normal'])
 else:links.new(bump.outputs['Normal'],shader.inputs['Normal'])
 mix=node('ShaderNodeMixShader','retain outside shader');links.new(mask.outputs['Result'],mix.inputs[0]);links.new(source,mix.inputs[1]);links.new(shader.outputs[0],mix.inputs[2]);links.new(mix.outputs[0],output.inputs['Surface'])
 return mat

def main():
 import bpy
 parser=argparse.ArgumentParser();parser.add_argument('--phase',required=True,choices=['build','validate','render-before','render-after']);parser.add_argument('--input',required=True);parser.add_argument('--output',required=True);parser.add_argument('--preview',action='store_true');a=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);src=Path(a.input).resolve();out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True)
 assert digest(src)==SOURCE_SHA,'Input hash differs'
 bpy.ops.wm.open_mainfile(filepath=str(src if a.phase in ['build','render-before'] else out/'after.blend'))
 if a.phase=='build':
  assert not any(m.name.startswith('OTW Road finish v1 /') for m in bpy.data.materials),'Already applied'
  before=snapshot();write(out/'baseline.json',before);created={};assignments={}
  for name,kind in TARGETS.items():
   o=bpy.data.objects[name];assert len(o.data.materials)==1;old=o.data.materials[0];key=old.name
   if key not in created:created[key]=finish(old,kind)
   o.data.materials[0]=created[key]
   # Keep the immutable original datablock referenced through an unused slot.
   # Otherwise Blender drops zero-user originals when saving the candidate.
   o.data.materials.append(old);assignments[name]=created[key].name
  bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(out/'after.blend'),compress=True)
  write(out/'build.json',{'ok':True,'source_sha256':SOURCE_SHA,'assignments':assignments,'new_materials':{n:m.name for n,m in created.items()},'region_m':[INNER,OUTER],'geometry_changes':0,'code_sha256':digest(Path(__file__))})
 elif a.phase=='validate':
  before=json.loads((out/'baseline.json').read_text(encoding='utf-8'));after=snapshot();build=json.loads((out/'build.json').read_text(encoding='utf-8'))
  write(out/'saved-snapshot.json',after)
  assert before['metadata']==after['metadata'],'Object metadata changed';assert before['assets']==after['assets'],'Asset dependencies changed';assert before['counts']==after['counts'],'Geometry counts changed';assert before['lights']==after['lights']
  for name,entry in before['objects'].items():
   new=after['objects'][name];want=dict(entry)
   if name in TARGETS:want['materials']=new['materials']
   assert new==want,'Unexpected object change: '+name
  for name,fp in before['materials'].items():assert after['materials'][name]==fp,'Original material changed: '+name
  for name,slots in before['slots'].items():assert after['slots'][name]==([build['assignments'][name],slots[0]] if name in TARGETS else slots),'Unexpected slots: '+name
  for kind,count in before['data_counts'].items():assert after['data_counts'][kind]==count+(len(build['new_materials']) if kind=='materials' else 0)
  for name in build['new_materials'].values():
   m=bpy.data.materials[name];mask=m.node_tree.nodes['OTW finish / bounded finish'];assert mask.clamp and mask.inputs['From Min'].default_value==INNER and mask.inputs['From Max'].default_value==OUTER
   output=next(n for n in m.node_tree.nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output);mix=output.inputs['Surface'].links[0].from_node;assert mix.name=='OTW finish / retain outside shader';assert mix.inputs[1].is_linked and mix.inputs[2].is_linked
  assert digest(src)==SOURCE_SHA
  write(out/'validation.json',{'ok':True,'objects':len(after['objects']),'material_slot_changes':len(TARGETS),'new_materials':len(build['new_materials']),'unchanged_geometry':True,'source_unchanged':True,'outside_region_uses_original_shader':True,'region_m':[INNER,OUTER],'warnings':after['warnings'],'limitations':['Surface finish is an artistic approximation, not a survey or material measurement.','No road geometry or new markings are introduced.','Existing shader fingerprint limits apply.']})
 else:
  from blender_worker import render
  cameras=json.loads((ROOT/'areas/tokyo-tower/road-finish-v1-cameras.json').read_text(encoding='utf-8'))
  if a.preview:cameras['views']=[v for v in cameras['views'] if v['id'] in ['south-road-vehicle','west-road-vehicle']]
  settings={'width':640 if a.preview else 1280,'height':424 if a.preview else 848,'samples':16 if a.preview else 32,'seed':0,'device':'OPTIX'}
  write(out/(a.phase+'.json'),render({'output':str(out),'cameras':cameras,'settings':settings},a.phase.replace('render-','')))
 assert digest(src)==SOURCE_SHA,'Source changed'
if __name__=='__main__':main()
