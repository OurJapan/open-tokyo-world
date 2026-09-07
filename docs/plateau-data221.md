# PLATEAU data221：地物・依存・座標の確定

確認日：2026-09-07。PR #22採用後の `805178260506f0951540d7cae1d13e86ea1cd2ee` を起点に、選定した1タイルを実解析した。結果は [解析台帳](plateau-data221.json)。公開Areaの完成、測量精度、取込CLIの完成を意味しない。

## 取得するファイル

| ファイル | 容量 | SHA-256 |
|---|---:|---|
| 建築物LOD3配信の `tileset.json` | 412,889 bytes | `edec4c24d137eaf08a8525cecea505a3f21a30823b9ef4fb530e10774cea1323` |
| `data/data221.b3dm` | 1,246,040 bytes | `dc8c7539b2bb22d8c6659689c37aafa53b4896650bbd6bcfe7f791ab8b1a38d2` |

合計1,658,929 bytes。公式配信から取得してハッシュを記録した。このタイルを直接取り込むための階層情報は同じtileset内にあり、rootからchildrenのインデックス `[1,2,0,3,0]` をたどる。経路上の全tileにtransform指定はなく、恒等変換。祖先タイルの形状を重ねて取り込む必要はない。GLBのbuffer・画像は埋め込みで、外部URIは0件。

この確認はdata221単体の依存に限る。隣接タイルや地形を含む一区画全体の入力一覧ではない。

## 地物と表示範囲

Batch Tableは24地物で、全てにgml_idがある。圧縮解除後は4,804三角形で、全三角形の3頂点が同じbatch IDに属することを確認した。森JPの位置根拠として追跡していたbatch 5は `bldg_433bc5b3-db73-4644-ac24-a28d51b7ecd5`。名前属性はnullであるため、地物IDと位置・既存の対応記録で識別する。

配信名はLOD3だがbatch 5の `_lod` は2、DataQualityの記録はLOD2.2。タイルのフォルダー名から全地物のLODを決めない。IDは今回のデータ版内で固定し、別年度でも同じIDとは仮定しない。

タイル全体の経緯度範囲は西139.7385525966°・南35.6602599757°・東139.7412412028°・北35.6629107561°。これはbounding regionで、一区画の採用境界や全てが建物で覆われる範囲ではない。

## 変換順序と検証

このファイルではglTFノードに変換がなく、座標は相対値。glTFの `(x,y,z)` をZ-upの `(x,-z,y)` に変換し、`CESIUM_RTC.center` のECEF座標 `(-3959174.752745184, 3352851.2838770067, 3697827.9120842386)` を加える。Feature Tableの `RTC_CENTER` は存在せず、両方の平行移動を足す処理はしない。

根拠は [3D Tilesの座標変換](https://github.com/CesiumGS/3d-tiles/blob/main/specification/README.adoc#core-gltf-transforms)、[b3dmの地物と座標](https://github.com/CesiumGS/3d-tiles/blob/main/specification/TileFormats/Batched3DModel/README.adoc)、[CESIUM_RTCの説明](https://github.com/KhronosGroup/glTF/blob/main/extensions/1.0/Vendor/CESIUM_RTC/README.md)。CESIUM_RTCは古いglTF向けの拡張であり、今回のglTF 2.0入力で実測照合した変換を他の全タイルへ無条件に適用しない。

Draco圧縮をBlender 4.5.1同梱ライブラリで解除した。必要拡張は `KHR_draco_mesh_compression`、`EXT_texture_webp`、`CESIUM_RTC`。形状・IDの復号は確認済みだが、WebP材質のBlender表示試験は次工程に残る。復号した全頂点をWGS84経緯度・楕円体高に変換し、公式tilesetの6境界値と照合した。経緯度の最大差は1e-9度未満、高さは0.00001m未満。

旧シーンへの対応には、経度139.74543°・緯度35.65858°・楕円体高0mを原点とするENU（東・北・上）の局所座標を使用する。原点高0mは計算上の基準で、現地の地面標高ではない。

1. WGS84のa=6378137m、e²=0.0066943799901413165で原点ECEFを計算。
2. 頂点ECEFから原点ECEFを引き、原点の東・北・上の単位ベクトルとの内積を取る。
3. **旧表示との互換モードに限り**、地物ごとの最小ENU zを引いて0.32mを加える。元の高さと移動量は別に保持する。

batch 5を除いた23地物をこの式で変換すると、旧シーンの `PLATEAU_data221` と三角形数3,160・頂点数9,480が一致した。頂点集合の双方向最近傍距離の最大値は約0.0000331m。これは生成時の座標変換との一致であり、面の接続や材質の完全一致、現実の測量精度を保証する値ではない。既存シーンの採用ハッシュは前段の入力選定と同じ。読み取りのみで保存していない。

24地物を丸ごと既存シーンへ追加すると、置換済みの森JP候補を重複させる。既存詳細モデルとの組立時は地物IDでbatch 5を置換対象とし、batch番号だけを別年度へ持ち越さない。旧モデルなしの取込試験では24地物を保持し、公式形状であることを明記する。

## 高さの注意点と次の実装

Batch Tableの `_zmin/_zmax` と、復号頂点から計算した楕円体高には約36.62～36.64mの差がある。元属性の標高系や変換由来の独立確認前に、この差を一律の補正定数として適用しない。旧シーンではさらに各地物を平坦化している。街の互換表示と地理的な標高を分けて保持する。

次はこの2ファイルを対象とする取得・ハッシュ検査・地物ID付き取込・保存後検証を実装する。公開スターターの広場との組立では、旧表示の互換座標を明示し、元の地理座標もsidecarに残す。旧blendやキャッシュなしの取得試験、WebP表示、広場との接続の画像レビューが完了してからArea候補とする。今回、都市データの新しいReleaseや有料ストレージは作成していない。

## 出典

出典：[3D都市モデル（Project PLATEAU）港区（2025年度）](https://www.geospatial.jp/ckan/dataset/plateau-13103-minato-ku-2025)を解析・加工して作成（OurJapan）。[個別配布リソース](https://www.geospatial.jp/ckan/dataset/plateau-13103-minato-ku-2025/resource/08755b94-7b2e-4c9c-bf35-6c4d0768a463)と[利用条件](https://www.mlit.go.jp/plateau/site-policy/)は前段の2026-09-07確認を引き継ぐ。データ年度と観測日は同一視しない。台帳には識別子・境界・検査結果を記録し、写真・画像ファイル・タイル本体はGitに同梱しない。
