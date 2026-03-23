# War Room Frontend Context

## Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── (dashboard)/        # Dashboard route group
│   │   ├── auth/               # Authentication pages
│   │   └── layout.tsx          # Root layout
│   ├── components/             # Reusable components
│   │   ├── ui/                 # Base UI components
│   │   ├── forms/              # Form components
│   │   ├── dashboard/          # Dashboard-specific
│   │   └── workflow/           # React Flow components
│   ├── hooks/                  # Custom React hooks
│   ├── lib/                    # Utilities and configurations
│   ├── store/                  # State management
│   └── types/                  # TypeScript type definitions
├── public/                     # Static assets
└── styles/                     # Global styles (Tailwind CSS)
```

## Technology Stack

### Core Technologies
- **Framework**: Next.js 14 with App Router
- **Styling**: Tailwind CSS
- **UI Components**: Custom components + shadcn/ui
- **Workflow Editor**: React Flow (@xyflow/react)
- **State Management**: Zustand + SWR for server state
- **Forms**: React Hook Form + Zod validation
- **Icons**: Lucide React
- **TypeScript**: Full type safety

### Key Dependencies
```json
{
  "next": "^14.0.0",
  "react": "^18.0.0",
  "@xyflow/react": "^12.0.0",
  "tailwindcss": "^3.4.0",
  "zustand": "^4.4.0",
  "swr": "^2.2.0",
  "react-hook-form": "^7.48.0",
  "zod": "^3.22.0",
  "lucide-react": "^0.292.0"
}
```

## Component Architecture

### Layout Pattern
```typescript
// app/layout.tsx
export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  )
}

// app/(dashboard)/layout.tsx
export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex h-screen bg-gray-100">
      <Sidebar />
      <main className="flex-1 overflow-hidden">
        <Header />
        <div className="p-6">
          {children}
        </div>
      </main>
    </div>
  )
}
```

### Component Composition
```typescript
// components/ui/Button.tsx
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'primary' | 'secondary' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'default',
  size = 'md',
  loading = false,
  children,
  className,
  ...props
}) => {
  const baseClasses = 'inline-flex items-center justify-center rounded-md font-medium';
  const variants = {
    default: 'bg-gray-100 text-gray-900 hover:bg-gray-200',
    primary: 'bg-blue-600 text-white hover:bg-blue-700',
    secondary: 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50',
    danger: 'bg-red-600 text-white hover:bg-red-700'
  };
  
  return (
    <button
      className={cn(baseClasses, variants[variant], className)}
      disabled={loading}
      {...props}
    >
      {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
};
```

## State Management Patterns

### Zustand Store
```typescript
// store/auth.ts
interface AuthState {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: null,
  
  login: async (email: string, password: string) => {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    
    const data = await response.json();
    
    if (response.ok) {
      set({ user: data.user, token: data.access_token });
      localStorage.setItem('token', data.access_token);
    } else {
      throw new Error(data.message);
    }
  },
  
  logout: () => {
    set({ user: null, token: null });
    localStorage.removeItem('token');
  }
}));
```

### SWR Data Fetching
```typescript
// hooks/useContacts.ts
import useSWR from 'swr';
import { Contact } from '@/types';

const fetcher = (url: string) => fetch(url).then(res => res.json());

export function useContacts(page = 1, limit = 20) {
  const { data, error, mutate } = useSWR<{
    data: Contact[];
    total: number;
    page: number;
    pages: number;
  }>(`/api/crm/contacts?page=${page}&limit=${limit}`, fetcher);

  return {
    contacts: data?.data || [],
    total: data?.total || 0,
    isLoading: !error && !data,
    isError: error,
    mutate
  };
}
```

## React Flow Integration

### Workflow Editor Component
```typescript
// components/workflow/WorkflowEditor.tsx
import { ReactFlow, useNodesState, useEdgesState, addEdge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

interface WorkflowEditorProps {
  initialNodes?: Node[];
  initialEdges?: Edge[];
  onSave?: (nodes: Node[], edges: Edge[]) => void;
}

export const WorkflowEditor: React.FC<WorkflowEditorProps> = ({
  initialNodes = [],
  initialEdges = [],
  onSave
}) => {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onConnect = useCallback(
    (params: Edge | Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const handleSave = () => {
    onSave?.(nodes, edges);
  };

  return (
    <div className="h-screen w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
      >
        <Controls />
        <MiniMap />
        <Background />
      </ReactFlow>
      
      <div className="absolute top-4 right-4">
        <Button onClick={handleSave}>Save Workflow</Button>
      </div>
    </div>
  );
};
```

### Custom Node Types
```typescript
// components/workflow/nodes/index.ts
import { Node, NodeTypes } from '@xyflow/react';

export const nodeTypes: NodeTypes = {
  'trigger': TriggerNode,
  'action': ActionNode,
  'condition': ConditionNode,
  'delay': DelayNode
};

// components/workflow/nodes/TriggerNode.tsx
export const TriggerNode: React.FC<NodeProps> = ({ data, selected }) => {
  return (
    <div className={cn(
      "px-4 py-2 shadow-md rounded-md border-2",
      selected ? "border-blue-500" : "border-gray-300",
      "bg-white"
    )}>
      <div className="flex items-center">
        <Zap className="w-4 h-4 mr-2 text-yellow-500" />
        <span className="text-sm font-medium">{data.label}</span>
      </div>
      
      <Handle
        type="source"
        position={Position.Right}
        className="w-2 h-2 bg-blue-500"
      />
    </div>
  );
};
```

## Form Handling

### Form Components with React Hook Form
```typescript
// components/forms/ContactForm.tsx
interface ContactFormData {
  name: string;
  email: string;
  phone: string;
  company?: string;
}

const contactSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  email: z.string().email('Invalid email').optional().or(z.literal('')),
  phone: z.string().optional(),
  company: z.string().optional()
});

export const ContactForm: React.FC<{
  contact?: Contact;
  onSubmit: (data: ContactFormData) => Promise<void>;
}> = ({ contact, onSubmit }) => {
  const form = useForm<ContactFormData>({
    resolver: zodResolver(contactSchema),
    defaultValues: contact || {
      name: '',
      email: '',
      phone: '',
      company: ''
    }
  });

  const handleSubmit = async (data: ContactFormData) => {
    try {
      await onSubmit(data);
      form.reset();
    } catch (error) {
      form.setError('root', { message: 'Failed to save contact' });
    }
  };

  return (
    <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
      <div>
        <label htmlFor="name">Name *</label>
        <Input {...form.register('name')} />
        {form.formState.errors.name && (
          <p className="text-red-500 text-sm mt-1">
            {form.formState.errors.name.message}
          </p>
        )}
      </div>
      
      <div>
        <label htmlFor="email">Email</label>
        <Input type="email" {...form.register('email')} />
      </div>
      
      <Button type="submit" loading={form.formState.isSubmitting}>
        {contact ? 'Update' : 'Create'} Contact
      </Button>
    </form>
  );
};
```

## Quick Actions Pattern

### Action Buttons
```typescript
// components/dashboard/QuickActions.tsx
interface QuickActionsProps {
  contact: Contact;
}

export const QuickActions: React.FC<QuickActionsProps> = ({ contact }) => {
  const [loading, setLoading] = useState<string | null>(null);

  const handleCall = async () => {
    setLoading('call');
    try {
      await fetch('/api/quick-actions/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ contact_id: contact.id })
      });
    } catch (error) {
      console.error('Call failed:', error);
    } finally {
      setLoading(null);
    }
  };

  const handleSMS = async () => {
    setLoading('sms');
    // SMS logic
    setLoading(null);
  };

  const handleEmail = async () => {
    setLoading('email');
    // Email logic
    setLoading(null);
  };

  return (
    <div className="flex space-x-2">
      <Button
        size="sm"
        onClick={handleCall}
        loading={loading === 'call'}
        disabled={!contact.phone}
      >
        <Phone className="w-4 h-4 mr-1" />
        Call
      </Button>
      
      <Button
        size="sm"
        onClick={handleSMS}
        loading={loading === 'sms'}
        disabled={!contact.phone}
      >
        <MessageSquare className="w-4 h-4 mr-1" />
        SMS
      </Button>
      
      <Button
        size="sm"
        onClick={handleEmail}
        loading={loading === 'email'}
        disabled={!contact.email}
      >
        <Mail className="w-4 h-4 mr-1" />
        Email
      </Button>
    </div>
  );
};
```

## TypeScript Types

### Core Types
```typescript
// types/index.ts
export interface User {
  id: number;
  email: string;
  name: string;
  created_at: string;
}

export interface Contact {
  id: number;
  name: string;
  email?: string;
  phone?: string;
  company?: string;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface Deal {
  id: number;
  title: string;
  value: number;
  contact_id: number;
  contact?: Contact;
  pipeline_id: number;
  stage: string;
  close_date?: string;
  created_at: string;
}

export interface WorkflowTemplate {
  id: number;
  name: string;
  description: string;
  nodes: Node[];
  edges: Edge[];
  created_at: string;
}
```

## Styling Patterns

### Tailwind Configuration
```typescript
// tailwind.config.ts
export default {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0f9ff',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        }
      },
      fontFamily: {
        sans: ['Inter', ...defaultTheme.fontFamily.sans],
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
};
```

### Component Styling
```typescript
// lib/cn.ts (className utility)
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Usage
<div className={cn(
  "base-styles",
  condition && "conditional-styles",
  className // external className prop
)} />
```