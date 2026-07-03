# renovate-ideal-succotash

aiohttp を使ったミニマムな Web サーバに、Renovate と Dependabot の初期設定を加えた検証用リポジトリです。

aiohttp を最新版 (3.14.1 以降) ではなく `==3.14.0` に固定しているため、リモートに push すると Renovate がすぐに更新 PR を作成します。Dependabot はセキュリティアップデート専用の設定にしており、固定中のバージョンに影響するセキュリティアドバイザリが公開されたときだけ PR を作成します。

## 構成

- `main.py` — aiohttp のミニマム Web サーバ (`GET /` で挨拶を返す)
- `pyproject.toml` / `uv.lock` — uv 管理の依存定義 (Python 3.14)
- `renovate.json` — Renovate 設定
- `.github/dependabot.yml` — Dependabot 設定 (security updates 専用)
- `requirements.txt` — uv.lock からのエクスポート (dependency graph / Dependabot alerts 用)

## アプリの実行

```console
$ uv sync
$ uv run main.py
```

別のターミナルから動作確認します。

```console
$ curl http://127.0.0.1:8080/
Hello, aiohttp 3.14.0
```

Lint は ruff で行います。

```console
$ uv run ruff check .
```

## Renovate のセットアップ手順

Renovate は GitHub App として動作します。設定ファイル (`renovate.json`) は本リポジトリに用意済みなので、App のインストールと設定の検証を行えば稼働します。

### 1. 設定ファイルの検証

npm/npx は使わず bunx で検証します。

```console
$ bunx --package renovate renovate-config-validator renovate.json
 INFO: Validating renovate.json as global config
 INFO: Config validated successfully against 1 file(s)
```

### 2. リポジトリを GitHub へ push

```console
$ git add .
$ git commit -m "Add aiohttp app and Renovate/Dependabot config"
$ git push origin main
```

### 3. Renovate GitHub App のインストール

App のインストール操作自体はブラウザで行います。コンソールからインストールページを開きます。

```console
$ open https://github.com/apps/renovate
```

「Install」からアカウントを選択し、「Only select repositories」で本リポジトリを選択します。

`renovate.json` が既に main ブランチに存在するため、オンボーディング PR (`Configure Renovate`) はスキップされ、そのまま依存更新 PR の作成が始まります。数分待っても PR が来ない場合は Developer Portal (https://developer.mend.io/) からジョブログを確認できます。

### 4. 動作確認

```console
$ gh pr list
```

`chore(deps): update dependency aiohttp to v3.14.1` のような PR が作成されていれば成功です。

## Dependabot のセットアップ手順 (security updates 専用)

本リポジトリの Dependabot はセキュリティアップデート専用に設定しています。通常のバージョン更新 PR は作らず、固定中のバージョンに影響するセキュリティアドバイザリ (GitHub Advisory Database) が公開されたときだけ、修正版へ引き上げる PR を作成します。

aiohttp でいえば、たとえば 3.14.0 に影響する脆弱性が公表され 3.15.x で修正された場合に、`build(deps): bump aiohttp from 3.14.0 to 3.15.x` のような PR が自動で作られる想定です。

### 1. 設定ファイル

version updates を止めるには `open-pull-requests-limit: 0` を設定します。これは「security updates だけ欲しい場合」の公式推奨の書き方で、ファイル自体は security update PR のカスタマイズ (ラベルやグルーピングなど) のために残せます。

```yaml
version: 2
updates:
  - package-ecosystem: "uv"
    directory: "/"
    schedule:
      interval: "daily"
    open-pull-requests-limit: 0
```

push して default ブランチに反映します。

```console
$ git add .github/dependabot.yml
$ git commit -m "Restrict dependabot to security updates"
$ git push origin main
```

### 2. GitHub 側のセキュリティ機能の有効化

security updates の動作には dependency graph、Dependabot alerts、Dependabot security updates の 3 つが必要です。dependency graph は public リポジトリではデフォルト有効なので、残り 2 つを gh CLI で有効化します (本リポジトリでは有効化済み)。

```console
$ gh api -X PUT repos/lmd649/renovate-ideal-succotash/vulnerability-alerts
$ gh api -X PUT repos/lmd649/renovate-ideal-succotash/automated-security-fixes
```

有効化されているかは次で確認できます。

```console
$ gh api repos/lmd649/renovate-ideal-succotash/vulnerability-alerts -i | head -1
HTTP/2.0 204 No Content
$ gh api repos/lmd649/renovate-ideal-succotash/automated-security-fixes
{"enabled":true,"paused":false}
```

### 3. 動作確認

状態はリポジトリの Insights > Dependency graph > Dependabot、およびアラートは Security > Dependabot alerts で確認できます。

```console
$ gh browse --repo lmd649/renovate-ideal-succotash network/updates
$ gh api repos/lmd649/renovate-ideal-succotash/dependabot/alerts
```

なお aiohttp 3.14.0 には GHSA-xcgm-r5h9-7989 (websocket frame payloads bypass memory limits) など 3.14.1 で修正されたアドバイザリが複数あるため、push するとアラートが検出され、`Bump aiohttp from 3.14.0 to 3.14.1` のような security update PR が自動作成されます。

### 補足: uv.lock は dependency graph 未対応

GitHub の dependency graph は uv.lock / PEP 621 の pyproject.toml をまだ解析できません (Dependabot version updates の uv 対応とは別)。dependency graph に依存が載らないと Dependabot alerts も security updates も動かないため、本リポジトリでは uv.lock からエクスポートした `requirements.txt` を alerts 検出用に置いています。

```console
$ uv export --format requirements-txt --no-hashes --no-dev --no-emit-project -o requirements.txt
```

依存を変更したら上記コマンドで再生成してください。security update PR は requirements.txt を書き換えるので、取り込む際は pyproject.toml / uv.lock 側も合わせて更新します。

### 4. 手動実行について

Dependabot の手動トリガは次の手段があります (一括実行の公開 API はありません)。

- version updates は Insights > Dependency graph > Dependabot からマニフェストを選び「Check for updates」ボタンで即時実行できる (本リポジトリでは `open-pull-requests-limit: 0` のため PR は作られない)
- security updates はアラート検出時に自動実行される。個別には Security > Dependabot alerts の各アラートページにある「Create Dependabot security update」ボタンで、そのアラートに対する修正 PR を(再)作成できる
- `dependabot.yml` や `pyproject.toml` / `uv.lock` を push すると再スキャンが走るため、実質的な再実行手段になる

## 補足

役割分担として、通常のバージョン更新は Renovate、セキュリティアップデートは Dependabot が担当します。Renovate 側も `vulnerabilityAlerts` で脆弱性起点の PR を作れるため、セキュリティ PR が二重になる可能性はありますが、本リポジトリは動作比較が目的のため許容しています。

## ドキュメントリンク

- aiohttp: https://docs.aiohttp.org/
- aiohttp Web サーバ クイックスタート: https://docs.aiohttp.org/en/stable/web_quickstart.html
- uv: https://docs.astral.sh/uv/
- Renovate ドキュメント: https://docs.renovatebot.com/
- Renovate GitHub App インストール: https://docs.renovatebot.com/getting-started/installing-onboarding/
- Renovate pep621 (uv) マネージャ: https://docs.renovatebot.com/modules/manager/pep621/
- Renovate 設定バリデータ: https://docs.renovatebot.com/config-validation/
- Dependabot security updates の設定: https://docs.github.com/en/code-security/dependabot/dependabot-security-updates/configuring-dependabot-security-updates
- Dependabot security updates のカスタマイズ (open-pull-requests-limit: 0 の記載あり): https://docs.github.com/en/code-security/dependabot/dependabot-security-updates/customizing-dependabot-security-prs
- Dependabot version updates の設定: https://docs.github.com/en/code-security/dependabot/dependabot-version-updates/configuring-dependabot-version-updates
- dependabot.yml リファレンス: https://docs.github.com/en/code-security/dependabot/working-with-dependabot/dependabot-options-reference
- Dependabot 対応エコシステム (uv 含む): https://docs.github.com/en/code-security/dependabot/ecosystems-supported-by-dependabot/supported-ecosystems-repositories
- dependency graph 対応エコシステム (uv.lock は未対応): https://docs.github.com/en/code-security/supply-chain-security/understanding-your-software-supply-chain/dependency-graph-supported-package-ecosystems
- uv export: https://docs.astral.sh/uv/reference/cli/#uv-export
