# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Estimated FootTown exterior, independent of Blender and material creation.

The retained legacy footprint is 73 x 58 m. Four simplified storeys and a roof
are inherited from the earlier model; dimensions, window placement, roof equipment, and
the 1.1 m railing are visual estimates, not survey measurements. The shell
is intended to receive the dark reddish-brown finish visible in the supplied
construction photograph. This does not reproduce signs or interior shops.

``geometry(builder)`` uses only ``box(group, center, size)`` and
``beam(group, start, end, radius, sides=8)``. The caller owns the resulting
meshes and materials. The roof centre is reserved for the tower's separate
lift/stair assembly.
"""

from __future__ import annotations

import math


GROUPS = (
    "foottown-shell",
    "foottown-glazing",
    "foottown-metal",
    "foottown-roof",
)
FOOTPRINT = (73.0, 58.0)
FLOOR_LEVELS = (0.5, 4.4, 8.3, 12.2, 16.0)
ROOF_TOP = 16.2
ROOF_SHAFT_HALF = 2.35
RAILING_HEIGHT = 1.1
_WALL_THICKNESS = 0.3
_COPINGS = ((4.365, 4.435), (8.265, 8.335), (12.165, 12.235), (15.93, 16.0))


def _wall_box(builder, group, axis, normal, lo, hi, bottom, top, depth):
    """Place an axis-aligned wall rectangle along its horizontal axis."""
    center = [(lo + hi) / 2.0, normal, (bottom + top) / 2.0]
    size = [hi - lo, depth, top - bottom]
    if axis == 1:
        center[0], center[1] = center[1], center[0]
        size[0], size[1] = size[1], size[0]
    builder.box(group, tuple(center), tuple(size))


def _facade(builder, axis, sign, span, normal, openings):
    """Cut rectangular openings before inserting their frames and glazing."""
    lo, hi = -span / 2.0, span / 2.0
    cuts = sorted({FLOOR_LEVELS[0], FLOOR_LEVELS[-1]} |
                  {z for _, _, bottom, top, _ in openings for z in (bottom, top)} |
                  {z for band in _COPINGS for z in band})
    for bottom, top in zip(cuts, cuts[1:]):
        middle = (bottom + top) / 2.0
        # Metal replaces each narrow shell strip to avoid coplanar surfaces.
        group = GROUPS[2] if any(z0 < middle < z1 for z0, z1 in _COPINGS) else GROUPS[0]
        holes = sorted((left, right) for left, right, z0, z1, _ in openings
                       if z0 < middle < z1)
        cursor = lo
        for left, right in holes + [(hi, hi)]:
            if left > cursor:
                _wall_box(builder, group, axis, normal, cursor, left,
                          bottom, top, _WALL_THICKNESS)
            cursor = right

    # Frames and panes sit inside the cut opening, with no opaque wall behind.
    frame_normal = normal + sign * 0.05
    glass_normal = normal + sign * 0.065
    frame = 0.065
    for left, right, bottom, top, pane_count in openings:
        for edge0, edge1 in ((left, left + frame), (right - frame, right)):
            _wall_box(builder, GROUPS[2], axis, frame_normal, edge0, edge1,
                      bottom, top, 0.14)
        for z0, z1 in ((bottom, bottom + frame), (top - frame, top)):
            _wall_box(builder, GROUPS[2], axis, frame_normal,
                      left + frame, right - frame, z0, z1, 0.14)
        pane_width = (right - left - frame * (pane_count + 1)) / pane_count
        for index in range(pane_count):
            start = left + frame + index * (pane_width + frame)
            _wall_box(builder, GROUPS[1], axis, glass_normal,
                      start, start + pane_width, bottom + frame, top - frame, 0.06)
            if index + 1 < pane_count:
                _wall_box(builder, GROUPS[2], axis, frame_normal,
                          start + pane_width, start + pane_width + frame,
                          bottom + frame, top - frame, 0.14)


def _perimeter_rails(builder):
    half_x, half_y = FOOTPRINT[0] / 2.0 - 0.35, FOOTPRINT[1] / 2.0 - 0.35
    corners = ((-half_x, -half_y), (half_x, -half_y),
               (half_x, half_y), (-half_x, half_y))
    for a, b in zip(corners, corners[1:] + corners[:1]):
        # The top of the rail, including its radius, is 1.1 m above the roof.
        for height, radius in ((0.53, 0.025), (RAILING_HEIGHT - 0.035, 0.035)):
            builder.beam(GROUPS[2], (*a, ROOF_TOP + height),
                         (*b, ROOF_TOP + height), radius, sides=8)
        length = math.dist(a, b)
        count = math.ceil(length / 1.6)
        for index in range(count):
            ratio = index / count
            point = (a[0] + ratio * (b[0] - a[0]),
                     a[1] + ratio * (b[1] - a[1]))
            builder.beam(GROUPS[2], (*point, ROOF_TOP + 0.04),
                         (*point, ROOF_TOP + RAILING_HEIGHT - 0.035),
                         0.025, sides=8)


def geometry(builder):
    """Build a hollow exterior with a roof and shaft opening at z=16.2 m.

    All output stays within x=+/-36.5 and y=+/-29 m. Above the roof, the
    rectangle x=+/-6 and y=+/-8 m stays free for the central stair/lift core.
    A 4.7 m square opening lets the separate lower lift pass through the roof.
    The ground-level south entrance and small paired windows are estimates.
    """
    half_x, half_y = FOOTPRINT[0] / 2.0, FOOTPRINT[1] / 2.0
    builder.box(GROUPS[0], (0.0, 0.0, 0.425), (*FOOTPRINT, 0.15))
    for sign in (-1, 1):
        builder.box(GROUPS[3], (0.0, sign * (half_y + ROOF_SHAFT_HALF) / 2.0, 16.1),
                    (FOOTPRINT[0], half_y - ROOF_SHAFT_HALF, 0.2))
        builder.box(GROUPS[3], (sign * (half_x + ROOF_SHAFT_HALF) / 2.0, 0.0, 16.1),
                    (half_x - ROOF_SHAFT_HALF, ROOF_SHAFT_HALF * 2.0, 0.2))

    for axis in (0, 1):
        # Long walls include the corners; side walls meet their inside edges.
        span = FOOTPRINT[axis] - (2.0 * _WALL_THICKNESS if axis == 1 else 0.0)
        half_normal = half_y if axis == 0 else half_x
        positions = (-25.0, -13.0, 0.0, 13.0, 25.0) if axis == 0 else (-19.0, -6.5, 6.5, 19.0)
        for sign in (-1, 1):
            openings = []
            for storey, (bottom, top) in enumerate(zip(FLOOR_LEVELS, FLOOR_LEVELS[1:])):
                for position in positions:
                    if axis == 0 and sign == -1 and storey == 0 and position == 0.0:
                        openings.append((-3.6, 3.6, bottom, bottom + 3.0, 4))
                    else:
                        openings.append((position - 1.3, position + 1.3,
                                         bottom + 1.15, min(bottom + 2.4, top - 0.6), 2))
            normal = sign * (half_normal - _WALL_THICKNESS / 2.0)
            _facade(builder, axis, sign, span, normal, openings)

    _perimeter_rails(builder)
    # A few low roof service units leave the central circulation area clear.
    for x in (-26.0, 26.0):
        for y in (-18.0, 18.0):
            builder.box(GROUPS[2], (x, y, ROOF_TOP + 0.6), (3.2, 2.2, 1.2))
            for offset in (-0.75, -0.25, 0.25, 0.75):
                builder.box(GROUPS[2], (x, y + offset, ROOF_TOP + 1.24),
                            (2.95, 0.12, 0.08))
