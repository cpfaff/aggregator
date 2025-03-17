# Dataset Management Platform

A full-stack application for managing scientific datasets and their providers.
Built with FastAPI backend and React frontend, containerized with Docker for
easy deployment.

![Dataset Management Platform](https://via.placeholder.com/800x400?text=Dataset+Management+Platform)

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
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Overview

The Dataset Management Platform is designed to catalog and manage scientific
datasets and their providers. It allows users to browse datasets,
administrators to manage user access, and provides a comprehensive API for
integration with other systems.

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

- **Modern Web Interface**
  - Responsive React-based frontend
  - User-friendly dashboard

- **API Integration**
  - RESTful API for all operations
  - Legacy harvesting support
  - Comprehensive documentation

## Getting Started

### For Users

As a user of the Dataset Management Platform, you can:

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

As a developer working with the Dataset Management Platform:

1. **Local Development Setup**:
   ```bash
   # Clone the repository
   git clone <repository-url>
   cd fastapi

   # Create environment file in the root directory
   # Example contents:
   # DB_USER=user
   # DB_PASSWORD=password
   # DB_NAME=dbname
   # SECRET_KEY=your-secret-key
   # REACT_APP_API_URL=http://localhost:8000
   
   # Start development environment
   docker-compose up
   ```

2. **API Integration**:
   - Use the API documentation at `/docs` to understand available endpoints
   - Authenticate with JWT tokens
   - Make API calls to integrate with your systems

## Architecture

The application follows a modern architecture:

- **Backend**: FastAPI (Python) with PostgreSQL database
- **Frontend**: React.js with component-based UI
- **Deployment**: Docker containers orchestrated with Docker Compose
- **Proxy**: Nginx for serving static content and API routing in production

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

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## License

[MIT License](LICENSE) - See LICENSE file for details
