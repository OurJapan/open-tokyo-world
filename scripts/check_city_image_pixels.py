# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Blender diagnostic: compare decoded pixels and a specific resize hypothesis.

Run with --factory-startup --disable-autoexec --background INPUT --python ... --
--report REPORT --cache CACHE --output NEW_DIRECTORY. Never saves the scene.
"""
import argparse
from collections import Counter
import hashlib
from pathlib import Path
import sys
import tempfile

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_city_images import embedded_images, read_json, sha, source_dataset, write_new_json


def file_sha(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def rgba8(image):
    pixels = np.empty(len(image.pixels), dtype=np.float32)
    image.pixels.foreach_get(pixels)
    if image.channels != 4 or not np.isfinite(pixels).all() or (pixels < 0).any() or (pixels > 1).any():
        raise ValueError("Expected finite RGBA values in [0,1]")
    return np.rint(pixels * 255).astype(np.uint8)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    report = read_json(args.report)
    input_hash = file_sha(bpy.data.filepath)
    if bpy.app.version != (4, 5, 1) or report["input_sha256"] != input_hash:
        raise ValueError("Wrong Blender version or scene for this report")
    if not report.get("source_lock_enforced") or report["source_errors"]:
        raise ValueError("Use a complete report checked against a source lock")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    results = []
    # Only this newly created child directory contains temporary extracted bytes.
    with tempfile.TemporaryDirectory(prefix="decode-", dir=output) as temporary:
        assert Path(temporary).resolve().is_relative_to(output)
        for record in report["images"]:
            if record["status"] != "content-mismatch":
                continue
            original = bpy.data.images.get(record["image"])
            if not original or not original.packed_file or sha(original.packed_file.data) != record["packed_sha256"]:
                raise ValueError("Packed image differs from inventory")
            size = list(original.size)
            expected = rgba8(original)
            item = {"image": original.name, "packed_sha256": record["packed_sha256"], "size": size,
                    "colorspace": original.colorspace_settings.name, "rgba8_sha256": sha(expected.tobytes()), "comparisons": []}
            for url in record["claimed_urls"]:
                source_dataset(url)
                data = (args.cache / (sha(url.encode()) + ".b3dm")).read_bytes()
                source = report["sources"][url]
                if len(data) != source["bytes"] or sha(data) != source["sha256"]:
                    raise ValueError("Source cache changed since locked verification")
                for image in embedded_images(data, include_bytes=True):
                    extension = {"image/webp": ".webp", "image/png": ".png", "image/jpeg": ".jpg"}[image["mime_type"]]
                    path = Path(temporary) / (image["sha256"] + extension)
                    path.write_bytes(image["data"])
                    decoded = bpy.data.images.load(str(path), check_existing=False)
                    try:
                        decoded.colorspace_settings.name = original.colorspace_settings.name
                        source_size = list(decoded.size)
                        resized = source_size != size
                        if resized:
                            decoded.scale(*size)
                        actual = rgba8(decoded)
                        if actual.shape != expected.shape:
                            raise ValueError("Decoded image dimensions differ")
                        delta = np.abs(actual.astype(np.int16) - expected.astype(np.int16))
                        item["comparisons"].append({"url": url, "source_image_index": image["index"],
                            "source_image_sha256": image["sha256"], "source_size": source_size,
                            "operation": "Blender Image.scale then RGBA8 rounding" if resized else "decode to RGBA8",
                            "rgba8_sha256": sha(actual.tobytes()), "exact_rgba8_match": bool(np.array_equal(actual, expected)),
                            "max_channel_delta": int(delta.max()), "mean_channel_delta": float(delta.mean())})
                    finally:
                        bpy.data.images.remove(decoded)
                        path.unlink()
            item["status"] = "exact-rgba8-match" if any(c["exact_rgba8_match"] for c in item["comparisons"]) else "not-exact-under-tested-transform"
            results.append(item)
            original.buffers_free()
            if len(results) % 20 == 0:
                print(f"Compared decoded pixels for {len(results)} images", flush=True)
    if file_sha(bpy.data.filepath) != input_hash:
        raise ValueError("Input changed during diagnostic")
    result = {"version": 1, "input_sha256": input_hash, "source_report_sha256": file_sha(args.report),
              "tool_sha256_lf": sha(Path(__file__).read_bytes().replace(b"\r\n", b"\n")),
              "blender": bpy.app.version_string, "input_unchanged": True, "scene_saved": False,
              "summary": dict(Counter(r["status"] for r in results)), "images": results,
              "limits": ["Exact comparison is of rounded 8-bit RGBA, not float pixels or encoded files.",
                         "Resize equivalence tests a reconstruction hypothesis; it does not prove historical processing.",
                         "No tolerance is used to declare matches; similarity alone does not establish origin.",
                         "This diagnostic grants no redistribution rights and changes no saved scene."]}
    write_new_json(output / "report.json", result)
    print(result["summary"])


if __name__ == "__main__":
    main()
