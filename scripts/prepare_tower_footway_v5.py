# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Prepare bounded tower footway surfaces from pinned historical OSM routes.
Requires the repository production runtime (Shapely 2.1.2).
"""
import argparse,hashlib,json,math,xml.etree.ElementTree as ET
from pathlib import Path
import shapely as sh
ROOT=Path(__file__).resolve().parents[1]
SCOPES=[(33.5,-63.,67.,-30.),(33.5,20.,63.,60.5),(-51.,45.,-38.,61.)]
OSM_HASH='f04e8e70ab24a61ca749375d1ef37401feb0fdc840cc506b670ef71454a6a8ab'
WIDTHS={'motorway':18,'trunk':18,'primary':19,'secondary':16,'tertiary':12,'residential':6,'service':4,'footway':2,'path':1.5,'pedestrian':9,'steps':2}

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def xy(n):
    x=(float(n.get('lon'))-139.74543)*111320*math.cos(math.radians(35.65858));y=(float(n.get('lat'))-35.65858)*110950
    a=math.radians(33.7);c,s=math.cos(a),math.sin(a)
    return (c*x-s*y,s*x+c*y)
def polygons(g):return [p for p in sh.get_parts(g) if p.geom_type=='Polygon' and p.area>1e-7]
def mesh(zone,top,bottom=None):
    vs=[];fs=[];lookup={}
    def vertex(x,y,z):
        key=(float(x),float(y),float(z))
        if key not in lookup:lookup[key]=len(vs);vs.append(key)
        return lookup[key]
    for poly in polygons(zone):
        poly=sh.orient_polygons(poly)
        for tri in sh.get_parts(sh.constrained_delaunay_triangles(poly)):
            ring=list(sh.orient_polygons(tri).exterior.coords)[:3]
            ids=[vertex(x,y,top) for x,y in ring];fs.append(ids)
            if bottom is not None:fs.append([vertex(x,y,bottom) for x,y in reversed(ring)])
        if bottom is not None:
            for ring in [poly.exterior,*poly.interiors]:
                ps=list(ring.coords)
                for a,b in zip(ps,ps[1:]):
                    fs.append([vertex(*a,top),vertex(*a,bottom),vertex(*b,bottom),vertex(*b,top)])
    return {'vertices':vs,'faces':fs}

def prepare(osm):
    assert sh.__version__=='2.1.2'
    assert digest(osm)==OSM_HASH
    tree=ET.parse(osm).getroot();nodes={n.get('id'):n for n in tree.findall('node')}
    scope=sh.union_all([sh.box(*b) for b in SCOPES]);near=scope.buffer(30)
    roads=[];outer=[];routes=[]
    for w in tree.findall('way'):
        tags={t.get('k'):t.get('v') for t in w.findall('tag')};typ=tags.get('highway')
        if typ not in WIDTHS or tags.get('tunnel')=='yes' or tags.get('indoor')=='yes' or tags.get('bridge')=='yes':continue
        try:
            if float(tags.get('layer','0'))<0:continue
        except ValueError:raise ValueError('Unsupported source layer')
        ps=[xy(nodes[t.get('ref')]) for t in w.findall('nd') if t.get('ref') in nodes]
        if len(ps)<2:continue
        line=sh.LineString(ps)
        if not line.intersects(near):continue
        try:width=float(tags.get('width','0')) or WIDTHS[typ]
        except ValueError:width=WIDTHS[typ]
        pedestrian=typ in ('footway','path','steps','pedestrian')
        # Keep the inherited 1.05m pavement allowance at vehicle roads.
        # An explicitly mapped walking route is a 2m nominal pedestrian strip,
        # not the old default 4m asphalt road used for each stairs segment.
        if pedestrian:outer.append(line.buffer(width/2,cap_style=2,join_style=1,quad_segs=6))
        else:
            roads.append(line.buffer(width/2,cap_style=2,join_style=1,quad_segs=6))
            outer.append(line.buffer(width/2+1.05,cap_style=2,join_style=1,quad_segs=6))
        routes.append({'id':w.get('id'),'tags':tags,'width_m':width,'width_source':'OSM width' if tags.get('width') else 'model nominal width','points':list(sh.intersection(line,near).coords) if sh.intersection(line,near).geom_type=='LineString' else ps})
    road=sh.union_all(roads);walk=sh.union_all(outer).difference(road)
    # Round fragile pointed ends without extending into the carriageway.
    walk=walk.buffer(-.22,quad_segs=6).buffer(.22,quad_segs=6).intersection(walk)
    # Retain the v4 tower and apron; no new walking surface beneath them.
    from tower_foundation_geometry_v4 import grid
    rows=grid();apron=sh.Polygon(rows[0]+[r[-1] for r in rows[1:]]+list(reversed(rows[-1][:-1]))+[r[0] for r in reversed(rows[1:-1])])
    caps=sh.union_all([sh.box(sx*44-5.25,sy*44-5.25,sx*44+5.25,sy*44+5.25) for sx in (-1,1) for sy in (-1,1)])
    mask=sh.union_all([caps,apron]);road=road.difference(mask).intersection(scope);walk=walk.difference(mask).intersection(scope)
    gutter=road.difference(road.buffer(-.24,join_style=1)).intersection(scope)
    # Only physical road edges get gutters, not the rectangular edit boundary.
    fullroad=sh.union_all(roads).difference(mask)
    gutter=fullroad.difference(fullroad.buffer(-.24,join_style=1)).intersection(scope)
    asphalt=road.difference(gutter)
    zones={name:sh.set_precision(zone,.001) for name,zone in {'asphalt 15s road detail':asphalt,'gutter 15s road detail':gutter,'pavement_0 unified road':walk}.items()}
    zones['gutter 15s road detail']=zones['gutter 15s road detail'].difference(zones['asphalt 15s road detail'])
    zones['pavement_0 unified road']=zones['pavement_0 unified road'].difference(sh.union_all([zones['asphalt 15s road detail'],zones['gutter 15s road detail']]))
    assert max(sh.intersection(a,b).area for i,a in enumerate(zones.values()) for j,b in enumerate(zones.values()) if i<j)<1e-7
    return {'version':1,'osm_sha256':OSM_HASH,'scopes':SCOPES,'routes':routes,'runtime':{'shapely':sh.__version__,'geos':sh.geos_version_string},'replacement':{name:{**mesh(zone,.46 if name.startswith('pavement') else .3,.3 if name.startswith('pavement') else None),'area_m2':zone.area,'polygons':[{'exterior':list(p.exterior.coords),'holes':[list(h.coords) for h in p.interiors]} for p in polygons(zone)]} for name,zone in zones.items()},'limits':['Nominal widths and flat local road elevations are inherited model assumptions.','OSM steps way 1245345677 remains a mapped pedestrian route; real riser elevations and stair geometry are not reconstructed.','Existing tower/road georegistration conflicts are not solved by moving road centre lines.','Only three declared edit rectangles are rebuilt; other city roads are unchanged.']}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--osm',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();data=prepare(a.osm)
    if a.output.exists():raise ValueError('Refusing to overwrite plan')
    a.output.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print({n:(len(d['faces']),round(d['area_m2'],3)) for n,d in data['replacement'].items()})
