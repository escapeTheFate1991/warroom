"use client";

import { useState, useEffect } from "react";
import { 
  BarChart3, TrendingUp, Clock, Zap, Target, Film, Eye,
  ArrowUpRight, ArrowDownRight, Info, Loader2, Play, AlertCircle
} from "lucide-react";
import { API, authFetch } from "@/lib/api";

interface VideoRecord {
  id: number;
  title: string;
  competitor_handle: string;
  platform: string;
  runtime_seconds?: number;
  likes: number;
  comments: number;
  shares?: number;
  engagement_score: number;
  posted_at?: string;
  url?: string;
}

interface PerformanceComparison {
  post_id: number;
  engagement_rate: number;
  virality_score: number;
  vs_competitor_avg: number;
  vs_platform_avg: number;
  rank_percentile: number;
}

interface CommentSentiment {
  overall_sentiment: string;
  positive_percentage: number;
  negative_percentage: number;
  neutral_percentage: number;
  top_positive_themes: string[];
  top_negative_themes: string[];
}

interface DropOffAnalysis {
  retention_curve: number[];
  drop_off_points: Array<{
    timestamp: number;
    reason: string;
    drop_percentage: number;
  }>;
  avg_watch_time: number;
  completion_rate: number;
}

interface VideoAnalyticsData {
  performance_comparison?: PerformanceComparison;
  comment_sentiment?: CommentSentiment;
  dropoff_analysis?: DropOffAnalysis;
  available_data: {
    has_performance_data: boolean;
    has_sentiment_data: boolean;
    has_dropoff_data: boolean;
  };
}

function formatPercent(n: number): string {
  return `${n.toFixed(1)}%`;
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function PerformanceComparisonCard({ comparison }: { comparison: PerformanceComparison }) {
  const vsCompetitorTrend = comparison.vs_competitor_avg >= 0;
  const vsPlatformTrend = comparison.vs_platform_avg >= 0;

  return (
    <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
      <h4 className="text-sm font-semibold text-warroom-text mb-4 flex items-center gap-2">
        <TrendingUp size={16} className="text-warroom-accent" />
        Performance vs. Competition
      </h4>
      
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="text-center">
          <p className="text-2xl font-bold text-warroom-accent">{formatPercent(comparison.engagement_rate)}</p>
          <p className="text-xs text-warroom-muted">Engagement Rate</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-pink-400">{comparison.virality_score.toFixed(1)}</p>
          <p className="text-xs text-warroom-muted">Virality Score</p>
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm text-warroom-text">vs. Competitor Average</span>
          <div className="flex items-center gap-1">
            {vsCompetitorTrend ? (
              <ArrowUpRight size={14} className="text-emerald-400" />
            ) : (
              <ArrowDownRight size={14} className="text-red-400" />
            )}
            <span className={`text-sm font-medium ${vsCompetitorTrend ? 'text-emerald-400' : 'text-red-400'}`}>
              {vsCompetitorTrend ? '+' : ''}{formatPercent(comparison.vs_competitor_avg)}
            </span>
          </div>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-sm text-warroom-text">vs. Platform Average</span>
          <div className="flex items-center gap-1">
            {vsPlatformTrend ? (
              <ArrowUpRight size={14} className="text-emerald-400" />
            ) : (
              <ArrowDownRight size={14} className="text-red-400" />
            )}
            <span className={`text-sm font-medium ${vsPlatformTrend ? 'text-emerald-400' : 'text-red-400'}`}>
              {vsPlatformTrend ? '+' : ''}{formatPercent(comparison.vs_platform_avg)}
            </span>
          </div>
        </div>

        <div className="mt-4 p-3 bg-warroom-bg rounded-lg">
          <div className="flex items-center justify-between">
            <span className="text-sm text-warroom-text">Performance Rank</span>
            <span className="text-sm font-medium text-warroom-accent">
              Top {Math.round(100 - comparison.rank_percentile)}%
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function SentimentAnalysisCard({ sentiment }: { sentiment: CommentSentiment }) {
  const sentimentColor = sentiment.overall_sentiment === 'positive' ? 'text-emerald-400' :
                         sentiment.overall_sentiment === 'negative' ? 'text-red-400' : 'text-yellow-400';

  return (
    <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
      <h4 className="text-sm font-semibold text-warroom-text mb-4 flex items-center gap-2">
        <Zap size={16} className="text-orange-400" />
        Comment Sentiment Analysis
      </h4>

      <div className="text-center mb-4">
        <p className={`text-2xl font-bold capitalize ${sentimentColor}`}>
          {sentiment.overall_sentiment}
        </p>
        <p className="text-xs text-warroom-muted">Overall Sentiment</p>
      </div>

      {/* Sentiment Bar */}
      <div className="mb-4">
        <div className="flex h-3 rounded-full overflow-hidden bg-warroom-bg">
          <div 
            className="bg-emerald-400" 
            style={{ width: `${sentiment.positive_percentage}%` }}
          />
          <div 
            className="bg-warroom-border" 
            style={{ width: `${sentiment.neutral_percentage}%` }}
          />
          <div 
            className="bg-red-400" 
            style={{ width: `${sentiment.negative_percentage}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-warroom-muted mt-1">
          <span className="text-emerald-400">{formatPercent(sentiment.positive_percentage)}</span>
          <span>{formatPercent(sentiment.neutral_percentage)}</span>
          <span className="text-red-400">{formatPercent(sentiment.negative_percentage)}</span>
        </div>
      </div>

      <div className="space-y-3">
        {sentiment.top_positive_themes.length > 0 && (
          <div>
            <p className="text-xs text-emerald-400 font-medium mb-1">Top Positive Themes</p>
            <div className="flex flex-wrap gap-1">
              {sentiment.top_positive_themes.map((theme, i) => (
                <span key={i} className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded text-xs">
                  {theme}
                </span>
              ))}
            </div>
          </div>
        )}

        {sentiment.top_negative_themes.length > 0 && (
          <div>
            <p className="text-xs text-red-400 font-medium mb-1">Areas of Concern</p>
            <div className="flex flex-wrap gap-1">
              {sentiment.top_negative_themes.map((theme, i) => (
                <span key={i} className="px-2 py-0.5 bg-red-500/10 text-red-400 rounded text-xs">
                  {theme}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function RetentionAnalysisCard({ analysis }: { analysis: DropOffAnalysis }) {
  const maxValue = Math.max(...analysis.retention_curve);
  
  return (
    <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
      <h4 className="text-sm font-semibold text-warroom-text mb-4 flex items-center gap-2">
        <Eye size={16} className="text-blue-400" />
        Retention & Drop-off Analysis
      </h4>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="text-center">
          <p className="text-xl font-bold text-blue-400">{formatTime(analysis.avg_watch_time)}</p>
          <p className="text-xs text-warroom-muted">Avg. Watch Time</p>
        </div>
        <div className="text-center">
          <p className="text-xl font-bold text-purple-400">{formatPercent(analysis.completion_rate)}</p>
          <p className="text-xs text-warroom-muted">Completion Rate</p>
        </div>
      </div>

      {/* Retention Curve */}
      {analysis.retention_curve.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-medium text-warroom-text mb-2">Retention Curve</p>
          <div className="flex items-end gap-1 h-16 mb-2">
            {analysis.retention_curve.map((value, i) => {
              const height = (value / maxValue) * 100;
              return (
                <div key={i} className="flex-1 relative">
                  <div 
                    className="bg-gradient-to-t from-blue-500 to-blue-300 rounded-t transition-all"
                    style={{ height: `${height}%` }}
                  />
                  {i % 2 === 0 && (
                    <span className="absolute -bottom-4 text-[8px] text-warroom-muted left-0">
                      {i * 5}s
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Drop-off Points */}
      {analysis.drop_off_points.length > 0 && (
        <div>
          <p className="text-xs font-medium text-warroom-text mb-2">Critical Drop-off Points</p>
          <div className="space-y-2">
            {analysis.drop_off_points.slice(0, 3).map((dropOff, i) => (
              <div key={i} className="flex items-center justify-between bg-red-500/5 border border-red-500/10 rounded-lg px-3 py-2">
                <div>
                  <span className="text-xs font-medium text-red-400">{formatTime(dropOff.timestamp)}</span>
                  <span className="text-xs text-warroom-muted ml-2">{dropOff.reason}</span>
                </div>
                <span className="text-xs text-red-400 flex items-center gap-1">
                  <ArrowDownRight size={10} />
                  -{formatPercent(dropOff.drop_percentage)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function EmptyStateCard({ title, description, icon: Icon }: { 
  title: string; 
  description: string; 
  icon: any; 
}) {
  return (
    <div className="bg-warroom-surface border border-warroom-border rounded-xl p-8 text-center">
      <Icon size={32} className="text-warroom-muted mx-auto mb-3 opacity-30" />
      <p className="text-sm font-medium text-warroom-text mb-1">{title}</p>
      <p className="text-xs text-warroom-muted">{description}</p>
    </div>
  );
}

export default function VideoAnalyticsTab({ videoRecord }: { videoRecord: VideoRecord }) {
  const [analytics, setAnalytics] = useState<VideoAnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setLoading(true);
        setError("");

        // Parallel fetch for all analytics data
        const [performanceRes, sentimentRes, dropoffRes] = await Promise.all([
          authFetch(`${API}/api/competitors/video-analytics/performance-comparison?post_id=${videoRecord.id}`),
          authFetch(`${API}/api/content-intel/video/${videoRecord.id}/sentiment`),
          authFetch(`${API}/api/competitors/video-analytics/dropoff-analysis/${videoRecord.id}`)
        ]);

        const analyticsData: VideoAnalyticsData = {
          available_data: {
            has_performance_data: performanceRes.ok,
            has_sentiment_data: sentimentRes.ok,
            has_dropoff_data: dropoffRes.ok
          }
        };

        // Collect available data
        if (performanceRes.ok) {
          const performanceData = await performanceRes.json();
          if (performanceData.videos && performanceData.videos.length > 0) {
            const videoData = performanceData.videos.find((v: any) => v.post_id === videoRecord.id);
            if (videoData) {
              analyticsData.performance_comparison = {
                post_id: videoRecord.id,
                engagement_rate: videoData.engagement_rate,
                virality_score: videoData.virality_score || 0,
                vs_competitor_avg: videoData.engagement_rate - (performanceData.performance_benchmarks?.avg_engagement_rate || 0),
                vs_platform_avg: videoData.engagement_rate - 3.2, // Platform average estimate
                rank_percentile: 75 // Placeholder - would be calculated from actual data
              };
            }
          }
        }

        if (sentimentRes.ok) {
          analyticsData.comment_sentiment = await sentimentRes.json();
        }

        if (dropoffRes.ok) {
          const dropoffData = await dropoffRes.json();
          analyticsData.dropoff_analysis = {
            retention_curve: dropoffData.retention_curve || [],
            drop_off_points: dropoffData.drop_off_points || [],
            avg_watch_time: dropoffData.avg_watch_time || 0,
            completion_rate: dropoffData.completion_rate || 0
          };
        }

        setAnalytics(analyticsData);
      } catch (err) {
        setError("Failed to load analytics data");
        console.error("Analytics fetch error:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchAnalytics();
  }, [videoRecord.id]);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="text-center py-16">
          <Loader2 size={32} className="mx-auto mb-4 animate-spin text-warroom-accent" />
          <p className="text-sm text-warroom-muted">Analyzing video performance...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="text-center py-16">
          <AlertCircle size={32} className="mx-auto mb-4 text-red-400" />
          <p className="text-sm text-red-400">{error}</p>
        </div>
      </div>
    );
  }

  const hasAnyData = analytics && (
    analytics.available_data.has_performance_data ||
    analytics.available_data.has_sentiment_data ||
    analytics.available_data.has_dropoff_data
  );

  if (!hasAnyData) {
    return (
      <div className="max-w-4xl mx-auto">
        <EmptyStateCard
          title="Analytics data not available for this video"
          description="This video hasn't been processed for detailed analytics yet. Analytics are available for videos with frame analysis completed and sufficient comment data."
          icon={BarChart3}
        />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Performance Comparison */}
      {analytics?.performance_comparison ? (
        <PerformanceComparisonCard comparison={analytics.performance_comparison} />
      ) : (
        <EmptyStateCard
          title="Performance comparison not available"
          description="Insufficient data to compare against competitor averages"
          icon={TrendingUp}
        />
      )}

      {/* Comment Sentiment */}
      {analytics?.comment_sentiment ? (
        <SentimentAnalysisCard sentiment={analytics.comment_sentiment} />
      ) : (
        <EmptyStateCard
          title="Comment sentiment not available"
          description="No comment data processed for sentiment analysis"
          icon={Zap}
        />
      )}

      {/* Retention Analysis */}
      {analytics?.dropoff_analysis ? (
        <RetentionAnalysisCard analysis={analytics.dropoff_analysis} />
      ) : (
        <EmptyStateCard
          title="Retention analysis not available"
          description="Video frame analysis required for retention curve generation"
          icon={Eye}
        />
      )}
    </div>
  );
}