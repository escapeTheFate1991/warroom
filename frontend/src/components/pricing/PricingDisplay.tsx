"use client";

import { useState, useEffect } from "react";
import { Crown, Check, Zap, Users, Headphones, MessageSquare, Bot, Clock, Shield, Star } from "lucide-react";
import { API, authFetch } from "@/lib/api";

interface PricingTier {
  id: number;
  name: string;
  description: string;
  price: number;
  billing_interval: string;
  features: string[];
  stripe_price_id: string | null;
  is_active: boolean;
  tier_level: number;
  category: string;
  badge?: string;
}

export default function PricingDisplay() {
  const [tiers, setTiers] = useState<PricingTier[]>([]);
  const [loading, setLoading] = useState(true);

  const loadPricingTiers = async () => {
    setLoading(true);
    try {
      const response = await authFetch(`${API}/api/crm/products?category=ai-automation`);
      if (response.ok) {
        const data = await response.json();
        // Sort by tier level
        const sortedTiers = data
          .filter((tier: PricingTier) => tier.is_active)
          .sort((a: PricingTier, b: PricingTier) => a.tier_level - b.tier_level);
        setTiers(sortedTiers);
      }
    } catch (error) {
      console.error("Failed to load pricing tiers:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPricingTiers();
  }, []);

  const formatPrice = (price: number, billing_interval: string) => {
    if (billing_interval === 'custom') {
      return 'Custom';
    }
    return `$${price.toLocaleString()}/${billing_interval === 'monthly' ? 'mo' : billing_interval}`;
  };

  const getTierIcon = (tier_level: number) => {
    switch (tier_level) {
      case 1: return <Zap className="w-6 h-6 text-blue-500" />;
      case 2: return <Users className="w-6 h-6 text-purple-500" />;
      case 3: return <Crown className="w-6 h-6 text-yellow-500" />;
      default: return <Bot className="w-6 h-6 text-warroom-accent" />;
    }
  };

  const getTierBadge = (tier_level: number, features: string[]) => {
    if (tier_level === 1 && features.some(f => f.includes("First 100"))) {
      return (
        <div className="inline-flex items-center gap-1 px-2 py-1 bg-gradient-to-r from-yellow-500/20 to-orange-500/20 border border-yellow-500/30 rounded-full text-xs font-medium text-yellow-400">
          <Star className="w-3 h-3" />
          Founding Member
        </div>
      );
    }
    if (tier_level === 2) {
      return (
        <div className="inline-flex items-center gap-1 px-2 py-1 bg-purple-500/20 border border-purple-500/30 rounded-full text-xs font-medium text-purple-400">
          Most Popular
        </div>
      );
    }
    return null;
  };

  const getFeatureIcon = (feature: string) => {
    if (feature.includes("Agent")) return <Bot className="w-4 h-4" />;
    if (feature.includes("Token")) return <Zap className="w-4 h-4" />;
    if (feature.includes("Heartbeat")) return <Clock className="w-4 h-4" />;
    if (feature.includes("support")) return <Headphones className="w-4 h-4" />;
    if (feature.includes("messaging") || feature.includes("WhatsApp") || feature.includes("Discord")) return <MessageSquare className="w-4 h-4" />;
    if (feature.includes("API") || feature.includes("CRM")) return <Shield className="w-4 h-4" />;
    return <Check className="w-4 h-4" />;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-warroom-accent"></div>
      </div>
    );
  }

  return (
    <div className="w-full">
      {/* Header */}
      <div className="text-center mb-12">
        <h2 className="text-3xl font-bold text-warroom-text mb-4">
          AI Automation Services
        </h2>
        <p className="text-lg text-warroom-muted max-w-2xl mx-auto">
          Choose the perfect plan to supercharge your business with AI agents
        </p>
      </div>

      {/* Pricing Grid */}
      <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
        {tiers.map((tier) => (
          <div
            key={tier.id}
            className={`relative bg-warroom-surface border rounded-2xl p-6 ${
              tier.tier_level === 2 
                ? 'border-purple-500/50 shadow-lg shadow-purple-500/10' 
                : 'border-warroom-border'
            }`}
          >
            {/* Badge */}
            <div className="flex justify-between items-start mb-4">
              {getTierIcon(tier.tier_level)}
              {getTierBadge(tier.tier_level, tier.features)}
            </div>

            {/* Tier Name & Description */}
            <div className="mb-6">
              <h3 className="text-xl font-bold text-warroom-text mb-2">
                {tier.name.replace('AI Automation ', '')}
              </h3>
              <p className="text-sm text-warroom-muted">
                {tier.description}
              </p>
            </div>

            {/* Price */}
            <div className="mb-8">
              <div className="text-3xl font-bold text-warroom-text">
                {formatPrice(tier.price, tier.billing_interval)}
              </div>
              {tier.billing_interval === 'monthly' && (
                <p className="text-sm text-warroom-muted mt-1">
                  Billed monthly
                </p>
              )}
              {tier.billing_interval === 'custom' && (
                <p className="text-sm text-warroom-muted mt-1">
                  Contact us for pricing
                </p>
              )}
            </div>

            {/* Features */}
            <div className="space-y-3 mb-8">
              {tier.features.map((feature, index) => (
                <div key={index} className="flex items-start gap-3">
                  <div className="mt-0.5 text-warroom-accent">
                    {getFeatureIcon(feature)}
                  </div>
                  <span className="text-sm text-warroom-text">{feature}</span>
                </div>
              ))}
            </div>

            {/* CTA Button */}
            <button
              className={`w-full py-3 px-4 rounded-lg font-medium transition ${
                tier.tier_level === 2
                  ? 'bg-purple-600 hover:bg-purple-700 text-white'
                  : tier.tier_level === 3
                  ? 'bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600 text-white'
                  : 'bg-warroom-accent hover:bg-warroom-accent/80 text-white'
              }`}
            >
              {tier.billing_interval === 'custom' ? 'Contact Sales' : 'Get Started'}
            </button>

            {/* Enterprise Badge */}
            {tier.tier_level === 3 && (
              <div className="absolute -top-3 -right-3 bg-gradient-to-r from-yellow-500 to-orange-500 text-white px-3 py-1 rounded-full text-xs font-medium">
                Enterprise
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Footer Note */}
      <div className="text-center mt-12">
        <p className="text-sm text-warroom-muted">
          All plans include enterprise-grade security and 99.9% uptime SLA.{" "}
          <br />
          Need something custom? <span className="text-warroom-accent hover:underline cursor-pointer">Contact us</span> for enterprise solutions.
        </p>
      </div>
    </div>
  );
}