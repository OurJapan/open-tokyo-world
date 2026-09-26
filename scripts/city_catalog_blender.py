# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Disposable read/render worker. Never saves a blend or executes embedded text."""
import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpy
import numpy as np
from mathutils import Vector
from city_catalog import associate_record, classify, load_grants, read, require, sha, write
from blender_worker import mesh_fingerprint, material_fingerprint, packed_hash
from audit_image_sources import images_in_tree


def enabled_meshes():
    names = set()
    def visit(layer, enabled=True):
        enabled = enabled and not layer.exclude and not layer.collection.hide_render
        if enabled:
            names.update(o.name for o in layer.collection.objects if o.type == 'MESH' and not o.hide_render)
        for child in layer.children:
            visit(child, enabled)
    visit(bpy.context.view_layer.layer_collection)
    return names


def bounds(obj):
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return [[min(c[i] for c in corners) for i in range(3)], [max(c[i] for c in corners) for i in range(3)]]


def inventory(job):
    config = job['config']; scene = bpy.context.scene
    scene.frame_set(1)
    enabled = enabled_meshes(); grants = load_grants(config['input']['sha256'])
    meshes, materials, images = {}, {}, {}
    rows = []
    for obj in sorted(scene.objects, key=lambda o: o.name):
        if obj.type != 'MESH': continue
        key = obj.data.as_pointer()
        if key not in meshes: meshes[key] = mesh_fingerprint(obj.data)
        mats, used = [], set()
        for slot in obj.material_slots:
            mat = slot.material
            if mat is None: continue
            key = mat.as_pointer()
            if key not in materials:
                material_images = images_in_tree(mat.node_tree)
                for image in material_images:
                    images[image.name] = dict(name=image.name, packed_sha256=packed_hash(image), size=list(image.size))
                materials[key] = dict(name=mat.name, sha256=material_fingerprint(mat), images=sorted(i.name for i in material_images))
            mats.append(materials[key]); used.update(materials[key]['images'])
        claims = {k: str(obj[k]) for k in ('source', 'source_url', 'gml_id', 'otw_feature_id') if k in obj}
        row = dict(object=obj.name, collections=sorted(c.name for c in obj.users_collection),
                   vertices=len(obj.data.vertices), polygons=len(obj.data.polygons), mesh_sha256=meshes[obj.data.as_pointer()],
                   transform=[float(v) for line in obj.matrix_world for v in line], bounds=bounds(obj),
                   hide_render=obj.hide_render, render_enabled=obj.name in enabled, empty=len(obj.data.vertices) == 0,
                   modifiers=[m.type for m in obj.modifiers], materials=mats, images=sorted(used), claims=claims,
                   record=associate_record(obj.name, claims.get('source_url'), grants))
        row['group'] = classify(row, config['groups']); rows.append(row)
    require(len(rows) == config['expected_mesh_objects'], 'Unexpected mesh object count')
    groups = []
    for group in config['groups']:
        selected = [r for r in rows if r['group'] == group['id']]
        require(bool(selected), 'Empty classification: ' + group['id'])
        groups.append(dict(id=group['id'], objects=len(selected), visible=sum(r['render_enabled'] and not r['empty'] for r in selected),
                           empty=sum(r['empty'] for r in selected), records=dict(Counter(r['record']['kind'] for r in selected)),
                           images=sorted({i for r in selected for i in r['images']}),
                           scope_sha256=hashlib.sha256(json.dumps(selected, ensure_ascii=False, sort_keys=True).encode()).hexdigest()))
    return dict(ok=True, input_sha256=config['input']['sha256'], mesh_objects=len(rows), total_scene_objects=len(scene.objects),
                counts=dict(visible_meshes=sum(r['render_enabled'] and not r['empty'] for r in rows), empty_meshes=sum(r['empty'] for r in rows),
                            referenced_images=len(images), record_kinds=dict(Counter(r['record']['kind'] for r in rows))),
                groups=groups, objects=rows, images=sorted(images.values(), key=lambda i: i['name']),
                limitations=['Object counts are not building, tree or vehicle instance counts.',
                             'Same-name grant matches do not prove identical geometry or materials.',
                             'Fingerprints do not fully cover modifiers, animations or nested node groups.',
                             'Render eligibility reflects the active view layer at frame 1.'])


def camera_for(group, rows):
    config = group['preview']; target = Vector(config['anchor']); span = config['span']
    representatives = []
    if config['primary']:
        candidates = [r for r in rows if not r['empty'] and r['object'].startswith(config['primary'])]
        if candidates:
            def centre(r): return Vector([(a+b)/2 for a,b in zip(*r['bounds'])])
            seed = min(candidates, key=lambda r: (centre(r).x**2 + centre(r).y**2, -r['vertices'], r['object']))
            representatives.append(seed['object']); obj = bpy.data.objects[seed['object']]
            size = Vector(seed['bounds'][1]) - Vector(seed['bounds'][0])
            if max(size) < 70:
                target = centre(seed); span = max(span, max(size) * 1.55)
            else:
                # Large material batches span the city. Choose a reproducible
                # local patch around actual vertices rather than their midpoint.
                coords = np.empty(len(obj.data.vertices)*3, dtype=np.float32)
                obj.data.vertices.foreach_get('co', coords); coords = coords.reshape(-1, 3)
                matrix = np.array(obj.matrix_world, dtype=np.float64)
                coords = coords @ matrix[:3, :3].T + matrix[:3, 3]
                index = int(np.argmin(np.sum(coords[:, :2]**2, axis=1)))
                radius = config.get('focus_radius', span * .22)
                near = coords[np.sum((coords[:, :2] - coords[index, :2])**2, axis=1) < radius**2]
                target = Vector(((near.min(axis=0) + near.max(axis=0)) / 2).tolist())
            if group['id'] == 'street-trees':
                # The .001 companion is foliage; the unsuffixed mesh is bark.
                # Name correspondence selects a sample, not an authorship claim.
                family = re.sub(r'\.\d{3}$', '', seed['object'])
                pair = [r for r in candidates if re.sub(r'\.\d{3}$', '', r['object']) == family]
                representatives = [r['object'] for r in pair]
                low = Vector([min(r['bounds'][0][i] for r in pair) for i in range(3)])
                high = Vector([max(r['bounds'][1][i] for r in pair) for i in range(3)])
                target = (low + high) / 2; span = max(config['span'], max(high-low) * 1.25)
    # The existing facade camera provides a clear face-on example.
    if group['id'] == 'buildings':
        eye = Vector((-48, -31, 32)); target = Vector((-27, -87, 12)); lens = 46
    else:
        direction = Vector((.75, -1.15, .9)).normalized()
        eye = target + direction * (span * 1.8); lens = 42
    return eye, target, lens, representatives


def select_preview(group, rows, target, representatives):
    candidates = [r for r in rows if not r['empty']]
    if group['id'] == 'street-trees':
        # Render the named trunk/foliage pair without loading every street tree.
        return [r for r in candidates if r['object'] in representatives]
    if group['id'] == 'shrubs':
        return [r for r in candidates if r['object'] in representatives]
    if group['id'] == 'mori':
        # Keep the active facade; inactive earlier surfaces overlap it.
        return [r for r in candidates if r['render_enabled']]
    return candidates


def render(job):
    scene = bpy.context.scene; settings = job['settings']; output = Path(job['output'])
    data = read(output / 'inventory.json')
    require(data['input_sha256'] == job['config']['input']['sha256'], 'Inventory input differs')
    scene.frame_set(1); scene.timeline_markers.clear()
    scene.render.engine = 'CYCLES'; scene.cycles.samples = settings['samples']; scene.cycles.seed = 0
    scene.cycles.use_animated_seed = False; scene.cycles.use_adaptive_sampling = False; scene.cycles.use_denoising = True
    scene.render.resolution_x = settings['width']; scene.render.resolution_y = settings['height']; scene.render.resolution_percentage = 100
    scene.render.pixel_aspect_x = 1; scene.render.pixel_aspect_y = 1; scene.render.use_border = False
    scene.render.use_motion_blur = False; scene.render.use_compositing = False; scene.render.use_sequencer = False
    scene.render.image_settings.file_format = 'PNG'; scene.render.image_settings.color_mode = 'RGBA'; scene.render.image_settings.color_depth = '8'
    devices = []
    if settings['device'] == 'OPTIX':
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'OPTIX'; prefs.get_devices()
        for device in prefs.devices:
            device.use = device.type == 'OPTIX'
            if device.use: devices.append(device.name)
        require(bool(devices), 'No OptiX device; select CPU explicitly')
        scene.cycles.device = 'GPU'
    else: scene.cycles.device = 'CPU'
    active = bpy.context.view_layer
    for layer in scene.view_layers: layer.use = layer == active
    camera_data = bpy.data.cameras.new('Catalog camera')
    camera = bpy.data.objects.new('Catalog camera', camera_data); scene.collection.objects.link(camera)
    camera_data.clip_start = .05; camera_data.clip_end = 15000; camera_data.sensor_width = 36
    camera_data.sensor_fit = 'HORIZONTAL'; camera_data.dof.use_dof = False
    original = {o.name: o.hide_render for o in scene.objects if o.type == 'MESH'}
    preview_collection = bpy.data.collections.new('Catalog temporary visibility')
    scene.collection.children.link(preview_collection)
    results = []
    for group in job['config']['groups']:
        rows = [r for r in data['objects'] if r['group'] == group['id']]
        visible = [r for r in rows if r['render_enabled'] and not r['empty']]
        result = dict(id=group['id'], images={}, originally_visible_meshes=len(visible))
        if all(r['empty'] for r in rows):
            result['note'] = 'All meshes in this category are empty.'
            results.append(result); continue
        eye, target, lens, representatives = camera_for(group, rows)
        selected = select_preview(group, rows, target, representatives)
        names = {r['object'] for r in selected}
        for obj in list(preview_collection.objects): preview_collection.objects.unlink(obj)
        for name in names: preview_collection.objects.link(bpy.data.objects[name])
        camera.location = eye; camera.rotation_euler = (target-eye).to_track_quat('-Z','Y').to_euler(); camera_data.lens = lens
        scene.camera = camera
        result.update(camera_eye=list(eye), camera_target=list(target), lens_mm=lens, representatives=representatives,
                      selected_objects=sorted(names), temporarily_revealed=sum(not r['render_enabled'] for r in selected),
                      coverage='Selected camera view of this category, not every instance.')
        for mode in ('isolated', 'context'):
            for name, hidden in original.items():
                bpy.data.objects[name].hide_render = False if name in names else (True if mode == 'isolated' else hidden)
            scene.render.film_transparent = mode == 'isolated'
            filename = group['id'] + '-' + mode + '.png'
            scene.render.filepath = str(output / filename)
            bpy.ops.render.render(write_still=True)
            require(scene.camera == camera, 'Camera was overridden')
            image = bpy.data.images.load(str(output / filename), check_existing=False)
            try:
                pixels = np.asarray(image.pixels[:], dtype=np.float32).reshape(-1, 4)
                require(list(image.size) == [settings['width'], settings['height']] and np.isfinite(pixels).all(), 'Invalid image')
                alpha = float(np.mean(pixels[:, 3] > .02))
                require(alpha > .001 and float(pixels[:, :3].max()) > 1/255, 'Empty image: ' + filename)
                result['images'][mode] = dict(file=filename, sha256=sha(output / filename), alpha_coverage=alpha)
            finally: bpy.data.images.remove(image)
        results.append(result)
    return dict(ok=True, groups=results, devices=devices, scene_saved=False,
                limitations=['Named nonempty samples can be temporarily revealed; original eligibility is separately recorded.',
                             'Isolation changes occlusion and lighting; these are identification views, not change comparisons.'])


def main():
    p = argparse.ArgumentParser(); p.add_argument('--job', required=True); p.add_argument('--phase', required=True); p.add_argument('--report', required=True)
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:]); job = read(a.job)
    result = {'ok': False}; source = Path(bpy.data.filepath)
    try:
        require(bpy.app.version_string == job['config']['input']['blender_version'], 'Blender version differs')
        require(sha(source) == job['config']['input']['sha256'], 'Pinned city differs')
        if a.phase == 'inventory': result = inventory(job)
        elif a.phase == 'render': result = render(job)
        else: raise ValueError('Unknown phase')
        require(sha(source) == job['config']['input']['sha256'], 'Source changed during catalog')
    except Exception as e:
        result.update(ok=False, error=str(e)); raise
    finally:
        write(a.report, result)


if __name__ == '__main__':
    main()
