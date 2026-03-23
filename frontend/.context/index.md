---
module-name: "War Room Frontend"
description: "Next.js 14 React application with TypeScript, Tailwind CSS, and JWT authentication"
architecture:
  style: "Next.js App Router with React 18, TypeScript, Tailwind CSS"
  components:
    - name: "Next.js App Router"
      description: "File-based routing with app directory structure"
      path: "src/app/"
    - name: "React Components"
      description: "Modular component library organized by feature"
      path: "src/components/"
    - name: "Authentication Layer"
      description: "JWT-based auth with React Context and localStorage"
      files: ["src/components/AuthProvider.tsx", "src/lib/auth.ts"]
    - name: "UI Components" 
      description: "Reusable UI primitives with Tailwind CSS"
      path: "src/components/ui/"
    - name: "API Integration"
      description: "HTTP client for backend API communication"
      path: "src/lib/"
patterns:
  - name: "JWT Authentication Flow"
    description: "Context-based auth state management with localStorage persistence"
    usage: "useAuth() hook provides user state and auth methods"
    files: ["src/components/AuthProvider.tsx", "src/lib/auth.ts"]
    implementation: |
      1. AuthProvider wraps app, provides auth context
      2. Login stores JWT in localStorage, sets user state
      3. API requests include Authorization: Bearer <token>
      4. AuthGate protects routes, redirects unauthenticated users
  - name: "Component Organization"
    description: "Feature-based component organization with TypeScript"
    usage: "Components grouped by feature area (contacts, content, communications)"
    structure: |
      src/components/
      ├── contacts/        # Contact management components
      ├── content/         # Content creation and management
      ├── communications/  # SMS, email, call features
      ├── intelligence/    # Analytics and insights
      ├── ui/             # Reusable UI primitives
      └── AuthProvider.tsx # Global auth context
  - name: "API Integration Pattern"
    description: "Consistent API calling with JWT auth headers"
    usage: "All API calls include Authorization header automatically"
    files: ["src/lib/auth.ts", "src/lib/api.ts"]
  - name: "State Management"
    description: "React Context for global state, local state for components"
    usage: "Auth state global, component state local with useState/useReducer"
    files: ["src/components/AuthProvider.tsx"]
  - name: "Styling & Design System"
    description: "Tailwind CSS with custom design tokens and dark theme"
    usage: "Utility-first CSS with custom War Room brand colors"
    files: ["src/app/globals.css", "tailwind.config.ts"]
routing:
  structure: "Next.js App Router (file-based routing)"
  protected_routes: "All routes except /login and /signup require authentication"
  auth_gate: "AuthGate component wraps children, handles redirects"
  patterns: |
    /app/
    ├── page.tsx          # Dashboard (/)  
    ├── layout.tsx        # Root layout with AuthGate
    ├── login/page.tsx    # Login form (/login)
    └── signup/page.tsx   # Signup form (/signup)
styling:
  framework: "Tailwind CSS 3.4+ with TypeScript config"
  theme: "Dark theme by default with custom War Room brand colors"
  components: "Utility-first classes with component composition"
  custom_colors: |
    warroom-bg: Custom background color
    warroom-accent: Brand accent colors
    Dark theme applied via className="dark" on <html>
dependencies:
  core:
    - "next": "14.2.5"
    - "react": "^18.3.1" 
    - "typescript": "^5"
    - "tailwindcss": "^3.4.7"
  ui:
    - "lucide-react": "^0.400.0"  # Icon library
    - "framer-motion": "^12.38.0"  # Animations
    - "clsx": "^2.1.1"  # Conditional class names
    - "tailwind-merge": "^3.5.0"  # Tailwind class merging
  features:
    - "@xyflow/react": "^12.10.1"  # React Flow for workflow editor
    - "react-markdown": "^9.0.1"   # Markdown rendering
    - "dompurify": "^3.3.3"        # HTML sanitization
    - "zod": "^4.3.6"              # Schema validation
  media:
    - "@remotion/cli": "^4.0.435"    # Video generation
    - "@remotion/player": "^4.0.435" # Video player
    - "remotion": "^4.0.435"         # Video framework
common-issues:
  - issue: "Authentication state lost on page refresh"
    solution: "Check localStorage persistence in AuthProvider, verify token validation"
  - issue: "CORS errors when calling backend API"
    solution: "Verify backend ALLOWED_ORIGINS includes frontend URL (localhost:3300)"
  - issue: "Dark theme not applying"
    solution: "Ensure <html> has className='dark' in layout.tsx"
  - issue: "Tailwind classes not applying"
    solution: "Check tailwind.config.ts includes all source paths, restart dev server"
  - issue: "Component import errors"
    solution: "Verify TypeScript paths in tsconfig.json, check file extensions (.tsx)"
---

# War Room Frontend - Next.js React Application

The War Room frontend is a Next.js 14 application built with TypeScript, Tailwind CSS, and React 18. It provides a modern web interface for the social media management platform with JWT authentication and responsive design.

## Quick Start

```bash
# Start frontend container  
docker compose up -d --build frontend --remove-orphans

# Frontend will be available at http://localhost:3300
# Connects to backend API at http://localhost:8300
```

## Architecture Overview

### App Router Structure

```
src/
├── app/                    # Next.js App Router
│   ├── layout.tsx         # Root layout with AuthGate
│   ├── page.tsx           # Dashboard (/)
│   ├── login/page.tsx     # Login form  
│   └── signup/page.tsx    # Signup form
├── components/            # React components
│   ├── contacts/          # Contact management
│   ├── content/           # Content creation
│   ├── communications/    # SMS/email/calls
│   ├── intelligence/      # Analytics
│   └── ui/               # Reusable UI components
├── lib/                  # Utilities and API layer
└── hooks/                # Custom React hooks
```

## Authentication & Security

### JWT Authentication Flow

The frontend uses React Context for authentication state management:

```typescript
// AuthProvider pattern
const AuthContext = createContext<AuthContextType>()

interface AuthContextType {
  user: User | null
  loading: boolean
  login: (user: User) => void
  logout: () => void
}
```

**Authentication Flow:**
1. User logs in → JWT stored in localStorage
2. AuthProvider initializes with stored token
3. All API requests include `Authorization: Bearer <token>`
4. AuthGate redirects unauthenticated users to `/login`

### Route Protection

```typescript
// AuthGate component protects all routes
export function AuthGate({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  
  if (loading) return <LoadingSpinner />
  if (!user) redirect('/login')
  
  return children
}
```

## Component Architecture

### Feature-Based Organization

Components are organized by feature area for maintainability:

```
components/
├── contacts/           # Contact management
│   ├── ContactsPanel.tsx
│   └── ContactForm.tsx
├── content/           # Content creation
│   ├── ContentPipeline.tsx
│   └── ContentTracker.tsx  
├── communications/    # Multi-channel comms
│   ├── QuickActions.tsx
│   └── MessageThread.tsx
└── ui/               # Reusable primitives
    ├── Button.tsx
    └── Modal.tsx
```

### Component Patterns

```typescript
// Typical component pattern
interface ComponentProps {
  data: DataType
  onUpdate?: (data: DataType) => void
}

export function FeatureComponent({ data, onUpdate }: ComponentProps) {
  const [localState, setLocalState] = useState()
  const { user } = useAuth() // Global auth state
  
  const handleAction = async () => {
    // API call with auth
    const response = await fetch('/api/endpoint', {
      headers: {
        'Authorization': `Bearer ${getToken()}`
      }
    })
  }
  
  return (
    <div className="custom-styles">
      {/* Component JSX */}
    </div>
  )
}
```

## API Integration

### HTTP Client Pattern

```typescript
// API calls with automatic JWT auth
const apiCall = async (endpoint: string, options: RequestInit = {}) => {
  const token = localStorage.getItem('authToken')
  
  return fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...options.headers
    }
  })
}
```

## Styling & Design System

### Tailwind CSS Configuration

```typescript
// tailwind.config.ts
module.exports = {
  content: ['./src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        'warroom-bg': '#1a1a1a',
        'warroom-accent': '#00ff88'
      }
    }
  }
}
```

### Design System Patterns

- **Dark theme by default**: Applied via `className="dark"` on `<html>`
- **Utility-first**: Tailwind classes for styling
- **Component composition**: Reusable UI primitives in `/ui/`
- **Responsive design**: Mobile-first with Tailwind breakpoints

## Key Dependencies

### Core Framework
- **Next.js 14.2.5**: React framework with App Router
- **React 18.3.1**: Latest React with concurrent features
- **TypeScript 5**: Static type checking

### UI & Styling
- **Tailwind CSS 3.4.7**: Utility-first CSS framework
- **Lucide React**: Modern icon library
- **Framer Motion**: Animation library
- **clsx + tailwind-merge**: Conditional class handling

### Feature Libraries
- **@xyflow/react**: Visual workflow editor
- **React Markdown**: Markdown content rendering
- **DOMPurify**: HTML sanitization for security
- **Zod**: Runtime type validation

### Media & Video
- **Remotion**: Programmatic video generation
- **@remotion/player**: Video player component
- **@remotion/cli**: Video rendering CLI

## Docker Development

- **Container**: `warroom-frontend-1`
- **Dockerfile**: `./frontend/Dockerfile` 
- **Port**: `3300` (external) → `3000` (internal)
- **Volume**: `./frontend:/app` (live code reload)

### Development Commands

```bash
# Start development server
npm run dev

# Build for production  
npm run build

# Start production server
npm run start

# Docker rebuild
docker compose up -d --build frontend --remove-orphans
```

## Environment Configuration

Frontend configuration via environment variables:

- `NEXT_PUBLIC_API_URL`: Backend API base URL
- `NODE_ENV`: Environment mode (development/production)

## Common Issues & Solutions

### Authentication Issues
- **Token persistence**: Check localStorage in AuthProvider
- **API auth failures**: Verify JWT format and backend validation
- **Route protection**: Ensure AuthGate wraps protected components

### Styling Issues  
- **Dark theme**: Verify `className="dark"` on html element
- **Tailwind classes**: Check config includes all source paths
- **Custom colors**: Verify theme extension in tailwind.config.ts

### Development Issues
- **Hot reload failures**: Restart Next.js dev server
- **TypeScript errors**: Check tsconfig.json path mapping
- **Import errors**: Verify file extensions (.tsx) and relative paths

### Container Issues
- **Port conflicts**: Ensure no service using port 3300
- **Build failures**: Use `--no-cache` flag for clean rebuilds
- **Volume mounting**: Verify ./frontend directory exists and accessible