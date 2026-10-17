# Native Open WebUI for Google Cloud Shell (opt-in)

Cloud Shell's normal `make cloudshell` profile remains CLI-only. This optional installer is **not** a production deployment and does not change the WSL2 Compose architecture.

Cloud Shell 3.12 with Ollama already running on localhost:

```bash
sudo mkdir -p /opt/zeaz-storage
sudo chown "$(id -u):$(id -g)" /opt/zeaz-storage
bash scripts/cloudshell-webui.sh install
bash scripts/cloudshell-webui.sh start
# In another terminal:
bash scripts/cloudshell-webui.sh health
```

Native Open WebUI uses Ollama directly; it does **not** automatically enable ZEAZ Provider Gateway, LiteLLM or remote providers. These require a reachable authenticated Gateway and separate configuration. Native installation lives on ephemeral /opt storage; the UI data and stable secret live in persistent home, subject to the small Cloud Shell quota.

For first admin registration, keep Cloudflare Tunnel stopped and temporarily run `ENABLE_SIGNUP=true bash scripts/cloudshell-webui.sh start` with loopback binding. Use a local trusted access path to create the first account, stop it, and restart with default signup disabled **before** enabling a public hostname. Do not disable `WEBUI_AUTH`. Cloudflare Access protects the outer edge but does not replace application authorization.

Run a Cloudflare Tunnel only after `health` succeeds. A named Tunnel plus Access is preferred over a temporary Quick Tunnel. Cloud Shell sessions and /opt storage are ephemeral; no 24/7 availability guarantee. Do not publish Ollama port 11434 or SSH port 2222.
