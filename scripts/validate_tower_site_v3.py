# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Independent saved-scene inspection; does not call geometry production."""
import json
from collections import Counter
from pathlib import Path
from tower_site_v3 import (ROOT,PREFIX,COLLECTION,CHANGED_MESH,ADDED,OLD,read,
                           open_scene,points,components,bounds,rotation)
from validate_tower_structure import check_mesh,convex_intersects_box,require,near


def overlap(a,b):return all(x[1]>y[0]+1e-5 and x[0]<y[1]-1e-5 for x,y in zip(a,b))


def saved_geometry():
    import bpy
    parts={};stats={}
    for name in sorted(ADDED):
        stats[name],parts[name]=check_mesh(*points(bpy.data.objects[name].data),((-70,40),(-72,30),(-.1,149)))
    # Sampled surfaces use actual saved object raycasts in construction space.
    from mathutils import Vector
    paving=bpy.data.objects[PREFIX+'site-paving']
    for y,z in ((-29.1,4.4),(-33,4.4),(-36,4.4),(-55,2.92),(-69.99,.481627)):
        hit,co,normal,index=paving.ray_cast(Vector((0,y,10)),Vector((0,0,-1)))
        require(hit and abs(co.z-z)<.004,'Broken saved south grade at '+str(y))
    bridge=bpy.data.objects[PREFIX+'deck-bridge']
    for x in (-9.6,-9.1,-8,-6,-4,-3.7):
        hit,co,normal,index=bridge.ray_cast(Vector((x,4.4,146)),Vector((0,0,-1)))
        require(hit and near(co.z,145.1),'Missing deck connection floor')
    # Source landing and destination passenger-floor support, outside the new bridge.
    stairs=bpy.data.objects[OLD+'stairs-treads']
    require(stairs.ray_cast(Vector((-3.3,4.4,145.5)),Vector((0,0,-1)))[0],'Missing original last landing')
    supports=[]
    for o in bpy.context.scene.objects:
        if o.type=='MESH' and o.name.startswith('Photo based main deck / carpet'):
            hit,co,normal,index=o.ray_cast(Vector((-9.7,4.4,146)),Vector((0,0,-1)))
            if hit and abs(co.z-145.1)<.01:supports.append(o.name)
    require(supports,'Bridge does not overlap passenger-floor finish')
    # Reject blockers in the full pedestrian-width route, including original
    # walls, steel and furniture. Work in the shared construction frame.
    path=((-9.65,-3.65),(3.72,5.08),(145.20,147.35))
    roof=((-12,-4.8),(3.1,5.7),(16.30,18.4))
    blockers=[]
    names=set(read(ROOT/'areas/tokyo-tower/tower-site-v3-input.json')['tower_objects'])|ADDED
    # Check the apron against the saved surrounding city, including buildings
    # outside the tower change set. Sampling is not a full collision proof.
    dg=bpy.context.evaluated_depsgraph_get();site_samples=0
    for x in range(-36,37,3):
        for y in range(-69,-29,3):
            if not paving.ray_cast(Vector((x,y,10)),Vector((0,0,-1)))[0]:continue
            origin=rotation()@Vector((x,y,80));reached=False
            for _ in range(64):
                hit,co,normal,index,obj,matrix=bpy.context.scene.ray_cast(dg,origin,Vector((0,0,-1)),distance=90)
                if not hit:break
                if obj.name==paving.name:reached=True;break
                if obj.name not in names and not obj.hide_render:break
                origin=co+Vector((0,0,-.005))
            require(reached,'Existing city obstructs apron sample '+str((x,y)))
            site_samples+=1
    for o in bpy.context.scene.objects:
        if o.type!='MESH' or o.hide_render or o.name not in names:continue
        vs,fs=points(o.data)
        if not vs:continue
        to_construction=rotation().inverted()@o.matrix_world
        vs=[tuple(to_construction@Vector(v)) for v in vs]
        for volume,label in ((path,'deck route'),(roof,'roof approach')):
            if not overlap(bounds(vs),volume):continue
            for cv,cf in components(vs,fs):
                if not overlap(bounds(cv),volume):continue
                # Narrow phase for closed boxes/beams in all edited structures.
                # Generic inherited surfaces receive a BVH overlap/raycast check
                # below only where their component envelope meets the route.
                try:
                    _,solids=check_mesh(cv,cf,((-200,200),(-200,200),(-1,334)))
                    if any(convex_intersects_box(p,volume) for p in solids):blockers.append((label,o.name,bounds(cv)))
                except ValueError as exc:
                    blockers.append((label,o.name,'uninspectable intersecting component: '+str(exc)))
    require(not blockers,'Route obstruction: '+json.dumps(blockers[:8]))
    # No old south stairs/outer landing handrail remains in the replaced apron.
    metal=bpy.data.objects[OLD+'foottown-metal'].data
    require(not any(b[1][0]<-29.4 and b[1][1]<-29.3 and b[2][0]<5.5 and b[2][1]<5.6
                    for b in (bounds(v) for v,f in components(*points(metal)))),'Old south stair metal remains')
    return dict(meshes=stats,south_threshold_m=4.4,south_lot_m=2.92,deck_floor_m=145.1,
        passenger_floor_objects=supports,route_clear_width_m=1.36,route_checked_height_m=2.15,
        roof_approach_clear=True,site_extent_is_local_inferred_seam=True,unobstructed_city_apron_samples=site_samples)


def protected(config):
    import tower_foottown_v2 as detail
    from validate_tower_foottown import protected_metadata
    old=(detail.CHANGED,detail.ADDED,detail.COLLECTION)
    try:
        detail.CHANGED=set(config['tower_objects']);detail.ADDED=ADDED;detail.COLLECTION=COLLECTION
        return protected_metadata()
    finally:detail.CHANGED,detail.ADDED,detail.COLLECTION=old


def retained_components():
    """Fingerprint original solids outside the independently bounded cut volumes."""
    import bpy
    volumes={
        OLD+'foottown-metal':((-15,9),(-32,-29.3),(-.01,5.6)),
        OLD+'foottown-roof':((-15,9),(-32,-28.9),(.05,4.5)),
        OLD+'stairs-guards':((-4.1,-3.90),(2.8,6),(145,147)),
    }
    result={}
    for name in CHANGED_MESH:
        volume=volumes.get(name,((-9.2,-8.9),(3.62,5.18),(145,147.5)))
        signatures=[]
        for vs,fs in components(*points(bpy.data.objects[name].data)):
            if not overlap(bounds(vs),volume):
                signatures.append((tuple(vs),tuple(fs)))
        result[name]=Counter(signatures)
    return result


def inspect(source,out,config):
    import bpy
    from blender_worker import validate,mesh_fingerprint,material_fingerprint
    from review import compare_reports
    features=read(ROOT/'areas/tokyo-tower/foottown-v2-features.json')
    open_scene(source)
    before=validate({'features':features});meta=protected(config)
    retained=retained_components()
    def modifier_state():
        return {n:[{key:getattr(m,key) for key in ('name','type','show_render','show_viewport',
                    'width','segments','limit_method','angle_limit','offset_type','affect') if hasattr(m,key)}
                   for m in bpy.data.objects[n].modifiers] for n in config['tower_objects']}
    modifiers=modifier_state()
    shaders={m.name:material_fingerprint(m) for m in bpy.data.materials}
    def identity(o):
        return ({k:str(o[k]) for k in o.keys()},sorted(c.name for c in o.users_collection),
                o.hide_render,o.hide_viewport,o.hide_get())
    old_props={n:identity(bpy.data.objects[n]) for n in config['tower_objects']}
    open_scene(out/'after.blend')
    after=validate({'features':features})
    changed=compare_reports(before,after,set(config['tower_objects']),ADDED)
    new_retained=retained_components()
    require(all(not (parts-new_retained[name]) for name,parts in retained.items()),
            'A target solid outside the permitted opening/stair edits changed')
    require(modifier_state()==modifiers,'Tower modifier settings changed')
    require(protected(config)==meta,'Protected object flags or metadata changed')
    require(all(n in bpy.data.materials and material_fingerprint(bpy.data.materials[n])==h for n,h in shaders.items()),'Original shader changed')
    from mathutils import Matrix
    r=rotation()
    for name,spec in config['tower_objects'].items():
        o=bpy.data.objects[name]
        expected=r@Matrix(spec['matrix_world'])
        require(not o.parent and not o.constraints and not o.animation_data,'Unexpected transform dependency')
        require(all(abs(o.matrix_basis[i][j]-expected[i][j])<2e-5 for i in range(4) for j in range(4)),'Unexpected stored tower transform: '+name)
        if name not in CHANGED_MESH:require(mesh_fingerprint(o.data)==spec['mesh_sha256'],'Retained tower geometry changed: '+name)
        require(old_props[name]==identity(o),'Tower identity or visibility changed')
    # Disabled objects expose a stale world cache after reopening in Blender.
    # Verify their actual evaluated transform too, temporarily enabling them in
    # this disposable read-only process; restore visibility and never save.
    evaluation=bpy.data.collections.new('OTW validation transform evaluation')
    bpy.context.scene.collection.children.link(evaluation)
    hidden={n:(bpy.data.objects[n].hide_viewport,bpy.data.objects[n].hide_get()) for n in config['tower_objects']}
    try:
        for name in hidden:
            o=bpy.data.objects[name];evaluation.objects.link(o);o.hide_viewport=False;o.hide_set(False)
        bpy.context.view_layer.update()
        for name,spec in config['tower_objects'].items():
            o=bpy.data.objects[name];expected=r@Matrix(spec['matrix_world'])
            require(all(abs(o.matrix_world[i][j]-expected[i][j])<2e-5 for i in range(4) for j in range(4)),'Unexpected evaluated tower transform: '+name)
    finally:
        for name,(viewport,layer) in hidden.items():
            o=bpy.data.objects[name];o.hide_viewport=viewport;o.hide_set(layer)
        bpy.data.collections.remove(evaluation)
        bpy.context.view_layer.update()
    for name in ADDED:
        o=bpy.data.objects[name]
        require(not o.hide_render and o.visible_get() and len(o.data.materials)==1,'Invisible or unshaded addition')
        require({c.name for c in o.users_collection}=={COLLECTION},'Wrong new collection')
        require(all(abs(o.matrix_world[i][j]-r[i][j])<2e-6 for i in range(4) for j in range(4)),'New part not registered')
    geometry=saved_geometry()
    return dict(ok=True,changed_objects=changed,added_objects=sorted(ADDED),protected_objects=3361-len(config['tower_objects']),
        retained_tower_meshes=len(config['tower_objects'])-len(CHANGED_MESH),original_shaders_unchanged=True,
        protected_metadata_unchanged=True,geometry=geometry,warnings=after['warnings'],
        limits=after['limits']+['OSM-guided azimuth is not a surveyed registration.',
         'Site apron borders and deck passage are model-fit estimates; no complete terrain/interior survey.',
         'Upper framing schedule and rescue heights remain unverified and unchanged.'])
