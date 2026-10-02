# Mori plaza west footway: provisional local grading

This review candidate continues the adopted entrance junction north along approximately 15m of the mapped west footway. It starts from main `805310ef7a6aad5a13104334e798fb83b35f1711` and the accepted connection city input. It does not update the accepted city profile or its asset registration. [Selected matched comparison images](../renders/previews/mori-plaza-west-path-v1/README.md), [execution record](mori-plaza-west-path-v1-run.json), [saved-scene validation](mori-plaza-west-path-v1-validation.json), and [public evidence manifest](mori-plaza-west-path-v1-evidence.json) accompany the draft review.

## Basis and bounded change

The fixed production input contains OSM way `1443867478`, version 3, timestamp `2026-03-07T08:44:14Z`, tagged `highway=footway` and `surface=paving_stones`. Its XY line identifies the west path. OSM does not establish the elevation used here. The inherited road generator placed road and sidewalk surfaces at 0.30m and 0.46m, while the adopted plaza is at 0.11m. The saved input has 75 selected road/paving contact pairs in the target interval, with a maximum step of approximately 0.35m. See [the level audit](mori-plaza-level-audit.md) for the original model-space diagnosis.

The new flat core is 8m by 20m, centered on local plaza coordinates `(-22,61)`, at the adopted 0.11m. Four 4m transition strips return to the inherited heights within a 16m by 28m rectangle. These heights and dimensions are provisional model-space grading, not surveyed terrain.

Only `asphalt 15s road detail`, `gutter 15s road detail`, and `pavement_0 unified road` are cut and lowered in that rectangle. All original vertices remain unchanged. The original XY footprint is retained, and full exterior faces keep their vertex IDs, material indices and smooth flags. Original building, lawn, plaza paving, adopted entrance seam, materials and packed assets are preserved by the review harness fingerprints.

A separate closed object, `OTW Mori west path / seam fill`, adds only 0.0785201241m² of thin infill to inherited calculation gaps in the flat core. Its plan is bounded by the intersection of 1cm buffers of the existing paving and road surfaces, excludes the adopted entrance seam, and uses the existing pavement material. The fixed plan SHA-256 is `6bb6165ee58f9827162256023a7f5b8ebd514b66f05307b8bf01606df0a0127c`.

The infill uses exact integer object origin `(-412,355,0)` and small local float32 vertices. World-coordinate float32 rounding and a 0.04mm road-edge clearance left three inherited boundary probes open in the earlier candidate. Keeping local coordinate precision allows the infill to meet the inherited road edge directly. The adopted entrance seam retains a 0.1mm exclusion margin. Plan overlap with existing surfaces is 0.000000156343m² and overlap with the adopted seam is zero, both below the unchanged validation thresholds. An isolated Blender check of the new infill covers all 90 target probes that previously hit ground.

## Reproduction

Use the [accepted connection lock](../manifests/mori-plaza-connection-accepted.json): 559,040,261 bytes, SHA-256 `9c142f54cc85689cb8a8bc00794dfe8e9b6bc9098f121c9fb02cdbc1aa3dbbc4`. Set `CITY_BLEND` to those exact input bytes, `ROAD_INPUTS` to the pinned production input directory, and `BLENDER` to Blender 4.5.1 LTS. The inherited source files are checked against their recorded hashes. No source scene is overwritten.

Use the existing production Python 3.12 environment with NumPy 2.3.5, Shapely 2.1.2 and GEOS 3.13.1 for plan preparation and detailed validation. Each output directory below must be new. The patch rejects a plan with different bytes and rejects an already applied correction.

```text
PRODUCTION_PYTHON scripts/prepare_mori_plaza_west_path.py --blender BLENDER --input CITY_BLEND --output NEW_PLAN
python scripts/review.py --blender BLENDER --input CITY_BLEND --lock manifests/mori-plaza-connection-accepted.json --features areas/tokyo-tower/mori-plaza-connection-accepted-features.json --cameras areas/tokyo-tower/mori-plaza-west-path-cameras.json --patch patches/mori-plaza-west-path-v1.json --road-inputs ROAD_INPUTS --connection-plan NEW_PLAN/plan.json --output NEW_REVIEW --device OPTIX --width 1280 --height 720 --samples 24 --timeout 1200
PRODUCTION_PYTHON scripts/validate_mori_plaza_west_path.py --blender BLENDER --before NEW_REVIEW/before.blend --after NEW_REVIEW/after.blend --seam-plan NEW_PLAN/plan.json --output NEW_AUDIT
```

The detailed validator reopens both saved scenes in a fresh Blender process. It checks original vertices, complete exterior faces, XY union comparison including all exterior cut fragments, transition height, surface orientation, the closed infill and its pinned plan, the exact infill translation, boundary ray probes, the existing entrance junction and a fixed road grid. For the infill XY audit, the saved local vertices are translated in float64 to retain their stored edge precision. Vertical faces with zero XY projected area are excluded from the XY union. The XY tolerance remains 0.003m² per target mesh and the new vertex height tolerance remains 0.1mm.

The combined transition avoids dividing rounded heights by a tiny inherited transition factor when the point remains unchanged or is already flat. A regression covers the actual float32 boundary case found during saved-scene validation.

The six fixed views include three west-path views and the existing entrance, plaza and protected street context. Before and After use Cycles OPTIX, 1280 by 720 pixels, 24 samples, seed 0, and frame 1. Local scenes, packed assets and full execution directories remain under ignored `data/local/`. The public draft review includes only four selected PNGs and path-free execution/validation metadata. The PNGs preserve all image and colour chunks, while removing automatic text/EXIF metadata that included a local path. Source and public file hashes, plus unchanged IDAT hashes, are recorded in the public evidence manifest.

## Final local validation

The final local output is `data/local/west-path-review-04`, with the read-only saved-scene audit in `data/local/west-path-audit-04` and the fixed infill plan in `data/local/west-path-seam-plan-03`. Both final runs report success. Earlier candidates and failed diagnostic outputs are retained as history.

| Check | Final result |
| --- | --- |
| Target road/paving pairs | 75, with 31 offsets each (2,325 probes) |
| Maximum step at paired offsets | 0.350000381m before; 0.000000357628m after |
| Inherited gap probes that hit ground | 90 before; none unresolved after |
| Existing junction and entrance | All 74 probes preserve the hit object and height |
| Flat road grid | 338 selected probes pass |
| Original target vertices | All 803,980 retained exactly |
| Complete exterior faces | All 444,600 retain indices, material and smooth flags |
| Road XY symmetric difference | Asphalt 0.0000871774m²; gutter 0.0000787847m²; pavement 0.0000399478m² |
| Maximum new vertex height error | 0.000000726951m, below the unchanged 0.0001m limit |
| New inverted walking faces | Zero |
| Infill | Closed and consistently oriented; matches the fixed plan |
| Other object fingerprints | 3,304 unchanged; no removed objects |
| Packed images | All 383 asset fingerprints unchanged |
| Inherited warnings | 36 before and after; no new warning |

All twelve matched images were visually inspected. Raised fragments and curb steps within the target west path flatten into the adopted plaza height. The inherited road material and XY outline remain visible. No obvious new defect was observed in the west path, entrance, plaza or protected street views. Raised inherited surfaces remain beyond the bounded north transition and in other streets.

The final code was checked again for draft PR publication: the 232-test suite passed in portable Python (225 passed / 7 optional skips, 5.489 seconds) and in the pinned production environment (227 passed / 5 optional skips, 4.767 seconds). Five optional photo-estimation tests require image dependencies; portable checks also skip two optional geometry checks. The eight relevant production tests, compileall and Git whitespace checks passed. No dependency was installed. The saved-scene checks and rendered pixels are reused because their input, model code, cameras and render settings are unchanged; the manifest records both actual execution byte hashes and LF-normalized source hashes.

The final `after.blend` SHA-256 is `2a6f63658722beecdb8af2158baed62c044f33a22084df0d227c70c67332ae5b`; the saved-scene audit confirms it was unchanged during validation. Exact code, camera, input and report hashes are recorded in the local run files.

## Review limits

This candidate still needs human visual review and adoption. The checks establish continuity at fixed model-space probes and preserve documented mesh/material/asset fingerprints. They do not certify surveyed elevation, continuous collision, accessibility, all modifier or animation behavior, or every surrounding road. Existing road materials and the outline away from the bounded target remain inherited. The old warning set from the accepted city must not increase.
