# Utility Scripts

This directory contains utility scripts for managing the application.

## User Management

### `manage_user.py`

A command-line utility for managing users in the database. It can create new users or update existing ones with specified credentials and permissions.

#### Usage

```bash
# Create/update admin user with prompted password
python -m utils.manage_user

# Create/update a specific user with a specific password
python -m utils.manage_user --username john.doe --password securepass123

# Create a non-admin user
python -m utils.manage_user --username regular.user --password userpass --global-admin false

# Use a specific database connection
python -m utils.manage_user --database-url postgresql://user:pass@localhost:5432/mydb

# Use a specific .env file
python -m utils.manage_user --env-file /path/to/.env
```

#### Options

- `--username`, `-u`: Username for the user (default: admin)
- `--password`, `-p`: Password for the user. If not provided, will be prompted
- `--database-url`, `-d`: Database URL. If not provided, will use environment variable
- `--global-admin`, `-g`: Set the user as a global admin (default: True)
- `--env-file`, `-e`: Path to .env file

## Data Import

### `import_legacy_data.py`

A utility script for importing legacy data into the database. It reads data from JSON files and populates the database with providers, datasets, XML archives, and useful links.

#### Usage

```bash
# Import data from the default JSON file
python -m utils.import_legacy_data
```

The script will:
1. Load environment variables from .env files
2. Connect to the database (adjusting for local/Docker environments)
3. Clear existing data
4. Create an admin user
5. Import providers and their datasets from the JSON file
6. Reset database sequences

Note: This script is primarily for initial data setup or migration from legacy systems.
