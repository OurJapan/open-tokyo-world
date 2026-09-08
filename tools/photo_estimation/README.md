# PC側の写真寸法推定

スマホから保存したZIPをPCへ集め、写真の特徴点を自動照合して可視点間の距離を推定する。撮影者による対象名・寸法の入力は不要。Blenderや外部APIを使わずローカルで処理し、元写真・既存モデルを変更しない。

## 起動

Python 3.12で、リポジトリのルートから実行する。

```powershell
python -m venv .venv-photo
.\.venv-photo\Scripts\python.exe -m pip install -r tools/photo_estimation/requirements.txt
.\.venv-photo\Scripts\python.exe tools/photo_estimation/estimate.py C:\photos\one.zip C:\photos\two.zip --output C:\photos\estimate-001
```

入力は1〜12個の観測ZIP、またはそれぞれ `observation.json` と `photo.jpg` を含むフォルダ。現在のWebアプリのv0.1 ZIPをそのまま使える。受付番号は不要。APIから取得した場合も同じファイル名で1件ずつ配置する。出力は新しいフォルダを指定する。引数にAPIトークンは不要で、送信や公開は行わない。

## 出力とモデル作成への受け渡し

- `report.md`：結果・推定できなかった理由・対応点の画像。
- `estimate.json`：元写真のSHA、観測ID、手法、品質指標、GPSによる尺度、点間距離、両写真の対応画素、カメラ座標の端点。
- `pair-N-photo-M.jpg`：推定対象の2点A・Bを示す確認画像。元画像は変更しない。

モデル作成担当は対応点A・Bが同じ静止物の必要な箇所か確認し、距離を参考にする。自動選択された点は入口や建物の両端とは限らず、別の物体に属する可能性もある。**建物全体の幅・高さとして流用しない。** 自動モデル変更は `automatic_model_changes:false`、受け渡しも `apply_automatically:false` とする。座標は1枚目カメラ基準の右・下・前で、Blenderのワールド座標ではない。

## アルゴリズムと失敗条件

SIFT特徴点→双方向のratio test→Essential行列RANSAC→相対姿勢→三角測量。30点以上、対応の整合率35%以上、視差1.5度以上、再投影誤差2px以下を要求する。単一平面・回転だけと考えられる場合は奥行きの曖昧さを理由に停止する。外れ値の影響を減らすため、点群の各軸10〜90パーセンタイル内にある対応点から離れた2点を選ぶ。これは物体の境界抽出ではない。

GPS水平移動距離を尺度にする。移動距離が各GPSの報告誤差の和の3倍未満、2m未満、200m超ならメートル値を出さない。GPSがない場合も `unresolved`。写真1枚、重複、対応不足、画角情報不足、画像hash不一致を区別する。入力不正は終了コード2、解析完了（推定不能を含む）は0。

**距離が出ても `provisional_metric`（暫定）であり測量値ではない。** 同じ高さから撮ったという仮定で水平GPS距離を3D基線として利用する。階段や上下の移動には適さない。GPSの系統誤差は検出できない。現行Webの画角60度は実測値ではなく、レンズ歪みも未校正なので尺度や奥行きが偏る可能性がある。JSONの尺度感度はGPSの報告誤差に対する参考比率で、総合的な誤差範囲や信頼区間ではない。

建物の自動特定、地図の外形と画像の照合、多視点の統合・bundle adjustment、単眼深度AI、メッシュ作成は対象外。12枚の入力でも各ペアを独立に評価し、地理的な同一対象だとは断定しない。写真は同じ静止対象が重なるよう、地面の同程度の高さで位置を変えて撮る。撮影枚数や移動距離だけで成功は保証しない。

## 検証と出典

`python -m unittest discover -s tests -p test_photo_estimation.py -v`。依存導入済み環境で実施する。ポータブル契約テストは依存がなければ画像テストをskipするが、専用CIは依存を導入して必ず実施する。

合成の非平面3D点からの既知尺度復元、合成JPEG→ZIP→特徴点照合→レポート、GPS不足、平面・回転、無模様、重複、hash不正、出力上書き拒否を検証。合成データの成功は現地の精度保証ではない。飯田橋の複数視点実写真での精度確認は未完了。

実装のAPI根拠：[OpenCV Camera Calibration and 3D Reconstruction](https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html)。`recoverPose`の並進は尺度未定であり、画像だけから絶対寸法が確定するわけではない。
