-- Agent Chat Migration: Chat messages and task queue tables
-- Creates tables for agent-to-user conversations and task assignments

-- Agent chat messages table
CREATE TABLE IF NOT EXISTS public.agent_chat_messages (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    agent_instance_id INTEGER NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'agent', 'system')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    task_id TEXT, -- links to a task if this is task-related
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_agent_chat_org ON public.agent_chat_messages(org_id);
CREATE INDEX IF NOT EXISTS idx_agent_chat_user ON public.agent_chat_messages(user_id, agent_instance_id);
CREATE INDEX IF NOT EXISTS idx_agent_chat_agent ON public.agent_chat_messages(agent_instance_id);
CREATE INDEX IF NOT EXISTS idx_agent_chat_created ON public.agent_chat_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_agent_chat_task ON public.agent_chat_messages(task_id) WHERE task_id IS NOT NULL;

-- Agent task assignments (which tasks are assigned to which agent)
CREATE TABLE IF NOT EXISTS public.agent_task_queue (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL,
    agent_instance_id INTEGER NOT NULL,
    assigned_by_user_id INTEGER NOT NULL,
    task_title TEXT NOT NULL,
    task_description TEXT DEFAULT '',
    task_type TEXT DEFAULT 'general',
    priority INTEGER DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'assigned', 'in_progress', 'completed', 'failed', 'cancelled')),
    result JSONB,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for task queue
CREATE INDEX IF NOT EXISTS idx_task_queue_org ON public.agent_task_queue(org_id);
CREATE INDEX IF NOT EXISTS idx_task_queue_agent ON public.agent_task_queue(agent_instance_id, status);
CREATE INDEX IF NOT EXISTS idx_task_queue_user ON public.agent_task_queue(assigned_by_user_id);
CREATE INDEX IF NOT EXISTS idx_task_queue_priority ON public.agent_task_queue(priority, created_at);
CREATE INDEX IF NOT EXISTS idx_task_queue_status ON public.agent_task_queue(status);