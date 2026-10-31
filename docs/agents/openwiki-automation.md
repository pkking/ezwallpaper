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
| `ARK_API_KEY` | 火山引擎方舟（Volcengine Ark）通用模型 API Key，需已开通对应模型。OpenWiki 通过 OpenAI-compatible 接口使用 `glm-5.3-flash`，调用可能产生费用。 |
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
OPENWIKI_MODEL_ID: glm-5.3-flash
OPENWIKI_PAGE_CONCURRENCY: "1"
```

The OpenAI-compatible transport is documented in the [official Ark SDK compatibility guide](https://docs.volcengine.com/docs/ark/compatible-with-openai-sdk?lang=zh). The configured model ID `glm-5.3-flash` is the requested identifier for the custom gateway; confirm that this gateway exposes the model under this exact ID and supports tool calling. See the [Ark model list](https://docs.volcengine.com/docs/ark/model-list?lang=zh) for provider-side capability details. The model must be enabled for the API key. This integration is **source/API compatible but not runtime-tested** until a real generation run succeeds. Set `ARK_BASE_URL` to the Base URL root expected by the OpenAI-compatible SDK (the SDK appends `/chat/completions`; do not append that path yourself unless your gateway explicitly requires a rewritten route). The custom host must be reachable from the GitHub Actions runner. A private VPC-only endpoint is not reachable from `ubuntu-latest` without private networking, a self-hosted runner or an approved gateway. A different region or a Coding Plan subscription may require a **different base URL, token and model ID**; do not use a Coding Plan key with this ordinary metered endpoint. For Coding Plan use, consult [Ark third-party tool integration guidance](https://console.volcengine.com/ark/region%3Acn-beijing/docs/integrate-third-party-tools). No automatic paid fallback or model selection is configured.

### Live Ark preflight check

Before installing or running OpenWiki, the scheduled/manual workflow performs one small OpenAI-compatible `POST /chat/completions` request using `ARK_BASE_URL`, `ARK_API_KEY` and model ID `glm-5.3-flash`. It forces a tiny function call, so a successful check verifies all of the following:

- the runner can resolve, connect to and complete TLS with the custom HTTPS endpoint;
- the API key is accepted and has access to the configured model;
- the custom model ID is recognized;
- the endpoint returns an OpenAI-compatible response and supports the function/tool calling OpenWiki needs.

The probe is limited to 32 output tokens. It is a real model request and may incur a small provider charge. It runs before OpenWiki generation; any network, authentication, quota, model or tool-calling failure stops the job. The workflow masks the API key, custom Base URL and PR token, and reports only a generic error category / HTTP status—not the URL, credentials or provider response body. The preflight checks that `OPENWIKI_PR_TOKEN` is present, but does not perform a write operation with it; its repository write permissions are exercised when `create-pull-request` creates or updates a documentation PR.

This live check runs only in the `OpenWiki documentation` workflow on `master` (schedule or manual dispatch). It is deliberately not added to generic `pull_request` CI, where exposing provider secrets to PR-controlled code would be unsafe. The first real check requires all three repository secrets to be configured.

`ARK_BASE_URL` must be an HTTPS API base URL, not the full `/chat/completions` URL. The runner must have network access to the host. A private VPC-only endpoint requires a self-hosted runner with VPC connectivity or a controlled reachable gateway.

## Repository governance

The existing [agent execution protocol](workflow.md) and `scripts/validate_agent_plan.py` apply to **every** generated PR. Each automated PR references:

```text
Issue: #106
Plan: docs/exec-plans/active/2026-10-30-openwiki-automation-106.md
```

The workflow records a run checkpoint in the plan **only when OpenWiki changes substantive documentation**, so the existing PR validator can enforce plan participation without an exception. **Keep Issue #106 open and the plan active while this automation runs.** Do not archive or close them without first redesigning the automated PR identity and CI validation.

OpenWiki may update root `AGENTS.md`, but this project owns it as its authoritative agent contract. The workflow deliberately discards such edits. Do not include generated workflow files, production code, ADRs, or user wallpaper data in documentation PRs.

## CI test selection

The CI workflow classifies changed paths before selecting Noctalia/Niri-specific tests. It does **not** weaken or change any test assertions.

The following changes run both the offline Noctalia safety tests and the full Noctalia v5.2.1 + Sway/Niri dual-render E2E:

- Any production Rust source under `src/`, or dependency manifests `Cargo.toml` / `Cargo.lock`.
- Sway/Noctalia integration harnesses under `tests/e2e/sway/`.
- `tests/test_noctalia_live_verification.py`, `tests/test_noctalia_sway_helpers.py`, `tests/test_niri_noctalia_helpers.py`, and `scripts/verify_noctalia_live.py`.
- A change to shared workflow configuration (triggers, permissions, concurrency or global environment) or the `noctalia-sway-visual-e2e` job definition in `.github/workflows/ci.yml`.

Changes limited to documentation, OpenWiki output, execution plans, or unrelated workflows/jobs skip the Noctalia-specific tests. For `.github/workflows/ci.yml`, the selector compares the Noctalia job definition and ignores only the two lines that connect it to the selector, so adding or changing unrelated CI jobs does not trigger the expensive Noctalia build.

The filter skips only the Noctalia-specific safety test and the 75-minute Noctalia native build/render job. General Rust tests, Rust quality, agent-plan checks and the separate Sway E2E continue to run. This keeps broad regression coverage while avoiding unrelated Noctalia builds for docs-only PRs. This selection was verified on OpenWiki PR #107: the classifier returned `skip`, both Noctalia-specific jobs were skipped, and the general Rust/platform/Sway jobs continued.

## Verification and operating procedure

1. Merge the integration PR after all current-head CI gates pass.
2. Configure both secrets and manually dispatch the workflow on `master`.
3. Review the Actions run, generated `openwiki/` pages, source references, managed claim files and the new PR's `Agent plan integrity` and other CI results.
4. Merge generated docs only after the **latest PR HEAD** passes checks and the documentation has been reviewed. Leave the ongoing Issue open.
5. Subsequent scheduled runs reuse `openwiki/update`; no content change means no new PR.

On a failing generation, inspect the Actions log for Ark model access/authentication, quota or rate limits, Node/npm installation or OpenWiki errors. The workflow fails rather than posting incomplete docs. In case of unwanted output, do not merge the docs PR; re-run after fixing source/settings. Roll back this automation by removing its workflow in a governed PR, then retire Issue #106 and the plan after no scheduled generated PR depends on them.

**Upstream implementation:** [scheduled-workflow example](https://github.com/langchain-ai/openwiki/blob/v0.7.2/examples/openwiki-update.yml), [CLI/package requirements](https://github.com/langchain-ai/openwiki/blob/v0.7.2/package.json).
