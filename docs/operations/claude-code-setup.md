# Claude Code CLI Setup — ZEAZ Gateway

## Prerequisites

- Claude Code CLI v2.1.314 or later
- ZEAZ Gateway Provider running locally
- `PROVIDER_CLIENT_KEY` available (from `.env.production`)

## Environment Configuration

Set the following environment variables before launching Claude Code:

```bash
export ANTHROPIC_BASE_URL="http://localhost:8080"
export ANTHROPIC_AUTH_TOKEN="$PROVIDER_CLIENT_KEY"
export ANTHROPIC_MODEL="zeaz-claude"
```

- `ANTHROPIC_BASE_URL`: Points to the ZEAZ Gateway Provider (default port 8080)
- `ANTHROPIC_AUTH_TOKEN`: The Provider client key (same as `PROVIDER_CLIENT_KEY`)
- `ANTHROPIC_MODEL`: The route alias `zeaz-claude`

## Verification

1. **Gateway health**:
   ```bash
   curl http://localhost:8080/health/ready
   ```

2. **Model list** (requires auth):
   ```bash
   curl -H "Authorization: Bearer $PROVIDER_CLIENT_KEY" \
        http://localhost:8080/v1/models
   ```

3. **Claude Code CLI version**:
   ```bash
   claude --version
   ```

4. **E2E test**: Send a message through Claude Code and confirm it is answered by the local Qwen model via the gateway.

## Security Notes

- `ANTHROPIC_AUTH_TOKEN` must never be written to disk or shell history
- Use environment variables only
- The gateway authenticates all requests to `/v1/messages`
- `zeaz-claude` route uses `LOCAL_ONLY` policy — no remote fallback

## Troubleshooting

| Issue | Likely Cause | Fix |
|-------|-------------|-----|
| Connection refused | Gateway not running | Start provider on port 8080 |
| 401 Unauthorized | Invalid or missing key | Set `ANTHROPIC_AUTH_TOKEN` |
| 404 Model not found | Wrong model alias | Use `zeaz-claude` |
| 410 No local target | Ollama unavailable | Start Ollama service |
| 502 Upstream error | Ollama failure | Check Ollama logs |
