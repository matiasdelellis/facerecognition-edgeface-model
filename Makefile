COMPOSE := docker compose -f docker/docker-compose.yml

.PHONY: build compose-up compose-start compose-logs compose-down smoke

build:
	$(COMPOSE) build

# Builds and starts it, then follows the logs (Ctrl+C stops following, not the service).
compose-up: compose-start compose-logs

# Builds and starts it in the background, without following the logs.
compose-start:
	$(COMPOSE) up -d --build

compose-logs:
	$(COMPOSE) logs -f

compose-down:
	$(COMPOSE) down

smoke:
	python3 test/api_smoke.py
