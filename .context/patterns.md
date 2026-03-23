# War Room Code Patterns Context

## JWT Authentication Pattern

### Implementation
```python
# backend/app/middleware/auth.py
from fastapi import HTTPException, Depends
from jose import JWTError, jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
        return user_id
    except JWTError:
        raise credentials_exception
```

### Usage Pattern
- Global `AuthGuardMiddleware` protects all routes
- `user_id` claim is the primary identifier
- Token stored in httpOnly cookies + localStorage backup
- Multi-user support (Eddy + wife)

## Database Schema Patterns

### Multi-Schema Organization
```sql
-- Public schema: application-wide data
public.settings
public.facts
public.kanban
public.agent_events

-- CRM schema: customer management
crm.contacts
crm.deals
crm.pipelines
crm.social_accounts

-- LeadGen schema: lead generation
leadgen.search_jobs
leadgen.leads
```

### Entity Relationship Pattern
- Soft deletes using `deleted_at` timestamps
- UUID primary keys for external entities
- Integer IDs for internal relations
- JSON columns for flexible metadata

## API Response Patterns

### Standard Response Format
```typescript
interface APIResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}
```

### Error Handling Pattern
```python
# Standard HTTP status codes
200: Success with data
201: Created successfully  
400: Bad request (validation)
401: Unauthorized
403: Forbidden
404: Not found
422: Validation error
500: Internal server error
```

## Frontend Component Patterns

### Page Component Structure
```typescript
// pages/dashboard.tsx
export default function DashboardPage() {
  const { data, loading, error } = useAPI('/api/dashboard');
  
  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;
  
  return (
    <Layout>
      <DashboardContent data={data} />
    </Layout>
  );
}
```

### React Flow Pattern
```typescript
// Using @xyflow/react for workflow editor
import { ReactFlow, useNodesState, useEdgesState } from '@xyflow/react';

const WorkflowEditor = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  
  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
    />
  );
};
```

## State Management Patterns

### API State with SWR
```typescript
import useSWR from 'swr';

function useContacts() {
  const { data, error, mutate } = useSWR('/api/contacts', fetcher);
  
  return {
    contacts: data,
    isLoading: !error && !data,
    isError: error,
    mutate
  };
}
```

### Form State with React Hook Form
```typescript
import { useForm } from 'react-hook-form';

interface ContactForm {
  name: string;
  email: string;
  phone: string;
}

function ContactForm() {
  const { register, handleSubmit, formState: { errors } } = useForm<ContactForm>();
  
  const onSubmit = (data: ContactForm) => {
    // API call
  };
  
  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register('name', { required: true })} />
      {errors.name && <span>Name is required</span>}
    </form>
  );
}
```

## Twilio Integration Pattern

### SMS Sending
```python
from twilio.rest import Client

async def send_sms(to: str, message: str):
    client = Client(TWILIO_SID, TWILIO_TOKEN)
    
    message = client.messages.create(
        body=message,
        from_=TWILIO_PHONE,
        to=to
    )
    
    return message.sid
```

### Webhook Handling
```python
@app.post("/webhooks/twilio/sms")
async def twilio_webhook(request: Request):
    form = await request.form()
    
    from_number = form.get('From')
    message_body = form.get('Body')
    
    # Process incoming SMS
    await process_incoming_sms(from_number, message_body)
    
    return TwiMLResponse()
```

## Docker Development Patterns

### Hot Reload Setup
```yaml
# docker-compose.yml
services:
  frontend:
    build: ./frontend
    ports:
      - "3300:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    environment:
      - NODE_ENV=development
      
  backend:
    build: ./backend
    ports:
      - "8300:8000"
    volumes:
      - ./backend:/app
    environment:
      - RELOAD=true
```

### Rebuild Pattern
```bash
# Full rebuild with cache clearing
docker compose up -d --build --remove-orphans --no-cache

# Quick rebuild (preserve cache)
docker compose up -d --build --remove-orphans
```

## Testing Patterns

### API Testing
```python
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client():
    return TestClient(app)

def test_create_contact(client):
    response = client.post("/api/contacts", json={
        "name": "Test User",
        "email": "test@example.com"
    })
    
    assert response.status_code == 201
    assert response.json()["name"] == "Test User"
```

### Frontend Testing with React Testing Library
```typescript
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

test('contact form submission', async () => {
  const user = userEvent.setup();
  render(<ContactForm />);
  
  await user.type(screen.getByLabelText(/name/i), 'John Doe');
  await user.click(screen.getByRole('button', { name: /submit/i }));
  
  expect(screen.getByText(/contact created/i)).toBeInTheDocument();
});
```