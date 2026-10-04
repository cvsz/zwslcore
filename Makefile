SHELL := /bin/bash

.PHONY: help validate-template install up down restart doctor smoke logs models free-models config provider-build ci

help:
	@printf '%s\n' \
	  'install       bootstrap local AI stack' \
	  'up/down       start or stop stack' \
	  'doctor        verify runtime health' \
	  'smoke         verify authenticated model inference' \
	  'models        list local Ollama models' \
	  'free-models   discover current OpenRouter zero-price text models' \
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

provider-build:
	docker compose --env-file .env build provider

ci: validate-template
	python3 -m py_compile scripts/sync-free-models.py services/model_catalog/catalog.py
	python3 -m compileall -q services/provider/zeaz_provider
	python3 -m unittest tests.test_model_catalog -v
	bash -n scripts/install.sh
	bash -n scripts/doctor.sh
