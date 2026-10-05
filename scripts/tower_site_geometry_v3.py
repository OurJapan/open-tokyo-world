# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Source-guided site/roof additions in the inherited tower construction frame.

The four-metre relative site rise is supported by GSI samples. Exact edges,
roof service-room dimensions and the interior bridge remain model-fit estimates.
No unverified retail signs, hidden machinery, or measured framing schedule.
"""
from tower_structure_v1 import MeshBuilder, railing

ROTATION_DEGREES = -33.7
MATERIALS = {
    'site-paving': ((.105,.108,.106,1),0,.90),
    'roof-buildings': ((.085,.029,.021,1),.06,.72),
    'equipment': ((.55,.59,.59,1),.65,.34),
    'vents': ((.028,.032,.030,1),.30,.60),
    'roof-slabs': ((.34,.34,.30,1),0,.85),
    'deck-bridge': ((.18,.17,.15,1),0,.82),
    'deck-guards': ((.50,.055,.012,1),.30,.44),
}


def grade_cell(b, corners):
    """Solid under a four-corner, planar paving patch; no open underside."""
    b.add('site-paving', [(x,y,-.06) for x,y,z in corners]+corners,
          [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])


def site_geometry(b):
    # Southern apron reaches the retained 2F threshold; the sampled south lot
    # is lower than the threshold. Outermost strip fades to the legacy flat city.
    for ya,yb,za,zb,xa,xb in ((-70,-55,.48,2.92,10,36.5),(-55,-36,2.92,4.4,36.5,36.5),(-36,-29,4.4,4.4,36.5,36.5)):
        grade_cell(b,[(-xa,ya,za),(xa,ya,za),(xb,yb,zb),(-xb,yb,zb)])
    # Bound this increment between the south foundations. The west parking
    # area and city-wide terrain need their own registration/height audit.
    # Small facade threshold joins the closed door pair without the old
    # elevated balcony edge/rail blocking the walking connection.
    b.box('site-paving',(0,-28.78,4.37),(16,.48,.06))


def service_building(b,x0,x1,y0,y1,height,door_x):
    low,top=16.2,16.2+height
    # Front door is visibly recessed; side/back walls and roof are separate.
    for a,c in ((x0,door_x-.55),(door_x+.55,x1)):
        b.box('roof-buildings',((a+c)/2,y0,(low+top)/2),(c-a,.20,height))
    b.box('roof-buildings',(door_x,y0,(low+2.2+top)/2),(1.1,.20,height-2.2))
    b.box('equipment',(door_x,y0+.07,low+1.07),(1.02,.055,2.14))
    b.box('vents',(door_x+.32,y0-.035,low+1.1),(.05,.035,.24))
    for x in (x0+.10,x1-.10):
        b.box('roof-buildings',(x,(y0+y1)/2,(low+top)/2),(.20,y1-y0,height))
    b.box('roof-buildings',((x0+x1)/2,y1-.10,(low+top)/2),(x1-x0,.20,height))
    b.box('roof-slabs',((x0+x1)/2,(y0+y1)/2,top+.05),(x1-x0+.20,y1-y0+.20,.10))
    b.box('equipment',((x0+x1)/2,y0-.12,top),(x1-x0+.20,.30,.12))


def roof_geometry(b):
    # Low peripheral buildings in RF plan and retained roof photograph.
    # Their metric dimensions/roof heights are intentionally labelled estimates.
    service_building(b,-35,-23,-1,25,3.5,-29)
    service_building(b,20,27,-.5,5,2.8,23.5)
    service_building(b,28,35,-.5,5,2.8,31.5)
    # Two louvered banks and capped rectangular ductwork west of the central
    # block, leaving its stair doorway/approach entirely open.
    for x in (-19.5,-16.3):
        b.box('vents',(x,10.5,17.55),(2.5,7,2.5))
        b.box('equipment',(x,10.5,18.86),(2.62,7.12,.12))
        for y in (6.98,14.02):
            for i in range(14):
                b.box('equipment',(x,y,16.4+i*.165),(2.32,.06,.035))
        for y in (7.5,13.5):
            b.box('equipment',(x,y,16.36),(2.75,.20,.32))
        b.box('equipment',(x,10.5,19.42),(1.8,2.4,1.0))
        for y in (9.4,10.1,10.8,11.5):
            b.box('vents',(x,y,19.93),(1.65,.045,.015))
    # Exposed side riser and a short horizontal run on the central roof.
    b.beam('equipment',(7.25,-.5,16.3),(7.25,-.5,25.0),.17,12)
    b.beam('equipment',(7.25,-.5,25.0),(6.45,-.5,25.0),.17,12)
    for z in (17,19,21,23):
        b.box('equipment',(7.05,-.5,z),(.45,.5,.08))
    b.beam('equipment',(3.0,1.9,24.7),(6.3,1.9,24.7),.12,12)
    for x in (3.0,6.3):
        b.beam('equipment',(x,1.9,24.2),(x,1.9,24.7),.12,12)


def deck_geometry(b):
    # Existing last landing at (-3.4,4.4,145.1) has no floor leading through
    # the central wall to the passenger ring. Provide a continuous model route.
    b.box('deck-bridge',(-6.675,4.4,145.00),(6.15,1.5,.20))
    for y in (3.63,5.17):
        railing(b,'deck-guards',(-3.97,y,145.1),(-8.80,y,145.1),height=1.05)
    # Open three-sided doorway; no invented closed door across the only route.
    for y in (3.57,5.23):
        b.box('equipment',(-9.05,y,146.30),(.22,.10,2.40))
    b.box('equipment',(-9.05,4.4,147.55),(.22,1.76,.10))


def geometry():
    b=MeshBuilder();site_geometry(b);roof_geometry(b);deck_geometry(b)
    return b.groups


