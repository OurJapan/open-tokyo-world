# iPhone Web AR 技術調査

確認日：2026-09-07。公式文書・仕様に基づく机上調査。端末の実測結果ではない。APIが仕様に存在することと、そのiOS版で正常に動くことは区別する。

## 推奨

HTTPSの同じURLからSafariで`getUserMedia + Geolocation + DeviceOrientation + WebGL`を使う。表示・撮影・投稿を同じDOM内で完結させる。カメラへ描けることと現実に固定できることは別の成功条件とする。画像補正は[別工程](visual-localization.md)で検証する。

## APIとプラットフォーム差分

| 機能 | iPhone Safari | Android Chrome | PoCの扱い |
|---|---|---|---|
| getUserMedia | HTTPS・ユーザー許可。背面cameraを要求可能 | 同様、端末/カメラ選択差あり | 共通主経路。音声は要求しない |
| Geolocation | 位置許可が必要。精度/高さは可変・欠損あり | 同様 | 周辺取得と初期位置。測量値扱いしない |
| DeviceOrientation / Motion | `requestPermission`があればユーザー操作から呼ぶ | API/permission実装差を吸収 | Euler値・絶対方位・実イベントを検出 |
| WebGL | cameraとは別に描画。WebGL2 contextの成功を確認 | 同様 | Three.jsの採用版を固定、context lossから復帰 |
| WebGPU | Safari 26で導入されたが端末/API成功を検出 | 対応GPU・OS差あり | 最小PoCの必須条件にしない |
| WebXR immersive-ar | 本調査では一般iPhone向け標準対応の公式根拠を確認できず、依存不可 | 対応ARCore端末で利用可能 | Android追加adapter。`isSessionSupported`で判定 |
| ARKit / ARCoreのnative pose | Webページからnative SDK相当を直接取得できる前提は不可 | WebXRで一部提供、native機能全部ではない | 生camera intrinsics / depth / geospatialの同等性を仮定しない |
| AR Quick Look / USDZ | SafariリンクからOSのAR表示へ | 同じQuick Lookはない | 単体assetプレビューのみ |

根拠：[WebKit getUserMedia](https://webkit.org/blog/7763/a-closer-look-into-webrtc/)、[Media Capture仕様](https://www.w3.org/TR/mediacapture-streams/)、[Geolocation仕様](https://www.w3.org/TR/geolocation/)、[Orientation仕様](https://www.w3.org/TR/orientation-event/)。HTTPSやpermissionだけでセンサー値取得を保証しないため、許可結果とイベント到着を別々に扱う。

WebKitの[Safari 26.2説明](https://webkit.org/blog/17640/webkit-features-for-safari-26-2/)はSafari 26のWebGPU導入と、**visionOS**のWebXR/WebGPUを説明している。iPhoneのAR対応と取り違えない。[Apple engineerの回答](https://developer.apple.com/forums/thread/756850)は2024年の非対応回答であり、2026年の新規保証ではない。今回確認した公開資料にiPhone immersive-arの正式提供を裏付けるものはない、という保守的な判断である。実装時に通常設定の実機で再確認する。

Androidについては[Google WebXR](https://developers.google.com/ar/develop/webxr)がChrome/ARCore経路を説明している。[ARCore Geospatial](https://developers.google.com/ar/develop/geospatial)のnative向け機能をWebXRから当然呼べるとは扱わない。iPhoneのChromeもAndroid Chromeと同じ能力とは仮定せず、ブラウザ名ではなく実APIを検出する。

## App Store申請を使わない方式の比較

| 方式 | URLだけで開始 | 自動の地理整合 | 撮影/Feedback統合 | 判断 |
|---|---|---|---|---|
| Safari camera + WebGL | 可、権限操作は必要 | GPS/方位は粗い。VPSを追加可能 | 同一ページで制御可能 | 主経路 |
| Quick Look + USDZ | 可、OS viewerが開く | 表面配置。都市の既知地理位置への自動固定を保証しない | DOM外。自由なcamera/pose取得不可 | 補助 |
| Android WebXR | 対応端末で可 | local trackingのみでは世界座標が定まらない | DOM overlay等は能力差あり | 後続 |
| AR.js / LocAR | 可 | GPS型。高精度VPSではない | 自前UIで可能 | センサー処理の比較対象 |
| image/marker tracking | 可 | 見つけた既知target基準 | 可能 | 人工marker設置や対象を狙う摩擦が今回と合わない |
| Web向けSLAM engine | 配布条件と対応端末次第 | local 6DoFと地理位置の結合は別途必要 | SDK制約次第 | 継続追跡の追加調査 |
| native ARKit / ARCoreアプリ | 通常のWebだけでは完結しない | 高度なAPIを使用可能 | アプリ実装 | 今回の対象外 |

[AR.js公式](https://ar-js-org.github.io/AR.js-Docs/location-based/)と[LocAR examples](https://ar-js-org.github.io/locar.js/index.html)は再利用候補。ただし既存の投影をそのまま使うとOTWの座標契約と二重変換し得る。camera/姿勢adapterだけを比較し、地理frameはOTW契約に統一する。

**サービスの古い推奨に注意**：[8th Wall公式FAQ](https://8thwall.org/docs/migration/faq)によれば2026-02-28に旧hosted platformの編集アクセスが終了。self-host用engine binaryと公開コードの範囲は異なり、Niantic Spatial VPSは配布binaryに含まれない。旧Lightship VPS for Webの新規採用を最短経路にはしない。binaryの現行licenseと対応端末を確認できればlocal trackingの比較対象にはなる。

## Safariの開始と復帰

1. URLを開くと通常3D Viewerと「現地で見る」を表示。権限要求をページ読込時に乱発しない。
2. タップの直接handlerから、存在する`DeviceOrientationEvent.requestPermission()`、必要な場合のMotion permissionを開始する。先に長いcamera/GPS待ちを挟んでuser activationを失わない。各許可は個別結果として記録。
3. cameraは`audio:false`、背面`facingMode:{ideal:'environment'}`、初期1280×720以下を要求。実際のtrack settings/videoWidth/videoHeightを確認。`video`に`playsinline`と`muted`を付け、play拒否なら開始ボタンを表示。
4. `watchPosition`とorientationイベントを受け、位置・姿勢が揃うまでは通常Viewerまたは「位置推定中」。permission grantedだけではAR準備完了としない。
5. 精度が悪ければ「概略表示」。地物が現実と異なる方向へ固定されたように見せない。方位が取れなければ通常Viewerと撮影を維持する。
6. 非表示・画面lockでカメラと高負荷処理を停止し、復帰時は古いposeを無効化して再取得する。横向き変更、レンズ変更、解像度変更ではintrinsicsと画像cropを更新する。

SNS内browserはcamera・センサー・別画面遷移が異なるため、Safari/Chromeで開く案内とURLコピーを用意。SNSアプリ全てで直接動作する保証は成功条件にしない。permission拒否後も投稿下書きを失わず、端末設定からの再許可後に再開できる。

## 精度・投影・撮影の落とし穴

GeolocationはGPS専用APIではない。`enableHighAccuracy`は要求であって精度保証ではなく、位置のtimestampとaccuracyを保持する。`heading`は移動方向であり、停止したカメラの向きではない。高度がnullならunknownのまま保存する。

Orientationのalphaをそのまま北基準yawとしない。`absolute`、実装固有heading、画面回転、背面camera軸、磁北/真北基準を区別し、基準が不明ならunknown。Motion加速度の二重積分を歩行位置の代替にしない。磁気擾乱・bias・時刻同期のない統合はドリフトする。

GPSの仮想誤差10mは50m先で`atan(10/50)=11.3°`、100m先で5.7°に相当。幅390 CSS px、横FOV 60°の仮定では中心付近で各約68px、34pxずれる。方位誤差5°だけでも約30pxずれる。これは仕様の精度値ではなく、位置合わせ要求を説明する幾何計算。

HTML videoの`object-fit:cover`はcropを生む。cameraのK、video→canvas→表示領域の変換を合わせ、letterbox/鏡像/端末回転を保存する。getUserMediaの標準settingsから校正済みKが必ず得られるわけではない。FOV仮定は見た目の調整に留め、精密poseに使うときは校正誤差を測る。

写真はvideoの生フレームと合成previewを別assetにする。VPS/AIには原則として3D overlayのない画像を渡す。canvas撮影はCORS・同一originを満たすassetで行い、tainted canvasを処理する。合成画像だけではモデルを現実と誤認し得る。

## Quick Lookの範囲

[Apple Quick Look](https://developer.apple.com/documentation/ARKit/previewing-a-model-with-ar-quick-look)はUSDZ / realityを表面に配置し移動・拡縮する経路を提供し、`a rel="ar"`から起動できる。ページの自由なUIをAR画面へ載せる、camera poseを継続取得する、撮影画像を任意のObservation APIへ直接送る汎用bridgeとは説明されていない。custom actionを付けても完全なcamera session制御にはならない。

[model-viewer](https://modelviewer.dev/examples/augmentedreality/)は単体モデル表示とAR経路の振り分けに有用だが、都市VPSを提供するものではない。Quick Lookは遠隔利用者の単体プレビューへ限定し、Reality Feedback主経路を置き換えない。

実機ケース・合格基準は[poc-plan.md](poc-plan.md)に集約する。
