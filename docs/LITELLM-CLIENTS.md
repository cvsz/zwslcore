# LiteLLM cookbook client setup

The local stack exposes a protected OpenAI-compatible Provider at
`http://localhost:8080/v1`. Open WebUI already uses it. Coding clients should
use Provider so they retain the same client authentication and model routing;
connecting them straight to LiteLLM would skip that gateway.

## Codex CLI

Run `bash scripts/zwslcore-codex.sh`. It reads only `PROVIDER_CLIENT_KEY`
(and `PROVIDER_PORT`) from the private `.env.production` file, verifies the
local Provider is ready, exports them as OpenAI-compatible client settings,
and starts Codex with your arguments passed through untouched. Model and
profile selection follows your own Codex configuration.

Prerequisites: Codex CLI installed in WSL, the local stack running, and a
`.env.production` file holding the Provider key (copy `.env` once and set
production values inside).

## Other cookbook clients

The cookbook also documents Claude Code, Gemini CLI, Cursor, GitHub Copilot,
and Open WebUI. Open WebUI is already configured to use Provider.

The other clients are not installed in this WSL environment, so no client
configuration was written for them. When installed, use the Provider URL and
an authenticated Provider key rather than the LiteLLM master key:

- OpenAI-compatible clients: base URL `http://localhost:8080/v1`, model
  `zeaz-coder` (or another model returned by Provider), and bearer key from
  `PROVIDER_CLIENT_KEY`.
- Claude Code: Anthropic-compatible base URL `http://localhost:8080`, model
  `zeaz-claude` (or `zeaz-coder`), and the same Provider key as `ANTHROPIC_AUTH_TOKEN`.
  Provider implements `/v1/messages`; confirm the selected model supports the features
  your Claude Code version requires.

  The `zeaz-claude` route is configured with `cost_policy: LOCAL_ONLY`, meaning it
  routes only to providers with `cost_class: FREE_LOCAL` (Ollama by default) and
  will not fall back to remote/paid providers. If no local target is available,
  the gateway returns HTTP 410 instead of routing remotely. See
  `services/provider/config/providers.yaml` for route configuration.

- Cursor: add an OpenAI-compatible custom model using the Provider URL, model
  `zeaz-coder`, and the Provider key. Cursor UI options vary by version.
- Cursor: add an OpenAI-compatible custom model using the Provider URL, model
  `zeaz-coder`, and the Provider key. Cursor UI options vary by version.
- Gemini CLI: use its OpenAI-compatible provider mode with the Provider URL,
  model alias, and Provider key. Gemini CLI's configuration fields vary by
  version.
- GitHub Copilot: its cookbook guide applies to Copilot's supported custom
  model settings and GitHub account entitlements; this local stack cannot
  enable Copilot or grant those entitlements.

Never put `LITELLM_MASTER_KEY` or upstream provider credentials in a desktop
client. Provider authentication is shared by the local stack; use separate
client keys if the gateway is later configured to support per-client
revocation and model restrictions.
