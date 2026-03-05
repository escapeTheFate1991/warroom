"use client";

import { useState, useEffect, useRef } from "react";
import { ChevronDown, Cpu, DollarSign, Clock, Activity } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";

interface UsageTier {
  label: string;
  percent: number;
  resetsIn: string;
  tokens: number;
  cost: number;
}

interface UsageDetails {
  tokens: number;
  cost: number;
  sessions: number;
}

interface UsageData {
  model: string;
  tiers: UsageTier[];
  details: {
    today: UsageDetails;
    week: UsageDetails;
    month: UsageDetails;
  };
}

export default function UsageWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [models, setModels] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchUsage = async () => {
    try {
      const response = await fetch(`${API}/api/usage`);
      if (!response.ok) throw new Error('Failed to fetch usage');
      const data = await response.json();
      setUsage(data);
      setError(null);
    } catch (err) {
      setError('Failed to load usage data');
      console.error('Usage fetch error:', err);
    }
  };

  const fetchModels = async () => {
    try {
      const response = await fetch(`${API}/api/usage/models`);
      if (!response.ok) throw new Error('Failed to fetch models');
      const data = await response.json();
      setModels(data);
    } catch (err) {
      console.error('Models fetch error:', err);
    }
  };

  const setModel = async (model: string) => {
    try {
      const response = await fetch(`${API}/api/usage/model`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model })
      });
      if (!response.ok) throw new Error('Failed to set model');
      await fetchUsage(); // Refresh usage data
    } catch (err) {
      console.error('Set model error:', err);
    }
  };

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchUsage(), fetchModels()]);
      setLoading(false);
    };

    loadData();

    // Auto-refresh every 30 seconds
    intervalRef.current = setInterval(fetchUsage, 30000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  const getProgressColor = (percent: number): string => {
    if (percent >= 80) return "text-red-400";
    if (percent >= 60) return "text-amber-400";
    return "text-green-400";
  };

  const getProgressDot = (percent: number): string => {
    if (percent >= 80) return "bg-red-400";
    if (percent >= 60) return "bg-amber-400";
    return "bg-green-400";
  };

  const formatCost = (cost: number): string => {
    return `$${cost.toFixed(3)}`;
  };

  const formatTokens = (tokens: number): string => {
    if (tokens >= 1000000) {
      return `${(tokens / 1000000).toFixed(1)}M`;
    }
    if (tokens >= 1000) {
      return `${(tokens / 1000).toFixed(1)}k`;
    }
    return tokens.toString();
  };

  if (loading) {
    return (
      <div className="bg-warroom-surface border border-warroom-border rounded-lg p-3 animate-pulse">
        <div className="h-6 bg-warroom-border rounded w-24"></div>
      </div>
    );
  }

  if (error || !usage) {
    return (
      <div className="bg-warroom-surface border border-warroom-border rounded-lg p-3">
        <div className="text-warroom-muted text-sm">Usage unavailable</div>
      </div>
    );
  }

  const sessionTier = usage.tiers[0]; // Current session (5h)
  const weeklyTier = usage.tiers[1]; // Weekly

  return (
    <div className="relative">
      {/* Compact pill button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 bg-warroom-surface border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text hover:bg-opacity-80 transition-colors"
      >
        <Cpu className="w-4 h-4 text-warroom-muted" />
        <span className="font-medium">{usage.model}</span>
        <span className="text-warroom-muted">•</span>
        <span className="font-medium">{sessionTier.percent}%</span>
        <div className={`w-2 h-2 rounded-full ${getProgressDot(sessionTier.percent)}`}></div>
        <ChevronDown className={`w-4 h-4 text-warroom-muted transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown panel */}
      {isOpen && (
        <div className="absolute top-full right-0 mt-2 w-80 bg-warroom-surface border border-warroom-border rounded-lg shadow-lg z-50">
          <div className="p-4 space-y-4">
            {/* Active model and selector */}
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm font-medium text-warroom-text">
                <Cpu className="w-4 h-4" />
                Active Model
              </div>
              <select
                value={usage.model}
                onChange={(e) => setModel(e.target.value)}
                className="w-full bg-warroom-surface border border-warroom-border rounded px-3 py-2 text-sm text-warroom-text focus:outline-none focus:ring-2 focus:ring-warroom-accent"
              >
                {models.map(model => (
                  <option key={model} value={model}>
                    {model.replace('anthropic/', '')}
                  </option>
                ))}
              </select>
            </div>

            {/* Progress bars */}
            <div className="space-y-3">
              {/* Session progress */}
              <div className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-warroom-text font-medium">{sessionTier.label}</span>
                  <span className={`font-medium ${getProgressColor(sessionTier.percent)}`}>
                    {sessionTier.percent}%
                  </span>
                </div>
                <div className="w-full bg-warroom-border rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all duration-300 ${
                      sessionTier.percent >= 80 ? 'bg-red-400' :
                      sessionTier.percent >= 60 ? 'bg-amber-400' : 'bg-green-400'
                    }`}
                    style={{ width: `${Math.min(sessionTier.percent, 100)}%` }}
                  ></div>
                </div>
                <div className="flex items-center justify-between text-xs text-warroom-muted">
                  <span>{formatTokens(sessionTier.tokens)} tokens</span>
                  <span>{formatCost(sessionTier.cost)}</span>
                  <span>Resets in {sessionTier.resetsIn}</span>
                </div>
              </div>

              {/* Weekly progress */}
              <div className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-warroom-text font-medium">{weeklyTier.label}</span>
                  <span className={`font-medium ${getProgressColor(weeklyTier.percent)}`}>
                    {weeklyTier.percent}%
                  </span>
                </div>
                <div className="w-full bg-warroom-border rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all duration-300 ${
                      weeklyTier.percent >= 80 ? 'bg-red-400' :
                      weeklyTier.percent >= 60 ? 'bg-amber-400' : 'bg-green-400'
                    }`}
                    style={{ width: `${Math.min(weeklyTier.percent, 100)}%` }}
                  ></div>
                </div>
                <div className="flex items-center justify-between text-xs text-warroom-muted">
                  <span>{formatTokens(weeklyTier.tokens)} tokens</span>
                  <span>{formatCost(weeklyTier.cost)}</span>
                  <span>Resets in {weeklyTier.resetsIn}</span>
                </div>
              </div>
            </div>

            {/* Cost summary */}
            <div className="border-t border-warroom-border pt-3">
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center">
                  <div className="flex items-center justify-center gap-1 text-xs text-warroom-muted mb-1">
                    <Clock className="w-3 h-3" />
                    Today
                  </div>
                  <div className="text-sm font-medium text-warroom-text">
                    {formatCost(usage.details.today.cost)}
                  </div>
                  <div className="text-xs text-warroom-muted">
                    {usage.details.today.sessions} sessions
                  </div>
                </div>
                <div className="text-center">
                  <div className="flex items-center justify-center gap-1 text-xs text-warroom-muted mb-1">
                    <Activity className="w-3 h-3" />
                    Week
                  </div>
                  <div className="text-sm font-medium text-warroom-text">
                    {formatCost(usage.details.week.cost)}
                  </div>
                  <div className="text-xs text-warroom-muted">
                    {usage.details.week.sessions} sessions
                  </div>
                </div>
                <div className="text-center">
                  <div className="flex items-center justify-center gap-1 text-xs text-warroom-muted mb-1">
                    <DollarSign className="w-3 h-3" />
                    Month
                  </div>
                  <div className="text-sm font-medium text-warroom-text">
                    {formatCost(usage.details.month.cost)}
                  </div>
                  <div className="text-xs text-warroom-muted">
                    {usage.details.month.sessions} sessions
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}