# 未確認の外壁画像を使わない比較候補

2026-09-26、PR #12採用版から `facade_atlas.png` を取り除いた別の街モデルを作成しました。元の登録済みモデルは変更していません。候補の採用・街全体の配布承認は未決定です。

## 変更と見た目

`wall0`〜`wall7` の材質を、画像を参照しない数式による窓・窓枠・外壁の材質に置き換えました。この8メッシュは市街地の建物群をまとめたもので、8棟という意味ではありません。形状・位置・UV・道路・PLATEAU画像は保持します。

窓は横約2.5m、階高3.2mという表示上の仮定です。実物の窓やバルコニーを復元したものではありません。窓の凹みはシェーダーによる表現で、開口部や室内の形状は追加しません。屋根面では窓模様を抑制しますが、建物ごとの高さ・開口位置に合わせた個別調整はありません。

近景・街区・街全体の3視点を比較しました。近景では元画像のタイル、バルコニー、室外機などの細部が失われ、外壁が均一に見えます。上端・角では窓模様が途中で切れる箇所もあります。出典未確認画像への依存を取り除く技術的な候補であり、見た目の改善や実物精度の合格判定ではありません。

## 保存後の検査

Blender 4.5.1 LTSで作成し、保存したBefore/Afterをそれぞれ別プロセスで開いて検査しました。[検証記録](city-facades-v1-verification.json)に入力・出力・コード・カメラのhashを記録しています。

| 項目 | 結果 |
|---|---|
| 対象 | `wall0`〜`wall7` の材質のみ |
| 全体 | 3,305 objects / 3,255 mesh objects |
| 頂点・面 | 51,234,867 vertices / 39,532,616 polygons、変更なし |
| 対象外のobject指紋 | すべて一致 |
| 対象の形状・UV・変換・表示状態 | すべて一致 |
| 削除した画像 | 名前とpacked hashが固定された `facade_atlas.png` 1枚のみ |
| その他の画像 | 382枚、名前・packed hash・寸法を保持 |
| 新材質 | 画像・画像を隠せるノードグループなし。保存前後のノード設定hash一致 |
| 比較画像 | 同じ照明・カメラ、Cycles / OptiX、960×540、32 samples、seed 0、3視点×2 |

既存review harnessの指紋に基づく検査です。すべてのmodifier・animation・node group・外部資産の内容、実物精度を網羅した検査ではありません。出典が一致した画像にも、個別の利用条件と表示の確認は残ります。

## 再作成

PR #12の固定版を保持している場合に実行できます。[共通city基準版の更新](city-baseline-pr40.md)後も、この比較候補は旧PR #12を入力にします。出力フォルダーは新しい名前にしてください。入力hashが違う場合、既存出力がある場合、対象外の変更がある場合は失敗します。再実行で編集済み候補を上書きしません。

```powershell
$blender = 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe'
$python = 'C:\Program Files\Blender Foundation\Blender 4.5\4.5\python\bin\python.exe'

& $python scripts/review_city_facades.py --blender $blender --input data/local/assets/tokyo-city-pr12/city.blend --output data/local/reviews/facades-new --device OPTIX
```

OptiXを利用できない環境では明示的に `--device CPU` を指定します。GPUからCPUへの暗黙の切替は行いません。`review.html` が3視点の比較、`after.blend` が候補です。検証log・JSONも出力フォルダーに残します。今回の保存先は `data/local/reviews/facades-v1-20260926/` です。

候補blendと比較画像はローカルに保持します。公開対象は独自コード、数値設定、検証metadataです。街の登録版や配布可能状態は更新しません。[道路・形状を含む配布準備](city-distribution-plan.md)を続けます。
