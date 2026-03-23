---
module-name: "War Room"
description: "Full-stack social media management platform with multi-tenant CRM"
architecture:
  style: "Microservices with Docker Compose"
  components:
    - name: "FastAPI Backend"
      description: "REST API with JWT auth, PostgreSQL, multi-tenant architecture"
      port: 8300
      docker-service: "warroom-backend-1"
    - name: "Next.js Frontend" 
      description: "React app with Tailwind CSS, app router"
      port: "3300→3000"
      docker-service: "warroom-frontend-1"
    - name: "PostgreSQL Database"
      description: "Multi-tenant with CRM + social media schemas"
      port: 5435
patterns:
  - name: "JWT Authentication"
    usage: "AuthGuardMiddleware validates tokens, extracts user_id claim"
    files: ["backend/app/middleware/auth.py", "backend/app/utils/auth.py"]
  - name: "CSRF Protection"
    usage: "Origin header validation on POST/PUT/DELETE requests"
    files: ["backend/app/middleware/csrf.py"]
  - name: "Docker Rebuild"
    usage: "Always use --remove-orphans flag: docker compose up -d --build --remove-orphans"
    files: ["docker-compose.yml"]
  - name: "Multi-Tenant Data"
    usage: "All models include user_id foreign key for data isolation"
    files: ["backend/app/models/"]
deployment:
  containers:
    backend: "Always rebuild on code changes"
    frontend: "Always rebuild on dependency changes"
  ports:
    backend: "8300 (internal) mapped from host"
    frontend: "3000 (internal) → 3300 (host)"
    database: "5432 (internal) → 5435 (host)"
related-modules:
  - name: "Mental Library Backend"
    path: "../mental-library/"
    description: "Separate FastAPI service for AI content processing"
  - name: "Garage S3 Storage"
    url: "http://10.0.0.11:3900"
    description: "MinIO S3-compatible storage for media files"
---

# War Room - Social Media Management Platform

War Room is a full-stack social media management platform built with FastAPI backend and Next.js frontend. It provides multi-tenant CRM capabilities, social media account management, content scheduling, and workflow automation.

## Quick Start

```bash
# Start all services
docker compose up -d --build --remove-orphans

# Backend API: http://localhost:8300
# Frontend: http://localhost:3300  
# Database: localhost:5435
```

## Architecture Overview

```mermaid
graph TB
    Frontend[Next.js Frontend<br/>Port 3300] --> Backend[FastAPI Backend<br/>Port 8300]
    Backend --> DB[PostgreSQL<br/>Port 5435]
    Backend --> S3[Garage S3<br/>Port 3900]
    Backend --> External[External APIs<br/>Twilio, Social Platforms]
```

## Key Features

- **Multi-Tenant CRM**: Complete customer relationship management with user isolation
- **Social Media Integration**: Instagram, Facebook, LinkedIn, Twitter automation
- **Content Engine**: AI-powered content generation and scheduling  
- **Workflow Automation**: Custom workflows with React Flow visual editor
- **JWT Authentication**: Secure token-based auth with middleware validation
- **CSRF Protection**: Origin header validation for state-changing requests

## Current Focus Areas

- Content engine optimization and AI integration
- Social media platform API stability
- Performance optimization for large datasets
- Multi-tenant security hardening

## Development Notes

- Always use Docker rebuild commands with `--remove-orphans`
- JWT tokens contain `user_id` claim for multi-tenant data access
- CSRF middleware requires valid Origin header on POST/PUT/DELETE
- Database schemas: `crm` (main), `social` (social media data)