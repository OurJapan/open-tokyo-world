# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Read-only runtime and image/library checks for the contributor workspace."""
import argparse
import json
import sys
from pathlib import Path

import bpy
import numpy
from io_scene_gltf2.io.com.draco import dll_path


def inspect_scene(path):
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    missing, unsupported, external_images = [], [], []
    packed = 0
    for image in bpy.data.images:
        if image.source in {"GENERATED", "VIEWER"} or image.type in {"RENDER_RESULT", "COMPOSITING"}:
            continue
        if image.packed_file or len(image.packed_files):
            packed += 1
        elif image.source != "FILE":
            unsupported.append(image.name)
        elif not image.filepath or not Path(bpy.path.abspath(image.filepath, library=image.library)).is_file():
            missing.append(image.name)
        else:
            external_images.append(image.name)
    libraries = [lib.name for lib in bpy.data.libraries if not Path(bpy.path.abspath(lib.filepath)).is_file()]
    return {
        "opened": True,
        "objects": len(bpy.data.objects),
        "meshes": sum(obj.type == "MESH" for obj in bpy.data.objects),
        "packed_images": packed,
        "missing_images": missing,
        "unsupported_images": unsupported,
        "missing_libraries": libraries,
        "external_images": external_images,
        "linked_libraries": len(bpy.data.libraries),
        "self_contained_images_libraries": not (missing or unsupported or external_images or bpy.data.libraries),
        "references_ok": not (missing or unsupported or libraries),
        "scope": "Opening and image/library references only; not a full geometry, external dependency or accuracy audit.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--input", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    report = {
        "ok": False,
        "blender_version": ".".join(map(str, bpy.app.version)),
        "blender_python": sys.version.split()[0],
        "numpy": numpy.__version__,
        "draco_available": dll_path().is_file(),
        "autoexec_disabled": not bpy.context.preferences.filepaths.use_scripts_auto_execute,
        "saved_scene": False,
    }
    try:
        if args.input:
            report["scene"] = inspect_scene(args.input)
        report["ok"] = report["draco_available"] and report["autoexec_disabled"] and report.get("scene", {}).get("references_ok", True)
        if not report["ok"]:
            raise ValueError("Blender runtime or scene reference check failed")
    except Exception as error:
        report["error"] = str(error)
        raise
    finally:
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
