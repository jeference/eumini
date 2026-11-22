# EuMini: comandos de desenvolvimento. O backend usa um venv isolado em apps/backend/.venv.
# Funciona em cmd.exe e sh. pnpm roda via npx para dispensar instalação global.

BACKEND := apps/backend
ifeq ($(OS),Windows_NT)
PY := ".venv/Scripts/python.exe"
else
PY := .venv/bin/python
endif
PNPM ?= npx --yes pnpm@9.15.9

.PHONY: install db backend backend-tunnel simulate-pix verification-code worker scheduler frontend types migrate makemigrations test test-backend test-web lint fmt build prod-local prod-local-down deploy

install:
	cd $(BACKEND) && uv venv --python 3.12 .venv && uv pip install --python $(PY) -e ".[dev]"
	$(PNPM) install

# Postgres local sem Docker, instalado no venv (porta 5433). Fica em primeiro plano.
db:
	cd $(BACKEND) && $(PY) scripts/dev_db.py

backend:
	cd $(BACKEND) && $(PY) manage.py runserver

# Expõe o backend local (porta 8000) na internet via ngrok, para o webhook do AbacatePay
# (/api/webhooks/abacatepay/). Rode em outro terminal, com `make backend` já de pé.
# Requer ngrok instalado e autenticado: `winget install Ngrok.Ngrok`, `ngrok update` (a
# versão do winget é antiga) e `ngrok config add-authtoken <token>`.
# Usa o domínio estático da conta, já registrado no webhook do AbacatePay. Outro domínio:
#   make backend-tunnel DOMAIN=outro-nome.ngrok-free.dev
# O host do túnel precisa estar em DJANGO_ALLOWED_HOSTS, senão o Django responde 400.
DOMAIN ?= doubtably-unrotten-stanford.ngrok-free.dev
backend-tunnel:
	ngrok http --domain=$(DOMAIN) 8000

# Simula o pagamento do PIX de um pedido pelo AbacatePay (devMode) e espera o webhook.
# Precisa de `make backend` e `make backend-tunnel` de pé.
#   make simulate-pix ORDER=KB... [TIMEOUT=120]
simulate-pix:
	$(if $(ORDER),,$(error Informe o pedido: make simulate-pix ORDER=KB...))
	cd $(BACKEND) && $(PY) manage.py simulate_pix_payment $(ORDER) $(if $(TIMEOUT),--timeout $(TIMEOUT),)

# Emite um código de verificação de e-mail novo e imprime no terminal, já que em dev não há
# e-mail real. Invalida o código anterior. Só roda com DEBUG=True.
#   make verification-code EMAIL=fulano@eumini.com
verification-code:
	$(if $(EMAIL),,$(error Informe o e-mail: make verification-code EMAIL=fulano@eumini.com))
	cd $(BACKEND) && $(PY) manage.py dev_tool_get_verification_code $(EMAIL)

worker:
	cd $(BACKEND) && $(PY) manage.py run_generation_worker

scheduler:
	cd $(BACKEND) && $(PY) manage.py run_scheduler

frontend:
	$(PNPM) --filter @eumini/consumer dev

migrate:
	cd $(BACKEND) && $(PY) manage.py migrate

makemigrations:
	cd $(BACKEND) && $(PY) manage.py makemigrations

# Contrato: OpenAPI do backend -> schema.yaml -> tipos do frontend.
types:
	cd $(BACKEND) && $(PY) manage.py spectacular --file ../../packages/api-types/schema.yaml --validate
	$(PNPM) --filter @eumini/api-types generate

test: test-backend test-web

test-backend:
	cd $(BACKEND) && $(PY) -m pytest

test-web:
	$(PNPM) -r test

lint:
	cd $(BACKEND) && $(PY) -m ruff check .
	$(PNPM) -r lint
	$(PNPM) -r typecheck

fmt:
	cd $(BACKEND) && $(PY) -m ruff check --fix . && $(PY) -m ruff format .
	$(PNPM) format

build:
	$(PNPM) --filter @eumini/consumer build

# --- Produção (infra/) ---
# Testa a produção na própria máquina: gera as imagens e sobe tudo, menos o túnel, com o site
# em http://127.0.0.1:3100. Precisa de infra/.env e infra/.env.app de teste.
PROD_LOCAL := docker compose -f compose.yml -f compose.local.yml
prod-local:
	cd infra && $(PROD_LOCAL) up -d --build --wait postgres
	cd infra && $(PROD_LOCAL) run --rm --build migrate
	cd infra && $(PROD_LOCAL) up -d --build --wait web worker scheduler consumer

prod-local-down:
	cd infra && $(PROD_LOCAL) down

# Publica o código desta pasta na produção (SSH com a chave em ~/.eumini).
deploy:
	bash infra/deploy.sh
