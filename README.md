# FastAPI Dataset Management API

A RESTful API built with FastAPI for managing datasets, providers, and their relationships. The API supports both modern REST endpoints and legacy harvesting functionality.

## Features

- User Authentication and Authorization with JWT
- Role-Based Access Control (RBAC)
- Provider Management
- Dataset Management
- XML Archive Management
- Useful Links Management
- Legacy Dataset Harvesting Support

## Requirements

- Python 3.8+
- PostgreSQL
- FastAPI
- SQLAlchemy
- Pydantic

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd fastapi
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables in `config.env`:
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost/dbname
SECRET_KEY=your-secret-key
```

5. Run the application:
```bash
uvicorn main:app --reload
```

## API Documentation

Once the application is running, you can access:
- Interactive API documentation: `http://localhost:8000/docs`
- Alternative API documentation: `http://localhost:8000/redoc`

## Authentication

The API uses JWT tokens for authentication. To obtain a token:
1. Create a user using the `/users` endpoint
2. Get a token using the `/token` endpoint

## License

[License Type] - See LICENSE file for details
