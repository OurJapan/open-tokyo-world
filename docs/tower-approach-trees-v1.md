# 東京タワー北東アプローチの並木と植樹枡

旧cityで親collectionの描画設定により隠れている街路樹から、東京タワー北東側の8本を独立collectionへ復元しました。既存の推定XY配置を保持し、土面と縁枠を新しく制作して根元を合わせています。編集画面での二重表示を防ぐため、対象の元16部品だけに `hide_viewport=True` を設定します。街路樹の実在位置・樹種・本数や現地の地形を確定する変更ではありません。

起点はmain `805310ef7a6aad5a13104334e798fb83b35f1711`、入力は[入口接続採用版](../manifests/mori-plaza-connection-accepted.json)です。西側園路、森JP中央広場、XY約−430,390の別担当地物、共通city登録、通常のBlender設定は変更していません。後から取り込まれたPR #47との合成検証は親の統合作業に残します。

## 制作範囲

地物IDは `otw:jp:tokyo:minato:tokyo-tower:northeast-approach-trees-v1`。collectionは `OTW Tokyo Tower northeast approach / trees v1` です。[固定設定](../areas/tokyo-tower/approach-trees-v1.json)に元オブジェクトの変換、対象範囲、8本のID、4つのカメラを記録しました。

| 項目 | 制作内容 |
|---|---|
| 既存の配置番号 | 158、160、164、166、168、170、172、174 |
| 中心のXY範囲 | X −26.211〜69.435m、Y 28.867〜77.443m |
| 新規オブジェクト | 幹8、樹冠8、集約した土面1、集約した縁枠1 |
| 土面・縁枠 | 外幅1.20m、内幅1.04m、土面Z=0.44m、縁上端Z=0.46m、底面Z=0m |
| 接地 | プロトタイプの幹の最下端はローカルZ=0.2m。各scaleに応じて変換を補正し、土面へ接地 |
| 共有形状 | イチョウ3種類の幹・樹冠6メッシュを参照。新しい形状は閉じた土面・縁枠2メッシュ |

初回候補に含めた旧配置162は、追加検査で赤いタワー鉄骨との交差を検出したため採用していません。幹150組・樹冠3,877組のBVH面交差を確認し、この配置を保持したまま表示する案を除外しました。最終候補の8本は鉄骨・基礎とのBVH面交差が0組です。

樹木の形状と4材質は既存の[CC BY 4.0許諾記録](../assets/procedural-components/provenance.json)のhash・完全な数式材質signatureへ照合しています。作者表示はark4ez / OurJapanで、[既存NOTICE](../assets/procedural-components/NOTICE.md)を保持します。旧都市の形状・画像・配置に対する許諾範囲を拡張していません。植樹枡は今回の独自制作で、現地の植樹枡の形状を復元したという主張はありません。

## 再生成と確認

専用worktreeのルートで、正当な提供元の固定入力を指定します。出力は未使用の `data/local/` 内に限定し、通常workspace登録は呼び出しません。PythonはBlender同梱3.11.11でも実行できます。

```powershell
$blender = 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe'
$runner = 'C:\Program Files\Blender Foundation\Blender 4.5\4.5\python\bin\python.exe'
& $runner scripts/tower_approach.py --input 'C:\Received\city-connection.blend' --blender $blender --output data/local/tower-approach-new --device OPTIX --width 960 --height 540 --samples 16
```

固定入力は559,040,261 bytes、SHA-256 `9c142f54cc85689cb8a8bc00794dfe8e9b6bc9098f121c9fb02cdbc1aa3dbbc4`です。入力や対象の変換・許諾済み形状・材質が違う場合、既存出力がある場合、同じcollectionが存在する場合は停止します。非表示の元collectionを一括表示する処理はありません。

最終ローカル出力は `data/local/tower-approach-v1-final-02/` です。

- `after.blend`: 街の保存済み候補。bytes・SHA-256は検証JSONの `outputs` に固定しています。
- `approach-additions.blend`: 親の統合用collectionライブラリ（約5.75MB）。18オブジェクト・8メッシュ・4材質、画像・建物・カメラ・照明・埋め込みTextを含みません。bytes・SHA-256は検証JSONの `outputs` に固定しています。collectionの `otw_source_viewport_suppression` 属性には、統合時に編集表示を隠す元16部品の名前をJSON配列で保持します。
- `review.html`: 同条件の4組のBefore/After。並木・道路、歩行者、根元、タワー周辺の画角です。
- `run.json` と各phaseのJSON/log: 入力・生成コード・設定・画像hash、保存後の指紋、配置検査と実行時間。

[保存後検証の抜粋](tower-approach-trees-v1-validation.json)はGit管理のmetadataです。大型blend・都市画像・完全なログはローカルへ保持し、公開配布・push・PR・mergeは行っていません。初回 `tower-approach-v1-review-01` は鉄骨交差があり、次の `tower-approach-v1-review-final` は編集画面の二重表示がある旧候補です。`tower-approach-v1-final` は表示抑制に伴う変換の保存後検査で停止した実行です。最終候補は `tower-approach-v1-final-02` です。

## 検証結果と残る範囲

2026-10-02、Blender 4.5.1 LTS、Windows、RTX 3060 TiのOptiX、960×540、16 samples、seed 0で4組8枚を生成し、全画像を目視確認しました。カメラ・照明・色管理条件は各組で同じで、描画専用プロセスのカメラ切替は保存候補へ反映していません。

保存した街を別プロセスで再読込し、既存3,307オブジェクトの形状・材質・変換・描画設定・所属・記録した属性、17collection、383画像の検査記録、記録対象のscene設定を保持することを確認しました。対象の元16部品の編集表示抑制を許可差分に限定し、他3,291オブジェクトの指紋はすべて一致します。追加は18オブジェクトだけです。追加18部品の通常表示と元16部品の非表示も検査し、元入力hashは実行後も一致します。増分ライブラリも別プロセスの空sceneへappendして検査しました。

非表示にした元16部品は、再読込時に未評価の `matrix_world` が単位行列になるため、親・animation・constraintsのない固定sourceに限定して保存された `matrix_basis` で変換を比較します。新規配置もこの保存値から作り、表示を無効にした後の未評価cacheは使いません。

8本すべての根元が土面へ接し、縁枠は隣接歩道Z=0.46mに一致します。土面・縁枠は有限座標・非ゼロ面積・閉形状・外向き体積・設定寸法を検査しています。植樹枡の投影と既存車道・タワー基礎の連続面積重複は0㎡、樹木とタワー鉄骨・基礎のBVH面交差は0組です。近傍のPLATEAU・旧roof/wall計11メッシュに対して各植樹枡5点の建物柱状検査も通りました。

Portable testsは240件中234成功・6skip、追加16件はすべて成功です。保存した候補にbuildを再適用する異常系も終了1で二重追加を拒否し、候補hashは不変でした。既存modifier等の36警告は保持しており、完全なanimation・modifier評価・入れ子nodeの指紋や全都市のsolid-volume衝突検査は含みません。歩行者通行の連続幅、現況植生・地理高度・全周辺建物の実測精度、別PCは未検証です。時間は一度の測定で、性能の中央値や新しい性能予算の承認を意味しません。

親での次の作業は、検証済み `approach-additions.blend` のcollectionを最新の専用統合候補へappendし、属性にある元16部品の `hide_viewport=True` を適用して、西側園路などの他区画を含めて差分・接地・画像を再確認することです。本CLIは固定入力専用なので、PR #47を合成した別hashの街へ暗黙に適用しません。人間の画像確認と統合確認後に、公開するmetadata・コード・許諾された画像を選びます。
