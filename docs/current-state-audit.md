# 既存プロジェクト調査

調査日：2026-09-07。原本は変更していません。

## 対象と確認方法

ローカル起点：既存東京タワーリポジトリの制作環境のチェックアウト。
Git remote：`https://github.com/DoiTakayoshi/tokyo-tower-blender.git`。
HEAD：`defac576e076f40bf3bc4fddcdcefe30f9a009f7`。調査時のGit作業ツリーはclean。対象内に追加AGENTS.mdは見つかりませんでした。

ファイルとコードを読み、完成blendをBlender 4.5.1 LTSのbackground・autoexec無効で開き、保存せず棚卸ししました。[実行結果](evidence/scene-inspection.json)を添付しています。コード中の「検証」という名前だけを信用して実行していません。

## 現在の構成

| 場所 | 現状 |
|---|---|
| README.md | 開き方、再レンダリング、52秒のカット構成、推定表現・権利上の制約 |
| scripts/render.py, encode.py | 完成シーンのCyclesレンダリング、連番＋BGMの動画化 |
| assets/ | 60秒BGM WAV |
| outputs/Tokyo_Final_52s_Corrected/ | 完成シーン・MP4・比較画像・カメラ検証結果 |
| work/ | 多数の段階別生成・修正・取得スクリプト、ローカルキャッシュ |
| .gitattributes | blend/mp4/wavはLFS |
| .gitignore | allowlist形式。workの一部コードのみGit対象 |

`work/build.py`や取得manifestの一部はGit追跡対象外です。ローカルに存在することとcloneに含まれることを分けて移行します。READMEが示す通り、過去の中間blend・絶対パス依存があり、制作スクリプト一式の存在はゼロからの再現性を意味しません。

## 完成シーンの実測

| 項目 | 結果 |
|---|---:|
| blendサイズ | 977,587,171 bytes（約932.3 MiB） |
| MP4サイズ | 126,092,752 bytes（約120.3 MiB） |
| BGMサイズ | 10,584,044 bytes |
| Scene内オブジェクト | 3,299 |
| Meshオブジェクト | 3,249 |
| 頂点 | 51,070,948 |
| Polygon | 39,294,268 |
| Image datablock | 384 |
| 未packのFILE画像 | 0 |
| 外部リンクライブラリ | 0 |
| 非有限値を含むobject transform | 0 |
| レンダリング設定 | Cycles、48 samples、1920×1080、100%、24fps、1–1248 |

頂点・polygon数はScene内Meshオブジェクトごとの元データ合計です。共有Meshの重複やmodifier評価後の数を補正した値ではなく、GPUメモリ実測でもありません。

SHA-256：`f04b68c07d138b880576d511000b55a9fc3104d28cc9e3750b511023b10ab70d`。

過去の `work/github_asset_audit.json` は383画像・全pack・外部参照0を報告しています。今回の384は全Image datablock数であり、集計条件・時点が同じとは断定しません。

`work/` の読取可能範囲でPNG 12,208枚・30,063,094,352 bytes、ZIP約2.82 GB、GLB約1.36 GB、b3dm約1.17 GBを確認しました。別地域・重複・過去版を含み、東京タワーの必要容量ではありません。一部vendorディレクトリはアクセス不可で、全容量の厳密な棚卸しは未完です。

## 再利用マップ

以下のパス・行番号は調査時原本に対するものです。

| 資産 / 根拠 | 再利用先 | 必要な変更 |
|---|---|---|
| 完成52秒blend | immutable legacy baseline | hash固定、権利監査、world/film分離 |
| scripts/render.py:8–35 | scripts/render/ | CPU対応を維持。カメラ・seed・品質preset・時間上限を追加 |
| scripts/encode.py | scripts/render/encode.py | 1248固定とBGM必須を引数化。PRは無音静止画を標準に |
| work/detail_upgrade/extract_glb.py:4–15 | scripts/import/legacy_3dtiles.py | b3dm→GLBとbatch属性分離を再利用。RTC必須等の仮定に入力検証 |
| work/detail_upgrade/build_upgrade.py:26–50 | scripts/import/ | ECEF→局所変換、batch対応、source_url付与を抽出。面の削除処理をIDベースへ |
| work/wide_detail/fetch.py | data取得ツール | 範囲選択・cache・retry。実行時latest選択を版固定manifestへ |
| work/landmark_rebuild/build.py:89–176 | generation/tokyo_tower | 構造、展望台、FootTown。既存collectionを対象に関数化 |
| 同:177–253, 274 | generation/azabudai_mori_jp | 外形profile、facade、podium。PLATEAU_data221 / batch 5直指定を安定IDへ |
| work/landmark_rebuild/profiles.json | 地物入力パラメータ | 元tile・featureの対応とprofile抽出方法を記録 |
| work/interior_reference/model.py:15–92 | generation/interior | ガラス床・内装・カメラ。推定配置と観測根拠を区別 |
| work/tower15_env/build_environment.py | materials/、generation/environment | 材質ノードの関数を抽出。後工程で廃止された航空写真材質を復活させない |
| work/street_detail/、work/tokyo_traffic/ | generation/roads、vegetation | 初期候補。個別スクリプトの全依存は次段階で監査 |
| work/interior_walk/repair_final_motion.py | camera regressionの設計参考 | transformとlensのAction分離、全frame照合。原本を変更するため検証には直接使わない |
| motion_verification.json | 既存カメラbaseline | 1248frame照合・範囲外保存の過去結果。新headについて再検証が必要 |

完成Sceneで `Tokyo Tower structure`、`Tokyo Tower decks and interior`、`Photo based main deck`、`Mori JP curtain wall`、`Mori JP interior`、`Mori JP podium`、`Flush glass floor surrounds`、PLATEAU collection群の存在を確認しました。名前が同じでも今後永続IDを付与します。

## 発見した移行上の問題

1. **位置の扱い**：旧buildは緯度経度の簡易換算、detail_upgradeはECEF→局所回転。さらに建物ごとに底面をZ≈0.32mへ移しています。現状の高さを実測標高として再利用できません。
2. **ID**：tile名とbatch番号は再配信・再分割で変わり得ます。文字列によるcollection削除、merged meshの部分削除をsource feature IDと置換記録へ移行します。
3. **品質の意味**：窓の5度傾斜、推定内装、植種、材質値、照明には演出・推定が含まれます。過去のpreview設定など古いscene propertyも残り、metadataの単純転記は不適切です。
4. **検証の副作用**：work/landmark_rebuild/verify_models.pyは材質変更・purge・保存も行います。verify_corrected52.pyは別コードを文字列置換してexecします。検証は新processでread-onlyに分離すべきです。
5. **動画とsceneの不一致履歴**：既存画像の使い回しがカメラの不具合を隠した事例がREADMEに記録されています。PR画像は必ずbase/headの実入力から生成します。
6. **権利**：埋め込み済みは配布許可済みを意味しません。PLATEAU、OSM、参考写真、BGMの由来をasset単位で監査します。

## 今回の検証範囲

実行済み：正常open、構成取得、FILE画像pack状態、library一覧、object transform有限性、Git状態、主要ファイル容量と完成blend hash。

未実行：全meshの幾何検証、画像デコード完全性、modifier評価、fresh render、GPU時間・VRAM測定、全工程再構築、GitHub側LFS取得、権利の最終承認。既存status.jsonのcompleteと動画・音声検証は過去実行の記録です。本調査でE2Eが成立済みとは扱いません。
