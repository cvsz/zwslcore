SHELL := /bin/bash

.PHONY: cloudflare-stack-preflight cloudflare-stack-configure cloudflare-stack-rollback webhook-install webhook-start webhook-health webhook-route webhook-rollback cloudflare-doctor feature-preflight feature-install feature-verify cloudflare-preflight cloudshell-full-install cloudshell ai-help ai-doctor ai-test help validate-template install up down restart wait-runtime doctor smoke logs capacity models models-manifest free-models models-dev-sync models-dev-stats models-dev-recommend engineer-tasks engineer-profile engineer-work engineer-tui engineer-test config production-config production-up provider-build provider-lock provider-lock-check cloudflare-up ci

cloudshell:
	bash scripts/cloudshell.sh

cloudflare-stack-preflight:
	bash scripts/cloudflare-stack.sh preflight

cloudflare-stack-configure:
	bash scripts/cloudflare-stack.sh configure

cloudflare-stack-rollback:
	bash scripts/cloudflare-stack.sh rollback

webhook-install:
	bash scripts/cloudshell-webhook.sh install

webhook-start:
	bash scripts/cloudshell-webhook.sh start

webhook-health:
	bash scripts/cloudshell-webhook.sh health

webhook-route:
	bash scripts/cloudshell-webhook.sh configure

webhook-rollback:
	bash scripts/cloudshell-webhook.sh rollback

# Non-destructive capability inventory; Cloud Shell uses installed Ollama models.
feature-preflight:
	bash scripts/feature-install.sh preflight

feature-install:
	bash scripts/feature-install.sh install

feature-verify:
	bash scripts/feature-install.sh verify

# Set ZCLOUD_HOSTNAME in the command environment; does not modify routing or policy.
cloudflare-doctor:
	@test -n "$$ZCLOUD_HOSTNAME" || { echo "Set ZCLOUD_HOSTNAME first" >&2; exit 2; }
	bash scripts/cloudflare-ssh-doctor.sh doctor

cloudflare-preflight:
	@test -n "$$ZCLOUD_HOSTNAME" || { echo "Set ZCLOUD_HOSTNAME first" >&2; exit 2; }
	ZWSL_CHECK_CLOUDFLARE=1 bash scripts/feature-install.sh preflight

# Install only missing Open WebUI and local read-only MCP diagnostics.
# Prepare writable ZWSL_WEBUI_BASE (default /opt/zeaz-storage) beforehand.
cloudshell-full-install:
	ZWSL_PROFILE=cloudshell ZWSL_INSTALL_WEBUI=1 ZWSL_INSTALL_MCP=1 bash scripts/feature-install.sh preflight
	ZWSL_PROFILE=cloudshell ZWSL_INSTALL_WEBUI=1 ZWSL_INSTALL_MCP=1 bash scripts/feature-install.sh install

ai-help:
	bash scripts/ai.sh help

ai-doctor:
	bash scripts/ai.sh doctor

ai-test:
	bash -n scripts/ai.sh
	bash scripts/ai.sh selftest
	bash -n scripts/cloudshell.sh

help:
	@printf '%s\n' \
	  'cloudflare-stack-preflight check WebUI health and ingress prerequisites' \
	  'cloudflare-stack-configure add protected WebUI route with backup' \
	  'cloudflare-stack-rollback restore previous ingress configuration' \
	  'webhook-install   install local signed webhook receiver' \
	  'webhook-health    check local receiver health' \
	  'webhook-route     opt-in Cloudflare webhook route' \
	  'feature-preflight  inspect installed features before any changes' \
	  'feature-install    install the selected environment profile' \
	  'feature-verify     validate selected profile' \
	  'cloudflare-doctor  diagnose active connector, ingress and SSH transport' \
	  'cloudflare-preflight inspect existing SSH ingress; requires ZCLOUD_HOSTNAME' \
	  'cloudshell-full-install install missing native WebUI and local read-only MCP' \
	  'cloudshell    bootstrap Cloud Shell CLI-only profile (no Docker/PostgreSQL)' \
	  'ai-help      show AI CLI help' \
	  'ai-doctor    inspect AI CLI configuration' \
	  'ai-test      validate standalone AI CLI and Cloud Shell script' \
	  'install       bootstrap local AI stack' \
	  'up/down       start or stop stack' \
	  'wait-runtime  wait for stable runtime health' \
	  'doctor        verify runtime health' \
	  'smoke         verify authenticated model inference' \
	  'capacity      report disk and Docker storage pressure' \
	  'models        list local Ollama models' \
	  'models-manifest capture or compare local model identities' \
	  'free-models   discover current OpenRouter zero-price text models' \
	  'models-dev-sync sync provider/model metadata from models.dev' \
	  'models-dev-stats inspect cached models.dev catalog counts' \
	  'models-dev-recommend rank local-first model candidates' \
	  'engineer-tasks list durable engineering tasks' \
	  'engineer-profile show detected hardware/model profile' \
	  'engineer-work  list durable continuous work items' \
	  'engineer-reconcile inspect queue/task state drift' \
	  'engineer-recover recover blocked work with adaptive model fallback' \
	  'engineer-tui   open read-only engineering terminal dashboard' \
	  'engineer-test  run engineering agent/selector/TUI/control-plane tests' \
	  'config        validate Compose configuration' \
	  'production-config validate production Compose configuration' \
	  'production-up start with .env.production' \
  'provider-build build the in-repo provider gateway' \
  'provider-lock update the hashed Provider dependency lock' \
  'provider-lock-check verify Provider dependency lock drift' \
  'cloudflare-up start zwslcore on the Cloudflare loopback ports' \
	  'ci            repository + stack static validation'

validate-template:
	python3 scripts/validate_repo.py
	python3 -m unittest discover -s tests -v

install:
	bash scripts/install.sh

config:
	@test -f .env || cp .env.example .env
	docker compose --env-file .env config --quiet

production-config:
	@test -f .env.production || { echo 'Create .env.production first.' >&2; exit 1; }
	ZW_ENV_FILE=.env.production docker compose --env-file .env.production config --quiet

production-up:
	@test -f .env.production || { echo 'Create .env.production first.' >&2; exit 1; }
	@! grep -Eq '^(OPENWEBUI_WEB_URL|OPENWEBUI_CORS_ALLOW_ORIGIN)=.*REPLACE_ME_DOMAIN' .env.production || { echo 'Set the production HTTPS hostname in .env.production first.' >&2; exit 1; }
	ZW_ENV_FILE=.env.production docker compose --env-file .env.production up -d
	python3 scripts/bootstrap-litellm-admin.py .env.production

up:
	docker compose --env-file .env up -d
	python3 scripts/bootstrap-litellm-admin.py .env

down:
	docker compose --env-file .env down

restart:
	docker compose --env-file .env restart

wait-runtime:
	bash scripts/wait-runtime.sh

doctor:
	bash scripts/doctor.sh

smoke:
	bash scripts/smoke.sh

logs:
	docker compose --env-file .env logs -f --tail=200

capacity:
	python3 scripts/capacity.py

models:
	docker exec zwslcore-ollama ollama list

models-manifest:
	python3 scripts/model_manifest.py

free-models:
	python3 scripts/sync-free-models.py

models-dev-sync:
	python3 scripts/models-dev.py sync

models-dev-stats:
	python3 scripts/models-dev.py stats

models-dev-recommend:
	python3 scripts/models-dev.py recommend --structured-output --min-context 4096

engineer-tasks:
	python3 scripts/engineer.py list

engineer-profile:
	python3 scripts/engineer.py profile

engineer-work:
	python3 scripts/engineer.py work-list

engineer-reconcile:
	python3 scripts/engineer.py reconcile

engineer-recover:
	python3 scripts/engineer.py recover --max-iterations 4

engineer-tui:
	python3 scripts/engineer.py tui

engineer-test:
	python3 -m unittest tests.test_model_selector tests.test_engineering_agents tests.test_engineering_custom_agents tests.test_engineering_delegation tests.test_engineering_mcp tests.test_engineering_change_snapshot tests.test_engineering_tui tests.test_engineering_control_plane -v

provider-build:
	docker compose --env-file .env build provider

provider-lock:
	bash scripts/provider-lock.sh update

provider-lock-check:
	bash scripts/provider-lock.sh check

cloudflare-up:
	bash scripts/cloudflare-up.sh

ci: validate-template
	python3 -m py_compile scripts/sync-free-models.py scripts/models-dev.py services/model_catalog/catalog.py services/model_catalog/models_dev.py services/model_catalog/selector.py
	python3 -m compileall -q services/provider/zeaz_provider services/engineering scripts/engineer.py
	python3 -m unittest discover -s tests -v
	bash -n scripts/install.sh
	bash -n scripts/doctor.sh
