# War Room API Context

## Authentication Endpoints

### POST /auth/login
```yaml
description: Authenticate user and return JWT token
request:
  email: string
  password: string
response:
  access_token: string
  token_type: "bearer"
  user: User
```

### POST /auth/logout
```yaml
description: Invalidate current session
headers:
  Authorization: Bearer <token>
response:
  message: "Logged out successfully"
```

## CRM API Endpoints

### Contacts
```yaml
GET /api/crm/contacts:
  description: List all contacts with pagination
  query_params:
    page: integer (default: 1)
    limit: integer (default: 20)
    search: string (optional)
  response:
    data: Contact[]
    total: integer
    page: integer
    pages: integer

POST /api/crm/contacts:
  description: Create new contact
  request:
    name: string
    email: string (optional)
    phone: string (optional)
    company: string (optional)
    tags: string[] (optional)
  response:
    id: integer
    name: string
    email: string
    phone: string
    created_at: datetime

GET /api/crm/contacts/{id}:
  description: Get contact by ID
  response: Contact

PUT /api/crm/contacts/{id}:
  description: Update contact
  request: Partial<Contact>
  response: Contact

DELETE /api/crm/contacts/{id}:
  description: Soft delete contact
  response:
    message: "Contact deleted"
```

### Deals
```yaml
GET /api/crm/deals:
  description: List deals with pipeline info
  query_params:
    pipeline_id: integer (optional)
    stage: string (optional)
    contact_id: integer (optional)
  response:
    data: Deal[]
    total: integer

POST /api/crm/deals:
  description: Create new deal
  request:
    title: string
    value: decimal
    contact_id: integer
    pipeline_id: integer
    stage: string
    close_date: date (optional)
  response: Deal

PUT /api/crm/deals/{id}/stage:
  description: Move deal to different stage
  request:
    stage: string
    notes: string (optional)
  response: Deal
```

## Lead Generation API

### Search Jobs
```yaml
GET /api/leadgen/search-jobs:
  description: List configured search jobs
  response:
    data: SearchJob[]

POST /api/leadgen/search-jobs:
  description: Create new search job
  request:
    name: string
    platform: "linkedin" | "indeed" | "custom"
    query: string
    filters: object
    schedule: string (cron format)
  response: SearchJob

GET /api/leadgen/search-jobs/{id}/results:
  description: Get leads from search job
  response:
    data: Lead[]
    total: integer
```

### Leads
```yaml
GET /api/leadgen/leads:
  description: List generated leads
  query_params:
    status: "new" | "contacted" | "qualified" | "converted"
    source: string (optional)
    date_from: date (optional)
    date_to: date (optional)
  response:
    data: Lead[]
    total: integer

POST /api/leadgen/leads/{id}/convert:
  description: Convert lead to contact
  response: Contact
```

## Social Media API

### Social Accounts
```yaml
GET /api/social/accounts:
  description: List connected social accounts
  response:
    data: SocialAccount[]

POST /api/social/accounts:
  description: Connect new social account
  request:
    platform: "instagram" | "twitter" | "linkedin"
    username: string
    credentials: object
  response: SocialAccount

GET /api/social/accounts/{id}/analytics:
  description: Get account analytics
  query_params:
    period: "day" | "week" | "month"
  response:
    followers: integer
    engagement_rate: decimal
    posts: integer
    reach: integer
```

## Communication API

### SMS (Twilio)
```yaml
POST /api/communication/sms:
  description: Send SMS message
  request:
    to: string (phone number)
    message: string
    contact_id: integer (optional)
  response:
    message_sid: string
    status: string

GET /api/communication/sms:
  description: List SMS messages
  query_params:
    contact_id: integer (optional)
    direction: "inbound" | "outbound"
  response:
    data: SMSMessage[]
```

### Webhooks
```yaml
POST /webhooks/twilio/sms:
  description: Handle incoming Twilio SMS webhook
  request: (form data from Twilio)
    From: string
    To: string
    Body: string
    MessageSid: string
  response: TwiML

POST /webhooks/social/{platform}:
  description: Handle social media webhooks
  request: (varies by platform)
  response: { "status": "ok" }
```

## Workflow API

### Templates
```yaml
GET /api/workflows/templates:
  description: List workflow templates
  response:
    data: WorkflowTemplate[]

POST /api/workflows/templates:
  description: Create workflow template
  request:
    name: string
    description: string
    nodes: ReactFlowNode[]
    edges: ReactFlowEdge[]
  response: WorkflowTemplate
```

### Executions
```yaml
POST /api/workflows/execute:
  description: Execute workflow
  request:
    template_id: integer
    inputs: object
    trigger_data: object (optional)
  response:
    execution_id: string
    status: "started" | "running" | "completed" | "failed"

GET /api/workflows/executions/{id}:
  description: Get workflow execution status
  response:
    id: string
    status: string
    outputs: object
    logs: WorkflowLog[]
```

## Quick Actions API

### Contact Actions
```yaml
POST /api/quick-actions/call:
  description: Initiate call to contact
  request:
    contact_id: integer
    notes: string (optional)
  response:
    call_sid: string
    status: string

POST /api/quick-actions/email:
  description: Send email to contact
  request:
    contact_id: integer
    subject: string
    body: string
    template_id: integer (optional)
  response:
    message_id: string
    status: string
```

## Dashboard API

### Analytics
```yaml
GET /api/dashboard/stats:
  description: Get dashboard statistics
  query_params:
    period: "day" | "week" | "month"
  response:
    contacts_count: integer
    deals_count: integer
    deals_value: decimal
    leads_count: integer
    conversion_rate: decimal

GET /api/dashboard/recent-activity:
  description: Get recent activity feed
  response:
    data: ActivityItem[]
```

## Error Handling

### Standard Error Response
```yaml
error_response:
  error: string (error type)
  message: string (human readable)
  details: object (optional, validation errors)
  
example:
  error: "validation_error"
  message: "Invalid email format"
  details:
    field: "email"
    code: "invalid_format"
```

### Common Error Codes
```yaml
400: "bad_request"
401: "unauthorized" 
403: "forbidden"
404: "not_found"
422: "validation_error"
429: "rate_limit_exceeded"
500: "internal_server_error"
```

## Rate Limiting

### Limits
```yaml
authentication: 5/minute per IP
api_calls: 100/minute per user
webhooks: unlimited (trusted sources)
```

### Headers
```yaml
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1648576800
```