# 東京タワーの塗装とトップデッキ接合：最新mainへの統合

鉄骨の斜材・柱を横断する塗装境界を揃え、トップデッキの窓柱・ガラス・ガスケット下端を既存床へ延長します。独立制作の3コミット（`568a9e7`、`9f1aa67`、`dd188b7`）をmain `3b1eb5f6c10ca9c0ebb072348faea4981985439e` へ取り込み、同じ都市候補として検証します。塗装済みモデルを土台に接合修正を制作したため、依存関係を保つ1本のDraft PRです。

PR #50のviewer変更とPR #51の樹木コードはmainのままです。変更対象ファイルに重複はありません。PR #52のもみじ谷候補や他の未採用作業は含めません。元checkout、各制作worktree、入力blendと通常workspace登録を保持します。マージは行いません。

## 入力と範囲

登録用manifestはPR #46のままなので、登録済みcityを最新mainの成果と混同しません。PR #47＋#49の固定city `09977e34f02c…` へ、採用済みPR #51の固定増分 `bd190345084c…` を既存append処理で加え、Beforeを作成します。追加18オブジェクトとcollectionをPR #51保存モデル `966a81151bea…` に照合し、元3,309オブジェクトのうち旧樹木16部品の表示抑制だけを許可します。

[固定入力一覧](../assets/tokyo-tower/city-repairs-v1.json) / [再実行スクリプト](../scripts/tokyo_tower_city_repairs.py)。都市の大きなblendや素材はローカル入力であり、Gitへ同梱しません。

| 対象 | 都市側への反映 | 保持する状態 |
|---|---|---|
| 005・006：オレンジ／白の鉄骨 | 2個の専用材質で6境界を表現 | raw／評価後メッシュ、ベベル、元材質 |
| 009：窓柱 | 下端のraw 160頂点を約30 mm下へ | XY、上端、接続、元ベベル設定 |
| 010：ガラス | 下端のraw 160頂点を約57.5 mm下へ | XY、上端、接続、材質 |
| 011：ガスケット | 下端のraw 160頂点を約30 mm下へ | XY、上端、接続、材質 |

**これらはモデル座標上の隙間・推定境界です。実物を測量した寸法ではありません。** 塗装の7等分という考え方は[公式説明](https://www.tokyotower.co.jp/plan/towerpedia/)に基づきますが、154 m下端と境界標高は旧モデルの推定値です。接合部は[公式の内部写真](https://tdt.tokyotower.co.jp/en/topdecktour/)に見られる閉じた窓下部を参考に、既存3部品で簡略化した修正です。現実の水切り・金物・シールの断面を復元したものではありません。

独立モデルでは柱のベベルが焼き込まれているため、下端1,440頂点の移動になります。都市側はベベルを保持してraw 480頂点だけを移動します。柱のベベル再評価では独立候補に対しXY最大1.863e-9 m、下端Z最大1.526e-5 m（約0.0153 mm、float32の1 ULP）の数値差が出ます。評価後上端Zは完全一致し、raw座標ではXYと上端の完全一致を要求します。評価後座標を参照値へ戻した一時コピーが元の完全hashを再現することも検査し、接続・属性・シェーディングの追加変更を拒否します。ガラスとガスケットは完全hash一致です。柱のベベルは従来どおりviewport ON／render OFFです。独立メッシュをそのまま都市へ置換しません。

77個の固定部品IDとalias・形状・材質を照合し、全対応表を保持します。都市側でID属性を付けるのは従来の塗装対象005・006だけで、残り75部品の属性は変えません。独立ファイルの77個の永続IDも変更しません。共有台帳の変更はありません。

## 保存後の検査と画像

[検証JSON](tokyo-tower-city-repairs-v1-verification.json)と[Before/After画像](../renders/previews/tokyo-tower-city-repairs-v1/README.md)を参照してください。完全なログと構造スナップショットはignored `data/local/city-repairs-03/` と `data/local/` に保持します。01は旧部品の地物タグ有無の扱い、02は上記ベベルの完全hash比較で停止した診断用出力であり、採用候補ではありません。

検査は別Blenderプロセスで保存ファイルを再読込します。対象外の都市オブジェクト、元材質、packed画像、collection、action、World、カメラ、照明を比較し、対象3部品も座標を戻した一時コピーで元メッシュの完全hashを再現することを要求します。120部材へ床上15 mmの接触rayを投射します。rayは局所的な隙間の検査であり、接触面全域や気密・構造安全を保証しません。

保存後検証に成功し、3,327オブジェクト中3,322を完全保持。384画像データ（packed 383）、既存551材質、18 collections、23 actionsを保持しました。120部材のrayはBefore 0/120、After 120/120です。既存VIEWER画像のcolorspace enum警告が残りますが、新規の素材変更・修復はせず、処理はexit 0で完了しています。

PR #51で非表示になった静的な旧樹木16部品は、再読込時の評価キャッシュを避け、保存されたmatrix_basisと位置・回転・尺度を比較します。派生dimensionsだけを除外し、メッシュ・保存transform・表示状態は厳密に保持します。既存の組合せ検証で再有効化によりdimensionsが復元することを確認済みです。

最新コードのportable testsは297件中290成功・任意依存7 skip（Shapely 2、OpenCV 5）。`compileall` も成功。既存都市や樹木の変更、対象材質・modifierの変更、評価後上端Zの移動、許容丸め幅を超える座標差を拒否する検査を含みます。

全景、205 m帯、230 m帯、足元と樹木、トップデッキ全体、窓下端近景の6組を、同一camera・照明・World・色管理・seedで都市候補から描画します。Cycles CPU、2 threads、640×640、通常8 samples／下端近景32 samples、denoising ON、adaptive sampling OFFです。保存blendへのレンダー用cameraの書込みは行いません。

旧制作記録は[独立塗装](tokyo-tower-paint-bands-v1.md)、[初回都市塗装](tokyo-tower-paint-city-v1.md)、[独立接合](tokyo-tower-topdeck-junction-v1.md)に残します。各文書の当時の未公開・未統合という記述は履歴です。

## 再実行

Blender 4.5.1 LTSと、固定hashに一致する正当に提供された5入力が必要です。未作成の出力ディレクトリを指定します。次の各phaseを別プロセスで順番に実行します。

```text
BLENDER --background --factory-startup --threads 2 --disable-autoexec --python-exit-code 1 --python scripts/tokyo_tower_city_repairs.py -- --phase build --base PR47_PR49_CITY --trees PR51_CITY --delta PR51_DELTA --reference FIXED_ID_TOWER --topdeck ISOLATED_TOPDECK_CANDIDATE --output data/local/city-repairs-new
```

同じ引数で `validate`、`render-before`、`render-after`、`compare` を実行します。portable checksは `python -m unittest discover -s tests`。Blenderの追加検査は `tests/blender_tower_paint_bands_smoke.py`、`tests/blender_tower_paint_city_smoke.py`（固定PR47＋#49 cityを `--` の後へ渡す）、`tests/blender_topdeck_junction_smoke.py` です。

## 公開範囲と残る限界

2026-10-02のユーザー承認に基づき、コード・必要な検証資料・小さな比較PNGのみを `ark4ez` 名義のDraft PRとして公開します。東京タワー対象モデルの作者表示はark4ez / OurJapan、CC BY 4.0。元city、第三者のPLATEAU／OSM等、画像素材の既存条件は保持し、参考写真やtextureを新規配布しません。全都市blendの再配布許諾を追加するものではありません。

塗料色の実物一致、glTFへの材質変換、窓上端や床と外側白いshellの別の隙間、全都市の自己交差、実機性能、樹木位置・植樹枡の現地妥当性は未検証です。採用とマージは人間の判断に残します。
