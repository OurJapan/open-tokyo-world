# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Narrow contract for the eight-tree northeast Tokyo Tower approach candidate."""
import math

FEATURE = 'otw:jp:tokyo:minato:tokyo-tower:northeast-approach-trees-v1'
COLLECTION = 'OTW Tokyo Tower northeast approach / trees v1'
SOIL = 'OTW approach / soil beds'
EDGING = 'OTW approach / flush edging'
MATERIALS = ('Street tree textured bark', 'Tokyo ginkgo foliage',
             'Street tree pit soil', 'Tree pit edging')
SEEDS = [158, 160, 164, 166, 168, 170, 172, 174]


def tree_name(index, part):
    return f'OTW approach {index} / {part}'


def added_names(plan):
    return {SOIL, EDGING} | {tree_name(r['index'], p) for r in plan['trees'] for p in ('bark', 'foliage')}


def source_names():
    return {f'Street tree ginkgo {index}{suffix}' for index in SEEDS for suffix in ('','.001')}


def check_plan(plan):
    if plan.get('version') != 1 or plan.get('feature_id') != FEATURE:
        raise ValueError('Unsupported approach plan')
    if [r['index'] for r in plan['trees']] != SEEDS:
        raise ValueError('Only the reviewed eight seed objects are supported')
    for row in plan['trees']:
        matrix = row['source_matrix_world']
        if len(matrix) != 4 or any(len(r) != 4 for r in matrix):
            raise ValueError('Expected a 4x4 seed matrix')
        if not all(math.isfinite(v) for r in matrix for v in r):
            raise ValueError('Non-finite seed transform')
        x, y = matrix[0][3], matrix[1][3]
        if not (-30 < x < 75 and 25 < y < 80) or row['variant'] != row['index'] % 3:
            raise ValueError('Seed outside the approved local work extent')
    beds = plan['beds']
    if beds != {'outer_width_m': 1.20, 'inner_width_m': 1.04,
                'soil_top_m': 0.44, 'rim_top_m': 0.46, 'bottom_m': 0.0}:
        raise ValueError('Unreviewed bed dimensions')
    return plan


def clipped_area_2d(polygon, low, high):
    """Continuous projected intersection area with an axis-aligned bed rectangle."""
    points = [tuple(p[:2]) for p in polygon]
    for axis, bound, positive in [(0,low[0],True),(0,high[0],False),
                                  (1,low[1],True),(1,high[1],False)]:
        if not points:
            return 0.0
        result = []
        start = points[-1]
        start_inside = start[axis] >= bound if positive else start[axis] <= bound
        for end in points:
            end_inside = end[axis] >= bound if positive else end[axis] <= bound
            if start_inside != end_inside:
                t = (bound-start[axis])/(end[axis]-start[axis])
                result.append(tuple(a+t*(b-a) for a,b in zip(start,end)))
            if end_inside:
                result.append(end)
            start, start_inside = end, end_inside
        points = result
    return abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(points,points[1:]+points[:1])))/2


def box_geometry(low, high):
    """Outward-facing closed box; independent geometry, no legacy code execution."""
    if any(not math.isfinite(v) for v in (*low, *high)) or any(a >= b for a, b in zip(low, high)):
        raise ValueError('Invalid box bounds')
    x0, y0, z0 = low; x1, y1, z1 = high
    vertices = [(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),
                (x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)]
    faces = [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    return vertices, faces


def bed_geometry(plan, rim=False):
    vertices, faces = [], []
    dimensions = plan['beds']; outer = dimensions['outer_width_m']/2
    inner = dimensions['inner_width_m']/2; bottom = dimensions['bottom_m']
    for row in plan['trees']:
        x, y = row['source_matrix_world'][0][3], row['source_matrix_world'][1][3]
        if rim:
            rectangles = [(-outer,-outer,outer,-inner),(-outer,inner,outer,outer),
                          (-outer,-inner,-inner,inner),(inner,-inner,outer,inner)]
            top = dimensions['rim_top_m']
        else:
            rectangles = [(-inner,-inner,inner,inner)]; top = dimensions['soil_top_m']
        for x0,y0,x1,y1 in rectangles:
            vs, fs = box_geometry((x+x0,y+y0,bottom),(x+x1,y+y1,top))
            offset = len(vertices); vertices.extend(vs)
            faces.extend(tuple(offset+i for i in f) for f in fs)
    return vertices, faces
