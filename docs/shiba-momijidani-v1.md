# 芝公園もみじ谷：樹林と園路の初版候補

東京タワー南東側のもみじ谷を、採用済みの街に追加する最初の候補です。現行の平坦な草地に林地の地表、園路、広葉樹75本、低木120株を追加しました。東京タワーや道路などの既存オブジェクトは変更しません。**現地の個木配置・標高を再現した完成モデルではなく、人間の画像レビューと採用は未完了です。**

## 根拠と範囲

- 固定OSMの林地 way `30526664`（もみじ谷、約9,716㎡）を外周に使用します。地区全体、区立芝公園、増上寺は対象外です。
- 園路 way `222753172`・`222753173` の平面位置を使用します。幅2.4mと高さは推定です。
- 階段4本の地図位置は保護領域に使います。`layer=-1` は相対的な重なり順であり、標高-1mと解釈しません。
- 樹木・下草は、林地境界、道路、園路、階段、建物から離して決定的に配置します。地図と既存シーンの道路幅に差があるため、固定cityから抽出した実際の路面も除外します。75本・120株という数、個体位置・寸法・樹種表現は制作上の推定です。
- 樹木は幹・枝と葉のメッシュで構成し、外部の葉画像は使用しません。

[東京都公園協会の園内図](https://www.tokyo-park.or.jp/park/siba/assets/files/shiba_map.pdf)で19号地を確認し、[公式のもみじ谷紹介](https://www.tokyo-park.or.jp/special/nagaokayasuhei/momijidani.html)で滝・渓流・橋を確認しました。これらの図版や写真は配布モデルのテクスチャに使用しません。参照日・hash・推定区分は[出典記録](../sources/shiba-momijidani-v1.json)に残します。

水路・池・滝・高低差については、現在の固定OSMに十分な形状情報がありません。今回は造形していません。現状の平坦な都市基盤への追加で、園路と階段の実際の高さ関係も未解決です。

## 再生成と比較

入力は `manifests/mori-plaza-connection-accepted.json` に固定した街（SHA-256 `9c142f54cc85689cb8a8bc00794dfe8e9b6bc9098f121c9fb02cdbc1aa3dbbc4`）です。旧都市や `mori` profileで代用しません。共通CLIで登録した後、回収済みの固定制作入力からplanを生成します。

```powershell
# PLAN_PYTHON は Shapely 2.1.2 / GEOS 3.13.1 を使える Python 3.12。
& $BLENDER --factory-startup --disable-autoexec --background $CITY `
  --python-exit-code 1 --python scripts/export_shiba_road_mask.py `
  -- --output data/local/shiba/roads.json

& $PLAN_PYTHON scripts/prepare_shiba_momijidani.py `
  --inputs $PRODUCTION_INPUTS --road-mask data/local/shiba/roads.json `
  --output data/local/shiba/plan.json

# 同一planのhashを areas/tokyo-tower/shiba-momijidani-patch.json と照合します。
& $RUNNER_PYTHON scripts/review.py --blender $BLENDER --input $CITY `
  --lock manifests/mori-plaza-connection-accepted.json `
  --features areas/tokyo-tower/mori-plaza-connection-accepted-features.json `
  --cameras areas/tokyo-tower/shiba-momijidani-cameras.json `
  --patch areas/tokyo-tower/shiba-momijidani-patch.json `
  --shiba-plan data/local/shiba/plan.json `
  --output data/local/reviews/shiba-candidate --device OPTIX `
  --width 1280 --height 848 --samples 32 --timeout 1200

& $RUNNER_PYTHON scripts/validate_shiba_momijidani.py --blender $BLENDER `
  --input data/local/reviews/shiba-candidate/after.blend `
  --plan data/local/shiba/plan.json --output data/local/shiba/saved-validation.json
```

実行先は毎回新しいパスを指定します。CLIのPythonは3.11/3.12、Blenderは4.5.1 LTSです。OptiX対応GPUがない場合は明示的にCPUを指定してください。planは実行環境・生成コードのhashを含むため、環境が異なる場合は内容とhashを再確認し、patchのplan hashも更新して再検証します。固定hashを無条件に書き換える運用はしません。

初版のplan hashは `bbbdb093b85b94fa167a73c54f5387260ea8fb562e3e876d76b50805d9ec4137`。[5視点のBefore/After画像](../renders/previews/shiba-momijidani-v1/README.md)をレビュー用に公開しています。画像10枚は検証済みの最終出力を変更せずにコピーし、[画像ごとのhash・入力・生成条件](../renders/previews/shiba-momijidani-v1/evidence.json)を記録しました。plan・blend・全ログは `data/local/` に保管します。画像の公開は採用判断や都市全体・参考図版への新しい配布許諾を意味しません。

## 検証と次の作業

2026-10-02の最終候補は、5視点×Before/After（1280×848、32 samples、OptiX）、原本hash不変、既存3,307オブジェクトの指紋不変と追加5部品の保存後検査に成功しました。75本の幹と120株の低木の接地を確認し、既存路面901三角形に対する基部3,315サンプルの交差は0件です。portable testsは247件中241成功・任意依存6省略でした。[コード・入力・保存モデル・結果の記録](shiba-momijidani-v1-validation.json)

既存レビューCLIで原本hash不変・保存後の別process読み込み・許可した5オブジェクトのみの追加・5視点の同条件Before/Afterを検査します。専用validatorは地表と園路の閉面・面積・保存座標、植栽の境界と保護領域からの離隔、既存道路面と幹・低木の基部を検査します。路面との接触判定は基部のサンプル点によるもので、歩行可能性全体の保証ではありません。

2026-10-03にmain `29157af` を取り込み、共通review runnerに追加された森JP西側園路と芝公園の両処理を保持して競合を解消しました。同じ入力・plan・5視点で再生成し、保存したBefore/Afterの全オブジェクト指紋と素材参照が初回候補と一致することを確認しました。再レンダーの差は各色最大1/255の微小差で、画像ごとの測定値を[main同期後の検証記録](shiba-momijidani-main-sync-validation.json)に記載しています。公開済み画像と採用待ちの候補はそのままです。

次に現地写真・地形資料から、滝の位置と形状、渓流、橋、階段の高さ、樹林密度を詰めます。今回の樹木群と地表を細部の基準版として採用するかは、比較画像を確認して判断します。
