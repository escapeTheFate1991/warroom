"use client";

import { useState, useEffect } from "react";
import { TrendingUp, DollarSign, Target, Calendar, BarChart3, RefreshCw } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";

interface ForecastData {
  total_pipeline_value: number;
  weighted_value: number;
  total_deals: number;
  average_deal_size: number;
  conversion_rate: number;
  deals_by_stage: {
    stage_name: string;
    stage_probability: number;
    deal_count: number;
    total_value: number;
    weighted_value: number;
  }[];
  monthly_forecast: {
    month: string;
    expected_revenue: number;
    deal_count: number;
  }[];
  performance_metrics: {
    deals_won_this_month: number;
    deals_lost_this_month: number;
    revenue_this_month: number;
    deals_created_this_month: number;
  };
}

export default function ForecastPanel() {
  const [forecast, setForecast] = useState<ForecastData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedTimeframe, setSelectedTimeframe] = useState<"month" | "quarter" | "year">("quarter");

  useEffect(() => {
    loadForecast();
  }, [selectedTimeframe]);

  const loadForecast = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API}/api/crm/deals/forecast?timeframe=${selectedTimeframe}`);
      if (response.ok) {
        const data = await response.json();
        setForecast(data);
      }
    } catch (error) {
      console.error("Failed to load forecast:", error);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatPercent = (value: number) => {
    return `${(value * 100).toFixed(1)}%`;
  };

  const getStageColor = (probability: number) => {
    if (probability >= 80) return "bg-green-500";
    if (probability >= 60) return "bg-yellow-500";
    if (probability >= 40) return "bg-blue-500";
    if (probability >= 20) return "bg-blue-600";
    return "bg-gray-500";
  };

  const getStageTextColor = (probability: number) => {
    if (probability >= 80) return "text-green-400";
    if (probability >= 60) return "text-yellow-400";
    if (probability >= 40) return "text-blue-400";
    if (probability >= 20) return "text-blue-300";
    return "text-gray-400";
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw size={24} className="animate-spin text-warroom-muted" />
      </div>
    );
  }

  if (!forecast) {
    return (
      <div className="text-center py-20 text-warroom-muted">
        <BarChart3 size={48} className="mx-auto mb-4 opacity-20" />
        <p>Failed to load forecast data</p>
      </div>
    );
  }

  const maxStageValue = Math.max(...forecast.deals_by_stage.map(s => s.total_value));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-warroom-text flex items-center gap-2">
          <TrendingUp size={20} />
          Sales Forecast
        </h3>
        
        <div className="flex items-center gap-3">
          <select
            value={selectedTimeframe}
            onChange={(e) => setSelectedTimeframe(e.target.value as any)}
            className="bg-warroom-surface border border-warroom-border rounded-lg px-3 py-1.5 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
            style={{ colorScheme: "dark" }}
          >
            <option value="month">This Month</option>
            <option value="quarter">This Quarter</option>
            <option value="year">This Year</option>
          </select>
          
          <button
            onClick={loadForecast}
            className="text-warroom-muted hover:text-warroom-text transition p-2"
            title="Refresh"
          >
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      {/* Key Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-warroom-surface border border-warroom-border rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-warroom-muted uppercase">Total Pipeline</p>
              <p className="text-2xl font-bold text-warroom-text">
                {formatCurrency(forecast.total_pipeline_value)}
              </p>
            </div>
            <DollarSign size={24} className="text-blue-400" />
          </div>
          <p className="text-xs text-warroom-muted mt-1">
            {forecast.total_deals} active deals
          </p>
        </div>

        <div className="bg-warroom-surface border border-warroom-border rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-warroom-muted uppercase">Weighted Value</p>
              <p className="text-2xl font-bold text-green-400">
                {formatCurrency(forecast.weighted_value)}
              </p>
            </div>
            <Target size={24} className="text-green-400" />
          </div>
          <p className="text-xs text-warroom-muted mt-1">
            Probability-adjusted forecast
          </p>
        </div>

        <div className="bg-warroom-surface border border-warroom-border rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-warroom-muted uppercase">Avg Deal Size</p>
              <p className="text-2xl font-bold text-warroom-text">
                {formatCurrency(forecast.average_deal_size)}
              </p>
            </div>
            <BarChart3 size={24} className="text-orange-400" />
          </div>
          <p className="text-xs text-warroom-muted mt-1">
            Average value per deal
          </p>
        </div>

        <div className="bg-warroom-surface border border-warroom-border rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-warroom-muted uppercase">Conversion Rate</p>
              <p className="text-2xl font-bold text-yellow-400">
                {formatPercent(forecast.conversion_rate)}
              </p>
            </div>
            <TrendingUp size={24} className="text-yellow-400" />
          </div>
          <p className="text-xs text-warroom-muted mt-1">
            Historical win rate
          </p>
        </div>
      </div>

      {/* Performance This Month */}
      <div className="bg-warroom-surface border border-warroom-border rounded-lg p-6">
        <h4 className="text-sm font-semibold text-warroom-text mb-4">
          Performance This Month
        </h4>
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-green-400 mb-1">
              {forecast.performance_metrics.deals_won_this_month}
            </div>
            <div className="text-xs text-warroom-muted">Deals Won</div>
          </div>
          
          <div className="text-center">
            <div className="text-2xl font-bold text-red-400 mb-1">
              {forecast.performance_metrics.deals_lost_this_month}
            </div>
            <div className="text-xs text-warroom-muted">Deals Lost</div>
          </div>
          
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-400 mb-1">
              {forecast.performance_metrics.deals_created_this_month}
            </div>
            <div className="text-xs text-warroom-muted">New Deals</div>
          </div>
          
          <div className="text-center">
            <div className="text-2xl font-bold text-green-400 mb-1">
              {formatCurrency(forecast.performance_metrics.revenue_this_month)}
            </div>
            <div className="text-xs text-warroom-muted">Revenue Won</div>
          </div>
        </div>
      </div>

      {/* Pipeline by Stage */}
      <div className="bg-warroom-surface border border-warroom-border rounded-lg p-6">
        <h4 className="text-sm font-semibold text-warroom-text mb-6">
          Pipeline by Stage
        </h4>
        
        <div className="space-y-4">
          {forecast.deals_by_stage.map((stage) => {
            const percentage = maxStageValue > 0 ? (stage.total_value / maxStageValue) * 100 : 0;
            
            return (
              <div key={stage.stage_name} className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-3 h-3 rounded-full ${getStageColor(stage.stage_probability)}`} />
                    <span className="text-sm font-medium text-warroom-text">
                      {stage.stage_name}
                    </span>
                    <span className="text-xs px-2 py-1 bg-warroom-bg rounded-full text-warroom-muted">
                      {stage.stage_probability}%
                    </span>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-medium text-warroom-text">
                      {formatCurrency(stage.total_value)}
                    </div>
                    <div className="text-xs text-warroom-muted">
                      {stage.deal_count} deals
                    </div>
                  </div>
                </div>
                
                <div className="relative">
                  <div className="w-full h-2 bg-warroom-bg rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-500 ${getStageColor(stage.stage_probability)}`}
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                  
                  {/* Weighted value overlay */}
                  <div className="flex justify-between items-center mt-1">
                    <div className={`text-xs ${getStageTextColor(stage.stage_probability)}`}>
                      Weighted: {formatCurrency(stage.weighted_value)}
                    </div>
                    <div className="text-xs text-warroom-muted">
                      {formatCurrency(stage.total_value)}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Monthly Forecast */}
      {forecast.monthly_forecast.length > 0 && (
        <div className="bg-warroom-surface border border-warroom-border rounded-lg p-6">
          <h4 className="text-sm font-semibold text-warroom-text mb-6 flex items-center gap-2">
            <Calendar size={16} />
            Expected Revenue by Month
          </h4>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {forecast.monthly_forecast.slice(0, 3).map((month) => (
              <div key={month.month} className="text-center p-4 bg-warroom-bg rounded-lg border border-warroom-border">
                <div className="text-sm font-medium text-warroom-muted mb-2">
                  {new Date(month.month + "-01").toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
                </div>
                <div className="text-xl font-bold text-green-400 mb-1">
                  {formatCurrency(month.expected_revenue)}
                </div>
                <div className="text-xs text-warroom-muted">
                  {month.deal_count} deals expected
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}