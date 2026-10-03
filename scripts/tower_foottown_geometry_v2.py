# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""FootTown exterior derived from the retained footprint and reference photos.

Observed: mostly blank brown upper walls, staggered small windows, a central
open mesh screen, two-storey aluminium entrance face, deep canopy and tall
square columns, recessed door groups, a separate low south canopy/ducts,
vertical roof guards, and a brown roof service building around the lift.
All coordinates except the supplied 1.55 m door clear width are scene-fit
estimates; no surveyed footprint, elevation or facade schedule is claimed.
The south stair is an adaptation to the inherited flat terrain, not a claim
about the actual site's grading or accessibility. Logos and tenants omitted.

The main body is authored with front=-Y then rotated 180 degrees to world +Y.
This approximate north/east-approach registration does not rotate the retained
73 x 58 m footprint. The roof core stays in world coordinates to keep the
existing lift and stair access. Only closed boxes/capped beams are emitted.
"""

import math


GROUPS = ("foottown-shell", "foottown-glazing", "foottown-metal", "foottown-roof",
          "foottown-cladding", "foottown-joints", "foottown-screen")
SHELL, GLASS, METAL, ROOF, CLADDING, JOINTS, SCREEN = GROUPS
MATERIALS = {
    SHELL: dict(base_color=(.085, .029, .021, 1), metallic=.06, roughness=.72, transmission=0),
    GLASS: dict(base_color=(.24, .34, .34, 1), metallic=.05, roughness=.09, transmission=.68),
    METAL: dict(base_color=(.64, .69, .70, 1), metallic=.72, roughness=.29, transmission=0),
    ROOF: dict(base_color=(.34, .34, .30, 1), metallic=0, roughness=.85, transmission=0),
    CLADDING: dict(base_color=(.58, .58, .53, 1), metallic=.35, roughness=.42, transmission=0),
    JOINTS: dict(base_color=(.012, .012, .010, 1), metallic=.08, roughness=.78, transmission=0),
    SCREEN: dict(base_color=(.63, .66, .58, 1), metallic=.45, roughness=.52, transmission=0),
}
FOOTPRINT = (73.0, 58.0)
ROOF_TOP = 16.2
SHAFT_HALF = 2.35
DOOR_CLEAR_WIDTH = 1.55
MAIN_ENTRY_CENTRES = (-16.0, -5.5, 5.5, 16.0)  # Design coordinates; sign reverses in world.
ROOF_ACCESS_CLEAR = ((-12.0, -4.8), (3.1, 5.7), (16.2, 18.5))


class _BodyRegistration:
    """Keep facade registration separate from the world-fixed roof core."""
    def __init__(self, builder):
        self.builder = builder

    def box(self, group, center, size):
        self.builder.box(group, (-center[0], -center[1], center[2]), size)

    def beam(self, group, a, b, radius, sides=8):
        self.builder.beam(group, (-a[0], -a[1], a[2]), (-b[0], -b[1], b[2]), radius, sides=sides)


def _rect(b, group, axis, normal, lo, hi, bottom, top, depth):
    center = [(lo + hi) / 2, normal, (bottom + top) / 2]
    size = [hi - lo, depth, top - bottom]
    if axis:
        center[0], center[1] = center[1], center[0]
        size[0], size[1] = size[1], size[0]
    b.box(group, tuple(center), tuple(size))


def _wall(b, group, axis, normal, lo, hi, bottom, top, openings=(), depth=.24):
    """Opaque wall rectangles leave true holes for doors, windows and vents."""
    cuts = sorted({bottom, top} | {v for _, _, z0, z1, _ in openings for v in (z0, z1)})
    for z0, z1 in zip(cuts, cuts[1:]):
        mid = (z0 + z1) / 2
        holes = sorted((a, c) for a, c, low, high, _ in openings if low < mid < high)
        cursor = lo
        for a, c in holes + [(hi, hi)]:
            if a > cursor + 1e-8:
                _rect(b, group, axis, normal, cursor, a, z0, z1, depth)
            cursor = c


def _subtract(lo, hi, intervals):
    cursor = lo
    for a, c in sorted(intervals):
        a, c = max(lo, a), min(hi, c)
        if c <= lo or a >= hi:
            continue
        if a > cursor:
            yield cursor, a
        cursor = max(cursor, c)
    if hi > cursor:
        yield cursor, hi


def _panel_joints(b, axis, normal, lo, hi, bottom, top, openings, x_pitch=2.7):
    """Panel seams terminate at openings instead of crossing glass or doors."""
    count = math.ceil((hi - lo) / x_pitch)
    for index in range(1, count):
        x = lo + (hi - lo) * index / count
        holes = [(z0, z1) for a, c, z0, z1, _ in openings if a-.015 < x < c+.015]
        for z0, z1 in _subtract(bottom, top, holes):
            _rect(b, JOINTS, axis, normal, x-.008, x+.008, z0, z1, .014)
    for z in (2.2, 3.7, 4.4, 6.7):
        if not bottom < z < top:
            continue
        holes = [(a, c) for a, c, z0, z1, _ in openings if z0-.01 < z < z1+.01]
        for a, c in _subtract(lo, hi, holes):
            _rect(b, JOINTS, axis, normal, a, c, z-.008, z+.008, .014)


def _opening(b, axis, normal, item, inward=1, flush_threshold=False):
    """One framed aperture; door groups contain fixed sides and a 1.55 m pair."""
    lo, hi, bottom, top, kind = item
    center = (lo + hi) / 2
    if kind == "vent":
        _rect(b, JOINTS, axis, normal + inward*.025, lo, hi, bottom, top, .035)
        count = math.ceil((top-bottom)/.13)
        for i in range(count):
            z = bottom + (i+.5)*(top-bottom)/count
            _rect(b, METAL, axis, normal-inward*.025, lo+.045, hi-.045, z-.018, z+.018, .045)
        return
    frame = .065 if kind == "door" else .045
    for a, c in ((lo, lo+frame), (hi-frame, hi)):
        _rect(b, METAL, axis, normal, a, c, bottom, top, .22)
    # Main doors meet the retained flat ground: the 15 mm threshold sits
    # within the finish slab, rather than lifting the glass above a step.
    sill = (bottom-.015, bottom) if flush_threshold else (bottom, bottom+frame)
    pane_bottom = bottom if flush_threshold else bottom+frame
    for z0, z1 in (sill, (top-frame, top)):
        _rect(b, METAL, axis, normal, lo+frame, hi-frame, z0, z1, .22)
    if kind == "metal-door":
        _rect(b, METAL, axis, normal+inward*.04, lo+frame, hi-frame, bottom+frame, top-frame, .07)
        _rect(b, JOINTS, axis, normal-inward*.002, center-.008, center+.008, bottom+frame, top-frame, .016)
        return
    if kind == "door":
        # The specified clear width belongs to one automatic-door pair, not
        # the width of the entire fixed-glass entrance bay.
        split = DOOR_CLEAR_WIDTH / 2
        spans = ((lo+frame, center-split-.05), (center-split, center-.012),
                 (center+.012, center+split), (center+split+.05, hi-frame))
        for a, c in ((center-split-.05, center-split), (center+split, center+split+.05)):
            _rect(b, METAL, axis, normal, a, c, pane_bottom, top-frame, .16)
        _rect(b, JOINTS, axis, normal+inward*.06, center-.012, center+.012, pane_bottom, top-frame, .028)
    else:
        count = max(1, round((hi-lo)/1.7))
        pane_width = (hi-lo-frame*(count+1))/count
        spans = []
        for i in range(count):
            a = lo+frame+i*(pane_width+frame)
            spans.append((a, a+pane_width))
            if i+1 < count:
                _rect(b, METAL, axis, normal, a+pane_width, a+pane_width+frame, bottom+frame, top-frame, .12)
    for a, c in spans:
        _rect(b, GLASS, axis, normal+inward*.075, a, c, pane_bottom, top-frame, .025)


def _roof_with_hole(b, xmin, xmax, ymin, ymax, top, thickness=.20):
    for a, c in ((ymin, -SHAFT_HALF), (SHAFT_HALF, ymax)):
        b.box(ROOF, ((xmin+xmax)/2, (a+c)/2, top-thickness/2), (xmax-xmin, c-a, thickness))
    for a, c in ((xmin, -SHAFT_HALF), (SHAFT_HALF, xmax)):
        b.box(ROOF, ((a+c)/2, 0, top-thickness/2), (c-a, SHAFT_HALF*2, thickness))


def _canopy(b, xmin, xmax, ymin, ymax, top, thickness=.28):
    b.box(METAL, ((xmin+xmax)/2, (ymin+ymax)/2, top-.055), (xmax-xmin, ymax-ymin, .11))
    # Dark backing keeps thin joints legible beneath the aluminium soffit.
    b.box(JOINTS, ((xmin+xmax)/2, (ymin+ymax)/2, top-thickness+.075), (xmax-xmin-.08, ymax-ymin-.08, .035))
    nx, ny = math.ceil((xmax-xmin)/2.8), math.ceil((ymax-ymin)/2.0)
    dx, dy = (xmax-xmin)/nx, (ymax-ymin)/ny
    for i in range(nx):
        for j in range(ny):
            b.box(CLADDING, (xmin+(i+.5)*dx, ymin+(j+.5)*dy, top-thickness+.035), (dx-.016, dy-.016, .07))
    for y in (ymin+.04, ymax-.04):
        b.box(METAL, ((xmin+xmax)/2, y, top-thickness/2), (xmax-xmin, .08, thickness))
    for x in (xmin+.04, xmax-.04):
        b.box(METAL, (x, (ymin+ymax)/2, top-thickness/2), (.08, ymax-ymin-.16, thickness))


def _screen(b):
    # Real openings, not a white solid panel. Brown wall remains visible .1 m behind.
    xmin, xmax, zmin, zmax, y = -14.0, 14.0, 7.56, 16.14, -29.13
    pitch = .05
    for slope in (-1, 1):
        first = zmin-xmax if slope == 1 else zmin+xmin
        last = zmax-xmin if slope == 1 else zmax+xmax
        for index in range(math.ceil((last-first)/pitch)+1):
            c = first+index*pitch
            a = max(xmin, zmin-c) if slope == 1 else max(xmin, c-zmax)
            end = min(xmax, zmax-c) if slope == 1 else min(xmax, c-zmin)
            if end-a > .03:
                b.beam(SCREEN, (a,y,slope*a+c), (end,y,slope*end+c), .004, sides=4)
    for i in range(25):
        x = xmin+(xmax-xmin)*i/24
        b.box(METAL, (x, y-.025, (zmin+zmax)/2), (.038,.055,zmax-zmin))
    for i in range(5):
        z = zmin+(zmax-zmin)*i/4
        b.box(METAL, (0,y-.025,z), (xmax-xmin,.055,.04))


def _main_front(b):
    upper = [(x-.38,x+.38,z,z+.68,"window") for x,z in
             ((-31,14.5),(-25.5,13.6),(-20.5,14.5),(-16.7,13.6),
              (17.3,14.5),(22.5,13.6),(27,14.5),(32,13.6))]
    _wall(b,SHELL,0,-28.88,-36.5,36.5,7.27,16.0,upper)
    for item in upper:
        _opening(b,0,-28.95,item)
    for lo,hi in ((-36.5,-28.0),(28.0,36.5)):
        _wall(b,SHELL,0,-28.88,lo,hi,0,7.27)
    openings = [(x-2.2,x+2.2,.02,3.45,"door") for x in MAIN_ENTRY_CENTRES]
    openings += [(x-3.3,x+3.3,4.4,6.45,"window") for x in (-17.5,-5.5,5.5,17.5)]
    _wall(b,CLADDING,0,-27.08,-28.0,28.0,0,7.27,openings)
    _panel_joints(b,0,-27.208,-28,28,.02,7.27,openings)
    for item in openings:
        _opening(b,0,-27.045,item,flush_threshold=item[-1]=="door")
    for x in (-28.0,28.0):
        b.box(CLADDING,(x,-28.02,3.635),(.24,1.80,7.27))
    # Local Blender raycasts put the existing main approach ground at z=0.
    # This flush finish adapts the facade to that scene, not to surveyed grades.
    b.box(ROOF,(0,-30.05,.01),(56.0,6.5,.02))
    _canopy(b,-28.5,28.5,-33.15,-26.9,7.55)
    for x in (-24.0,-8.0,8.0,24.0):
        b.box(METAL,(x,-32.70,3.625),(.64,.66,7.25))
        # Shallow translucent column strip seen in the entrance photograph.
        b.box(JOINTS,(x,-33.039,4.22),(.31,.018,5.25))
        b.box(GLASS,(x,-33.057,4.22),(.285,.018,5.25))
        for dx in (-.18,.18):
            b.box(METAL,(x+dx,-33.066,4.22),(.055,.026,5.34))
    for z in (7.40,13.15,16.015):
        b.box(METAL,(0,-29.014,z),(73,.028,.06))
    _screen(b)


def _south_face(b):
    # Separate second-floor entry; the flat-site external stair is an adaptation.
    openings = [(x-2.2,x+2.2,4.4,7.08,"door") for x in (-5.0,5.0)]
    openings += [(x-.70,x+.70,10.0,10.5,"vent") for x in (-16,17)]
    _wall(b,SHELL,0,28.88,-36.5,36.5,0,16,openings)
    for item in openings:
        _opening(b,0,28.96,item,inward=-1)
    _canopy(b,-13,13,28.70,32.1,7.43,.25)
    b.box(ROOF,(0,30.20,4.30),(16,2.40,.20))
    for x in (-7.3,0,7.3):
        b.box(METAL,(x,31.60,3.715),(.20,.20,7.43))
        b.box(METAL,(x,30.15,2.15),(.22,.22,4.30))
    # Flat-site adaptation: 25 estimated .1752 m rises from .02 to 4.4 m.
    for i in range(25):
        x = 14.2-(i+.5)*6.2/25
        top = .02+(i+1)*4.38/25
        b.box(ROOF,(x,30.4,top-.045),(6.2/25+.018,1.4,.09))
    for y in (29.67,31.13):
        b.box(METAL,(14.2,y,.03),(.22,.22,.06))
        b.beam(METAL,(14.2,y,.075),(8.0,y,4.275),.065)
        b.beam(METAL,(14.2,y,1.07),(8.0,y,5.45),.032)
        for i in range(12):
            t=i/11
            x,z=14.2-6.2*t,.02+4.38*t
            b.beam(METAL,(x,y,z),(x,y,z+1.05),.022)
    for a,c in ((-8.0,7.8),):
        b.beam(METAL,(a,31.38,5.45),(c,31.38,5.45),.032)
        for i in range(20):
            x=a+(c-a)*i/19
            b.beam(METAL,(x,31.38,4.4),(x,31.38,5.45),.022)
    # South-photo handedness after body registration: from outside, the
    # U-shaped run is high on the right; the separate T-shaped run is left.
    b.box(METAL,(2.0,29.25,9.20),(18.0,.50,.58))
    b.box(METAL,(-7.0,29.25,12.35),(.60,.50,6.88))
    b.box(METAL,(11.0,29.25,10.12),(.60,.50,2.42))
    b.box(METAL,(21.0,29.25,13.55),(.65,.50,4.70))
    b.box(METAL,(24.3,29.25,15.58),(7.25,.50,.65))
    for x in range(-10,8,2):
        b.box(METAL,(-x,29.52,9.20),(.045,.05,.64))
    for z in (9.5,10.8,12.1,13.4,14.7):
        b.box(METAL,(-7.0,29.52,z),(.66,.05,.045))


def _roof_edge(b):
    corners=((-36.20,-28.70),(36.20,-28.70),(36.20,28.70),(-36.20,28.70))
    for a,c in zip(corners,corners[1:]+corners[:1]):
        length=math.dist(a,c)
        along_x=abs(c[0]-a[0])>.1
        b.box(SHELL,((a[0]+c[0])/2,(a[1]+c[1])/2,16.36),
              (length if along_x else .20,.20 if along_x else length,.32))
        # The photos distinguish solid brown edge sections from open pickets.
        # Their precise lengths/heights are unavailable; these shallow front
        # wings retain the inherited roof rather than inventing a full fence plan.
        if along_x and a[1] > 0:
            for lo,hi in ((-36.2,-14.3),(14.3,36.2)):
                b.box(SHELL,((lo+hi)/2,28.70,16.66),(hi-lo,.20,.28))
        for z,r in ((16.55,.021),(17.275,.025)):
            b.beam(METAL,(*a,z),(*c,z),r)
        count=math.ceil(length/.24)
        for i in range(count+1):
            t=i/count
            x,y=a[0]+(c[0]-a[0])*t,a[1]+(c[1]-a[1])*t
            b.box(METAL,(x,y,16.905),(.018,.018,.71))
        count=math.ceil(length/2.2)
        for i in range(count):
            t=(i+.5)/count
            b.box(METAL,(a[0]+(c[0]-a[0])*t,a[1]+(c[1]-a[1])*t,16.91),(.045,.045,.78))


def _roof_core(b):
    """World-fixed inferred 14 x 7.1 m service building; existing stairs stay north."""
    front=[(x-.62,x+.62,16.2,18.68,"metal-door") for x in (-4.7,-1.7,1.3,4.3)]
    front += [(x-.28,x+.28,z,z+.65,"window") for x,z in ((-5.6,22.0),(-3.3,22.2),(-.9,22.4),(1.4,22.6),(3.25,19.8),(5.35,19.8))]
    front += [(3.0,6.1,21.2,23.35,"vent")]
    _wall(b,SHELL,0,-4.38,-7,7,16.2,24.2,front)
    for item in front:
        _opening(b,0,-4.42,item)
    _wall(b,SHELL,0,2.48,-7,7,16.2,24.2)
    for x in (-6.88,6.88):
        _wall(b,SHELL,1,x,-4.26,2.36,16.2,24.2)
    _roof_with_hole(b,-7,7,-4.5,2.6,24.2,.18)
    _canopy(b,-7.05,7.05,-6.9,-4.25,19.30,.20)
    for x in (-6.2,-1.7,2.0,6.2):
        b.beam(METAL,(x,-6.65,19.30),(x,-4.48,20.40),.035)
    b.box(METAL,(0,-4.515,20.88),(14,.04,.075))
    b.box(METAL,(0,-4.515,24.20),(14,.04,.09))
    # The source shows roof machinery beside the lift, rather than four equal
    # corner boxes. This low enclosure and its vents remain a layout estimate.
    b.box(METAL,(4.70,-.40,24.77),(2.60,2.10,1.14))
    for z in (24.35,24.52,24.69,24.86,25.03,25.20):
        b.box(JOINTS,(4.7,-1.456,z),(2.35,.014,.055))
    b.box(SHELL,(6.85,-.90,24.64),(.30,7.20,.88))


def south_handrail_junction(builder):
    """Join existing stair/landing rail ends in the inherited world frame."""
    builder.beam(METAL,(-8.0,-31.13,5.45),(-7.8,-31.38,5.45),.032)


def geometry(builder):
    """Create the seven material groups, preserving the roof lift/stair interfaces."""
    b=_BodyRegistration(builder)
    b.box(SHELL,(0,0,.01),(73,58,.02))
    _main_front(b)
    _south_face(b)
    # The side faces remain deliberately plain; undocumented repetitive windows
    # from the previous approximation are not propagated around the building.
    for x in (-36.38,36.38):
        _wall(b,SHELL,1,x,-28.76,28.76,0,16.0)
    _roof_with_hole(builder,-36.5,36.5,-29,29,ROOF_TOP)
    _roof_edge(builder)
    _roof_core(builder)
    # Append one solid so the existing PR60 geometry remains an exact prefix.
    south_handrail_junction(builder)
