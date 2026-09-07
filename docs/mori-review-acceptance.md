# 森JPタワー：採用する形状と取り込み手順

## 人間が確認した範囲

2026-09-07、屋根・壁の欠落を修正した比較画面に対し、Maintainerが開発チャットで「いいですね。次何したらいいですか。」と回答。その後、採用基準の記録、取り込み準備、次Issueの分離を依頼した。

この記録は画像を用いた形状の採用であり、GitHubの正式なApprove reviewを代行したものではない。実寸・地理精度・入口の推定寸法・素材配布権への一括承認でもない。

採用対象：四隅の頂部、暗い青灰色の外装と非発光の縦帯、屋根と壁の欠落を修正した低層部、現在の写真ベースの入口庇・丸柱・フレーム。入口の位置と寸法は推定として保持する。

## 再現可能な参照

- モデルを生成した公開commit：`e6846145424bfe91c65d2ae12dbe3ae6d58bcac8`。
- 採用blend SHA-256：`77752f9009a0f3a1979734e3374de50d933253a5408c99f38297765548969179`。
- [機械可読のreview reference](mori-reviewed-baseline.json)に、入力・archive・patch・カメラ・実行コードのhashを保持する。
- [実行記録](mori-podium-repair-v3-run.json)と[保存後の検証](mori-podium-repair-v3-validation.json)を参照。Pythonテスト22件、Blender統合テスト2ケース、8視点の比較を実施済み。

採用blendと元archiveは、Maintainerのローカル成果物領域へ作業用runとは別に保管し、コピーのhashも確認した。実都市の画像とassetは配布権確認中のためGit repositoryに含めない。参照用blendは現在のrunnerの`--input`に渡す新しい入力ではない。再生成は元の固定原本と累積patchから行う。

今回の文書整理ではBlender生成コードとモデルを変更していない。PRの新headと上記モデルcommitが異なっても、画像の対象を取り違えないよう両者を区別する。

## 取り込み順

1. [PR #2：レビュー基盤](https://github.com/OurJapan/open-tokyo-world/pull/2)をmainへ取り込む。**Create a merge commit**（通常のMerge pull request）を使用し、依存ブランチが参照しているcommitの履歴を保つ。
2. [PR #4：森JPタワーの修正](https://github.com/OurJapan/open-tokyo-world/pull/4)のbaseがmainであること、Checksが成功し競合がないことを確認して取り込む。#2の取り込み前はその基盤commitも#4に含まれる。
3. mainへの取り込み後にIssue #3を完了扱いにする。#4の`Closes #3`で関連付ける。地物の細部や配布権がすべて解決したという意味ではない。
4. [Issue #5：低層部の植栽・手すり](https://github.com/OurJapan/open-tokyo-world/issues/5)を、取り込み済みmainから作った別ブランチで進める。

PR #2をsquash/rebaseで取り込む場合は、#4の依存関係を組み直してから再確認する。現在の簡単な取り込み手順はmerge commitを前提とする。

repositoryのAGENTS.mdにある`Do not merge your own changes.`に従い、Agentは資料整理・検証・Ready for reviewへの変更まで担当し、mergeは人間が行う。

## 未完の作業

正式なライセンス採用と既存素材の配布権確認、独立したContributor環境での再現、入力sceneの分割、全接合部・地理高度・歩行経路の検証、植栽・手すりなどの細部は引き続き課題。M1/M2の全条件を完了したとは記録しない。
