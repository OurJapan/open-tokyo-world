# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Photo-guided visible upper lift fittings; not a surveyed shaft assembly.

The installer photograph T_018 shows flanged steel and joint plates near the
car; it does not identify every shaft-specific member. Guide fittings are
construction interpolations. Neither it nor the reinforcement elevation
establishes the complete frame schedule. The existing inferred footprint and
bay rhythm are retained, explicitly as modelling dimensions. Hidden traction
equipment and the unlocated counterweight are not fabricated from that photo.
"""
def oriented_box(b, group, a, end, width, depth, offset=(0, 0)):
    from tower_structure_v1 import unit, sub, cross
    axis = unit(sub(end, a))
    u = unit(cross((0, 0, 1) if abs(axis[2]) < .98 else (0, 1, 0), axis))
    v = cross(axis, u)
    vertices = [tuple(p[k] + (x*width/2+offset[0])*u[k] +
                      (y*depth/2+offset[1])*v[k] for k in range(3))
                for p in (a, end) for x, y in ((-1,-1),(1,-1),(1,1),(-1,1))]
    b.add(group, vertices, [(0,3,2,1),(4,5,6,7),(0,1,5,4),
                            (1,2,6,5),(2,3,7,6),(3,0,4,7)])


def i_member(b, group, a, end, width=.20, depth=.28, flange=.018, web=.014):
    """Three closed steel plates, with the actual open I-shaped silhouette."""
    oriented_box(b, group, a, end, web, depth-2*flange)
    for sign in (-1, 1):
        oriented_box(b, group, a, end, width, flange,
                     offset=(0, sign*(depth-flange)/2))


def angle_member(b, group, a, end, size=.085, thickness=.012):
    oriented_box(b, group, a, end, size, thickness,
                 offset=(0, -(size-thickness)/2))
    oriented_box(b, group, a, end, thickness, size-thickness,
                 offset=(-(size-thickness)/2, thickness/2))


def joint(b, x, y, z):
    # Rectangular splice plates / hexagonal heads read at close range. Their
    # size and fastener pattern are inferred; no bolt grade is claimed.
    b.box('upper-shaft-frame', (x, y-.155, z), (.34,.022,.44))
    for dx in (-.105,.105):
        for dz in (-.135,.135):
            b.beam('upper-shaft-frame', (x+dx,y-.167,z+dz),
                   (x+dx,y-.193,z+dz), .023, 6)


def service_stairs(b):
    """Observed adjacent stair route, with explicitly inferred flights/widths.

    The 2021 exterior panorama resolves stairs and landings but cannot support
    measuring their count. These 50 short flights fit the existing deck span
    and the two inferred rescue levels; they are not an as-built stair survey.
    """
    from tower_structure_v1 import railing
    levels = [154.0]
    for low,high,count in ((154,184,16),(184,217,18),(217,246.1,16)):
        levels.extend(low+(high-low)*i/count for i in range(1,count+1))
    for i,(low,high) in enumerate(zip(levels,levels[1:])):
        sign=1 if i%2 == 0 else -1
        # Narrow maintenance flights stay inside the inherited upper trusses.
        y=2.33 if sign == 1 else 3.00
        for j in range(10):
            b.box('upper-service-stairs',(sign*(-1.15+(j+.5)*.23),y,
                                         low+(high-low)*(j+1)/10-.025),(.245,.60,.05))
        for yy in (y-.31,y+.31):
            angle_member(b,'upper-service-stairs',(-sign*1.15,yy,low-.08),
                         (sign*1.15,yy,high-.08),.075,.010)
            railing(b,'upper-service-stairs',(-sign*1.15,yy,low),
                    (sign*1.15,yy,high),height=1.0,spacing=.65)
        b.box('upper-service-stairs',(sign*1.50,2.665,high-.045),(.70,1.27,.09))
        railing(b,'upper-service-stairs',(sign*1.84,2.03,high),
                (sign*1.84,3.30,high),height=1.0)
    b.box('upper-service-stairs',(-1.50,2.665,153.955),(.70,1.27,.09))
    for x in (-1.84,1.84):
        for y in (2.03,3.30):
            angle_member(b,'upper-service-stairs',(x,y,154),(x,y,246.1),.09,.012)


def geometry(b):
    from tower_structure_v1 import UPPER_BOTTOM, UPPER_TOP, RESCUE_LEVELS, tower_half_width, railing
    from tower_lift_car_v2 import upper_car_geometry
    half = 1.8
    levels = [UPPER_BOTTOM+i*(UPPER_TOP-UPPER_BOTTOM)/24 for i in range(25)]
    for x in (-half,half):
        for y in (-half,half):
            i_member(b,'upper-shaft-frame',(x,y,UPPER_BOTTOM),(x,y,UPPER_TOP),.24,.28)
    for a,z in zip(levels,levels[1:]):
        rescue_bay = any(a < r+2.5 and z > r for r in RESCUE_LEVELS)
        for sign in (-1,1):
            if not (sign == 1 and any(r < a < r+2.5 for r in RESCUE_LEVELS)):
                i_member(b,'upper-shaft-frame',(-half,sign*half,a),(half,sign*half,a),.16,.24)
            i_member(b,'upper-shaft-frame',(sign*half,-half,a),(sign*half,half,a),.16,.24)
            # The two rails have a visible web, foot and discrete attachment
            # brackets, rather than four indistinguishable rectangular bars.
            b.box('upper-guide-rails',(sign*1.66,0,a+.24),(.28,.20,.025))
            b.box('upper-guide-rails',(sign*1.80,0,a+.15),(.025,.28,.20))
            for yy in (-.08,.08):
                b.box('upper-guide-rails',(sign*1.51,yy,a+.275),(.075,.035,.045))
            i_member(b,'upper-shaft-frame',(sign*half,-half,a+.15),
                     (sign*half,half,a+.15),.12,.16)
            angle_member(b,'upper-shaft-frame',(sign*half,-half,a+.20),(sign*half,half,z-.20))
            joint(b,sign*half,-half,a+.28)
            joint(b,sign*half,half,a+.28)
        if not rescue_bay:
            angle_member(b,'upper-shaft-frame',(-half,half,a+.20),(half,half,z-.20),.10)
    for sign in (-1,1):
        # T profile: flange outside, guide blade projects towards the car shoe.
        b.box('upper-guide-rails',(sign*1.515,0,(UPPER_BOTTOM+UPPER_TOP)/2),
              (.025,.145,UPPER_TOP-UPPER_BOTTOM))
        b.box('upper-guide-rails',(sign*1.46,0,(UPPER_BOTTOM+UPPER_TOP)/2),
              (.085,.018,UPPER_TOP-UPPER_BOTTOM))
    # Seven suspension ropes are a sourced count. Only the visible car-to-top
    # segment is shown. Full-wrap traction lives in an enclosed machine room;
    # the hidden sheaves / return route cannot be placed from available plans.
    for i in range(7):
        x=-.27+i*.09
        b.beam('upper-suspension',(x,0,204.32),(x,0,UPPER_TOP),.012,8)
        b.beam('upper-car-rigging',(x,0,204.23),(x,0,204.41),.027,8)
    for z in (UPPER_BOTTOM,*RESCUE_LEVELS,243.8):
        width=tower_half_width(z)
        for sx in (-1,1):
            for sy in (-1,1):
                i_member(b,'upper-support-links',(sx*half,sy*half,z),
                         (sx*width,sy*width,z),.22,.30)
                angle_member(b,'upper-support-links',(sx*half,sy*half,z-1.8),
                             (sx*width,sy*width,z),.14,.018)
    for z in RESCUE_LEVELS:
        # Two intermediate rescue doorways are sourced. Coordinates, grating
        # layout and access perimeter are explicitly inferred at current scale.
        # Grating bars leave real openings; no opaque box deck fills the shaft.
        for i in range(29):
            x=-2.8+(i+.5)*5.6/29
            b.box('upper-platforms',(x,2.52,z-.045),(.04,1.56,.09))
        for yy in (1.77,2.52,3.27):
            b.box('upper-platforms',(0,yy,z-.075),(5.6,.04,.10))
        for sign in (-1,1):
            x=sign*2.30
            for i in range(15):
                yy=-.7+(i+.5)*2.45/15
                b.box('upper-platforms',(x,yy,z-.045),(1.0,.04,.09))
            for xx in (sign*1.81,sign*2.79):
                b.box('upper-platforms',(xx,.52,z-.075),(.04,2.45,.10))
            railing(b,'upper-platforms',(sign*2.8,-.7,z),(sign*2.8,3.3,z))
            i_member(b,'upper-shaft-frame',(sign*1.8,-.7,z-.18),
                     (sign*1.8,3.3,z-.18),.16,.24)
            angle_member(b,'upper-shaft-frame',(sign*1.8,1.8,z-1.1),
                         (sign*2.7,3.15,z-.2),.10)
        # Keep the return landing clear: a continuous rear rail would cut
        # across the adjacent stair route at both inferred rescue levels.
        railing(b,'upper-platforms',(-2.8,3.3,z),(-1.91,3.3,z))
        railing(b,'upper-platforms',(-1.09,3.3,z),(2.8,3.3,z))
        i_member(b,'upper-shaft-frame',(-2.8,3.2,z-.18),(2.8,3.2,z-.18),.16,.24)
        # Landing door: distinct sill, two opaque leaves and a three-sided jamb.
        b.box('upper-landing-doors',(0,1.60,z-.035),(1.36,.38,.07))
        for x in (-.285,.285):
            b.box('upper-landing-doors',(x,1.58,z+1.045),(.56,.045,2.05))
        for x in (-.65,.65):
            b.box('upper-landing-doors',(x,1.58,z+1.10),(.12,.20,2.20))
        b.box('upper-landing-doors',(0,1.58,z+2.23),(1.42,.22,.14))
        for x in (-.76,.76):
            b.box('upper-shaft-frame',(x,1.77,z+1.16),(.10,.12,2.32))
        b.box('upper-shaft-frame',(0,1.77,z+2.38),(1.62,.12,.12))
    service_stairs(b)
    upper_car_geometry(b)
