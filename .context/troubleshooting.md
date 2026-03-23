# War Room Troubleshooting Context

## Common Issues & Solutions

### Docker Issues

#### Container Won't Start
```bash
# Check container status
docker compose ps

# View container logs  
docker compose logs -f service-name

# Common causes:
# - Port conflicts
# - Environment variable issues
# - Volume mount problems
# - Dependency startup order
```

#### Port Already in Use
```bash
# Find what's using the port
sudo lsof -i :3300  # Frontend port
sudo lsof -i :8300  # Backend port

# Kill the process
sudo kill -9 $(sudo lsof -t -i:3300)

# Or use different ports in docker-compose.yml
ports:
  - "3301:3000"  # Change external port
```

#### Database Connection Failures
```bash
# Test database connectivity
docker compose exec backend python -c "
import asyncpg
import asyncio
async def test():
    conn = await asyncpg.connect('postgresql://user:pass@10.0.0.11:5433/warroom')
    print('✅ Database connection successful')
    await conn.close()
asyncio.run(test())
"

# Common fixes:
# 1. Check DATABASE_URL in .env
# 2. Ensure postgres container is running
# 3. Check firewall/network settings
# 4. Verify credentials
```

#### Volume Mount Issues
```bash
# Fix permissions on Linux
sudo chown -R $USER:$USER .

# Clear volumes and restart
docker compose down -v
docker compose up -d --build
```

### Authentication Issues

#### JWT Token Validation Failures
```yaml
symptoms:
  - 401 Unauthorized errors
  - "Invalid token" messages
  - User logged out unexpectedly

causes:
  - JWT_SECRET mismatch between frontend/backend
  - Token expired
  - Token format incorrect
  - Middleware configuration error

solutions:
  1. Check JWT_SECRET in .env matches
  2. Clear localStorage and login again
  3. Check token format in browser DevTools
  4. Verify AuthGuardMiddleware is applied correctly
```

#### CSRF Protection Blocking Requests
```yaml
symptoms:
  - 403 Forbidden on POST/PUT/DELETE
  - "CSRF validation failed"
  - Origin header errors

solutions:
  1. Check ALLOWED_ORIGINS in backend includes frontend URL
  2. Ensure Origin header is set correctly
  3. Add localhost:3300 to allowed origins for development
  4. Check for proxy/reverse proxy configuration issues
```

### Frontend Issues

#### Hot Reload Not Working
```yaml
docker-compose.yml environment additions:
  - CHOKIDAR_USEPOLLING=true
  - WATCHPACK_POLLING=true

# Also ensure volume mounts are correct:
volumes:
  - ./frontend:/app
  - /app/node_modules  # Prevent overwrite
```

#### TypeScript Errors
```bash
# Type check entire project
npm run type-check

# Common issues:
# 1. Missing type definitions
# 2. Incorrect import paths
# 3. Environment variable types
# 4. API response type mismatches

# Fix missing types
npm install --save-dev @types/package-name
```

#### Build Failures
```bash
# Clear Next.js cache
rm -rf .next
npm run build

# Check for:
# 1. Syntax errors
# 2. Import/export issues  
# 3. Environment variable access
# 4. Static analysis errors
```

### Backend Issues

#### FastAPI Server Won't Start
```bash
# Check Python dependencies
docker compose exec backend pip list

# Common issues:
# 1. Missing requirements in requirements.txt
# 2. Python path issues
# 3. Database connection on startup
# 4. Environment variable errors

# Fix Python path
export PYTHONPATH=/app
```

#### Database Migration Errors
```bash
# Check migration status
docker compose exec backend alembic current

# Show migration history
docker compose exec backend alembic history

# Fix migration conflicts
docker compose exec backend alembic stamp head
docker compose exec backend alembic revision --autogenerate -m "fix"
```

#### API Endpoint Errors
```yaml
404 Not Found:
  - Check route registration
  - Verify URL pattern matches
  - Ensure router is included in main app

422 Validation Error:
  - Check request body schema
  - Verify required fields
  - Check data type mismatches

500 Internal Server Error:
  - Check backend logs
  - Verify database connectivity
  - Check for unhandled exceptions
```

### Performance Issues

#### Slow Frontend Loading
```bash
# Analyze bundle size
npm run build
npm run analyze  # If configured

# Common causes:
# 1. Large dependencies
# 2. Unoptimized images
# 3. No code splitting
# 4. Excessive re-renders

# Solutions:
# 1. Lazy load components
# 2. Optimize images
# 3. Use React.memo for heavy components
# 4. Implement proper key props
```

#### Slow API Responses
```python
# Add timing middleware to FastAPI
import time
from fastapi import Request

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Common causes:
# 1. N+1 database queries
# 2. Missing database indexes
# 3. Synchronous operations
# 4. Large payload serialization

# Solutions:
# 1. Use async/await properly
# 2. Add database indexes
# 3. Implement query optimization
# 4. Add caching layer
```

### Development Environment

#### Environment Variables Not Loading
```bash
# Check .env file exists and has correct format
cat .env

# Ensure no spaces around = sign
DATABASE_URL=postgresql://user:pass@host:port/db

# Restart containers after .env changes
docker compose down
docker compose up -d
```

#### Docker Build Failures
```bash
# Clear Docker cache
docker system prune -f
docker builder prune -f

# Rebuild without cache
docker compose build --no-cache

# Check Dockerfile syntax
docker build --no-cache -t test-build .
```

#### Git Hooks Not Working
```bash
# Check hook permissions
ls -la .git/hooks/

# Make executable
chmod +x .git/hooks/post-commit
chmod +x .git/hooks/post-checkout
chmod +x .git/hooks/post-merge

# Test hook manually
./.git/hooks/post-commit
```

## Debugging Commands

### Docker Debugging
```bash
# Enter running container
docker compose exec backend bash
docker compose exec frontend bash

# Check container resources
docker stats

# View container details
docker compose exec backend env
docker compose exec frontend env

# Check networking
docker compose exec frontend ping backend
docker compose exec backend ping db
```

### Database Debugging
```bash
# Direct database access
docker compose exec backend python -c "
from app.database import get_db
from sqlalchemy import text
db = next(get_db())
result = db.execute(text('SELECT COUNT(*) FROM contacts')).scalar()
print(f'Contact count: {result}')
"

# Check table structure
docker compose exec backend python -c "
from app.database import engine
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()
print('Tables:', tables)
"
```

### API Debugging
```bash
# Test API endpoints
curl -X GET http://localhost:8300/api/health

# Test with authentication
curl -X GET http://localhost:8300/api/contacts \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Check API documentation
open http://localhost:8300/docs  # FastAPI Swagger UI
```

### Frontend Debugging
```bash
# Check build output
npm run build 2>&1 | tee build.log

# Analyze bundle
npm run build && npm run analyze

# Check for unused dependencies
npx depcheck
```

## Error Messages & Solutions

### "Module not found"
```bash
# Python backend
docker compose exec backend pip install missing-package
echo "missing-package" >> requirements.txt

# Node frontend  
docker compose exec frontend npm install missing-package
```

### "Permission denied"
```bash
# Fix file permissions
sudo chown -R $USER:$USER .

# Fix Docker socket
sudo usermod -aG docker $USER
# Then logout and login again
```

### "Port already in use"
```bash
# Change ports in docker-compose.yml
services:
  frontend:
    ports:
      - "3301:3000"  # Changed from 3300
  backend:
    ports:
      - "8301:8000"  # Changed from 8300
```

### "Database connection refused"
```bash
# Check if database is external
# Update DATABASE_URL to point to correct host
DATABASE_URL=postgresql://user:pass@10.0.0.11:5433/warroom

# For local development
DATABASE_URL=postgresql://user:pass@localhost:5432/warroom
```

## Monitoring & Logs

### Log Locations
```bash
# Docker logs
docker compose logs -f --tail=100 backend
docker compose logs -f --tail=100 frontend

# Application logs (if configured)
docker compose exec backend tail -f /app/logs/app.log
```

### Health Checks
```bash
# Backend health
curl http://localhost:8300/health

# Frontend health (Next.js)
curl http://localhost:3300/api/health

# Database health
docker compose exec backend python -c "
import asyncpg
import asyncio
async def test():
    try:
        conn = await asyncpg.connect('postgresql://user:pass@10.0.0.11:5433/warroom')
        await conn.close()
        print('✅ Database healthy')
    except Exception as e:
        print(f'❌ Database error: {e}')
asyncio.run(test())
"
```

### Performance Monitoring
```bash
# Docker stats
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Check disk usage
df -h
docker system df
```