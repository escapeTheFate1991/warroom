-- Content Scheduler Upgrade Migration
-- Adds recycling, multi-account, optimal timing, and series support

ALTER TABLE public.scheduled_posts ADD COLUMN IF NOT EXISTS social_account_id INTEGER;
ALTER TABLE public.scheduled_posts ADD COLUMN IF NOT EXISTS is_recycled BOOLEAN DEFAULT false;
ALTER TABLE public.scheduled_posts ADD COLUMN IF NOT EXISTS original_post_id INTEGER;
ALTER TABLE public.scheduled_posts ADD COLUMN IF NOT EXISTS recycle_count INTEGER DEFAULT 0;
ALTER TABLE public.scheduled_posts ADD COLUMN IF NOT EXISTS optimal_time_used BOOLEAN DEFAULT false;
ALTER TABLE public.scheduled_posts ADD COLUMN IF NOT EXISTS engagement_score NUMERIC(8,4) DEFAULT 0;
ALTER TABLE public.scheduled_posts ADD COLUMN IF NOT EXISTS series_id INTEGER;
ALTER TABLE public.scheduled_posts ADD COLUMN IF NOT EXISTS series_order INTEGER DEFAULT 0;

-- Add foreign key reference to original post for recycling
ALTER TABLE public.scheduled_posts ADD CONSTRAINT fk_original_post 
    FOREIGN KEY (original_post_id) REFERENCES public.scheduled_posts(id) ON DELETE SET NULL;

-- Add foreign key reference to social accounts (optional, may not exist yet)
-- ALTER TABLE public.scheduled_posts ADD CONSTRAINT fk_social_account 
--     FOREIGN KEY (social_account_id) REFERENCES crm.social_accounts(id) ON DELETE SET NULL;

-- Create index for recycling queries
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_engagement_score ON public.scheduled_posts(engagement_score DESC);
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_recyclable ON public.scheduled_posts(org_id, platform, is_recycled, status);
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_series ON public.scheduled_posts(series_id, series_order);
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_account ON public.scheduled_posts(social_account_id);