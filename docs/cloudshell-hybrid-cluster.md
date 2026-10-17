# Experimental Cloud Shell hybrid AI pool

Cloud Shell is ephemeral and subject to session/usage limits. This is a development tool, not an always-on cluster.

## Two-node Ollama task routing

Run Ollama independently on each node. Access remote nodes **only** over authenticated, private, HTTPS transport; do not publish Ollama's unauthenticated API. The pool intentionally rejects non-loopback HTTP URLs. It does not create or authenticate tunnels itself.

```bash
export ZWSL_OLLAMA_ENDPOINTS='http://127.0.0.1:11434,https://YOUR-AUTHENTICATED-PRIVATE-WORKER'
python3 scripts/cloudshell_cluster.py health
python3 scripts/cloudshell_cluster.py agents --jobs 2 --prompt 'Review this module for bugs'
python3 scripts/cloudshell_cluster.py benchmark --jobs 2
python3 -m unittest discover -s tests -p 'test_cloudshell_cluster.py' -v
```

Each node loads its own model. This does **not** combine RAM or implement model sharding. Job retries, durable scheduling, authenticated transport configuration, and production observability are not yet implemented.

## Model sharding (experimental, not installed)

llama.cpp RPC is a separate backend that requires careful private network isolation, compatible binaries and benchmarking. Do not expose RPC ports publicly. This PR does not install or claim a functioning distributed model-sharding engine.

## Cloud Shell storage

Root overlay space (e.g. /opt) is ephemeral. Keep model copies in persistent storage if redownload is unacceptable. Never automatically delete the original ~/.ollama/models after copying to /opt. A reset may remove all models stored under /opt.
