"""Read-only Blender image/usage inventory; embedded URLs are claims, not licenses.

Run Blender with --disable-autoexec --background INPUT --python this_file -- OUTPUT.
No image bytes or absolute local paths are exported. Never saves the input scene.
"""
import hashlib
import json
import sys
from pathlib import Path
import bpy


def images_in_tree(tree, seen=None):
    seen = set() if seen is None else seen
    if tree is None or tree.as_pointer() in seen:
        return set()
    seen.add(tree.as_pointer())
    result = set()
    for node in tree.nodes:
        image = getattr(node, 'image', None)
        if image:
            result.add(image)
        result.update(images_in_tree(getattr(node, 'node_tree', None), seen))
    return result


def main():
    output = Path(sys.argv[sys.argv.index('--') + 1])
    if output.exists():
        raise ValueError('Use a new output path')
    usages = {image: [] for image in bpy.data.images}
    for obj in bpy.context.scene.objects:
        images = set()
        for slot in obj.material_slots:
            if slot.material:
                images.update(images_in_tree(slot.material.node_tree))
        for image in images:
            usages[image].append({
                'object': obj.name,
                'source_claim': str(obj.get('source', '')),
                'source_url_claim': str(obj.get('source_url', '')),
            })
    records = []
    for image, uses in sorted(usages.items(), key=lambda item: item[0].name):
        records.append({
            'image': image.name,
            'source_type': image.source,
            'packed_sha256': hashlib.sha256(image.packed_file.data).hexdigest() if image.packed_file else None,
            'material_object_uses': uses,
            'provenance_status': 'embedded-source-claim' if any(u['source_url_claim'] for u in uses) else 'unresolved',
            'redistribution': 'pending',
        })
    result = {
        'version': 1,
        'input_sha256': hashlib.file_digest(open(bpy.data.filepath, 'rb'), 'sha256').hexdigest(),
        'images': records,
        'limits': ['Object source URLs do not prove image origin or usage rights.',
                   'World, compositor, unused material and non-material usages are not mapped.',
                   'No image-to-upstream byte comparison performed.'],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print('Image source inventory:', len(records))


if __name__ == '__main__':
    main()
