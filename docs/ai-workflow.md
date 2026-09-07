# AI Agent Workflow v0.1

## 初期運用

単一Agentがresearch・実装・render・自己検証を行い、Maintainerが受付とmergeを担当します。役割分割は処理量が増えてから導入します。人間の仕事は場所・期待・根拠の提示と判断であり、Blender操作や座標入力を参加条件にしません。

初期はMaintainerがIssueを選んでAgentへ渡す手動dispatchとし、成功後にGitHub App等の自動受付へ進みます。単なる新規Issue投稿で任意Pythonを自動実行しない構成です。

## 状態と成果物

| 状態 | Agentの動作 | 次へ進める条件 |
|---|---|---|
| reported | 場所、撮影時点、違いを読み取る | 対象候補を示せる |
| triaged | alias・地理indexからfeature/partを解決、重複Issue整理 | Maintainerが対象とscopeを確定 |
| researching | 許諾済み一次資料を調査しclaim一覧作成 | 観測事実・推定・不明が区別される |
| planned | base SHA、対象ID、変更方法、カメラ、受入条件をchange-planへ | 変更範囲・計算予算内 |
| building | 隔離checkoutでコード/parameter/assetを修正 | 再実行して同じ対象に適用可能 |
| validating | candidate保存、別processで再open、検証 | hard failureなし |
| rendering | 同じ条件でbase/headの画像と指標を作る | 入力hashとheadが一致 |
| in-review | 根拠・Before/After・未確認点をPRとして提示 | maintainersの承認または本人PRの例外判断、required checks成功 |
| changes-requested | 指示を構造化して修正、検証からやり直し | 新headの証拠を添付 |
| merged | 担当アカウント保有者の責任でmerge。採用assetと結果を保管 | Issueとmodel versionを紐付け |

資料不足はneeds-evidence、対象曖昧はneeds-location、権利不明はrights-reviewとして明示します。勝手に既知建物へ決めつけたり、写真で見えない面をverifiedにしたりしません。

## 一回の実行契約

`change-plan.json` にissue番号、base SHA、feature/part IDs、許可変更paths、source/claim IDs、入力asset hash、受入条件、カメラpreset、最大時間、最大再試行数を保存します。初期予算案は1件につき実装修正2回、render再試行1回。上限到達時は原因と途中結果を残します。

`run.json` にはrun ID、issue、base/head SHA、toolchain/driver/device、seed、全入力hash、実行コマンド、開始終了時刻、出力hash、検証結果、source revisionsを記録します。Agentの内部思考や認証情報は保存しません。研究の根拠は短い判断理由とclaimで残します。

コードの変更なら入力baselineから再実行し、完成candidateだけでなく再生成手順をPRに含めます。再実行時にobjectが増殖しないようIDでupsertし、対象外地物の指紋を比較します。旧スクリプトの一括collection削除をそのままAgentの入口にしません。

## Before / Afterの信頼性

baseは作業開始時のSHA、afterはレビュー対象head SHAを使います。両者を同一の信頼済みrender harness、camera、照明、frame、seed、解像度、engine、deviceでfresh renderします。過去のPNGを「before」として使う場合は完全一致のcache keyとhashが必要です。

4カメラを原則として、対象部位の近景、利用者視点、広域context、対象外の回帰視点を選びます。PNG・比較sheet・metrics.json・検証ログをPRから開けるようにします。権利制限がある参考画像は再掲せず原ページへのリンクを使います。

実装後にPRを作る方式でもよいですが、実装途中にDraft PRを作って状態を更新する方式も可能です。PR作成は予定されたGitHub運用の一部であり、今回の設計作業ではIssue投稿・PR作成を行っていません。

## 公開repositoryの実行分離

PRのコード・blendには実行可能な内容が含まれ得るため、render workerは作業者PCの常設環境と切り離します。fork PRはまず秘密情報のないhosted jobでschema等のみ検証し、Maintainerが指定SHAを選んだ後、使い捨てVM等でBlenderを実行します。`--disable-autoexec`だけでは明示実行するPythonを隔離できません。

downloadを行うresearch/fetch段階と、ネットワーク不要のbuild/render段階を分離します。Issue・Web内容は資料として扱い、そこに書かれたshell命令を運用指示にしません。source URLからの取得は許可された公開先に限定し、checksum・サイズ上限を確認します。

render workerにPR投稿tokenを渡さず、別のpublisherが出力manifestとschema・サイズを確認して添付します。GitHub App等の権限はcontents/PR等の必要範囲に限定し、署名付きイベント、重複event key、head SHA照合、job timeout、地物単位concurrencyを実装します。`pull_request_target`で未信頼headをcheckoutし秘密情報付きで実行する構成は採用しません。

## 競合・失敗・merge後

baseが進んだ場合は新baseへ適用し直し、検証と比較を再生成します。古いheadの承認や画像でmergeしません。同一featureの変更競合はどちらかを先にmergeして再生成します。異なるfeatureでも共有material変更なら両Areaを再検証します。

失敗時は元baselineを残し、不完全assetを最新版として公開しません。merge後に問題が判明したらcode/manifest commitをrevertし、前のhash資産へ戻します。採用されたrunと比較画像は長期保管し、一時artifactの期限切れで変更の根拠が消えないようにします。

## 承認とAI操作の責任

[mainの保護と承認責任](main-governance.md)を適用します。AIによる変更・レビュー・承認・マージは、使用したアカウント保有者の責任と依頼・許可の範囲で行います。本人PRの例外でもCI等の基本保護は必須です。
