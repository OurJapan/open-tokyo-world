"""Fixed-profile geometric operations. No silent fallback for missing intersections."""
import math

FEATURE='bldg_433bc5b3-db73-4644-ac24-a28d51b7ecd5'
CENTER=(-430.39,253.4)

def target_index(ids):
    if ids.count(FEATURE)!=1:raise ValueError('Expected exactly one Mori feature')
    return ids.index(FEATURE)

def cross_section(triangles, height=100., count=160):
    import numpy as np
    tri=np.asarray(triangles,dtype=float)
    if tri.ndim!=3 or tri.shape[1:]!=(3,3) or not np.isfinite(tri).all():raise ValueError('Invalid triangles')
    segments=[]
    for t in tri[(tri[:,:,2].min(axis=1)<height)&(tri[:,:,2].max(axis=1)>height)]:
        pts=[]
        for a,b in zip(t,np.roll(t,-1,axis=0)):
            if a[2]<=height<b[2] or b[2]<=height<a[2]:pts.append((a+(b-a)*(height-a[2])/(b[2]-a[2]))[:2])
        if len(pts)!=2:raise ValueError('Invalid section segment')
        segments.append(pts)
    center=np.array(CENTER);radii=[]
    for i in range(count):
        angle=math.tau*i/count;direction=np.array([math.cos(angle),math.sin(angle)])
        hits=[]
        for a,b in segments:
            matrix=np.column_stack((direction,a-b))
            if abs(np.linalg.det(matrix))<1e-10:continue
            radius,t=np.linalg.solve(matrix,a-center)
            if 0<radius<=80 and -1e-8<=t<=1+1e-8:hits.append(float(radius))
        if not hits:raise ValueError('Missing profile ray '+str(i))
        radii.append(max(hits))
    return radii

def lowrise(triangles):
    import numpy as np
    from mori_podium_v3 import truncated_lowrise_edges
    tri=np.asarray(triangles)
    keep=tri[:,:,2].max(axis=1)<=50
    if len(tri)!=1644 or int(keep.sum())!=1070:raise ValueError('Unexpected Mori source face count')
    if truncated_lowrise_edges(tri,keep):raise ValueError('Truncated podium adjacency')
    return tri[keep]
