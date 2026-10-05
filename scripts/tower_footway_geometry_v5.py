# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Pure 3D polygon clipping for the bounded footway correction."""
import math
TARGETS={'asphalt 15s road detail','gutter 15s road detail','pavement_0 unified road'}
ANGLE=math.radians(33.7)
def local(p):
    c,s=math.cos(ANGLE),math.sin(ANGLE);x,y,z=p
    return c*x-s*y,s*x+c*y,z
def world(p):
    c,s=math.cos(ANGLE),math.sin(ANGLE);x,y,z=p
    return c*x+s*y,-s*x+c*y,z
def area(poly):
    if len(poly)<3:return 0.
    a=poly[0];total=0.
    for b,c in zip(poly[1:-1],poly[2:]):
        u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
        total+=math.sqrt(sum(q*q for q in (u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])))/2
    return total

def half(poly,axis,value,sign):
    out=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=sign*(a[axis]-value);db=sign*(b[axis]-value)
        if da>=0:out.append(a)
        if (da<0)!=(db<0):
            t=da/(da-db);out.append(tuple(a[i]+t*(b[i]-a[i]) for i in range(3)))
    clean=[]
    for p in out:
        if not clean or math.dist(p,clean[-1])>1e-8:clean.append(p)
    if len(clean)>1 and math.dist(clean[0],clean[-1])<1e-8:clean.pop()
    return clean

def cut(poly,box):
    xmin,ymin,xmax,ymax=box;inside=poly;outside=[]
    for axis,value,sign in ((0,xmin,1),(0,xmax,-1),(1,ymin,1),(1,ymax,-1)):
        p=half(inside,axis,value,-sign)
        if area(p)>1e-8:outside.append(p)
        inside=half(inside,axis,value,sign)
        if area(inside)<1e-8:return outside,[]
    return outside,inside

def subtract(poly,scopes):
    remain=[poly];removed=[]
    for box in scopes:
        rest=[]
        for p in remain:
            xs=[v[0] for v in p];ys=[v[1] for v in p]
            if max(xs)<=box[0] or min(xs)>=box[2] or max(ys)<=box[1] or min(ys)>=box[3]:rest.append(p);continue
            outside,inside=cut(p,box);rest.extend(outside)
            if area(inside)>1e-8:removed.append(inside)
        remain=rest
    return remain,removed

def inside(p,scopes,eps=1e-5):
    return any(a-eps<=p[0]<=c+eps and b-eps<=p[1]<=d+eps for a,b,c,d in scopes)
