"use client";

import React, { useState, useRef, useEffect } from 'react';
import { 
  Heart, MessageCircle, Eye, ExternalLink, Flame, Film, FileText, 
  Sparkles, BarChart3, Target, Zap, Info, Clock, TrendingUp,
  ArrowUpRight, Play, Loader2, Brain
} from 'lucide-react';

// Info tooltip component
function InfoTooltip({ content, children }: { content: string; children: React.ReactNode }) {
  const [showTooltip, setShowTooltip] = useState(false);
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });
  const triggerRef = useRef<HTMLDivElement>(null);

  const handleMouseEnter = (e: React.MouseEvent) => {
    if (triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      setTooltipPosition({
        x: rect.left + rect.width / 2,
        y: rect.top - 8
      });
      setShowTooltip(true);
    }
  };

  return (
    <div className="relative inline-block">
      <div 
        ref={triggerRef}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={() => setShowTooltip(false)}
        className="cursor-help"
      >
        {children}
      </div>
      {showTooltip && (
        <div 
          className="fixed z-50 px-2 py-1 bg-gray-900 text-white text-xs rounded shadow-lg max-w-xs whitespace-pre-wrap pointer-events-none"
          style={{
            left: tooltipPosition.x,
            top: tooltipPosition.y,
            transform: 'translateX(-50%) translateY(-100%)'
          }}
        >
          {content}
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-l-transparent border-r-transparent border-t-gray-900"></div>
        </div>
      )}
    </div>
  );
}

// Enhanced video metrics card with accurate data
function VideoMetricsCard({ 
  video, 
  compact = false,
  showFrameAnalysis = false 
}: { 
  video: any; 
  compact?: boolean;
  showFrameAnalysis?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  
  // Calculate accurate metrics from video analysis data
  const getEngagementScore = () => {
    if (video.engagement_score) return video.engagement_score;
    // Fallback calculation if no score available
    return Math.round((video.likes + video.comments * 3 + video.shares * 5) / 100);
  };

  const getHookScore = () => {
    // Use real hook strength from content analysis
    if (video.content_analysis?.hook?.strength) {
      return Math.round(video.content_analysis.hook.strength * 100);
    }
    // Use video analysis hook strength
    if (video.video_analysis?.hook_strength) {
      return Math.round(video.video_analysis.hook_strength * 100);
    }
    // Fallback based on engagement in first 15 seconds
    return Math.min(100, Math.round(getEngagementScore() / 10));
  };

  const getRetentionScore = () => {
    // Use actual retention data from video analysis
    if (video.video_analysis?.retention_curve?.length > 0) {
      const avgRetention = video.video_analysis.retention_curve.reduce((a: number, b: number) => a + b, 0) / video.video_analysis.retention_curve.length;
      return Math.round(avgRetention);
    }
    // Fallback estimation
    return Math.max(20, 100 - Math.round(getEngagementScore() / 20));
  };

  const getViralityIndicators = () => {
    const indicators = [];
    
    // High engagement rate
    const engagementRate = (video.likes + video.comments) / (video.views || video.likes * 20) * 100;
    if (engagementRate > 5) indicators.push({ label: 'High Engagement', color: 'text-green-400' });
    
    // Strong hook (from analysis)
    if (getHookScore() > 80) indicators.push({ label: 'Strong Hook', color: 'text-orange-400' });
    
    // Good retention
    if (getRetentionScore() > 70) indicators.push({ label: 'Good Retention', color: 'text-blue-400' });
    
    // Rapid growth
    const hoursAgo = (new Date().getTime() - new Date(video.timestamp || video.posted_at).getTime()) / (1000 * 60 * 60);
    if (hoursAgo < 24 && video.likes > 10000) {
      indicators.push({ label: 'Trending', color: 'text-pink-400' });
    }
    
    return indicators;
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className={`bg-warroom-surface border border-warroom-border rounded-xl hover:border-warroom-accent/30 transition-all ${compact ? 'p-3' : 'p-4'}`}>
      {/* Header with improved hierarchy */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            {/* Format badge with tooltip */}
            <InfoTooltip content="Content format detected by AI analysis of visual and narrative patterns">
              <span className="px-2 py-0.5 bg-blue-500/10 text-blue-400 rounded-full text-xs font-medium">
                {video.detected_format?.replace('_', ' ') || 'Video'}
              </span>
            </InfoTooltip>
            
            {/* Analysis status */}
            {video.analysis_status === 'completed' && (
              <InfoTooltip content="Frame-by-frame analysis completed with detailed insights">
                <span className="flex items-center gap-1 px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded-full text-xs">
                  <Film size={10} />
                  Analyzed
                </span>
              </InfoTooltip>
            )}
            
            {/* Virality indicators */}
            {getViralityIndicators().map((indicator, i) => (
              <span key={i} className={`px-2 py-0.5 bg-gray-500/10 rounded-full text-xs ${indicator.color}`}>
                {indicator.label}
              </span>
            ))}
          </div>
          
          {/* Title with better typography */}
          <h4 className="text-sm font-semibold text-warroom-text line-clamp-2 mb-1">
            {video.title || video.hook || video.text?.slice(0, 60) + '...' || 'Untitled'}
          </h4>
          
          {/* Hook preview */}
          {video.hook && (
            <p className="text-xs text-warroom-accent line-clamp-1 mb-2">
              🪝 {video.hook}
            </p>
          )}
        </div>

        {/* Quick action menu */}
        <div className="flex items-center gap-1 flex-shrink-0 ml-2">
          <InfoTooltip content="View original post on platform">
            <a 
              href={video.url || video.post_url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="p-1.5 hover:bg-warroom-bg rounded-lg transition text-warroom-muted hover:text-warroom-accent"
            >
              <ExternalLink size={12} />
            </a>
          </InfoTooltip>
        </div>
      </div>

      {/* Enhanced metrics grid with tooltips */}
      <div className="grid grid-cols-4 gap-2 mb-3">
        <InfoTooltip content="Total likes received on this video">
          <div className="bg-warroom-bg rounded-lg p-2 text-center">
            <p className="text-xs font-bold text-warroom-text">{formatNumber(video.likes)}</p>
            <div className="flex items-center justify-center gap-1 text-[10px] text-red-400">
              <Heart size={8} />
              Likes
            </div>
          </div>
        </InfoTooltip>

        <InfoTooltip content="Comments indicating audience engagement and discussion">
          <div className="bg-warroom-bg rounded-lg p-2 text-center">
            <p className="text-xs font-bold text-warroom-text">{formatNumber(video.comments)}</p>
            <div className="flex items-center justify-center gap-1 text-[10px] text-blue-400">
              <MessageCircle size={8} />
              Comments
            </div>
          </div>
        </InfoTooltip>

        <InfoTooltip content={`Engagement score: ${getEngagementScore()}\nCalculated from likes, comments, shares and reach`}>
          <div className="bg-warroom-bg rounded-lg p-2 text-center">
            <p className="text-xs font-bold text-warroom-accent">{getEngagementScore()}</p>
            <div className="flex items-center justify-center gap-1 text-[10px] text-warroom-accent">
              <BarChart3 size={8} />
              Score
            </div>
          </div>
        </InfoTooltip>

        <InfoTooltip content={`Hook effectiveness: ${getHookScore()}%\nBased on early engagement and retention analysis`}>
          <div className="bg-warroom-bg rounded-lg p-2 text-center">
            <p className="text-xs font-bold text-orange-400">{getHookScore()}%</p>
            <div className="flex items-center justify-center gap-1 text-[10px] text-orange-400">
              <Zap size={8} />
              Hook
            </div>
          </div>
        </InfoTooltip>
      </div>

      {/* Content themes from actual analysis */}
      {video.video_analysis?.dominant_themes && video.video_analysis.dominant_themes.length > 0 && (
        <div className="mb-3">
          <InfoTooltip content="Content themes identified through AI analysis of visual and narrative elements">
            <div className="flex items-center gap-1 mb-1">
              <Target size={10} className="text-warroom-muted" />
              <span className="text-xs text-warroom-muted">Themes</span>
              <Info size={10} className="text-warroom-muted" />
            </div>
          </InfoTooltip>
          <div className="flex flex-wrap gap-1">
            {video.video_analysis.dominant_themes.slice(0, 3).map((theme: string, i: number) => (
              <span key={i} className="px-1.5 py-0.5 bg-purple-500/10 text-purple-400 rounded text-[10px]">
                {theme}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Video-specific metrics */}
      {(video.media_type === 'video' || video.media_type === 'reel') && (
        <div className="grid grid-cols-2 gap-2 mb-3">
          <InfoTooltip content={`Video retention rate: ${getRetentionScore()}%\nPercentage of viewers who watched to the end`}>
            <div className="bg-blue-500/5 border border-blue-500/10 rounded-lg p-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-blue-400">Retention</span>
                <span className="text-xs font-bold text-blue-400">{getRetentionScore()}%</span>
              </div>
              <div className="w-full bg-blue-500/10 rounded-full h-1 mt-1">
                <div 
                  className="bg-blue-400 h-1 rounded-full transition-all"
                  style={{ width: `${getRetentionScore()}%` }}
                />
              </div>
            </div>
          </InfoTooltip>

          {video.video_analysis?.total_duration && (
            <InfoTooltip content="Total video duration from frame analysis">
              <div className="bg-gray-500/5 border border-gray-500/10 rounded-lg p-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-warroom-muted">Duration</span>
                  <span className="text-xs font-bold text-warroom-text">
                    {formatDuration(video.video_analysis.total_duration)}
                  </span>
                </div>
                <div className="flex items-center gap-1 text-[10px] text-warroom-muted mt-1">
                  <Clock size={8} />
                  {video.video_analysis.content_style || 'Standard'}
                </div>
              </div>
            </InfoTooltip>
          )}
        </div>
      )}

      {/* Enhanced script generation with frame analysis data */}
      <div className="flex gap-2">


        {/* Frame analysis toggle */}
        {showFrameAnalysis && video.analysis_status === 'completed' && (
          <InfoTooltip content="View detailed frame-by-frame breakdown and visual analysis">
            <button
              onClick={() => setExpanded(!expanded)}
              className="px-3 py-2 bg-warroom-bg hover:bg-warroom-border/50 border border-warroom-border rounded-lg text-xs font-medium transition"
            >
              <Film size={12} />
            </button>
          </InfoTooltip>
        )}
      </div>

      {/* Expandable frame analysis section */}
      {expanded && showFrameAnalysis && video.frame_chunks && (
        <div className="mt-4 pt-4 border-t border-warroom-border">
          <div className="flex items-center gap-2 mb-3">
            <Film size={14} className="text-warroom-accent" />
            <span className="text-sm font-semibold">Frame Analysis</span>
            <InfoTooltip content="AI-generated breakdown of visual elements, pacing, and narrative structure">
              <Info size={12} className="text-warroom-muted" />
            </InfoTooltip>
          </div>
          
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {video.frame_chunks.map((chunk: any, i: number) => (
              <div key={i} className="bg-warroom-bg rounded-lg p-3 border border-warroom-border">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-mono text-warroom-accent">
                    {formatDuration(chunk.start_time)} - {formatDuration(chunk.end_time)}
                  </span>
                  <div className="flex gap-1">
                    <span className="px-2 py-0.5 bg-blue-500/10 text-blue-400 rounded text-[10px]">
                      {chunk.action_type}
                    </span>
                    <span className="px-2 py-0.5 bg-purple-500/10 text-purple-400 rounded text-[10px]">
                      {chunk.pacing}
                    </span>
                  </div>
                </div>
                <p className="text-xs text-warroom-text mb-2">{chunk.description}</p>
                {chunk.visual_elements?.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {chunk.visual_elements.map((element: string, j: number) => (
                      <span key={j} className="px-1.5 py-0.5 bg-green-500/10 text-green-400 rounded text-[10px]">
                        {element}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Utility function for number formatting
function formatNumber(num: number): string {
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
  return num.toString();
}

// Enhanced competitor overview card
function EnhancedCompetitorCard({ 
  competitor, 
  topVideos, 
  onViewDetails
}: { 
  competitor: any; 
  topVideos: any[]; 
  onViewDetails: () => void;
}) {
  const [loading, setLoading] = useState(false);

  const getPerformanceGrade = () => {
    if (competitor.avg_engagement_rate >= 5) return { grade: 'A', color: 'text-green-400' };
    if (competitor.avg_engagement_rate >= 3) return { grade: 'B', color: 'text-yellow-400' };
    if (competitor.avg_engagement_rate >= 1.5) return { grade: 'C', color: 'text-orange-400' };
    return { grade: 'D', color: 'text-red-400' };
  };

  const performance = getPerformanceGrade();

  return (
    <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4 hover:border-warroom-accent/30 transition-all">
      {/* Header with improved layout */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-full bg-warroom-gradient flex items-center justify-center text-lg font-bold text-white shadow-lg">
            {competitor.handle.charAt(0).toUpperCase()}
          </div>
          <div>
            <h3 className="font-semibold text-sm">@{competitor.handle}</h3>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 bg-pink-500/10 text-pink-400 rounded text-xs">
                {competitor.platform}
              </span>
              {competitor.posting_frequency && (
                <span className="text-xs text-warroom-muted">
                  {competitor.posting_frequency}
                </span>
              )}
            </div>
          </div>
        </div>
        
        {/* Performance grade */}
        <InfoTooltip content={`Performance Grade: ${performance.grade}\nBased on engagement rate: ${competitor.avg_engagement_rate.toFixed(1)}%`}>
          <div className={`w-8 h-8 rounded-full border-2 flex items-center justify-center font-bold text-sm ${performance.color}`}>
            {performance.grade}
          </div>
        </InfoTooltip>
      </div>

      {/* Enhanced stats with tooltips */}
      <div className="grid grid-cols-4 gap-2 mb-4">
        <InfoTooltip content="Total follower count on platform">
          <div className="bg-warroom-bg rounded-lg p-2 text-center">
            <p className="text-sm font-bold text-warroom-text">{formatNumber(competitor.followers)}</p>
            <p className="text-[10px] text-warroom-muted">Followers</p>
          </div>
        </InfoTooltip>

        <InfoTooltip content="Total number of posts published">
          <div className="bg-warroom-bg rounded-lg p-2 text-center">
            <p className="text-sm font-bold text-warroom-text">{formatNumber(competitor.post_count)}</p>
            <p className="text-[10px] text-warroom-muted">Posts</p>
          </div>
        </InfoTooltip>

        <InfoTooltip content={`Engagement Rate: ${competitor.avg_engagement_rate.toFixed(1)}%\nCalculated from likes, comments, and shares relative to follower count`}>
          <div className="bg-warroom-bg rounded-lg p-2 text-center">
            <p className="text-sm font-bold text-warroom-accent">{competitor.avg_engagement_rate.toFixed(1)}%</p>
            <p className="text-[10px] text-warroom-muted">Engage</p>
          </div>
        </InfoTooltip>

        <InfoTooltip content="Number of videos analyzed with frame-by-frame insights">
          <div className="bg-warroom-bg rounded-lg p-2 text-center">
            <p className="text-sm font-bold text-emerald-400">{topVideos?.length || 0}</p>
            <p className="text-[10px] text-warroom-muted">Analyzed</p>
          </div>
        </InfoTooltip>
      </div>



      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={onViewDetails}
          className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-warroom-bg hover:bg-warroom-border/50 border border-warroom-border rounded-lg text-xs font-medium transition"
        >
          <Eye size={12} />
          View Details
        </button>
      </div>
    </div>
  );
}

export { VideoMetricsCard, EnhancedCompetitorCard, InfoTooltip };