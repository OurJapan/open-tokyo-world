# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Keep the reviewed PR52 woodland on both sides of the tower comparison."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import tokyo_tower_city_repairs as repairs

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'assets/tokyo-tower/city-main-sync-v1.json'


def require_append(old, new, reference):
    require = repairs.require
    for key in old:
        if key not in ('objects', 'materials', 'collections'):
            require(old[key] == new[key], 'Woodland append changed city ' + key)
    for key in ('objects', 'materials', 'collections'):
        added = reference[key]
        require(not set(old[key]) & set(added), 'Woodland already present or name conflict')
        require(set(new[key]) == set(old[key]) | set(added), 'Woodland membership differs: ' + key)
        require(all(new[key][n] == value for n, value in old[key].items()), 'Existing city changed: ' + key)
        require(all(new[key][n] == value for n, value in added.items()), 'PR52 state differs: ' + key)


def append(path):
    import bpy
    from shiba_momijidani_v1 import COLLECTION, ADDED
    repairs.require(COLLECTION not in bpy.data.collections and not ADDED.intersection(bpy.data.objects.keys()), 'Woodland already present')
    old_libraries = set(bpy.data.libraries)
    with bpy.data.libraries.load(str(path), link=False) as (available, loaded):
        repairs.require(COLLECTION in available.collections, 'Missing PR52 collection')
        loaded.collections = [COLLECTION]
    collection = loaded.collections[0]
    repairs.require(set(o.name for o in collection.objects) == ADDED, 'Unexpected woodland objects')
    bpy.context.scene.collection.children.link(collection)
    bpy.context.view_layer.update()
    new_libraries = set(bpy.data.libraries) - old_libraries
    # Blender retains an append-source bookkeeping ID even with link=False.
    # Verify no datablock is linked, then drop only these new source stubs.
    repairs.require(not any(block.library in new_libraries for block in bpy.data.user_map()), 'Linked woodland dependency')
    for library in new_libraries:
        repairs.require(Path(library.filepath).resolve() == path.resolve(), 'Unexpected append source')
        bpy.data.libraries.remove(library)


def build(a, pin):
    import bpy
    from shiba_momijidani_v1 import COLLECTION, ADDED, FEATURE
    out = a.output; out.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    append(a.shiba)
    reference = repairs.city.snapshot()
    repairs.require(len(reference['objects']) == 5 and len(reference['materials']) == 11 and
                    len(reference['collections']) == 1 and not bpy.data.images and not bpy.data.libraries and not bpy.data.texts,
                    'Unexpected woodland dependency')
    repairs.require(all(bpy.data.objects[n].get('otw_feature_id') == FEATURE for n in ADDED), 'PR52 feature differs')
    states = {}
    for label in ('before', 'after'):
        bpy.ops.wm.open_mainfile(filepath=str(a.repairs / (label + '.blend')), use_scripts=False)
        old = repairs.snapshot()
        append(a.shiba)
        current = repairs.snapshot()
        require_append(old, current, reference)
        states[label] = current
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(out / (label + '.blend')), compress=True, relative_remap=False)
        print('PR52_APPEND_OK', label, flush=True)
    record = repairs.city.paint.load(a.repairs / 'build.json')
    record['initial_tower_build_sha256'] = repairs.city.paint.sha(a.repairs / 'build.json')
    record['inputs']['shiba'] = pin['shiba_sha256']
    record['baseline_sha256'] = repairs.city.paint.sha(out / 'before.blend')
    record['candidate_sha256'] = repairs.city.paint.sha(out / 'after.blend')
    record['city_objects'] = len(states['after']['objects'])
    record['unchanged_objects'] = record['city_objects'] - 5
    record['main_sync'] = {'main_commit': pin['main_commit'], 'added_to_both_sides': sorted(ADDED),
                           'materials_added_to_both_sides': sorted(reference['materials']),
                           'existing_city_preserved_on_both_sides': True, 'script_sha256': repairs.city.paint.sha(__file__)}
    repairs.city.paint.write(out / 'build.json', record)
    repairs.city.paint.write(out / 'before-state.json', states['before'])
    repairs.city.paint.write(out / 'expected-state.json', states['after'])


def main():
    import bpy
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--phase', choices=['build', 'validate', 'render-before', 'render-after', 'compare'], required=True)
    p.add_argument('--repairs', type=Path, required=True)
    p.add_argument('--shiba', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(sys.argv[sys.argv.index('--') + 1:]); a.output = a.output.resolve(); a.view = None
    pin = repairs.city.paint.load(PLAN)
    repairs.require(bpy.app.version == (4, 5, 1) and not bpy.context.preferences.filepaths.use_scripts_auto_execute, 'Use Blender 4.5.1 with autoexec disabled')
    repairs.require(a.output.is_relative_to(ROOT / 'data/local'), 'Output must be in worktree data/local')
    paths = {'before': a.repairs / 'before.blend', 'after': a.repairs / 'after.blend', 'shiba': a.shiba}
    for label, path in paths.items():
        repairs.require(repairs.city.paint.sha(path) == pin[label + '_sha256'], 'Wrong pinned input: ' + label)
    if a.phase == 'build': build(a, pin)
    elif a.phase == 'validate':
        limits = repairs.city.paint.load(repairs.PLAN)
        limits['limits'] += pin['limits']
        repairs.validate(a, limits)
        result = repairs.city.paint.load(a.output / 'validation.json')
        result['main_sync'] = repairs.city.paint.load(a.output / 'build.json')['main_sync']
        repairs.city.paint.write(a.output / 'validation.json', result)
    elif a.phase.startswith('render-'):
        repairs.render(a, a.phase.removeprefix('render-'))
    else:
        repairs.deck.VIEWS = repairs.VIEWS
        repairs.deck.compare(a.output)
        page = a.output / 'review.html'
        page.write_text(page.read_text(encoding='utf8').replace('Tokyo Tower: top-deck window bases',
            'Tokyo Tower: paint and window bases, PR52 woodland retained').replace('Original model: ark4ez / OurJapan, CC BY 4.0.',
            'Tower original: ark4ez / OurJapan, CC BY 4.0. City context retains all existing third-party conditions.'), encoding='utf8')
    for label, path in paths.items():
        repairs.require(repairs.city.paint.sha(path) == pin[label + '_sha256'], 'Input changed: ' + label)
    print('CITY_MAIN_SYNC_OK', a.phase, flush=True)


if __name__ == '__main__': main()
