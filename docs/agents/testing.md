# Verification and evidence

## Required offline commands

Run from repository root, using the toolchain chosen in the current CI workflow:

    python3 -m unittest discover -s tests -p 'test_agent_plan.py' -v
    cargo fmt --all -- --check
    cargo clippy --all-targets --all-features -- -D warnings -W clippy::unwrap_used
    cargo test --all-targets --verbose
    cargo run -- --help
    cargo run -- --version

Never describe a command as passing unless its exit code and tested revision are known.

## CI jobs and contracts

- Agent plan integrity: PR body has exactly one Issue and canonical Plan; the Issue is open and the plan contains a matching ID, recognized status, recovery point and required headings.
- Agent contract self-tests: negative and positive offline unit tests for the plan validator, no GitHub token needed.
- Rust quality: existing strict fmt and Clippy gates remain enforced; no warning allowlists introduced for convenience.
- Rust tests and CLI smoke: Rust tests plus offline --help, --version, and invalid backend rejection, without a real network call, Pexels token or wallpaper mutation. These are CLI contract tests, **not** evidence of successful wallpaper setting.

Expected logs are uploaded as an artifact on failure as well as success. Uploads are useful for diagnosis; their presence alone is not proof of success.

## Testing requirements for future changes

- Parsing/validation/model updates: unit tests for positive, negative and boundary values.
- Bing/Pexels adapter changes: deterministic fixture-based response/HTTP contract tests for valid, empty, malformed, error and status-code behavior; no live API access in required jobs.
- Download/file changes: tests with temporary directories and safe paths, explicit overwrite/error assertions, no writes outside the test sandbox.
- CLI changes: offline binary invocation asserting exit status, stdout/stderr and user-visible flags.
- Wallpaper side effects: isolate behind an injectable interface before adding automatic tests; use a fake adapter for CI. A real desktop integration test requires a controlled platform runner and must be reported as a distinct gate.
- Cross-platform support: Windows/macOS/Linux/Wayland claims require named platform-specific evidence, not merely Linux compilation.

## Evidence vocabulary

Record command, revision SHA, status code, relevant output, artifact path and CI run URL. Mark not executed as UNASSESSED, not PASS. For external APIs, separate simulated fixture coverage from live diagnostic observations.

A CLI smoke test passes only if the command behavior was checked; it must not be presented as an end-to-end wallpaper success. A post-merge archive needs the specific final CI result.
