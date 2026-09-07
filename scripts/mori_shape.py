"""Versioned visual hypothesis for the legacy Mori JP exterior, not survey geometry.

Only explicit feature objects may use this adapter. See patches/mori-shape-v1.json
and docs/mori-shape-review.md for photographic evidence and estimated dimensions.
"""
import math

CENTER = (-430.39, 253.4)
CROWN_OBJECTS = {'Mori continuous pearl glass / '+k for k in ('recessed spandrel','slender mullion','pearl grey coated glass','sealing joint')}
PODIUM_KEYS = ('stone','aluminum','clear glass','gasket','soil','wood','leaf','warm light','ceiling')
TARGETS = CROWN_OBJECTS | {'Mori JP podium / '+k for k in PODIUM_KEYS}


def crown_offset(x, y, z):
    if z <= 205:
        return 0.
    angle = math.atan2(y-CENTER[1], x-CENTER[0])
    petal = math.sin(2*angle)**2
    t = min(1., max(0., (z-205)/113.4))
    # Gradually bend external bands toward the four corner petals; preserve
    # the peak height. Interior slabs remain flat and outside this operation.
    cap = min(1., max(0., (323.4-z)/5.08)) if z>318.32 else 1.
    return -8.0 * (1-petal) * t*t*(3-2*t) * cap


def apply(obj):
    import numpy as np
    import bpy
    if obj.name not in TARGETS or obj.type!='MESH' or obj.data.users!=1 or obj.data.shape_keys:
        raise ValueError('Mori adapter requires an exact, single-user mesh target')
    if any(abs(obj.matrix_world[r][c]-(1 if r==c else 0))>1e-6 for r in range(4) for c in range(4)):
        raise ValueError('Mori legacy adapter requires identity world transform')
    if obj.name in CROWN_OBJECTS:
        coords=np.empty(len(obj.data.vertices)*3,dtype=np.float32)
        obj.data.vertices.foreach_get('co',coords)
        coords=coords.reshape(-1,3)
        for p in coords:
            p[2]+=crown_offset(*p)
        obj.data.vertices.foreach_set('co',coords.ravel()); obj.data.update()
    else:
        # Retain legacy geometry for reversibility; do not add unverified masses
        # over the already present PLATEAU context. Detailed podium is unresolved.
        obj.hide_render=True
