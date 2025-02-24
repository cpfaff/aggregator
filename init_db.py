import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
import bcrypt
from main import UserModel

# Load environment variables
load_dotenv('config.env')

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_admin():
    async with async_session() as session:
        # Check if admin already exists
        admin = await session.get(UserModel, 1)
        if admin is None:
            # Create admin user
            hashed_password = bcrypt.hashpw("admin".encode(), bcrypt.gensalt()).decode()
            admin = UserModel(
                username="admin",
                hashed_password=hashed_password,
                is_global_admin=True,
                provider_roles={}
            )
            session.add(admin)
            await session.commit()
            print("Admin user created successfully!")
        else:
            print("Admin user already exists!")

async def main():
    await init_admin()

if __name__ == "__main__":
    asyncio.run(main())
