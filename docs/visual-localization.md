# Visual Localization / OTW Visual Map

調査日：2026-09-07。実機・現地データによる精度測定は未実施。以下の時間・精度・件数は実験の初期予算と判定基準であり、既存サービスの性能保証ではない。

## 結論

既存OTW geometryは候補絞込み・輪郭・遮蔽の予測・地物ID付与に再利用できる。ただし、演出材質、推定形状、個別の地面補正を含むため、そのまま信頼できるVisual Mapにはならない。最初はGPS/方位で概略表示し、**停止中の単一画像からposeを補正できるか**を検証する。運営が事前にmapを登録する工程と、一般利用者が周囲へcameraを向ける工程を分ける。利用者による枠合わせを必須にしない。

## 再利用技術の比較

| 方式 | 使う情報 | 利点 / 主な不足 | 採用段階 |
|---|---|---|---|
| GPS + orientation | 地理位置、重力、粗い方位 | 少ない準備。位置・方位誤差で外観が大きくずれる | 全端末のbaseline |
| OTWからのsynthetic view matching | RGB/edge/depth + 地物ID render | 既存資産を直接使える。実写との外観差・誤geometryが問題 | 最初の小実験A |
| 実写SfM + retrieval + 2D–3D PnP | 重複写真、特徴点、測地登録した点群 | 実写外観を使える。map作成・位置登録・権利処理が必要 | 比較実験B、精度向上の本命 |
| 商用VPS REST | 自前/契約mapと画像・K | server機能を再利用。coverage、転送、契約、vendor lock-in | API adapterで比較可能 |
| ブラウザVIO / SLAM | 同期camera・IMU時系列 | 連続追跡。Safariのセンサー同期/K/発熱が課題 | 単画像成功後 |
| NeRF / 3DGS pose最適化 | 事前に構築したradiance map | appearanceを使った微調整。map生成・初期pose・GPUが必要 | 後続研究 |

[hloc](https://github.com/cvg/Hierarchical-Localization)はretrievalとfeature matchingを組み合わせる6DoF localizationの再利用候補。[LightGlue](https://github.com/cvg/LightGlue)は画像間matchingに使えるが、単独では地理座標・metric scale・地物IDを出さない。[COLMAP](https://colmap.github.io/faq.html)のSfMとgeo-registrationを組み合わせる。採用時は各repo、重み、依存extractorのlicenseとversionを別々に固定する。hloc一式をブラウザでそのまま動かせるとは扱わない。

[Immersal REST API](https://developers.immersal.com/docs/rest-api/)は画像とcamera intrinsicsを用いたserver localizationを提供する。東京タワー周辺の利用可能map・精度・最新料金は未確認。自前mapの登録、OTW frameへの変換、匿名化後画像の受理可否を先に試す。tokenはbackendのみ保持し、失敗は`no_match`として返す。[Niantic VPS](https://nianticspatial.com/docs/nsdk/features/lightship_vps/)のnative SDK説明をSafari対応の根拠にはしない。旧Web VPSの新規利用制約は[Safari調査](iphone-web-ar-research.md)を参照。

[iNeRF](https://arxiv.org/abs/2012.05877)はradiance fieldからのpose最適化、[GSLoc](https://arxiv.org/abs/2410.06165)は3D Gaussian mapを使うdense alignmentの研究例。研究成果の存在は、東京の屋外Safariで低遅延に動く証拠ではない。最初のPoCの依存にしない。

## 単画像localizerの処理

1. 撮影時の位置・方位・時刻・frame/version・解像度・Kの推定根拠を受ける。GPS accuracyが大きい場合は候補範囲を広げるが、300mの公開PoC範囲を超えるなら`outside_coverage`。
2. retrievalで候補視点top 5〜10を選ぶ。方位の信頼度が低いときに狭いyaw窓で正解を排除しない。
3. local feature matchingで2D対応を作り、動く人/車、空、反射、画面へ重ねた3Dを除外する。
4. 参照画像のSfM pointまたはsynthetic depthで対応を2D–3Dにする。単なる画像間homographyでは一般的な都市のmetric 6DoFは定まらない。
5. Kと歪みモデルを使いRANSAC PnP→inlierでrefine。[OpenCV PnP](https://docs.opencv.org/4.x/d5/d1f/calib3d_solvePnP.html)のworld→camera変換を[座標契約](web-spatial-viewer-architecture.md)のcamera→areaへ変換する。
6. inlier数、画像上の分布、再投影誤差、候補間の曖昧さ、GPSとの整合、map登録誤差、撮影からの経過時間を判定する。反復窓面への集中や平面退化を拒否する。
7. `localized / no_match / ambiguous / stale / outside_coverage / invalid_calibration`を返す。失敗をidentity poseやconfidence=1で埋めない。

初期gate例：inlier 30以上、inlier率0.25以上、画像の4区画以上へ分散、median再投影誤差3px以下（幅960pxへ正規化）。閾値は検証集合で調整し、テスト集合では固定。再投影誤差だけでは正解を保証しない。confidenceは未校正の確率にせず、raw metricsと`low/medium/high`判定理由を返す。

## A：既存geometryからの検証

許諾が確認できた東京タワーの少数部品または周辺建物を対象に、固定入力hashからRGB、edge、depth、feature ID maskを生成。架空形状を実在の測地精度の証拠にしない。

まず限定した安全な歩道区間で候補camera 50地点×yaw 12方向×pitch 3段階=1,800 viewをoffline生成する。高さは初期仮定と記録し、必要なら段階追加。RGB 100KB/viewなら約180MB、depth/特徴量を加えると数百MB〜GBのserver mapになる。全mapをiPhoneへ送らない。実写queryは別日に30枚以上を取得し、見た目が良い一例だけで合格としない。

評価を「同一モデルrender同士」と「実写→render」に分ける。前者は変換/実装の単体確認であり、現地localization成功には数えない。texture一致が弱ければ線分・輪郭・semantic maskを比較するが、位置不定性を隠してyawだけを6DoF結果として返さない。

## B：Reality Observationからの実写map

運営者が歩道から重複のある100〜300枚を撮影する初期案。SfMでcameraと点群を復元し、独立した既知点/測位情報でscale・rotation・translationをOTWの登録済みframeへ結び付ける。GPSが付いた写真が集まっただけではmetric mapの精度は保証されない。弱いGPSは不確かさ付きpriorとし、検証点を別に確保する。

visual mapを`map_id / map_revision / frame_revision / source_observation_ids / registration residuals / feature associations / consent policy revision`で管理する。新規投稿はreview前にmapへ自動混入させない。地物を誤修正した画像や悪意ある投稿によるmap汚染を防ぐ。world geometryとvisual mapの版は別で、互換組合せをmanifestで指定する。

地物IDは、登録済みpointのgeometryへの近傍/投影対応と人間確認を保存する。木、車、人物の点は建物IDへ強制所属させない。同じ地点でも季節・時間帯・工事でreferenceが古くなるため、観測日を残し、map更新後も旧版の再現性と削除要求の依存追跡を維持する。

## camera校正と連続追跡の限界

一般Safari cameraからはnative AR cameraの校正済みKが保証されない。運営側で少数端末の背面主cameraを校正し、streamの実寸・crop・orientationとKを一緒に保存する。レンズ自動切替・電子手ぶれ補正・zoomでKが変わり得る。単一FOVを全iPhoneへ流用しない。校正不能なら粗いyaw補正だけの実験結果とし、metric pose成功に含めない。

serverから返るposeは**送信フレームの時刻**に対応する。歩いた後の現在位置へ適用してはいけない。最小PoCでは停止中だけ採用し、撮影から2秒を超えた結果、要求ID/stream/frame不一致、移動が疑われる結果は棄却して再要求する。連続利用では特徴追跡やlocal SLAMで相対変換を伝播できることが必要で、ジャイロだけでは並進が分からない。

## browser / serverの処理分担と概算

| 配置 | 利点 | 課題 | 最小案 |
|---|---|---|---|
| browser JS/Wasm/WebGPU | 写真を送らず低RTT、offline候補 | model/map download、発熱、メモリ、Safari差、学習済みmodel変換 | resize・任意mask・軽い品質判定 |
| server CPU/GPU | hloc/COLMAP/OpenCVや大きなmapを再利用 | upload、通信切断、queue、データ保護 | retrieval/matching/PnP |
| hybrid | 小画像送信＋端末表示の分離 | 時刻同期、同じframeの扱い | 推奨 |

試算：960px JPEG 200KB、upload 5Mbpsなら約0.32秒。resize/encode 0.03〜0.10秒、RTT 0.05〜0.20秒、GPU retrieval/matching/PnP 0.2〜1.0秒、返却/描画0.02〜0.05秒と仮定すると、queueなし約0.62〜1.67秒。1Mbpsではuploadだけで1.6秒となり2秒採用期限を超えやすい。数値は測定前の予算で、採用APIの実測で置き換える。

初期mapは100〜300参照画像、各2,000点×256次元×float32なら特徴descriptorだけで約205〜614MB。照合を全件全点で実行せず、粗い地理絞込みとretrievalを使う。ブラウザへ大mapを送る方式を初手にしない。

2秒に1回200KBを送ると1端末約0.8Mbps、1分約6MB。10端末で最大5 request/s、server処理0.5 GPU秒/requestなら単純直列換算で2.5 GPU秒/秒となりqueueが増える。PoCは明示開始の少数query、1端末1 in-flight、再試行最大2回、server上限/timeoutを設定する。月額費用はprovider・稼働時間未確定なので算定しない。予算式は`query数×単価 + GPU稼働時間×単価 + 保存GB月×単価 + egress`。

## 比較実験の判定

GPSのみ、GPS+orientation、A、Bを同じtest queryで比較。別日・別端末・新しい撮影位置をtest側に分離し、隣接動画frameをtrain/testへ混在させない。独立した基準pose/検証点から位置m・回転deg・再投影pxを測り、基準自体の不確かさも記録する。

最初の画像補正gateは、30以上の独立queryで受理率70%以上、受理結果のmedian位置誤差3m以下・yaw誤差3°以下、GPS/方位baselineより改善、誤った建物へのhigh-confidence受理0件を目標とする。0件は安全性の統計保証ではない。基準poseを用意できなければpx比較と人間評価だけを報告し、3m達成を主張しない。夜間・雨天・工事・反射面は失敗群として別記録する。
