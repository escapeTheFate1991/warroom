"use client";

import { useState, useEffect } from "react";
import { Check, Crown, Zap, Building, ArrowRight } from "lucide-react";
import { API, authFetch } from "@/lib/api";

interface Product {
  id: number;
  name: string;
  description: string | null;
  price: number;
  billing_interval: string;
  features: string[];
  tier_level: number;
  category: string;
  is_active: boolean;
}

export default function PricingPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTier, setSelectedTier] = useState<number | null>(null);

  const loadProducts = async () => {
    try {
      const response = await authFetch(`${API}/api/crm/products?category=ai-automation&is_active=true`);
      if (response.ok) {
        const data = await response.json();
        // Ensure data is an array before sorting and setting
        const productsArray = Array.isArray(data) ? data : (data.products || []);
        const sortedProducts = productsArray.sort((a: Product, b: Product) => a.tier_level - b.tier_level);
        setProducts(sortedProducts);
      } else {
        console.error("Failed to load products - API response not OK");
        setProducts([]); // Set empty array on failure
      }
    } catch (error) {
      console.error("Failed to load products:", error);
      setProducts([]); // Set empty array on error
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProducts();
  }, []);

  const formatPrice = (price: number, interval: string) => {
    if (interval === 'custom' || price === 0) {
      return 'Custom';
    }
    return `$${Math.round(price)}`;
  };

  const getTierIcon = (tierLevel: number) => {
    switch (tierLevel) {
      case 1: return <Crown className="h-6 w-6" />;
      case 2: return <Zap className="h-6 w-6" />;
      case 3: return <Building className="h-6 w-6" />;
      default: return <Crown className="h-6 w-6" />;
    }
  };

  const getTierColors = (tierLevel: number, isSelected: boolean) => {
    const baseClasses = "relative rounded-xl border-2 p-8 transition-all duration-300 hover:shadow-xl";
    
    if (isSelected) {
      switch (tierLevel) {
        case 1: return `${baseClasses} border-green-400 bg-green-50/10 shadow-lg scale-105`;
        case 2: return `${baseClasses} border-purple-400 bg-purple-50/10 shadow-lg scale-105`;
        case 3: return `${baseClasses} border-yellow-400 bg-yellow-50/10 shadow-lg scale-105`;
        default: return `${baseClasses} border-warroom-accent bg-warroom-accent/5 shadow-lg scale-105`;
      }
    }

    switch (tierLevel) {
      case 1: return `${baseClasses} border-warroom-border bg-warroom-surface hover:border-green-400/50`;
      case 2: return `${baseClasses} border-warroom-border bg-warroom-surface hover:border-purple-400/50`;
      case 3: return `${baseClasses} border-warroom-border bg-warroom-surface hover:border-yellow-400/50`;
      default: return `${baseClasses} border-warroom-border bg-warroom-surface hover:border-warroom-accent/50`;
    }
  };

  const getButtonColors = (tierLevel: number) => {
    switch (tierLevel) {
      case 1: return "bg-green-500 hover:bg-green-600 text-white";
      case 2: return "bg-purple-500 hover:bg-purple-600 text-white";
      case 3: return "bg-yellow-500 hover:bg-yellow-600 text-black";
      default: return "bg-warroom-accent hover:bg-warroom-accent/80 text-white";
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-warroom-accent border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-warroom-bg">
      {/* Header */}
      <div className="px-8 py-12 text-center bg-gradient-to-br from-warroom-surface to-warroom-bg border-b border-warroom-border">
        <h1 className="text-4xl font-bold text-warroom-text mb-4">
          AI Automation Services
        </h1>
        <p className="text-lg text-warroom-muted max-w-2xl mx-auto">
          Scale your business with intelligent automation powered by OpenClaw agents. 
          Choose the plan that fits your needs.
        </p>
      </div>

      {/* Pricing Cards */}
      <div className="flex-1 px-8 py-12">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {Array.isArray(products) && products.map((product) => (
              <div
                key={product.id}
                className={getTierColors(product.tier_level, selectedTier === product.tier_level)}
                onClick={() => setSelectedTier(selectedTier === product.tier_level ? null : product.tier_level)}
                style={{ cursor: 'pointer' }}
              >
                {/* Popular Badge for Professional */}
                {product.tier_level === 2 && (
                  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                    <span className="bg-purple-500 text-white px-4 py-1 rounded-full text-sm font-medium">
                      Most Popular
                    </span>
                  </div>
                )}

                {/* Founding Member Badge for Starter */}
                {product.tier_level === 1 && (
                  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                    <span className="bg-green-500 text-white px-4 py-1 rounded-full text-sm font-medium flex items-center gap-1">
                      <Crown className="h-3 w-3" />
                      Founding Member
                    </span>
                  </div>
                )}

                <div className="flex items-center gap-3 mb-4">
                  <div className={`p-2 rounded-lg ${
                    product.tier_level === 1 ? 'bg-green-500/20 text-green-400' :
                    product.tier_level === 2 ? 'bg-purple-500/20 text-purple-400' :
                    'bg-yellow-500/20 text-yellow-400'
                  }`}>
                    {getTierIcon(product.tier_level)}
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold text-warroom-text">
                      {product.name.replace(' (Foundation)', '')}
                    </h3>
                    <p className="text-sm text-warroom-muted">Tier {product.tier_level}</p>
                  </div>
                </div>

                <div className="mb-6">
                  <div className="flex items-baseline gap-1">
                    <span className="text-3xl font-bold text-warroom-text">
                      {formatPrice(product.price, product.billing_interval)}
                    </span>
                    {product.billing_interval !== 'custom' && (
                      <span className="text-warroom-muted">
                        /{product.billing_interval === 'monthly' ? 'month' : product.billing_interval}
                      </span>
                    )}
                  </div>
                  {product.description && (
                    <p className="text-sm text-warroom-muted mt-2">
                      {product.description}
                    </p>
                  )}
                </div>

                {/* Features */}
                <div className="space-y-3 mb-8">
                  {Array.isArray(product.features) && product.features.map((feature, index) => (
                    <div key={index} className="flex items-start gap-3">
                      <Check className="h-4 w-4 text-green-400 mt-0.5 flex-shrink-0" />
                      <span className="text-sm text-warroom-text">{feature}</span>
                    </div>
                  ))}
                </div>

                {/* CTA Button */}
                <button
                  className={`w-full py-3 px-4 rounded-lg font-medium transition-all duration-200 flex items-center justify-center gap-2 ${getButtonColors(product.tier_level)}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    // Handle signup/contact logic here
                    console.log(`Selected ${product.name}`);
                  }}
                >
                  {product.tier_level === 3 ? 'Contact Sales' : 'Get Started'}
                  <ArrowRight className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>

          {/* Additional Info */}
          <div className="mt-16 text-center">
            <div className="bg-warroom-surface border border-warroom-border rounded-lg p-8">
              <h3 className="text-xl font-semibold text-warroom-text mb-4">
                Why Choose ALEC AI Automation?
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-sm text-warroom-muted">
                <div>
                  <div className="text-warroom-accent font-semibold mb-2">🤖 OpenClaw Powered</div>
                  <p>Built on the cutting-edge OpenClaw agent framework for maximum flexibility and performance.</p>
                </div>
                <div>
                  <div className="text-warroom-accent font-semibold mb-2">🔄 24/7 Monitoring</div>
                  <p>Your agents work around the clock with intelligent heartbeat monitoring and auto-recovery.</p>
                </div>
                <div>
                  <div className="text-warroom-accent font-semibold mb-2">📈 Scalable Solutions</div>
                  <p>From single-agent setups to enterprise-scale orchestration — we grow with your business.</p>
                </div>
              </div>
            </div>
          </div>

          {/* FAQ Section */}
          <div className="mt-12">
            <h3 className="text-2xl font-semibold text-warroom-text text-center mb-8">
              Frequently Asked Questions
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-warroom-surface border border-warroom-border rounded-lg p-6">
                <h4 className="font-semibold text-warroom-text mb-2">What is an OpenClaw Agent?</h4>
                <p className="text-sm text-warroom-muted">
                  An OpenClaw agent is an autonomous AI assistant that can perform complex tasks, 
                  integrate with your existing tools, and make intelligent decisions on your behalf.
                </p>
              </div>
              <div className="bg-warroom-surface border border-warroom-border rounded-lg p-6">
                <h4 className="font-semibold text-warroom-text mb-2">What are Standard Tokens?</h4>
                <p className="text-sm text-warroom-muted">
                  Standard tokens represent the computational resources used by your agents. 
                  Different AI models consume tokens at different rates based on complexity.
                </p>
              </div>
              <div className="bg-warroom-surface border border-warroom-border rounded-lg p-6">
                <h4 className="font-semibold text-warroom-text mb-2">Can I upgrade or downgrade?</h4>
                <p className="text-sm text-warroom-muted">
                  Yes! You can change your plan at any time. Founding members keep their special pricing 
                  even when upgrading to higher tiers.
                </p>
              </div>
              <div className="bg-warroom-surface border border-warroom-border rounded-lg p-6">
                <h4 className="font-semibold text-warroom-text mb-2">What channels are supported?</h4>
                <p className="text-sm text-warroom-muted">
                  We support WhatsApp, Telegram, Discord, Slack, and more. Enterprise plans include 
                  API access for custom integrations.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}