# License scope / ライセンス適用範囲

This repository has a partial, file-specific license grant. It is not licensed as a whole under MIT.

## MIT: four independent Python implementations

The independent code in the following four files, as present in baseline commit `b7462dceb907ed38d07fa600e39c23527d5e2c2d`, is licensed under the [MIT License](MIT-LICENSE.txt), copyright (c) 2026 ark4ez. The hashes identify that snapshot; they do not restrict modification or redistribution permitted by MIT. Retain the copyright and license notice when redistributing the covered code.

| File | SHA-256 (UTF-8 bytes, CRLF normalized to LF) |
|---|---|
| `scripts/mori_plaza_v1.py` | `b16a1179b14f9e56b615d818c06da11c7be77959c199e2d93c6ee4544076fc2c` |
| `scripts/mori_plaza_link_v1.py` | `c5e15978e47a7e4816001b175ead98d7445bf37828f48945f15915db639f4d37` |
| `scripts/mori_entrance_v1.py` | `f9ab6f5aa0ad9a1cd201c8b021e9893a411e9556afbc7bb877f558e6faa2fede` |
| `scripts/mori_terrace_v1.py` | `2056674560bbcd92503db2a5e8491eca0f2f21ab782ba9d332820b70a74d1a9d` |

対象は上記4ファイルの独自実装です。この版の利用・改変・再配布・商用利用をMITの条件で許諾します。ハッシュは対象版の特定用であり、改変禁止や追加制限ではありません。後続寄稿者の権利をこの表示で勝手に許諾しません。

## MIT: starter runner

The original `starter/plaza/package.py` and `tests/test_plaza_package.py` are also covered by MIT, copyright (c) 2026 ark4ez. These grants cover these named implementations, not unrelated repository files.

The original code in `starter/plaza/run.py` and `starter/plaza/scene.py`, marked with SPDX-License-Identifier: MIT and copyright (c) 2026 ark4ez, is also licensed under [MIT](MIT-LICENSE.txt). This does not extend the four-file snapshot grant above to unrelated later modifications.

## CC BY 4.0: six-part starter

The original six procedural parts, their materials, starter camera/lighting, previews, and documentation/metadata in `starter/plaza/` have the separate grant in [starter/plaza/ASSET-LICENSE.md](starter/plaza/ASSET-LICENSE.md). Preserve its source notices. Python code remains MIT.

## MIT: pinned PLATEAU import trial

The original implementations in `starter/plateau/run.py`, `starter/plateau/tile.py`, `starter/plateau/scene.py`, and `tests/test_plateau_tile.py` are licensed under the [MIT License](MIT-LICENSE.txt), copyright (c) 2026 ark4ez. This grant does not cover PLATEAU data, imagery, Blender or its installed Draco library. Keep the input-specific notices in `starter/plateau/NOTICE.md`; generated combined scenes do not receive a blanket MIT grant.

## MIT: standalone Mori generation and adapters

The independent implementations in the eleven files below, at commit `e349a7dafd788224f9b7b203e71f170fc19637ed`, are licensed under [MIT](MIT-LICENSE.txt), copyright (c) 2026 ark4ez. This includes licensor-controlled legacy-derived code incorporated into these files, not unrelated legacy files. The licensor confirmed authority and consent on 2026-09-07; see [provenance](starter/mori/provenance.json). Hashes identify the snapshot (CRLF normalized to LF) and do not restrict modification or redistribution under MIT. The original license-bundling updates to `starter/mori/run.py` and `tests/test_mori_standalone.py` in this change are also MIT.

| File | SHA-256 (LF) |
|---|---|
| `starter/mori/facade.py` | `e0422fc6998ad3791ecf3122ccd3e509a540559e791cd415b7578a8cf054f4f4` |
| `starter/mori/profile.py` | `78767146deaa0dd7280eda01dfe3da09e69bcc6cce6e4bde812a14c5da220a9b` |
| `starter/mori/run.py` | `9b5fe2d029e8debe02e950a73def5b3ba3ce6a4be86ab2cf22ce5c9765bc27c8` |
| `starter/mori/scene.py` | `171b9658e2cc5028953b871b793209da83ee47e40a9b92998c937d819a9bf92e` |
| `scripts/mori_shape.py` | `5588ac6e1409944faf1d686baffa7230b7a95a0b939c21502686b0a96d80df5a` |
| `scripts/mori_crown_v2.py` | `8bb386b4429575c4c37b914c71b63629fb844c84c0399e943706b34fd10e64a7` |
| `scripts/mori_crown_material.py` | `25d8ae26b7c5b2ba38f6db5fd5baa507f18c3965a83a3e09996d71fceb2d1959` |
| `scripts/mori_facade_v2.py` | `5df83c9acf790bbfc1491f133445221174644663e2c041ec860a2900a81e7b9e` |
| `scripts/mori_podium_v3.py` | `b202252d78763d965213c30a8c85260b0ce550e32128a7dbef05107d9e639dfb` |
| `tests/test_mori_standalone.py` | `2c6992a1b2555083ae61811b441d73b0adc9690a4ac5d80863ac567d1485e9b1` |
| `tests/mori_standalone_blender.py` | `b080f2f5ef20fd8ad65e8b7ca76e9bc33fc3cb254cebb26f2ad4bcad680ac6cc` |

## CC BY 4.0: original Mori additions

The original contributions within thirteen detailed Mori parts, their original materials, standalone camera/lighting, and original documentation/metadata in `starter/mori/` have the grant in [ASSET-LICENSE.md](starter/mori/ASSET-LICENSE.md). Underlying PLATEAU-derived geometry and other third-party components retain their source terms. This is not a blanket license for the combined scene.

## Tokyo Tower: MIT code and CC BY 4.0 original assets

The nine historical code snapshots listed with SHA-256 and source ranges in [Tokyo Tower provenance](assets/tokyo-tower/provenance.json), plus the original `assets/tokyo-tower/export.py` and `tests/test_tower_license.py`, are licensed under [MIT](MIT-LICENSE.txt), copyright (c) 2026 ark4ez. Source ranges cover only the archived text, not unrelated portions of the legacy files. The account holder explicitly confirmed authorship, authority and the same MIT/CC BY policy on 2026-09-07. Snapshot hashes identify the grant and do not restrict modifications allowed by MIT.

The 77 original Tokyo Tower parts and their original materials, plus the new isolated review setup and previews, have the [CC BY 4.0 grant](assets/tokyo-tower/ASSET-LICENSE.md). Third-party rights and the rest of the legacy city remain outside that grant.

## Generic object registry

The original `scripts/object_registry.py`, `tests/test_object_registry.py`, `registry/example.json`, and `registry/example.lock.json` are licensed under [MIT](MIT-LICENSE.txt), copyright (c) 2026 ark4ez. The registry example is synthetic contract data, not a real city model or a grant for third-party inputs.

## MIT: contributor workspace

The original implementations in `scripts/workspace.py`, `scripts/workspace_blender.py`, `otw.ps1`, and `tests/test_workspace.py` are licensed under the [MIT License](MIT-LICENSE.txt), copyright (c) 2026 ark4ez. This grant covers these named workspace implementations; it does not grant new rights to the city scenes or other inputs they handle.

The original implementations in `scripts/verify_city_images.py`, `scripts/check_city_image_pixels.py`, and `tests/test_city_images.py` are also licensed under [MIT](MIT-LICENSE.txt), copyright (c) 2026 ark4ez. This grant covers the named image verification code, not the third-party images or city scenes being checked.

The original implementations in `scripts/city_facades.py`, `scripts/review_city_facades.py`, `scripts/audit_city_geometry.py`, and `tests/test_city_facades.py` are also licensed under [MIT](MIT-LICENSE.txt), copyright (c) 2026 ark4ez. This grant covers the named procedural material, comparison and inventory code. It does not grant new rights to legacy geometry, remaining textures or the combined city scene.

The original implementations in `scripts/city_catalog.py`, `scripts/city_catalog_blender.py`, `scripts/city_catalog_template.html`, and `tests/test_city_catalog.py` are licensed under [MIT](MIT-LICENSE.txt), copyright (c) 2026 ark4ez. This grant covers the named catalogue code and interface, not the legacy scenes, images or third-party content shown by it.

The original implementations in `scripts/fetch_legacy_production.py`, `scripts/audit_city_production.py`, `scripts/verify_tree_prototypes.py`, and `tests/test_legacy_production.py` are licensed under [MIT](MIT-LICENSE.txt), copyright (c) 2026 ark4ez. This covers the new inspection utilities, not the historical source files they retrieve, embedded scene text, or the city assets.

The original implementations in `scripts/import_legacy_inputs.py`, `scripts/replay_production_inputs.py`, `scripts/verify_city_tree_placements.py`, and `tests/test_production_inputs.py` are licensed under [MIT](MIT-LICENSE.txt), copyright (c) 2026 ark4ez. This covers the new import, replay and verification utilities. It does not grant new rights to the historical scripts, recovered map/layout data, intermediate scenes, or third-party Python packages.

The original implementations in `scripts/component_contracts.py`, `scripts/verify_city_components.py`, `scripts/prepare_procedural_candidate.py`, `tests/test_city_components.py`, and `tests/components_blender.py` are licensed under [MIT](MIT-LICENSE.txt), copyright (c) 2026 ark4ez. This covers the new comparison and local candidate preparation utilities, not historical source fragments executed from separately supplied files. The extracted assets have the separate grant below.

The original `scripts/package_procedural_components.py` and `tests/test_procedural_package.py` are also licensed under [MIT](MIT-LICENSE.txt), copyright (c) 2026 ark4ez. This covers the new license-annotation, verification and packaging implementations; it does not relicense Blender or historical source code.

The original `scripts/district_distribution.py` and `tests/test_district_distribution.py` are also licensed under [MIT](MIT-LICENSE.txt), copyright (c) 2026 ark4ez. This covers district selection, content verification, local caching and workspace integration, not the models, source datasets or third-party content they retrieve.

The original `tests/contributor_smoke.py` and `tests/contributor_edit_blender.py` are also licensed under [MIT](MIT-LICENSE.txt), copyright (c) 2026 ark4ez. This covers the isolated onboarding and disposable edit verification code, not the downloaded Blender binaries, source datasets or generated scenes.

## MIT: plaza outline correction and verification

The original implementations in `scripts/mori_plaza_outline_v1.py`, `scripts/validate_mori_plaza_outline.py`, and `tests/test_mori_plaza_outline.py` are licensed under [MIT](MIT-LICENSE.txt), copyright (c) 2026 ark4ez. This covers the named correction and verification code, not the saved OSM data, legacy road seeds, city scenes, images or other third-party inputs.

## MIT: plaza landscape correction and verification

The original implementations in `scripts/mori_plaza_landscape_v1.py`, `scripts/prepare_mori_plaza_landscape.py`, `scripts/validate_mori_plaza_landscape.py`, and `tests/test_mori_plaza_landscape.py` are licensed under [MIT](MIT-LICENSE.txt), copyright (c) 2026 ark4ez. This covers the named landscape preparation, correction and verification code, not the saved OSM footprints, local geometry plans, legacy city scenes, images or other third-party inputs.

## CC BY 4.0: tree/shrub prototypes and procedural materials

On 2026-09-27 the account holder approved CC BY 4.0 for the 16 prototype meshes and 31 procedural materials identified in [provenance](assets/procedural-components/provenance.json), together with their dedicated preview setup and image, to the extent the licensor controls those rights. See the [asset grant](assets/procedural-components/ASSET-LICENSE.md). The original city placement, mapped aggregate meshes, third-party inputs and historical code remain outside this grant.

## Local plaza connection correction

The original implementations in `scripts/mori_plaza_connection_v1.py`, `scripts/prepare_mori_plaza_connection.py`, `scripts/validate_mori_plaza_connection.py`, and `tests/test_mori_plaza_connection.py` are licensed under [MIT](MIT-LICENSE.txt), copyright (c) 2026 ark4ez. This covers the named correction and verification code, not the legacy scene, saved OSM, local geometry plans, images or other third-party inputs.

## Local west footway correction

The original implementations in `scripts/mori_plaza_west_path_v1.py`, `scripts/prepare_mori_plaza_west_path.py`, `scripts/validate_mori_plaza_west_path.py`, and `tests/test_mori_plaza_west_path.py` are licensed under [MIT](MIT-LICENSE.txt), copyright (c) 2026 ark4ez. This covers the named original correction and verification code. Legacy city scenes, saved OSM data, recovered road seeds, local geometry plans, textures and other third-party inputs retain their existing terms.

The four selected Before/After PNGs in [the west footway review preview](renders/previews/mori-plaza-west-path-v1/README.md) were explicitly approved for publication with the draft PR on 2026-10-02. Their publication as review evidence adds no asset license for the underlying legacy scene or third-party content. Preserve the source notices in that preview and [NOTICE](NOTICE.md).

## Tokyo Tower exterior structure correction

The original implementations in `scripts/tower_structure_v1.py`, `scripts/tower_foottown_v1.py`, `scripts/tower_upper_lift_v2.py`, `scripts/tower_lift_car_v2.py`, `scripts/validate_tower_structure.py`, `tests/test_tower_structure_geometry.py`, `tests/test_tower_structure_review.py`, `tests/test_tower_lift_car_v2.py`, and `tests/test_tower_foottown.py`, together with the original `tower_structure_v1` integration additions to `scripts/review.py` and `scripts/blender_worker.py`, are licensed under [MIT](MIT-LICENSE.txt), copyright (c) 2026 ark4ez. This covers the named original correction and verification code, not the legacy city, reference photographs/PDFs, textures, generated combined scenes or third-party inputs.

The original implementations in `scripts/tower_site_v3.py`, `scripts/tower_site_geometry_v3.py`, `scripts/validate_tower_site_v3.py`, and `tests/test_tower_site_v3.py` are also licensed under [MIT](MIT-LICENSE.txt), copyright (c) 2026 ark4ez. This grant does not include city scenes, reference images or geographic datasets. OSM-derived centroid data in `areas/tokyo-tower/tower-site-v3-sources.json` is attributed to OpenStreetMap contributors under ODbL 1.0.

The 18 Before/After PNGs in the [tower structure review](renders/previews/tower-structure-v1/README.md) are published as evidence for the user-requested PR. Their publication does not grant a new blanket licence for the images, underlying city or third-party content. Retain the attribution and scope recorded in that preview and [NOTICE](NOTICE.md).

The 30 PNGs in the [upper lift revision review](renders/previews/tower-lift-v2/README.md) follow the same publication scope. They include 26 pinned-input Before/After views and four views of the previous proposal for comparison with the revised upper lift. Reference photographs and PDFs are not redistributed.

## Outside these grants

Except for the separately identified starters and original additions above, no license is granted here for other repository files, legacy city scenes, generated models, reference photos, textures, music, trademarks, PLATEAU data, OpenStreetMap data, or other third-party content. Any separately applicable license remains in effect. Execution of the covered code does not itself grant rights to its inputs or outputs. This scope document adds no conditions to the MIT grant for the covered code.

広場6部品、森JPタワーの独自追加部分等、東京タワーの指定独自部分等、および植栽の指定16部品・31材質等にCC BY 4.0を適用します。全都市モデルや他のコード・文書が一括してMIT／CC BYになったとは扱わないでください。

See [NOTICE](NOTICE.md) for provenance and operational dependencies. Attribution required by a third-party license must be retained when that data is used; those requirements are not additional restrictions on the independent MIT code.
