# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Prepare pinned local terrain and an eight-riser path; Shapely 2.1.2."""
import argparse,json,math
from pathlib import Path
import shapely as sh
import prepare_tower_footway_v5 as roads
import tower_ground_geometry_v7 as geo
ROOT=Path(__file__).resolve().parents[1]

def terrain_mesh(zone,top,bottom,plan):
    """Conforming edge splits prevent long triangles cutting through terrain."""
    from collections import Counter
    data=roads.mesh(zone,top);vs=data['vertices'];fs=data['faces']
    while True:
        edges={tuple(sorted((f[i],f[(i+1)%3]))) for f in fs for i in range(3)}
        mids={}
        for a,b in sorted(edges):
            if math.dist(vs[a][:2],vs[b][:2])>.6:
                mids[(a,b)]=len(vs);vs.append(tuple((x+y)/2 for x,y in zip(vs[a],vs[b])))
        if not mids:break
        new=[]
        for f in fs:
            marked=[i for i in range(3) if tuple(sorted((f[i],f[(i+1)%3]))) in mids]
            if not marked:new.append(f);continue
            if len(marked)==1:
                i=marked[0];a,b,c=f[i],f[(i+1)%3],f[(i+2)%3];m=mids[tuple(sorted((a,b)))];new.extend(((a,m,c),(m,b,c)))
            elif len(marked)==2:
                i=next(i for i in marked if (i+1)%3 in marked)
                a,b,c=f[i],f[(i+1)%3],f[(i+2)%3];m=mids[tuple(sorted((a,b)))];n=mids[tuple(sorted((b,c)))];new.extend(((b,n,m),(a,m,c),(m,n,c)))
            else:
                a,b,c=f;m,n,o=[mids[tuple(sorted((f[i],f[(i+1)%3])))] for i in range(3)];new.extend(((a,m,o),(m,b,n),(o,n,c),(m,n,o)))
        fs=new
    if bottom is not None:
        count=len(vs);edge_counts=Counter(tuple(sorted((f[i],f[(i+1)%3]))) for f in fs for i in range(3))
        walls=[(a,a+count,b+count,b) for f in fs for a,b in zip(f,(*f[1:],f[0])) if edge_counts[tuple(sorted((a,b)))]==1]
        vs.extend((x,y,bottom) for x,y,z in list(vs));fs=fs+[tuple(i+count for i in reversed(f)) for f in fs]+walls
    return {'vertices':[(x,y,z+geo.profile(x,y,plan)) for x,y,z in vs],'faces':fs}

def prepare(osm):
    old=json.loads((ROOT/'areas/tokyo-tower/tower-registration-v6-plan.json').read_text(encoding='utf-8'))
    caps=old['caps'];scope=[33.498,19.998,63.002,60.502]
    p=roads.prepare(osm,[c['rectangle'] for c in caps],[scope]);p['caps']=caps
    route=next(r for r in p['routes'] if r['id']=='1245345677');line=sh.LineString(route['points']);length=line.length
    sections=[]
    for i in range(9):
        s=length*i/8;q=line.interpolate(s);a=line.interpolate(max(0,s-.05));b=line.interpolate(min(length,s+.05));dx,dy=b.x-a.x,b.y-a.y;d=math.hypot(dx,dy)
        sections.append([[q.x-dy/d,q.y+dx/d],[q.x+dy/d,q.y-dx/d]])
    steps=[]
    for i in range(8):
        ring=[sections[i][0],sections[i][1],sections[i+1][1],sections[i+1][0]]
        ring=list(sh.orient_polygons(sh.Polygon(ring)).exterior.coords)[:4]
        steps.append(dict(polygon=ring,height=-1.44+(i+1)*.275))
    # Profile extends the lower landing toward the surrounding road and blends
    # to the retained city. Heights use a local front anchor, not an absolute datum.
    ps=route['points'];a,b=ps[0],ps[1];dx,dy=a[0]-b[0],a[1]-b[1];d=math.hypot(dx,dy)
    lead=[a[0]+dx/d*10,a[1]+dy/d*10,0.]
    landing=[a[0]+dx/d*1.2,a[1]+dy/d*1.2,-1.9]
    cumulative=[0.]
    for a,b in zip(ps,ps[1:]):cumulative.append(cumulative[-1]+math.dist(a,b))
    profile=[lead,landing]+[[*q,-1.9+2.2*s/length] for q,s in zip(ps,cumulative)]
    tail=next(r for r in p['routes'] if r['id']=='1245345678')['points'][-1];profile.append([*tail,0.])
    p.update(steps=steps,sections=sections,profile_line=profile,step_count=8,total_rise_m=2.2,riser_m=.275,stairs_length_m=length)
    stair_mask=sh.union_all([sh.Polygon(s['polygon']) for s in steps])
    for name,row in p['replacement'].items():
        zone=sh.union_all([sh.Polygon(x['exterior'],x['holes']) for x in row['polygons']])
        if name.startswith('pavement'):zone=sh.set_precision(zone.difference(stair_mask.buffer(.06,join_style=2)),.001)
        data=terrain_mesh(zone,.46 if name.startswith('pavement') else .3,.3 if name.startswith('pavement') else None,p)
        row.update(data)
        row['area_m2']=zone.area
        row['polygons']=[{'exterior':list(poly.exterior.coords)[:-1],'holes':[list(r.coords)[:-1] for r in poly.interiors]} for poly in roads.polygons(zone)]
    # Original 30km ground-box sides/bottom remain; only its top acquires a local
    # depressed grid. The outside top is still exactly the original Z=0 plane.
    xmin,ymin,xmax,ymax=scope
    xs=[xmin+(xmax-xmin)*i/60 for i in range(61)];ys=[ymin+(ymax-ymin)*i/82 for i in range(83)]
    vs=[geo.world((x,y,geo.profile(x,y,p))) for y in ys for x in xs];fs=[];n=len(xs)
    for i in range(len(ys)-1):
        for j in range(n-1):
            a=i*n+j;fs.extend(((a,a+1,a+n+1),(a,a+n+1,a+n)))
    border=list(range(n))+[i*n+n-1 for i in range(1,len(ys))]+list(range(len(vs)-2,len(vs)-n-1,-1))+[i*n for i in range(len(ys)-2,0,-1)]
    for i in border:assert abs(vs[i][2])<1e-8,'Terrain must meet retained ground at zero'
    hole=[vs[i][:2] for i in border];outer=[(-15000,-15000),(15000,-15000),(15000,15000),(-15000,15000)]
    patch=sh.Polygon(outer,[hole]);outside=roads.mesh(patch,0.)
    p['ground_top']={'grid':{'vertices':vs,'faces':fs},'outside':outside}
    p['limits']=[
        'Eight risers come from saved OSM; the 2.2m endpoint difference is a 1m DEM estimate, not measured riser height.',
        'The 0.275m model risers and long treads are provisional; no accessibility or construction compliance claim.',
        'Ground and roads blend locally into the inherited flat city; this is not a regional terrain reconstruction.',
        'Visible plinth height 7m is a mapped estimate corroborated qualitatively by photographs. Taper, panels and bolt layout are inferred.',
        'The south apron is anchored to the retained 4.4m doorway, with 3.2m at the DEM lot sample; absolute datum remains unknown.']
    return p

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--osm',type=Path,required=True);a.add_argument('--output',type=Path,required=True);s=a.parse_args();assert not s.output.exists()
    s.output.write_text(json.dumps(prepare(s.osm),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
