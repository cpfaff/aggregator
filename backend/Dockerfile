FROM python:3.11-slim

WORKDIR /app

# Install curl for health checks and Poetry
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
RUN pip install poetry==1.7.1

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies (without creating virtualenv in container)
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi

# Copy the rest of the application
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application with hot reload for development
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
