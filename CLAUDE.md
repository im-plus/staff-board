# staff-board (社内スタッフボード + 機材予約)

株式会社インプラス（implus）の社内ツール。Claude Code や ChatGPT 等の AI アシスタントがこのフォルダで作業する際の前提情報をまとめた文書。

## このドキュメントの目的

- フォルダ内のファイルだけでは把握できない **運用上の前提・外部依存・歴史的経緯** を記録する
- 別の担当者・別のAIアシスタントが後から作業する際のコンテキストとして使う

---

## プロジェクト概要

| 項目 | 内容 |
|---|---|
| **用途** | 社員の在社/外出ステータスボード + 機材予約ガントチャート |
| **技術** | 静的 HTML + Vanilla JS（ビルドプロセスなし）+ Supabase |
| **ホスティング** | Vercel (GitHub main ブランチから自動デプロイ) |
| **本番URL** | https://staff-board-pearl.vercel.app |
| **リポジトリ** | https://github.com/im-plus/staff-board （**Public**） |

## ファイル構成

| ファイル | 役割 | リポジトリ管理 |
|---|---|---|
| `index.html` | スタッフステータスボード UI | ✅ |
| `equipment.html` | 機材予約ガントチャート UI | ✅ |
| `config.js` | Supabase 接続情報（URL + publishable key） | ✅（2026-04-24〜） |
| `config.example.js` | 設定サンプル | ✅ |
| `.gitignore` | （現在は空） | ✅ |
| `jobcan-sync.py` | ジョブカン打刻→Supabase同期スクリプト | ❌ untracked（後述） |
| `CLAUDE.md` | このドキュメント | ✅ |

---

## デプロイフロー

**`main` ブランチに push → Vercel が自動検知してデプロイ（1-2分）**

- ローカルに `vercel.json` 等の Vercel 設定ファイルは**ない**（Vercel 側で GitHub 連携設定）
- Vercel プロジェクト: `im-plus' projects` org → `staff-board`
- 別ドメイン（独自ドメイン）は未設定、`*.vercel.app` で運用

### 過去のデプロイトラブル（2026-03-09〜2026-04-24）

`1b2f231 fix: Supabaseキーをconfig.jsに分離し.gitignoreで除外` commit 以降、Vercel デプロイが Blocked になっていた。

**原因**: config.js を `.gitignore` で除外 → リポジトリに config.js が存在しない → Vercel が `<script src="config.js">` を読み込めず本番サイトが壊れる状態。

**修正（2026-04-24）**: `.gitignore` から config.js を削除し、config.js をリポジトリに含める方針に変更。Supabase の publishable key は元々ブラウザに配布される前提のため、リポジトリ同梱で問題なし。

---

## 運用モデル（重要）

### アクセス方法

- **PC ブラウザ**: 社内から開く
- **スマートフォン**: 社員が**外出先から**ステータス確認・変更に使用（必須用途）
- URL を知っている人は誰でもアクセス可能（認証なし）

### セキュリティ方針

- **リポジトリは Public**（意図的）
  - Supabase の publishable (anon) key はブラウザに配布される仕様 → 隠蔽に実質的な意味がない
  - 社内ツールだが機密情報を扱わないため、Public で運用
- **RLS はオフ**（意図的）
  - publishable key を持つ人（=サイト閲覧者全員）が全テーブルの CRUD 可能
  - 社内ツールとしての利便性優先
  - データが破壊されても即復旧可能な粒度の情報のみ保持

### これはセキュリティホールではないか？

- 悪意のあるユーザーがデータを削除する理論的リスクはある
- しかし **URL を知らない外部者が偶発的に到達する可能性は低い**
- 社内用の軽い運用として許容されている（2026-04-24 時点のユーザー判断）
- 将来的に RLS + 認証を導入する可能性はあるが、**現状の仕様を勝手に変更しない**

---

## Supabase プロジェクト

| 項目 | 値 |
|---|---|
| Project | `staff-board` |
| Organization | `implus-internal` （**Free** プラン） |
| Account | `implus0605@gmail.com` |
| Region | ap-northeast-1 (Tokyo) |
| project-ref | `ehitufdlbrrjpyivrfod` |
| URL | `https://ehitufdlbrrjpyivrfod.supabase.co` |

**アカウント分離方針**: インプラスのメインアカウント `info@im-plus.jp`（`implus` org, Pro）とは別アカウント。理由は「社内ツール＝他社員が引き継ぎ開発する可能性があるため、メインの本番サービス（Snapplot 等）と切り離して運用する」（2026-04-24 決定）。

### テーブル構成

| テーブル | 用途 | PK | FK |
|---|---|---|---|
| `members` | スタッフ一覧・ステータス | id | - |
| `statuses` | ステータス定義（色・絵文字） | id | - |
| `equipment` | 機材マスタ | id | - |
| `equipment_users` | 機材予約の担当者マスタ | id | - |
| `reservations` | 機材予約 | id | equipment_id (ON DELETE CASCADE), user_id (ON DELETE SET NULL) |

全テーブル `supabase_realtime` パブリケーションに追加済み（`index.html` の `client.channel()` 購読が動作する前提）。

### 移行履歴

**2026-04-24: Supabase プロジェクト分離移行**

- 元々は Snapplot 本番プロジェクト `wkramctyxgdjpqueuyfp.supabase.co`（当時のプロジェクト名「スタッフボード」、後に「snapplot」にリネーム）に Snapplot 本番データと同居していた
- Snapplot は社外公開・決済・認証ありの本番サービス → 事故防止のため分離
- スタッフボードは社内ツール・他社員が触る可能性あり → 別アカウント化が望ましい
- 5テーブルのスキーマ + データ（計 232 行：members 9, statuses 4, equipment 12, equipment_users 4, reservations 203）を新プロジェクトに移行
- `config.js` / `jobcan-sync.py` の URL/KEY を差し替え
- 旧 snapplot プロジェクト側の5テーブル DROP は**保留中**（動作確認期間後に実施予定）

---

## jobcan-sync.py（サーバー側スクリプト）

- ジョブカン打刻 DB（`C:\ProgramData\Donuts\JobcanKintai\Kintai.db`）を5秒間隔でポーリング
- 新しい打刻を検知したら、該当スタッフの Supabase `members.status` を更新
- 打刻 class → status マッピング:
  - 1 (出勤) / 4 (休憩終了) → `在社`
  - 2 (退勤) → `休み`
  - 3 (休憩開始) → `休憩中`

### 配置・運用

- **壁掛けPCで常駐動作**
- ファイル配置: `Z:\997＿IMPLUS\スタッフボード\staff-board\jobcan-sync.py`（社内 NAS 共有）
- GitHub リポジトリには**含めない**（untracked）
  - 理由: 社員 ID マッピング（`STAFF_MAP`）がコードに含まれるため、Public リポジトリには置かない判断
- 変更後は**壁掛けPCで再起動が必要**

---

## ローカル作業時の注意

### Windows 環境

- ソース配置: Z ドライブ（NAS 共有マウント） `Z:\997＿IMPLUS\スタッフボード\staff-board\`
- 実体パス: `\\new-implus-nas\Work\997＿IMPLUS\スタッフボード\staff-board\`

### git ownership 警告

NAS 上のフォルダで git 操作すると "dubious ownership" 警告が出ることがある。その場合：

```bash
git config --global --add safe.directory '%(prefix)///new-implus-nas/Work/997＿IMPLUS/スタッフボード/staff-board'
```

### 文字コード / 改行

- ファイル文字コード: UTF-8
- 改行: LF（Windows 上では git が CRLF 変換することがあるが気にしなくてよい）

---

## 作業時のチェックリスト

変更を加える前に確認すべきこと：

- [ ] リポジトリは Public である。機密情報を commit しないこと（publishable key 以外）
- [ ] `jobcan-sync.py` を編集した場合は壁掛けPCでの再起動が必要
- [ ] DB スキーマ変更時は `supabase_realtime` パブリケーションへの追加を忘れない
- [ ] 本番（`staff-board-pearl.vercel.app`）は push 後 1-2 分で自動更新される。破壊的変更は慎重に
- [ ] RLS をオンにすると現状の anon key 直接 CRUD が全て失敗する。ユーザー確認なしに変更しない

---

## 関連する外部ドキュメント

- Supabase Dashboard: https://supabase.com/dashboard/project/ehitufdlbrrjpyivrfod
- GitHub: https://github.com/im-plus/staff-board
- Vercel: https://vercel.com/im-pluses-projects/staff-board
