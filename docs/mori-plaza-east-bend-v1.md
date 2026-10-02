# 中央広場の園路北東曲がり角：局所接続候補

PR51・PR47を含む固定city候補を起点に、地図上の園路の一箇所で、既存舗装との19cm・35cmの段差と計算上の微小な隙間を修正しました。中心8m四方を既存広場のモデル高0.11mに揃え、外周4mで旧高さへ戻します。[前後8枚の軽量比較画像](../renders/previews/mori-plaza-east-bend-v1/README.md)と[最新mainでの再検証記録](mori-plaza-east-bend-main-validation.json)を、承認されたDraft PR用に公開します。共通city登録と採用・マージは別の判断です。

## 最新mainとの整合

main `68247dad0421f331f4179b9146a7b06273540a01` を起点に、完成済み修正 `d2b2731552db5c8cc8d4f0b209543a51356a7440` の9ファイルだけを取り込みました。PR #47・#51はmainへマージ済みで、既存の園路・並木コードを重複追加していません。今回の入力hashは、mainに記録されたPR #51の保存済み最終候補と一致します。

PR #48〜#54の既存コード・成果物と、タワー・建物の既存データを保全します。新しい建物・もみじ谷・タワーの別候補を全て組み合わせた都市モデルの制作は今回に含みません。コードの最新main整合と、固定PR #47/#51都市上での園路修正の検証を区別します。

補修planを最新コードで再生成し、元のplan hashと一致することを確認しました。新しいローカル出力へ都市を再生成し、保存後再読込、許可変更範囲、道路境界、重複適用拒否、4視点の同条件描画、軽量review blendの再読込が成功しました。Before/Afterの全検査snapshotと幾何監査結果は引継ぎ成果に一致し、最大段差0.350000262m→0.000000477m、地面露出48測点→0を再確認しました。

最新の全315テストは標準環境307成功・任意依存8スキップ、制作環境310成功・写真推定依存5スキップです。構文検査も成功しました。公開PNGは4視点×前後の8枚、各640×360、合計1,980,647 bytesです。8枚を目視確認し、局所段差の解消と周辺の保持を確認しました。実行コード・入力・画像hashは上記JSONに記録しています。

今回のローカル出力は専用worktreeの `data/local/east-bend-main-plan/`、`east-bend-main-review/`、`east-bend-main-audit/` です。新しい全都市候補のSHA-256は `994c2007fa97b09b7ff8db6c41c249687337f25d169d48851e2a3fdcd99ccab7`。blendは再保存によりbyte hashが変わりますが、記録対象の形状・材質・設定等の検査snapshotは元成果と一致しました。以下は元の制作範囲と引継ぎ時の測定結果です。

## 対象と根拠

固定OSM `work/osm.xml` のway `1443867478`（version 3、2026-03-07T08:44:14Z、`highway=footway / surface=paving_stones`）が対象です。道路制作seedに旧生成式の幅4.1mと2mを照合し、各15面のXY・高さが一致しました。選択矩形にはこのwayの線分5〜8が約17.47m含まれます。実測の道路高・勾配を示す資料ではありません。

東側外周の候補には車道沿いの段差が含まれ、平坦にすべき歩行接続とは確認できなかったため選択していません。今回の対象はその内側の、歩道として記録された北東曲がり角です。

| 項目 | 固定値 |
| --- | --- |
| 起点コード | `102ad0a41a84b5336795bb8d5b2aeb5e8c81eb39` |
| 起点city SHA-256 | `966a81151beaf851a796bae8f91cad4d4106e82a40ccc69bad92aec48f1f6d9b` |
| 中心・外縁 | 入口ローカルUV `(-8,85)`、外縁 `U=-16..0, V=77..93` |
| 修正対象 | `asphalt 15s road detail`、`gutter 15s road detail`、`pavement_0 unified road` |
| 追加 | `OTW Mori east bend / seam fill`、閉じた薄い隙間補修1部品 |
| 補修面積 | 0.0426814174m²。既存舗装と道路の両方から1cm以内の隙間のみ |
| plan SHA-256 | `a5ad01479cf411183cfa019e945a06efc9999dd11d0f2f9f69c242bafd3397ee` |
| 完成候補 SHA-256 | `ead21b18a8f4c9f7b74cbc2acdeefadab1fef8d9f1ac2c9f9a79ba9ec3e6398c` |

旧道路の119面を切り分けて局所的に下げ、平坦部で高さがなくなる縁石側面の13断片を除去します。道路の元頂点804,478個は保持し、切断に499頂点を追加します。材質・XY輪郭を引き継ぎ、追加補修には既存pavement材質を使用します。地形・芝生・広場本体・建物・東京タワー・PR51植栽は変更しません。

PR47の西側修正外縁はV=75までで、今回の外縁はV=77からです。世界XYの外接範囲はX=-399.6754〜-378.2091m、Y=359.6909〜381.1571mで、別担当の建物候補の外接範囲およびPR51樹冠範囲と重なりません。新しいコードだけを追加し、西側パッチ・既存validator・共有runnerのコードは変更していません。

## 保存後の検証

Blender 4.5.1 LTSで完全なcityを別ファイルに保存し、別プロセスで再読込しました。さらに独立の保存形状検査でBefore/Afterを読み、道路配列と各4,199本のrayを取得しました。

| 検査 | 結果 |
| --- | --- |
| 対象の接続境界 | 45組、各31点・2mm間隔、計1,395点 |
| 最大段差 | 0.350000262m → 0.000000477m |
| 接続部でgroundが露出する測点 | 48 → 0 |
| 未解決の境界測点 | 0 |
| 元頂点 | 804,478個すべて一致 |
| 完全に外側の面 | 444,655面の頂点index・材質番号・smoothを保持 |
| XY面積対称差 | asphalt 0.0000783694m²、gutter 0.0000151871m²、pavement 0 |
| 新頂点の最大高さ誤差 | 0.000000881m、許容0.0001m以内 |
| 新規の下向き歩行面 | 0 |
| 補修形状 | 閉形状・向き・固定planとの一致に成功 |
| PR47・入口等の保護測点 | 567点でobject・高さを保持 |
| 中心平坦部の道路格子 | 134点で0.11mを確認 |
| 対象外object | 3,323件の記録した指紋が一致 |
| 資産・設定 | 383資産、既存18collection（補修の所属追加以外）、scene設定と既存属性、埋込Text3件を保持 |
| 警告 | 既存36件のまま、増加なし |
| 関連テスト | 固定production環境で57件成功（今回の6件を含む） |
| portableテスト | 264件中256件成功、任意依存8件省略、失敗なし |

## 前後画像とローカル成果物

4視点（周囲、歩行目線、境界近接、反対側）をCycles OptiX、960×540、16 samples、seed 0、frame 1、同一カメラ・照明・色管理で比較し、全8枚を目視確認しました。対象の段差と浮いた舗装片が平坦部に接続し、対象外には既存の段差と不規則な輪郭が残ります。

描画対象は中心からXY各95mの近隣抽出です。大きな集約meshは範囲に交差する面だけを保持し、範囲外objectを除外しています。これは全都市描画ではなく、遠方の景観・遮蔽の審査ではありません。完全なcity候補は抽出とは別に保持しています。

- `data/local/east-bend-review-02/after.blend`：完全なcity候補。
- `data/local/east-bend-review-02/before-neighborhood.blend` と `after-neighborhood.blend`：軽量な近隣比較用。
- `data/local/east-bend-review-02/before-review.blend` と `after-review.blend`：対象箇所のカメラで開く閲覧用コピー（各約18MB）。別プロセスの再読込で形状・材質・画像の指紋とカメラを照合済み。
- `data/local/east-bend-review-02/review.html`：4組の画像比較と検証要約。
- `data/local/east-bend-review-02/run.json`：コード・入力hash、各処理時間、保全結果。
- `data/local/east-bend-audit-01/run.json`：保存後の道路・隙間・高さ検査。
- `data/local/east-bend-plan-01/`：固定補修planと入力面。
- `data/local/east-bend-selection.json`：固定OSMと過去の境界監査による選択根拠。

既存の入力モデル・旧担当の成果は上書きしていません。最初の実行はハッシュ関数の参照漏れで編集前に停止し、失敗ログを`east-bend-review-01`に保持しています。実行環境の切断復旧後に修正して完成しました。

## 再現

これは新しい専用runnerです。共有`review.py`への新operation登録は行っていません。`CITY`は上記の固定起点、`ROAD_INPUTS`は固定OSMと`work/twin_towers/tower_surfaces.json`を含む正規のローカル入力、`PRODUCTION_PYTHON`は既存のPython 3.12 / NumPy 2.3.5 / Shapely 2.1.2 / GEOS 3.13.1環境、`BLENDER`は4.5.1 LTSを指定します。

```text
PRODUCTION_PYTHON scripts/prepare_mori_plaza_east_bend.py --blender BLENDER --input CITY --output NEW_PLAN
PYTHON scripts/mori_east_bend.py --input CITY --blender BLENDER --output NEW_REVIEW --plan NEW_PLAN/plan.json --road-inputs ROAD_INPUTS --phase build-check
PRODUCTION_PYTHON scripts/validate_mori_plaza_east_bend.py --blender BLENDER --before CITY --after NEW_REVIEW/after.blend --seam-plan NEW_PLAN/plan.json --output NEW_AUDIT
PYTHON scripts/mori_east_bend.py --input CITY --blender BLENDER --output NEW_REVIEW --plan NEW_PLAN/plan.json --road-inputs ROAD_INPUTS --phase render
PYTHON scripts/mori_east_bend.py --input CITY --blender BLENDER --output NEW_REVIEW --plan NEW_PLAN/plan.json --road-inputs ROAD_INPUTS --phase duplicate
PYTHON scripts/mori_east_bend_review_copy.py --blender BLENDER --output NEW_REVIEW
```

出力先はこのworktreeの`data/local/`内で新規に指定します。入力・道路mesh・planのhash違いと二重適用は拒否します。保存済み候補への二重適用は保存せず拒否され、候補hashの不変を確認しました。`--device CPU`を明示した再現も可能ですが、今回の画像比較はOptiXです。

## 制限

現地の標高・階段・スロープの実測復元ではありません。固定モデル内の限定した接続を改善した候補であり、連続衝突・バリアフリー適合・全modifier/animation・周辺全道路の完成を保証しません。材質とXY輪郭は旧表現を残しています。人間の採否判断と、他担当の後続差分を含む共通cityへの統合は別作業です。都市・既存画像・OSMに新たな公開許諾は付与していません。
