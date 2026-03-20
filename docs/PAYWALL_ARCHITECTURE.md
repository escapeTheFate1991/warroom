# Paywall Architecture for WAR ROOM Platform

**Version:** 1.0  
**Date:** March 20, 2026  
**Author:** Agent 5  

## Overview

This document outlines the paywall implementation strategy for the WAR ROOM platform, supporting three AI Automation Services (ALEC) tiers with grandfathering logic and usage-based billing.

## Feature Inventory by Tier

### Tier 1: Starter (Foundation) - $99/month
**Target:** Small businesses starting their AI journey  
**Grandfathered:** First 100 customers locked at $99 pricing  

**Included Features:**
- ✅ Basic CRM (Contacts, Organizations, up to 1,000 records)
- ✅ 1 Managed OpenClaw Agent
- ✅ 1,000,000 Standard Tokens per month
- ✅ 24/7 Heartbeat monitoring (every 30 minutes)
- ✅ WhatsApp OR Telegram messaging
- ✅ Email support (48-hour response)
- ✅ Basic reports (Overview, Contact activity)
- ✅ Single calendar integration
- ✅ 5 workflow automations
- ✅ Basic library search
- ✅ Standard content templates

**Restricted Features:**
- ❌ Advanced CRM features (Custom fields, Advanced pipelines)
- ❌ Multi-agent orchestration
- ❌ Discord/Slack integrations
- ❌ Priority support
- ❌ Custom business logic
- ❌ API access
- ❌ Advanced analytics
- ❌ White-label options
- ❌ Unlimited token usage

### Tier 2: Professional - $299/month  
**Target:** Growing businesses ready to scale automation  

**All Tier 1 features PLUS:**
- ✅ 3 Dedicated OpenClaw Agents
- ✅ 5,000,000 Standard Tokens per month
- ✅ 24/7 Heartbeat monitoring (every 5 minutes)
- ✅ WhatsApp + Discord + Slack messaging
- ✅ Priority Slack support (12-hour response)
- ✅ Advanced CRM orchestration
- ✅ Custom business logic
- ✅ Advanced pipelines and custom fields
- ✅ Up to 10,000 CRM records
- ✅ 25 workflow automations
- ✅ Advanced analytics and reporting
- ✅ Multiple calendar integrations
- ✅ Team collaboration features
- ✅ Content scheduling and recycling
- ✅ Competitor intelligence features

**Still Restricted:**
- ❌ Unlimited agents
- ❌ White-label options
- ❌ Dedicated AI Engineer
- ❌ Custom SLA agreements
- ❌ On-premise deployment

### Tier 3: Enterprise - Custom Pricing
**Target:** Enterprise-scale operations  

**All Tier 1 & 2 features PLUS:**
- ✅ Unlimited OpenClaw Agents
- ✅ Unlimited tokens OR BYO API key
- ✅ Real-time heartbeat monitoring (custom intervals)
- ✅ All communication channels + API access
- ✅ Dedicated AI Engineer
- ✅ Custom SLA agreements
- ✅ White-label options
- ✅ On-premise deployment available
- ✅ Unlimited CRM records
- ✅ Unlimited workflows
- ✅ Custom integrations
- ✅ Advanced security features
- ✅ Audit logs and compliance tools

## Gating Mechanism

### Three-Layer Approach

#### 1. API-Level Checks (Backend)
```python
# Middleware for all CRM endpoints
@app.middleware("http")
async def tier_enforcement_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        user = await get_current_user(request)
        tier = await get_user_tier(user.id)
        feature = extract_feature_from_path(request.url.path)
        
        if not has_feature_access(tier, feature):
            return JSONResponse(
                status_code=402,
                content={
                    "error": "feature_restricted",
                    "message": f"This feature requires {get_required_tier(feature)} or higher",
                    "upgrade_url": "/pricing",
                    "current_tier": tier.name
                }
            )
    
    return await call_next(request)
```

#### 2. Component-Level Gating (Frontend)
```typescript
// Hook for feature access checks
const useFeatureAccess = (feature: string) => {
  const { user } = useAuth();
  const tier = user?.tier || 'starter';
  
  const hasAccess = useMemo(() => {
    return checkFeatureAccess(tier, feature);
  }, [tier, feature]);
  
  const requiredTier = getRequiredTier(feature);
  
  return { hasAccess, requiredTier, currentTier: tier };
};

// Usage in components
const { hasAccess, requiredTier } = useFeatureAccess('advanced_pipelines');

if (!hasAccess) {
  return <UpgradePrompt requiredTier={requiredTier} feature="Advanced Pipelines" />;
}
```

#### 3. Database-Level Constraints
```sql
-- Usage limits enforced at DB level
ALTER TABLE crm.contacts ADD CONSTRAINT tier_contact_limit 
CHECK (
  (SELECT COUNT(*) FROM crm.contacts WHERE org_id = crm.contacts.org_id) <= 
  (SELECT contact_limit FROM user_tiers WHERE tier = (SELECT tier FROM users WHERE org_id = crm.contacts.org_id))
);

-- Agent count limits
ALTER TABLE agents ADD CONSTRAINT tier_agent_limit
CHECK (
  (SELECT COUNT(*) FROM agents WHERE org_id = agents.org_id) <= 
  (SELECT agent_limit FROM user_tiers WHERE tier = (SELECT tier FROM users WHERE org_id = agents.org_id))
);
```

## UI Treatment for Locked Features

### Show, Don't Hide Principle
Never hide features completely. Instead:

#### 1. Visible but Disabled
```tsx
<button 
  disabled={!hasAccess}
  className={`btn ${hasAccess ? 'btn-primary' : 'btn-disabled'}`}
  onClick={hasAccess ? handleAction : () => setShowUpgrade(true)}
>
  {hasAccess ? 'Create Pipeline' : '🔒 Unlock Advanced Pipelines'}
</button>
```

#### 2. Feature Preview
```tsx
const AdvancedAnalytics = () => {
  const { hasAccess } = useFeatureAccess('advanced_analytics');
  
  return (
    <div className={`analytics-panel ${!hasAccess ? 'blur-sm' : ''}`}>
      {!hasAccess && <UpgradeOverlay feature="Advanced Analytics" />}
      <AnalyticsCharts data={mockData} />
    </div>
  );
};
```

#### 3. Usage Indicators
```tsx
const TokenUsage = () => {
  const { usage, limit } = useTokenUsage();
  const percentUsed = (usage / limit) * 100;
  
  return (
    <div className="usage-meter">
      <div className="usage-bar">
        <div 
          className={`fill ${percentUsed > 90 ? 'bg-red-500' : 'bg-green-500'}`}
          style={{ width: `${percentUsed}%` }}
        />
      </div>
      <span>{usage.toLocaleString()} / {limit.toLocaleString()} tokens</span>
      {percentUsed > 90 && (
        <UpgradePrompt message="Running low on tokens" />
      )}
    </div>
  );
};
```

## Upgrade Flow UX

### 1. Contextual Upgrade Prompts
- **Trigger:** User hits a tier limit or tries to use a restricted feature
- **Action:** Show modal with specific benefit of upgrading
- **CTA:** "Upgrade to Professional" vs generic "Upgrade Now"

### 2. Progressive Disclosure
```tsx
const UpgradeModal = ({ feature, requiredTier }) => {
  return (
    <Modal>
      <div className="upgrade-prompt">
        <h3>Unlock {feature}</h3>
        <p>This feature is available in {requiredTier} and higher plans.</p>
        
        <div className="tier-comparison">
          <CurrentTierColumn />
          <TargetTierColumn tier={requiredTier} highlightFeature={feature} />
        </div>
        
        <div className="upgrade-cta">
          <Button onClick={() => handleUpgrade(requiredTier)}>
            Upgrade to {requiredTier} - {getPrice(requiredTier)}/month
          </Button>
          <Button variant="ghost" onClick={handleContactSales}>
            Talk to Sales
          </Button>
        </div>
      </div>
    </Modal>
  );
};
```

### 3. Granular Upgrade Paths
- **Starter → Professional:** Focus on agent count and advanced features
- **Professional → Enterprise:** Focus on scale, customization, and support
- **Any → Custom:** Schedule consultation call

## Grandfathering Logic with Stripe

### 1. Database Schema
```sql
-- User grandfathering status
ALTER TABLE crm.users ADD COLUMN is_grandfathered BOOLEAN DEFAULT false;
ALTER TABLE crm.users ADD COLUMN grandfathered_tier TEXT; -- 'starter', 'professional', etc.
ALTER TABLE crm.users ADD COLUMN grandfathered_price DECIMAL(10,2); -- Locked-in price
```

### 2. Stripe Implementation
```python
# When creating subscription for grandfathered user
async def create_subscription(user_id: str, target_tier: str):
    user = await get_user(user_id)
    
    if user.is_grandfathered:
        # Use special grandfathered price
        price_id = f"price_grandfathered_{target_tier}"
        if not await stripe_price_exists(price_id):
            # Create special price for this user
            price_id = await stripe.Price.create(
                unit_amount=int(user.grandfathered_price * 100),  # Convert to cents
                currency='usd',
                recurring={'interval': 'month'},
                product=get_product_id(target_tier),
                metadata={'grandfathered_user': user_id}
            )
    else:
        price_id = get_standard_price(target_tier)
    
    return await stripe.Subscription.create(
        customer=user.stripe_customer_id,
        items=[{'price': price_id}],
        metadata={
            'user_id': user_id,
            'tier': target_tier,
            'grandfathered': str(user.is_grandfathered)
        }
    )
```

### 3. Grandfathering Rules
- **First 100 customers:** Automatically marked as grandfathered at Starter tier ($99)
- **Upgrade protection:** Grandfathered users keep founding member pricing when upgrading
- **Downgrade protection:** Can return to grandfathered tier at original price
- **Transfer protection:** Grandfathering status is non-transferable (tied to account)

## Usage-Based Billing (Token Metering)

### 1. Token Tracking
```python
# Track token usage in real-time
class TokenMeter:
    @staticmethod
    async def consume_tokens(user_id: str, amount: int, operation: str):
        usage = await get_current_usage(user_id)
        limit = await get_token_limit(user_id)
        
        if usage + amount > limit:
            # Check if auto-refill is enabled
            user = await get_user(user_id)
            if user.auto_refill_enabled:
                await trigger_auto_refill(user_id, amount)
            else:
                raise TokenLimitExceeded(f"Usage would exceed limit: {usage + amount} > {limit}")
        
        await record_usage(user_id, amount, operation)
        
        # Trigger alerts at 90% usage
        if (usage + amount) / limit >= 0.9:
            await send_usage_alert(user_id, usage + amount, limit)
```

### 2. Auto-Refill Logic ($20 at 90% usage)
```python
async def trigger_auto_refill(user_id: str, additional_tokens: int = 500_000):
    """Auto-purchase additional tokens when hitting 90% usage"""
    
    user = await get_user(user_id)
    
    # Create one-time charge for token refill
    charge = await stripe.PaymentIntent.create(
        amount=2000,  # $20.00 in cents
        currency='usd',
        customer=user.stripe_customer_id,
        description=f"Token refill: +{additional_tokens:,} tokens",
        automatic_payment_methods={'enabled': True}
    )
    
    if charge.status == 'succeeded':
        await add_token_credits(user_id, additional_tokens)
        await log_refill_event(user_id, additional_tokens, 20.00)
        await notify_user_refill(user_id, additional_tokens)
```

### 3. Hard Caps for Runaway Loops
```python
# Circuit breaker for excessive usage
class UsageCircuitBreaker:
    MAX_TOKENS_PER_HOUR = 50_000
    MAX_TOKENS_PER_DAY = 200_000
    
    @staticmethod
    async def check_rate_limits(user_id: str, requested_tokens: int):
        # Check hourly limit
        hourly_usage = await get_usage_in_window(user_id, hours=1)
        if hourly_usage + requested_tokens > UsageCircuitBreaker.MAX_TOKENS_PER_HOUR:
            await emergency_pause_agents(user_id)
            raise RateLimitExceeded("Hourly token limit exceeded - agents paused")
        
        # Check daily limit  
        daily_usage = await get_usage_in_window(user_id, hours=24)
        if daily_usage + requested_tokens > UsageCircuitBreaker.MAX_TOKENS_PER_DAY:
            await emergency_pause_agents(user_id)
            raise RateLimitExceeded("Daily token limit exceeded - agents paused")
```

### 4. Usage Monitoring Dashboard
```tsx
const UsageDashboard = () => {
  const { usage, limit, refills, projectedOverage } = useTokenUsage();
  
  return (
    <div className="usage-dashboard">
      <TokenMeter current={usage} limit={limit} />
      
      {projectedOverage > 0 && (
        <OverageWarning projected={projectedOverage} />
      )}
      
      <RefillHistory refills={refills} />
      
      <AutoRefillToggle />
    </div>
  );
};
```

## Implementation Priority

### Phase 1: Core Infrastructure
1. ✅ User tier tracking in database
2. ✅ Basic feature flags system
3. ✅ Stripe integration setup
4. ❌ Token usage tracking
5. ❌ API middleware for tier enforcement

### Phase 2: UI Components
1. ❌ Upgrade prompt components
2. ❌ Usage meters and indicators
3. ❌ Feature access hooks
4. ❌ Tier comparison modals

### Phase 3: Advanced Features
1. ❌ Auto-refill system
2. ❌ Usage analytics
3. ❌ Circuit breakers
4. ❌ Admin override capabilities

## Security Considerations

### 1. Client-Side vs Server-Side Enforcement
- **Client-side:** UI hints and UX improvements only
- **Server-side:** All actual enforcement and billing logic
- **Never trust the frontend** for access control

### 2. Audit Trail
```sql
CREATE TABLE tier_access_logs (
    id SERIAL PRIMARY KEY,
    user_id INT,
    feature_attempted TEXT,
    access_granted BOOLEAN,
    tier_at_time TEXT,
    timestamp TIMESTAMP DEFAULT NOW()
);
```

### 3. Bypass Prevention
- Database-level constraints for hard limits
- Rate limiting at API gateway level
- Monitoring for unusual usage patterns
- Automated alerts for potential abuse

## Monitoring and Alerts

### 1. Business Metrics
- Monthly Recurring Revenue (MRR) by tier
- Customer tier distribution
- Upgrade/downgrade rates
- Token usage patterns
- Auto-refill frequency

### 2. Technical Metrics
- API error rates by tier
- Feature access denial rates
- Token limit breach frequency
- Circuit breaker activation rates

### 3. Alert Thresholds
- User approaching tier limits (90% of any constraint)
- Unusual usage spikes (>3x normal)
- Payment failures
- Grandfathered user account issues

## Migration Strategy

### 1. Existing Users
- All current users automatically become "Founding Members" (grandfathered)
- Existing functionality remains unchanged
- Gradual rollout of new tier restrictions for new signups only

### 2. Feature Flag Rollout
```yaml
feature_flags:
  paywall_enabled: true
  grandfathering_active: true
  auto_refill_enabled: false  # Enable after Phase 2
  circuit_breakers_active: true
```

### 3. Testing Strategy
- Canary deployment to 10% of new users
- A/B testing of upgrade prompts
- Load testing of token metering system
- Grandfathering logic validation with test accounts

---

**Next Steps:**
1. Implement token tracking system
2. Build upgrade prompt components
3. Set up Stripe webhook handlers
4. Create usage monitoring dashboard
5. Deploy with feature flags for gradual rollout