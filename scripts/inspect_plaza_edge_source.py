from pathlib import Path
import xml.etree.ElementTree as ET,json,math,sys,hashlib
import argparse
p=argparse.ArgumentParser();p.add_argument('--osm',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
if a.output.exists():raise ValueError('Output exists')
sys.path.insert(0,str(Path(__file__).resolve().parent))
from mori_plaza_link_v1 import local
src=a.osm
assert hashlib.file_digest(src.open('rb'),'sha256').hexdigest()=='f04e8e70ab24a61ca749375d1ef37401feb0fdc840cc506b670ef71454a6a8ab'
root=ET.parse(src).getroot()
nodes={n.get('id'):local(((float(n.get('lon'))-139.74543)*111320*math.cos(math.radians(35.65858)),(float(n.get('lat'))-35.65858)*110950,0))[:2] for n in root.findall('node')}
def dist(p,a,b):
 dx,dy=b[0]-a[0],b[1]-a[1];l=dx*dx+dy*dy
 t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/l)) if l else 0
 return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)
ways=[]
for w in root.findall('way'):
 tags={t.get('k'):t.get('v') for t in w.findall('tag')}
 if 'highway' not in tags:continue
 pts=[nodes[n.get('ref')] for n in w.findall('nd') if n.get('ref') in nodes]
 if not pts:continue
 if min(dist((0,28),a,b) for a,b in zip(pts,pts[1:]))>65:continue
 ways.append({'id':w.get('id'),'tags':tags,'pts':pts})
rows=[]
for u in (-12,-10,-8,-6,6,8,10,12,14):
 for v in (24,26,28,30,32,34):
  nearest=sorted((min(dist((u,v),a,b) for a,b in zip(w['pts'],w['pts'][1:])),w['id']) for w in ways if w['tags'].get('tunnel')!='yes' and w['tags'].get('indoor')!='yes')[:3]
  rows.append({'u':u,'v':v,'nearest':nearest})
out={'source_sha256':hashlib.file_digest(src.open('rb'),'sha256').hexdigest(),'ways':ways,'samples':rows}
a.output.write_text(json.dumps(out,indent=2),encoding='utf8')
print('Source research saved locally; contains third-party geometry, do not publish it.')
