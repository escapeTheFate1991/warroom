"use client";

import React, { useState } from 'react';
import { 
  BarChart3, TrendingUp, Clock, Zap, Target, Film, Eye,
  ArrowUpRight, ArrowDownRight, Info, Loader2, Play
} from 'lucide-react';
import { InfoTooltip } from './RedesignedCompetitorCards';

interface VideoAnalyticsProps {
  videoAnalytics: any;
  viralPatterns: any;
  contentRecommendations: any;
  loadingVideoAnalytics: boolean;
  loadingViralPatterns: boolean;
  loadingRecommendations: boolean;
  selectedAnalyticsVideo: any;
  onVideoSelect: (video: any) => void;
}

function formatNumber(num: number): string {
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
  return num.toString();
}

function formatPercent(num: number): string {
  return `${(num * 100).toFixed(1)}%`;
}

function RetentionCurveVisualization({ curve, title }: { curve: number[], title: string }) {
  if (!curve || curve.length === 0) return null;

  const maxValue = Math.max(...curve);
  const normalizedCurve = curve.map(val => (val / maxValue) * 100);

  return (
    <div className="space-y-2">
      <h5 className="text-xs font-medium text-warroom-text">{title}</h5>
      <div className="flex items-end gap-1 h-16">
        {normalizedCurve.map((height, i) => (
          <div key={i} className="relative flex-1 min-w-[2px]">
            <div 
              className="bg-gradient-to-t from-warroom-accent to-warroom-accent/50 rounded-t transition-all"
              style={{ height: `${height}%` }}
            />
            <div className="absolute -bottom-4 left-0 right-0 text-center">
              <span className="text-[8px] text-warroom-muted">{i * 5}s</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function DropOffAnalysis({ dropOffs }: { dropOffs: any[] }) {
  if (!dropOffs || dropOffs.length === 0) return null;

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <h5 className="text-xs font-medium text-warroom-text">Critical Drop-off Points</h5>
        <InfoTooltip content="Moments where significant viewer drop-off occurs, identified through retention curve analysis">
          <Info size={10} className="text-warroom-muted" />
        </InfoTooltip>
      </div>
      <div className="space-y-1">
        {dropOffs.map((dropOff, i) => (
          <div key={i} className="flex items-center justify-between bg-red-400/5 border border-red-400/10 rounded-lg px-2 py-1">
            <div>
              <span className="text-xs font-medium text-red-400">{dropOff.timestamp}s</span>
              <span className="text-xs text-warroom-muted ml-2">{dropOff.reason || 'Unknown cause'}</span>
            </div>
            <span className="text-xs text-red-400 flex items-center gap-1">
              <ArrowDownRight size={10} />
              -{dropOff.drop_percentage}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function VideoPerformanceCard({ video, onSelect, isSelected }: { 
  video: any; 
  onSelect: (video: any) => void; 
  isSelected: boolean;
}) {
  const engagementTrend = video.engagement_rate > 5 ? 'high' : video.engagement_rate > 2 ? 'medium' : 'low';
  const trendColor = engagementTrend === 'high' ? 'text-green-400' : 
                    engagementTrend === 'medium' ? 'text-yellow-400' : 'text-red-400';

  return (
    <div 
      className={`bg-warroom-bg border rounded-lg p-3 cursor-pointer transition ${
        isSelected ? 'border-warroom-accent bg-warroom-accent/5' : 'border-warroom-border hover:border-warroom-accent/50'
      }`}
      onClick={() => onSelect(video)}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium text-warroom-text">@{video.competitor_handle}</span>
            <span className="px-2 py-0.5 bg-pink-500/10 text-pink-400 rounded text-[10px]">
              {video.platform}
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs text-warroom-muted mb-1">
            <span>Duration: {Math.floor(video.duration / 60)}:{(video.duration % 60).toString().padStart(2, '0')}</span>
            <span>•</span>
            <span>Hook: {Math.round(video.hook_strength)}%</span>
          </div>
        </div>
        <div className="text-right">
          <p className={`text-lg font-bold ${trendColor}`}>{formatPercent(video.engagement_rate / 100)}</p>
          <p className="text-[10px] text-warroom-muted">Engagement</p>
        </div>
      </div>
      
      <div className="grid grid-cols-3 gap-2 text-center mb-2">
        <div>
          <p className="text-xs font-bold text-warroom-text">{formatNumber(video.likes)}</p>
          <p className="text-[9px] text-warroom-muted">Likes</p>
        </div>
        <div>
          <p className="text-xs font-bold text-warroom-text">{formatNumber(video.comments)}</p>
          <p className="text-[9px] text-warroom-muted">Comments</p>
        </div>
        <div>
          <p className="text-xs font-bold text-warroom-text">{formatNumber(video.views)}</p>
          <p className="text-[9px] text-warroom-muted">Views</p>
        </div>
      </div>

      {video.content_themes && video.content_themes.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {video.content_themes.slice(0, 3).map((theme: string, i: number) => (
            <span key={i} className="px-1.5 py-0.5 bg-purple-500/10 text-purple-400 rounded text-[9px]">
              {theme}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function ViralPatternCard({ pattern }: { pattern: any }) {
  const confidenceColor = pattern.confidence_score >= 0.8 ? 'text-green-400' :
                          pattern.confidence_score >= 0.6 ? 'text-yellow-400' : 'text-orange-400';

  const categoryIcons = {
    hook: Zap,
    structure: BarChart3,
    visual: Eye,
    timing: Clock
  };

  const Icon = categoryIcons[pattern.category as keyof typeof categoryIcons] || Target;

  return (
    <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <Icon size={16} className="text-warroom-accent" />
          <span className="text-sm font-semibold text-warroom-text">{pattern.title}</span>
        </div>
        <div className="text-right">
          <p className={`text-sm font-bold ${confidenceColor}`}>
            {Math.round(pattern.confidence_score * 100)}%
          </p>
          <p className="text-[10px] text-warroom-muted">Confidence</p>
        </div>
      </div>

      <p className="text-xs text-warroom-muted mb-3">{pattern.description}</p>

      <div className="grid grid-cols-2 gap-3 mb-3">
        <div className="text-center">
          <p className="text-lg font-bold text-emerald-400">{formatPercent(pattern.success_rate / 100)}</p>
          <p className="text-[10px] text-warroom-muted">Success Rate</p>
        </div>
        <div className="text-center">
          <p className="text-lg font-bold text-blue-400">+{formatPercent(pattern.avg_engagement_boost / 100)}</p>
          <p className="text-[10px] text-warroom-muted">Engagement Boost</p>
        </div>
      </div>

      <div className="border-t border-warroom-border pt-2">
        <p className="text-xs text-warroom-text">{pattern.recommended_usage}</p>
      </div>
    </div>
  );
}

export default function EnhancedVideoAnalytics({
  videoAnalytics,
  viralPatterns,
  contentRecommendations,
  loadingVideoAnalytics,
  loadingViralPatterns,
  loadingRecommendations,
  selectedAnalyticsVideo,
  onVideoSelect
}: VideoAnalyticsProps) {
  return (
    <div className="space-y-6">
      {/* Performance Overview */}
      <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <BarChart3 size={24} className="text-warroom-accent" />
          <div>
            <h3 className="text-lg font-semibold text-warroom-text">Performance Analytics</h3>
            <p className="text-xs text-warroom-muted">Frame-by-frame analysis and engagement patterns</p>
          </div>
          <InfoTooltip content="Comprehensive video performance metrics derived from actual video analysis data including retention curves, hook effectiveness, and engagement patterns.">
            <Info size={16} className="text-warroom-muted" />
          </InfoTooltip>
        </div>

        {loadingVideoAnalytics ? (
          <div className="text-center py-16">
            <Loader2 size={32} className="mx-auto mb-4 animate-spin text-warroom-accent" />
            <p className="text-sm text-warroom-muted">Analyzing video performance…</p>
          </div>
        ) : videoAnalytics?.success ? (
          <div className="space-y-6">
            {/* Key Metrics */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <InfoTooltip content="Total number of videos analyzed with frame-by-frame breakdown">
                <div className="bg-warroom-bg rounded-xl p-4 text-center">
                  <p className="text-2xl font-bold text-warroom-accent">{videoAnalytics.total_videos_analyzed}</p>
                  <p className="text-xs text-warroom-muted">Videos Analyzed</p>
                </div>
              </InfoTooltip>
              
              <InfoTooltip content="Videos with engagement rates above 5% threshold">
                <div className="bg-warroom-bg rounded-xl p-4 text-center">
                  <p className="text-2xl font-bold text-emerald-400">{videoAnalytics.top_performers}</p>
                  <p className="text-xs text-warroom-muted">Top Performers</p>
                </div>
              </InfoTooltip>

              <InfoTooltip content="Average engagement rate across all analyzed videos">
                <div className="bg-warroom-bg rounded-xl p-4 text-center">
                  <p className="text-2xl font-bold text-blue-400">
                    {formatPercent(videoAnalytics.performance_benchmarks.avg_engagement_rate / 100)}
                  </p>
                  <p className="text-xs text-warroom-muted">Avg Engagement</p>
                </div>
              </InfoTooltip>

              <InfoTooltip content="Average retention rate at 30-second mark across all videos">
                <div className="bg-warroom-bg rounded-xl p-4 text-center">
                  <p className="text-2xl font-bold text-purple-400">
                    {formatPercent(videoAnalytics.performance_benchmarks.avg_retention_30s)}
                  </p>
                  <p className="text-xs text-warroom-muted">30s Retention</p>
                </div>
              </InfoTooltip>
            </div>

            {/* Video Performance Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Video List */}
              <div>
                <h4 className="text-sm font-semibold text-warroom-text mb-3">Top Performing Videos</h4>
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {videoAnalytics.videos.slice(0, 10).map((video: any) => (
                    <VideoPerformanceCard
                      key={video.post_id}
                      video={video}
                      onSelect={onVideoSelect}
                      isSelected={selectedAnalyticsVideo?.post_id === video.post_id}
                    />
                  ))}
                </div>
              </div>

              {/* Selected Video Details */}
              <div>
                {selectedAnalyticsVideo ? (
                  <div className="space-y-4">
                    <div className="flex items-center gap-2 mb-3">
                      <h4 className="text-sm font-semibold text-warroom-text">Detailed Analysis</h4>
                      <InfoTooltip content="Detailed breakdown of selected video including retention curve and drop-off analysis">
                        <Info size={12} className="text-warroom-muted" />
                      </InfoTooltip>
                    </div>

                    <div className="bg-warroom-bg border border-warroom-border rounded-xl p-4">
                      <div className="flex items-center justify-between mb-4">
                        <span className="text-sm font-medium text-warroom-text">
                          @{selectedAnalyticsVideo.competitor_handle}
                        </span>
                        <span className="text-xs text-warroom-muted">
                          {selectedAnalyticsVideo.platform}
                        </span>
                      </div>

                      {selectedAnalyticsVideo.retention_curve && (
                        <RetentionCurveVisualization
                          curve={selectedAnalyticsVideo.retention_curve}
                          title="Viewer Retention Curve"
                        />
                      )}

                      {selectedAnalyticsVideo.drop_off_points && (
                        <div className="mt-4">
                          <DropOffAnalysis dropOffs={selectedAnalyticsVideo.drop_off_points} />
                        </div>
                      )}

                      <div className="mt-4 pt-4 border-t border-warroom-border">
                        <h6 className="text-xs font-medium text-warroom-text mb-2">Performance Metrics</h6>
                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div>
                            <span className="text-warroom-muted">Hook Strength:</span>
                            <span className="text-orange-400 font-medium ml-1">
                              {Math.round(selectedAnalyticsVideo.hook_strength)}%
                            </span>
                          </div>
                          <div>
                            <span className="text-warroom-muted">Virality Score:</span>
                            <span className="text-pink-400 font-medium ml-1">
                              {selectedAnalyticsVideo.virality_score?.toFixed(1) || 'N/A'}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="bg-warroom-bg border border-warroom-border rounded-xl p-8 text-center">
                    <Film size={32} className="text-warroom-muted mx-auto mb-3" />
                    <p className="text-sm text-warroom-muted">Select a video to view detailed analysis</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center py-16">
            <p className="text-sm text-warroom-muted">No video analytics available yet</p>
          </div>
        )}
      </div>

      {/* Viral Patterns */}
      <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <TrendingUp size={24} className="text-orange-400" />
          <div>
            <h3 className="text-lg font-semibold text-warroom-text">Viral Pattern Detection</h3>
            <p className="text-xs text-warroom-muted">AI-identified patterns in high-performing content</p>
          </div>
          <InfoTooltip content="Machine learning algorithms analyze top-performing videos to identify recurring patterns in hooks, visuals, pacing, and structure that contribute to viral success.">
            <Info size={16} className="text-warroom-muted" />
          </InfoTooltip>
        </div>

        {loadingViralPatterns ? (
          <div className="text-center py-16">
            <Loader2 size={32} className="mx-auto mb-4 animate-spin text-orange-400" />
            <p className="text-sm text-warroom-muted">Identifying viral patterns…</p>
          </div>
        ) : viralPatterns && viralPatterns.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {viralPatterns.map((pattern: any, i: number) => (
              <ViralPatternCard key={i} pattern={pattern} />
            ))}
          </div>
        ) : (
          <div className="text-center py-16">
            <p className="text-sm text-warroom-muted">No viral patterns detected yet</p>
            <p className="text-xs text-warroom-muted mt-1">Analyze more videos to identify patterns</p>
          </div>
        )}
      </div>

      {/* Content Recommendations */}
      <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <Target size={24} className="text-emerald-400" />
          <div>
            <h3 className="text-lg font-semibold text-warroom-text">AI Content Recommendations</h3>
            <p className="text-xs text-warroom-muted">Actionable insights for content creation</p>
          </div>
          <InfoTooltip content="Data-driven recommendations based on competitor analysis, viral patterns, and audience behavior to optimize your content strategy.">
            <Info size={16} className="text-warroom-muted" />
          </InfoTooltip>
        </div>

        {loadingRecommendations ? (
          <div className="text-center py-16">
            <Loader2 size={32} className="mx-auto mb-4 animate-spin text-emerald-400" />
            <p className="text-sm text-warroom-muted">Generating recommendations…</p>
          </div>
        ) : contentRecommendations && contentRecommendations.length > 0 ? (
          <div className="space-y-4">
            {contentRecommendations.map((recommendation: any, i: number) => (
              <div key={i} className="bg-warroom-bg border border-warroom-border rounded-xl p-4">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h4 className="text-sm font-semibold text-warroom-text">{recommendation.title}</h4>
                    <span className="inline-block px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded text-xs mt-1">
                      {recommendation.category}
                    </span>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-emerald-400">
                      {Math.round(recommendation.confidence_score * 100)}%
                    </p>
                    <p className="text-[10px] text-warroom-muted">Confidence</p>
                  </div>
                </div>
                
                <p className="text-sm text-warroom-text mb-3">{recommendation.description}</p>
                
                <div className="bg-emerald-400/5 border border-emerald-400/10 rounded-lg p-3">
                  <p className="text-xs font-medium text-emerald-400 mb-1">Expected Impact</p>
                  <p className="text-xs text-warroom-text">{recommendation.expected_impact}</p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-16">
            <p className="text-sm text-warroom-muted">No recommendations available yet</p>
            <p className="text-xs text-warroom-muted mt-1">Complete video analysis to get recommendations</p>
          </div>
        )}
      </div>
    </div>
  );
}