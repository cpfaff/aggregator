# Aggregator

A full-stack application for managing scientific datasets and their providers.
Built with FastAPI backend and React frontend, containerized with Docker for
easy deployment.

<!-- Add a screenshot of your application here -->
<!-- ![Aggregator](docs/screenshot.png) -->

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Getting Started](#getting-started)
  - [For Users](#for-users)
  - [For Administrators](#for-administrators)
  - [For Developers](#for-developers)
- [Architecture](#architecture)
- [Environment Setup](#environment-setup)
- [Development Workflow](#development-workflow)
- [Production Deployment](#production-deployment)
- [API Documentation](#api-documentation)
- [Traefik Integration](#traefik-integration)
- [Maintenance Mode](#maintenance-mode)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Overview

Aggregator — branded the **Data Provider Manager** in its user interface — is
the registration front door to the GFBio Search and Harvesting Infrastructure
(SAHIS). Data centers and partner institutions use it to register the data
providers and datasets they contribute, validate their ABCD metadata, and mark
records as ready for publication. It publishes a harvest feed that the GFBio
harvester collects, and it reads back from the shared Elasticsearch search
index to report whether registered data has actually been published.

It does not store the harvested research records themselves; it manages the
registry, the data quality, and the publication status, and exposes a
comprehensive REST API for integration with other systems.

## Features

- **User Authentication and Authorization**
  - JWT-based authentication
  - Role-based access control
  - Provider-specific permissions

- **Provider Management**
  - Create, read, update, and delete data providers
  - Associate metadata with providers

- **Dataset Management**
  - Organize datasets under providers
  - Track dataset sources and landing pages
  - Manage XML archives and useful links

- **Metadata Validation**
  - ABCD XML validated against the TDWG ABCD schemas (2.06–3.0)
  - Per-dataset data-quality scoring with detailed reports
  - Runs asynchronously on Celery workers (Redis broker)

- **Harvesting & Statistics**
  - Publishes a harvest-ready feed for the GFBio panFMP harvester
    (`/api/v1/legacy-data-sets`)
  - Reads the shared Elasticsearch index to surface harvest status
  - Registry statistics: growth, data quality, provider/dataset counts

- **Modern Web Interface**
  - Responsive React-based frontend
  - User-friendly dashboard

- **API Integration**
  - RESTful API for all operations
  - Legacy harvesting support
  - Comprehensive documentation

## Getting Started

### For Users

As a user of Aggregator, you can:

1. **Access the Platform**:
   - Navigate to the application URL in your web browser
   - Log in with your provided credentials

2. **Browse Datasets**:
   - View available datasets organized by provider
   - Access dataset details and related resources

3. **Use Dataset Resources**:
   - Follow links to dataset landing pages
   - Access XML archives
   - Use provided useful links for additional information

### For Administrators

As an administrator, you have additional capabilities:

1. **User Management**:
   - Create new user accounts
   - Assign roles and permissions
   - Manage provider-specific access

2. **Provider Administration**:
   - Add new data providers to the system
   - Update provider information
   - Remove providers when necessary

3. **Dataset Administration**:
   - Add, update, or remove datasets
   - Manage dataset metadata
   - Organize datasets under appropriate providers

### For Developers

As a developer working with Aggregator:

1. **Local Development Setup**:
   ```bash
   # Clone the repository
   git clone <repository-url>
   cd aggregator

   # Copy and configure environment files
   cp .env.example .env
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env

   # IMPORTANT: Generate a secure SECRET_KEY for backend/.env:
   # python -c "import secrets; print(secrets.token_hex(32))"
   # Replace the default SECRET_KEY with your generated key

   # Start development environment
   docker-compose up
   ```

2. **Backend Development Setup**:

   **Prerequisites:**
   - Python 3.11+
   - Poetry 2.2.1 (matches the backend Docker image; `pip install poetry==2.2.1`)
   - Docker (for testcontainers and development environment)

   **Installation:**
   ```bash
   cd backend
   poetry install --with dev
   ```

   **Running Tests:**
   ```bash
   # Run all tests
   poetry run pytest tests/ -v

   # Run with coverage report
   poetry run pytest tests/ -v --cov=app --cov-report=term-missing
   ```

   **Testing with Testcontainers:**
   Tests use real PostgreSQL and Redis via Docker containers.
   Ensure Docker daemon is running before running tests.
   First test run may be slow (pulling images). Subsequent runs are faster (cached images).

   **Linting & Formatting:**
   ```bash
   # Check linting issues
   poetry run ruff check app/

   # Auto-fix linting issues
   poetry run ruff check --fix app/

   # Check formatting
   poetry run ruff format --check app/

   # Auto-format code
   poetry run ruff format app/
   ```

   **Code Quality:**
   Ruff (lint + format) is enforced in CI and via pre-commit. New code must pass
   `ruff check` and `ruff format --check` before merging.

3. **CI/CD Configuration**:

   **GitLab Runner Compatibility:**
   The CI pipeline supports both Docker executor and shell executor runners:

   - **Docker executor runners**: Jobs run inside containers with `docker:dind` service
   - **Shell executor runners**: Jobs run directly on host using host's Docker daemon

   The test jobs automatically detect the runner type and configure Docker access accordingly.

   **Requirements for shell executor runners:**
   ```bash
   # Docker must be installed and accessible to the gitlab-runner user
   sudo usermod -aG docker gitlab-runner

   # Verify Docker is accessible
   sudo -u gitlab-runner docker ps
   ```

   **Testing CI configuration locally:**
   ```bash
   # Install gitlab-runner (if not already installed)
   # See: https://docs.gitlab.com/runner/install/

   # Test a specific job
   gitlab-runner exec shell test-backend
   ```

4. **API Integration**:
   - Use the API documentation at `/docs` to understand available endpoints
   - Authenticate with JWT tokens
   - Make API calls to integrate with your systems

## Architecture

Aggregator is a containerized, modular application:

- **Backend**: FastAPI (async) application providing the RESTful API
- **Frontend**: React single-page application for the user interface
- **Database**: PostgreSQL for persistent storage (providers, datasets,
  validation jobs, archive snapshots, users)
- **Async workers**: Celery workers (heavy-validation and light/statistics
  queues) plus a beat scheduler, with Redis as broker and result backend
- **Validator**: a bundled ABCD XML validator used by the validation workers
- **Search index**: reads the shared GFBio Elasticsearch index (read-only) for
  harvest status and statistics
- **Reverse Proxy**: Traefik for routing, load balancing, and service discovery

### Traefik Integration

The application uses Traefik as a modern reverse proxy and load balancer:

- **Automatic Service Discovery**: Traefik automatically discovers services through Docker labels
- **Path-Based Routing**:
  - `/api/*` routes are directed to the backend service
  - All other routes are directed to the frontend service
- **Network Isolation**: Services are connected through a dedicated Docker network (`app-network`)
- **Security**:
  - Only containers explicitly enabled with `traefik.enable=true` label are exposed
  - SSL/TLS configuration (commented out but ready for production use)
  - API dashboard is disabled by default for security

To add a new service to Traefik:

1. Connect the service to the `app-network` in docker-compose
2. Add the following labels to your service:
   ```yaml
   labels:
     - "traefik.enable=true"
     - "traefik.http.routers.[service-name].rule=PathPrefix(`/your-path`)"
     - "traefik.http.routers.[service-name].entrypoints=web"
     - "traefik.http.services.[service-name].loadbalancer.server.port=[internal-port]"
   ```

For production deployments, uncomment and configure the HTTPS sections in `traefik/traefik.yml` and update the `acme.json` file permissions to 600.

## Maintenance Mode

The application includes a maintenance mode feature that can be enabled during deployments or updates:

### How Maintenance Mode Works

When enabled, a maintenance page is displayed to users while the application services are being updated. This is implemented using Traefik's dynamic routing rules:

- A dedicated `maintenance` container serves a static maintenance page
- The container has a higher priority route that intercepts all traffic
- Backend and frontend services are temporarily disabled in Traefik routing

### Enabling Maintenance Mode

#### Through GitLab CI/CD

1. **Using CI/CD Variables**:
   - In GitLab, go to Settings > CI/CD > Variables
   - Add variable `MAINTENANCE_MODE` with value `true`
   - Run a deployment to enable maintenance mode
   - Set back to `false` and re-deploy when maintenance is complete

2. **For a Single Deployment**:
   - When manually triggering a pipeline, set variable `MAINTENANCE_MODE=true`
   - After completing maintenance, run another deployment with `MAINTENANCE_MODE=false`

#### Manual Override on the Server

You can also directly enable/disable maintenance mode on the server:

```bash
# Enable maintenance mode
docker-compose exec traefik traefik service update --label-add "traefik.enable=true" maintenance
docker-compose exec traefik traefik service update --label-add "traefik.enable=false" backend
docker-compose exec traefik traefik service update --label-add "traefik.enable=false" frontend

# Disable maintenance mode
docker-compose exec traefik traefik service update --label-add "traefik.enable=false" maintenance
docker-compose exec traefik traefik service update --label-add "traefik.enable=true" backend
docker-compose exec traefik traefik service update --label-add "traefik.enable=true" frontend
```

### Customizing the Maintenance Page

The maintenance page is located at `/maintenance/index.html` and can be customized:

- **Content**: Modify the HTML to change the maintenance message
- **Styling**: Update the CSS in the style section
- **Countdown**: By default, the page shows a 30-minute countdown
- **Behavior**: The page will automatically refresh after the countdown ends

The maintenance page includes:
- GFBio branding
- Informative message about the maintenance
- Visual countdown timer
- Automatic refresh to check if the service is back online

## Environment Setup

The application uses environment variables for configuration:

1. **Root `.env` file**:
   ```
   # Database configuration
   DB_USER=user
   DB_PASSWORD=password
   DB_NAME=dbname

   # Security
   SECRET_KEY=your-secret-key

   # Frontend configuration (for development)
   REACT_APP_API_URL=http://localhost:8000
   ```

2. **Environment-specific configuration**:
   - Development: Uses local directories mounted as volumes for hot-reloading
   - Production: Uses built Docker images with optimized settings

## Development Workflow

1. **Start the Development Environment**:
   ```bash
   docker-compose up
   ```

2. **Backend Development**:
   - Edit files in the `backend/` directory
   - FastAPI hot-reloads changes automatically
   - Access API documentation at `http://localhost:8000/docs`

3. **Frontend Development**:
   - Edit files in the `frontend/` directory
   - React development server hot-reloads changes
   - Access frontend at `http://localhost:3000`

4. **Database Migrations**:
   ```bash
   # Inside the backend container
   alembic revision --autogenerate -m "description"
   alembic upgrade head
   ```

## Production Deployment

1. **Build and Start Production Services**:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

2. **Access the Application**:
   - Frontend: `http://your-server`
   - Backend API: `http://your-server/api`

3. **Scaling Considerations**:
   - Adjust memory limits in `docker-compose.prod.yml` if needed
   - Consider using a container orchestration platform for larger deployments

## API Documentation

Once the application is running, you can access:
- Interactive API documentation: `http://localhost:8000/docs` (development) or `http://your-server/api/docs` (production)
- Alternative API documentation: `http://localhost:8000/redoc` (development) or `http://your-server/api/redoc` (production)

## Troubleshooting

### Common Issues

1. **Database Connection Errors**:
   - Verify database credentials in `.env`
   - Ensure PostgreSQL service is running
   - Check network connectivity between containers

2. **Frontend Not Loading**:
   - Check browser console for JavaScript errors
   - Verify API URL configuration
   - Ensure Nginx is properly configured

3. **API Request Failures**:
   - Verify authentication token is valid
   - Check CORS configuration
   - Ensure proper permissions for the requested operation

4. **Docker Issues**:
   - Run `docker-compose down` and then `docker-compose up` to rebuild
   - Check Docker logs with `docker-compose logs`
   - Verify Docker and Docker Compose versions

5. **Traefik Routing Issues**:
   - Verify container labels are correctly configured
   - Check Traefik logs with `docker-compose logs traefik`
   - Ensure your service is connected to the `app-network`
   - Check that the container has `traefik.enable=true` label

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.
