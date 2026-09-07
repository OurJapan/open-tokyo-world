"""Align crown peaks to the four radial corners of the visible legacy contour.

Angles are from the same three-pass smoothing / 256-bay resampling used by
legacy glass_return.py. Heights remain legacy estimates, not surveyed heights.
"""
import math
from mori_shape import CENTER, CROWN_OBJECTS

CORNER_DEGREES = (18.28125, 109.6875, 198.28125, 286.875)
CAP_BASE = 318.32
VALLEY = 323.4
AMPLITUDE = 7.7


def top_height(angle):
    angle = math.degrees(angle) % 360
    points = CORNER_DEGREES + (CORNER_DEGREES[0]+360,)
    if angle < points[0]:
        angle += 360
    for start,end in zip(points,points[1:]):
        if start <= angle <= end:
            t=(angle-start)/(end-start)
            return VALLEY+AMPLITUDE*math.cos(math.pi*t)**2
    raise ValueError('Invalid crown angle')


def corrected_z(x,y,z):
    if z <= CAP_BASE:
        return z
    angle=math.atan2(y-CENTER[1],x-CENTER[0])
    previous_top=VALLEY+AMPLITUDE*math.sin(2*angle)**2
    # Positive scale preserves ordering and the cap-to-facade boundary.
    return CAP_BASE+(z-CAP_BASE)*(top_height(angle)-CAP_BASE)/(previous_top-CAP_BASE)


def apply(obj):
    import numpy as np
    if obj.name not in CROWN_OBJECTS or obj.type!='MESH' or obj.data.users!=1 or obj.data.shape_keys:
        raise ValueError('Crown v2 requires exact single-user visible-facade meshes')
    if obj.hide_render:
        raise ValueError('Refusing to repair an invisible crown')
    if any(abs(obj.matrix_world[r][c]-(1 if r==c else 0))>1e-6 for r in range(4) for c in range(4)):
        raise ValueError('Crown v2 requires the legacy identity transform')
    coords=np.empty(len(obj.data.vertices)*3,dtype=np.float32)
    obj.data.vertices.foreach_get('co',coords);coords=coords.reshape(-1,3)
    for p in coords:
        p[2]=corrected_z(*p)
    obj.data.vertices.foreach_set('co',coords.ravel());obj.data.update()
