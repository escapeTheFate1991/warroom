"use client";

import { useState, useEffect } from "react";
import {
  BarChart, TrendingUp, Star, Loader2, RefreshCw, Sparkles, Clock,
  ChevronDown, ChevronUp, Award, Target, Calendar
} from "lucide-react";
import { authFetch, API } from "@/lib/api";

/* ── Types ─────────────────────────────────────────────── */
interface ProjectCard {
  id: number;
  title: string;
  format_slug: string;
  status: string; // "queued" | "generating" | "complete" | "distributed"
  created_at: string;
  performance?: {
    engagement_score: number;
    competitor_avg: number;
    delta: number; // percentage
    tier: "outperform" | "match" | "underperform";
  };
  thumbnail_url?: string;
}

interface PerformanceDashboardData {
  format_leaderboard: Array<{
    format: string;
    avg_engagement: number;
    count: number;
    avg_delta: string;
  }>;
  hook_leaderboard: Array<{
    hook: string;
    engagement: number;
    format: string;
    delta: string;
  }>;
  time_heatmap: Record<string, Record<string, number>>;
  format_trends: Record<string, Array<{ week: string; avg: number }>>;
  total_posts: number;
  avg_engagement: number;
  best_format: string;
  best_time: string;
}

interface PerformanceDashboardProps {
  onSeedForBatch?: (projectId: number) => void;
}

/* ── Format Badge Colors (reused from FormatPicker) ─────── */
const formatColors: Record<string, { bg: string; text: string; border: string; color: string }> = {
  myth_buster: { bg: "bg-purple-500/20", text: "text-purple-400", border: "border-purple-500/30", color: "#a855f7" },
  expose: { bg: "bg-red-500/20", text: "text-red-400", border: "border-red-500/30", color: "#f87171" },
  transformation: { bg: "bg-emerald-500/20", text: "text-emerald-400", border: "border-emerald-500/30", color: "#34d399" },
  pov: { bg: "bg-blue-500/20", text: "text-blue-400", border: "border-blue-500/30", color: "#60a5fa" },
  speed_run: { bg: "bg-yellow-500/20", text: "text-yellow-400", border: "border-yellow-500/30", color: "#fbbf24" },
  challenge: { bg: "bg-orange-500/20", text: "text-orange-400", border: "border-orange-500/30", color: "#fb923c" },
  show_dont_tell: { bg: "bg-cyan-500/20", text: "text-cyan-400", border: "border-cyan-500/30", color: "#22d3ee" },
  direct_to_camera: { bg: "bg-pink-500/20", text: "text-pink-400", border: "border-pink-500/30", color: "#f472b6" },
};

const formatNames: Record<string, string> = {
  myth_buster: "Myth Buster",
  expose: "Exposé",
  transformation: "Transformation",
  pov: "POV",
  speed_run: "Speed Run",
  challenge: "Challenge",
  show_dont_tell: "Show Don't Tell",
  direct_to_camera: "Direct to Camera",
};

const dayNames = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const hourLabels = Array.from({ length: 24 }, (_, i) => `${i}:00`);

export default function PerformanceDashboard({ onSeedForBatch }: PerformanceDashboardProps) {
  const [activeTab, setActiveTab] = useState<"projects" | "insights">("projects");
  const [projects, setProjects] = useState<ProjectCard[]>([]);
  const [dashboardData, setDashboardData] = useState<PerformanceDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedHook, setExpandedHook] = useState<number | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      // Fetch projects
      const projectsRes = await authFetch(`${API}/api/ai-studio/ugc/projects`);
      if (projectsRes.ok) {
        const projectsData = await projectsRes.json();
        setProjects(projectsData.projects || []);
      }

      // Fetch dashboard data
      const dashboardRes = await authFetch(`${API}/api/content-intel/performance-dashboard`);
      if (dashboardRes.ok) {
        const dashData = await dashboardRes.json();
        setDashboardData(dashData);
      }
    } catch (error) {
      console.error("Error fetching performance data:", error);
    }
    setLoading(false);
  };

  const handleSeedProject = (projectId: number) => {
    onSeedForBatch?.(projectId);
    // Could also show toast notification here
  };

  const getPerformanceBadge = (performance?: ProjectCard['performance']) => {
    if (!performance) return null;

    const { tier, delta } = performance;
    const sign = delta > 0 ? "+" : "";
    
    if (tier === "outperform") {
      return (
        <div className="flex items-center gap-1 px-2 py-1 bg-green-500/20 border border-green-500/30 text-green-400 text-xs rounded-full">
          🟢 {sign}{delta}% vs competitor avg
        </div>
      );
    } else if (tier === "underperform") {
      return (
        <div className="flex items-center gap-1 px-2 py-1 bg-red-500/20 border border-red-500/30 text-red-400 text-xs rounded-full">
          🔴 {sign}{delta}% below avg
        </div>
      );
    } else {
      return (
        <div className="flex items-center gap-1 px-2 py-1 bg-yellow-500/20 border border-yellow-500/30 text-yellow-400 text-xs rounded-full">
          🟡 On par with avg
        </div>
      );
    }
  };

  const getFormatBadge = (formatSlug: string) => {
    const colors = formatColors[formatSlug] || { bg: "bg-warroom-border", text: "text-warroom-muted", border: "border-warroom-border" };
    const name = formatNames[formatSlug] || formatSlug;
    
    return (
      <span className={`px-2 py-0.5 text-xs rounded-full border ${colors.bg} ${colors.text} ${colors.border}`}>
        {name}
      </span>
    );
  };

  const renderProjectsTab = () => {
    if (loading) {
      return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1,2,3,4].map(i => (
            <div key={i} className="bg-warroom-surface border border-warroom-border rounded-lg p-4 animate-pulse">
              <div className="h-6 bg-warroom-border rounded w-3/4 mb-3" />
              <div className="space-y-2">
                <div className="h-4 bg-warroom-border rounded w-full" />
                <div className="h-4 bg-warroom-border rounded w-2/3" />
              </div>
            </div>
          ))}
        </div>
      );
    }

    if (projects.length === 0) {
      return (
        <div className="flex flex-col items-center py-16 text-warroom-muted gap-3">
          <BarChart size={36} className="text-warroom-accent/30" />
          <p className="text-sm">No projects yet</p>
          <p className="text-xs text-center max-w-md">
            📊 No performance data yet. Generate and distribute your first video to start tracking results.
          </p>
        </div>
      );
    }

    return (
      <div className="space-y-3">
        {projects.map((project) => (
          <div key={project.id} className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3 flex-1">
                {/* Thumbnail or placeholder */}
                <div className="w-16 h-16 bg-warroom-bg border border-warroom-border rounded-lg flex items-center justify-center flex-shrink-0">
                  {project.thumbnail_url ? (
                    <img src={project.thumbnail_url} alt={project.title} className="w-full h-full object-cover rounded-lg" />
                  ) : (
                    <BarChart size={24} className="text-warroom-muted" />
                  )}
                </div>

                {/* Project info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <h3 className="text-sm font-semibold text-warroom-text truncate">{project.title}</h3>
                    {getFormatBadge(project.format_slug)}
                  </div>
                  
                  <div className="flex items-center gap-2 text-xs text-warroom-muted mb-2">
                    <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                      project.status === "complete" ? "bg-emerald-500/20 text-emerald-400" :
                      project.status === "generating" ? "bg-yellow-500/20 text-yellow-400" :
                      "bg-warroom-bg text-warroom-muted"
                    }`}>
                      {project.status}
                    </span>
                    <span className="text-warroom-border">·</span>
                    <span>{new Date(project.created_at).toLocaleDateString()}</span>
                  </div>

                  {/* Performance badge */}
                  {getPerformanceBadge(project.performance)}
                </div>
              </div>

              {/* Seed button for outperforming videos */}
              {project.performance?.tier === "outperform" && (
                <button
                  onClick={() => handleSeedProject(project.id)}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-warroom-accent/20 text-warroom-accent text-xs rounded-lg hover:bg-warroom-accent/30 transition flex-shrink-0"
                >
                  <Sparkles size={12} />
                  Seed for Next Batch
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    );
  };

  const renderInsightsTab = () => {
    if (loading || !dashboardData) {
      return (
        <div className="space-y-6">
          <div className="bg-warroom-surface border border-warroom-border rounded-lg p-4 animate-pulse">
            <div className="h-6 bg-warroom-border rounded w-1/4 mb-4" />
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[1,2,3,4].map(i => (
                <div key={i} className="bg-warroom-border h-16 rounded" />
              ))}
            </div>
          </div>
          <div className="bg-warroom-surface border border-warroom-border rounded-lg p-4 animate-pulse">
            <div className="h-6 bg-warroom-border rounded w-1/3 mb-4" />
            <div className="h-32 bg-warroom-border rounded" />
          </div>
          <div className="text-sm text-warroom-muted text-center">Loading performance insights...</div>
        </div>
      );
    }

    if (dashboardData.total_posts === 0) {
      return (
        <div className="flex flex-col items-center py-16 text-warroom-muted gap-3">
          <TrendingUp size={36} className="text-warroom-accent/30" />
          <p className="text-sm">No performance data yet</p>
          <p className="text-xs text-center max-w-md">
            📊 Generate and distribute your first video to start seeing insights.
          </p>
        </div>
      );
    }

    const maxEngagement = Math.max(...dashboardData.format_leaderboard.map(f => f.avg_engagement));
    const maxHeatmapValue = Math.max(
      ...Object.values(dashboardData.time_heatmap).flatMap(hours => Object.values(hours))
    );

    return (
      <div className="grid grid-cols-2 gap-4">
        {/* Format Leaderboard */}
        <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
          <h3 className="text-sm font-semibold text-warroom-text mb-3 flex items-center gap-2">
            <Award size={16} className="text-warroom-accent" />
            Format Leaderboard
          </h3>
          <div className="space-y-3">
            {dashboardData.format_leaderboard
              .sort((a, b) => b.avg_engagement - a.avg_engagement)
              .map((format, index) => {
                const colors = formatColors[format.format] || { bg: "bg-warroom-border", text: "text-warroom-muted", border: "border-warroom-border", color: "#94a3b8" };
                const name = formatNames[format.format] || format.format;
                
                return (
                  <div key={format.format} className="flex items-center gap-2">
                    <span className="w-6 text-xs text-warroom-muted">#{index + 1}</span>
                    <span className="w-20 text-xs truncate">{name}:</span>
                    <div className="flex-1 bg-warroom-border rounded-full h-3">
                      <div 
                        className="h-full rounded-full"
                        style={{ 
                          width: `${(format.avg_engagement / maxEngagement) * 100}%`,
                          backgroundColor: colors.color,
                        }}
                      />
                    </div>
                    <span className="text-xs text-warroom-muted">{format.avg_engagement.toLocaleString()}</span>
                    <span className="text-xs text-green-400">({format.avg_delta})</span>
                  </div>
                );
              })}
          </div>
        </div>

        {/* Hook Leaderboard */}
        <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
          <h3 className="text-sm font-semibold text-warroom-text mb-3 flex items-center gap-2">
            <Target size={16} className="text-warroom-accent" />
            Hook Leaderboard
          </h3>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {dashboardData.hook_leaderboard.slice(0, 10).map((hook, index) => (
              <div key={index} className="space-y-1">
                <div 
                  className="flex items-center gap-2 p-2 rounded-lg hover:bg-warroom-bg cursor-pointer transition"
                  onClick={() => setExpandedHook(expandedHook === index ? null : index)}
                >
                  <span className="w-6 text-xs text-warroom-muted">#{index + 1}</span>
                  <span className="flex-1 text-xs text-warroom-text truncate">
                    {hook.hook.length > 60 ? `${hook.hook.substring(0, 60)}...` : hook.hook}
                  </span>
                  <span className="text-xs text-warroom-muted">{hook.engagement.toLocaleString()}</span>
                  <span className="text-xs text-green-400">{hook.delta}</span>
                  {expandedHook === index ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                </div>
                
                {expandedHook === index && (
                  <div className="ml-8 p-2 bg-warroom-bg rounded-lg text-xs">
                    <p className="text-warroom-text mb-1">{hook.hook}</p>
                    <p className="text-warroom-muted">Format: {formatNames[hook.format] || hook.format}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Time Heatmap */}
        <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
          <h3 className="text-sm font-semibold text-warroom-text mb-3 flex items-center gap-2">
            <Clock size={16} className="text-warroom-accent" />
            Time Heatmap
          </h3>
          <div className="space-y-2">
            {/* Day labels */}
            <div className="grid grid-cols-8 gap-1 text-xs">
              <div></div>
              {dayNames.map(day => (
                <div key={day} className="text-center text-warroom-muted truncate">
                  {day.slice(0, 3)}
                </div>
              ))}
            </div>
            
            {/* Heatmap grid */}
            <div className="space-y-1">
              {Array.from({ length: 6 }, (_, rowIndex) => (
                <div key={rowIndex} className="grid grid-cols-8 gap-1 text-xs">
                  <div className="text-warroom-muted text-right">
                    {rowIndex * 4}:00
                  </div>
                  {dayNames.map((day, dayIndex) => {
                    const hour = rowIndex * 4;
                    const value = dashboardData.time_heatmap[day.toLowerCase()]?.[hour] || 0;
                    const intensity = value / maxHeatmapValue;
                    const isBestTime = `${day} ${hour}:00` === dashboardData.best_time;
                    
                    return (
                      <div
                        key={`${day}-${hour}`}
                        className={`h-4 rounded-sm border relative ${isBestTime ? 'border-yellow-400' : 'border-warroom-border/50'}`}
                        style={{
                          backgroundColor: `rgba(124, 58, 237, ${intensity})`,
                        }}
                        title={`${day} ${hour}:00 - ${value.toLocaleString()} engagement`}
                      >
                        {isBestTime && (
                          <Star size={8} className="absolute inset-0 m-auto text-yellow-400" />
                        )}
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Format Trends */}
        <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
          <h3 className="text-sm font-semibold text-warroom-text mb-3 flex items-center gap-2">
            <TrendingUp size={16} className="text-warroom-accent" />
            Format Trends
          </h3>
          <div className="h-32">
            <svg width="100%" height="100%" viewBox="0 0 300 120" className="overflow-visible">
              {Object.entries(dashboardData.format_trends).map(([format, data], formatIndex) => {
                const colors = formatColors[format] || { color: "#94a3b8" };
                const color = colors.color;
                
                if (data.length < 2) return null;
                
                const maxValue = Math.max(...Object.values(dashboardData.format_trends).flat().map(d => d.avg));
                const points = data.map((point, index) => {
                  const x = (index / (data.length - 1)) * 280 + 10;
                  const y = 110 - ((point.avg / maxValue) * 100);
                  return `${x},${y}`;
                }).join(' ');
                
                return (
                  <g key={format}>
                    <polyline
                      fill="none"
                      stroke={color}
                      strokeWidth="2"
                      points={points}
                    />
                    {data.map((point, index) => {
                      const x = (index / (data.length - 1)) * 280 + 10;
                      const y = 110 - ((point.avg / maxValue) * 100);
                      return (
                        <circle
                          key={index}
                          cx={x}
                          cy={y}
                          r="2"
                          fill={color}
                        />
                      );
                    })}
                  </g>
                );
              })}
            </svg>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="p-5 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-warroom-text">Performance Dashboard</h2>
          <p className="text-xs text-warroom-muted mt-0.5">
            Track your content performance vs competitor benchmarks
          </p>
        </div>
        <button
          onClick={fetchData}
          className="p-1.5 rounded-lg hover:bg-warroom-border/50 text-warroom-muted"
        >
          <RefreshCw size={14} />
        </button>
      </div>

      {/* Tab Toggle */}
      <div className="flex bg-warroom-bg border border-warroom-border rounded-lg p-1">
        <button
          onClick={() => setActiveTab("projects")}
          className={`flex-1 px-3 py-2 text-xs font-medium rounded-md transition ${
            activeTab === "projects"
              ? "bg-warroom-surface text-warroom-text"
              : "text-warroom-muted hover:text-warroom-text"
          }`}
        >
          Projects
        </button>
        <button
          onClick={() => setActiveTab("insights")}
          className={`flex-1 px-3 py-2 text-xs font-medium rounded-md transition ${
            activeTab === "insights"
              ? "bg-warroom-surface text-warroom-text"
              : "text-warroom-muted hover:text-warroom-text"
          }`}
        >
          Insights
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === "projects" ? renderProjectsTab() : renderInsightsTab()}
    </div>
  );
}