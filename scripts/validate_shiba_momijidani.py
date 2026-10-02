"""Inspect the saved Shiba candidate in an independent, read-only Blender process.

This checks saved geometry directly; it never calls the geometry generator.
Existing-object fingerprints are checked separately by scripts/review.py.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import platform
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import shiba_momijidani_v1 as shiba

EPS = 2e-5
ROADS = ('asphalt 15s road detail', 'gutter 15s road detail',
         'pavement_0 unified road', 'asphalt_7 unified road', 'pavement_7 unified road')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def edge_distance(point, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    length = dx*dx+dy*dy
    t = max(0., min(1., ((point[0]-a[0])*dx+(point[1]-a[1])*dy)/length)) if length else 0.
    return math.hypot(point[0]-a[0]-t*dx, point[1]-a[1]-t*dy)


def ring_distance(point, ring):
    return min(edge_distance(point,a,b) for a,b in zip(ring,ring[1:]+ring[:1]))


def in_ring(point, ring, tolerance=EPS):
    if ring_distance(point,ring) <= tolerance:
        return True
    x,y=point[:2];odd=False
    for a,b in zip(ring,ring[1:]+ring[:1]):
        if (a[1]>y)!=(b[1]>y) and x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:
            odd=not odd
    return odd


def in_polygon(point, polygon):
    return in_ring(point,polygon['exterior']) and not any(in_ring(point,hole,0) for hole in polygon['holes'])


def cross(a,b,c):
    u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
    return (u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])


def check_mesh(vertices, faces, boundary, closed=False):
    require(bool(vertices) and bool(faces), 'Empty saved Shiba mesh')
    lo_x,lo_y,hi_x,hi_y=shiba.BOUNDS
    for point in vertices:
        require(len(point)==3 and all(math.isfinite(v) for v in point), 'Non-finite saved vertex')
        require(lo_x-EPS<=point[0]<=hi_x+EPS and lo_y-EPS<=point[1]<=hi_y+EPS and
                .12-EPS<=point[2]<=12.17+EPS, 'Saved vertex outside Shiba scope')
        require(in_ring(point,boundary), 'Saved vertex outside woodland boundary')
    edges=Counter();directed=Counter();area=0.
    for face in faces:
        require(len(face)==3 and all(type(i) is int and 0<=i<len(vertices) for i in face), 'Invalid saved triangle')
        normal=cross(*(vertices[i] for i in face))
        norm2=sum(v*v for v in normal)
        require(norm2>1e-18, 'Degenerate saved triangle')
        area+=math.sqrt(norm2)*.5
        if closed:
            for a,b in zip(face,face[1:]+face[:1]):
                edges[tuple(sorted((a,b)))]+=1;directed[(a,b)]+=1
    if closed:
        require(all(count==2 for count in edges.values()), 'Saved surface is not closed: edge incidence differs from two')
        require(all(count==directed[(b,a)] for (a,b),count in directed.items()), 'Inconsistent saved surface winding')
    return {'vertices':len(vertices),'triangles':len(faces),'area_m2':area,
            'bounds_xyz':[list(map(min,zip(*vertices))),list(map(max,zip(*vertices)))],
            'nonfinite_vertices':0,'degenerate_triangles':0,
            'closed_edge_incidence_two':True if closed else None}


def top_area(vertices, faces, z):
    return sum(abs(cross(*(vertices[i] for i in face))[2])*.5 for face in faces
               if all(abs(vertices[i][2]-z)<=EPS for i in face))


def match_surface(vertices, faces, planned):
    require(len(vertices)==len(planned['vertices']) and len(faces)==len(planned['faces']),
            'Saved surface counts differ from plan')
    # Blender stores input coordinates in float32; compare those exact values.
    f32=lambda value:struct.unpack('<f',struct.pack('<f',value))[0]
    require(all(tuple(map(f32,p))==tuple(v) for p,v in zip(planned['vertices'],vertices)),
            'Saved surface coordinates differ from plan')
    require(all(list(a)==list(b) for a,b in zip(faces,planned['faces'])), 'Saved surface indices differ from plan')
    z=max(p[2] for p in planned['vertices'])
    actual,expected=top_area(vertices,faces,z),top_area(planned['vertices'],planned['faces'],z)
    require(abs(actual-expected)<=.01, 'Saved top area differs from plan')
    return {'plan_coordinates_float32_exact':True,'plan_faces_exact':True,
            'top_area_m2':actual,'plan_top_area_m2':expected,'top_area_error_m2':abs(actual-expected)}


def validate_placement_masks(plan):
    masks=plan.get('audit',{}).get('placement_mask_polygons')
    require(isinstance(masks,list) and bool(masks), 'Plan has no protected placement masks')
    for polygon in masks:
        require(set(polygon)=={'exterior','holes'} and isinstance(polygon['holes'],list), 'Invalid protected polygon')
        for ring in [polygon['exterior']]+polygon['holes']:
            require(len(ring)>=4 and ring[0]==ring[-1], 'Protected ring is not closed')
            require(all(len(p)==2 and all(isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) for x in p)
                        for p in ring), 'Invalid protected coordinate')
    result={}
    for kind in ('trees','shrubs'):
        edge_gaps=[];mask_gaps=[]
        for item in plan[kind]:
            point=(item['x'],item['y']);radius=item['radius']
            require(in_ring(point,plan['boundary']), 'Planting center outside woodland')
            edge_gaps.append(ring_distance(point,plan['boundary'])-radius)
            require(not any(in_polygon(point,p) for p in masks), 'Planting center inside protected area')
            mask_gaps.append(min(ring_distance(point,ring) for p in masks for ring in [p['exterior']]+p['holes'])-radius)
        require(min(edge_gaps)>=1.-EPS and min(mask_gaps)>=1.-EPS, 'Planting envelope lacks one metre clearance')
        result[kind]={'count':len(plan[kind]),'minimum_envelope_boundary_clearance_m':min(edge_gaps),
                      'minimum_envelope_protected_clearance_m':min(mask_gaps)}
    return result


def match_planting_envelopes(vertices, plants, coverage=False):
    buckets=defaultdict(list)
    for index,plant in enumerate(plants):
        buckets[(math.floor(plant['x']/10),math.floor(plant['y']/10))].append((index,plant))
    found=set();maximum=0.
    for point in vertices:
        gx,gy=math.floor(point[0]/10),math.floor(point[1]/10)
        choices=[]
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                for index,plant in buckets.get((gx+dx,gy+dy),[]):
                    distance=math.hypot(point[0]-plant['x'],point[1]-plant['y'])
                    if distance<=plant['radius']+EPS:choices.append((distance/plant['radius'],index))
        require(bool(choices), 'Saved planting exceeds every planned crown envelope')
        relative,index=min(choices);found.add(index);maximum=max(maximum,relative)
    if coverage:require(len(found)==len(plants), 'A planned planting has no saved foliage')
    return {'vertices_within_planned_envelopes':len(vertices),'represented_plantings':len(found),
            'maximum_relative_envelope_radius':maximum}


def check_planting_contact(vertices, plants, kind):
    """Each planned stem or shrub needs saved geometry at the forest-floor top."""
    contacts=defaultdict(list)
    for point in vertices:
        if abs(point[2]-.16)<=EPS:
            contacts[(math.floor(point[0]/10),math.floor(point[1]/10))].append(point)
    for index,plant in enumerate(plants):
        radius=plant['height']*.027 if kind=='trees' else plant['radius']*.85
        gx,gy=math.floor(plant['x']/10),math.floor(plant['y']/10)
        found=any(math.hypot(point[0]-plant['x'],point[1]-plant['y'])<=radius+EPS
                  for dx in (-1,0,1) for dy in (-1,0,1) for point in contacts.get((gx+dx,gy+dy),[]))
        require(found, f'{kind} {index} has no saved ground contact at the planned base')
    return {'grounded_plantings':len(plants),'contact_height_m':.16,
            'contact_radius_rule':'height * 0.027' if kind=='trees' else 'radius * 0.85'}


def in_triangle_xy(point, triangle):
    values=[]
    for a,b in zip(triangle,triangle[1:]+triangle[:1]):
        values.append((b[0]-a[0])*(point[1]-a[1])-(b[1]-a[1])*(point[0]-a[0]))
    return min(values)>=-1e-7 or max(values)<=1e-7


def horizontal_road_projection(triangle):
    # The pinned legacy road tops face downward. Project both windings so
    # inherited normal errors cannot silently remove a protected road surface.
    normal=cross(*triangle);length=math.sqrt(sum(v*v for v in normal))
    return bool(length and abs(normal[2])/length>.9 and
                min(p[2] for p in triangle)>=.1-EPS and max(p[2] for p in triangle)<=.6+EPS)


def road_clearance(plan):
    import bpy
    from blender_worker import mesh_fingerprint
    cells=defaultdict(list);counts={};orientations={}
    expected_hashes={road['name']:road['mesh_sha256'] for road in plan['sources']['road_mask']['roads']}
    lo_x,lo_y,hi_x,hi_y=shiba.BOUNDS
    for name in ROADS:
        obj=bpy.data.objects.get(name)
        require(obj is not None and obj.type=='MESH', 'Missing protected road mesh: '+name)
        require(mesh_fingerprint(obj.data)==expected_hashes[name], 'Saved road differs from the pinned placement mask: '+name)
        obj.data.calc_loop_triangles()
        vertices=[tuple(obj.matrix_world@v.co) for v in obj.data.vertices]
        counts[name]=0;orientations[name]={'up':0,'down':0}
        for face in obj.data.loop_triangles:
            triangle=[vertices[i] for i in face.vertices]
            if not horizontal_road_projection(triangle):continue
            xmin,ymin=min(p[0] for p in triangle),min(p[1] for p in triangle)
            xmax,ymax=max(p[0] for p in triangle),max(p[1] for p in triangle)
            if xmax<lo_x or xmin>hi_x or ymax<lo_y or ymin>hi_y:continue
            counts[name]+=1
            orientations[name]['up' if cross(*triangle)[2]>0 else 'down']+=1
            for x in range(math.floor(max(xmin,lo_x)/10),math.floor(min(xmax,hi_x)/10)+1):
                for y in range(math.floor(max(ymin,lo_y)/10),math.floor(min(ymax,hi_y)/10)+1):
                    cells[(x,y)].append((name,triangle))
    samples=0
    for kind in ('trees','shrubs'):
        for index,plant in enumerate(plan[kind]):
            radius=.35 if kind=='trees' else plant['radius']*.85
            points=[(plant['x'],plant['y'])]+[(plant['x']+radius*math.cos(i*math.tau/16),
                     plant['y']+radius*math.sin(i*math.tau/16)) for i in range(16)]
            for point in points:
                samples+=1
                for name,triangle in cells.get((math.floor(point[0]/10),math.floor(point[1]/10)),[]):
                    require(not in_triangle_xy(point,triangle), f'{kind} {index} base intersects saved road: {name}')
    require(sum(counts.values())>0, 'No protected horizontal road surfaces found in Shiba scope')
    return {'horizontal_road_triangles_in_scope':counts,'source_winding_counts':orientations,
            'road_mesh_sha256':expected_hashes,'mask_source_meshes_exact':True,
            'protected_road_z_range_m':[.1,.6],'base_disk_samples':samples,'intersecting_samples':0,
            'tree_base_radius_m':.35,'shrub_base_radius_factor':.85,
            'sampling':'Both horizontal face windings are projected. Center and 16 perimeter points per base; canopy overhang above pedestrian height is allowed.'}


def inspect(args):
    import bpy
    require(bpy.app.version_string=='4.5.1 LTS', 'Use Blender 4.5.1 LTS')
    require(not bpy.context.preferences.filepaths.use_scripts_auto_execute, 'Disable Blender auto-execution')
    require(Path(bpy.data.filepath).resolve()==args.input.resolve(), 'Opened scene differs from requested input')
    bpy.context.scene.frame_set(1)
    plan=json.loads(args.plan.read_text(encoding='utf-8'));shiba.validate_plan(plan)
    plan_hash=digest(args.plan)
    coll=bpy.data.collections.get(shiba.COLLECTION)
    require(coll is not None and coll.get('otw_feature_id')==shiba.FEATURE, 'Missing Shiba feature collection')
    require(coll.get('otw_plan_sha256')==plan_hash, 'Saved collection plan hash differs')
    require({o.name for o in coll.all_objects}==shiba.ADDED, 'Saved collection object scope differs')
    found={o.name for o in bpy.context.scene.objects if o.name.startswith(shiba.PREFIX) or o.get('otw_feature_id')==shiba.FEATURE}
    require(found==shiba.ADDED, 'Saved feature object scope differs')
    result={'ok':False,'blender_version':bpy.app.version_string,'frame':1,'autoexec_enabled':False,'objects':{},
            'placement':validate_placement_masks(plan),'scene_saved':False,
            'limitations':['Existing-object fingerprints and original-input protection are validated separately by review.py.',
                          'Mapped horizontal layout and inferred vegetation/flat elevation; no surveyed terrain or waterfall reconstruction.',
                          'Road contact checks sample base disks; they do not certify collision-free navigation.']}
    for part in shiba.PARTS:
        name=shiba.PREFIX+part;obj=bpy.data.objects[name]
        require(obj.type=='MESH' and not obj.hide_render, 'Shiba object must be a visible mesh: '+name)
        require(obj.get('otw_feature_id')==shiba.FEATURE and
                obj.get('otw_part_id')=='shiba-momijidani-v1-'+part.replace(' ','-'), 'Saved feature/part ID differs: '+name)
        require(obj.get('otw_plan_sha256')==plan_hash, 'Saved object plan hash differs: '+name)
        require({c.name for c in obj.users_collection}=={shiba.COLLECTION}, 'Unexpected Shiba collection membership')
        require(not obj.modifiers and not obj.parent and not obj.constraints and not obj.animation_data, 'Unsupported saved Shiba state')
        require(all(abs(obj.matrix_world[r][c]-(r==c))<1e-7 for r in range(4) for c in range(4)), 'Unexpected Shiba transform')
        vertices=[tuple(v.co) for v in obj.data.vertices];faces=[list(f.vertices) for f in obj.data.polygons]
        stats=check_mesh(vertices,faces,plan['boundary'],closed=part in ('forest floor','paths'))
        if part in ('forest floor','paths'):
            stats.update(match_surface(vertices,faces,plan['forest_floor' if part=='forest floor' else 'path_surface']))
        else:
            kind='shrubs' if part=='understory' else 'trees'
            stats.update(match_planting_envelopes(vertices,plan[kind],coverage=True))
            if part in ('trunks','understory'):
                stats.update(check_planting_contact(vertices,plan[kind],kind))
        if part=='crowns':
            require(min(p[2] for p in vertices)>=2.8-EPS, 'Saved crown below pedestrian clearance')
        result['objects'][name]=stats
    result['saved_road_clearance']=road_clearance(plan)
    result['ok']=True
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender',type=Path)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True,help='New JSON report path')
    parser.add_argument('--timeout',type=int,default=900)
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    args=parser.parse_args(argv)
    require(not args.output.exists(), 'Refusing to overwrite validation report')
    if args.worker:
        report={'ok':False}
        try:report=inspect(args)
        except Exception as error:
            report['error']=str(error)
            raise
        finally:write(args.output,report)
        return
    require(args.blender is not None and args.timeout>0, 'Specify Blender and a positive timeout')
    args.input=args.input.resolve();args.plan=args.plan.resolve();args.output=args.output.resolve()
    log=args.output.with_suffix('.log')
    require(not log.exists(), 'Refusing to overwrite validation log')
    input_hash,plan_hash=digest(args.input),digest(args.plan)
    dependencies=(Path(__file__),Path(shiba.__file__),Path(__file__).with_name('blender_worker.py'))
    code_hashes={path.name:digest(path) for path in dependencies}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    report={'ok':False}
    try:
        command=[str(args.blender),'--factory-startup','--disable-autoexec','--background',str(args.input),
                 '--python-exit-code','1','--python',str(Path(__file__).resolve()),'--','--worker',
                 '--input',str(args.input),'--plan',str(args.plan),'--output',str(args.output)]
        with log.open('w',encoding='utf-8') as stream:
            process=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=args.timeout,check=False)
        if args.output.exists():report=json.loads(args.output.read_text(encoding='utf-8'))
        require(process.returncode==0 and report.get('ok') is True, report.get('error','Saved Shiba validation failed; inspect local log'))
        require(digest(args.input)==input_hash, 'Saved input scene changed during validation')
        require(digest(args.plan)==plan_hash, 'Plan changed during validation')
        require(all(digest(path)==code_hashes[path.name] for path in dependencies), 'Validation code changed during inspection')
    except Exception as error:
        report.update(ok=False,error=str(error))
        raise
    finally:
        report.update(input_sha256=input_hash,plan_sha256=plan_hash,
                      platform=platform.platform(),python_version=platform.python_version(),
                      code_sha256=code_hashes)
        write(args.output,report)
    print('Saved Shiba validation complete: '+str(args.output))


if __name__=='__main__':main()
