# War Room Architecture Context

## Overview
War Room is a Next.js + FastAPI monorepo for CRM, lead generation, and social media management.

```mermaid
graph TB
    subgraph "Frontend (Next.js 14)"
        A[Web App :3300→3000]
        B[React Flow Editor]
        C[Dashboard UI]
    end
    
    subgraph "Backend (FastAPI)"
        D[API Server :8300]
        E[Auth Middleware]
        F[Background Tasks]
    end
    
    subgraph "Database"
        G[(PostgreSQL)]
        H[Public Schema]
        I[CRM Schema] 
        J[LeadGen Schema]
    end
    
    subgraph "External Services"
        K[Twilio SMS]
        L[Social APIs]
        M[Web Scrapers]
    end
    
    A --> D
    D --> G
    D --> K
    D --> L
    F --> M
```

## Service Ports
- Frontend: `3300:3000` (Docker mapped)
- Backend: `8300` (internal)
- Database: `10.0.0.11:5433` (Brain 2)

## Container Architecture
- `warroom-frontend-1`: Next.js app with standalone output
- `warroom-backend-1`: FastAPI with uvicorn
- Database: External PostgreSQL on Brain 2

## Authentication Flow
```yaml
type: JWT
claim: user_id
middleware: AuthGuardMiddleware (global)
multi_user: true # Eddy + wife
storage: httpOnly cookies + localStorage tokens
```

## Database Schemas
```yaml
public:
  - settings
  - facts  
  - kanban
  - agent_events

crm:
  - contacts
  - deals
  - pipelines
  - social_accounts

leadgen:
  - search_jobs
  - leads
```

## Key Technologies
- **Frontend**: Next.js 14, Tailwind CSS, React Flow (@xyflow/react)
- **Backend**: FastAPI, SQLAlchemy, asyncpg
- **Database**: PostgreSQL with multi-schema design
- **Communication**: Twilio (primary), Telnyx (backup)
- **Workflow**: React Flow templates (20 seeded)
- **Deployment**: Docker Compose