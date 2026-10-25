COMPOSE := docker compose -f docker/docker-compose.yml

.PHONY: build compose-up compose-down smoke

build:
	$(COMPOSE) build

compose-up:
	$(COMPOSE) up -d --build
	$(COMPOSE) logs -f

compose-down:
	$(COMPOSE) down

smoke:
	python3 test/api_smoke.py
