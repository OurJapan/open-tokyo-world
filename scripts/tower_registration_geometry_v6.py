# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Map estimated lower supports onto visible mapped plinth rectangles."""
from tower_foundation_geometry_v4 import STONE,STEEL,PLATES
TARGETS={STONE,STEEL,PLATES}

def point(p,caps,stone=False):
    x,y,z=p
    if not stone and z>=30.:return tuple(p)
    sx,sy=(1 if x>0 else -1),(1 if y>0 else -1)
    c=next(c for c in caps if c['quadrant']==[sx,sy])
    dx=(x-sx*44)*c['size'][0]/10.5;dy=(y-sy*44)*c['size'][1]/10.5
    q=[c['center'][i]+dx*c['u'][i]+dy*c['v'][i] for i in (0,1)]
    t=max(0.,min(1.,(z-2.)/28.));weight=1. if stone else 1.-t*t*(3.-2.*t)
    return x+(q[0]-x)*weight,y+(q[1]-y)*weight,z
