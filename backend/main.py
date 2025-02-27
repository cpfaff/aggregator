from fastapi import FastAPI, HTTPException, Depends, status, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, AnyUrl
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import jwt
import bcrypt
import os
import sys
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

# Load environment variables - try multiple locations
# Docker will provide env vars directly, but for local dev we might need a file
# First check if variables are already in the environment (set by Docker)
if not os.getenv("DATABASE_URL"):
    # If not, try to load from .env files
    if os.path.exists('../.env'):
        load_dotenv('../.env')
    elif os.path.exists('.env'):
        load_dotenv('.env')
    elif os.path.exists('config.env'):  # For backward compatibility
        load_dotenv('config.env')

# SQLAlchemy async imports
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, relationship, declarative_base, selectinload
from sqlalchemy import Column, Integer, String, Boolean, JSON, ForeignKey, select, and_

# ------------------- Configuration & Database Setup -------------------
DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()

# Dependency to get DB session per request
async def get_db():
    async with async_session() as session:
        yield session

# ------------------- ORM Models -------------------
class UserModel(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    provider_roles = Column(JSON, default={})
    is_global_admin = Column(Boolean, default=False)

class DataProviderModel(Base):
    __tablename__ = "data_providers"
    id = Column(Integer, primary_key=True, index=True)
    datacenter = Column(String)
    shortName = Column(String)
    name = Column(String)
    url = Column(String, nullable=True)
    biocaseUrl = Column(String, nullable=True)
    datasets = relationship("DatasetModel", back_populates="provider", cascade="all, delete-orphan")

class DatasetModel(Base):
    __tablename__ = "datasets"
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("data_providers.id"))
    source = Column(String)
    title = Column(String)
    landingPageUrl = Column(String, nullable=True)
    provider = relationship("DataProviderModel", back_populates="datasets")
    xmlArchives = relationship("XmlArchiveModel", back_populates="dataset", cascade="all, delete-orphan")
    usefulLinks = relationship("UsefulLinkModel", back_populates="dataset", cascade="all, delete-orphan")

class XmlArchiveModel(Base):
    __tablename__ = "xml_archives"
    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"))
    url = Column(String)
    isLatest = Column(Boolean)
    dataset = relationship("DatasetModel", back_populates="xmlArchives")

class UsefulLinkModel(Base):
    __tablename__ = "useful_links"
    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"))
    title = Column(String)
    url = Column(String)
    isLatest = Column(Boolean)
    dataset = relationship("DatasetModel", back_populates="usefulLinks")

# ------------------- Pydantic Models -------------------

# Authentication settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# User models
class User(BaseModel):
    username: str
    provider_roles: Dict[str, str]  # storing keys as strings for JSON compatibility
    is_global_admin: bool = False

    class Config:
        orm_mode = True

class UserCreate(BaseModel):
    username: str
    password: str
    provider_roles: Optional[Dict[str, str]] = {}
    is_global_admin: bool = False

class UserUpdate(BaseModel):
    password: Optional[str] = None
    provider_roles: Optional[Dict[str, str]] = None
    is_global_admin: Optional[bool] = None

class UserPermissions(BaseModel):
    username: str
    is_global_admin: bool
    provider_roles: Dict[str, str]

    class Config:
        orm_mode = True

# Data Provider and nested resource models
class XmlArchive(BaseModel):
    id: Optional[int] = None  # Keep id for responses
    url: AnyUrl
    isLatest: bool

    class Config:
        from_attributes = True
        populate_by_name = True
        json_encoders = {
            AnyUrl: str
        }

class UsefulLink(BaseModel):
    id: Optional[int] = None  # Keep id for responses
    title: str
    url: AnyUrl
    isLatest: bool

    class Config:
        from_attributes = True
        populate_by_name = True
        json_encoders = {
            AnyUrl: str
        }

class Dataset(BaseModel):
    id: Optional[int] = None
    source: str
    title: str
    landingPageUrl: Optional[AnyUrl] = None
    xmlArchives: List[XmlArchive] = []
    usefulLinks: List[UsefulLink] = []

    def dict(self, *args, **kwargs):
        # Override dict to exclude empty lists
        data = super().dict(*args, **kwargs)
        if not data.get('xmlArchives'):
            data.pop('xmlArchives', None)
        if not data.get('usefulLinks'):
            data.pop('usefulLinks', None)
        return data

    class Config:
        from_attributes = True
        populate_by_name = True
        json_encoders = {
            AnyUrl: str
        }

class DataProvider(BaseModel):
    id: Optional[int] = None
    datacenter: str
    shortName: str
    name: str
    url: Optional[AnyUrl] = None
    biocaseUrl: Optional[AnyUrl] = None
    datasets: List[Dataset] = []

    class Config:
        from_attributes = True
        populate_by_name = True
        json_encoders = {
            AnyUrl: str
        }

# Legacy harvesting models
class LegacyXmlArchive(BaseModel):
    archive_id: int
    xml_archive: AnyUrl
    latest: bool

class LegacyUsefulLink(BaseModel):
    link_id: int
    title: str
    url: AnyUrl
    is_latest: bool

class LegacyDataset(BaseModel):
    dataset_id: int
    datasource: str
    dataset: str
    custom_landingpage: Optional[AnyUrl]
    provider_id: int
    xml_archives: List[LegacyXmlArchive]
    useful_links: List[LegacyUsefulLink]
    provider_datacenter: str
    provider_shortname: str
    provider_name: str
    provider_url: Optional[AnyUrl]
    biocase_url: Optional[AnyUrl]

# Provider Association for users
class ProviderAssociation(BaseModel):
    provider_id: int
    role: str  # Expected values: "admin" or "curator"

# ------------------- FastAPI App Setup -------------------
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost", "http://localhost:80"],  # Allow both development and production ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Create tables at startup
@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# ------------------- Helper Functions -------------------
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        # Ensure proper encoding for bcrypt comparison
        if isinstance(plain_password, str):
            pwd_bytes = plain_password.encode('utf-8')
        else:
            pwd_bytes = plain_password
            
        if isinstance(hashed_password, str):
            hash_bytes = hashed_password.encode('utf-8')
        else:
            hash_bytes = hashed_password
            
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception as e:
        print(f"Error verifying password: {e}")
        return False

def hash_password(password: str) -> str:
    """
    Hash a password for storing in the database.
    Always returns a string.
    """
    if not password:
        # For create operations, this would be caught by pydantic validation
        # For update operations, we'll return empty to indicate "no change"
        return ""
    
    # Ensure password is bytes
    if isinstance(password, str):
        password_bytes = password.encode('utf-8')
    else:
        password_bytes = password
    
    # Generate salt and hash password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    
    # Ensure the hash is returned as a string
    if isinstance(hashed, bytes):
        return hashed.decode('utf-8')
    return hashed

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def normalize_provider_roles(roles):
    """
    Ensure provider_roles is always a clean dictionary.
    """
    if roles is None:
        return {}
    return dict(roles)

async def get_user_model(username: str, db: AsyncSession) -> Optional[UserModel]:
    result = await db.execute(select(UserModel).where(UserModel.username == username))
    return result.scalar_one_or_none()

async def authenticate_user(username: str, password: str, db: AsyncSession):
    print(f"Authenticating user: {username}")
    user_model = await get_user_model(username, db)
    print(f"Found user model: {user_model}")
    if not user_model:
        print("User not found")
        return None
    valid = verify_password(password, user_model.hashed_password)
    print(f"Password verification result: {valid}")
    if not valid:
        print(f"Invalid password. Expected hash: {user_model.hashed_password}")
        return None
    return user_model

def check_global_admin(current_user: UserModel):
    if not current_user.is_global_admin:
        raise HTTPException(status_code=403, detail="Operation requires global admin privileges")

def check_provider_permission(provider_id: int, current_user: UserModel, operation: str = "read"):
    # Global admins bypass permission check
    if current_user.is_global_admin:
        return
    roles = normalize_provider_roles(current_user.provider_roles)
    # Provider keys are stored as strings in the JSON column
    role = roles.get(str(provider_id))
    if role is None:
        raise HTTPException(status_code=403, detail="Operation not permitted for this provider")
    
    # Define allowed operations for each role
    if operation == "read":
        # All roles can read
        return
    elif operation == "write":
        # admin or curator can write/edit
        if role not in ["admin", "curator"]:
            raise HTTPException(status_code=403, detail="Write operation requires provider admin or curator privileges")
    elif operation == "delete":
        # Only admins can delete
        if role != "admin":
            raise HTTPException(status_code=403, detail="Delete operation requires provider admin privileges")

# ------------------- Authentication Endpoint -------------------
@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

# Dependency that decodes token and fetches user
async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> UserModel:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    user = await get_user_model(username, db)
    if user is None:
        raise credentials_exception
    return user

# ------------------- User Endpoints -------------------
@app.get("/me/permissions", response_model=UserPermissions)
async def get_user_permissions(current_user: UserModel = Depends(get_current_user)):
    # Ensure provider_roles is a clean dictionary to avoid JSON serialization issues
    provider_roles = normalize_provider_roles(current_user.provider_roles)
    
    return UserPermissions(
        username=current_user.username,
        is_global_admin=current_user.is_global_admin,
        provider_roles=provider_roles
    )

@app.get("/users", response_model=List[User])
async def list_users(current_user: UserModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    check_global_admin(current_user)
    result = await db.execute(select(UserModel))
    users = result.scalars().all()
    return users

@app.get("/users/{username}", response_model=User)
async def get_user_endpoint(username: str, current_user: UserModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    check_global_admin(current_user)
    user_obj = await get_user_model(username, db)
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")
    return user_obj

@app.post("/users", response_model=User, status_code=201)
async def create_user(user: UserCreate, current_user: UserModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    check_global_admin(current_user)
    existing = await get_user_model(user.username, db)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Generate password hash properly
    hashed_pw = hash_password(user.password)
    
    # Ensure provider_roles is a clean dictionary
    provider_roles = normalize_provider_roles(user.provider_roles)
    
    user_obj = UserModel(
        username=user.username,
        hashed_password=hashed_pw,
        provider_roles=provider_roles,
        is_global_admin=user.is_global_admin
    )
    db.add(user_obj)
    await db.commit()
    await db.refresh(user_obj)
    return user_obj

@app.put("/users/{username}", response_model=User)
async def update_user(username: str, user_update: UserUpdate, current_user: UserModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    check_global_admin(current_user)
    user_obj = await get_user_model(username, db)
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Track if we made any changes that need to be committed
    changes_made = False
    
    if user_update.password is not None:
        # Only update password if non-empty (UI might send empty string)
        hashed_pw = hash_password(user_update.password)
        if hashed_pw:  # Only update if we got a real hash
            user_obj.hashed_password = hashed_pw
            changes_made = True
        
    if user_update.provider_roles is not None:
        # Make sure we're working with a proper dictionary to avoid JSON serialization issues
        user_obj.provider_roles = normalize_provider_roles(user_update.provider_roles)
        changes_made = True
        
    if user_update.is_global_admin is not None:
        user_obj.is_global_admin = user_update.is_global_admin
        changes_made = True
    
    # Only commit changes if we actually modified something
    if changes_made:
        db.add(user_obj)
        await db.commit()
        await db.refresh(user_obj)
    
    return user_obj

@app.delete("/users/{username}", status_code=204)
async def delete_user(username: str, current_user: UserModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    check_global_admin(current_user)
    user_obj = await get_user_model(username, db)
    if user_obj:
        await db.delete(user_obj)
        await db.commit()
    else:
        raise HTTPException(status_code=404, detail="User not found")
    return

# Provider association endpoints
@app.post("/users/{username}/providers", response_model=User)
async def add_provider_association(username: str, association: ProviderAssociation, current_user: UserModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    check_global_admin(current_user)
    user_obj = await get_user_model(username, db)
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")
    roles = normalize_provider_roles(user_obj.provider_roles)
    roles[str(association.provider_id)] = association.role
    user_obj.provider_roles = roles
    db.add(user_obj)
    await db.commit()
    await db.refresh(user_obj)
    return user_obj

@app.put("/users/{username}/providers/{provider_id}", response_model=User)
async def update_provider_association(username: str, provider_id: int, association: ProviderAssociation, current_user: UserModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    check_global_admin(current_user)
    user_obj = await get_user_model(username, db)
    if not user_obj or not (normalize_provider_roles(user_obj.provider_roles) and str(provider_id) in normalize_provider_roles(user_obj.provider_roles)):
        raise HTTPException(status_code=404, detail="User or association not found")
    roles = normalize_provider_roles(user_obj.provider_roles)
    roles[str(provider_id)] = association.role
    user_obj.provider_roles = roles
    db.add(user_obj)
    await db.commit()
    await db.refresh(user_obj)
    return user_obj

@app.delete("/users/{username}/providers/{provider_id}", response_model=User)
async def remove_provider_association(username: str, provider_id: int, current_user: UserModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    check_global_admin(current_user)
    user_obj = await get_user_model(username, db)
    if not user_obj or not (normalize_provider_roles(user_obj.provider_roles) and str(provider_id) in normalize_provider_roles(user_obj.provider_roles)):
        raise HTTPException(status_code=404, detail="User or association not found")
    roles = normalize_provider_roles(user_obj.provider_roles)
    roles.pop(str(provider_id))
    user_obj.provider_roles = roles
    db.add(user_obj)
    await db.commit()
    await db.refresh(user_obj)
    return user_obj

# ------------------- Data Provider & Nested Resources Endpoints -------------------
@app.get("/providers", response_model=List[DataProvider])
async def get_providers(current_user: UserModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.is_global_admin:
        result = await db.execute(
            select(DataProviderModel)
            .options(
                selectinload(DataProviderModel.datasets)
                .selectinload(DatasetModel.xmlArchives),
                selectinload(DataProviderModel.datasets)
                .selectinload(DatasetModel.usefulLinks)
            )
        )
        return result.scalars().all()
    
    # Extract numeric IDs from provider role keys (e.g., 'provider1' -> 1)
    allowed_ids = []
    if normalize_provider_roles(current_user.provider_roles):
        for key in normalize_provider_roles(current_user.provider_roles).keys():
            try:
                # Extract the numeric part from the key (e.g., 'provider1' -> '1')
                numeric_part = ''.join(filter(str.isdigit, key))
                if numeric_part:
                    allowed_ids.append(int(numeric_part))
            except ValueError:
                continue

    result = await db.execute(
        select(DataProviderModel)
        .where(DataProviderModel.id.in_(allowed_ids))
        .options(
            selectinload(DataProviderModel.datasets)
            .selectinload(DatasetModel.xmlArchives),
            selectinload(DataProviderModel.datasets)
            .selectinload(DatasetModel.usefulLinks)
        )
    )
    return result.scalars().all()

@app.get("/providers/{provider_id}", response_model=DataProvider)
async def get_provider(provider_id: int, current_user: UserModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    check_provider_permission(provider_id, current_user)
    
    result = await db.execute(
        select(DataProviderModel)
        .where(DataProviderModel.id == provider_id)
        .options(
            selectinload(DataProviderModel.datasets)
            .selectinload(DatasetModel.xmlArchives),
            selectinload(DataProviderModel.datasets)
            .selectinload(DatasetModel.usefulLinks)
        )
    )
    provider = result.scalar_one_or_none()
    
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    return provider

@app.post("/providers", response_model=DataProvider, status_code=201)
async def create_provider(provider: DataProvider, current_user: UserModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    check_global_admin(current_user)
    
    # Create provider without datasets first
    provider_data = provider.dict(exclude={'datasets', 'id'}, exclude_unset=True)
    # Convert AnyUrl fields to strings
    if provider_data.get('url'):
        provider_data['url'] = str(provider_data['url'])
    if provider_data.get('biocaseUrl'):
        provider_data['biocaseUrl'] = str(provider_data['biocaseUrl'])
    
    provider_obj = DataProviderModel(**provider_data)
    
    # Create and attach datasets if present
    if provider.datasets:
        for dataset in provider.datasets:
            dataset_data = dataset.dict(exclude={'id', 'xmlArchives', 'usefulLinks'}, exclude_unset=True)
            if dataset_data.get('landingPageUrl'):
                dataset_data['landingPageUrl'] = str(dataset_data['landingPageUrl'])
            
            db_dataset = DatasetModel(**dataset_data)
            
            # Handle XML archives if provided and not empty
            if dataset.xmlArchives and len(dataset.xmlArchives) > 0:
                for archive in dataset.xmlArchives:
                    db_dataset.xmlArchives.append(
                        XmlArchiveModel(
                            url=str(archive.url),
                            isLatest=archive.isLatest
                        )
                    )
            
            # Handle useful links if provided and not empty
            if dataset.usefulLinks and len(dataset.usefulLinks) > 0:
                for link in dataset.usefulLinks:
                    db_dataset.usefulLinks.append(
                        UsefulLinkModel(
                            title=link.title,
                            url=str(link.url),
                            isLatest=link.isLatest
                        )
                    )
            
            provider_obj.datasets.append(db_dataset)
    
    db.add(provider_obj)
    await db.commit()
    await db.refresh(provider_obj)
    
    # Explicitly load all relationships
    result = await db.execute(
        select(DataProviderModel)
        .options(
            selectinload(DataProviderModel.datasets)
            .selectinload(DatasetModel.xmlArchives),
            selectinload(DataProviderModel.datasets)
            .selectinload(DatasetModel.usefulLinks)
        )
        .where(DataProviderModel.id == provider_obj.id)
    )
    return result.scalar_one()

@app.put("/providers/{provider_id}", response_model=DataProvider)
async def update_provider(provider_id: int, provider: DataProvider, current_user: UserModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Allow admins or curators of this provider to update it
    check_provider_permission(provider_id, current_user, "write")
    
    # Eager load relationships first
    result = await db.execute(
        select(DataProviderModel)
        .options(
            selectinload(DataProviderModel.datasets)
            .selectinload(DatasetModel.xmlArchives),
            selectinload(DataProviderModel.datasets)
            .selectinload(DatasetModel.usefulLinks)
        )
        .where(DataProviderModel.id == provider_id)
    )
    db_provider = result.scalar_one_or_none()
    
    if not db_provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Update provider fields
    provider_data = provider.dict(exclude={'datasets', 'id'}, exclude_unset=True)
    if provider_data.get('url'):
        provider_data['url'] = str(provider_data['url'])
    if provider_data.get('biocaseUrl'):
        provider_data['biocaseUrl'] = str(provider_data['biocaseUrl'])
    
    for key, value in provider_data.items():
        setattr(db_provider, key, value)
    
    # Add async context manager for dataset operations
    async with db.begin_nested():
        # Update nested datasets
        if provider.datasets is not None:
            # Create a map of existing datasets by ID for efficient lookup
            existing_datasets = {ds.id: ds for ds in db_provider.datasets if ds.id is not None}
            
            # Keep track of processed dataset IDs
            processed_dataset_ids = set()
            updated_datasets = []
            
            # Process each dataset in the update
            for dataset in provider.datasets:
                if dataset.id is not None and dataset.id in existing_datasets:
                    # Update existing dataset
                    db_dataset = existing_datasets[dataset.id]
                    processed_dataset_ids.add(dataset.id)
                    
                    dataset_data = dataset.dict(exclude={'id', 'xmlArchives', 'usefulLinks'}, exclude_unset=True)
                    # Convert AnyUrl fields to strings
                    if 'landingPageUrl' in dataset_data:
                        dataset_data['landingPageUrl'] = str(dataset_data['landingPageUrl']) if dataset_data['landingPageUrl'] else None
                    
                    for key, value in dataset_data.items():
                        setattr(db_dataset, key, value)
                    
                    # Update XML archives if provided and not empty
                    if dataset.xmlArchives is not None and len(dataset.xmlArchives) > 0:
                        # Create map of existing archives with valid IDs
                        existing_archives = {arch.id: arch for arch in db_dataset.xmlArchives if arch.id is not None}
                        new_archives = []
                        
                        for archive in dataset.xmlArchives:
                            # Only consider it an existing archive if ID is not None AND it exists in our map
                            if archive.id is not None and archive.id in existing_archives:
                                db_archive = existing_archives[archive.id]
                                archive_data = archive.dict(exclude={'id'}, exclude_unset=True)
                                # Convert URL fields to strings
                                if 'url' in archive_data:
                                    archive_data['url'] = str(archive_data['url'])
                                for key, value in archive_data.items():
                                    setattr(db_archive, key, value)
                                new_archives.append(db_archive)
                            else:
                                # For new archive, ignore any provided ID
                                new_archive = XmlArchiveModel(
                                    url=str(archive.url),
                                    isLatest=archive.isLatest,
                                    dataset_id=db_dataset.id
                                )
                                db.add(new_archive) # Add to session to ensure it gets a new ID assigned
                                await db.flush()
                                new_archives.append(new_archive)
                        
                        # Replace the archives collection only if we have new archives
                        if new_archives:
                            db_dataset.xmlArchives = new_archives
                    
                    # Update useful links if provided and not empty
                    if dataset.usefulLinks is not None and len(dataset.usefulLinks) > 0:
                        # Create map of existing links with valid IDs
                        existing_links = {link.id: link for link in db_dataset.usefulLinks if link.id is not None}
                        new_links = []
                        
                        for link in dataset.usefulLinks:
                            # Only consider it an existing link if ID is not None AND it exists in our map
                            if link.id is not None and link.id in existing_links:
                                db_link = existing_links[link.id]
                                link_data = link.dict(exclude={'id'}, exclude_unset=True)
                                # Convert URL fields to strings
                                if 'url' in link_data:
                                    link_data['url'] = str(link_data['url'])
                                for key, value in link_data.items():
                                    setattr(db_link, key, value)
                                new_links.append(db_link)
                            else:
                                # For new link, ignore any provided ID
                                new_link = UsefulLinkModel(
                                    title=link.title,
                                    url=str(link.url),
                                    isLatest=link.isLatest,
                                    dataset_id=db_dataset.id
                                )
                                db.add(new_link) # Add to session to ensure it gets a new ID assigned
                                await db.flush()
                                new_links.append(new_link)
                        
                        # Replace the links collection only if we have new links
                        if new_links:
                            db_dataset.usefulLinks = new_links
                    
                    updated_datasets.append(db_dataset)
                else:
                    # Create new dataset, ignore any provided ID
                    new_dataset = DatasetModel(
                        provider_id=db_provider.id,
                        source=dataset.source,
                        title=dataset.title,
                        landingPageUrl=str(dataset.landingPageUrl) if dataset.landingPageUrl else None
                    )
                    
                    # Add XML archives if they exist, ignoring any client-provided IDs
                    if dataset.xmlArchives and len(dataset.xmlArchives) > 0:
                        for archive in dataset.xmlArchives:
                            new_dataset.xmlArchives.append(
                                XmlArchiveModel(
                                    url=str(archive.url),
                                    isLatest=archive.isLatest
                                )
                            )
                    
                    # Add useful links if they exist, ignoring any client-provided IDs
                    if dataset.usefulLinks and len(dataset.usefulLinks) > 0:
                        for link in dataset.usefulLinks:
                            new_dataset.usefulLinks.append(
                                UsefulLinkModel(
                                    title=link.title,
                                    url=str(link.url),
                                    isLatest=link.isLatest
                                )
                            )
                    
                    updated_datasets.append(new_dataset)
            
            # Replace datasets collection
            db_provider.datasets = updated_datasets
    
    await db.commit()
    
    # Reload with fresh data
    result = await db.execute(
        select(DataProviderModel)
        .options(
            selectinload(DataProviderModel.datasets)
            .selectinload(DatasetModel.xmlArchives),
            selectinload(DataProviderModel.datasets)
            .selectinload(DatasetModel.usefulLinks)
        )
        .where(DataProviderModel.id == provider_id)
    )
    return result.scalar_one()

@app.delete("/providers/{provider_id}", status_code=204)
async def delete_provider(provider_id: int, current_user: UserModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    check_global_admin(current_user)
    result = await db.execute(select(DataProviderModel).where(DataProviderModel.id == provider_id))
    provider = result.scalar_one_or_none()
    if provider:
        await db.delete(provider)
        await db.commit()
    return

# Dataset endpoints
@app.get("/providers/{provider_id}/datasets", response_model=List[Dataset])
async def get_datasets(provider_id: int, current_user: UserModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    check_provider_permission(provider_id, current_user, "read")
    result = await db.execute(
        select(DatasetModel)
        .where(DatasetModel.provider_id == provider_id)
        .options(
            selectinload(DatasetModel.xmlArchives),
            selectinload(DatasetModel.usefulLinks)
        )
    )
    return result.scalars().all()

@app.get("/providers/{provider_id}/datasets/{dataset_id}", response_model=Dataset)
async def get_dataset(provider_id: int, dataset_id: int, current_user: UserModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    check_provider_permission(provider_id, current_user, "read")
    result = await db.execute(
        select(DatasetModel)
        .where(
            and_(
                DatasetModel.provider_id == provider_id,
                DatasetModel.id == dataset_id
            )
        )
        .options(
            selectinload(DatasetModel.xmlArchives),
            selectinload(DatasetModel.usefulLinks)
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset

@app.post("/providers/{provider_id}/datasets", response_model=Dataset, status_code=201)
async def create_dataset(
    provider_id: int,
    dataset: Dataset,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    check_provider_permission(provider_id, current_user, "write")
    
    # Verify provider exists
    result = await db.execute(
        select(DataProviderModel).where(DataProviderModel.id == provider_id)
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    # Explicitly exclude id fields from all levels
    dataset_data = dataset.dict(exclude={'id', 'xmlArchives', 'usefulLinks'}, exclude_unset=True)
    # Convert AnyUrl fields to strings
    if dataset_data.get('landingPageUrl'):
        dataset_data['landingPageUrl'] = str(dataset_data['landingPageUrl'])
    
    dataset_obj = DatasetModel(**dataset_data, provider_id=provider_id)
    
    # Add XML archives if they exist, ignoring any client-provided IDs
    if dataset.xmlArchives:
        for archive in dataset.xmlArchives:
            dataset_obj.xmlArchives.append(
                XmlArchiveModel(
                    url=str(archive.url),
                    isLatest=archive.isLatest
                )
            )
    
    # Add useful links if they exist, ignoring any client-provided IDs
    if dataset.usefulLinks:
        for link in dataset.usefulLinks:
            dataset_obj.usefulLinks.append(
                UsefulLinkModel(
                    title=link.title,
                    url=str(link.url),
                    isLatest=link.isLatest
                )
            )
    
    db.add(dataset_obj)
    await db.commit()
    await db.refresh(dataset_obj)
    
    # Explicitly load relationships
    result = await db.execute(
        select(DatasetModel)
        .options(
            selectinload(DatasetModel.xmlArchives),
            selectinload(DatasetModel.usefulLinks)
        )
        .where(DatasetModel.id == dataset_obj.id)
    )
    return result.scalar_one()

@app.put("/providers/{provider_id}/datasets/{dataset_id}", response_model=Dataset)
async def update_dataset(
    provider_id: int, 
    dataset_id: int, 
    dataset: Dataset, 
    current_user: UserModel = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    check_provider_permission(provider_id, current_user, "write")
    
    # Load the dataset with all nested resources
    result = await db.execute(
        select(DatasetModel)
        .options(
            selectinload(DatasetModel.xmlArchives),
            selectinload(DatasetModel.usefulLinks)
        )
        .where(
            and_(
                DatasetModel.provider_id == provider_id,
                DatasetModel.id == dataset_id
            )
        )
    )
    db_dataset = result.scalar_one_or_none()
    if not db_dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Update dataset basic fields
    dataset_data = dataset.dict(exclude={'id', 'xmlArchives', 'usefulLinks'}, exclude_unset=True)
    # Convert AnyUrl fields to strings
    if dataset_data.get('landingPageUrl'):
        dataset_data['landingPageUrl'] = str(dataset_data['landingPageUrl'])
    
    for key, value in dataset_data.items():
        setattr(db_dataset, key, value)
    
    # Update XML archives if provided and not empty
    if dataset.xmlArchives is not None and len(dataset.xmlArchives) > 0:
        # Create a map of existing archives with valid IDs
        existing_archives = {arch.id: arch for arch in db_dataset.xmlArchives if arch.id is not None}
        new_archives = []
        
        for archive in dataset.xmlArchives:
            # Only consider it an existing archive if ID is not None AND it exists in our map
            if archive.id is not None and archive.id in existing_archives:
                db_archive = existing_archives[archive.id]
                archive_data = archive.dict(exclude={'id'}, exclude_unset=True)
                # Convert URL fields to strings
                if 'url' in archive_data:
                    archive_data['url'] = str(archive_data['url'])
                for key, value in archive_data.items():
                    setattr(db_archive, key, value)
                new_archives.append(db_archive)
            else:
                # For new archive, ignore any provided ID
                new_archive = XmlArchiveModel(
                    url=str(archive.url),
                    isLatest=archive.isLatest,
                    dataset_id=db_dataset.id
                )
                db.add(new_archive) # Add to session to ensure it gets a new ID assigned
                await db.flush()
                new_archives.append(new_archive)
        
        # Replace the archives collection only if we have new archives
        if new_archives:
            db_dataset.xmlArchives = new_archives
    
    # Update useful links if provided and not empty
    if dataset.usefulLinks is not None and len(dataset.usefulLinks) > 0:
        # Create a map of existing links with valid IDs
        existing_links = {link.id: link for link in db_dataset.usefulLinks if link.id is not None}
        new_links = []
        
        for link in dataset.usefulLinks:
            # Only consider it an existing link if ID is not None AND it exists in our map
            if link.id is not None and link.id in existing_links:
                db_link = existing_links[link.id]
                link_data = link.dict(exclude={'id'}, exclude_unset=True)
                # Convert URL fields to strings
                if 'url' in link_data:
                    link_data['url'] = str(link_data['url'])
                for key, value in link_data.items():
                    setattr(db_link, key, value)
                new_links.append(db_link)
            else:
                # For new link, ignore any provided ID
                new_link = UsefulLinkModel(
                    title=link.title,
                    url=str(link.url),
                    isLatest=link.isLatest,
                    dataset_id=db_dataset.id
                )
                db.add(new_link) # Add to session to ensure it gets a new ID assigned
                await db.flush()
                new_links.append(new_link)
        
        # Replace the links collection only if we have new links
        if new_links:
            db_dataset.usefulLinks = new_links
    
    await db.commit()
    
    # Reload with fresh data
    result = await db.execute(
        select(DatasetModel)
        .options(
            selectinload(DatasetModel.xmlArchives),
            selectinload(DatasetModel.usefulLinks)
        )
        .where(DatasetModel.id == dataset_id)
    )
    return result.scalar_one()

@app.delete("/providers/{provider_id}/datasets/{dataset_id}", status_code=204)
async def delete_dataset(provider_id: int, dataset_id: int, current_user: UserModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    check_provider_permission(provider_id, current_user, "delete")
    result = await db.execute(
        select(DatasetModel).where(DatasetModel.id == dataset_id, DatasetModel.provider_id == provider_id)
    )
    dataset_obj = result.scalar_one_or_none()
    if not dataset_obj:
        raise HTTPException(status_code=404, detail="Dataset not found")
    await db.delete(dataset_obj)
    await db.commit()
    return

# XML Archive endpoints
@app.get("/providers/{provider_id}/datasets/{dataset_id}/xml-archives", response_model=List[XmlArchive])
async def get_xml_archives(provider_id: int, dataset_id: int, current_user: UserModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    check_provider_permission(provider_id, current_user, "read")
    result = await db.execute(
        select(XmlArchiveModel)
        .join(DatasetModel)
        .where(
            and_(
                DatasetModel.provider_id == provider_id,
                DatasetModel.id == dataset_id
            )
        )
    )
    return result.scalars().all()

@app.post("/providers/{provider_id}/datasets/{dataset_id}/xml-archives", response_model=XmlArchive, status_code=201)
async def create_xml_archive(
    provider_id: int,
    dataset_id: int,
    xml_archive: XmlArchive,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    check_provider_permission(provider_id, current_user, "write")
    
    # Verify dataset exists and belongs to provider
    result = await db.execute(
        select(DatasetModel)
        .where(
            and_(
                DatasetModel.provider_id == provider_id,
                DatasetModel.id == dataset_id
            )
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    xml_data = xml_archive.dict(exclude={'id', 'datasetId'}, exclude_unset=True)
    # Convert URL fields to strings
    if xml_data.get('url'):
        xml_data['url'] = str(xml_data['url'])
    
    xml_obj = XmlArchiveModel(**xml_data, dataset_id=dataset_id)
    db.add(xml_obj)
    await db.commit()
    await db.refresh(xml_obj)
    return xml_obj

# Useful Link endpoints
@app.get("/providers/{provider_id}/datasets/{dataset_id}/useful-links", response_model=List[UsefulLink])
async def get_useful_links(provider_id: int, dataset_id: int, current_user: UserModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    check_provider_permission(provider_id, current_user, "read")
    result = await db.execute(
        select(UsefulLinkModel)
        .join(DatasetModel)
        .where(
            and_(
                DatasetModel.provider_id == provider_id,
                DatasetModel.id == dataset_id
            )
        )
    )
    return result.scalars().all()

@app.post("/providers/{provider_id}/datasets/{dataset_id}/useful-links", response_model=UsefulLink, status_code=201)
async def create_useful_link(
    provider_id: int,
    dataset_id: int,
    useful_link: UsefulLink,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    check_provider_permission(provider_id, current_user, "write")
    
    # Verify dataset exists and belongs to provider
    result = await db.execute(
        select(DatasetModel)
        .where(
            and_(
                DatasetModel.provider_id == provider_id,
                DatasetModel.id == dataset_id
            )
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    link_data = useful_link.dict(exclude={'id', 'datasetId'}, exclude_unset=True)
    # Convert URL fields to strings
    if link_data.get('url'):
        link_data['url'] = str(link_data['url'])
    
    link_obj = UsefulLinkModel(**link_data, dataset_id=dataset_id)
    db.add(link_obj)
    await db.commit()
    await db.refresh(link_obj)
    return link_obj

# ------------------- Health Check Endpoint -------------------
@app.get("/health", status_code=200)
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        # Check database connection
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

# ------------------- Legacy Harvesting Endpoint -------------------
@app.get("/harvest/datasets", response_model=List[LegacyDataset])
async def harvest_datasets(db: AsyncSession = Depends(get_db)):
    # Get all providers with their relationships loaded
    result = await db.execute(
        select(DataProviderModel)
        .options(
            selectinload(DataProviderModel.datasets)
            .selectinload(DatasetModel.xmlArchives),
            selectinload(DataProviderModel.datasets)
            .selectinload(DatasetModel.usefulLinks)
        )
        .order_by(DataProviderModel.id)  # Sort providers by ID
    )
    providers = result.scalars().all()
    
    legacy_list = []
    for provider in providers:
        # Sort datasets by ID
        sorted_datasets = sorted(provider.datasets, key=lambda ds: ds.id)
        
        for ds in sorted_datasets:
            # Sort xmlArchives and usefulLinks by their IDs
            sorted_xml_archives = sorted(ds.xmlArchives, key=lambda xml: xml.id)
            sorted_useful_links = sorted(ds.usefulLinks, key=lambda link: link.id)
            
            legacy_ds = LegacyDataset(
                dataset_id=ds.id,
                datasource=ds.source,
                dataset=ds.title,
                custom_landingpage=ds.landingPageUrl,
                provider_id=provider.id,
                xml_archives=[
                    LegacyXmlArchive(
                        archive_id=xml.id,
                        xml_archive=xml.url,
                        latest=xml.isLatest
                    ) for xml in sorted_xml_archives
                ],
                useful_links=[
                    LegacyUsefulLink(
                        link_id=link.id,
                        title=link.title,
                        url=link.url,
                        is_latest=link.isLatest
                    ) for link in sorted_useful_links
                ],
                provider_datacenter=provider.datacenter,
                provider_shortname=provider.shortName,
                provider_name=provider.name,
                provider_url=provider.url,
                biocase_url=provider.biocaseUrl
            )
            legacy_list.append(legacy_ds)
    
    # Finally, sort the entire legacy_list by dataset_id
    legacy_list.sort(key=lambda legacy_ds: legacy_ds.dataset_id)
    
    return legacy_list
