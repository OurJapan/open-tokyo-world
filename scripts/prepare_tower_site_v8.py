# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Prepare the bounded shared ground shell; Shapely 2.1.2."""
import json
from pathlib import Path
import shapely as sh
from prepare_tower_footway_v5 import mesh
import tower_site_geometry_v8 as geo
from tower_footway_geometry_v5 import world
ROOT=Path(__file__).resolve().parents[1]


def prepare(old):
    if sh.__version__!='2.1.2':raise ValueError('Expected Shapely 2.1.2')
    xs=sorted(set(float(x) for x in range(-60,61))|{-36.5,-36.25,36.25,36.5})
    ys=sorted(set(float(y) for y in range(-90,-11))|{-28.75})
    vs=[world((x,y,geo.grade(x,y))) for y in ys for x in xs];fs=[];n=len(xs)
    for i in range(len(ys)-1):
        for j in range(n-1):
            a=i*n+j;fs.extend(((a,a+1,a+n+1),(a,a+n+1,a+n)))
    border=list(range(n))+[i*n+n-1 for i in range(1,len(ys))]+list(range(len(vs)-2,len(vs)-n-1,-1))+[i*n for i in range(len(ys)-2,0,-1)]
    assert all(abs(vs[i][2])<1e-9 for i in border)
    north=old['ground_top']['grid']
    # Retain every collinear boundary vertex to keep the complete shell closed.
    xmin,ymin,xmax,ymax=old['scopes'][0]
    from tower_footway_geometry_v5 import local
    ring=[p[:2] for p in north['vertices'] if min(abs(local(p)[0]-xmin),abs(local(p)[0]-xmax),abs(local(p)[1]-ymin),abs(local(p)[1]-ymax))<1e-6]
    cx=sum(p[0] for p in ring)/len(ring);cy=sum(p[1] for p in ring)/len(ring)
    import math
    ring.sort(key=lambda p:math.atan2(p[1]-cy,p[0]-cx))
    outside=mesh(sh.Polygon([(-15000,-15000),(15000,-15000),(15000,15000),(-15000,15000)],[ring,[vs[i][:2] for i in border]]),0.)
    slopes=geo.cap_slopes(old['caps']);masks=[]
    from tower_ground_geometry_v7 import cap_mesh
    vertices=geo.cladding_vertices(cap_mesh(old['caps'],old)['vertices'],old['caps'],slopes)
    for i in range(4):
        ps=[p[:2] for p in vertices[i*16:i*16+16]]
        hull=sh.orient_polygons(sh.MultiPoint(ps).convex_hull)
        masks.append(list(hull.exterior.coords)[:-1])
    return dict(version=1,generation_environment={'shapely':sh.__version__,'geos':sh.geos_version_string},caps=old['caps'],slopes=slopes,masks=masks,
        bounds=geo.BOUNDS,ground_top={'south':dict(vertices=vs,faces=fs),'north':north,'outside':outside},
        steps=old['steps'],limits=[
        'South terrain uses a bounded relative grade, not an absolute or region-wide DEM reconstruction.',
        'The retained 4.4m doorway and 3.2m lot anchors control the surface; lateral and boundary transitions are estimated.',
        'Plinth cladding follows the retained lower-leg axis. Its common Z=7m top and panel dimensions remain provisional.',
        'OSM records eight steps and no handrail. Unsupported rails are hidden, while the unmeasured 0.275m risers and long treads remain provisional.',
        'Point samples and mesh checks are not a continuous pedestrian or accessibility certification.'])


if __name__=='__main__':
    out=ROOT/'areas/tokyo-tower/tower-site-v8-plan.json'
    assert not out.exists()
    old=json.loads((ROOT/'areas/tokyo-tower/tower-ground-v7-plan.json').read_text(encoding='utf-8'))
    out.write_text(json.dumps(prepare(old),ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
