# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Read embedded production clues into a new local directory; never save a blend.

Blender --factory-startup --disable-autoexec --background INPUT
        --python-exit-code 1 --python scripts/audit_city_production.py -- OUTPUT
Full custom properties and Text contents are private inspection data, not a grant.
"""
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from city_catalog import classify, read, require, sha, write


def main():
    import bpy
    root = Path(__file__).resolve().parents[1]
    config = read(root / 'manifests/city-catalog-v1.json')
    scope = read(root / 'sources/city-pr12-authorship-notes.json')
    source = Path(bpy.data.filepath)
    expected = config['input']['sha256']
    require(source.stat().st_size == config['input']['bytes'] and sha(source) == expected, 'Wrong city input')
    require(scope['baseline']['sha256'] == expected, 'Authorship notes reference another input')
    require(bpy.app.version_string == config['input']['blender_version'], 'Wrong Blender version')
    require(not bpy.context.preferences.filepaths.use_scripts_auto_execute, 'Disable automatic script execution')
    output = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
    require(not output.exists(), 'Use a new output directory')
    output.mkdir(parents=True)

    def value(v):
        if v is None or isinstance(v, (str, bool, int, float)):
            return v
        if isinstance(v, bpy.types.ID):
            return {'id_type': v.bl_rna.identifier, 'name': v.name, 'library': v.library.filepath if v.library else None}
        if hasattr(v, 'to_dict'):
            return {k: value(x) for k, x in v.items()}
        if hasattr(v, 'to_list'):
            return [value(x) for x in v.to_list()]
        return {'unserialized_type': type(v).__name__}

    def props(item):
        return {k: value(item[k]) for k in item.keys()}

    groups = {g['id'] for g in scope['candidate_groups']}
    objects, materials, meshes = [], {}, {}
    for obj in sorted(bpy.context.scene.objects, key=lambda o: o.name):
        if obj.type != 'MESH':
            continue
        group = classify({'object': obj.name, 'collections': [c.name for c in obj.users_collection]}, config['groups'])
        if group not in groups:
            continue
        objects.append({'name': obj.name, 'group': group, 'properties': props(obj), 'mesh': obj.data.name,
                        'library': obj.library.filepath if obj.library else None,
                        'modifiers': [{'name': m.name, 'type': m.type} for m in obj.modifiers]})
        meshes[obj.data.name] = props(obj.data)
        for mat in obj.data.materials:
            if mat:
                materials[mat.name] = props(mat)
    require(len(objects) == scope['candidate_mesh_objects'], 'Unexpected authorship scope coverage')
    texts = []
    for i, item in enumerate(sorted(bpy.data.texts, key=lambda t: t.name)):
        data = item.as_string().encode('utf8')
        # Never use untrusted datablock names as output paths or execute Text.
        target = output / ('text-%03d.txt' % i)
        target.write_bytes(data)
        texts.append({'name': item.name, 'filepath': item.filepath, 'use_module': item.use_module,
                      'utf8_bytes': len(data), 'utf8_sha256': hashlib.sha256(data).hexdigest(), 'local_text': target.name})
    result = {'version': 1, 'input_sha256': expected, 'blender_version': bpy.app.version_string,
              'code_sha256_lf': hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
              'texts': texts, 'scenes': {s.name: props(s) for s in bpy.data.scenes},
              'collections': {c.name: props(c) for c in bpy.data.collections},
              'objects': objects, 'meshes': meshes, 'materials': materials,
              'libraries': [lib.filepath for lib in bpy.data.libraries],
              'input_unchanged': sha(source) == expected}
    require(result['input_unchanged'], 'Input changed')
    write(output / 'audit.json', result)
    print(json.dumps({'objects': len(objects), 'text_blocks': len(texts), 'input_unchanged': True}))


if __name__ == '__main__':
    main()
