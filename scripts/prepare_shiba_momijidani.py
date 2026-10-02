# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Prepare a deterministic, local-only Momiji-dani landscape plan from pinned OSM.

Requires Shapely 2.1 or later for constrained Delaunay triangulation. The output
contains third-party source geometry and belongs in ignored data/local/.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import platform
import random
import re
import xml.etree.ElementTree as ET

import shapely
from shapely.geometry import LineString, Point, Polygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union


VERSION = 1
CITY_SHA256 = '9c142f54cc85689cb8a8bc00794dfe8e9b6bc9098f121c9fb02cdbc1aa3dbbc4'
OSM_SHA256 = 'f04e8e70ab24a61ca749375d1ef37401feb0fdc840cc506b670ef71454a6a8ab'
BOUNDARY_ID = '30526664'
PATH_IDS = ('222753172', '222753173')
STEP_IDS = ('222753175', '222753176', '1382211864', '1382211865')
SEED = 19019
PATH_WIDTH = 2.4
WALKWAYS = {'footway', 'path', 'steps', 'pedestrian', 'cycleway'}
ROAD_NAMES = ('asphalt 15s road detail', 'gutter 15s road detail',
              'pavement_0 unified road', 'asphalt_7 unified road', 'pavement_7 unified road')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project(lon, lat):
    return ((lon - 139.74543) * 111320 * math.cos(math.radians(35.65858)),
            (lat - 35.65858) * 110950)


def polygon_parts(geometry):
    if geometry.is_empty:
        return []
    if geometry.geom_type == 'Polygon':
        return [geometry]
    if hasattr(geometry, 'geoms'):
        return [p for g in geometry.geoms for p in polygon_parts(g)]
    return []


def polygon_records(geometry):
    return [{'exterior': list(p.exterior.coords),
             'holes': [list(r.coords) for r in p.interiors]}
            for p in polygon_parts(geometry)]


def closed_mesh(geometry, bottom_z, top_z):
    """Extrude constrained polygon triangles, including holes, into a closed mesh."""
    vertices, faces, indices = [], [], {}

    def vertex(x, y, z):
        key = (x, y, z)
        if key not in indices:
            indices[key] = len(vertices)
            vertices.append(list(key))
        return indices[key]

    triangle_area = 0.0
    for raw in polygon_parts(geometry):
        polygon = orient(raw, sign=1.0)
        triangulation = shapely.constrained_delaunay_triangles(polygon)
        for triangle in triangulation.geoms:
            points = list(triangle.exterior.coords)[:-1]
            if len(points) != 3:
                raise ValueError('Constrained triangulation produced a non-triangle')
            a, b, c = points
            cross = (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
            if cross < 0:
                points.reverse()
            triangle_area += triangle.area
            top = [vertex(x, y, top_z) for x, y in points]
            bottom = [vertex(x, y, bottom_z) for x, y in reversed(points)]
            faces.extend((top, bottom))
        for ring in [polygon.exterior, *polygon.interiors]:
            points = list(ring.coords)
            for a, b in zip(points, points[1:]):
                lower_a, lower_b = vertex(*a, bottom_z), vertex(*b, bottom_z)
                upper_a, upper_b = vertex(*a, top_z), vertex(*b, top_z)
                faces.extend(([lower_a, lower_b, upper_b],
                              [lower_a, upper_b, upper_a]))
    edges = Counter()
    for face in faces:
        for a, b in zip(face, face[1:]+face[:1]):
            if a == b:
                raise ValueError('Degenerate mesh edge')
            edges[tuple(sorted((a, b)))] += 1
    if not faces or any(count != 2 for count in edges.values()):
        raise ValueError('Extruded surface is empty or is not a closed two-manifold mesh')
    if not math.isclose(triangle_area, geometry.area, rel_tol=1e-9, abs_tol=1e-6):
        raise ValueError('Triangulation area does not equal source polygon area')
    if not all(math.isfinite(v) for p in vertices for v in p):
        raise ValueError('Mesh contains nonfinite values')
    return {'vertices': vertices, 'faces': faces, 'area_m2': geometry.area,
            'bottom_z': bottom_z, 'top_z': top_z, 'height_classification': 'inferred',
            'components': len(polygon_parts(geometry)),
            'validation': {'closed_edge_incidence': True, 'triangulation_area_m2': triangle_area}}


def read_osm(path):
    if digest(path) != OSM_SHA256:
        raise ValueError('OSM SHA-256 does not match the pinned legacy production input')
    root = ET.parse(path).getroot()
    nodes = {n.attrib['id']: project(float(n.attrib['lon']), float(n.attrib['lat']))
             for n in root.findall('node')}
    ways = {}
    for element in root.findall('way'):
        refs = [n.attrib['ref'] for n in element.findall('nd')]
        if not refs:
            continue
        ways[element.attrib['id']] = {
            'id': element.attrib['id'], 'version': element.attrib.get('version'),
            'timestamp': element.attrib.get('timestamp'),
            'tags': {t.attrib['k']: t.attrib['v'] for t in element.findall('tag')},
            'xy': [nodes[n] for n in refs if n in nodes],
            'missing_nodes': [n for n in refs if n not in nodes],
            'closed': refs[0] == refs[-1],
        }
    return ways


def source_record(way):
    return {k: way[k] for k in ('id', 'version', 'timestamp', 'tags')}


def read_road_mask(path):
    """Read the exporter output for the exact accepted city, without opening it."""
    blob = path.read_bytes()
    document = json.loads(blob)
    if type(document.get('version')) is not int or document['version'] != 1:
        raise ValueError('Road mask version differs')
    if document.get('input_sha256') != CITY_SHA256:
        raise ValueError('Road mask does not describe the accepted city input')
    roads = document.get('roads')
    if not isinstance(roads, list) or len(roads) != len(ROAD_NAMES):
        raise ValueError('Road mask must contain all five protected road meshes')
    if any(not isinstance(road, dict) for road in roads):
        raise ValueError('Invalid road mask entry')
    if any(not isinstance(road.get('name'), str) for road in roads) or {road['name'] for road in roads} != set(ROAD_NAMES):
        raise ValueError('Road mask protected mesh names differ')
    polygons, records = [], []
    for road in roads:
        fingerprint = road.get('mesh_sha256')
        if not isinstance(fingerprint, str) or not re.fullmatch('[0-9a-f]{64}', fingerprint):
            raise ValueError('Road mask mesh fingerprint is invalid')
        triangles = road.get('triangles')
        if not isinstance(triangles, list):
            raise ValueError('Road mask triangles must be a list')
        for triangle in triangles:
            if not isinstance(triangle, list) or len(triangle) != 3:
                raise ValueError('Road mask contains a non-triangle')
            if any(not isinstance(point, list) or len(point) != 2 or
                   not all(isinstance(value, (int, float)) and not isinstance(value, bool)
                           and math.isfinite(value) for value in point) for point in triangle):
                raise ValueError('Road mask contains invalid XY coordinates')
            polygon = Polygon(triangle)
            if not polygon.is_valid or polygon.area <= 1e-12:
                raise ValueError('Road mask contains a degenerate triangle')
            polygons.append(polygon)
        records.append({'name': road['name'], 'mesh_sha256': fingerprint,
                        'triangle_count': len(triangles)})
    if not polygons:
        raise ValueError('Road mask contains no protected road triangles')
    metadata = {'sha256': hashlib.sha256(blob).hexdigest(), 'input_sha256': CITY_SHA256,
                'bytes': len(blob), 'roads': records,
                'use': 'Planting clearance only; existing forest-floor and path-overlay geometry is retained.'}
    return unary_union(polygons), metadata


def prepare_plan(inputs, road_mask_path):
    scene_road_mask, road_metadata = read_road_mask(road_mask_path)
    source_path = inputs / 'work' / 'osm.xml'
    ways = read_osm(source_path)
    boundary_way = ways[BOUNDARY_ID]
    if boundary_way['missing_nodes']:
        raise ValueError('Boundary has missing OSM nodes')
    boundary = Polygon(boundary_way['xy'])
    if not boundary.is_valid or boundary.area <= 0:
        raise ValueError('Invalid Momiji-dani boundary')
    vicinity = boundary.buffer(25)
    road_masks, walk_masks, building_masks, source_ways = [], [], [], []
    repairs, widths, road_ids, walk_ids, building_ids = [], [], [], [], []
    for way in ways.values():
        points, tags = way['xy'], way['tags']
        if len(points) < 2:
            continue
        line = LineString(points)
        if not line.intersects(vicinity):
            continue
        highway = tags.get('highway')
        building = 'building' in tags or 'building:part' in tags
        if not highway and not building:
            continue
        if way['missing_nodes']:
            raise ValueError(f"Mask source way {way['id']} has missing nodes")
        source_ways.append(source_record(way))
        if highway:
            walking = highway in WALKWAYS
            explicit_width = tags.get('width')
            try:
                width = float(explicit_width) if explicit_width is not None else (PATH_WIDTH if walking else 6.0)
            except ValueError as exc:
                raise ValueError(f"Unsupported OSM width on way {way['id']}: {explicit_width}") from exc
            if width <= 0 or not math.isfinite(width):
                raise ValueError(f"Invalid OSM width on way {way['id']}")
            margin = 0.0 if walking else 2.0
            if highway == 'steps':
                half_width = 1.5
            else:
                half_width = width / 2 + margin
            mask = line.buffer(half_width, quad_segs=8)
            (walk_masks if walking else road_masks).append(mask)
            (walk_ids if walking else road_ids).append(way['id'])
            widths.append({'osm_way_id': way['id'], 'width_m': width,
                           'width_classification': 'osm_tag' if explicit_width is not None else 'inferred',
                           'mask_half_width_m': half_width, 'mask_margin_m': margin,
                           'mask_classification': 'inferred'})
        if building and way['closed'] and len(points) >= 4:
            polygon = Polygon(points)
            if not polygon.is_valid:
                polygon = shapely.make_valid(polygon)
                repairs.append(way['id'])
            building_masks.extend(polygon_parts(polygon))
            building_ids.append(way['id'])
    road_mask = unary_union(road_masks)
    building_mask = unary_union(building_masks)
    protected = unary_union([road_mask, building_mask])
    steps = unary_union([LineString(ways[i]['xy']).buffer(1.5, quad_segs=8) for i in STEP_IDS])
    path_lines = [LineString(ways[i]['xy']) for i in PATH_IDS]
    path_mask = unary_union([line.buffer(PATH_WIDTH / 2, quad_segs=8) for line in path_lines])
    floor_geometry = boundary.difference(protected)
    path_geometry = path_mask.intersection(boundary).difference(unary_union([protected, steps]))
    plant_mask = unary_union([protected, *walk_masks, steps, path_mask, scene_road_mask])
    rng = random.Random(SEED)
    bounds = boundary.bounds
    boundary_edge = boundary.boundary

    def place(target, radius_range, height_range, existing=None):
        placements, attempts = [], 0
        while len(placements) < target and attempts < 50000:
            attempts += 1
            radius = rng.uniform(*radius_range)
            x, y = rng.uniform(bounds[0], bounds[2]), rng.uniform(bounds[1], bounds[3])
            point = Point(x, y)
            clearance = radius + 1.0
            if not boundary.contains(point) or point.distance(boundary_edge) < clearance:
                continue
            if point.distance(plant_mask) < clearance:
                continue
            tree_mode = radius_range[0] > 2
            if any(math.hypot(x-p['x'], y-p['y']) < (max(7.0, radius+p['radius']+0.6) if tree_mode else radius+p['radius']+0.6)
                   for p in placements):
                continue
            if existing and any(math.hypot(x-p['x'], y-p['y']) < radius+1.2 for p in existing):
                continue
            placements.append({'x': x, 'y': y, 'radius': radius,
                               'height': rng.uniform(*height_range), 'seed': rng.randrange(2**31)})
        return placements, attempts

    trees, tree_attempts = place(80, (2.8, 4.8), (7.0, 12.0))
    shrubs, shrub_attempts = place(120, (0.4, 1.0), (0.4, 1.0), existing=trees)
    floor_mesh = closed_mesh(floor_geometry, 0.12, 0.16)
    path_mesh = closed_mesh(path_geometry, 0.49, 0.53)
    if digest(source_path) != OSM_SHA256:
        raise ValueError('Pinned OSM changed during plan generation')
    if digest(road_mask_path) != road_metadata['sha256']:
        raise ValueError('Accepted-city road mask changed during plan generation')
    return {
        'version': VERSION, 'input_sha256': CITY_SHA256,
        'sources': {
            'road_mask': road_metadata,
            'osm': {'relative_path': 'work/osm.xml', 'sha256': OSM_SHA256,
                    'bytes': source_path.stat().st_size, 'attribution': 'OpenStreetMap contributors',
                    'license': 'ODbL-1.0', 'license_url': 'https://www.openstreetmap.org/copyright',
                    'boundary': source_record(boundary_way),
                    'paths': [source_record(ways[i]) for i in PATH_IDS],
                    'steps': [source_record(ways[i]) for i in STEP_IDS], 'mask_ways': source_ways},
            'code_sha256': digest(Path(__file__)),
            'runtime': {'python': platform.python_version(), 'shapely': shapely.__version__,
                        'geos': shapely.geos_version_string,
                        'triangulation': 'shapely.constrained_delaunay_triangles'},
            'coordinates': {'x': '(lon-139.74543)*111320*cos(radians(35.65858))',
                            'y': '(lat-35.65858)*110950', 'units': 'metres'},
            'distribution': 'Local-only plan contains third-party geometry; do not commit or publish.',
        },
        'boundary': boundary_way['xy'],
        'paths': [{'osm_way_id': i, 'xy': ways[i]['xy'], 'width_m': PATH_WIDTH,
                   'width_classification': 'inferred'} for i in PATH_IDS],
        'forest_floor': floor_mesh, 'path_surface': path_mesh,
        'trees': trees, 'shrubs': shrubs,
        'audit': {
            'seed': SEED, 'boundary_area_m2': boundary.area,
            'floor_area_m2': floor_geometry.area, 'path_area_m2': path_geometry.area,
            'tree_count': len(trees), 'shrub_count': len(shrubs),
            'tree_attempts': tree_attempts, 'shrub_attempts': shrub_attempts,
            'road_way_ids': road_ids, 'walkway_way_ids': walk_ids, 'building_way_ids': building_ids,
            'step_way_ids': list(STEP_IDS), 'building_geometry_repaired': repairs,
            'mask_widths': widths,
            'placement_mask_polygons': polygon_records(plant_mask),
            'building_footprint_polygons': polygon_records(building_mask),
            'road_mask_polygons': polygon_records(road_mask),
            'scene_road_mask_polygons': polygon_records(scene_road_mask),
            'scene_road_mask_area_m2': scene_road_mask.area,
            'path_surface_polygons': polygon_records(path_geometry),
            'classification': {'plant_locations': 'inferred', 'plant_sizes': 'inferred',
                               'plant_species': 'inferred', 'path_width': 'inferred',
                               'floor_and_path_z': 'inferred', 'horizontal_boundary': 'pinned_osm'},
            'placement_rules': {'boundary_clearance': 'radius + 1 metre',
                                'protected_feature_clearance': 'radius + 1 metre beyond buffered masks',
                                'tree_centre_spacing_m': 'max(7, radius_i + radius_j + 0.6)',
                                'tree_radius_range_m': [2.8, 4.8], 'tree_height_range_m': [7, 12],
                                'shrub_radius_range_m': [0.4, 1], 'shrub_height_range_m': [0.4, 1]},
            'limitations': [
                'Tree/shrub locations, dimensions, species, path width, surface elevations and collision margins are inferred; no surveyed accuracy is claimed.',
                'OSM does not contain individual tree, watercourse, pond or waterfall geometry within this woodland.',
                'Planting uses both OSM masks and exported triangles from the pinned city road meshes. The saved candidate still requires independent road-contact checks; this does not certify collision-free navigation.',
                'The exported city-road mask changes planting clearance only; the low forest-floor layer and path overlay retain their OSM-derived geometry.',
                'No measured terrain, waterfall, stream or stairs are reconstructed. Existing stairways are excluded from the new path surface.',
                'The layer=-1 tag is relative OSM layering, not a ground elevation of -1 metre.',
            ],
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True, help='Pinned legacy-production-inputs-v1 root')
    parser.add_argument('--road-mask', type=Path, required=True, help='Exported mask for the exact accepted city road meshes')
    parser.add_argument('--output', type=Path, required=True, help='New local JSON path; never overwritten')
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Use a new plan output')
    plan = prepare_plan(args.inputs, args.road_mask)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(plan, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'output': str(args.output), 'sha256': digest(args.output),
                      'tree_count': len(plan['trees']), 'shrub_count': len(plan['shrubs']),
                      'floor_area_m2': plan['forest_floor']['area_m2'],
                      'path_area_m2': plan['path_surface']['area_m2']}, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
