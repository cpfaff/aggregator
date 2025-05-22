.PHONY: help up down restart logs shell backup restore create-admin create-user migrate test format maintenance-on maintenance-off prod-up prod-down prod-restart

# Colors for terminal output
ifeq ($(shell tput colors 2>/dev/null || echo 0),0)
  # Terminal doesn't support colors
  GREEN=
  YELLOW=
  RED=
  NC=
else
  # Define colors with proper shell escaping
  GREEN=$(shell printf "\033[0;32m")
  YELLOW=$(shell printf "\033[0;33m")
  RED=$(shell printf "\033[0;31m")
  NC=$(shell printf "\033[0m") # No Color
endif

# Help command to list all available commands
help:
	@echo "${GREEN}Dataset Management Platform Development Tool${NC}"
	@echo ""
	@echo "${YELLOW}Usage:${NC}"
	@echo "  make [command]"
	@echo ""
	@echo "${YELLOW}Available Commands:${NC}"
	@echo "  ${GREEN}help${NC}               Show this help message"
	@echo "  ${GREEN}up${NC}                 Start the development environment"
	@echo "  ${GREEN}down${NC}               Stop the development environment"
	@echo "  ${GREEN}restart${NC}            Restart the development environment"
	@echo "  ${GREEN}logs${NC}               View logs from all services"
	@echo "  ${GREEN}logs-backend${NC}       View backend logs"
	@echo "  ${GREEN}logs-frontend${NC}      View frontend logs"
	@echo "  ${GREEN}logs-db${NC}            View database logs"
	@echo "  ${GREEN}shell-backend${NC}      Open a shell in the backend container"
	@echo "  ${GREEN}shell-frontend${NC}     Open a shell in the frontend container"
	@echo "  ${GREEN}backup-db${NC}          Create a database backup"
	@echo "  ${GREEN}restore-db${NC}         Restore database from backup"
	@echo "  ${GREEN}create-admin${NC}       Create a new admin user"
	@echo "  ${GREEN}create-user${NC}        Create a new regular user"
	@echo "  ${GREEN}migrate${NC}            Run database migrations"
	@echo "  ${GREEN}test${NC}               Run tests"
	@echo "  ${GREEN}format${NC}             Format code according to project standards"
	@echo "  ${GREEN}maintenance-on${NC}     Enable maintenance mode"
	@echo "  ${GREEN}maintenance-off${NC}    Disable maintenance mode"
	@echo "  ${GREEN}prod-up${NC}            Start production services"
	@echo "  ${GREEN}prod-down${NC}          Stop production services"
	@echo "  ${GREEN}prod-restart${NC}       Restart production services"
	@echo ""
	@echo "${YELLOW}Examples:${NC}"
	@echo "  make up                  # Start all containers"
	@echo "  make backup-db           # Create a timestamped database backup"
	@echo "  make create-admin        # Interactive prompt to create an admin user"
	@echo "  make create-user         # Interactive prompt to create a regular user"
	@echo "  make maintenance-on      # Enable maintenance mode for production"

# Docker compose commands
up:
	@echo "${GREEN}Starting development environment...${NC}"
	docker-compose -f ../docker-compose.merged.yml up -d --pull never
	@echo "${GREEN}Services are now running:${NC}"
	@echo "  Backend:  http://localhost:8000/api/v1"
	@echo "  Frontend: http://localhost:3000"
	@echo "  API Docs: http://localhost:8000/docs"

down:
	@echo "${RED}Stopping development environment...${NC}"
	docker-compose -f ../docker-compose.merged.yml down

restart:
	@echo "${YELLOW}Restarting development environment...${NC}"
	docker-compose -f ../docker-compose.merged.yml down
	docker-compose -f ../docker-compose.merged.yml up -d --pull never

# Logs
logs:
	docker-compose logs -f

logs-backend:
	docker logs -f searchgfbioorg-aggregator_backend-1

logs-frontend:
	docker logs -f searchgfbioorg-aggregator_frontend-1

logs-db:
	docker logs -f searchgfbioorg-postgres-1

# Shell access
shell-backend:
	docker exec -it searchgfbioorg-aggregator_backend-1 /bin/bash

shell-frontend:
	docker exec -it searchgfbioorg-aggregator_frontend-1 /bin/bash

# Database operations
backup-db:
	@echo "${GREEN}Creating database backup...${NC}"
	@mkdir -p backups
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	docker exec searchgfbioorg-postgres-1 pg_dump -U $${DB_USER:-user} $${DB_NAME:-dbname} > backups/db_backup_$${TIMESTAMP}.sql
	@echo "${GREEN}Backup created in backups/db_backup_$${TIMESTAMP}.sql${NC}"

restore-db:
	@echo "${YELLOW}Available backups:${NC}"
	@ls -1 backups/ | grep .sql | cat -n
	@echo ""
	@read -p "Enter backup number to restore: " number; \
	FILE=$$(ls -1 backups/ | grep .sql | sed -n $${number}p); \
	if [ -n "$$FILE" ]; then \
		echo "${YELLOW}Restoring from backups/$${FILE}...${NC}"; \
		docker exec -i searchgfbioorg-postgres-1 psql -U $${DB_USER:-user} $${DB_NAME:-dbname} < backups/$${FILE}; \
		echo "${GREEN}Database restored successfully!${NC}"; \
	else \
		echo "${RED}Invalid backup number${NC}"; \
	fi

# User management
create-admin:
	@echo "${GREEN}Creating new admin user...${NC}"
	@docker exec searchgfbioorg-aggregator_backend-1 python -m utils.manage_user --global-admin

create-user:
	@echo "${GREEN}Creating new regular user...${NC}"
	@echo "Please enter a username when prompted (do NOT use 'admin')."
	@read -p "Enter username for the new regular user: " username; \
	if [ -z "$$username" ]; then \
		echo "${RED}Username cannot be empty.${NC}"; \
		exit 1; \
	fi; \
	docker exec searchgfbioorg-aggregator_backend-1 python -m utils.manage_user --username $$username && \
	docker exec searchgfbioorg-aggregator_backend-1 python -m utils.update_regular_user $$username
	@echo "${GREEN}Regular user creation complete${NC}"

# Development tasks
migrate:
	@echo "${GREEN}Running database migrations...${NC}"
	@docker exec searchgfbioorg-aggregator_backend-1 alembic upgrade head

test:
	@echo "${GREEN}Running tests...${NC}"
	@docker exec searchgfbioorg-aggregator_backend-1 pytest

# Maintenance mode
maintenance-on:
	@echo "${YELLOW}Enabling maintenance mode...${NC}"
	@if [ -f "docker-compose.prod.registry.yml" ]; then \
		export BACKEND_TRAEFIK_ENABLED=false; \
		export FRONTEND_TRAEFIK_ENABLED=false; \
		export MAINTENANCE_TRAEFIK_ENABLED=true; \
		export IMAGE_TAG=$$(docker images docker.gitlab-pe.gwdg.de/gfbio/aggregator/backend --format "{{.Tag}}" | head -1); \
		echo "${YELLOW}Using image tag: $${IMAGE_TAG}${NC}"; \
		docker-compose -f docker-compose.prod.registry.yml down; \
		docker-compose -f docker-compose.prod.registry.yml up -d --no-build --pull never; \
		echo "${GREEN}Maintenance mode enabled.${NC}"; \
	else \
		echo "${RED}Error: docker-compose.prod.registry.yml not found.${NC}"; \
		exit 1; \
	fi

maintenance-off:
	@echo "${YELLOW}Disabling maintenance mode...${NC}"
	@if [ -f "docker-compose.prod.registry.yml" ]; then \
		export BACKEND_TRAEFIK_ENABLED=true; \
		export FRONTEND_TRAEFIK_ENABLED=true; \
		export MAINTENANCE_TRAEFIK_ENABLED=false; \
		export IMAGE_TAG=$$(docker images docker.gitlab-pe.gwdg.de/gfbio/aggregator/backend --format "{{.Tag}}" | head -1); \
		echo "${YELLOW}Using image tag: $${IMAGE_TAG}${NC}"; \
		docker-compose -f docker-compose.prod.registry.yml down; \
		docker-compose -f docker-compose.prod.registry.yml up -d --no-build --pull never; \
		echo "${GREEN}Maintenance mode disabled.${NC}"; \
	else \
		echo "${RED}Error: docker-compose.prod.registry.yml not found.${NC}"; \
		exit 1; \
	fi

# Production deployment commands
prod-up:
	@echo "${YELLOW}Starting production services...${NC}"
	@if [ -f "docker-compose.prod.registry.yml" ]; then \
		export IMAGE_TAG=$$(docker images docker.gitlab-pe.gwdg.de/gfbio/aggregator/backend --format "{{.Tag}}" | head -1); \
		echo "${YELLOW}Using image tag: $${IMAGE_TAG}${NC}"; \
		docker-compose -f docker-compose.prod.registry.yml up -d --no-build --pull never; \
		echo "${GREEN}Production services started.${NC}"; \
	else \
		echo "${RED}Error: docker-compose.prod.registry.yml not found.${NC}"; \
		exit 1; \
	fi

prod-down:
	@echo "${YELLOW}Stopping production services...${NC}"
	@if [ -f "docker-compose.prod.registry.yml" ]; then \
		docker-compose -f docker-compose.prod.registry.yml down; \
		echo "${GREEN}Production services stopped.${NC}"; \
	else \
		echo "${RED}Error: docker-compose.prod.registry.yml not found.${NC}"; \
		exit 1; \
	fi

prod-restart:
	@echo "${YELLOW}Restarting production services...${NC}"
	@if [ -f "docker-compose.prod.registry.yml" ]; then \
		export IMAGE_TAG=$$(docker images docker.gitlab-pe.gwdg.de/gfbio/aggregator/backend --format "{{.Tag}}" | head -1); \
		echo "${YELLOW}Using image tag: $${IMAGE_TAG}${NC}"; \
		docker-compose -f docker-compose.prod.registry.yml down; \
		docker-compose -f docker-compose.prod.registry.yml up -d --no-build --pull never; \
		echo "${GREEN}Production services restarted.${NC}"; \
	else \
		echo "${RED}Error: docker-compose.prod.registry.yml not found.${NC}"; \
		exit 1; \
	fi
