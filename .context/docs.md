# War Room - Detailed Context Documentation

## Authentication & Security Implementation

### JWT Authentication Deep Dive

**Current Implementation:**

The War Room backend uses a global `AuthGuardMiddleware` that validates JWT tokens on all `/api/*` routes except explicitly whitelisted public paths.

**Backend Flow (app/middleware/auth_guard.py):**
```python
# AuthGuardMiddleware validates ALL /api/* routes
PUBLIC_PATHS = {
    "/api/auth/login",
    "/api/auth/signup", 
    "/api/auth/verify-email",
    "/api/health",
    "/api/webhooks/*",  # Webhook endpoints
}

# Middleware extracts user_id from JWT claims
def extract_user_from_token(token: str) -> int:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise InvalidTokenError("Missing user_id claim")
        return user_id
    except jwt.ExpiredSignatureError:
        raise InvalidTokenError("Token has expired")
    except jwt.InvalidTokenError:
        raise InvalidTokenError("Invalid token")
```

**Frontend Flow (src/components/AuthProvider.tsx):**
```typescript
// AuthProvider manages global auth state
const AuthContext = createContext<AuthContextType>()

// Login flow stores JWT in localStorage
const login = (user: User) => {
  localStorage.setItem('authToken', user.token)
  localStorage.setItem('user', JSON.stringify(user))
  setUser(user)
}

// All API calls include auth header
const getAuthHeaders = () => ({
  'Authorization': `Bearer ${localStorage.getItem('authToken')}`,
  'Content-Type': 'application/json'
})
```

### CSRF Protection Implementation

**Backend CSRF Guard (app/middleware/csrf_guard.py):**
```python
ALLOWED_ORIGINS = [
    "https://warroom.stuffnthings.io",
    "https://stuffnthings.io", 
    "https://www.stuffnthings.io",
    "http://localhost:3300",  # Development
    "http://localhost:3000",  # Next.js dev server
    "http://192.168.1.94:3300",  # Local network
]

# Validates Origin header on state-changing requests
def validate_origin(request: Request) -> bool:
    origin = request.headers.get("origin") or request.headers.get("referer")
    if not origin:
        return False
    
    parsed_origin = urlparse(origin)
    origin_url = f"{parsed_origin.scheme}://{parsed_origin.netloc}"
    
    return origin_url in ALLOWED_ORIGINS
```

### Multi-Tenant Data Isolation

**Pattern:** Every database model includes `user_id` foreign key for complete data separation.

**Implementation Example:**
```python
# Backend service pattern
async def get_user_contacts(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(Contact)
        .where(Contact.user_id == user_id)
        .order_by(Contact.created_at.desc())
    )
    return result.scalars().all()

# Route handler pattern
@router.get("/contacts")
async def get_contacts(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.state.user_id  # Set by AuthGuardMiddleware
    contacts = await contact_service.get_user_contacts(db, user_id)
    return contacts
```

## Database Architecture

### Schema Organization

War Room uses PostgreSQL with two primary schemas:

1. **CRM Schema**: Core customer relationship management
   - `users` - User accounts and authentication
   - `contacts` - Contact management
   - `companies` - Company/organization data
   - `deals` - Sales pipeline management
   - `activities` - Interaction history

2. **Social Schema**: Social media platform integration
   - `social_accounts` - Connected social media accounts
   - `posts` - Social media posts and content
   - `campaigns` - Marketing campaigns
   - `analytics` - Performance metrics

### Connection Configuration

```python
# Backend database configuration
DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5435/warroom"

# Docker networking
# Container: postgres:15
# Internal port: 5432
# External port: 5435 (to avoid conflicts)
```

## Docker Development Patterns

### Container Architecture

**Current Setup:**
```yaml
# docker-compose.yml key sections
services:
  backend:
    build: ./backend
    ports: ["8300:8300"]
    volumes: ["./backend:/app"]
    
  frontend:
    build: ./frontend  
    ports: ["3300:3000"]
    volumes: ["./frontend:/app"]
    
  postgres:
    image: postgres:15
    ports: ["5435:5432"]
    volumes: ["warroom_postgres_data:/var/lib/postgresql/data"]
```

### Rebuild Best Practices

**Always use `--remove-orphans`** to clean up leftover containers:

```bash
# Standard rebuild (most common)
docker compose up -d --build --remove-orphans

# Individual service rebuild
docker compose up -d --build backend --remove-orphans
docker compose up -d --build frontend --remove-orphans

# Force clean rebuild (when dependencies change)
docker compose up -d --build --no-cache --remove-orphans

# Troubleshooting: Stop everything and rebuild
docker compose down
docker compose up -d --build --remove-orphans
```

**When to use each:**
- `--build`: Always use when code changes
- `--remove-orphans`: Always use to prevent container conflicts  
- `--no-cache`: Use when package.json/requirements.txt changes
- Individual service: Use when only one service needs rebuilding

## API Design Patterns

### Consistent Route Structure

**Authentication Routes:**
```
POST   /api/auth/login          # User login
POST   /api/auth/signup         # User registration
POST   /api/auth/logout         # User logout
GET    /api/auth/me            # Get current user info
```

**CRM Routes:**
```
GET    /api/contacts           # List user's contacts
POST   /api/contacts           # Create new contact
GET    /api/contacts/{id}      # Get specific contact
PUT    /api/contacts/{id}      # Update contact
DELETE /api/contacts/{id}      # Delete contact
```

**Social Media Routes:**
```
GET    /api/social/accounts    # List connected accounts
POST   /api/social/accounts    # Connect new account
GET    /api/social/posts       # List posts
POST   /api/social/posts       # Create/schedule post
```

### Error Response Format

**Consistent JSON error responses:**
```json
{
  "detail": "Human readable error message",
  "error_code": "SPECIFIC_ERROR_TYPE",
  "field_errors": {
    "field_name": "Field-specific error"
  }
}
```

**HTTP Status Codes:**
- `200`: Success
- `201`: Created
- `400`: Bad Request (validation errors)
- `401`: Unauthorized (invalid/missing JWT)
- `403`: Forbidden (CSRF violation, insufficient permissions)
- `404`: Not Found
- `422`: Unprocessable Entity (validation errors)
- `500`: Internal Server Error

## Frontend Architecture Patterns

### Component Organization Strategy

**Feature-Based Structure:**
```
src/components/
├── contacts/          # Contact management features
│   ├── ContactsPanel.tsx
│   ├── ContactForm.tsx
│   └── ContactDetails.tsx
├── content/           # Content creation and management
│   ├── ContentPipeline.tsx
│   ├── ContentTracker.tsx
│   └── ContentToSocial.tsx
├── communications/    # Multi-channel communications
│   ├── QuickActions.tsx
│   ├── MessageThread.tsx
│   └── CallHistory.tsx
├── intelligence/      # Analytics and insights
│   ├── CompetitorIntel.tsx
│   └── PostDetailModal.tsx
└── ui/               # Reusable UI primitives
    ├── Button.tsx
    ├── Modal.tsx
    └── DataTable.tsx
```

### State Management Patterns

**Global State (React Context):**
- Authentication state (`AuthProvider`)
- Theme preferences
- User preferences

**Local State (useState/useReducer):**
- Form data
- Component-specific UI state
- Loading states

**Server State (API calls):**
- Fetch data in useEffect
- No complex caching (rely on browser cache)
- Optimistic updates for better UX

### TypeScript Patterns

**Interface Definitions:**
```typescript
// API response types
interface User {
  id: number
  email: string
  name: string
  created_at: string
}

interface Contact {
  id: number
  user_id: number
  name: string
  email?: string
  phone?: string
  company?: string
}

// Component props
interface ContactFormProps {
  contact?: Contact
  onSave: (contact: Contact) => void
  onCancel: () => void
}
```

## Common Development Issues & Solutions

### Authentication Issues

**Issue: JWT token validation fails**
```
401 Unauthorized - Invalid token
```
**Solutions:**
1. Check JWT_SECRET matches between frontend/backend
2. Verify token format: `Authorization: Bearer <token>`
3. Check token expiration
4. Ensure middleware is properly configured

**Issue: User state lost on page refresh**
```
User redirected to login after page reload
```
**Solutions:**
1. Verify AuthProvider initializes from localStorage
2. Check token persistence in localStorage
3. Ensure AuthGate waits for auth initialization

### CORS & CSRF Issues

**Issue: CORS errors in development**
```
CORS policy blocked: No 'Access-Control-Allow-Origin' header
```
**Solutions:**
1. Add development URLs to `ALLOWED_ORIGINS` in `csrf_guard.py`
2. Verify Origin header is sent with requests
3. Check CORS middleware configuration

**Issue: CSRF protection blocking requests**
```
403 Forbidden - CSRF validation failed
```
**Solutions:**
1. Ensure Origin header matches `ALLOWED_ORIGINS`
2. Check request comes from same domain
3. Verify POST/PUT/DELETE requests include proper headers

### Docker Development Issues

**Issue: Container build failures**
```
Error: Cannot find module 'package-name'
```
**Solutions:**
1. Use `--no-cache` flag to force rebuild
2. Check package.json/requirements.txt is current
3. Verify Dockerfile COPY commands include dependency files

**Issue: Port conflicts**
```
Port 8300 already in use
```
**Solutions:**
1. Use `--remove-orphans` flag
2. Check for running containers: `docker ps`
3. Stop conflicting services: `docker compose down`

**Issue: Database connection failures**
```
Could not connect to database
```
**Solutions:**
1. Verify postgres container is running
2. Check DATABASE_URL environment variable
3. Ensure port 5435 is not blocked
4. Wait for postgres initialization (can take 10-30 seconds)

### Performance Issues

**Issue: Slow API responses**
**Solutions:**
1. Check database query efficiency
2. Add database indexes for frequently queried fields
3. Implement API response caching
4. Use database query profiling

**Issue: Large bundle sizes (Frontend)**
**Solutions:**
1. Use Next.js dynamic imports for code splitting
2. Analyze bundle with `npm run build`
3. Remove unused dependencies
4. Optimize images and assets

## Testing Patterns

### Backend Testing

**API Endpoint Testing:**
```python
# test_api_endpoints.py pattern
@pytest.mark.asyncio
async def test_get_contacts_authenticated():
    # Arrange
    user_id = 1
    token = create_test_jwt(user_id)
    
    # Act
    response = await client.get(
        "/api/contacts",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
```

### Frontend Testing

**Component Testing (Jest/React Testing Library):**
```typescript
// ContactForm.test.tsx pattern
import { render, screen, fireEvent } from '@testing-library/react'
import { ContactForm } from './ContactForm'

test('submits contact data correctly', async () => {
  const mockOnSave = jest.fn()
  
  render(<ContactForm onSave={mockOnSave} />)
  
  fireEvent.change(screen.getByLabelText('Name'), {
    target: { value: 'John Doe' }
  })
  
  fireEvent.click(screen.getByText('Save'))
  
  expect(mockOnSave).toHaveBeenCalledWith({
    name: 'John Doe'
  })
})
```

## Environment Configuration

### Backend Environment Variables

```bash
# .env (backend)
JWT_SECRET=your-secret-key-here
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/warroom
DEBUG=true
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
GARAGE_S3_ENDPOINT=http://10.0.0.11:3900
GARAGE_S3_ACCESS_KEY=your-access-key
GARAGE_S3_SECRET_KEY=your-secret-key
```

### Frontend Environment Variables

```bash
# .env.local (frontend)
NEXT_PUBLIC_API_URL=http://localhost:8300
NODE_ENV=development
```

## Monitoring & Debugging

### Backend Logging

**Structured Logging Pattern:**
```python
import logging

logger = logging.getLogger(__name__)

# Log levels used consistently
logger.info(f"User {user_id} logged in successfully")
logger.warning(f"Failed login attempt for email: {email}")
logger.error(f"Database connection failed: {error}")
logger.debug(f"Processing request: {request.url}")
```

### Frontend Debugging

**Console Debugging:**
```typescript
// Development-only logging
if (process.env.NODE_ENV === 'development') {
  console.log('User state:', user)
  console.log('API response:', response.data)
}

// Error boundaries for production
class ErrorBoundary extends React.Component {
  // Handle React errors gracefully
}
```

### Database Query Monitoring

**SQLAlchemy Query Logging:**
```python
# Enable query logging in development
if settings.DEBUG:
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

## Security Best Practices

### Input Validation

**Backend (Pydantic):**
```python
from pydantic import BaseModel, EmailStr, constr

class CreateContactRequest(BaseModel):
    name: constr(min_length=1, max_length=100)
    email: EmailStr | None = None
    phone: constr(regex=r'^\+?1?\d{9,15}$') | None = None
```

**Frontend (Zod):**
```typescript
import { z } from 'zod'

const contactSchema = z.object({
  name: z.string().min(1).max(100),
  email: z.string().email().optional(),
  phone: z.string().regex(/^\+?1?\d{9,15}$/).optional()
})
```

### XSS Prevention

**Backend:** Automatic via FastAPI/Pydantic serialization

**Frontend:** DOMPurify for HTML sanitization
```typescript
import DOMPurify from 'dompurify'

const sanitized = DOMPurify.sanitize(userContent)
```

### SQL Injection Prevention

**Parameterized Queries via SQLAlchemy:**
```python
# Safe - parameterized query
result = await db.execute(
    select(Contact).where(Contact.user_id == user_id)
)

# NEVER - string concatenation
# query = f"SELECT * FROM contacts WHERE user_id = {user_id}"  # DANGEROUS
```