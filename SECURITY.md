# Security Policy

## Reporting a vulnerability

Please report security issues privately to the maintainers (open a private security advisory on
the repository host, or contact the maintainer directly) rather than filing a public issue.
Include reproduction steps and impact. We aim to acknowledge reports promptly.

## Security model & guarantees

Prompt Workbench is a **local developer tool**, designed to run on a laptop or a single private
development server. It is not a hardened multi-tenant cloud service.

- **Network binding.** The server binds to `127.0.0.1` by default. Exposing it beyond localhost
  should be done only behind an existing HTTPS proxy / VPN with authentication.
- **Authentication.** Local username/password accounts; passwords hashed with **Argon2id**.
  Interactive sessions use short-lived **JWT** access tokens (HS256) with issuer/audience/expiry
  and per-user `token_version` checks. Logout / password change / disable invalidate outstanding
  tokens by bumping `token_version`.
- **Integration keys.** Separate, scoped, hashed, revocable opaque API keys for service
  integrations (e.g. `captures:write`). A capture-only key cannot read captures, edit the
  registry, run models, or publish.
- **Secret containment.** Provider credentials are referenced by **environment-variable name**
  only. Secret values are never stored in the database, returned to the browser, or written into
  exports, release bundles, logs, error bodies, or change-history metadata.
- **No code execution.** The `simple-v1` template engine performs no code execution and no HTML
  escaping of untrusted content into markup. Function tool schemas are supported but their
  functions are never executed. Imports accept data files only, with size/path/traversal checks.
- **Outbound access.** Only explicitly configured provider connections make network calls.
  Metadata/link-local destinations and credential-carrying redirects are rejected. Telemetry and
  external LiteLLM callbacks are disabled.

## Data & retention notes

- SQLite/MongoDB data is stored on local disk with no encryption-at-rest promise; use an
  encrypted volume for sensitive datasets and keep the data directory private to the OS user.
- Raw captures and run payloads have configurable retention; payload deletion replaces content
  with tombstones while preserving non-sensitive identifiers.
- This project is **not** certified against SOC 2, GDPR, or similar frameworks.

## Scope

Demo and test data are entirely synthetic and never sent to a paid provider.
