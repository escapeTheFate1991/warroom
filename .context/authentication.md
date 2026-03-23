# Authentication & JWT Implementation

## Overview

War Room uses JWT (JSON Web Tokens) for stateless authentication across the FastAPI backend and Next.js frontend.

## JWT Token Structure

```python
# JWT Payload
{
    "user_id": 123,
    "email": "user@example.com",
    "exp": 1640995200,  # Expiration timestamp
    "iat": 1640908800,  # Issued at timestamp
    "sub": "user_auth"  # Subject
}
```

## Backend Authentication (FastAPI)

### Location: `backend/app/auth/`

- **jwt.py**: JWT token generation and validation
- **middleware.py**: Authentication middleware for protected routes
- **dependencies.py**: FastAPI dependency injection for auth

### Key Functions

```python
# backend/app/auth/jwt.py
def create_access_token(user_id: int, email: str) -> str
def verify_token(token: str) -> dict
def decode_token(token: str) -> dict

# backend/app/auth/dependencies.py  
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User
```

### Common Errors

- `TokenExpiredError`: JWT token has expired → regenerate token
- `InvalidTokenError`: Malformed or invalid token → redirect to login
- `401 Unauthorized`: Missing or invalid auth header → check token format

## Frontend Authentication (Next.js)

### Location: `frontend/src/lib/auth.ts`

```typescript
// Token management
export function getToken(): string | null
export function setToken(token: string): void
export function removeToken(): void
export function isTokenExpired(token: string): boolean

// API authentication
export async function authenticatedFetch(url: string, options?: RequestInit)
```

### Auth Flow

1. Login → POST `/api/auth/login` → JWT token returned
2. Store token in localStorage/httpOnly cookie  
3. Include token in Authorization header: `Bearer <token>`
4. Middleware validates token on protected routes
5. Token refresh before expiration

## Database Schema

```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Sessions table (for refresh tokens)
CREATE TABLE user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    refresh_token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Environment Variables

```bash
# JWT Configuration
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# Database
DATABASE_URL=postgresql://user:password@localhost/warroom
```

## API Endpoints

### Authentication Routes

- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout  
- `POST /api/auth/refresh` - Refresh JWT token
- `GET /api/auth/me` - Get current user info

### Protected Routes

All API routes under `/api/` require authentication except:
- `/api/auth/login`
- `/api/auth/register`
- `/api/health`

## Troubleshooting

### JWT Token Expired

**Error**: `TokenExpiredError: JWT token has expired`

**Solution**: 
1. Check token expiration time
2. Implement automatic token refresh
3. Redirect to login if refresh fails

### Invalid Token Format

**Error**: `401 Unauthorized` or `InvalidTokenError`

**Solution**:
1. Verify Authorization header format: `Bearer <token>`
2. Check token is properly base64 encoded
3. Ensure JWT_SECRET_KEY matches between frontend/backend

### CORS Issues

**Error**: CORS errors during auth requests

**Solution**:
1. Configure CORS middleware in FastAPI
2. Include credentials in frontend requests
3. Check allowed origins configuration

## Security Best Practices

1. **Secret Rotation**: Rotate JWT_SECRET_KEY periodically
2. **HTTPS Only**: Always use HTTPS in production  
3. **Token Expiration**: Keep JWT expiration time reasonable (15-60 minutes)
4. **Refresh Tokens**: Use refresh tokens for longer sessions
5. **Input Validation**: Validate all auth inputs
6. **Rate Limiting**: Implement login attempt rate limiting

## Testing

```bash
# Test authentication endpoints
pytest backend/tests/test_auth.py

# Test JWT functions
pytest backend/tests/test_jwt.py
```

## Recent Changes

- Added refresh token functionality
- Implemented proper CORS handling
- Enhanced error messages for debugging
- Added session management table