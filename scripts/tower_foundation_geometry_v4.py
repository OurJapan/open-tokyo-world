# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Bounded foundation registration and model-ground transition, not a survey."""
from tower_structure_v1 import MeshBuilder

BASE_HALF = 44.0
OLD_JOINT_HALF = 46.6066666667
BLEND_TOP = 52.0
STONE = 'Tokyo Tower structure / stone'
STEEL = 'Tokyo Tower structure / orange'
PLATES = 'OTW Tokyo Tower structure / base-connections'
PAVING = 'OTW Tokyo Tower site v3 / site-paving'
TARGETS = {STONE, STEEL, PLATES, PAVING}


def lower_point(point):
    """Match the 88m base axes; smoothly retain the original frame at 52m."""
    x,y,z=point
    if z >= BLEND_TOP:
        return tuple(point)
    t=max(0.,min(1.,(z-2.)/(BLEND_TOP-2.)))
    ease=t*t*(3.-2.*t)
    factor=BASE_HALF/OLD_JOINT_HALF+(1.-BASE_HALF/OLD_JOINT_HALF)*ease
    return x*factor,y*factor,z


def foundation_point(point):
    x,y,z=point
    return x-(3.5 if x>0 else -3.5),y-(3.5 if y>0 else -3.5),z


def width(y):
    return 4.+(y+70.)*32.5/15. if y < -55. else 36.5


def grid():
    # Additional rows resolve the two measured curb crossings. A coarse grid
    # would interpolate across their step and leave a false edge mismatch.
    ys=sorted(set(range(-70,-28,2))|{-55,-36,-29}|
              {-69.+i/32. for i in range(33)}|{-49.25+i/32. for i in range(17)})
    xs=sorted({j/16.-1. for j in range(33)}|{.15625})
    return [[(width(y)*x,float(y)) for x in xs] for y in ys]


def longitudinal_height(y):
    if y < -55.:
        return .48+(y+70.)*(2.92-.48)/15.
    if y < -36.:
        return 2.92+(y+55.)*(4.4-2.92)/19.
    return 4.4


def surface_height(x,y,ground_z):
    # Keep the doorway approach flat across 32m. Blend down inside the old
    # footprint instead of leaving a four-metre vertical apron side face.
    core=min(16.,width(y)-4.)
    t=max(0.,min(1.,(abs(x)-core)/(width(y)-core)))
    lateral=1.-t*t*(3.-2.*t)
    end=max(0.,min(1.,(y+70.)/2.))
    return ground_z+.015+(longitudinal_height(y)-ground_z-.015)*lateral*end


def paving_mesh(ground):
    rows=grid();nr,nc=len(rows),len(rows[0])
    if len(ground)!=nr or any(len(r)!=nc for r in ground):
        raise ValueError('Ground sample grid differs')
    vertices=[(x,y,surface_height(x,y,ground[i][j])) for i,row in enumerate(rows) for j,(x,y) in enumerate(row)]
    n=len(vertices)
    vertices += [(x,y,-.06) for x,y,z in vertices]
    faces=[]
    for i in range(nr-1):
        for j in range(nc-1):
            a=i*nc+j;b=a+1;c=a+nc+1;d=a+nc
            faces.extend([(a,b,c),(a,c,d),(n+c,n+b,n+a),(n+d,n+c,n+a)])
    edge=list(range(nc))+[i*nc+nc-1 for i in range(1,nr)]+list(range(n-2,n-nc-1,-1))+[i*nc for i in range(nr-2,0,-1)]
    for a,b in zip(edge,edge[1:]+edge[:1]):
        # Triangulate sides too: saved float coordinates never form twisted quads.
        faces.extend([(a,n+a,n+b),(a,n+b,b)])
    builder=MeshBuilder();builder.add('paving',vertices,faces)
    builder.box('paving',(0,-28.78,4.37),(16,.48,.06))
    return builder.groups['paving']
