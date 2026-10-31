# OpenWiki automatic documentation

`ezwallpaper` uses upstream [OpenWiki v0.7.2](https://github.com/langchain-ai/openwiki/tree/v0.7.2)
to generate and maintain source-grounded Markdown documentation under `openwiki/`.
The configuration lives at [`.github/workflows/openwiki-update.yml`](../../.github/workflows/openwiki-update.yml).

## Triggers and output

- **Scheduled:** Mondays, 08:17 UTC (GitHub Actions UTC cron; scheduled runs are not guaranteed to execute at the exact minute).
- **Manual:** Actions > **OpenWiki documentation** > **Run workflow** on `master`.
- A full-history checkout runs `openwiki code --update --print` with Node.js 22.22.0 and OpenWiki 0.7.2. On the first run, `--update` initializes the repository wiki when provider settings exist.
- Changes are proposed in a reusable `openwiki/update` PR. Only `openwiki/` and the linked ongoing plan are eligible to be committed; no auto-merge.
- Timestamp-only `openwiki/.last-update.json` churn does not open a new PR. New or updated substantive docs include the checkpoint metadata needed for future incremental updates.
- This workflow does not deploy GitHub Pages. Generated Markdown becomes part of the repository after review/merge.

## Required repository secrets

Configure these via GitHub repository **Settings > Secrets and variables > Actions**:

| Secret | Purpose |
|---|---|
| `ARK_API_KEY` | 火山引擎方舟（Volcengine Ark）通用模型 API Key，需已开通对应模型。OpenWiki 通过 OpenAI-compatible 接口使用 `doubao-seed-2-1-pro-260915`，调用可能产生费用。 |
| `ARK_BASE_URL` | 你的方舟自定义 OpenAI-compatible API Base URL。工作流不再写死官方公开地址。 |
| `OPENWIKI_PR_TOKEN` | Fine-grained PAT or GitHub App token scoped to `pkking/ezwallpaper` with **Contents: read/write** and **Pull requests: read/write**. Required to open a PR that triggers required GitHub CI. |

Use a dedicated automation identity if possible. Never commit tokens or include them in generated documents. Missing secrets produce a failing workflow with a configuration message, not a silently skipped docs run. The default GitHub `GITHUB_TOKEN` cannot be used as a drop-in replacement: PRs it creates normally do not trigger `pull_request` workflows.

The inference step receives the model-provider key but **not** the PR token. Source content is sent to 火山引擎方舟（Volcengine Ark）; the repository is public, but review data-sharing, data residency and costs before enabling scheduled inference. OpenWiki's optional telemetry is disabled.

### Ark provider configuration

The workflow selects the OpenWiki `openai-compatible` provider (not the native `openrouter` provider):

```yaml
OPENWIKI_PROVIDER: openai-compatible
OPENAI_COMPATIBLE_BASE_URL: ${{ secrets.ARK_BASE_URL }}
OPENAI_COMPATIBLE_API_KEY: ${{ secrets.ARK_API_KEY }}
OPENWIKI_MODEL_ID: doubao-seed-2-1-pro-260915
OPENWIKI_PAGE_CONCURRENCY: "1"
```

The endpoint and model ID are from the [official Ark OpenAI SDK compatibility example](https://docs.volcengine.com/docs/ark/compatible-with-openai-sdk?lang=zh); [model capabilities](https://docs.volcengine.com/docs/ark/model-list?lang=zh) include tool calling. The model must be enabled for the API key. This integration is **source/API compatible but not runtime-tested** until a real generation run succeeds. Set `ARK_BASE_URL` to the Base URL root expected by the OpenAI-compatible SDK (the SDK appends `/chat/completions`; do not append that path yourself unless your gateway explicitly requires a rewritten route). The custom host must be reachable from the GitHub Actions runner. A private VPC-only endpoint is not reachable from `ubuntu-latest` without private networking, a self-hosted runner or an approved gateway. A different region or a Coding Plan subscription may require a **different base URL, token and model ID**; do not use a Coding Plan key with this ordinary metered endpoint. For Coding Plan use, consult [Ark third-party tool integration guidance](https://console.volcengine.com/ark/region%3Acn-beijing/docs/integrate-third-party-tools). No automatic paid fallback or model selection is configured.

## Repository governance

The existing [agent execution protocol](workflow.md) and `scripts/validate_agent_plan.py` apply to **every** generated PR. Each automated PR references:

```text
Issue: #106
Plan: docs/exec-plans/active/2026-10-30-openwiki-automation-106.md
```

The workflow records a run checkpoint in the plan **only when OpenWiki changes substantive documentation**, so the existing PR validator can enforce plan participation without an exception. **Keep Issue #106 open and the plan active while this automation runs.** Do not archive or close them without first redesigning the automated PR identity and CI validation.

OpenWiki may update root `AGENTS.md`, but this project owns it as its authoritative agent contract. The workflow deliberately discards such edits. Do not include generated workflow files, production code, ADRs, or user wallpaper data in documentation PRs.

## Verification and operating procedure

1. Merge the integration PR after all current-head CI gates pass.
2. Configure both secrets and manually dispatch the workflow on `master`.
3. Review the Actions run, generated `openwiki/` pages, source references, managed claim files and the new PR's `Agent plan integrity` and other CI results.
4. Merge generated docs only after the **latest PR HEAD** passes checks and the documentation has been reviewed. Leave the ongoing Issue open.
5. Subsequent scheduled runs reuse `openwiki/update`; no content change means no new PR.

On a failing generation, inspect the Actions log for Ark model access/authentication, quota or rate limits, Node/npm installation or OpenWiki errors. The workflow fails rather than posting incomplete docs. In case of unwanted output, do not merge the docs PR; re-run after fixing source/settings. Roll back this automation by removing its workflow in a governed PR, then retire Issue #106 and the plan after no scheduled generated PR depends on them.

**Upstream implementation:** [scheduled-workflow example](https://github.com/langchain-ai/openwiki/blob/v0.7.2/examples/openwiki-update.yml), [CLI/package requirements](https://github.com/langchain-ai/openwiki/blob/v0.7.2/package.json).
