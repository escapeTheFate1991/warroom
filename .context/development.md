# War Room Development Context

## Development Environment Setup

### Prerequisites
```bash
# Required tools
docker --version          # Docker for containerization
docker-compose --version  # Docker Compose for orchestration
node --version            # Node.js 18+ for frontend
python3 --version         # Python 3.12+ for backend
```

### Environment Variables
```bash
# .env file structure
DATABASE_URL=postgresql://user:pass@10.0.0.11:5433/warroom
JWT_SECRET=your-secret-key
TWILIO_SID=your-twilio-sid
TWILIO_TOKEN=your-twilio-token
TWILIO_PHONE=your-twilio-phone
NEXTAUTH_SECRET=your-nextauth-secret
NEXTAUTH_URL=http://localhost:3300
```

### Development Startup
```bash
# Start all services
docker compose up -d --build --remove-orphans

# Check service status
docker compose ps

# View logs
docker compose logs -f frontend
docker compose logs -f backend
```

## Docker Development Patterns

### Container Architecture
```yaml
# docker-compose.yml pattern
services:
  frontend:
    build: ./frontend
    ports:
      - "3300:3000"  # External:Internal
    volumes:
      - ./frontend:/app
      - /app/node_modules  # Prevent node_modules overwrite
    environment:
      - NODE_ENV=development
      - CHOKIDAR_USEPOLLING=true  # Hot reload for Docker
    depends_on:
      - backend

  backend:
    build: ./backend
    ports:
      - "8300:8000"
    volumes:
      - ./backend:/app
      - /app/venv  # Preserve virtual environment
    environment:
      - RELOAD=true
      - PYTHONPATH=/app
    depends_on:
      - db
```

### Rebuild Strategies
```bash
# Full rebuild (use when dependencies change)
docker compose down
docker compose up -d --build --no-cache --remove-orphans

# Quick rebuild (preserve cache)
docker compose up -d --build --remove-orphans

# Rebuild single service
docker compose up -d --build frontend

# Clear everything and restart
docker compose down -v
docker system prune -f
docker compose up -d --build
```

### Volume Management
```bash
# Named volumes for persistence
volumes:
  postgres_data:
  node_modules:
  python_packages:

# Bind mounts for development
volumes:
  - ./frontend:/app          # Source code
  - /app/node_modules        # Preserve installed packages
  - ./backend:/app
  - /app/venv               # Preserve Python packages
```

## Development Workflows

### Frontend Development
```bash
# Local development (without Docker)
cd frontend
npm install
npm run dev           # http://localhost:3000

# Docker development
docker compose up -d frontend
docker compose logs -f frontend

# Package updates
docker compose exec frontend npm install package-name
docker compose restart frontend
```

### Backend Development
```bash
# Local development (without Docker)
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Docker development  
docker compose up -d backend
docker compose logs -f backend

# Package updates
docker compose exec backend pip install package-name
docker compose exec backend pip freeze > requirements.txt
docker compose restart backend
```

### Database Management
```bash
# Connect to database
docker compose exec backend python -c "
from app.database import get_db
from sqlalchemy import text
db = next(get_db())
result = db.execute(text('SELECT version()')).scalar()
print(f'Database version: {result}')
"

# Run migrations
docker compose exec backend alembic upgrade head

# Create new migration
docker compose exec backend alembic revision --autogenerate -m "description"
```

## Common Development Issues

### Port Conflicts
```bash
# Check what's using ports
lsof -i :3300  # Frontend port
lsof -i :8300  # Backend port
lsof -i :5432  # Database port

# Kill processes
kill -9 $(lsof -t -i:3300)
```

### Docker Issues
```bash
# Container won't start
docker compose ps
docker compose logs service-name

# Out of disk space
docker system df
docker system prune -f
docker volume prune -f

# Permission issues (Linux)
sudo chown -R $USER:$USER .
```

### Hot Reload Problems
```bash
# Frontend hot reload not working
# Add to docker-compose.yml:
environment:
  - CHOKIDAR_USEPOLLING=true
  - WATCHPACK_POLLING=true

# Backend reload not working
# Ensure in docker-compose.yml:
environment:
  - RELOAD=true
volumes:
  - ./backend:/app
```

### Database Connection Issues
```bash
# Check database connectivity
docker compose exec backend python -c "
import asyncpg
import asyncio
async def test():
    conn = await asyncpg.connect('postgresql://user:pass@db:5432/warroom')
    result = await conn.fetchval('SELECT 1')
    print(f'Connection test: {result}')
    await conn.close()
asyncio.run(test())
"
```

## Testing Patterns

### Frontend Testing
```bash
# Unit tests
docker compose exec frontend npm test

# E2E tests
docker compose exec frontend npm run test:e2e

# Type checking
docker compose exec frontend npm run type-check

# Linting
docker compose exec frontend npm run lint
```

### Backend Testing
```bash
# Unit tests
docker compose exec backend pytest

# Coverage
docker compose exec backend pytest --cov=app

# API tests
docker compose exec backend pytest tests/test_api/

# Load testing
docker compose exec backend locust -f tests/load_test.py
```

### Integration Testing
```bash
# Full stack tests
docker compose -f docker-compose.test.yml up --abort-on-container-exit
docker compose -f docker-compose.test.yml down
```

## Debugging

### Frontend Debugging
```bash
# Browser debugging
# Add to frontend/src/app/page.tsx:
if (typeof window !== 'undefined') {
  console.log('Debug info:', { user, data });
}

# React DevTools
# Install React Developer Tools browser extension

# Next.js debugging
# Add to next.config.js:
experimental: {
  logging: {
    level: 'verbose'
  }
}
```

### Backend Debugging
```bash
# Python debugging
# Add to backend code:
import pdb; pdb.set_trace()

# Container debugging
docker compose exec backend bash
python -c "import app; print(app.__file__)"

# FastAPI debugging
# Add to main.py:
import logging
logging.basicConfig(level=logging.DEBUG)

# Database query debugging
# Add to database.py:
engine = create_engine(
    DATABASE_URL,
    echo=True  # Log all SQL queries
)
```

### Network Debugging
```bash
# Check container networking
docker compose exec frontend ping backend
docker compose exec backend ping db

# Check service discovery
docker compose exec frontend nslookup backend
docker compose exec backend nslookup db

# Port mapping
docker compose port frontend 3000
docker compose port backend 8000
```

## Performance Monitoring

### Frontend Performance
```typescript
// Add to app/layout.tsx
import { Analytics } from '@vercel/analytics/react';

export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        {children}
        <Analytics />
      </body>
    </html>
  );
}

// Performance monitoring
export function reportWebVitals(metric) {
  console.log(metric);
}
```

### Backend Performance
```python
# Add to main.py
import time
from fastapi import Request

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

## Deployment Checklist

### Pre-deployment
```bash
# Build test
docker compose build

# Run tests
npm test
pytest

# Security scan
npm audit
pip-audit

# Environment check
docker compose config
```

### Production Build
```bash
# Frontend production build
docker compose exec frontend npm run build

# Backend production setup
# Ensure in production docker-compose.yml:
environment:
  - NODE_ENV=production
  - RELOAD=false
  - DEBUG=false
```

## Git Hooks

### Pre-commit Hook
```bash
#!/bin/bash
# .git/hooks/pre-commit

# Run linters
npm run lint
python -m flake8 backend/

# Run quick tests
npm test -- --passWithNoTests
pytest tests/unit/

# Type check
npm run type-check
mypy backend/app/
```

### Post-commit Hook
```bash
#!/bin/bash
# .git/hooks/post-commit

# Update context index
if [ -f bin/friday-ctx ]; then
    ./bin/friday-ctx index
fi

# Rebuild containers if dependencies changed
if git diff HEAD~1 --name-only | grep -E "(package\.json|requirements\.txt)"; then
    echo "Dependencies changed, consider rebuilding containers"
    echo "Run: docker compose up -d --build"
fi
```