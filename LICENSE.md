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

## Outside these grants

Except for the separately identified starters and original additions above, no license is granted here for other repository files, legacy city scenes, generated models, reference photos, textures, music, trademarks, PLATEAU data, OpenStreetMap data, or other third-party content. Any separately applicable license remains in effect. Execution of the covered code does not itself grant rights to its inputs or outputs. This scope document adds no conditions to the MIT grant for the covered code.

広場6部品、森JPタワーの独自追加部分等、および東京タワーの指定独自部分等にCC BY 4.0を適用します。全都市モデルや他のコード・文書が一括してMIT／CC BYになったとは扱わないでください。

See [NOTICE](NOTICE.md) for provenance and operational dependencies. Attribution required by a third-party license must be retained when that data is used; those requirements are not additional restrictions on the independent MIT code.
