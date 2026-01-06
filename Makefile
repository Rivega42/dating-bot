.PHONY: help install start stop restart logs status backup health clean

COMPOSE = docker compose

help:
	@echo "Dating Bot Platform - Commands:"
	@echo "  make start      - Start all services"
	@echo "  make stop       - Stop all services"
	@echo "  make restart    - Restart all services"
	@echo "  make logs       - View logs"
	@echo "  make status     - Service status"
	@echo "  make health     - Health check"
	@echo "  make backup     - Create backup"

start:
	@$(COMPOSE) up -d
	@$(COMPOSE) ps

stop:
	@$(COMPOSE) down

restart:
	@$(COMPOSE) restart

rebuild:
	@$(COMPOSE) up -d --build

logs:
	@$(COMPOSE) logs -f --tail=100

logs-api:
	@$(COMPOSE) logs -f --tail=100 api

logs-worker:
	@$(COMPOSE) logs -f --tail=100 worker

status:
	@$(COMPOSE) ps

health:
	@chmod +x scripts/health-check.sh
	@./scripts/health-check.sh

backup:
	@chmod +x scripts/backup.sh
	@./scripts/backup.sh full

shell-api:
	@$(COMPOSE) exec api /bin/bash

shell-worker:
	@$(COMPOSE) exec worker /bin/bash

shell-redis:
	@$(COMPOSE) exec redis redis-cli -a $${REDIS_PASSWORD}

clean:
	@echo "Warning: This will remove all containers and volumes!"
	@$(COMPOSE) down -v --remove-orphans
	@docker system prune -f

update:
	@git pull
	@$(COMPOSE) pull
	@$(COMPOSE) up -d --build
