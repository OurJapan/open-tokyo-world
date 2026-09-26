# 地区ごとに取得し、同じ構成を再現する

参加者の入口は `otw.ps1` にまとめ、都市データは地区と共通素材に分けます。選択した地区が必要とするパッケージだけを取得し、版・サイズ・SHA-256・Blender版・実行コードを固定した構成ファイル（lock）を残します。

現在登録している地区は **森JP周辺** です。公式PLATEAUの固定1タイルを使い、森JPの詳細モデル・周囲23棟・広場6部品を再生成します。採用済みの街全体を切断したものではありません。東京タワー、道路、地形、旧都市の植栽配置は含みません。範囲は既存の生成対象に基づき、地理的な境界ポリゴンは未確定です。

共通素材として、許諾済みの樹木・低木16部品と31材質を登録し、[v0.1.0プレリリース](https://github.com/OurJapan/open-tokyo-world/releases/tag/procedural-components-v0.1.0)で公開しました。`--common procedural-components` を指定すると取得できます。地区を選んだだけでは自動取得しません。

## 森JP周辺を準備する

Blender 4.5.1 LTSとコードの用意は[共通の制作環境](contributor-workspace.md)を参照してください。リポジトリのルートで実行します。

```powershell
.\otw.ps1 district list
.\otw.ps1 district plan --district mori --output build/locks/mori.json
.\otw.ps1 district setup --lock build/locks/mori.json
.\otw.ps1 district verify --lock build/locks/mori.json
.\otw.ps1 district edit --lock build/locks/mori.json --open
```

`plan` は取得予定のファイル、必要な転送量、再利用できるキャッシュ、入手できない素材を表示します。ネットワーク通信やモデル生成は行いません。新しいlockだけを保存し、既存のlockは上書きしません。森JPだけを新規取得する場合、公式入力の合計は **1,658,929 bytes** です。これは転送する入力の容量で、生成モデル・編集コピー・一時領域・Blenderのメモリ使用量を含みません。

`setup` は必要なファイルを取得・照合してから、既存の森JP生成処理で保存・別プロセスでの再読み込み・4視点の比較描画を行います。同じ構成の生成済みモデルがあれば、そのハッシュと読み込みを再検査して再利用します。共通素材を追加しただけでは森JPを再生成しません。

`verify` はパッケージと、そのlockで生成済みの地区ファイルを照合します。未生成でもパッケージの検証は可能で、`built_districts` に生成済みの地区だけを表示します。Blenderによる再読み込みを含める場合は `setup` を再実行してください。現実との一致の検査とは別です。

`edit` は一つの地区を選んだlockに対して、毎回新しい編集用コピーを作ります。サブフォルダー、出典、ライセンスを保持し、元モデルとキャッシュは編集しません。`--open` がなければ保存先だけを表示します。編集結果の採用には[レビュー手順](review-harness.md)に沿った確認が必要です。

Blenderを起動せず取得だけ先に行う場合は、`setup` を `sync` に置き換えます。別Pythonからは `python scripts/workspace.py district ...` と同じ引数を使えます。

## 共通素材を追加する

森JP周辺と共通素材を公開URLからまとめて取得する場合：

```powershell
.\otw.ps1 district plan --district mori --common procedural-components --output build/locks/mori-with-trees.json
.\otw.ps1 district setup --lock build/locks/mori-with-trees.json
```

共通素材だけなら `--district mori` を省略できます。取得済みZIPを使う場合は `--source-dir 'C:\Received\packages'` を追加します。探すファイル名は `procedural-components-v0.1.0.zip` です。指定フォルダーの直下、または `procedural-components/` 配下だけを調べます。無関係なフォルダーを検索しません。複数の入力フォルダーは `--source-dir` を繰り返して指定できます。

今後、公開URLも明示したローカルファイルもなく、キャッシュにもないパッケージを選ぶと、**ダウンロード開始前に停止**します。共通素材を省略して成功したように表示することはありません。URLは台帳で管理し、認証不要のHTTPS取得と固定ハッシュの照合を行います。

森JPと共通素材を両方初めて用意する場合、固定入力・ZIPの合計は **12,064,491 bytes** です。ZIPを手元から指定すれば、その10,405,562 bytesはローカルコピーとして扱います。共通素材の `kit.blend` は独立したライブラリとして表示し、BlenderのAppendで利用できます。街への自動配置や地区間の自動結合は行いません。

ネットワークを使わず再利用・取り込みする場合は `--offline` を付けます。必要なデータがなければ停止し、自動で通信へ切り替えません。

## 同じ構成を共有・更新する

1. 協力者同士で同じコードのcommitまたはタグを使用します。
2. `plan --output` で作ったlockを渡します。lockには個人PCの絶対パスや認証情報を含めません。素材本体は別途取得します。
3. 相手は `setup --lock PATH` を実行します。入力はバイト単位で照合し、生成前に実行コードのLF正規化ハッシュを照合します。コードが違う場合は対応する版への切り替えを案内して停止します。
4. 更新時は新しいlockを作り、旧lockと旧パッケージを保持します。旧版を再現する際は、対応するコードと旧lockを使います。編集中のコピーを更新で上書きしません。

取得先URLをコンテンツの識別とは分離しています。GitHub Releasesから別のHTTPSストレージへ移す場合も、同じ版・内容・ファイルハッシュならキャッシュと構成IDを再利用できます。新しい台帳に登録された取得先も、旧lockの内容と一致する場合だけ使用します。内容が違うURLからの取得は照合で停止します。lockのIDは署名や配布許諾の証明ではありません。

森JPの実行設定は、runner・出力名・メッシュ数・入力のNOTICE・実行環境を明示して固定します。取得先の公開情報など、生成に使わない台帳項目の更新では地区の構成IDを変えません。コード・データ・Blender版を揃える仕組みで、別PCで生成したblendや描画結果のバイト単位一致、GPU性能、地理精度を保証するものではありません。

## 保存先と拡張

```text
manifests/district-distribution.json   地区・依存パッケージ・取得先の台帳（Git）
data/local/distribution/              取得済みデータ（Git対象外）
  blobs/sha256/                      ハッシュ単位の共通キャッシュ
  packages/<id>/<version>-<hash>/     固定版の展開済みファイル
  locks/                             使用した構成
  builds/<district>/                 構成に対応する生成モデルの記録
data/local/builds/                   森JPなどの生成結果
data/local/edits/                    個別の編集用コピー
```

同じ素材を複数地区が参照しても、ダウンロードはハッシュ単位で一度です。ファイルは一定量ずつ読み書きし、大型ZIP全体をメモリへ読み込みません。ZIP全体と展開後の全ファイルを照合し、欠落・余分なファイル・重複名・フォルダー外への展開を拒否します。壊れた既存データは自動上書きしません。失敗した取得の一時ファイルは残さず、検証済みの取得済みファイルは次回に再利用します。

地区を増やす場合は、安定した地区ID、範囲、座標の定義、必要パッケージを台帳に登録します。`requires` が共通依存を指定し、`--district` は複数指定できます。合成データのテストで、二地区が同じ共通素材を参照する場合を確認しています。

生成済みの地区モデルには `blend-package-v1` アダプターがあり、固定ファイル一覧と `scene`・`expected_meshes` を持つパッケージを地区として開けます。画像の同梱・外部library参照の不在を検査します。これは画像/library参照の検査であり、全種類のシミュレーションキャッシュやフォント等を網羅するものではありません。新しい地区ごとに実モデルの出典、依存、形状・座標・境界を検証し、出典表示をパッケージに同梱してください。任意のコマンドを台帳から実行する機能はありません。

地物の所有地区・部位・配置・変更影響は[既存のobject registry](object-registry.md)の担当です。この配布台帳はファイル単位の取得・固定・準備を担当します。実都市registryからの自動選択、既存都市の空間分割、地物の自動組立、LODの生成・切り替えは未接続です。地理的な境界を跨ぐ地物を無条件に切断しません。

配布先は当面GitHub Releasesを想定します。ファイル容量・更新頻度・配布量に応じて保存先を変更できる構成ですが、新しいストレージ契約やRelease公開はこのコマンドでは行いません。[Releaseの運用手順](../starter/plaza/releases.md)を参照してください。

## 検証

```powershell
python -m unittest discover -s tests
```

地区選択、共通依存、循環検出、部分取得、オフライン再利用、破損・中断、ZIP照合、旧版保持、URL移行、コード・実行設定の不一致、生成済み地区の再利用、編集コピーを検査します。初版の実データ実行は[検証記録](district-distribution-verification.json)、公開後の匿名取得と地区セットアップは[公開取得の検証](../assets/procedural-components/public-download-verification.json)に残します。
