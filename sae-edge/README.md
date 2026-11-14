# SAE EDGE CORE — Federation Contract v1

**Scope:** opt-in registration and deployment policy for repositories owned by `pergolessi9-star`. This registry is not a reverse-proxy deployment.

The existing SAE EDGE CORE 0.3.0 Go gateway is validated only with a local simulated origin. Its Cloudflare Pages site is an informational portal, not a working cloud proxy. No production routing, authentication secret, or DNS record is modified by this repository contract.

## Enrollment

Each participating repository receives `.sae/edge-core.json`. New repositories can be onboarded through the GitHub template workflow after they contain a default branch. The default mode is `catalog-only` and the data plane is **disabled**.

Integration levels:
1. Catalog-only: repository listed, ownership and config validated.
2. Staging: route can be provisioned only after an isolated environment and explicit approved credentials exist.
3. Production: only after health checks, TLS, Access, origin allow-list, persistence, audit, rollback and performance testing.

**Secrets:** use provider secret stores. No tokens, private URLs or API keys in manifests or pull requests.

## Review/rollout

CI checks manifest structural validity and ensures routing is disabled in catalog-only mode. Automated PRs do not merge themselves. To activate a route, perform a separate architecture review and approval. Do not add gateway URLs to browser-side JavaScript or bypass the origin's existing authentication.

Future automation is delivered as a safe **dry-run by default** script; enabling cross-repo PR creation requires a dedicated scoped GitHub App token, not the built-in `GITHUB_TOKEN` for another repository. Never grant this automation permission to merge, deploy, or change secrets.

See: https://sae-edge-core-30.pages.dev/
