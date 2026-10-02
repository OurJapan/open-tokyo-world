# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Photo-guided upper lift cabin and approximate exterior suspension frame.

Observed interior arrangement: Mitsubishi detail image 26, figure 7, and
Elevator Journal No.19 (2018.4), printed page 17. There is one rear glass pane and
two on the right when looking into the cabin from its doors, stainless
steel on the other walls, low window trim, handrails, and a mirror ceiling.
The roof, sling, guide shoes, all dimensions and the closed door pose are
construction interpolations, not surveyed dimensions or engineering CAD.
In particular the T rail and shoe sections are not claimed as photo-confirmed.

The caller owns materials, rails, seven rope-end fittings and ropes. Fixtures
are represented with metal housings and glass lenses, without an emissive
material. Only the six named groups are emitted; no lower lift is changed.
"""

import math


GROUPS = (
    "upper-car-shell", "upper-car-glass", "upper-car-mirror",
    "upper-car-floor", "upper-car-rigging", "upper-car-dark",
)
WIDTH, DEPTH, CABIN_HEIGHT = 2.45, 2.40, 2.70
GUIDE_X = 1.46
GUIDE_BLADE = (.085, .018)


def _guide_shoe(b, sign, z):
    """Open-outward U shoe: liners touch the nominal T-blade, not its foot."""
    # The rail blade spans |x|=1.4175..1.5025 and |y|<=.009. Its outboard
    # foot begins at |x|=1.5025. Jaws stop at 1.49, clear of that foot.
    b.box(GROUPS[4], (sign * 1.3845, 0, z), (.054, .144, .26))
    b.box(GROUPS[5], (sign * 1.4145, 0, z), (.006, .018, .22))
    for side in (-1, 1):
        b.box(GROUPS[4], (sign * 1.425, side * .0445, z), (.13, .055, .26))
        b.box(GROUPS[5], (sign * 1.44, side * .013, z), (.10, .008, .22))
    b.box(GROUPS[4], (sign * 1.3375, 0, z), (.08, .14, .16))


def upper_car_geometry(b, floor_z=201.0):
    """Emit closed solids for a 2.45 x 2.40 m cabin, doors facing +y.

    The walking floor is ``floor_z`` and mirror underside ``floor_z+2.70``.
    Rigging extends to x=+/-1.49 and z=floor_z-.38..floor_z+3.32.
    Crosshead top receives caller-owned fittings at x=-.27..+.27, y=0.
    """
    if not math.isfinite(floor_z):
        raise ValueError("floor_z must be finite")
    shell, glass, mirror, floor, rigging, dark = GROUPS

    def box(group, center, size):
        b.box(group, (center[0], center[1], floor_z + center[2]), size)

    def beam(group, a, end, radius, sides=12):
        b.beam(group, (a[0], a[1], floor_z + a[2]),
               (end[0], end[1], floor_z + end[2]), radius, sides=sides)

    # Photo-observed cabin arrangement; panel dimensions are proportional estimates.
    box(floor, (0, 0, -.07), (WIDTH, DEPTH, .14))
    for x in (-1.195, 1.195):
        for y in (-1.17, 1.17):
            box(shell, (x, y, 1.35), (.06, .06, CABIN_HEIGHT))
    box(shell, (1.20, 0, 1.35), (.05, 2.28, CABIN_HEIGHT))
    for z in (.025, 2.675):
        box(shell, (0, -1.17, z), (2.33, .06, .05))
        box(shell, (-1.195, 0, z), (.06, 2.28, .05))
    box(shell, (-1.195, 0, 1.35), (.06, .055, 2.60))
    # Exactly three large, full-height panes. The side mullion divides two panes.
    box(glass, (0, -1.188, 1.35), (2.33, .024, 2.60))
    side_width = 1.14 - .0275
    for sign in (-1, 1):
        box(glass, (-1.213, sign * (1.14 + .0275) / 2, 1.35),
            (.024, side_width, 2.60))

    # Stainless entrance face, three-sided frame and two closed centre-opening doors.
    for sign in (-1, 1):
        box(shell, (sign * .95, 1.17, 1.35), (.43, .06, CABIN_HEIGHT))
        box(shell, (sign * .6975, 1.17, 1.175), (.075, .06, 2.35))
        box(shell, (sign * .333, 1.155, 1.155), (.654, .05, 2.23))
    box(dark, (0, 1.156, 1.155), (.012, .048, 2.23))
    box(shell, (0, 1.17, 2.32), (1.47, .06, .10))
    box(shell, (0, 1.17, 2.535), (2.33, .06, .33))
    box(shell, (0, 1.15, .02), (1.47, .10, .04))
    # A shallow dark display inset on the cabin-facing surface; deliberately blank.
    box(dark, (0, 1.133, 2.525), (.50, .012, .16))
    for offset in (-.026, .026):
        box(dark, (0, 1.15 + offset, .0405), (1.30, .008, .001))

    # Low rails and their short mounts sit inside the glazing, not through it.
    beam(shell, (-1.075, -1.05, .95), (1.075, -1.05, .95), .024)
    for x in (-1.065, 1.065):
        beam(shell, (x, -1.04, .95), (x, 1.04, .95), .024)
    for sign in (-1, 1):
        beam(shell, (sign * 1.178, -1.15, .95), (sign * 1.075, -1.05, .95), .014)
        beam(shell, (-1.18, sign * 1.16, .95), (-1.065, sign * 1.04, .95), .014)
        beam(shell, (1.178, sign * 1.04, .95), (1.065, sign * 1.04, .95), .014)

    box(mirror, (0, 0, 2.71), (2.33, 2.28, .02))
    for x in (-.88, .88):
        for y in (-.88, .88):
            beam(shell, (x, y, 2.672), (x, y, 2.70), .075, 16)
            beam(glass, (x, y, 2.660), (x, y, 2.672), .052, 16)

    # Estimated sealed roof service enclosure only, without an opaque cabin wrap.
    box(rigging, (0, 0, 2.735), (WIDTH, DEPTH, .03))
    box(rigging, (0, 0, 2.985), (WIDTH, DEPTH, .03))
    for sign in (-1, 1):
        box(rigging, (sign * 1.20, 0, 2.86), (.05, DEPTH, .22))
        box(rigging, (0, sign * 1.175, 2.86), (2.35, .05, .22))

    # Estimated car sling: underside bearers, two side uprights and crosshead.
    for x in (-.85, .85):
        box(rigging, (x, 0, -.205), (.14, 2.35, .13))
    box(rigging, (0, 0, -.29), (2.73, .22, .18))
    for sign in (-1, 1):
        box(rigging, (sign * 1.305, 0, 1.47), (.12, .16, 3.52))
        _guide_shoe(b, sign, floor_z - .08)
        _guide_shoe(b, sign, floor_z + 2.93)
    box(rigging, (0, 0, 3.23), (2.76, .32, .18))
    # Seven parent-owned fittings overlap this crosshead at z=+3.23..+3.32.
    # Their ropes must remain above the roof, outside the occupied cabin volume.
