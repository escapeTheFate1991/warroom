# WAR ROOM Paywall Architecture

**Last Updated:** 2026-03-19  
**Status:** Planning Document (No Code Implementation)

## Overview

This document outlines the paywall implementation strategy for WAR ROOM's AI Automation Services. The goal is to gate features by subscription tier while maintaining a seamless user experience and clear upgrade paths.

## 1. Feature Inventory by Tier

### Tier 1: Starter (Foundation) - $99/month
**Target:** Small businesses, solopreneurs, first-time AI adopters

**Included Features:**
- **CRM Basic:** Contact management (up to 1,000 contacts), basic deal pipeline
- **AI Studio:** Basic content generation (10 posts/month), simple templates
- **Social Media:** Connect 2 accounts, basic scheduling
- **Messaging:** WhatsApp OR Telegram integration
- **Analytics:** Basic reports, 30-day data retention
- **Support:** Email support (48h response)
- **OpenClaw:** 1 managed agent, 1M tokens/month

**Limited/Restricted:**
- Advanced CRM workflows (locked)
- Bulk content generation (locked)
- Multiple social accounts (locked)
- Video editing features (locked)
- Real-time notifications (locked)
- Advanced analytics (locked)
- API access (locked)

### Tier 2: Professional - $299/month
**Target:** Growing businesses, marketing teams, agencies

**Included Features:**
- **CRM Advanced:** Unlimited contacts, custom pipelines, automation workflows
- **AI Studio:** Unlimited content generation, advanced templates, competitor analysis
- **Social Media:** Connect unlimited accounts, advanced scheduling, bulk operations
- **Video Editing:** Full video editor, templates, automated editing
- **Messaging:** WhatsApp + Discord + Slack integration
- **Analytics:** Advanced reports, 12-month retention, custom dashboards
- **Support:** Priority Slack support (12h response)
- **OpenClaw:** 3 dedicated agents, 5M tokens/month, advanced orchestration

**Exclusive Features:**
- Custom business logic automation
- Advanced CRM segmentation
- White-label options
- Webhook integrations
- Advanced video editing

### Tier 3: Enterprise - Custom Pricing
**Target:** Large organizations, custom requirements

**Included Features:**
- **Everything in Professional**
- **Custom Development:** Dedicated AI engineer, custom features
- **Infrastructure:** Unlimited agents, BYO API keys, custom heartbeat
- **Support:** Dedicated success manager, 24/7 phone support
- **Compliance:** SOC2, HIPAA compliance options
- **Integration:** Custom API development, enterprise SSO
- **Deployment:** On-premise or private cloud options

## 2. Gating Mechanism

### Database Schema
```sql
-- Add tier tracking to users table (already implemented)
ALTER TABLE crm.users 
ADD COLUMN user_tier INTEGER DEFAULT 1,
ADD COLUMN is_grandfathered BOOLEAN DEFAULT false;

-- Subscription tracking table
CREATE TABLE crm.subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES crm.users(id),
    product_id INTEGER REFERENCES crm.products(id),
    stripe_subscription_id TEXT,
    status TEXT, -- active, cancelled, past_due, etc.
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Usage tracking for metered billing
CREATE TABLE crm.usage_tracking (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES crm.users(id),
    resource_type TEXT, -- tokens, api_calls, contacts, etc.
    amount INTEGER,
    period_start DATE,
    period_end DATE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Middleware Checks
```typescript
// Backend: Feature access middleware
export function requireTier(minTier: number) {
  return async (req: Request, res: Response, next: NextFunction) => {
    const user = req.user;
    const userTier = user.is_grandfathered ? 1 : user.user_tier;
    
    if (userTier < minTier) {
      return res.status(403).json({
        error: 'Upgrade required',
        required_tier: minTier,
        current_tier: userTier,
        upgrade_url: '/pricing'
      });
    }
    
    next();
  };
}

// Usage example
router.get('/api/crm/advanced-workflows', requireTier(2), handler);
```

### Component-Level Guards
```typescript
// Frontend: Feature gating hook
export function useFeatureAccess() {
  const { user } = useAuth();
  
  const hasFeature = (feature: string): boolean => {
    const userTier = user.is_grandfathered ? 1 : user.user_tier;
    
    const featureMap = {
      'advanced_workflows': 2,
      'video_editing': 2,
      'unlimited_contacts': 2,
      'custom_logic': 2,
      'api_access': 3,
      'dedicated_engineer': 3
    };
    
    return userTier >= (featureMap[feature] || 1);
  };
  
  const getUpgradeInfo = (feature: string) => ({
    required_tier: featureMap[feature] || 1,
    current_tier: user.user_tier,
    is_grandfathered: user.is_grandfathered
  });
  
  return { hasFeature, getUpgradeInfo };
}
```

## 3. UI for Locked Features

### Overlay Component
```typescript
interface FeatureGateProps {
  feature: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export function FeatureGate({ feature, children, fallback }: FeatureGateProps) {
  const { hasFeature, getUpgradeInfo } = useFeatureAccess();
  
  if (hasFeature(feature)) {
    return <>{children}</>;
  }
  
  const upgradeInfo = getUpgradeInfo(feature);
  
  return (
    <div className="relative">
      {/* Blurred/grayed content */}
      <div className="blur-sm opacity-50 pointer-events-none">
        {children}
      </div>
      
      {/* Upgrade overlay */}
      <div className="absolute inset-0 flex items-center justify-center bg-black/60 rounded-lg">
        <div className="text-center p-6 bg-warroom-surface rounded-lg border border-warroom-border max-w-sm">
          <Crown className="w-8 h-8 text-yellow-500 mx-auto mb-3" />
          <h3 className="font-semibold text-warroom-text mb-2">
            Unlock This Feature
          </h3>
          <p className="text-sm text-warroom-muted mb-4">
            Upgrade to Tier {upgradeInfo.required_tier} to access this feature
          </p>
          <button 
            onClick={() => router.push('/pricing')}
            className="bg-warroom-accent hover:bg-warroom-accent/80 text-white px-4 py-2 rounded-lg text-sm font-medium"
          >
            View Plans
          </button>
        </div>
      </div>
    </div>
  );
}
```

### Usage Examples
```typescript
// Lock entire sections
<FeatureGate feature="advanced_workflows">
  <AdvancedWorkflowBuilder />
</FeatureGate>

// Lock specific buttons
<FeatureGate 
  feature="video_editing" 
  fallback={
    <button disabled className="opacity-50">
      Video Editor (Pro Feature)
    </button>
  }
>
  <button onClick={openVideoEditor}>
    Open Video Editor
  </button>
</FeatureGate>
```

## 4. Upgrade Flow

### User Journey
1. **Feature Discovery** → User encounters locked feature
2. **Education** → Overlay explains benefit and required tier
3. **Comparison** → Click "View Plans" → Pricing page with feature comparison
4. **Selection** → User selects plan → Stripe Checkout
5. **Processing** → Stripe processes payment → Webhook updates user tier
6. **Activation** → Feature unlocks immediately → Success notification

### Implementation Steps
```typescript
// 1. Pricing page with clear CTAs
export function PricingPage() {
  return (
    <div className="grid md:grid-cols-3 gap-8">
      {pricingTiers.map(tier => (
        <PricingCard 
          key={tier.id}
          tier={tier}
          onSelect={() => startCheckout(tier.stripe_price_id)}
        />
      ))}
    </div>
  );
}

// 2. Stripe Checkout integration
async function startCheckout(priceId: string) {
  const response = await authFetch('/api/billing/create-checkout', {
    method: 'POST',
    body: JSON.stringify({ price_id: priceId })
  });
  
  const { checkout_url } = await response.json();
  window.location.href = checkout_url;
}

// 3. Webhook handler for subscription updates
router.post('/api/webhooks/stripe', async (req, res) => {
  const event = req.body;
  
  if (event.type === 'customer.subscription.created' || 
      event.type === 'customer.subscription.updated') {
    
    const subscription = event.data.object;
    await updateUserTier(subscription.customer, subscription.items);
  }
  
  res.status(200).send('OK');
});
```

## 5. Grandfathering System

### Founding Member Logic
```sql
-- First 100 customers get grandfathered pricing
UPDATE crm.users 
SET is_grandfathered = true 
WHERE id IN (
  SELECT id FROM crm.users 
  ORDER BY created_at 
  LIMIT 100
);
```

### Stripe Price IDs
- **Regular Starter:** `price_starter_regular` ($99)
- **Grandfathered Starter:** `price_starter_founding` ($99, locked forever)
- **Regular Professional:** `price_pro_regular` ($299)
- **Regular Enterprise:** Custom pricing

### Grandfathering Rules
1. **Locked Rate:** Grandfathered users pay $99 forever, even if prices increase
2. **Upgrade Path:** Can upgrade to Pro/Enterprise at regular rates
3. **Downgrade Protection:** If they downgrade, they return to $99 Starter
4. **Badge Display:** Show "Founding Member" badge in UI
5. **Stripe Handling:** Separate price IDs ensure billing isolation

## 6. Stripe Metered Billing

### Token Usage Tracking
```typescript
// Track LLM API calls
async function trackTokenUsage(userId: number, tokens: number) {
  await db.query(`
    INSERT INTO crm.usage_tracking (user_id, resource_type, amount, period_start, period_end)
    VALUES ($1, 'tokens', $2, DATE_TRUNC('month', NOW()), 
            DATE_TRUNC('month', NOW()) + INTERVAL '1 month' - INTERVAL '1 day')
    ON CONFLICT (user_id, resource_type, period_start) 
    DO UPDATE SET amount = usage_tracking.amount + $2
  `, [userId, tokens]);
}

// Usage monitoring and auto-refill
async function checkUsageLimits() {
  const users = await db.query(`
    SELECT u.id, u.user_tier, ut.amount, p.features::json->'tokens' as token_limit
    FROM crm.users u
    JOIN crm.usage_tracking ut ON u.id = ut.user_id
    JOIN crm.products p ON p.tier_level = u.user_tier
    WHERE ut.resource_type = 'tokens'
      AND ut.period_start = DATE_TRUNC('month', NOW())
      AND ut.amount > (p.features::json->'tokens')::int * 0.9  -- 90% threshold
  `);
  
  for (const user of users) {
    if (user.amount / user.token_limit > 0.9) {
      await offerTokenRefill(user.id);
    }
  }
}

// Auto-refill mechanism
async function offerTokenRefill(userId: number) {
  const refillPrice = 'price_token_refill_1m'; // $20 for 1M tokens
  
  // Create Stripe checkout for token refill
  await stripe.checkout.sessions.create({
    customer: user.stripe_customer_id,
    line_items: [{
      price: refillPrice,
      quantity: 1,
    }],
    mode: 'payment',
    success_url: `${process.env.APP_URL}/billing/success?refill=true`,
    cancel_url: `${process.env.APP_URL}/billing`,
  });
}
```

### Hard Caps and Safety
```typescript
// Prevent runaway token usage
async function enforceTokenLimits(userId: number, requestedTokens: number) {
  const currentUsage = await getCurrentMonthUsage(userId);
  const userLimits = await getUserLimits(userId);
  
  // Hard cap: 110% of plan limit
  const hardCap = userLimits.tokens * 1.1;
  
  if (currentUsage + requestedTokens > hardCap) {
    throw new Error('Monthly token limit exceeded. Please upgrade or purchase additional tokens.');
  }
  
  // Soft warning at 90%
  if (currentUsage + requestedTokens > userLimits.tokens * 0.9) {
    await notifyApproachingLimit(userId);
  }
  
  return true;
}
```

## 7. Implementation Timeline

### Phase 1: Foundation (Week 1)
- [ ] Database schema updates
- [ ] Basic tier checking middleware
- [ ] Simple feature gates on key sections
- [ ] Pricing page display

### Phase 2: Core Gating (Week 2)
- [ ] Component-level feature gates
- [ ] Upgrade flow implementation
- [ ] Stripe checkout integration
- [ ] Webhook handlers

### Phase 3: Polish & Metering (Week 3)
- [ ] Usage tracking system
- [ ] Auto-refill mechanism
- [ ] Grandfathering logic
- [ ] Admin tools for tier management

### Phase 4: Launch Prep (Week 4)
- [ ] Testing and QA
- [ ] Documentation
- [ ] Customer communication
- [ ] Analytics and monitoring

## 8. Success Metrics

### Revenue Metrics
- **Monthly Recurring Revenue (MRR)** growth
- **Average Revenue Per User (ARPU)** by tier
- **Upgrade conversion rate** from Starter to Professional
- **Churn rate** by tier

### Usage Metrics
- **Feature adoption** by tier
- **Token usage patterns** and refill rates
- **Support ticket volume** by tier
- **Time to upgrade** after hitting limits

### Product Metrics
- **Feature gate interaction rates**
- **Upgrade CTA click-through rates**
- **Abandoned checkout recovery**
- **Customer satisfaction** by tier

---

**Next Steps:** Review this document with the team, validate pricing strategy, and begin Phase 1 implementation.