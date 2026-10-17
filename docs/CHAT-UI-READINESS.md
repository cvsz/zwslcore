# Open WebUI integration readiness

## Existing architecture (do not install a duplicate Chat UI)

```
User -> Open WebUI (port 3000 loopback) -> authenticated ZEAZ Provider Gateway
                                               -> LiteLLM / optional cloud APIs
                                               -> Ollama local models
```

This repository already includes Open WebUI, LiteLLM, Ollama, and an authenticated ZEAZ Provider Gateway. The default Compose stack uses Open WebUI's OpenAI-compatible connection to the Provider, with direct Ollama API access disabled. Keep this boundary intact.

## Fast static checks

```bash
python3 scripts/chat_ui_contract.py
python3 -m unittest tests.test_chat_ui_contract -v
docker compose --env-file .env config --quiet
```

These checks are static configuration assertions only. They do not prove runtime streaming or user-level authorization.

## Deployment and verification

Use `make install` on supported WSL2/Linux with Docker and host PostgreSQL. Do not try to run the full Compose stack on ordinary Google Cloud Shell; use its CLI profile instead. From an installed host:

1. Verify all four containers healthy and that Open WebUI is accessible only on the intended interface.
2. Test login, session expiry, logout, disabled public signup and RBAC with two separate non-admin accounts.
3. Test streaming chats and conversation history across a container restart.
4. Change between `zeaz-fast`, `zeaz-coder`, `zeaz-reasoning` and `zeaz-auto`; verify aliases actually appear in the UI and that unavailable providers fail clearly.
5. Upload a harmless document; test retrieval with an authorized user, then prove another user cannot retrieve it.
6. Test MCP tool permissions and approval prompts on the *real configured runtime*. The local engineering MCP client is not automatically exposed to Open WebUI.
7. Test code execution only in a separately isolated sandbox with explicit approval. Do not mount the host Docker socket, source repositories or WSL host filesystem into the chat container.
8. Validate HTTPS-only access, secure cookies, CORS, rate limits, CSRF protection and API key rotation.
9. Back up and restore `open-webui-data` plus LiteLLM's separately managed PostgreSQL database, then verify restored conversations and accounts.
10. Verify logs do not contain API keys or private prompts; test readiness, failed dependencies and rollback.

## Scope notes

Open WebUI product features are **not** proof that they are enabled in zwslcore. RAG, search, image, voice, MCP, memory and code execution each need explicit installation, configuration, authorization tests and evidence. Enabling arbitrary tool execution inside the Chat UI is not a safe shortcut to autonomous coding.

Cloud Shell's temporary root disk must not hold the sole copy of irreplaceable model or user data. Multi-node experimental functionality is tracked separately from this Chat UI contract.
