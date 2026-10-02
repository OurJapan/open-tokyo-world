"""Pinned batch-0 topology contract; no inferred faces or coordinate movement."""
from data221_af7335da_mesh import weld_exact, surface_stats, require_closed
from validate_data221_af7335da_integration import topology_extras
import math

FEATURE = 'bldg_0551e688-a2a3-498e-ad2f-09ed3aca361c'
BATCH = 0
AGGREGATE = 'PLATEAU_data221'
PREVIOUS_FEATURE = 'bldg_af7335da-7542-44dd-964d-8cccd2b046ff'
INPUT_SHA256 = '09977e34f02c02a7e24448767874294e0f7c09e3bbaf40b5630ea1dea8965216'
SOURCE_TRIANGLES = 946
WELDED_VERTICES = 475


def verify_source(actual, expected, tolerance=5e-5):
    if len(actual) != SOURCE_TRIANGLES or len(expected) != SOURCE_TRIANGLES:
        raise ValueError('Reserved feature triangle count differs')
    for triangles in (actual, expected):
        if any(len(t) != 3 or any(len(p) != 3 or not all(math.isfinite(x) for x in p)
                                 for p in t) for t in triangles):
            raise ValueError('Invalid source triangle data')
    error = max(abs(a-b) for tri, ref in zip(actual, expected)
                for p, q in zip(tri, ref) for a, b in zip(p, q))
    if error > tolerance:
        raise ValueError('Reserved feature differs from pinned source')
    return error


def verify_topology(vertices, faces):
    stats = surface_stats(vertices, faces)
    extras = topology_extras(vertices, faces)
    # This is the measured contract of this particular source, not a rule that
    # every building must be a single sphere-topology surface.
    require_closed(stats)
    if stats['vertices'] != WELDED_VERTICES or stats['faces'] != SOURCE_TRIANGLES:
        raise ValueError('Reserved topology counts differ')
    if extras['duplicate_geometric_faces'] or extras['nonmanifold_vertex_links']:
        raise ValueError('Duplicate face or nonmanifold vertex link')
    return {'surface': stats, 'extras': extras}
