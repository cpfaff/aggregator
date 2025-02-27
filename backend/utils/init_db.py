import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from dotenv import load_dotenv
import os
import bcrypt
from main import UserModel

# Load environment variables
load_dotenv('../../.env')

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_admin():
    async with async_session() as session:
        # Find existing admin by username
        result = await session.execute(
            select(UserModel).where(UserModel.username == "admin")
        )
        admin = result.scalar_one_or_none()
        
        # Generate new password hash
        salt = bcrypt.gensalt()
        print(f"Using salt: {salt}")
        hashed_password = bcrypt.hashpw("admin".encode('utf-8'), salt).decode('utf-8')
        print(f"Generated hash: {hashed_password}")
        
        if admin:
            # Update existing admin
            print("Updating existing admin user")
            admin.hashed_password = hashed_password
            admin.is_global_admin = True
            admin.provider_roles = {}
        else:
            # Create new admin
            print("Creating new admin user")
            admin = UserModel(
                username="admin",
                hashed_password=hashed_password,
                is_global_admin=True,
                provider_roles={}
            )
            session.add(admin)
        
        await session.commit()
        print("Admin user updated/created successfully!")

async def main():
    await init_admin()

if __name__ == "__main__":
    asyncio.run(main())
