# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Disposable edit/save/reopen check; never a proposed change to the city."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
import numpy as np

TARGET = "Mori independent / floors and roof"


def snapshot():
    meshes = {}
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        mesh = obj.data
        value = hashlib.sha256()
        for collection, field, width, dtype in (
            (mesh.vertices, "co", 3, "<f4"),
            (mesh.loops, "vertex_index", 1, "<i4"),
            (mesh.polygons, "loop_total", 1, "<i4"),
            (mesh.polygons, "material_index", 1, "<i4"),
        ):
            array = np.empty(len(collection) * width, dtype=dtype)
            collection.foreach_get(field, array)
            value.update(array.tobytes())
        for layer in mesh.uv_layers:
            array = np.empty(len(layer.data) * 2, dtype="<f4")
            layer.data.foreach_get("uv", array)
            value.update(layer.name.encode("utf-8"))
            value.update(array.tobytes())
        value.update(np.asarray(obj.matrix_world, dtype="<f4").tobytes())
        value.update(json.dumps([mat.name if mat else None for mat in mesh.materials]).encode())
        meshes[obj.name] = value.hexdigest()
    images = {}
    for image in bpy.data.images:
        if image.type in {"RENDER_RESULT", "COMPOSITING"}:
            continue
        if not image.packed_file:
            raise ValueError("Unexpected unpacked image")
        images[image.name] = hashlib.sha256(image.packed_file.data).hexdigest()
    if bpy.data.libraries or bpy.data.texts:
        raise ValueError("Unexpected library or embedded script")
    return {"meshes": meshes, "packed_images": images}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["edit", "reopen"])
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--result", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    if bpy.app.version != (4, 5, 1) or bpy.context.preferences.filepaths.use_scripts_auto_execute:
        raise ValueError("Requires Blender 4.5.1 with automatic script execution disabled")
    bpy.ops.wm.open_mainfile(filepath=str(args.input.resolve()), use_scripts=False)
    current = snapshot()
    if len(current["meshes"]) != 42:
        raise ValueError("Unexpected Mori mesh count")
    if args.phase == "edit":
        if not args.output or args.output.exists() or args.record.exists():
            raise ValueError("Use new output and record files")
        obj = bpy.data.objects[TARGET]
        before = list(obj.data.vertices[0].co)
        obj.data.vertices[0].co.x += 0.125
        obj.data.update()
        bpy.context.view_layer.update()
        expected = snapshot()
        changed = sorted(name for name in current["meshes"] if current["meshes"][name] != expected["meshes"][name])
        if changed != [TARGET] or current["packed_images"] != expected["packed_images"]:
            raise ValueError("Test edit changed unexpected mesh/image data")
        bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()), compress=True)
        record = {"test_only": True, "object": TARGET, "vertex": 0,
                  "before": before, "after": list(obj.data.vertices[0].co),
                  "expected": expected, "changed_meshes": changed}
        args.record.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    else:
        record = json.loads(args.record.read_text(encoding="utf-8"))
        if current != record["expected"]:
            raise ValueError("Saved mesh/UV/transform/material-slot or packed-image state changed on reopen")
        actual = list(bpy.data.objects[TARGET].data.vertices[0].co)
        if actual != record["after"] or actual == record["before"]:
            raise ValueError("Test vertex edit did not persist")
        if not args.result or args.result.exists():
            raise ValueError("Use a new result file")
        args.result.write_text(json.dumps({"ok": True, "blender": bpy.app.version_string,
            "meshes": len(current["meshes"]), "test_only": True,
            "changed_meshes": record["changed_meshes"], "edited_vertex_persisted": True,
            "mesh_uv_transform_material_slots_preserved": True,
            "packed_images_preserved": True, "separate_process_reopen": True}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
