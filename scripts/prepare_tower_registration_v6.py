# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Derive provisional visible plinth registration from pinned OSM, not a survey."""
import argparse,json,math,xml.etree.ElementTree as ET
from pathlib import Path
import shapely as sh
import prepare_tower_footway_v5 as roads

CAP_HASH='be3de9cbf95ce6f7a1243e7690543477b06bd4cdbe42a17ee6b28dd2c3717dd6'
CAP_IDS={'1244967004','1244967005','1244967006','1244967007'}

def caps(path):
    assert roads.digest(path)==CAP_HASH
    tree=ET.parse(path).getroot();nodes={n.get('id'):n for n in tree.findall('node')};out=[]
    for w in tree.findall('way'):
        if w.get('id') not in CAP_IDS:continue
        ps=[roads.xy(nodes[n.get('ref')]) for n in w.findall('nd')]
        p=sh.Polygon(ps);rect=p.minimum_rotated_rectangle;ring=list(rect.exterior.coords)[:4]
        cx,cy=rect.centroid.coords[0]
        edges=[(b[0]-a[0],b[1]-a[1]) for a,b in zip(ring,ring[1:]+ring[:1])]
        u=max(edges,key=lambda e:e[0]);width=math.hypot(*u);u=[v/width for v in u]
        v=[-u[1],u[0]];height=rect.area/width
        out.append(dict(way_id=w.get('id'),version=w.get('version'),timestamp=w.get('timestamp'),
            source_polygon=ps,rectangle=ring,center=[cx,cy],size=[width,height],u=u,v=v,
            quadrant=[1 if cx>0 else -1,1 if cy>0 else -1],
            rectangle_excess_area_m2=rect.area-p.area))
    assert len(out)==4
    return out

def prepare(osm,cap_osm):
    cs=caps(cap_osm)
    # Reuse the already reviewed OSM route and width logic, changing only its
    # plinth mask. Keep historical v5 outputs reproducible.
    # Enclose saved float32 boundary side walls from v5 by 1mm, so they
    # are replaced once rather than retained as coincident internal walls.
    scopes=[(a-.001,b-.001,c+.001,d+.001) for a,b,c,d in roads.SCOPES]
    plan=roads.prepare(osm,[c['rectangle'] for c in cs],scopes)
    plan.update(caps=cs,cap_osm_sha256=CAP_HASH,blend_top_m=30.)
    plan['limits']=[s for s in plan['limits'] if not s.startswith('Existing tower/road')]+[
        'Visible plinths follow OSM minimum rectangles, not measured construction dimensions.',
        'Independent mapped plinth positions are not treated as proof of real tower asymmetry.',
        'Lower steel and estimated plates interpolate to unchanged geometry at 30m; this is not a structural reconstruction.',
        'Cap height remains the inherited 2m estimate; OSM height=7 is not adopted.',
        'The upper tower, FootTown, apron, geographic origin and vertical datum are unchanged.']
    return plan

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--osm',type=Path,required=True);p.add_argument('--cap-osm',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists()
    a.output.write_text(json.dumps(prepare(a.osm,a.cap_osm),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
