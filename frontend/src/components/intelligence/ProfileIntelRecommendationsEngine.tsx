"use client";

import { useState, useEffect } from "react";
import { 
  User, TrendingUp, Users, Target, Edit3, Trash2, ArrowRight, 
  Check, X, AlertTriangle, Star, Film, ChevronDown, ChevronRight,
  Crown, MessageCircle, Eye, BarChart3, RefreshCw, Play, Lightbulb,
  Brain, Zap, Clock, Award, TrendingDown
} from "lucide-react";
import { API, authFetch } from "@/lib/api";
import { useSocialAccounts } from "@/hooks/useSocialAccounts";

interface CategoryGrade {
  score: number;
  details: string;
}

interface VideoGrade {
  video_id: string;
  title?: string;
  grade: string; // Letter grade A-F
  strengths: string[];
  weaknesses: string[];
  engagement_score?: number;
  format_tags?: string[];
}

interface AudienceIntelligenceItem {
  text: string;
  frequency: number;
  usage_hint?: string;
  category?: string;
}

interface ProfileIntelData {
  profile_id: string;
  platform: string;
  last_synced_at?: string;
  oauth_data?: {
    followerCount?: number;
    followingCount?: number;
    postCount?: number;
    engagementRate?: number;
    replyRate?: number;
    avgReplyTime?: number;
    reachMetrics?: {
      avgDailyReach?: number;
      avgDailyImpressions?: number;
      totalDays?: number;
    };
    audienceDemographics?: {
      netFollowerGrowth?: number;
      totalProfileViews?: number;
      saveToShareRatio?: number;
    };
    topPerformingPosts?: any[];
  };
  scraped_data?: {
    bio?: string;
    profilePicUrl?: string;
    linkInBio?: string;
    postingFrequency?: string;
  };
  processed_videos?: VideoGrade[];
  grades?: {
    profileOptimization?: CategoryGrade;
    videoMessaging?: CategoryGrade;
    storyboarding?: CategoryGrade;
    audienceEngagement?: CategoryGrade;
    contentConsistency?: CategoryGrade;
    replyQuality?: CategoryGrade;
  };
  recommendations?: {
    keepDoing?: Array<{what: string, why: string, priority: string}>;
    stopDoing?: Array<{what: string, why: string, priority: string}>;
    profileChanges?: Array<{what: string, why: string, priority: string}>;
    contentRecommendations?: Array<{topic: string, reason: string, priority: string}>;
    videosToRemove?: Array<{video_id?: string, videoId?: string, title?: string, reason: string}>;
    nextSteps?: Array<{action: string, expected_impact?: string, expectedImpact?: string, priority: string}>;
  };
}

interface CompetitorBenchmarks {
  avg_engagement_rate: number;
  top_performer_engagement_rate: number;
  avg_hook_length_chars: number;
  avg_posting_frequency_per_week: number;
  total_posts_analyzed: number;
  total_competitors: number;
}

interface AudienceIntelligence {
  objections: AudienceIntelligenceItem[];
  desires: AudienceIntelligenceItem[];
  questions: AudienceIntelligenceItem[];
  emotional_triggers: AudienceIntelligenceItem[];
  competitor_gaps: AudienceIntelligenceItem[];
}

function getGradeColor(score: number): string {
  if (score >= 90) return "text-emerald-400";
  if (score >= 80) return "text-green-400";
  if (score >= 70) return "text-yellow-400";
  if (score >= 60) return "text-orange-400";
  return "text-red-400";
}

function getLetterGrade(score: number): string {
  if (score >= 90) return "A+";
  if (score >= 85) return "A";
  if (score >= 80) return "A-";
  if (score >= 75) return "B+";
  if (score >= 70) return "B";
  if (score >= 65) return "B-";
  if (score >= 60) return "C+";
  if (score >= 55) return "C";
  if (score >= 50) return "C-";
  if (score >= 45) return "D+";
  if (score >= 40) return "D";
  return "F";
}

function getPriorityColor(priority: string): string {
  switch (priority.toUpperCase()) {
    case 'HIGH': return 'bg-red-500/10 text-red-400 border-red-500/20';
    case 'MEDIUM': case 'MED': return 'bg-orange-500/10 text-orange-400 border-orange-500/20';
    case 'LOW': return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20';
    default: return 'bg-warroom-surface text-warroom-muted border-warroom-border';
  }
}

function isUnanalyzed(grade?: CategoryGrade): boolean {
  if (!grade) return true;
  return grade.score === 0 && (
    grade.details === "not_analyzed" || 
    grade.details.includes("Not yet analyzed") ||
    grade.details.includes("Connect Instagram") ||
    grade.details.includes("Connected account missing")
  );
}

function VideoGradeCard({ video, expanded, onToggle }: { 
  video: VideoGrade; 
  expanded: boolean; 
  onToggle: () => void;
}) {
  const letterGrade = getLetterGrade(video.engagement_score || 0);
  const gradeColor = getGradeColor(video.engagement_score || 0);
  
  // Handle titles
  const videoTitle = video.title && video.title !== "undefined" && video.title !== "Video undefined" 
    ? video.title 
    : "Analysis pending";

  // Determine if this is best/worst
  const isBest = video.grade === "A+" || video.grade === "A";
  const isWorst = video.grade === "D" || video.grade === "F";
  
  return (
    <div className={`bg-warroom-bg border rounded-lg ${
      isBest ? 'border-emerald-500/40 bg-emerald-500/5' : 
      isWorst ? 'border-red-500/40 bg-red-500/5' : 
      'border-warroom-border'
    }`}>
      <button 
        onClick={onToggle}
        className="w-full flex items-center justify-between p-3 text-left hover:bg-warroom-surface/50 transition"
      >
        <div className="flex items-center gap-3">
          <div className={`w-8 h-8 rounded-full bg-warroom-surface border border-warroom-border flex items-center justify-center text-sm font-bold ${gradeColor}`}>
            {letterGrade}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <p className="text-sm font-medium text-warroom-text">{videoTitle}</p>
              {isBest && <Award size={14} className="text-emerald-400" />}
              {isWorst && <TrendingDown size={14} className="text-red-400" />}
            </div>
            {video.format_tags && video.format_tags.length > 0 && (
              <div className="flex gap-1 mt-1">
                {video.format_tags.map((tag, i) => (
                  <span key={i} className="text-xs px-2 py-1 bg-warroom-surface rounded-full text-warroom-muted">
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
        {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
      </button>
      
      {expanded && (
        <div className="border-t border-warroom-border p-3 space-y-3">
          {video.strengths.length > 0 && (
            <div>
              <p className="text-xs font-medium text-emerald-400 mb-1">Strengths</p>
              <ul className="space-y-1">
                {video.strengths.map((strength, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-warroom-text">
                    <Check size={10} className="text-emerald-400 mt-0.5 flex-shrink-0" />
                    {strength}
                  </li>
                ))}
              </ul>
            </div>
          )}
          
          {video.weaknesses.length > 0 && (
            <div>
              <p className="text-xs font-medium text-red-400 mb-1">Areas for Improvement</p>
              <ul className="space-y-1">
                {video.weaknesses.map((weakness, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-warroom-text">
                    <X size={10} className="text-red-400 mt-0.5 flex-shrink-0" />
                    {weakness}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ProfileIntelRecommendationsEngine() {
  const [profileIntel, setProfileIntel] = useState<ProfileIntelData | null>(null);
  const [benchmarks, setBenchmarks] = useState<CompetitorBenchmarks | null>(null);
  const [audienceIntelligence, setAudienceIntelligence] = useState<AudienceIntelligence | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>("");
  const [expandedVideo, setExpandedVideo] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [analyzingVideos, setAnalyzingVideos] = useState(false);
  
  const { isConnected, connect } = useSocialAccounts();

  useEffect(() => {
    const fetchAllData = async () => {
      try {
        setLoading(true);
        setError("");
        
        // Fetch profile intel data
        const [profileResponse, benchmarksResponse, audienceResponse] = await Promise.all([
          authFetch(`${API}/api/content-intel/profile-intel`),
          authFetch(`${API}/api/content-intel/competitor-benchmarks`),
          authFetch(`${API}/api/content-intel/profile-intel/audience-intelligence`)
        ]);
        
        if (profileResponse.ok) {
          const profileData = await profileResponse.json();
          setProfileIntel(profileData);
        } else if (profileResponse.status === 404) {
          setError("Profile intel data not available.");
        }

        if (benchmarksResponse.ok) {
          const benchmarksData = await benchmarksResponse.json();
          setBenchmarks(benchmarksData.benchmarks?.engagement_metrics || null);
        }

        if (audienceResponse.ok) {
          const audienceData = await audienceResponse.json();
          if (audienceData.success) {
            setAudienceIntelligence(audienceData.audience_intelligence || null);
          }
        }
        
      } catch (err) {
        setError("Error connecting to intelligence service.");
      } finally {
        setLoading(false);
      }
    };

    fetchAllData();
  }, []);

  const handleRefresh = async () => {
    try {
      setRefreshing(true);
      const response = await authFetch(`${API}/api/content-intel/profile-intel`, {
        method: 'GET'
      });
      
      if (response.ok) {
        const data = await response.json();
        setProfileIntel(data);
      } else {
        setError("Failed to refresh profile intel data.");
      }
    } catch (err) {
      setError("Error refreshing profile data.");
    } finally {
      setRefreshing(false);
    }
  };

  const handleAnalyzeVideos = async () => {
    try {
      setAnalyzingVideos(true);
      const response = await authFetch(`${API}/api/content-intel/profile-intel/analyze-videos`, {
        method: 'POST'
      });
      
      if (response.ok) {
        // Video analysis started in background
        setTimeout(() => {
          handleRefresh(); // Refresh data after analysis should be complete
        }, 30000); // 30 seconds
      } else {
        setError("Failed to start video analysis.");
      }
    } catch (err) {
      setError("Error starting video analysis.");
    } finally {
      setAnalyzingVideos(false);
    }
  };

  if (loading) {
    return (
      <div className="text-center py-16">
        <div className="text-center py-16 space-y-6 max-w-md mx-auto">
          {/* Loading Structure Instead of Loader */}
          <div className="space-y-4">
            <div className="bg-warroom-surface border border-warroom-border rounded-2xl p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 rounded-xl bg-warroom-bg animate-pulse" />
                <div className="space-y-2 flex-1">
                  <div className="h-4 bg-warroom-bg animate-pulse rounded w-3/4" />
                  <div className="h-3 bg-warroom-bg animate-pulse rounded w-1/2" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <div className="h-3 bg-warroom-bg animate-pulse rounded" />
                  <div className="h-2 bg-warroom-bg animate-pulse rounded w-full" />
                </div>
                <div className="space-y-2">
                  <div className="h-3 bg-warroom-bg animate-pulse rounded" />
                  <div className="h-2 bg-warroom-bg animate-pulse rounded w-full" />
                </div>
              </div>
            </div>
            <p className="text-sm text-warroom-text">Building your profile intelligence report...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-16">
        <AlertTriangle size={32} className="mx-auto mb-4 text-orange-400" />
        <p className="text-sm text-orange-400 mb-4">{error}</p>
        <div className="space-y-4">
          <p className="text-sm text-warroom-muted">Connect your Instagram account to begin analysis</p>
          <button 
            onClick={() => connect('instagram')}
            className="px-6 py-3 bg-warroom-accent hover:bg-warroom-accent/80 text-black rounded-lg font-medium transition"
          >
            Connect Instagram Account
          </button>
        </div>
      </div>
    );
  }

  if (!profileIntel) {
    return (
      <div className="text-center py-16">
        <User size={32} className="mx-auto mb-4 text-warroom-muted opacity-50" />
        <p className="text-sm text-warroom-muted mb-4">No profile intelligence data available</p>
      </div>
    );
  }

  // Check if we have real OAuth data (indicating connected account)
  const hasOAuthData = profileIntel.oauth_data && Object.keys(profileIntel.oauth_data).length > 0;
  const isProfileConnected = hasOAuthData;

  // If we have the profile intel response but no OAuth data, show connect prompt
  if (!isProfileConnected) {
    return (
      <div className="text-center py-16">
        <User size={32} className="mx-auto mb-4 text-warroom-muted opacity-50" />
        <p className="text-sm text-warroom-muted mb-4">Connect your Instagram account to get started</p>
        <button 
          onClick={() => connect('instagram')}
          className="px-6 py-3 bg-warroom-accent hover:bg-warroom-accent/80 text-black rounded-lg font-medium transition"
        >
          Connect Instagram Account
        </button>
      </div>
    );
  }

  // Calculate overall score only from analyzed categories
  const analyzedGrades = Object.values(profileIntel.grades || {}).filter(grade => !isUnanalyzed(grade));
  const overallScore = analyzedGrades.length > 0 
    ? Math.round(analyzedGrades.reduce((sum, grade) => sum + (grade?.score || 0), 0) / analyzedGrades.length) 
    : 0;

  const totalCategories = Object.keys(profileIntel.grades || {}).length;
  const analyzedCategories = analyzedGrades.length;

  return (
    <div className="space-y-8">
      {/* Control Bar */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-semibold text-warroom-text">Profile Intelligence</h3>
            {isProfileConnected && (
              <div className="flex items-center gap-1 px-2 py-1 bg-emerald-500/10 border border-emerald-500/20 rounded-full">
                <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></div>
                <span className="text-xs text-emerald-400">Connected</span>
              </div>
            )}
          </div>
          {profileIntel.last_synced_at ? (
            <p className="text-xs text-warroom-muted">
              Last updated: {new Date(profileIntel.last_synced_at).toLocaleDateString()}
              {isProfileConnected && profileIntel.oauth_data?.followerCount && (
                <span> • {profileIntel.oauth_data.followerCount.toLocaleString()} followers</span>
              )}
            </p>
          ) : (
            isProfileConnected && profileIntel.oauth_data?.followerCount && (
              <p className="text-xs text-warroom-muted">
                {profileIntel.oauth_data.followerCount.toLocaleString()} followers
              </p>
            )
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleAnalyzeVideos}
            disabled={analyzingVideos}
            className="flex items-center gap-2 px-4 py-2 bg-purple-500/20 hover:bg-purple-500/30 disabled:opacity-50 text-purple-400 rounded-lg text-sm font-medium transition"
          >
            {analyzingVideos ? <RefreshCw size={16} className="animate-spin" /> : <Play size={16} />}
            {analyzingVideos ? 'Analyzing Videos...' : 'Analyze My Videos'}
          </button>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 disabled:opacity-50 text-black rounded-lg text-sm font-medium transition"
          >
            {refreshing ? <RefreshCw size={16} className="animate-spin" /> : <Eye size={16} />}
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* 1. OVERALL GRADE */}
      <section className="bg-warroom-surface border border-warroom-border rounded-2xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-warroom-accent/20 to-purple-500/20 flex items-center justify-center">
            <Crown size={24} className="text-warroom-accent" />
          </div>
          <div className="flex-1">
            <h4 className="text-xl font-bold text-warroom-text">Overall Grade</h4>
            <p className="text-sm text-warroom-muted">
              {isProfileConnected 
                ? `@${profileIntel.profile_id} • Based on ${analyzedCategories} of ${totalCategories} categories`
                : `Based on ${analyzedCategories} of ${totalCategories} categories`
              }
            </p>
          </div>
          <div className="text-right">
            <div className={`text-4xl font-bold ${getGradeColor(overallScore)}`}>
              {getLetterGrade(overallScore)}
            </div>
            <div className="flex items-center gap-1 text-xs text-warroom-muted">
              <TrendingUp size={12} className="text-emerald-400" />
              <span>Improving</span>
            </div>
          </div>
        </div>

        {overallScore > 0 && (
          <div className="bg-warroom-bg border border-warroom-border rounded-lg p-4">
            <p className="text-sm text-warroom-text">
              {overallScore >= 85 
                ? "Excellent profile performance — you're outperforming most creators in your niche."
                : overallScore >= 70 
                ? "Strong foundation with clear improvement opportunities identified below."
                : overallScore >= 60
                ? "Good potential with several optimization areas that could significantly boost your reach."
                : "Significant opportunity to optimize your profile for better audience engagement and growth."
              }
            </p>
          </div>
        )}
      </section>

      {/* 2. PROFILE OPTIMIZATION */}
      {profileIntel.grades?.profileOptimization && !isUnanalyzed(profileIntel.grades.profileOptimization) && (
        <section className="bg-warroom-surface border border-warroom-border rounded-2xl p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500/20 to-pink-500/20 flex items-center justify-center">
              <Edit3 size={20} className="text-purple-400" />
            </div>
            <div>
              <h4 className="text-lg font-semibold text-warroom-text">Profile Optimization</h4>
              <p className="text-xs text-warroom-muted">Bio, link, highlights, and visual consistency</p>
            </div>
            <div className="ml-auto">
              <div className={`text-2xl font-bold ${getGradeColor(profileIntel.grades.profileOptimization.score)}`}>
                {profileIntel.grades.profileOptimization.score}/100
              </div>
            </div>
          </div>

          {profileIntel.recommendations?.profileChanges && profileIntel.recommendations.profileChanges.length > 0 && (
            <div className="space-y-3">
              {profileIntel.recommendations.profileChanges.map((change, idx) => (
                <div key={idx} className="border border-warroom-border rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-purple-500/20 flex items-center justify-center mt-0.5">
                      <Edit3 size={12} className="text-purple-400" />
                    </div>
                    <div className="flex-1">
                      <h5 className="text-sm font-semibold text-warroom-text mb-1">{change.what}</h5>
                      <p className="text-xs text-warroom-muted mb-2">{change.why}</p>
                      <span className={`text-xs px-2 py-1 rounded-full ${getPriorityColor(change.priority)}`}>
                        {change.priority.toUpperCase()}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* 3. VIDEO GRADES */}
      <section className="bg-warroom-surface border border-warroom-border rounded-2xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-pink-500/20 to-purple-500/20 flex items-center justify-center">
            <Film size={20} className="text-pink-400" />
          </div>
          <div className="flex-1">
            <h4 className="text-lg font-semibold text-warroom-text">Video Grades</h4>
            <p className="text-xs text-warroom-muted">
              {profileIntel.processed_videos && profileIntel.processed_videos.length > 0 
                ? `Analysis of your last ${profileIntel.processed_videos.length} videos`
                : "No videos analyzed yet"
              }
            </p>
          </div>
        </div>

        {profileIntel.processed_videos && profileIntel.processed_videos.length > 0 ? (
          <div className="space-y-3">
            {profileIntel.processed_videos.map((video, idx) => (
              <VideoGradeCard
                key={video.video_id || idx}
                video={video}
                expanded={expandedVideo === video.video_id}
                onToggle={() => setExpandedVideo(expandedVideo === video.video_id ? null : video.video_id)}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-8 border border-warroom-border rounded-lg">
            <Film size={32} className="mx-auto mb-3 opacity-30 text-warroom-muted" />
            <p className="text-sm text-warroom-text mb-2">No videos analyzed</p>
            <p className="text-xs text-warroom-muted mb-4">Click "Analyze My Videos" to start frame-by-frame analysis</p>
            <button
              onClick={handleAnalyzeVideos}
              disabled={analyzingVideos}
              className="px-4 py-2 bg-purple-500/20 hover:bg-purple-500/30 text-purple-400 rounded-lg text-sm transition"
            >
              {analyzingVideos ? 'Analyzing...' : 'Analyze My Videos'}
            </button>
          </div>
        )}
      </section>

      {/* 4. AUDIENCE INTELLIGENCE (NEW SECTION) */}
      {audienceIntelligence && (
        <section className="bg-warroom-surface border border-warroom-border rounded-2xl p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500/20 to-cyan-500/20 flex items-center justify-center">
              <Brain size={20} className="text-blue-400" />
            </div>
            <div>
              <h4 className="text-lg font-semibold text-warroom-text">Audience Intelligence</h4>
              <p className="text-xs text-warroom-muted">What YOUR audience wants, resists, and asks for</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Objections */}
            {audienceIntelligence.objections.length > 0 && (
              <div className="space-y-3">
                <h5 className="text-sm font-semibold text-red-400 flex items-center gap-2">
                  <X size={14} />
                  Common Objections
                </h5>
                {audienceIntelligence.objections.slice(0, 3).map((objection, idx) => (
                  <div key={idx} className="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
                    <p className="text-sm text-warroom-text mb-1">"{objection.text}"</p>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-red-400">{objection.frequency} mentions</span>
                      {objection.usage_hint && (
                        <span className="text-xs text-warroom-muted">{objection.usage_hint}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Desires */}
            {audienceIntelligence.desires.length > 0 && (
              <div className="space-y-3">
                <h5 className="text-sm font-semibold text-emerald-400 flex items-center gap-2">
                  <Star size={14} />
                  What They Want
                </h5>
                {audienceIntelligence.desires.slice(0, 3).map((desire, idx) => (
                  <div key={idx} className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3">
                    <p className="text-sm text-warroom-text mb-1">"{desire.text}"</p>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-emerald-400">{desire.frequency} mentions</span>
                      {desire.usage_hint && (
                        <span className="text-xs text-warroom-muted">{desire.usage_hint}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Questions */}
            {audienceIntelligence.questions.length > 0 && (
              <div className="space-y-3 md:col-span-2">
                <h5 className="text-sm font-semibold text-blue-400 flex items-center gap-2">
                  <MessageCircle size={14} />
                  Frequent Questions
                </h5>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {audienceIntelligence.questions.slice(0, 4).map((question, idx) => (
                    <div key={idx} className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
                      <p className="text-sm text-warroom-text mb-1">"{question.text}"</p>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-blue-400">{question.frequency} mentions</span>
                        {question.usage_hint && (
                          <span className="text-xs text-warroom-muted">{question.usage_hint}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>
      )}

      {/* 5. ENGAGEMENT ANALYSIS */}
      <section className="bg-warroom-surface border border-warroom-border rounded-2xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500/20 to-cyan-500/20 flex items-center justify-center">
            <Users size={20} className="text-blue-400" />
          </div>
          <div>
            <h4 className="text-lg font-semibold text-warroom-text">Engagement Analysis</h4>
            <p className="text-xs text-warroom-muted">Your performance vs. competitor benchmarks</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-warroom-bg border border-warroom-border rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-blue-400 mb-1">
              {profileIntel.oauth_data?.replyRate !== undefined
                ? `${profileIntel.oauth_data.replyRate.toFixed(1)}%`
                : 'N/A'
              }
            </div>
            <p className="text-xs text-warroom-muted mb-1">Reply Rate</p>
            <p className="text-xs text-blue-400">
              {benchmarks && profileIntel.oauth_data?.replyRate !== undefined
                ? `Competitor avg: ${(benchmarks.avg_engagement_rate * 100).toFixed(1)}%`
                : 'Connect for comparison'
              }
            </p>
          </div>
          
          <div className="bg-warroom-bg border border-warroom-border rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-emerald-400 mb-1">
              {profileIntel.oauth_data?.engagementRate !== undefined
                ? `${profileIntel.oauth_data.engagementRate.toFixed(1)}%`
                : 'N/A'
              }
            </div>
            <p className="text-xs text-warroom-muted mb-1">Engagement Rate</p>
            <p className="text-xs text-emerald-400">
              {benchmarks && profileIntel.oauth_data?.engagementRate !== undefined
                ? `${profileIntel.oauth_data.engagementRate >= benchmarks.avg_engagement_rate ? 'Above' : 'Below'} average`
                : 'Connect for comparison'
              }
            </p>
          </div>
          
          <div className="bg-warroom-bg border border-warroom-border rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-purple-400 mb-1">
              {profileIntel.oauth_data?.followerCount !== undefined 
                ? profileIntel.oauth_data.followerCount.toLocaleString()
                : 'N/A'
              }
            </div>
            <p className="text-xs text-warroom-muted mb-1">Followers</p>
            <p className="text-xs text-purple-400">
              {profileIntel.oauth_data?.audienceDemographics?.netFollowerGrowth 
                ? `${profileIntel.oauth_data.audienceDemographics.netFollowerGrowth > 0 ? '+' : ''}${profileIntel.oauth_data.audienceDemographics.netFollowerGrowth} last 30 days`
                : 'Current audience size'
              }
            </p>
          </div>
        </div>
      </section>

      {/* 6. COMPETITIVE POSITIONING */}
      {benchmarks && (
        <section className="bg-warroom-surface border border-warroom-border rounded-2xl p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500/20 to-red-500/20 flex items-center justify-center">
              <BarChart3 size={20} className="text-orange-400" />
            </div>
            <div>
              <h4 className="text-lg font-semibold text-warroom-text">Competitive Positioning</h4>
              <p className="text-xs text-warroom-muted">
                Based on {benchmarks.total_posts_analyzed} posts from {benchmarks.total_competitors} competitors
              </p>
            </div>
          </div>

          <div className="bg-warroom-bg border border-warroom-border rounded-lg p-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-warroom-muted">Market avg engagement:</span>
                <span className="ml-2 font-medium text-warroom-text">
                  {(benchmarks.avg_engagement_rate * 100).toFixed(1)}%
                </span>
              </div>
              <div>
                <span className="text-warroom-muted">Top performers:</span>
                <span className="ml-2 font-medium text-warroom-text">
                  {(benchmarks.top_performer_engagement_rate * 100).toFixed(1)}%
                </span>
              </div>
              <div>
                <span className="text-warroom-muted">Avg posting:</span>
                <span className="ml-2 font-medium text-warroom-text">
                  {benchmarks.avg_posting_frequency_per_week.toFixed(1)}x/week
                </span>
              </div>
              <div>
                <span className="text-warroom-muted">Hook length:</span>
                <span className="ml-2 font-medium text-warroom-text">
                  {benchmarks.avg_hook_length_chars} chars
                </span>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* 7. WHAT'S WORKING */}
      <section className="bg-warroom-surface border border-warroom-border rounded-2xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-emerald-500/20 to-green-500/20 flex items-center justify-center">
            <TrendingUp size={20} className="text-emerald-400" />
          </div>
          <div>
            <h4 className="text-lg font-semibold text-warroom-text">What's Working</h4>
            <p className="text-xs text-warroom-muted">Double down on these strengths</p>
          </div>
        </div>

        {profileIntel.recommendations?.keepDoing && profileIntel.recommendations.keepDoing.length > 0 ? (
          <div className="space-y-4">
            {profileIntel.recommendations.keepDoing.map((item, idx) => (
              <div key={idx} className="bg-emerald-500/5 border border-emerald-500/20 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <div className="w-6 h-6 rounded-full bg-emerald-500/20 flex items-center justify-center mt-0.5">
                    <Check size={12} className="text-emerald-400" />
                  </div>
                  <div className="flex-1">
                    <h5 className="text-sm font-semibold text-warroom-text mb-1">{item.what}</h5>
                    <p className="text-xs text-warroom-muted">{item.why}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-warroom-muted">
            <TrendingUp size={32} className="mx-auto mb-3 opacity-30" />
            <p className="text-sm">Building performance insights</p>
            <p className="text-xs mt-1">Positive patterns will appear as data is collected</p>
          </div>
        )}
      </section>

      {/* 8. WHAT TO IMPROVE */}
      <section className="bg-warroom-surface border border-warroom-border rounded-2xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500/20 to-red-500/20 flex items-center justify-center">
            <Target size={20} className="text-orange-400" />
          </div>
          <div>
            <h4 className="text-lg font-semibold text-warroom-text">What to Improve</h4>
            <p className="text-xs text-warroom-muted">Prioritized opportunities for growth</p>
          </div>
        </div>

        {profileIntel.recommendations?.stopDoing && profileIntel.recommendations.stopDoing.length > 0 ? (
          <div className="space-y-3">
            {profileIntel.recommendations.stopDoing.map((item, idx) => (
              <div key={idx} className={`border rounded-lg p-4 ${getPriorityColor(item.priority)}`}>
                <div className="flex items-start gap-3">
                  <span className={`text-xs font-bold px-2 py-1 rounded-full ${getPriorityColor(item.priority)}`}>
                    {item.priority.toUpperCase()}
                  </span>
                  <div className="flex-1">
                    <h5 className="text-sm font-semibold text-warroom-text mb-1">{item.what}</h5>
                    <p className="text-xs text-warroom-muted">{item.why}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-warroom-muted">
            <Target size={32} className="mx-auto mb-3 opacity-30" />
            <p className="text-sm">Identifying improvement opportunities</p>
            <p className="text-xs mt-1">Recommendations will appear after analysis</p>
          </div>
        )}
      </section>

      {/* 9. CONTENT RECOMMENDATIONS (NEW) */}
      <section className="bg-warroom-surface border border-warroom-border rounded-2xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-yellow-500/20 to-orange-500/20 flex items-center justify-center">
            <Lightbulb size={20} className="text-yellow-400" />
          </div>
          <div>
            <h4 className="text-lg font-semibold text-warroom-text">Content Recommendations</h4>
            <p className="text-xs text-warroom-muted">Create Next — based on audience demand</p>
          </div>
        </div>

        {profileIntel.recommendations?.contentRecommendations && profileIntel.recommendations.contentRecommendations.length > 0 ? (
          <div className="space-y-3">
            {profileIntel.recommendations.contentRecommendations.map((rec, idx) => (
              <div key={idx} className="bg-yellow-500/5 border border-yellow-500/20 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <div className="w-6 h-6 rounded-full bg-yellow-500/20 flex items-center justify-center mt-0.5">
                    <Lightbulb size={12} className="text-yellow-400" />
                  </div>
                  <div className="flex-1">
                    <h5 className="text-sm font-semibold text-warroom-text mb-1">{rec.topic}</h5>
                    <p className="text-xs text-warroom-muted mb-2">{rec.reason}</p>
                    <span className={`text-xs px-2 py-1 rounded-full ${getPriorityColor(rec.priority)}`}>
                      {rec.priority.toUpperCase()}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-warroom-muted">
            <Lightbulb size={32} className="mx-auto mb-3 opacity-30" />
            <p className="text-sm">Analyzing audience demand</p>
            <p className="text-xs mt-1">Content ideas will appear based on your audience intelligence</p>
          </div>
        )}
      </section>

      {/* 10. VIDEOS TO CONSIDER REMOVING */}
      <section className="bg-warroom-surface border border-warroom-border rounded-2xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-red-500/20 to-orange-500/20 flex items-center justify-center">
            <Trash2 size={20} className="text-red-400" />
          </div>
          <div>
            <h4 className="text-lg font-semibold text-warroom-text">Videos to Consider Removing</h4>
            <p className="text-xs text-warroom-muted">Underperforming content that may hurt your reach</p>
          </div>
        </div>

        {profileIntel.recommendations?.videosToRemove && profileIntel.recommendations.videosToRemove.length > 0 ? (
          <div className="space-y-3">
            {profileIntel.recommendations.videosToRemove.map((video, idx) => (
              <div key={idx} className="bg-red-500/5 border border-red-500/20 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <div className="w-6 h-6 rounded-full bg-red-500/20 flex items-center justify-center mt-0.5">
                    <Trash2 size={12} className="text-red-400" />
                  </div>
                  <div className="flex-1">
                    <h5 className="text-sm font-semibold text-warroom-text mb-1">
                      {video.title || `Video ${video.videoId || video.video_id}`}
                    </h5>
                    <p className="text-xs text-warroom-muted">{video.reason}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-warroom-muted">
            <Trash2 size={32} className="mx-auto mb-3 opacity-30" />
            <p className="text-sm">No videos recommended for removal</p>
            <p className="text-xs mt-1">All analyzed content is performing adequately</p>
          </div>
        )}
      </section>

      {/* 11. NEXT STEPS */}
      <section className="bg-warroom-surface border border-warroom-border rounded-2xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-emerald-500/20 to-blue-500/20 flex items-center justify-center">
            <ArrowRight size={20} className="text-emerald-400" />
          </div>
          <div>
            <h4 className="text-lg font-semibold text-warroom-text">Next Steps</h4>
            <p className="text-xs text-warroom-muted">Top 5 actions for maximum impact</p>
          </div>
        </div>

        {profileIntel.recommendations?.nextSteps && profileIntel.recommendations.nextSteps.length > 0 ? (
          <div className="space-y-4">
            {profileIntel.recommendations.nextSteps.slice(0, 5).map((step, idx) => (
              <div key={idx} className="bg-emerald-500/5 border border-emerald-500/20 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center mt-0.5">
                    <span className="text-xs font-bold text-emerald-400">{idx + 1}</span>
                  </div>
                  <div className="flex-1">
                    <h5 className="text-sm font-semibold text-warroom-text mb-1">{step.action}</h5>
                    <p className="text-xs text-warroom-muted mb-2">
                      Impact: {step.expected_impact || step.expectedImpact || "Positive improvement expected"}
                    </p>
                    <div className="flex items-center justify-between">
                      <span className={`text-xs px-2 py-1 rounded-full ${getPriorityColor(step.priority)}`}>
                        {step.priority.toUpperCase()}
                      </span>
                      <div className="flex items-center gap-1 text-xs text-warroom-muted">
                        <Clock size={10} />
                        <span>~15 min</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-warroom-muted">
            <ArrowRight size={32} className="mx-auto mb-3 opacity-30" />
            <p className="text-sm">Building action plan</p>
            <p className="text-xs mt-1">Personalized next steps will appear after analysis</p>
          </div>
        )}
      </section>
    </div>
  );
}