"""Read-only geometry checks plus a disposable, ID-selected review scene."""
from collections import Counter, defaultdict
import argparse
import hashlib
import json
from pathlib import Path
import sys


def topology_extras(vertices, faces):
    """Check duplicate geometric faces and a single closed link at each vertex."""
    keys = [tuple(sorted(tuple(vertices[i]) for i in face)) for face in faces]
    duplicate_faces = len(keys)-len(set(keys))
    links = defaultdict(list)
    for face in faces:
        for i, vertex in enumerate(face):
            links[vertex].append((face[(i+1)%3], face[(i+2)%3]))
    bad = []
    for vertex, pairs in links.items():
        graph = defaultdict(set)
        degree = Counter()
        for a,b in pairs:
            graph[a].add(b); graph[b].add(a)
            degree[a]+=1; degree[b]+=1
        remaining=set(graph); components=0
        while remaining:
            components+=1; stack=[remaining.pop()]
            while stack:
                for neighbor in graph[stack.pop()] & remaining:
                    remaining.remove(neighbor); stack.append(neighbor)
        if components != 1 or any(n != 2 for n in degree.values()):
            bad.append(vertex)
    return {'duplicate_geometric_faces':duplicate_faces,
            'vertex_links_checked':len(links),'nonmanifold_vertex_links':len(bad)}


def main():
    import bpy
    import numpy as np
    from mathutils import Vector
    ROOT=Path(__file__).resolve().parents[1]
    sys.path.insert(0,str(ROOT/'scripts'))
    import data221_af7335da_mesh as mesh
    import data221_af7335da_worker as worker
    import blender_worker as review
    parser=argparse.ArgumentParser()
    parser.add_argument('--index',type=Path,required=True)
    parser.add_argument('--review',type=Path,required=True)
    parser.add_argument('--reference',type=Path,required=True)
    parser.add_argument('--phase',choices=['check','reopen'],default='check')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    out=args.review.resolve(); index=json.loads(args.index.read_text(encoding='utf8'))
    if not index['ok'] or index['candidate_count'] != 1:
        raise ValueError('Expected one index candidate')
    row=index['candidates'][0]; gid=row['gml_id']
    if gid != mesh.FEATURE: raise ValueError('Only the reserved feature is supported')
    selection=out/'selected-neighborhood.blend'
    if args.phase=='reopen':
        bpy.ops.wm.open_mainfile(filepath=str(selection),use_scripts=False)
        matches=[o for o in bpy.context.scene.objects if o.get('gml_id')==gid]
        if len(matches)!=1 or bpy.context.view_layer.objects.active!=matches[0]:
            raise ValueError('Saved active feature selection lost')
        if [o.name for o in bpy.context.selected_objects]!=[matches[0].name]:
            raise ValueError('Saved selected set differs')
        if worker.stats(matches[0])['vertices']!=235:
            raise ValueError('Wrong selected model')
        worker.write(out/'selection-reopen.json',{'ok':True,'gml_id':gid,
                     'active_object':matches[0].name,'selected_objects':[o.name for o in bpy.context.selected_objects],
                     'saved_scene_meshes':sum(o.type=='MESH' for o in bpy.context.scene.objects)})
        return
    if selection.exists(): raise ValueError('Choose a fresh review directory')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(out/'after-neighborhood.blend'),link=False) as (src,dst):
        dst.objects=list(src.objects)
    for obj in dst.objects:bpy.context.scene.collection.objects.link(obj)
    # Use the exact identity/property returned by the evidence index.
    key=row['scene_lookup']['mori_after_property']
    value=row['scene_lookup']['mori_after_value']
    matches=[o for o in bpy.context.scene.objects if o.get(key)==value]
    if len(matches)!=1: raise ValueError('Index does not select exactly one produced model')
    target=matches[0]
    actual=worker.records(target)
    with bpy.data.libraries.load(str(args.reference/'before-neighborhood.blend'),link=False) as (src,ref):
        ref.objects=[mesh.AGGREGATE]
    original=ref.objects[0]
    expected=[r for r in worker.records(original) if r['batch']==row['batch_id']]
    if actual!=expected: raise ValueError('Original expanded geometry/UV/material/batch differ')
    original_materials=json.loads((args.reference/'city-before.json').read_text(encoding='utf8'))['objects'][mesh.AGGREGATE]['materials']
    if [review.material_fingerprint(m) for m in target.data.materials] != original_materials:
        raise ValueError('Material definitions differ')
    stat=worker.stats(target); mesh.require_closed(stat)
    extras=topology_extras([tuple(v.co) for v in target.data.vertices],
                          [tuple(f.vertices) for f in target.data.polygons])
    if extras['duplicate_geometric_faces'] or extras['nonmanifold_vertex_links']:
        raise ValueError('Duplicate face or nonmanifold vertex')
    xyz=np.array([r['points'] for r in expected])
    normals=np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0]); normals/=np.linalg.norm(normals,axis=1)[:,None]
    stored=np.array([tuple(f.normal) for f in target.data.polygons])
    stored/=np.linalg.norm(stored,axis=1)[:,None]
    cosine=np.einsum('ij,ij->i',normals,stored)
    if cosine.min()<.999999: raise ValueError('Saved face normal differs from source winding')
    # Describe available high facade evidence for the next visual-work decision.
    centers=xyz.mean(axis=1); neighbors=defaultdict(list)
    for face in target.data.polygons:
        for a,b in zip(face.vertices,list(face.vertices)[1:]+list(face.vertices)[:1]):
            neighbors[tuple(sorted((a,b)))].append(face.index)
    shallow=[]
    for edge,incident in neighbors.items():
        if len(incident)!=2:continue
        a,b=incident
        if min(centers[a,2],centers[b,2])<30 or max(abs(normals[a,2]),abs(normals[b,2]))>.05:continue
        angle=float(np.degrees(np.arccos(np.clip(np.dot(normals[a],normals[b]),-1,1))))
        if .1<angle<30:shallow.append(angle)
    bpy.data.objects.remove(original,do_unlink=True)
    for obj in bpy.context.scene.objects:obj.select_set(False)
    target.select_set(True); bpy.context.view_layer.objects.active=target
    # Save an explicit camera and useful viewport, without touching any normal registration.
    scene=bpy.context.scene; camera_data=bpy.data.cameras.new('ID review camera')
    camera=bpy.data.objects.new('ID review camera',camera_data);scene.collection.objects.link(camera);scene.camera=camera
    center=Vector((-460,404,118));camera.location=center+Vector((360,-140,140))
    camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    camera_data.type='ORTHO';camera_data.ortho_scale=310;camera_data.clip_end=2000
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.region_3d.view_location=center
                area.spaces.active.region_3d.view_distance=350
                area.spaces.active.region_3d.view_rotation=camera.rotation_euler.to_quaternion()
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(selection),compress=True)
    worker.write(out/'additional-geometry-selection.json',{'ok':True,
        'index_sha256':hashlib.sha256(args.index.read_bytes()).hexdigest(),
        'selected_gml_id':gid,'index_property_used':key,'selected_object':target.name,
        'candidate_matches':len(matches),'face_count':len(actual),'expanded_face_data_identical_to_original':True,
        'uv_material_batch_and_flat_shading_identical':True,'material_definitions_identical':True,
        'indexed_surface':stat,'additional_topology':extras,
        'minimum_normal_cosine_to_original':float(cosine.min()),
        'maximum_normal_angle_degrees':float(np.degrees(np.arccos(np.clip(cosine,-1,1))).max()),
        'normal_comparison_faces':len(actual),'self_intersections_tested':False,
        'watertight_solid_certified':False,
        'next_visual_candidate_evidence':{'high_vertical_facade_edges_with_0_1_to_30_degree_dihedral':len(shallow),
          'dihedral_range_degrees':[min(shallow),max(shallow)] if shallow else None,
          'interpretation':'Candidate for a reversible normal-smoothing comparison only; preserve roof/podium creases, UVs and source vertices. Does not establish real facade curvature.'},
        'selection_scene':'selected-neighborhood.blend',
        'limits':['Closed consistent indexed topology plus vertex-link checks; geometric self-intersections and suitability as a watertight solid are not certified.',
                  'Selection proof uses the extracted data221 neighborhood, not a UI interaction in the normal city workspace.']})


if __name__=='__main__':main()
