# 東京タワー周辺の道路・歩道の仕上げ

[7視点のBefore/After画像](../renders/previews/road-finish-v1/README.md) / [保存後検証とテスト結果](road-finish-v1-validation.json)。保存後検証は成功し、portable testsは424件成功・8件skipです。人間による見た目の採用判断は未完了です。

採用済みPR #67の保存モデルを起点に、車道・駐車場・歩道・側溝・既存の路面塗装を見分けやすくします。アスファルトの細かな粒感、石・コンクリートの目地、舗装ごとの粗さと色の差を追加しました。形状、道路幅、高さ、白線の位置は維持します。仕上げ値は演出上の近似であり、実物の材質・寸法・色を測定したものではありません。

変更は8路面オブジェクトの材質割り当てと、専用材質6個の追加です。元材質は未使用の第2スロットに参照を残し、保存時の消失を防ぎます。面の材質番号は保持し、追加スロットを使う面はありません。建物、タワー、階段、交通と植栽の表示状態を保持します。

タワー原点から水平距離150m以内に新しい仕上げを適用し、150–220mで元の仕上げに連続的に戻します。220m以上では、複製して保持した元のノードグラフをそのまま使います。世界座標を用いた粒感と矩形の舗装目地です。目地の向き・割り付けや0.6×0.3mの制作値は現地の再現を確定するものではありません。隆起や割れ、道路標示は新設していません。既存の輪郭や地形の近似は残ります。

入力: 640,221,535 bytes、SHA-256 `df71be6c9b2e606a7ec277f15285bc92123a712d0069d7c413ab5d210d7cc9c3`。ローカルの不変入力は `data/local/reviews/tower-site-v8-final-02/after.blend` です。旧都市ファイル、埋め込み素材、音源、参照写真はこの変更に同梱しません。

[実装](../scripts/road_finish_v1.py) / [固定カメラ](../areas/tokyo-tower/road-finish-v1-cameras.json)。`build`で入力を検査して新しいblendを保存し、`validate`で別プロセスから保存候補を開きます。全3,372オブジェクトのメッシュ指紋、変換、材質番号、UV、対象外の材質割り当て、メタデータ、既存材質、画像依存、カメラ・ライト等のデータ数を照合します。既存のmodifierやネストしたノードグループの完全な指紋には対応していません。

`render-before` / `render-after`は固定7視点を同条件で描画します。通常の交通コレクション非表示を維持し、車両確認用視点のカメラも路面を撮る視点として利用します。既存の交通を診断表示した前PRの画像とは条件が異なります。Blender 4.5.1、Cycles/OptiX、1280×848、32 samples、seed 0。

```powershell
# 各PHASEを build → validate → render-before → render-after の順に実行
& BLENDER --factory-startup -b --threads 2 --disable-autoexec --python-exit-code 1 --python scripts/road_finish_v1.py -- --phase PHASE --input INPUT_BLEND --output NEW_OUTPUT
```

保存候補は `data/local/reviews/road-finish-v1-preview-02/after.blend` を別プロセスで検証しています。最終描画用の `data/local/reviews/road-finish-v1-final-01/after.blend` はそのバイト単位で同じコピーです。再検査結果と入力・候補・コード・カメラのhashは各runに記録しています。技術検査と人間による見た目の採用判断を分けます。
