# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Shared, bounded site grade and inclined cladding; not surveyed dimensions."""
import math
from tower_ground_geometry_v7 import smooth, STONE, PAVING, GROUND, MARKS, PREFIX
from tower_footway_geometry_v5 import area

BOUNDS = (-60., -90., 60., -12.)
SURFACES = {'asphalt 15s road detail', 'gutter 15s road detail',
            'pavement_0 unified road', 'parking mapped land use',
            'park mapped land use', 'gravel mapped land use'}
DETAILS = {MARKS, 'Close detail iron', 'Close detail rim', 'Close detail silver',
           'Close detail white', 'Close detail yellow', 'Skywalk visible detail dark',
           'Skywalk visible detail seam', 'Skywalk visible detail steel'}
RAILS = PREFIX+'rails'
JOINTS = PREFIX+'plinth-joints'
TRAFFIC_PREFIX = 'Tokyo traffic \u2022 '
TRAFFIC = {TRAFFIC_PREFIX+k for k in ('black','white','glass','head','tail','plate','kei_plate','rim','tire')}
TARGETS = SURFACES | DETAILS | TRAFFIC | {STONE, PAVING, GROUND, RAILS, JOINTS}
KNOTS = ((-90.,0.), (-70.,2.085), (-55.,3.085), (-33.,4.285),
         (-29.,4.285), (-12.,0.))


def grade(x, y):
    """One displacement for the lot, apron, roads, ground and ground furniture.

    The two retained anchors are the 4.4m south door and 3.2m lot surface.
    The boundary transition joins the inherited flat city. Interior soil is
    excluded at the FootTown wall; this is not a regional DEM interpolation.
    """
    if not BOUNDS[0] < x < BOUNDS[2] or not BOUNDS[1] < y < BOUNDS[3]:
        return 0.
    for (a,za),(b,zb) in zip(KNOTS,KNOTS[1:]):
        if a <= y <= b:
            z=za+(zb-za)*smooth((y-a)/(b-a));break
    lateral=1-smooth((abs(x)-48.)/12.)
    interior=max(1-smooth((y+29.)/.25), smooth((abs(x)-36.25)/.25))
    return z*lateral*interior


def cap_slopes(caps):
    from tower_foundation_geometry_v4 import lower_point
    from tower_registration_geometry_v6 import point
    from tower_ground_geometry_v7 import lift
    result=[]
    for c in caps:
        sx,sy=[1 if q>0 else -1 for q in c['center']]
        def node(z):
            w=47.5+(40.8-47.5)*z/15
            return lift(point(lower_point((sx*w,sy*w,z)),caps))
        a,b=node(2),node(7)
        result.append(tuple((b[i]-a[i])/(b[2]-a[2]) for i in (0,1)))
    return result


def incline(p, caps, slopes):
    x,y,z=p
    i=min(range(len(caps)),key=lambda j:math.dist((x,y),caps[j]['center']))
    dx,dy=slopes[i]
    return x+(z-7)*dx,y+(z-7)*dy,z


def cladding_vertices(vertices, caps, slopes):
    """Sink the four lower rings below the inherited north depression.

    The hidden -2.1m termination is a modeling closure, not foundation depth.
    Moving the old lower ring sideways alone would leave a visible air gap.
    """
    if len(vertices)!=64:raise ValueError('Expected four 16-vertex plinth shells')
    return [incline((x,y,-2.1 if i%16<4 else z),caps,slopes)
            for i,(x,y,z) in enumerate(vertices)]


def vehicle_pose(car):
    """Rigid tangent pose from the four wheel locations; keeps the source yaw."""
    from tower_footway_geometry_v5 import local,ANGLE
    x,y,z=local((*car['xy'],car['z']));theta=car['yaw']+ANGLE
    c,s=math.cos(theta),math.sin(theta);a=car['length']/2-.72;b=car['width']/2-.02
    samples=[(u,v,grade(x+c*u-s*v,y+s*u+c*v)) for u in (-a,a) for v in (-b,b)]
    mean=sum(h for u,v,h in samples)/4
    along=sum(u*h for u,v,h in samples)/sum(u*u for u,v,h in samples)
    across=sum(v*h for u,v,h in samples)/sum(v*v for u,v,h in samples)
    gx=c*along-s*across;gy=s*along+c*across
    def norm(p):
        d=math.sqrt(sum(q*q for q in p));return tuple(q/d for q in p)
    e=norm((c,s,along));n=norm((-gx,-gy,1.))
    f=(n[1]*e[2]-n[2]*e[1],n[2]*e[0]-n[0]*e[2],n[0]*e[1]-n[1]*e[0])
    return dict(center=(x,y,z),cos=c,sin=s,axes=(e,f,n),height=mean,lift=0.)


def vehicle_point(world_point, pose):
    from tower_footway_geometry_v5 import local,world
    p=local(world_point);x,y,z=pose['center'];c,s=pose['cos'],pose['sin']
    a=c*(p[0]-x)+s*(p[1]-y);b=-s*(p[0]-x)+c*(p[1]-y);h=p[2]-z
    e,f,n=pose['axes'];q=[pose['center'][i]+a*e[i]+b*f[i]+h*n[i] for i in range(3)]
    q[2]+=pose['height']+pose['lift'];return world(q)


def clip_convex(poly, ring):
    """Subtract a CCW convex XY mask, interpolating original 3D positions."""
    inside=list(poly);outside=[]
    for a,b in zip(ring,ring[1:]+ring[:1]):
        if not inside:break
        dx,dy=b[0]-a[0],b[1]-a[1]
        def half(sign):
            result=[]
            for p,q in zip(inside,inside[1:]+inside[:1]):
                dp=sign*(dx*(p[1]-a[1])-dy*(p[0]-a[0]))
                dq=sign*(dx*(q[1]-a[1])-dy*(q[0]-a[0]))
                if dp>=0:result.append(p)
                if (dp<0)!=(dq<0):
                    t=dp/(dp-dq);result.append(tuple(p[k]+t*(q[k]-p[k]) for k in range(3)))
            clean=[]
            for p in result:
                if not clean or math.dist(p,clean[-1])>1e-8:clean.append(p)
            if len(clean)>1 and math.dist(clean[0],clean[-1])<1e-8:clean.pop()
            return clean
        part=half(-1)
        if area(part)>1e-8:outside.append(part)
        inside=half(1)
    return outside


def subdivide(triangle, length=1.):
    """Densify only the local replacement; preserve its piecewise planar source."""
    stack=[triangle]
    while stack:
        a,b,c=stack.pop()
        if max(math.dist(a[:2],b[:2]),math.dist(b[:2],c[:2]),math.dist(c[:2],a[:2]))<=length:
            yield a,b,c
        else:
            ab=tuple((a[k]+b[k])/2 for k in range(3))
            bc=tuple((b[k]+c[k])/2 for k in range(3))
            ca=tuple((c[k]+a[k])/2 for k in range(3))
            stack.extend(((a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)))


def components(vertices, faces):
    parent=list(range(len(vertices)))
    def root(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for f in faces:
        r=root(f[0])
        for i in f[1:]:parent[root(i)]=r
    groups={}
    for i in range(len(vertices)):groups.setdefault(root(i),[]).append(i)
    return list(groups.values())
