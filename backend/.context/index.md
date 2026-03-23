---
module-name: "War Room Backend"
description: "FastAPI REST API with JWT authentication, CSRF protection, and multi-tenant data isolation"
architecture:
  style: "FastAPI with Uvicorn, middleware-based auth"
  components:
    - name: "FastAPI Application"
      description: "Main ASGI app with middleware stack"
      file: "app/main.py"
    - name: "Authentication Middleware" 
      description: "Global JWT validation on all /api/* routes"
      file: "app/middleware/auth_guard.py"
    - name: "CSRF Protection"
      description: "Origin header validation for state-changing requests"  
      file: "app/middleware/csrf_guard.py"
    - name: "Database Layer"
      description: "SQLAlchemy models with multi-tenant isolation"
      path: "app/models/"
    - name: "API Routes"
      description: "Organized by feature area with consistent patterns"
      path: "app/api/"
patterns:
  - name: "JWT Authentication Flow"
    description: "AuthGuardMiddleware extracts user_id from JWT, sets request.state.user_id"
    usage: "All protected routes access current_user via request.state.user_id"
    files: ["app/middleware/auth_guard.py", "app/utils/auth.py"]
    implementation: |
      1. Client sends Authorization: Bearer <token>
      2. AuthGuardMiddleware validates JWT and extracts user_id
      3. Sets request.state.user_id for route handlers
      4. Route handlers query data WHERE user_id = request.state.user_id
  - name: "CSRF Protection"
    description: "Origin header validation on POST/PUT/DELETE requests"
    usage: "Prevents cross-site request forgery attacks"
    files: ["app/middleware/csrf_guard.py"]
    allowed_origins: ["http://localhost:3300", "http://localhost:3000", "https://warroom.stuffnthings.io"]
  - name: "Multi-Tenant Data Isolation"
    description: "All models include user_id foreign key for data separation"
    usage: "Every database query includes user_id filter"
    files: ["app/models/", "app/api/"]
  - name: "Error Handling"
    description: "Consistent JSON error responses with proper HTTP status codes"
    usage: "Use HTTPException for API errors, handle edge cases gracefully"
    files: ["app/api/", "app/middleware/"]
  - name: "Configuration Management"
    description: "Environment-based config with Pydantic settings"
    usage: "All settings centralized in app.config.settings"
    files: ["app/config.py"]
api-patterns:
  authentication:
    login: "POST /api/auth/login"
    signup: "POST /api/auth/signup" 
    protected_routes: "All /api/* except PUBLIC_PATHS in auth_guard.py"
  data_access:
    pattern: "WHERE user_id = request.state.user_id"
    isolation: "Complete tenant isolation via middleware"
  error_responses:
    format: |
      {
        "detail": "Error message",
        "error_code": "SPECIFIC_ERROR_TYPE"
      }
database:
  schemas:
    - name: "crm"
      description: "Main CRM data - contacts, deals, companies"
    - name: "social" 
      description: "Social media accounts, posts, engagement data"
  connection: "PostgreSQL via SQLAlchemy async sessions"
  migration: "Alembic for schema changes"
common-issues:
  - issue: "CORS errors in development"
    solution: "Check ALLOWED_ORIGINS in csrf_guard.py includes localhost:3300"
  - issue: "JWT validation failures"
    solution: "Verify JWT_SECRET matches between frontend and backend"
  - issue: "Database connection errors"
    solution: "Check DATABASE_URL in .env, ensure postgres container is running"
  - issue: "Import errors after container rebuild"
    solution: "Check Python path, verify requirements.txt includes all dependencies"
---

# War Room Backend - FastAPI REST API

The War Room backend is a FastAPI application providing REST API endpoints for the social media management platform. It implements JWT authentication, CSRF protection, and multi-tenant data isolation.

## Quick Start

```bash
# Start backend container
docker compose up -d --build backend --remove-orphans

# Backend will be available at http://localhost:8300
# API documentation at http://localhost:8300/docs
```

## Authentication & Security

### JWT Authentication Flow

All API routes under `/api/*` require JWT authentication except whitelisted public paths:

```python
# Public paths (no auth required)
PUBLIC_PATHS = {
    "/api/auth/login",
    "/api/auth/signup", 
    "/api/auth/verify-email",
    "/api/auth/resend-verification",
    "/api/auth/forgot-password",
    "/api/auth/reset-password",
    # ... health checks, webhooks
}
```

**Middleware Flow:**
1. Request → `AuthGuardMiddleware`
2. Extract Bearer token from Authorization header
3. Validate JWT signature and expiration  
4. Extract `user_id` claim and set `request.state.user_id`
5. Route handler accesses current user via `request.state.user_id`

### CSRF Protection

State-changing requests (POST/PUT/DELETE) require valid Origin header:

```python
ALLOWED_ORIGINS = [
    "https://warroom.stuffnthings.io",
    "http://localhost:3300",
    "http://localhost:3000", 
    "http://192.168.1.94:3300",
]
```

## Multi-Tenant Architecture

Every database query includes user isolation:

```python
# Example: Get user's contacts
contacts = session.query(Contact).filter(
    Contact.user_id == request.state.user_id
).all()
```

All models include `user_id` foreign key for complete data isolation between tenants.

## Common Development Patterns

### Route Handler Pattern
```python
@router.get("/contacts")
async def get_contacts(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.state.user_id  # Set by AuthGuardMiddleware
    contacts = await contact_service.get_user_contacts(db, user_id)
    return contacts
```

### Error Handling Pattern
```python
if not contact:
    raise HTTPException(
        status_code=404, 
        detail="Contact not found",
        error_code="CONTACT_NOT_FOUND"
    )
```

### Database Service Pattern
```python
async def get_user_contacts(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(Contact).where(Contact.user_id == user_id)
    )
    return result.scalars().all()
```

## Docker Development

- **Container**: `warroom-backend-1`
- **Dockerfile**: `./backend/Dockerfile`
- **Port**: `8300` (external) → `8300` (internal)
- **Volume**: `./backend:/app` (live code reload)

### Rebuild Commands

```bash
# Full rebuild (recommended)
docker compose up -d --build --remove-orphans

# Backend only  
docker compose up -d --build backend --remove-orphans

# Force rebuild without cache
docker compose up -d --build --no-cache --remove-orphans
```

## Environment Configuration

Key environment variables in `.env`:

- `JWT_SECRET`: Secret key for JWT signing
- `DATABASE_URL`: PostgreSQL connection string
- `DEBUG`: Enable debug mode and detailed logging
- `TWILIO_ACCOUNT_SID`: Twilio API credentials
- `GARAGE_S3_*`: MinIO/Garage S3 storage configuration

## Troubleshooting

**Common Issues:**

1. **Module import errors**: Check Python path in container, rebuild with `--no-cache`
2. **Database connection failures**: Verify postgres container is running, check DATABASE_URL
3. **JWT validation errors**: Ensure JWT_SECRET matches between frontend/backend
4. **CORS/CSRF errors**: Add development origins to ALLOWED_ORIGINS list
5. **Container port conflicts**: Check no other services using port 8300