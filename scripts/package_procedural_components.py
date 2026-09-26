# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""License the approved isolated candidate, reopen it, and package only approved files."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from component_contracts import material_snapshot, mesh_object_snapshot, scalar_properties, signature
from workspace import digest, read_json, verify_file, write_json

ASSETS = ROOT / 'assets/procedural-components'
FILES = {'kit.blend', 'preview.png', 'README.md', 'ASSET-LICENSE.md', 'NOTICE.md',
         'provenance.json', 'verification.json'}
ARCHIVE_NAME = 'procedural-components-v0.1.0.zip'


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf8')


def code_hash():
    return hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def grant():
    value = read_json(ASSETS / 'provenance.json')
    if value['status'] != 'consent-confirmed' or value['license'] != 'CC-BY-4.0':
        raise ValueError('A recorded license grant is required')
    if len(value['prototype_meshes']) != 16 or len(value['material_signatures']) != 31:
        raise ValueError('Unexpected licensed scope')
    return value


def inventory(files):
    if set(files) != FILES:
        raise ValueError('Unexpected package file set')
    return {'version': 1, 'license': 'CC-BY-4.0', 'packager_sha256_lf': code_hash(),
            'files': {n: {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}
                      for n, b in sorted(files.items())}}


def verify_archive(path):
    """Validate the fixed member set before any extraction; reject duplicates."""
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != FILES | {'inventory.json'}:
            raise ValueError('Unexpected ZIP members')
        if archive.testzip() is not None:
            raise ValueError('ZIP CRC verification failed')
        record = json.loads(archive.read('inventory.json'))
        if set(record['files']) != FILES:
            raise ValueError('Unexpected inventory members')
        for name, pin in record['files'].items():
            data = archive.read(name)
            if len(data) != pin['bytes'] or hashlib.sha256(data).hexdigest() != pin['sha256']:
                raise ValueError('ZIP member hash mismatch: ' + name)
    return record


def write_archive(path, files):
    record = inventory(files)
    contents = {**files, 'inventory.json': encoded(record)}
    with zipfile.ZipFile(path, 'x', zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(contents.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 9, 27, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    if verify_archive(path) != record:
        raise ValueError('ZIP inventory changed')
    with zipfile.ZipFile(path) as archive:
        if any(archive.read(n) != data for n, data in contents.items()):
            raise ValueError('ZIP content differs from approved files')
    return record


def model_state(scope):
    import bpy
    scene = bpy.context.scene
    meshes = {o.name: o for o in scene.objects if o.type == 'MESH'}
    if set(meshes) != {p['id'] for p in scope['prototype_meshes']} or len(bpy.data.meshes) != 16:
        raise ValueError('Unexpected mesh scope')
    if set(bpy.data.objects.keys()) != set(meshes) | set(scope['preview_setup']['objects']):
        raise ValueError('Unexpected preview object scope')
    if bpy.data.images or bpy.data.libraries or bpy.data.texts:
        raise ValueError('External or embedded content is outside the grant')
    snapshots = {n: mesh_object_snapshot(o) for n, o in meshes.items()}
    for p in scope['prototype_meshes']:
        obj = meshes[p['id']]
        if (snapshots[p['id']]['mesh_sha256'] != p['mesh_sha256']
                or list(obj.location) != p['location'] or any(obj.rotation_euler)
                or tuple(obj.scale) != (1, 1, 1) or obj.modifiers
                or snapshots[p['id']]['materials'] != p['materials']):
            raise ValueError('Prototype differs: ' + p['id'])
    if set(bpy.data.materials.keys()) != set(scope['material_signatures']):
        raise ValueError('Unexpected material scope')
    for name, pin in scope['material_signatures'].items():
        if signature(material_snapshot(bpy.data.materials[name])) != pin:
            raise ValueError('Material differs: ' + name)
    preview = {}
    for name in scope['preview_setup']['objects']:
        obj = bpy.data.objects[name]
        if obj.type not in {'CAMERA', 'LIGHT'} or obj.animation_data or obj.constraints or obj.parent:
            raise ValueError('Unexpected preview dependency')
        preview[name] = {'matrix': [float(v) for row in obj.matrix_world for v in row],
                         'type': obj.type, 'settings': scalar_properties(obj.data)}
    return signature({'objects': snapshots, 'materials': scope['material_signatures'], 'preview': preview})


def worker(args):
    import bpy
    if bpy.app.version_string != '4.5.1 LTS' or bpy.context.preferences.filepaths.use_scripts_auto_execute:
        raise ValueError('Blender 4.5.1 with auto-execution disabled is required')
    scope = grant()
    loaded = Path(bpy.data.filepath).resolve()
    before = digest(loaded)
    state = model_state(scope)
    if args.mode == 'export':
        verify_file(loaded, scope['approved_candidate'])
        if args.model.exists() or args.record.exists() or args.model.resolve() == loaded:
            raise ValueError('Use new model and record paths')
        scene = bpy.context.scene
        scene['distribution_status'] = 'licensed; CC-BY-4.0'
        scene['license'] = scope['license']; scene['license_url'] = scope['license_url']
        scene['attribution'] = scope['attribution']
        scene.render.filepath = '//preview.png'
        for p in scope['prototype_meshes']:
            bpy.data.objects[p['id']]['candidate_scope'] = 'licensed prototype; CC-BY-4.0'
        if model_state(scope) != state:
            raise ValueError('Model changed during license annotation')
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(args.model), compress=True)
        if digest(loaded) != before:
            raise ValueError('Approved candidate changed')
        write_json(args.record, {'source_candidate_sha256': before, 'source_unchanged': True,
                                'state_sha256': state, 'file_sha256': digest(args.model)})
        return
    record = read_json(args.record)
    if before != record['file_sha256'] or state != record['state_sha256']:
        raise ValueError('Saved or extracted model differs')
    if (bpy.context.scene.get('license') != scope['license']
            or bpy.context.scene.get('license_url') != scope['license_url']
            or bpy.context.scene.get('attribution') != scope['attribution']
            or bpy.context.scene.get('distribution_status') != 'licensed; CC-BY-4.0'
            or any(bpy.data.objects[p['id']].get('candidate_scope') != 'licensed prototype; CC-BY-4.0'
                   for p in scope['prototype_meshes'])):
        raise ValueError('Saved license annotations differ')
    if args.result.exists() or args.render.exists():
        raise ValueError('Use new verification outputs')
    verify_file(args.preview, scope['approved_preview'])
    bpy.context.scene.render.filepath = str(args.render)
    bpy.ops.render.render(write_still=True)
    import numpy as np
    arrays = []
    for path in (args.preview, args.render):
        image = bpy.data.images.load(str(path), check_existing=False)
        if tuple(image.size) != (1200, 850):
            raise ValueError('Preview dimensions changed')
        pixels = np.empty(len(image.pixels), dtype=np.float32); image.pixels.foreach_get(pixels)
        if not np.isfinite(pixels).all() or np.max(pixels.reshape(-1, 4)[:, 3]) == 0:
            raise ValueError('Invalid preview')
        arrays.append(pixels)
    if not np.array_equal(*arrays):
        raise ValueError('Licensed preview pixels differ from the approved candidate')
    if digest(loaded) != before:
        raise ValueError('Model changed during verification')
    write_json(args.result, {'ok': True, 'license': scope['license'], 'blender': bpy.app.version_string,
        'mesh_prototypes': 16, 'procedural_materials': 31, 'images': 0, 'libraries': 0, 'embedded_texts': 0,
        'state_sha256': state, 'file_sha256': before, 'file_unchanged': True,
        'approved_preview_pixels_equal': True, 'verifier_sha256_lf': code_hash()})


def build(args):
    scope = grant()
    verify_file(args.input, scope['approved_candidate'])
    verify_file(args.preview, scope['approved_preview'])
    if args.output.exists():
        raise ValueError('Use a new package output directory')
    args.output.mkdir(parents=True)
    model = args.output / 'kit.blend'; record = args.output / 'export-record.json'
    verification = args.output / 'verification.json'

    def run(stage, source, options, log):
        command = [str(args.blender), '--factory-startup', '--disable-autoexec', '--background', str(source),
                   '--python-exit-code', '1', '--python', str(Path(__file__).resolve()), '--', stage, *map(str, options)]
        with (args.output / log).open('w', encoding='utf8') as output:
            subprocess.run(command, check=True, stdout=output, stderr=subprocess.STDOUT, timeout=180,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))

    run('export', args.input, ['--model', model, '--record', record], 'export.log')
    run('check', model, ['--record', record, '--preview', args.preview, '--result', verification,
                         '--render', args.output / 'licensed-preview.png'], 'verification.log')
    files = {'kit.blend': model.read_bytes(), 'preview.png': args.preview.read_bytes(),
             'verification.json': verification.read_bytes()}
    for destination, source in [('README.md', 'PACKAGE-README.md'), ('ASSET-LICENSE.md', 'ASSET-LICENSE.md'),
                                ('NOTICE.md', 'NOTICE.md'), ('provenance.json', 'provenance.json')]:
        files[destination] = (ASSETS / source).read_text(encoding='utf8').encode('utf8')
    archive = args.output / ARCHIVE_NAME
    record_inventory = write_archive(archive, files)
    write_json(args.output / 'inventory.json', record_inventory)
    # The fixed, verified member names cannot escape this fresh directory.
    received = args.output / 'received'; received.mkdir()
    with zipfile.ZipFile(archive) as package:
        for name in package.namelist():
            (received / name).write_bytes(package.read(name))
    run('check', received / 'kit.blend', ['--record', record, '--preview', received / 'preview.png',
        '--result', args.output / 'received-verification.json', '--render', args.output / 'received-preview.png'], 'received.log')
    roundtrip = read_json(args.output / 'received-verification.json')
    if not roundtrip['ok'] or any(digest(received / n) != p['sha256'] for n, p in record_inventory['files'].items()):
        raise ValueError('Extracted package changed')
    archive_pin = digest(archive)
    (args.output / 'SHA256SUMS.txt').write_text(archive_pin + '  ' + ARCHIVE_NAME + '\n', encoding='ascii')
    result = {'version': 1, 'status': 'licensed-package-verified-public-release-pending',
        'license': scope['license'], 'asset_id': scope['asset_id'],
        'package': {'file': ARCHIVE_NAME, 'bytes': archive.stat().st_size, 'sha256': archive_pin},
        'model': record_inventory['files']['kit.blend'], 'verification': roundtrip,
        'source_candidate_unchanged': digest(args.input) == scope['approved_candidate']['sha256'],
        'archive_members': sorted(FILES | {'inventory.json'}), 'zip_crc_and_hashes_verified': True,
        'reopened_after_extraction': True, 'public_download_url': None,
        'platform_scope': 'Same Windows PC, fresh extraction directory; no legacy city input was opened.',
        'packager_sha256_lf': code_hash()}
    write_json(args.output / 'package-result.json', result)
    print(json.dumps(result, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode', required=True)
    prepare = sub.add_parser('build')
    for option in ('input', 'preview', 'blender', 'output'):
        prepare.add_argument('--' + option, type=Path, required=True)
    export = sub.add_parser('export')
    for option in ('model', 'record'):
        export.add_argument('--' + option, type=Path, required=True)
    check = sub.add_parser('check')
    for option in ('record', 'preview', 'result', 'render'):
        check.add_argument('--' + option, type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else None)
    for name, value in vars(args).items():
        if isinstance(value, Path):
            setattr(args, name, value.resolve())
    build(args) if args.mode == 'build' else worker(args)


if __name__ == '__main__':
    main()
