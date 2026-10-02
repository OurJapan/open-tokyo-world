"""Exact topology repair for one reserved PLATEAU feature; no inferred surfaces."""
from collections import Counter, defaultdict
import math

FEATURE = 'bldg_af7335da-7542-44dd-964d-8cccd2b046ff'
BATCH = 15
AGGREGATE = 'PLATEAU_data221'
SOURCE_TRIANGLES = 466


def weld_exact(triangles):
    """Join bit-identical positions only; retain face and corner order for UVs."""
    vertices, faces, lookup = [], [], {}
    for tri in triangles:
        if len(tri) != 3:
            raise ValueError('Expected triangles')
        face = []
        for point in tri:
            point = tuple(point)
            if len(point) != 3 or not all(math.isfinite(v) for v in point):
                raise ValueError('Invalid vertex')
            if point not in lookup:
                lookup[point] = len(vertices)
                vertices.append(point)
            face.append(lookup[point])
        if len(set(face)) != 3:
            raise ValueError('Collapsed triangle')
        faces.append(tuple(face))
    return vertices, faces


def surface_stats(vertices, faces):
    """Independent indexed-edge, winding, component and volume checks."""
    edges, directed, adjacency = Counter(), Counter(), defaultdict(set)
    used, areas, volume = set(), [], 0.0
    for face in faces:
        if len(face) != 3 or len(set(face)) != 3:
            raise ValueError('Invalid triangular face')
        if any(i < 0 or i >= len(vertices) for i in face):
            raise ValueError('Vertex index outside mesh')
        used.update(face)
        a, b, c = [vertices[i] for i in face]
        u = [b[i] - a[i] for i in range(3)]
        v = [c[i] - a[i] for i in range(3)]
        cross = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
        area = math.sqrt(sum(x*x for x in cross))/2
        if not math.isfinite(area) or area <= 1e-10:
            raise ValueError('Degenerate/nonfinite triangle')
        areas.append(area)
        volume += sum(a[i]*cross[i] for i in range(3))/6
        for x, y in zip(face, face[1:]+face[:1]):
            edges[tuple(sorted((x, y)))] += 1
            directed[x, y] += 1
            adjacency[x].add(y)
            adjacency[y].add(x)
    components, remaining = 0, set(used)
    while remaining:
        components += 1
        stack = [remaining.pop()]
        while stack:
            for other in adjacency[stack.pop()] & remaining:
                remaining.remove(other)
                stack.append(other)
    return {'vertices': len(vertices), 'faces': len(faces), 'edges': len(edges),
            'boundary_edges': sum(n == 1 for n in edges.values()),
            'nonmanifold_edges': sum(n != 2 for n in edges.values()),
            'winding_errors': sum(n == 2 and (directed[a,b] != 1 or directed[b,a] != 1)
                                  for (a,b), n in edges.items()),
            'components': components, 'loose_vertices': len(vertices)-len(used),
            'euler_characteristic': len(used)-len(edges)+len(faces),
            'minimum_triangle_area_m2': min(areas) if areas else 0,
            'surface_area_m2': sum(areas), 'signed_volume_m3': volume}


def require_closed(stats):
    if (stats['components'] != 1 or stats['nonmanifold_edges']
            or stats['winding_errors'] or stats['loose_vertices']
            or stats['euler_characteristic'] != 2 or stats['signed_volume_m3'] <= 0):
        raise ValueError('Expected one closed outward-oriented surface')


def verify_source(actual, expected, tolerance=5e-5):
    """Verify every ordered source triangle, including winding, one-to-one."""
    if len(actual) != SOURCE_TRIANGLES or len(expected) != SOURCE_TRIANGLES:
        raise ValueError('Reserved feature triangle count differs')
    for triangles in (actual, expected):
        if any(len(t) != 3 or any(len(p) != 3 or not all(math.isfinite(x) for x in p)
                                 for p in t) for t in triangles):
            raise ValueError('Invalid source triangle data')
    # Source/import face order is retained by the pinned importer. Fail closed
    # instead of spatially guessing which other feature should be edited.
    error = max(abs(a-b) for tri, ref in zip(actual, expected)
                for p, q in zip(tri, ref) for a, b in zip(p, q))
    if not math.isfinite(error) or error > tolerance:
        raise ValueError('Reserved feature differs from pinned source')
    return error
