"""Standalone extraction of legacy facade geometry; see NOTICE.md for scope.
No legacy file is read or executed at runtime.
"""
import math
import numpy as np
import bpy
from mathutils import Vector
import mori_crown_v2, mori_facade_v2

def build(profile):
    geo={};section='Mori continuous pearl glass';materials={}
    def add(k,v,f):
     a,b=geo.setdefault((section,k),([],[]));off=len(a);a.extend([tuple(q) for q in v]);b.extend([tuple(off+i for i in q) for q in f])
    
    def beam(k,a,b,r,N=8):
     a,b=Vector(a),Vector(b);d=b-a
     if d.length<1e-5:return
     d.normalize();u=d.cross(Vector((0,0,1)))
     if u.length<.01:u=d.cross(Vector((0,1,0)))
     u.normalize();v=d.cross(u);vs=[q+r*(u*math.cos(i*math.tau/N)+v*math.sin(i*math.tau/N)) for q in [a,b] for i in range(N)]
     add(k,vs,[tuple(range(N-1,-1,-1)),tuple(range(N,2*N))]+[(i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N)])
    
    def band(k,pts,z,h,depth=.16):
     a=np.array(pts);c=a.mean(0);b=a+(c-a)/np.linalg.norm(c-a,axis=1)[:,None]*depth;N=len(a)
     vs=[(x,y,zz) for zz in [z,z+h] for arr in [a,b] for x,y in arr];faces=[]
     for i in range(N):
      j=(i+1)%N;faces.extend([(i,j,2*N+j,2*N+i),(N+j,N+i,3*N+i,3*N+j),(2*N+i,2*N+j,3*N+j,3*N+i),(i,N+i,N+j,j)])
     add(k,vs,faces)
    
    def mat(k,c,metal=0,rough=.25,trans=0):
     m=bpy.data.materials.new('Mori corrected / '+k);m.use_nodes=True;m.diffuse_color=(*c,1);p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*c,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough;p.inputs['Transmission Weight'].default_value=trans;p.inputs['IOR'].default_value=1.46;materials[k]=m;return m
    glass=mat('pearl grey coated glass',(.48,.63,.67),.12,.055,.9)
    mat('recessed spandrel',(.07,.105,.125),.38,.095);mat('slender mullion',(.13,.17,.19),.65,.23);mat('sealing joint',(.011,.018,.02),.1,.5)
    cx,cy=(-430.39,253.4);raw=np.asarray(profile,dtype=float)
    for _ in range(3):raw=(np.roll(raw,2)+4*np.roll(raw,1)+6*raw+4*np.roll(raw,-1)+np.roll(raw,-2))/16
    N=256;theta=np.arange(N)*math.tau/N;radii=np.interp(theta,np.r_[np.arange(160)*math.tau/160,math.tau],np.r_[raw,raw[0]]);dirs=np.column_stack([np.cos(theta),np.sin(theta)])
    def contour(z,inset=0):return np.array([cx,cy])+dirs*(radii*(1-.014*((z-165)/165)**2)-inset)[:,None]
    def pane(i,z0,z1,top0=None,top1=None):
     j=(i+1)%N;p0=contour(z0)[i];p1=contour(z0)[j];h0=z1 if top0 is None else top0;h1=z1 if top1 is None else top1
     q0=contour(h0)[i];q1=contour(h1)[j];outer=[(*p0,z0),(*p1,z0),(*q1,h1),(*q0,h0)]
     inner=[(v[0]-dirs[idx,0]*.028,v[1]-dirs[idx,1]*.028,v[2]) for v,idx in zip(outer,[i,j,j,i])]
     add('pearl grey coated glass',outer+inner,[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)])
    floors=np.r_[np.linspace(.32,24.32,5),np.linspace(29.22,318.32,60)]
    for z0,z1 in zip(floors,floors[1:]):
     pts=contour(z0,.008);band('recessed spandrel',pts,z0,.72,.12)
     # Thin, continuous joints replace the projecting silver ledges.
     band('slender mullion',contour(z0,.005),z0,.075,.09)
     for i in range(N):
      pane(i,z0+.72,z1-.008)
      p=contour(z0)[i];q=contour(z1)[i];beam('slender mullion',(*p,z0),(*q,z1),.026,6)
     # A central narrow seam describes the four petal segments.
     for i in [0,64,128,192]:
      p=contour(z0)[i];q=contour(z1)[i];beam('sealing joint',(*p,z0),(*q,z1),.13,8)
    heights=323.4+7.7*np.sin(2*theta)**2
    for i in range(N):
     j=(i+1)%N;pane(i,318.32,331,heights[i],heights[j]);p=contour(heights[i])[i];q=contour(heights[j])[j];beam('slender mullion',(*p,heights[i]),(*q,heights[j]),.045,8)
    col=bpy.data.collections.new(section);bpy.context.scene.collection.children.link(col)
    for (sect,k),(v,f) in geo.items():
     me=bpy.data.meshes.new(sect+' / '+k);me.from_pydata(v,[],f);me.materials.append(materials[k]);me.update();ob=bpy.data.objects.new(me.name,me);col.objects.link(ob)
    
    for ob in col.objects:
     mori_crown_v2.apply(ob)
     mori_facade_v2.apply(ob)
    return list(col.objects)
