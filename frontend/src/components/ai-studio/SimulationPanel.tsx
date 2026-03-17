"use client";

import { useState, useEffect } from "react";
import { X, Clock, Heart, Share, Bookmark, MessageCircle, Sparkles, Wand2 } from "lucide-react";

interface OptimizationRecommendation {
  type: "hook" | "body" | "cta";
  originalText: string;
  suggestedText: string;
  reason: string;
  predictedImpact: string;
}

interface SimulationPanelProps {
  script: { hook: string; body: string; cta: string };
  formatSlug: string;
  onOptimize: (recommendation: OptimizationRecommendation) => void;
  onClose: () => void;
}

interface SimulationResult {
  engagementScore: number;
  metrics: {
    likesPropensity: number;
    sharesPropensity: number;
    savesPropensity: number;
    commentsPropensity: number;
  };
  retentionTimeline: Array<{
    timestamp: string;
    percentage: number;
    reason: string;
  }>;
  predictedComments: Array<{
    personaName: string;
    personaInitials: string;
    comment: string;
    sentiment: "positive" | "negative" | "neutral" | "skeptical";
  }>;
  sceneFriction: Array<{
    scene: string;
    frictionLevel: "low" | "medium" | "high";
    description: string;
  }>;
  audioRecommendation: {
    suggestion: string;
    impact: string;
  };
  optimization?: OptimizationRecommendation;
}

export default function SimulationPanel({
  script,
  formatSlug,
  onOptimize,
  onClose
}: SimulationPanelProps) {
  const [simulationResult, setSimulationResult] = useState<SimulationResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [simulationTimestamp] = useState(new Date().toISOString());

  useEffect(() => {
    // Simulate API call to get simulation results
    const fetchSimulationResults = async () => {
      setLoading(true);
      
      // For now, generate mock data based on the script content
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      const mockResult: SimulationResult = {
        engagementScore: Math.floor(Math.random() * 40) + 60, // 60-100
        metrics: {
          likesPropensity: Math.floor(Math.random() * 30) + 70,
          sharesPropensity: Math.floor(Math.random() * 25) + 65,
          savesPropensity: Math.floor(Math.random() * 35) + 60,
          commentsPropensity: Math.floor(Math.random() * 20) + 75,
        },
        retentionTimeline: [
          { timestamp: "0s", percentage: 100, reason: "Hook engagement" },
          { timestamp: "2s", percentage: 95, reason: "Strong opener retention" },
          { timestamp: "5s", percentage: 78, reason: "Content transition" },
          { timestamp: "15s", percentage: 52, reason: "Mid-content drop" },
          { timestamp: "25s", percentage: 45, reason: "CTA effectiveness" },
        ],
        predictedComments: [
          { personaName: "Sarah M", personaInitials: "SM", comment: "This is exactly what I needed!", sentiment: "positive" },
          { personaName: "Tech Skeptic", personaInitials: "TS", comment: "Not sure if this actually works...", sentiment: "skeptical" },
          { personaName: "Mike R", personaInitials: "MR", comment: "Link in bio pls", sentiment: "neutral" },
        ],
        sceneFriction: [
          { scene: "Hook", frictionLevel: "low", description: "Strong hook, matches format expectations" },
          { scene: "Main Content", frictionLevel: "medium", description: "Transition could be smoother" },
          { scene: "CTA", frictionLevel: "medium", description: "CTA is generic — customize for platform" },
        ],
        audioRecommendation: {
          suggestion: "Trending Fast-Paced",
          impact: "Triggered 'Save' behavior in 40% more agents"
        },
        optimization: {
          type: "hook",
          originalText: script.hook,
          suggestedText: "POV: You just discovered the secret everyone's talking about...",
          reason: "Higher engagement potential with POV format",
          predictedImpact: "+22% share rate"
        }
      };
      
      setSimulationResult(mockResult);
      setLoading(false);
    };

    fetchSimulationResults();
  }, [script]);

  const getScoreColor = (score: number) => {
    if (score >= 71) return "#22c55e"; // green
    if (score >= 41) return "#eab308"; // yellow
    return "#ef4444"; // red
  };

  const getScoreLabel = (score: number) => {
    if (score >= 71) return "High Virality Potential";
    if (score >= 41) return "Moderate Potential";
    return "Low Potential";
  };

  const getFrictionIcon = (level: "low" | "medium" | "high") => {
    switch (level) {
      case "low": return "🟢";
      case "medium": return "🟡";
      case "high": return "🔴";
    }
  };

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case "positive": return "text-green-400 bg-green-500/10";
      case "negative": return "text-red-400 bg-red-500/10";
      case "neutral": return "text-gray-400 bg-gray-500/10";
      case "skeptical": return "text-yellow-400 bg-yellow-500/10";
      default: return "text-gray-400 bg-gray-500/10";
    }
  };

  if (loading || !simulationResult) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-warroom-surface border border-warroom-border rounded-xl p-8 max-w-md">
          <div className="flex flex-col items-center gap-4">
            <div className="animate-spin w-8 h-8 border-2 border-warroom-accent border-t-transparent rounded-full"></div>
            <div className="text-center">
              <h3 className="text-sm font-semibold text-warroom-text mb-1">🔮 Running Simulation</h3>
              <p className="text-xs text-warroom-muted">
                Testing against personas and analyzing viral potential...
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-warroom-bg border border-warroom-border rounded-xl w-full max-w-6xl h-[90vh] flex flex-col">
        {/* Top Bar */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-warroom-border">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🔮</span>
            <div>
              <h2 className="text-lg font-bold text-warroom-text">Mirofish Prediction Report</h2>
              <p className="text-xs text-warroom-muted">
                Simulation run at {new Date(simulationTimestamp).toLocaleTimeString()}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-warroom-surface rounded-lg text-warroom-muted hover:text-warroom-text transition"
          >
            <X size={20} />
          </button>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Left Column - The Vibe Check (40%) */}
          <div className="w-2/5 p-6 border-r border-warroom-border overflow-y-auto">
            {/* Engagement Score Gauge */}
            <div className="mb-8">
              <h3 className="text-sm font-semibold text-warroom-text mb-4">Engagement Score</h3>
              <div className="flex flex-col items-center">
                {/* Large Circular Gauge */}
                <div className="relative w-32 h-32 mb-4">
                  <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                    {/* Background circle */}
                    <circle
                      cx="50"
                      cy="50"
                      r="40"
                      stroke="currentColor"
                      strokeWidth="8"
                      fill="none"
                      className="text-warroom-border"
                    />
                    {/* Progress circle */}
                    <circle
                      cx="50"
                      cy="50"
                      r="40"
                      stroke={getScoreColor(simulationResult.engagementScore)}
                      strokeWidth="8"
                      fill="none"
                      strokeLinecap="round"
                      strokeDasharray={`${simulationResult.engagementScore * 2.51} 251`}
                      className="transition-all duration-1000"
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-3xl font-bold text-warroom-text">{simulationResult.engagementScore}</span>
                  </div>
                </div>
                <div
                  className="px-4 py-2 rounded-lg text-sm font-medium text-center"
                  style={{ 
                    backgroundColor: getScoreColor(simulationResult.engagementScore) + "20",
                    color: getScoreColor(simulationResult.engagementScore)
                  }}
                >
                  {getScoreLabel(simulationResult.engagementScore)}
                </div>
              </div>
            </div>

            {/* Predicted Metrics - 2x2 Grid */}
            <div className="mb-8">
              <h3 className="text-sm font-semibold text-warroom-text mb-4">Predicted Metrics</h3>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { key: "likesPropensity", label: "Like", icon: Heart, value: simulationResult.metrics.likesPropensity },
                  { key: "sharesPropensity", label: "Share", icon: Share, value: simulationResult.metrics.sharesPropensity },
                  { key: "savesPropensity", label: "Save", icon: Bookmark, value: simulationResult.metrics.savesPropensity },
                  { key: "commentsPropensity", label: "Comment", icon: MessageCircle, value: simulationResult.metrics.commentsPropensity },
                ].map(({ key, label, icon: Icon, value }) => (
                  <div key={key} className="bg-warroom-surface border border-warroom-border rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <Icon size={14} className="text-warroom-accent" />
                      <span className="text-xs font-medium text-warroom-text">{label}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-lg font-bold" style={{ color: getScoreColor(value) }}>
                        {value}
                      </span>
                      <span className="text-xs text-warroom-muted">%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Audio Recommendation */}
            <div className="bg-warroom-surface border border-warroom-border rounded-lg p-4">
              <h4 className="text-sm font-semibold text-warroom-text mb-2">Audio Recommendation</h4>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-warroom-accent">
                    Best audio: {simulationResult.audioRecommendation.suggestion}
                  </span>
                </div>
                <p className="text-xs text-warroom-muted">
                  {simulationResult.audioRecommendation.impact}
                </p>
              </div>
            </div>
          </div>

          {/* Right Column - The Details (60%) */}
          <div className="w-3/5 p-6 overflow-y-auto space-y-6">
            {/* Retention Timeline */}
            <div>
              <h3 className="text-sm font-semibold text-warroom-text mb-4">Retention Timeline</h3>
              <div className="space-y-2">
                {simulationResult.retentionTimeline.map((point, index) => (
                  <div key={index} className="flex items-center gap-3">
                    <div className="w-8 text-xs text-warroom-muted font-mono">
                      {point.timestamp}
                    </div>
                    <div className="flex-1 relative">
                      <div className="bg-warroom-border h-2 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-warroom-accent transition-all duration-500"
                          style={{ width: `${point.percentage}%` }}
                        />
                      </div>
                    </div>
                    <div className="w-12 text-xs text-warroom-text font-medium text-right">
                      {point.percentage}%
                    </div>
                    <div className="w-40 text-xs text-warroom-muted">
                      {point.reason}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Predicted Comments */}
            <div>
              <h3 className="text-sm font-semibold text-warroom-text mb-3">
                Predicted Comments
              </h3>
              <p className="text-xs text-warroom-muted mb-3">
                {simulationResult.predictedComments.length} Agents are already typing...
              </p>
              <div className="space-y-3">
                {simulationResult.predictedComments.map((comment, index) => (
                  <div key={index} className="flex gap-3">
                    <div className="w-8 h-8 rounded-full bg-warroom-accent/20 text-warroom-accent flex items-center justify-center text-xs font-bold">
                      {comment.personaInitials}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-medium text-warroom-text">
                          {comment.personaName}
                        </span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${getSentimentColor(comment.sentiment)}`}>
                          {comment.sentiment}
                        </span>
                      </div>
                      <p className="text-sm text-warroom-text">
                        {comment.comment}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Scene Friction Map */}
            <div>
              <h3 className="text-sm font-semibold text-warroom-text mb-4">Scene Friction Map</h3>
              <div className="space-y-2">
                {simulationResult.sceneFriction.map((scene, index) => (
                  <div key={index} className="flex items-center gap-3 p-3 bg-warroom-surface border border-warroom-border rounded-lg">
                    <div className="text-sm">
                      {getFrictionIcon(scene.frictionLevel)}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium text-warroom-text">
                          {scene.scene}
                        </span>
                        <span className="text-xs text-warroom-muted">
                          {scene.frictionLevel} friction
                        </span>
                      </div>
                      <p className="text-xs text-warroom-muted">
                        {scene.description}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Magic Edit */}
            {simulationResult.optimization && (
              <div className="bg-warroom-accent/10 border border-warroom-accent rounded-lg p-4">
                <h3 className="text-sm font-semibold text-warroom-text mb-3 flex items-center gap-2">
                  <Sparkles size={16} className="text-warroom-accent" />
                  Optimization Recommendation
                </h3>
                <div className="space-y-3">
                  <div>
                    <p className="text-sm text-warroom-text mb-2">
                      {simulationResult.optimization.reason}
                    </p>
                    <div className="bg-warroom-bg border border-warroom-border rounded-lg p-3">
                      <div className="text-xs text-warroom-muted mb-1">Suggested change:</div>
                      <p className="text-sm text-warroom-text">
                        "{simulationResult.optimization.suggestedText}"
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="text-sm font-medium text-warroom-accent">
                      Predicted impact: {simulationResult.optimization.predictedImpact}
                    </div>
                    <button
                      onClick={() => onOptimize(simulationResult.optimization!)}
                      className="flex items-center gap-2 px-4 py-2 bg-warroom-accent text-white text-sm font-medium rounded-lg hover:bg-warroom-accent/80 transition"
                    >
                      <Wand2 size={14} />
                      Apply Fix
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}