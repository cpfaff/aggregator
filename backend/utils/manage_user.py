import asyncio
import sys
import os
import argparse
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from dotenv import load_dotenv
import bcrypt

"""
User Management Utility

This script provides a command-line interface for managing users in the database.
It can create new users or update existing ones with specified credentials and permissions.
The script is designed to work in any environment (local or Docker) and can be run
from anywhere by specifying the appropriate database connection.

Usage examples:
  # Create/update admin user with prompted password
  python -m utils.manage_user
  
  # Create/update a specific user with a specific password
  python -m utils.manage_user --username john.doe --password securepass123
  
  # Create a non-admin user
  python -m utils.manage_user --username regular.user --password userpass --global-admin false
  
  # Use a specific database connection
  python -m utils.manage_user --database-url postgresql://user:pass@localhost:5432/mydb
"""

# Add the parent directory to sys.path to allow importing from the backend directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import UserModel

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Manage users in the database - create new users or update existing ones.')
    parser.add_argument('--username', '-u', default='admin', help='Username for the user (default: admin)')
    parser.add_argument('--password', '-p', help='Password for the user. If not provided, will be prompted')
    parser.add_argument('--database-url', '-d', help='Database URL. If not provided, will use environment variable')
    parser.add_argument('--global-admin', '-g', action='store_true', default=True, 
                        help='Set the user as a global admin (default: True)')
    parser.add_argument('--env-file', '-e', help='Path to .env file')
    return parser.parse_args()

def get_password(args):
    """Get password from arguments or prompt if not provided."""
    if args.password:
        return args.password
    
    try:
        import getpass
        return getpass.getpass('Enter password for user: ')
    except ImportError:
        # Fallback if getpass is not available
        print('Enter password for user: ', end='', flush=True)
        return input()

def get_database_url(args):
    """Get database URL from arguments, environment variables, or .env files."""
    # First check if provided as argument
    if args.database_url:
        return args.database_url
    
    # Check if specific env file is provided
    if args.env_file and os.path.exists(args.env_file):
        load_dotenv(args.env_file)
        print(f"Loaded environment from {args.env_file}")
    else:
        # Try to load from backend/.env first, then from root .env
        env_paths = [
            Path(__file__).parent.parent / '.env',  # backend/.env
            Path(__file__).parent.parent.parent / '.env'  # root .env
        ]

        for env_path in env_paths:
            if env_path.exists():
                load_dotenv(env_path)
                print(f"Loaded environment from {env_path}")
                break
        else:
            print("No .env file found, using environment variables directly")
    
    # Get from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        print("Please provide a database URL using the --database-url option or set the DATABASE_URL environment variable")
        sys.exit(1)
    
    return database_url

async def init_user(username, password, database_url, is_global_admin=True):
    """Initialize or update a user in the database."""
    # Check if we're trying to connect to 'db' host which is the Docker service name
    # If running locally, we should use 'localhost' instead
    if 'db:' in database_url and not os.path.exists('/.dockerenv'):
        print("Detected Docker database URL but running locally, adjusting to localhost")
        database_url = database_url.replace('db:', 'localhost:')

    print(f"Using database URL: {database_url}")

    # Create async engine
    engine = create_async_engine(database_url, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Find existing user by username
        result = await session.execute(
            select(UserModel).where(UserModel.username == username)
        )
        user = result.scalar_one_or_none()
        
        # Generate password hash
        salt = bcrypt.gensalt()
        print(f"Using salt: {salt}")
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        
        if user:
            # Update existing user
            print(f"Updating existing user: {username}")
            user.hashed_password = hashed_password
            user.is_global_admin = is_global_admin
        else:
            # Create new user
            print(f"Creating new user: {username}")
            user = UserModel(
                username=username,
                hashed_password=hashed_password,
                is_global_admin=is_global_admin,
                provider_roles={}
            )
            session.add(user)
        
        await session.commit()
        print(f"User '{username}' {'updated' if user else 'created'} successfully!")
        if is_global_admin:
            print(f"User '{username}' has global admin privileges")

async def main():
    args = parse_arguments()
    password = get_password(args)
    database_url = get_database_url(args)
    
    await init_user(
        username=args.username,
        password=password,
        database_url=database_url,
        is_global_admin=args.global_admin
    )

if __name__ == "__main__":
    asyncio.run(main())
