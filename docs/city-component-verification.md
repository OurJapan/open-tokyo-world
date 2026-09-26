# 植栽・車両・設備と材質の照合

対象はPR #12採用の固定した街です。以前の基本形状・配置の検査に続き、残っていた29メッシュと、6分類2,676メッシュの材質割当を調べます。制作元についての[ご本人の記憶](../sources/city-pr12-authorship-notes.json)と、コード・入力からの技術的な照合を別々に記録します。

2026-09-27の[照合記録](../sources/city-pr12-component-verification.json)では、29メッシュの形状・変換・smooth・材質割当と、31材質のノード設定が一致しました。材質割当は6分類の2,676メッシュ全件を確認しています。元の街と固定入力のhashは変わっていません。

生成直後には9メッシュのBevelの `show_render` だけが異なりました。固定コミットの `work/camera_options/render.py:14–17` にある無効化ルールを作業用メッシュへ適用すると、この設定も一致します。`work/preview30/render.py:12–14` にも同じルールがあります。どちらを過去に実行したかの確定ではなく、保存状態を再現できる後段処理を特定した結果です。collectionやobjectの非表示設定は再現・変更していません。

中間段階では、元樹冠3,313本のうち近景479本を縮小し、選別後2,082本を保持する処理が保存版と一致しました。車両593台分、街灯308灯分、窓1,632枚分を生成し、窓の入力となる144組の面も保存記録と一致しました。これらは制作処理上の件数で、現地調査による実数ではありません。

## 再実行

[固定コードと入力](city-input-recovery.md)を用意し、今回使用する前段モデルも共通フォルダーへ取り込みます。`--include-scenes` により、前段blend5本（計約2.76GB）もhashを確認してコピーします。

```powershell
.\otw.ps1 fetch-production
.\otw.ps1 import-production-inputs --input 'C:\Received\legacy-project' --include-scenes
& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' --factory-startup --disable-autoexec --background data/local/assets/tokyo-city-pr12/city.blend --python-exit-code 1 --python scripts/verify_city_components.py -- --output data/local/audits/components-new.json
```

Blender 4.5.1 LTSに付属するPython・NumPyを使います。前段モデルはcinematic、environment、street-detailの3本を読み、元ファイルへ保存しません。旧コード8本の全体hashと、実行する文単位の範囲を固定しています。旧制作処理の保存・レンダリング・外部プロセス起動や、埋め込みTextは実行しません。

| 対象 | 再生成・確認する内容 |
|---|---|
| 旧樹冠4メッシュ | cinematic版から3,313本分の元樹冠を読み、複数の葉塊へ再生成。近景の葉塊縮小を再現し、回収した道路重なり判定で選別する |
| 樹皮・植樹帯の土2メッシュ | 選別した樹木の中心と街路樹配置から生成する |
| 交通等14メッシュ | 車両593台分を材質ごとに統合する。分類には植樹帯の縁1メッシュも含まれ、14台を意味しない |
| 街灯1メッシュ | 保存OSMと建物範囲の台帳から配置・形状を再生成する |
| 近景設備8メッシュ | 蓋・排水口・車止め・点字ブロックと窓枠等。窓の元になる前段モデルの面のグループも回収入力と比較する |
| 31材質と2,676メッシュの割当 | 原コードの数式材質を再生成し、材質名・ノード・設定・割当を比較する |

窓枠等の生成には前段の建物形状を使います。旧処理が写真から推定した建物壁面の6色パレットは、上記8メッシュの材質に含まれません。再実行中の壁面スロットには作業用の仮材質を使い、その壁面の材質や画像の照合・許諾を確認済みとは扱いません。

## 検査の範囲

形状は頂点座標、面の構成、面の材質番号、UV、smooth設定を比較します。29オブジェクトのワールド変換とBevel設定も比較し、親・制約・アニメーション・形状キー・カスタム法線などの対象外の依存があれば停止します。

材質は、使用している8種類のノードについて、入出力の既定値、リンク、Noiseの方式・座標変換、ColorRampの色と位置、Bump、半透明シェーダー、材質とCyclesの設定を比較します。ノードの画面上の位置や選択状態は対象外です。画像・ノードグループ・アニメーションや対象外のノードは無視せず停止します。これは観測した手続き生成材質の検査であり、任意のBlender材質に対応する一般的な検証器ではありません。

検査コード自体も、Noiseの方式、色の変化、入力値、Bevel幅とレンダリングの有効・無効、smooth設定、位置の変更を実際のBlender上で検出する小さなfixtureで確認します。

```powershell
python -m unittest discover -s tests
& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' --factory-startup --disable-autoexec --background --python-exit-code 1 --python tests/components_blender.py
```

表示状態、全画角の見た目、実在との精度や、全都市を原資料から再構築する工程は別の確認です。元の街に保存された非表示設定も、この照合によって変更しません。

## 配布候補を分ける

最初の候補は、街路樹6バリエーションの幹・葉12メッシュと低木4メッシュ、数式材質31種です。基本形状のローカル座標と新しい展示用配置だけを取り出し、街の配置座標・地図・建物・旧スクリプトを含めません。これはローカル確認用の候補で、許諾確定や公開済みパッケージではありません。

[候補の固定台帳](../manifests/procedural-components-distribution.draft.json)に全16部品・31材質の名前とhash、除外範囲を記録しました。2026-09-27に作成した `data/local/candidates/procedural-components-20260927/kit.blend` は9,844,090 bytes、SHA-256 `78ea637f9b154274c62fd20160995b649139c191a09056f8696ec5baee10595a` です。別プロセスで16形状・31材質を照合し、画像・外部library参照・埋め込みTextがすべて0件で、1200×850の確認画像も生成できました。6種類の木と4種類の低木が画面内に収まることを確認しています。残りの塗装・灯具等の材質は、対応する街の集約形状を含めず材質データだけ保持しています。

この確認は同じWindows PCで行いました。通常テストは150件中145件成功・5件スキップ、上記のBlender fixtureも成功しています。

検証結果から候補を作り、別のBlenderプロセスで保存後の形状・材質・外部依存を検査します。次の `components-new.json` は上の検証で成功した出力、`procedural-components-new` は未使用の出力先です。

```powershell
& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' --factory-startup --disable-autoexec --background data/local/assets/tokyo-city-pr12/city.blend --python-exit-code 1 --python scripts/prepare_procedural_candidate.py -- build --report data/local/audits/components-new.json --output data/local/candidates/procedural-components-new
& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' --factory-startup --disable-autoexec --background data/local/candidates/procedural-components-new/kit.blend --python-exit-code 1 --python scripts/prepare_procedural_candidate.py -- verify --output data/local/candidates/procedural-components-new --render
```

`kit.blend`、`candidate.json`、`verification.json` と `preview.png` ができます。描画はCycles CPUで、GPU設定の変更は不要です。元の街と候補のhashを記録し、元ファイルへ保存しません。候補は生成済み形状と数式材質を内蔵していますが、別PCでの実機確認と公開取得先はまだありません。

一方、29の集約メッシュは地図から推定した位置や前段の建物形状を含みます。基本形状と同じ配布範囲には含めず、地図・建物入力と加工経路の整理を続けます。OSMの利用には出典とODbLへの案内が必要です。[OSM公式案内](https://www.openstreetmap.org/copyright)

候補の独自部分は、既存の独自資産と同じCC BY 4.0を提案します。この条件では出典・変更表示を伴う改変や商用再配布が可能です。適用には、ご本人が許諾できる範囲であることと、その範囲への許諾意思を確認します。[CC BY 4.0公式案内](https://creativecommons.org/licenses/by/4.0/)
