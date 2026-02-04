#!/usr/bin/env python3
import asyncio
import os
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from main import UserModel


async def make_regular_user(username):
    """Update a user to be a regular user (not global admin)."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)

    print(f"Updating permissions for user: {username}")

    # Create async engine
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Find user by username
        result = await session.execute(select(UserModel).where(UserModel.username == username))
        user = result.scalar_one_or_none()

        if user:
            # Update user permissions
            user.is_global_admin = False
            await session.commit()
            print(f"✅ User '{username}' updated to regular user (no admin privileges)")
        else:
            print(f"❌ Error: User '{username}' not found")
            sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m utils.update_regular_user <username>")
        sys.exit(1)

    username = sys.argv[1]
    asyncio.run(make_regular_user(username))
