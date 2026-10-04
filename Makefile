SHELL := /bin/bash

.PHONY: help validate-template install up down restart wait-runtime doctor smoke logs models free-models models-dev-sync models-dev-stats models-dev-recommend engineer-tasks engineer-profile engineer-work engineer-tui engineer-test config provider-build ci

help:
	@printf '%s\n' \
	  'install       bootstrap local AI stack' \
	  'up/down       start or stop stack' \
	  'wait-runtime  wait for stable runtime health' \
	  'doctor        verify runtime health' \
	  'smoke         verify authenticated model inference' \
	  'models        list local Ollama models' \
	  'free-models   discover current OpenRouter zero-price text models' \
	  'models-dev-sync sync provider/model metadata from models.dev' \
	  'models-dev-stats inspect cached models.dev catalog counts' \
	  'models-dev-recommend rank local-first model candidates' \
	  'engineer-tasks list durable engineering tasks' \
	  'engineer-profile show detected hardware/model profile' \
	  'engineer-work  list durable continuous work items' \
	  'engineer-test run engineering control-plane tests' \
	  'config        validate Compose configuration' \
	  'provider-build build the in-repo provider gateway' \
	  'ci            repository + stack static validation'

validate-template:
	python3 scripts/validate_repo.py
	python3 -m unittest discover -s tests -v

install:
	bash scripts/install.sh

config:
	@test -f .env || cp .env.example .env
	docker compose --env-file .env config --quiet

up:
	docker compose --env-file .env up -d

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

models:
	docker exec zwslcore-ollama ollama list

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

engineer-tui:
	python3 scripts/engineer.py tui

engineer-test:
	python3 -m unittest tests.test_engineering_control_plane -v

provider-build:
	docker compose --env-file .env build provider

ci: validate-template
	python3 -m py_compile scripts/sync-free-models.py scripts/models-dev.py services/model_catalog/catalog.py services/model_catalog/models_dev.py services/model_catalog/selector.py
	python3 -m compileall -q services/provider/zeaz_provider services/engineering scripts/engineer.py
	python3 -m unittest tests.test_model_catalog tests.test_models_dev_catalog tests.test_model_selector tests.test_engineering_tui tests.test_engineering_control_plane -v
	bash -n scripts/install.sh
	bash -n scripts/doctor.sh
