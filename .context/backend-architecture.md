# Backend Architecture

## Overview

War Room backend is built with FastAPI and follows a modular architecture pattern with clear separation of concerns.

## Directory Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application setup
│   ├── config.py            # Configuration management
│   ├── database.py          # Database connection
│   │
│   ├── auth/                # Authentication module
│   │   ├── jwt.py
│   │   ├── middleware.py
│   │   └── dependencies.py
│   │
│   ├── api/                 # API routes
│   │   ├── __init__.py
│   │   ├── auth.py          # Auth endpoints
│   │   ├── users.py         # User management
│   │   ├── crm/             # CRM endpoints
│   │   └── social/          # Social media endpoints
│   │
│   ├── models/              # Database models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── crm.py
│   │   └── social.py
│   │
│   ├── schemas/             # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── crm.py
│   │   └── social.py
│   │
│   ├── services/            # Business logic
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── crm_service.py
│   │   └── social_service.py
│   │
│   └── utils/               # Utilities
│       ├── __init__.py
│       ├── security.py
│       └── helpers.py
│
├── tests/                   # Test suite
├── alembic/                 # Database migrations
├── requirements.txt         # Dependencies
└── Dockerfile              # Container definition
```

## Application Setup (main.py)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, users, crm, social
from app.auth.middleware import AuthMiddleware

app = FastAPI(title="War Room API", version="1.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication middleware
app.add_middleware(AuthMiddleware)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(crm.router, prefix="/api/crm", tags=["crm"])
app.include_router(social.router, prefix="/api/social", tags=["social"])
```

## Database Layer

### Connection Management (database.py)

```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Models (SQLAlchemy)

Models define database schema and relationships:

```python
# app/models/user.py
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    crm_contacts = relationship("Contact", back_populates="owner")
```

### Schemas (Pydantic)

Schemas handle data validation and serialization:

```python
# app/schemas/user.py
class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        orm_mode = True
```

## API Layer

### Route Handlers

```python
# app/api/users.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.dependencies import get_current_user
from app.schemas.user import UserResponse
from app.services.user_service import UserService

router = APIRouter()

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return current_user

@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_service = UserService(db)
    return user_service.get_users(skip=skip, limit=limit)
```

## Service Layer

Business logic is isolated in service classes:

```python
# app/services/user_service.py
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate
from app.utils.security import hash_password

class UserService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_user(self, user_data: UserCreate) -> User:
        hashed_password = hash_password(user_data.password)
        db_user = User(
            email=user_data.email,
            password_hash=hashed_password
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user
    
    def get_user_by_email(self, email: str) -> User:
        return self.db.query(User).filter(User.email == email).first()
```

## Configuration Management

```python
# app/config.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60
    
    # External API keys
    OPENAI_API_KEY: str
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    
    class Config:
        env_file = ".env"

settings = Settings()
```

## Error Handling

### Custom Exceptions

```python
# app/utils/exceptions.py
from fastapi import HTTPException

class AuthenticationError(HTTPException):
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(status_code=401, detail=detail)

class AuthorizationError(HTTPException):
    def __init__(self, detail: str = "Not authorized"):
        super().__init__(status_code=403, detail=detail)
```

### Global Error Handler

```python
# app/main.py
from fastapi.responses import JSONResponse

@app.exception_handler(AuthenticationError)
async def auth_exception_handler(request: Request, exc: AuthenticationError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "type": "authentication_error"}
    )
```

## Middleware

### Authentication Middleware

```python
# app/auth/middleware.py
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip auth for public endpoints
        if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Check authentication for protected routes
        if request.url.path.startswith("/api/") and not request.url.path.startswith("/api/auth/"):
            # Validate JWT token
            # ... authentication logic
            pass
        
        return await call_next(request)
```

## Testing

### Test Structure

```python
# tests/test_api/test_users.py
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from tests.conftest import override_get_db

client = TestClient(app)
app.dependency_overrides[get_db] = override_get_db

def test_get_current_user():
    response = client.get("/api/users/me", headers={"Authorization": "Bearer token"})
    assert response.status_code == 200
```

## Deployment

### Docker Configuration

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Setup

```bash
# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## Common Patterns

### Dependency Injection

```python
# Reusable dependencies
def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Usage in routes
@router.get("/protected")
async def protected_route(user: User = Depends(get_current_active_user)):
    return {"message": f"Hello {user.email}"}
```

### Database Transactions

```python
# Service method with transaction
def create_user_with_profile(self, user_data: UserCreate, profile_data: ProfileCreate):
    try:
        # Create user
        user = self.create_user(user_data)
        
        # Create profile
        profile = Profile(user_id=user.id, **profile_data.dict())
        self.db.add(profile)
        
        self.db.commit()
        return user
    except Exception as e:
        self.db.rollback()
        raise
```

## Performance Considerations

1. **Database Queries**: Use eager loading for relationships
2. **Response Caching**: Cache expensive computations
3. **Connection Pooling**: Configure SQLAlchemy pool settings
4. **Background Tasks**: Use Celery for heavy operations
5. **Query Optimization**: Monitor and optimize slow queries

## Security

1. **Input Validation**: Pydantic schemas validate all inputs
2. **SQL Injection**: SQLAlchemy ORM prevents SQL injection
3. **CORS**: Properly configured for frontend origins
4. **Rate Limiting**: Implement rate limiting for API endpoints
5. **Logging**: Log security events and errors