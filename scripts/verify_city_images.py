# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Compare packed image hashes with embedded images in selected official b3dm files.

This checks byte identity, not redistribution rights. No images are exported.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import threading
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_DOWNLOAD_BYTES = 1024 * 1024 * 1024
DATASETS = {
    "minato-2025-lod3": "https://assets.cms.plateau.reearth.io/assets/c7/ffcc73-1d33-434b-a49a-aa0289160814/13103_minato-ku_pref_2025_citygml_1_op_bldg_3dtiles_13103_minato-ku_lod3/",
    "chiyoda-2025-lod2": "https://assets.cms.plateau.reearth.io/assets/28/07d0a1-b6be-46ef-bd87-4f0683b5ef6e/13101_chiyoda-ku_pref_2025_citygml_1_op_bldg_3dtiles_13101_chiyoda-ku_lod2/",
    "chuo-2025-lod2": "https://assets.cms.plateau.reearth.io/assets/09/83a3f6-6605-477c-84dc-a973008b5a27/13102_chuo-ku_pref_2025_citygml_1_op_bldg_3dtiles_13102_chuo-ku_lod2/",
}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_new_json(path, value):
    with Path(path).open("x", encoding="utf8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source_dataset(url):
    for name, base in DATASETS.items():
        if re.fullmatch(re.escape(base) + r"data/data[0-9]+\.b3dm", url):
            return name
    raise ValueError("Source is outside the three reviewed HTTPS dataset paths")


class ExactRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Redirected source requires a separately reviewed URL")


def section(data, offset, length):
    if type(offset) is not int or type(length) is not int or offset < 0 or length < 0 or offset + length > len(data):
        raise ValueError("Binary section outside buffer")
    return data[offset:offset + length]


def embedded_images(data, include_bytes=False):
    """Read b3dm v1 containing GLB v2; reject external/unsupported image layouts."""
    magic, version, size, fj, fb, bj, bb = struct.unpack("<4s6I", section(data, 0, 28))
    if magic != b"b3dm" or version != 1 or size != len(data):
        raise ValueError("Unsupported b3dm header")
    glb_start = 28 + fj + fb + bj + bb
    section(data, 28, fj + fb + bj + bb)
    glb = section(data, glb_start, len(data) - glb_start)
    if struct.unpack("<4sII", section(glb, 0, 12)) != (b"glTF", 2, len(glb)):
        raise ValueError("Unsupported GLB header")
    json_length, json_type = struct.unpack("<II", section(glb, 12, 8))
    if json_type != 0x4E4F534A or json_length % 4:
        raise ValueError("Expected aligned GLB JSON chunk")
    doc = json.loads(section(glb, 20, json_length))
    bin_length, bin_type = struct.unpack("<II", section(glb, 20 + json_length, 8))
    if bin_type != 0x004E4942 or bin_length % 4 or 28 + json_length + bin_length != len(glb):
        raise ValueError("Expected one aligned GLB BIN chunk")
    binary = section(glb, 28 + json_length, bin_length)
    buffers = doc.get("buffers", [])
    if len(buffers) != 1 or "uri" in buffers[0]:
        raise ValueError("External or multiple buffers unsupported")
    declared = buffers[0]["byteLength"]
    section(binary, 0, declared)
    if len(binary) - declared > 3:
        raise ValueError("Unexpected GLB buffer padding")
    images = []
    for index, image in enumerate(doc.get("images", [])):
        if "uri" in image or image.get("mimeType") not in {"image/png", "image/jpeg", "image/webp"}:
            raise ValueError("External or unsupported image layout")
        view_index = image["bufferView"]
        views = doc.get("bufferViews", [])
        if type(view_index) is not int or not 0 <= view_index < len(views):
            raise ValueError("Invalid image bufferView")
        view = views[view_index]
        if view.get("buffer") != 0 or "byteStride" in view:
            raise ValueError("Unsupported image bufferView")
        raw = section(binary[:declared], view.get("byteOffset", 0), view["byteLength"])
        if not raw:
            raise ValueError("Empty image")
        record = {"index": index, "mime_type": image["mimeType"], "bytes": len(raw), "sha256": sha(raw)}
        if include_bytes:
            record["data"] = raw
        images.append(record)
    if not images:
        raise ValueError("No embedded images")
    return images


class DownloadBudget:
    def __init__(self, maximum=MAX_DOWNLOAD_BYTES):
        self.maximum, self.used, self.lock = maximum, 0, threading.Lock()

    def consume(self, count):
        with self.lock:
            if self.used + count > self.maximum:
                raise ValueError("Total download limit exceeded")
            self.used += count


def get_source(url, cache, download, budget, expected=None):
    dataset = source_dataset(url)
    key = sha(url.encode("utf8"))
    path, receipt_path = cache / (key + ".b3dm"), cache / (key + ".json")
    if path.exists() or receipt_path.exists():
        if not (path.is_file() and receipt_path.is_file()):
            raise ValueError("Incomplete cache entry; use a new cache directory")
        receipt = read_json(receipt_path)
        if path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("Cached source exceeds file limit")
        data = path.read_bytes()
        if receipt["url"] != url or receipt["bytes"] != len(data) or receipt["sha256"] != sha(data):
            raise ValueError("Cached source differs from receipt; refusing replacement")
    else:
        if not download:
            raise ValueError("Source not cached; explicitly use --download to fetch it")
        opener = urllib.request.build_opener(ExactRedirect())
        chunks, size = [], 0
        with opener.open(url, timeout=45) as response:
            if response.geturl() != url:
                raise ValueError("Unexpected response URL")
            while chunk := response.read(64 * 1024):
                budget.consume(len(chunk))
                size += len(chunk)
                if size > MAX_FILE_BYTES:
                    raise ValueError("Source exceeds file limit")
                chunks.append(chunk)
        data = b"".join(chunks)
        receipt = {"url": url, "bytes": len(data), "sha256": sha(data), "retrieved_at": datetime.now(timezone.utc).isoformat()}
        if expected and any(receipt[k] != expected[k] for k in ("bytes", "sha256")):
            raise ValueError("Downloaded source differs from the source lock")
        # Validate before installing, and never replace an existing cache entry.
        embedded_images(data)
        cache.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as handle:
            handle.write(data)
        write_new_json(receipt_path, receipt)
    if expected and any(receipt[k] != expected[k] for k in ("bytes", "sha256")):
        raise ValueError("Cached source differs from the source lock")
    return {**receipt, "dataset": dataset, "images": embedded_images(data), "ok": True}


def claimed_urls(image):
    return sorted({use["source_url_claim"] for use in image["material_object_uses"] if use["source_url_claim"]})


def compare_images(inventory, sources):
    records = []
    by_hash = {}
    for url, source in sources.items():
        for image in source.get("images", []):
            if source.get("ok"):
                by_hash.setdefault(image["sha256"], set()).add(url)
    for image in inventory["images"]:
        claims, packed = claimed_urls(image), image["packed_sha256"]
        matches = sorted(by_hash.get(packed, set())) if packed else []
        direct = sorted(set(matches) & set(claims))
        if packed and direct:
            status = "matched-claimed-source"
        elif packed and matches:
            status = "matched-other-source-review-mapping"
        elif not packed and image["source_type"] == "VIEWER" and not image["material_object_uses"]:
            status = "runtime-only"
        elif not packed:
            status = "unpacked-or-unsupported"
        elif not claims:
            status = "unresolved-no-source"
        elif any(not sources.get(url, {}).get("ok") for url in claims):
            status = "source-unavailable"
        else:
            status = "content-mismatch"
        records.append({"image": image["image"], "packed_sha256": packed, "status": status,
                        "objects": sorted({u["object"] for u in image["material_object_uses"]}),
                        "claimed_urls": claims, "matching_urls": matches, "redistribution": "pending-separate-review"})
    return records


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--cache", type=Path, default=ROOT / "data/local/sources/image-audit")
    parser.add_argument("--output", required=True, type=Path, help="New report directory; never overwritten")
    parser.add_argument("--download", action="store_true", help="Fetch only explicitly allowed official datasets, up to 1 GiB")
    parser.add_argument("--source-lock", type=Path, help="Check upstream bytes against an earlier source-lock.json")
    args = parser.parse_args(argv)
    inventory = read_json(args.inventory)
    pinned = read_json(ROOT / "manifests/contributor-workspace.json")["profiles"]["city"]["asset"]["sha256"]
    if inventory.get("version") != 1 or inventory.get("input_sha256") != pinned:
        raise ValueError("Inventory must belong to the pinned accepted city")
    names = [i["image"] for i in inventory["images"]]
    if len(set(names)) != len(names) or not names:
        raise ValueError("Empty inventory or duplicate image names")
    urls = sorted({url for image in inventory["images"] for url in claimed_urls(image)})
    if not urls or len(urls) > 1000:
        raise ValueError("Unexpected source count")
    for url in urls:
        source_dataset(url)
    lock = read_json(args.source_lock) if args.source_lock else None
    if lock and (lock.get("input_sha256") != pinned or set(lock["sources"]) != set(urls)):
        raise ValueError("Source lock does not cover this inventory")
    args.output.mkdir(parents=True, exist_ok=False)
    sources, budget = {}, DownloadBudget()
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(get_source, url, args.cache, args.download, budget,
                               lock["sources"][url] if lock else None): url for url in urls}
        for future in as_completed(futures):
            url = futures[future]
            try:
                sources[url] = future.result()
            except Exception as error:
                sources[url] = {"ok": False, "error": str(error)}
            if len(sources) % 25 == 0 or len(sources) == len(urls):
                print(f"Checked {len(sources)}/{len(urls)} official sources; errors: {sum(not s['ok'] for s in sources.values())}", flush=True)
    records = compare_images(inventory, sources)
    counts = dict(sorted(Counter(r["status"] for r in records).items()))
    source_lock = {"version": 1, "input_sha256": pinned, "sources": {
        url: {k: value[k] for k in ("bytes", "sha256")} for url, value in sorted(sources.items()) if value["ok"]}}
    write_new_json(args.output / "source-lock.json", source_lock)
    report = {"version": 1, "input_sha256": pinned, "inventory_sha256": sha(args.inventory.read_bytes()),
              "tool_sha256_lf": sha(Path(__file__).read_bytes().replace(b"\r\n", b"\n")),
              "checked_at": datetime.now(timezone.utc).isoformat(),
              "source_lock_enforced": lock is not None, "source_errors": sum(not s["ok"] for s in sources.values()),
              "summary": counts, "sources": dict(sorted(sources.items())), "images": records,
              "full_city_distribution_ready": False,
              "limits": ["Encoded image byte identity only; not geometry identity or legal clearance.",
                         "Object URL claims are checked, not treated as instructions or rights grants.",
                         "World, compositor and non-material usage are outside the input inventory's scope."]}
    write_new_json(args.output / "report.json", report)
    print(json.dumps({"summary": counts, "source_errors": report["source_errors"], "report": str(args.output / "report.json")}, indent=2))
    return 0 if report["source_errors"] == 0 else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError, struct.error) as error:
        print("Image verification error: " + str(error), file=sys.stderr)
        raise SystemExit(1)
