# スターターの固定版を使う

初版は [Plaza Starter v0.1.0 — preview](https://github.com/OurJapan/open-tokyo-world/releases/tag/plaza-starter-v0.1.0) です。広場6部品の比較画像・検証結果・生成ソースを約1.14 MBのZIPで取得できます。東京・日本全体の完成版ではありません。

## ダウンロードして見る

1. 上のページの Assets から `ourjapan-plaza-starter-v0.1.0.zip`、`release.json`、`SHA256SUMS.txt` を同じフォルダーに保存します。GitHubが自動生成する「Source code (zip)」はリポジトリのソースで、比較画像入り配布物とは別です。
2. ZIP全体を展開し、`review.html` をブラウザで開きます。画像を見るだけならPython・Blenderは不要です。
3. 再生成したい場合は同梱READMEを読み、展開先の `source` フォルダーから記載のコマンドを実行します。PythonとBlenderが必要です。出力先には新しいフォルダーを指定します。

ダウンロードの整合性はPowerShellで確認できます。

```powershell
Get-FileHash .\ourjapan-plaza-starter-v0.1.0.zip -Algorithm SHA256
Get-FileHash .\release.json -Algorithm SHA256
Get-Content .\SHA256SUMS.txt
```

表示されたハッシュをチェックサムの対応行と比較します。ZIPの期待値は `308eb5c1b8597b81a9bafbd3cec815c5bb38d5ac5b0cf7c0dd52cb92f3115116` です。不一致なら利用を止め、再取得して確認してください。チェックサムは破損や差し替えの検出用で、著者の電子署名ではありません。

初版のソースcommitは `31e2d3c12b9986e4f40831b3392d3b2173389f32`。機械可読の台帳は [release-v0.1.0.json](release-v0.1.0.json) です。正確な同梱ファイルのバイト数とハッシュはZIP内の `inventory.json` にあります。ソースとGit commitの照合ではCRLF/LFの違いを正規化しています。

対象ソースはMIT、対象6部品とプレビューはCC BY 4.0です。同梱のLICENSE・NOTICE・provenanceを確認してください。都市の .blend、建物本体、第三者写真やテクスチャは含みません。Windows / Python 3.12.14 / Blender 4.5.1 LTS / CPUで再生成済みですが、別OSと初参加者による確認は未実施です。

## 更新と以前の版への戻し方

- バージョンは部品群ごとに付けます。`plaza-starter-v0.1.0` は広場スターターの版で、日本全体の品質宣言ではありません。
- 公開したタグと配布ファイルは通常差し替えません。修正版は新しい番号（例：`plaza-starter-v0.1.1`）で公開し、変更点・検証・制約を記載します。
- 再現・報告には正確な版番号とハッシュを使います。`main` や `latest` は更新されるため、同じ結果を再現する指定には使いません。
- 更新前の版も保持します。不具合時は以前の版のページからZIPを取得し、ハッシュを確認して別フォルダーに展開します。編集したファイルに上書きしません。報告には問題の版と正常だった版を記載します。初版時点では戻れる旧リリースはありません。
- 権利侵害・重大な安全上の問題で公開停止が必要な場合は、理由と代替版を記録します。黙って同じファイルを差し替えません。

## 運営の公開手順

1. 別ブランチの変更を検証し、比較画像を人間がレビューしてPRをマージします。AIは自分のPRをマージしません。
2. マージ済みの正確なcommitを記録し、そのソースから生成・再オープン検証・レンダリング・パッケージ化します。既にレビュー済みのパッケージを使う場合も、同梱ソースがそのcommitと一致することを確認します。
3. `python -m unittest discover -s tests`、ZIPのCRC・全ファイルハッシュ、同梱ソースからの再生成を確認します。ライセンスと公開対象も確認します。
4. 新しい版番号を決め、ZIP・版情報JSON・チェックサムを用意します。版情報にソースcommit、パラメーター、ツール版、検証、利用範囲と未確認事項を残します。
5. 個人アカウントの権限でOurJapanのReleaseを作成します。タグの対象は記録したcommitに固定します。必要ならDraftで全ファイルをそろえて確認し、プレビューにはPre-releaseを付けて公開します。
6. 公開URLから全3ファイルを再取得し、手元とのバイト一致とタグのcommitを確認します。版情報をリポジトリ台帳にも残し、人間レビューのPRで案内を更新します。

## 保存先と容量

現段階ではコード・台帳・手順を通常のGit、比較ZIPをGitHub Releasesに保存します。小さなスターターのために新しい有料ストレージ契約は追加しません。巨大な都市ファイルや全レンダー履歴の無制限保存は、この初版の対象外です。

GitHub Releasesの添付は1ファイル2 GiB未満で、リリースごとの添付数などにも上限があります。[公式の制限](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)を公開前に確認します。都市データ配布が必要になった段階で、地域・部品・版ごとの分割、外部オブジェクトストレージ、取得量と保存期間の予算を設計します。

「既存版を差し替えない」は現在の運用方針です。この作業ではGitHubのimmutable release設定を有効化していません。通常のReleaseは管理者が編集・削除できるため、技術的な改変不能を保証しません。[GitHubのリリース管理](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository)を参照してください。

公開した3ファイルはローカルにも保存しますが、同じPC上のコピーは独立したバックアップではありません。別媒体・別サービスへのバックアップと復元訓練は今後の課題です。
