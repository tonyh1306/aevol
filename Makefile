.PHONY: up down build logs ps shell-backend shell-worker migrate seed scale-workers clean

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

ps:
	docker compose ps

# Run with hot-reload (uses override)
dev:
	docker compose -f docker-compose.yml -f docker-compose.override.yml up

shell-backend:
	docker compose exec backend bash

shell-worker:
	docker compose exec worker bash

migrate:
	docker compose exec backend alembic upgrade head

seed:
	docker compose exec backend python /scripts/seed_demo_data.py

# Scale workers: make scale-workers N=5
scale-workers:
	docker compose up -d --scale worker=$(N)

clean:
	docker compose down -v --remove-orphans
	docker system prune -f

# Run backend tests
test-backend:
	docker compose exec backend pytest tests/ -v

# Print live queue depths
queue-stats:
	docker compose exec redis redis-cli ZCARD eval:queue:normal
	docker compose exec redis redis-cli ZCARD eval:queue:retry
	docker compose exec redis redis-cli LLEN eval:queue:dead
