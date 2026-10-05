# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Source-guided tower ground and plinth details; dimensions include estimates."""
import math
from tower_structure_v1 import MeshBuilder,railing,unit,cross,sub
from tower_footway_geometry_v5 import world,local
from tower_foundation_geometry_v4 import STONE,STEEL,PLATES,PAVING
MARKS='Skywalk visible detail white'
GROUND='ground'
ROADS={'asphalt 15s road detail','gutter 15s road detail','pavement_0 unified road'}
TARGETS=ROADS|{STONE,STEEL,PLATES,PAVING,MARKS,GROUND}
PREFIX='OTW Tokyo Tower ground v7 / '
MATERIALS={'plinth':((.44,.32,.31,1),0,.85),'stairs':((.42,.42,.39,1),0,.85),'rails':((.22,.24,.25,1),.7,.38),
 'plinth-joints':((.22,.205,.19,1),0,.85),'gussets':((.54,.045,.012,1),.4,.4)}
ADDED={PREFIX+k for k in MATERIALS if k!='plinth'}

def smooth(t):
    t=max(0.,min(1.,t));return t*t*(3-2*t)

def profile(x,y,plan):
    """Local transition to the unchanged flat city, not a regional DEM."""
    line=plan['profile_line'];best=None
    for a,b in zip(line,line[1:]):
        dx,dy=b[0]-a[0],b[1]-a[1];length2=dx*dx+dy*dy
        t=max(0.,min(1.,((x-a[0])*dx+(y-a[1])*dy)/length2))
        q=(a[0]+t*dx,a[1]+t*dy);distance=math.hypot(x-q[0],y-q[1])
        if best is None or distance<best[0]:best=(distance,a[2]+t*(b[2]-a[2]))
    distance,height=best
    return height*(1-smooth((distance-1.15)/4.85))

def lift(p):
    x,y,z=p
    if z>=30:return tuple(p)
    return x,y,z+5.*(1-smooth((z-2.)/28.))

def apron_height(x,y,ground):
    from tower_foundation_geometry_v4 import width
    if y<-55:h=.48+(3.2-.48)*smooth((y+70)/15)
    elif y<-33:h=3.2+(4.4-3.2)*smooth((y+55)/22)
    else:h=4.4
    core=min(16.,width(y)-4.);f=1-smooth((abs(x)-core)/(width(y)-core))
    return ground+.015+(h-ground-.015)*f*max(0.,min(1.,(y+70)/2))

def cap_mesh(caps,plan):
    b=MeshBuilder()
    for c in caps:
        # Visible upper envelope follows the mapped outline. The lower inward
        # taper is photo-guided; the 7m height is the mapped, unmeasured value.
        rings=[]
        for scale,z in ((.72,-.12),(.72,.48),(1.,6.90),(1.,7.0)):
            ring=[]
            for dx,dy in ((-1,-1),(1,-1),(1,1),(-1,1)):
                x,y=[c['center'][k]+scale*(dx*c['size'][0]*c['u'][k]+dy*c['size'][1]*c['v'][k])/2 for k in (0,1)]
                ring.append((x,y,z+profile(x,y,plan) if z<0 else z))
            rings.extend(ring)
        fs=[(0,3,2),(0,2,1),(12,13,14),(12,14,15)]
        for r in range(3):
            for i in range(4):
                a=r*4+i;bb=r*4+(i+1)%4;cc=bb+4;d=a+4;fs.extend(((a,bb,cc),(a,cc,d)))
        b.add('cap',rings,fs)
    return b.groups['cap']

def details(caps,plan):
    b=MeshBuilder()
    for step in plan['steps']:
        vertices=[(*p,z) for z in (-1.99,step['height']) for p in step['polygon']]
        b.add('stairs',vertices,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
    sections=plan['sections']
    for side in (0,1):
        for i,(a,c) in enumerate(zip(sections,sections[1:])):
            A=(*a[side],-.065+i*.275);C=(*c[side],-.065+(i+1)*.275)
            # Continuous top rail stays at least 1.10m above each tread.
            b.beam('rails',A,C,.035,8)
        for i,section in enumerate(sections):
            z=-1.44+min(i+1,8)*.275
            x,y=section[side];b.beam('rails',(x,y,z),(x,y,-.065+i*.275),.029,8)
    for c in caps:
        u,v=c['u'],c['v'];cx,cy=c['center'];w,h=c['size']
        def at(a,d,z):
            scale=.72+.28*max(0.,min(1.,(z-.48)/6.42))
            return cx+scale*(a*u[0]+d*v[0]),cy+scale*(a*u[1]+d*v[1]),z
        for side in range(4):
            # Thin joints reproduce the visible stone-panel divisions, not
            # construction joints in the hidden structural foundation.
            if side<2:
                a=(-1 if side==0 else 1)*w/2;ends=lambda z:(at(a,-h/2,z),at(a,h/2,z))
                vertical=lambda t,z:at(a,t*h/2,z)
            else:
                d=(-1 if side==2 else 1)*h/2;ends=lambda z:(at(-w/2,d,z),at(w/2,d,z))
                vertical=lambda t,z:at(t*w/2,d,z)
            for z in (.48,1.28,2.08,2.88,3.68,4.48,5.28,6.08,6.9):
                start,end=ends(z);b.beam('plinth-joints',start,end,.008,4)
            for t in (-.75,-.5,-.25,0,.25,.5,.75):
                b.beam('plinth-joints',vertical(t,.48),vertical(t,6.9),.008,4)
    from tower_foundation_geometry_v4 import lower_point
    from tower_registration_geometry_v6 import point
    def node(sx,sy,dx,dy,z):
        w=47.5+(40.8-47.5)*z/15 if z<=15 else 40.8+(34-40.8)*(z-15)/15
        half=3.4-z*.017
        return lift(point(lower_point((sx*w+dx*half,sy*w+dy*half,z)),caps))
    corners=[(-1,-1),(1,-1),(1,1),(-1,1)]
    for sx,sy in corners:
        for z in (7,12,17,22):
            for i,(dx,dy) in enumerate(corners):
                p=node(sx,sy,dx,dy,z);q=node(sx,sy,dx,dy,z+5)
                for j in ((i-1)%4,(i+1)%4):
                    edge=sub(node(sx,sy,*corners[j],z),p);u=unit(edge);n=unit(cross(u,sub(q,p)))
                    # Orient the plate normal away from the leg centre.
                    if sum(n[k]*(p[k]-node(sx,sy,0,0,z)[k]) for k in (0,1))<0:n=tuple(-a for a in n)
                    v=unit(cross(n,u));center=tuple(p[k]+n[k]*.18 for k in range(3))
                    outline=[(-.38,-.34),(-.20,-.48),(.20,-.48),(.38,-.34),(.38,.34),(.20,.48),(-.20,.48),(-.38,.34)]
                    vs=[tuple(center[k]+a*u[k]+d*v[k]+t*n[k] for k in range(3)) for t in (-.025,.025) for a,d in outline]
                    fs=[tuple(range(7,-1,-1)),tuple(range(8,16))]+[(i,(i+1)%8,(i+1)%8+8,i+8) for i in range(8)]
                    b.add('gussets',vs,fs)
                    for a in (-.22,.22):
                        for d in (-.26,0,.26):
                            A=tuple(center[k]+a*u[k]+d*v[k]+.024*n[k] for k in range(3));B=tuple(A[k]+.07*n[k] for k in range(3))
                            b.beam('gussets',A,B,.04,6)
    return b.groups
