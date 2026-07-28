COMPOSE = docker compose
COMPOSE_TEST = $(COMPOSE) -f docker-compose.yml -f docker-compose.tests.yml

.PHONY: up down logs test migrate

up:
	$(COMPOSE) up --build -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f app

test:
	$(COMPOSE_TEST) build app
	$(COMPOSE_TEST) run --rm app

migrate:
	$(COMPOSE) run --rm app alembic upgrade head
