# Tokyo Tower top-deck window-base closure

This is the historical isolated-model record. See the [city integration record](tokyo-tower-city-repairs-v1.md) for the current PR47/49/51 city validation and publication.

The saved top-deck window posts and gaskets floated approximately 30 mm above
the existing floor; glass started approximately 57.5 mm above it. A close view
confirmed the floating post ends. This change extends only the existing lower
ends to the unchanged floor surface. It preserves the completed paint repair.

## Evidence and scope

The retained `glasswall` generator shortens glass panels by 55 mm, while its
top-deck call starts at z246.25 and the floor finishes at z246.22. The separate
saved coordinates agree with those gaps. Input coordinates are baked world
coordinates, with identity transforms and no modifiers or shape keys on the
affected objects. The old task's 75-part inspection was reused before the
focused close-view inspection; intentional leaf and mirror surfaces were not
treated as defects.

The [official Top Deck Tour page](https://tdt.tokyotower.co.jp/en/topdecktour/)
contains an [interior photograph](https://tdt.tokyotower.co.jp/assets/images/slider_pc.jpg)
showing a continuous metal window base closing toward the floor. It supports a
closed junction, but does not establish dimensions, exact profiles or direct
glass-to-floor contact. This is a simplified closure using existing parts,
not a surveyed reconstruction of the real sill assembly. No reference image
is distributed or used as a texture.

| Existing part | Lower vertices translated | Downward translation |
|---|---:|---:|
| 009, aluminum posts | 1,120 | 29.998779 mm |
| 010, glass | 160 | 57.495117 mm |
| 011, gaskets | 160 | 29.998779 mm |

The post's entire lower bevel, including the vertices up to approximately
6 mm above its bottom, moves together. This preserves its existing profile.
All XY coordinates, upper endpoints, mesh topology, attributes, material slots
and definitions, transforms, names and persistent IDs are preserved. The
remaining 74 meshes, camera, light and World are unchanged, including paint
parts005/006 and floor012. No objects or materials are added.

The separate approximately 300 mm gap between the floor and lower white shell,
upper glazing clearance, circular plan and other inherited approximations are
outside this repair. No full-city scene, common registry, tree, adjacent
building, street, main-deck window trial or viewer was changed.

## Inputs and local outputs

The branch starts at local city-paint commit
`9f1aa67028356851afefae5c565329b9a9d451b3`. The model input is the completed
isolated paint candidate from commit `568a9e76106b2354c94616e6c62d6c8b9ac3ac38`:
27,742,051 bytes, SHA-256
`361f45888ca17db9cee112bf76a55d21f2e9820f4d385f575101ffc152400f5f`.
The original fixed-ID export and previous body/tree compatibility result
remain untouched. Their locations are recorded in the ignored handoff.

The [pinned plan](../assets/tokyo-tower/topdeck-junction-v1.json) records inputs,
scope and source limitations. Final local outputs are in
`data/local/topdeck-junction-02/`: `after.blend`, `review.html`, six PNGs,
`build.json`, `validation.json`, and `comparison.json`. The earlier `01` run
retains its noisier 16-sample comparison and exact build script; its geometry
repair is the same. The final run uses 32 samples and denoising for readability.

## Verification

- Blender 4.5.1 LTS, Windows; final candidate reopened in a separate process.
- All 77 part IDs retained. All 74 non-target meshes and camera/light records
  match the original. All material definitions and World match.
- For each target, saved XY and upper-end coordinates match exactly. Lower
  profiles undergo only the recorded Z translation and finish at the existing
  floor top. Restoring just coordinates on an in-memory copy reproduces the
  complete original mesh fingerprint, including topology, attributes and
  shading. The saved candidate is never modified by this check.
- All 120 member components pass a radial ray at 15 mm above the floor after
  reopening; all 120 missed in the input. These probes complement the endpoint
  check and close image; they do not certify full contact area, airtightness
  or every possible intersection.
- 248 portable tests: 241 passed, 7 existing optional skips. Six additional
  Blender validator checks pass, including rejection of an upper-end move,
  horizontal move, remaining gap, distorted lower profile and material change.
- Sill close view, complete top deck and complete tower use matched camera,
  light, World, color transform, seed and renderer settings. Cycles CPU,
  2 threads, 32 samples, seed 0, denoising on, adaptive sampling off; close and
  deck views 800x600, full tower 640x800. Both sides are visually checked.

[Verification summary](tokyo-tower-topdeck-junction-v1-verification.json)
records result hashes and comparisons. No push, PR, merge or shared-city
adoption is part of this change.

## Reproduce

Use a fresh output directory and the exact pinned input. Each phase protects
the input hash and exits nonzero on failure. All Blender work runs sequentially.

```powershell
$blenderPath = 'C:/Program Files/Blender Foundation/Blender 4.5/blender.exe'
$towerInput = 'RECEIVED_ISOLATED_PAINT_CANDIDATE.blend'
$towerOutput = 'data/local/topdeck-junction-new'
foreach ($phase in @('build','validate','render-before','render-after','compare')) {
  & $blenderPath --background --factory-startup --threads 2 --disable-autoexec --python-exit-code 1 --python scripts/tokyo_tower_topdeck_junction.py -- --phase $phase --input $towerInput --output $towerOutput
  if ($LASTEXITCODE -ne 0) { throw "Top-deck phase failed: $phase" }
}
python -m unittest discover -s tests
& $blenderPath --background --factory-startup --threads 2 --disable-autoexec --python-exit-code 1 --python tests/blender_topdeck_junction_smoke.py
```

Original model: ark4ez / OurJapan, CC BY 4.0. Changes: existing top-deck window
bases extended to the existing floor, while retaining the prior paint repair.
The repository's asset license and notice continue to apply.
