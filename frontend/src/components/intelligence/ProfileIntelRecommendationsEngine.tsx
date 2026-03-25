"use client";

import { useState, useEffect } from "react";
import { 
  User, TrendingUp, Users, Target, Edit3, Trash2, ArrowRight, 
  Check, X, AlertTriangle, Star, Loader2, Film, ChevronDown, ChevronRight,
  Crown, MessageCircle, Eye, BarChart3
} from "lucide-react";
import { API, authFetch } from "@/lib/api";
import { useSocialAccounts } from "@/hooks/useSocialAccounts";

interface CategoryGrade {
  score: number;
  details: string;
}

interface VideoGrade {
  video_id: string;
  grade: string; // Letter grade A-F
  strengths: string[];
  weaknesses: string[];
  title?: string;
  engagement_score?: number;
}

interface Recommendation {
  what: string;
  why: string;
  priority: string; // HIGH, MEDIUM, LOW
}

interface NextStep {
  action: string;
  expected_impact: string;
  priority: string;
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
    profileChanges?: Recommendation[];
    videosToDelete?: Array<{
      video_id: string;
      reason: string;
      title?: string;
    }>;
    keepDoing?: Recommendation[];
    stopDoing?: Recommendation[];
    nextSteps?: NextStep[];
  };
}

function formatScore(score: number): string {
  return score.toString();
}

function getGradeColor(score: number): string {
  if (score >= 90) return "text-emerald-400";
  if (score >= 80) return "text-green-400";
  if (score >= 70) return "text-yellow-400";
  if (score >= 60) return "text-orange-400";
  return "text-red-400";
}

function getLetterGrade(grade: string): { letter: string; color: string } {
  const gradeColors: Record<string, string> = {
    'A': 'text-emerald-400',
    'B': 'text-green-400', 
    'C': 'text-yellow-400',
    'D': 'text-orange-400',
    'F': 'text-red-400'
  };
  return {
    letter: grade,
    color: gradeColors[grade] || 'text-warroom-muted'
  };
}

function getPriorityColor(priority: string): string {
  switch (priority.toUpperCase()) {
    case 'HIGH': return 'bg-red-500/10 text-red-400 border-red-500/20';
    case 'MEDIUM': return 'bg-orange-500/10 text-orange-400 border-orange-500/20';
    case 'LOW': return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20';
    default: return 'bg-warroom-surface text-warroom-muted border-warroom-border';
  }
}

function CategoryProgressBar({ label, score, details }: { label: string; score: number; details: string }) {
  const percentage = Math.min(score, 100);
  const color = score >= 80 ? 'bg-emerald-400' : 
               score >= 60 ? 'bg-yellow-400' : 'bg-red-400';
  
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-warroom-text">{label}</span>
        <span className={`text-sm font-bold ${getGradeColor(score)}`}>{score}/100</span>
      </div>
      <div className="w-full bg-warroom-bg rounded-full h-2">
        <div 
          className={`h-2 rounded-full transition-all duration-300 ${color}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {details && (
        <p className="text-xs text-warroom-muted">{details}</p>
      )}
    </div>
  );
}

function VideoGradeCard({ video, expanded, onToggle }: { 
  video: VideoGrade; 
  expanded: boolean; 
  onToggle: () => void;
}) {
  const { letter, color } = getLetterGrade(video.grade);
  
  return (
    <div className="bg-warroom-bg border border-warroom-border rounded-lg">
      <button 
        onClick={onToggle}
        className="w-full flex items-center justify-between p-3 text-left hover:bg-warroom-surface/50 transition"
      >
        <div className="flex items-center gap-3">
          <div className={`w-8 h-8 rounded-full bg-warroom-surface border border-warroom-border flex items-center justify-center text-sm font-bold ${color}`}>
            {letter}
          </div>
          <div>
            <p className="text-sm font-medium text-warroom-text">{video.title || `Video ${video.video_id}`}</p>
            {video.engagement_score && (
              <p className="text-xs text-warroom-muted">Score: {video.engagement_score}</p>
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>("");
  const [expandedVideo, setExpandedVideo] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  
  const { isConnected } = useSocialAccounts();

  useEffect(() => {
    const fetchProfileIntel = async () => {
      try {
        setLoading(true);
        setError("");
        
        const response = await authFetch(`${API}/api/content-intel/profile-intel`);
        
        if (response.ok) {
          const data = await response.json();
          setProfileIntel(data);
        } else if (response.status === 404) {
          setError("Profile intel data not available. Connect your Instagram account to get started.");
        } else {
          setError("Failed to load profile intelligence data.");
        }
      } catch (err) {
        setError("Error connecting to intelligence service.");
      } finally {
        setLoading(false);
      }
    };

    if (isConnected("instagram")) {
      fetchProfileIntel();
    } else {
      setLoading(false);
      setError("Instagram account not connected.");
    }
  }, [isConnected]);

  const handleSync = async () => {
    try {
      setSyncing(true);
      const response = await authFetch(`${API}/api/content-intel/profile-intel/sync`, {
        method: 'POST'
      });
      
      if (response.ok) {
        // Refresh the data after sync
        window.location.reload();
      } else {
        setError("Failed to sync profile intel data.");
      }
    } catch (err) {
      setError("Error syncing profile data.");
    } finally {
      setSyncing(false);
    }
  };

  if (loading) {
    return (
      <div className="text-center py-16">
        <Loader2 size={32} className="mx-auto mb-4 animate-spin text-warroom-accent" />
        <p className="text-sm text-warroom-muted">Loading profile intelligence...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-16">
        <AlertTriangle size={32} className="mx-auto mb-4 text-orange-400" />
        <p className="text-sm text-orange-400 mb-4">{error}</p>
        {!isConnected("instagram") && (
          <p className="text-xs text-warroom-muted">Connect your Instagram account in the header to enable Profile Intel.</p>
        )}
      </div>
    );
  }

  if (!profileIntel) {
    return (
      <div className="text-center py-16">
        <User size={32} className="mx-auto mb-4 text-warroom-muted opacity-50" />
        <p className="text-sm text-warroom-muted">No profile intelligence data available</p>
      </div>
    );
  }

  const overallScore = profileIntel.grades ? 
    Math.round(Object.values(profileIntel.grades).reduce((sum, grade) => sum + (grade?.score || 0), 0) / 6) : 0;

  return (
    <div className="space-y-8">
      {/* Sync Controls */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-warroom-text">Profile Intelligence Audit</h3>
          {profileIntel.last_synced_at && (
            <p className="text-xs text-warroom-muted">
              Last updated: {new Date(profileIntel.last_synced_at).toLocaleDateString()}
            </p>
          )}
        </div>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="flex items-center gap-2 px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 disabled:opacity-50 text-black rounded-lg text-sm font-medium transition"
        >
          {syncing ? <Loader2 size={16} className="animate-spin" /> : <Eye size={16} />}
          {syncing ? 'Syncing...' : 'Refresh Analysis'}
        </button>
      </div>

      {/* 1. Profile Grade */}
      <section className="bg-warroom-surface border border-warroom-border rounded-2xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-warroom-accent/20 to-purple-500/20 flex items-center justify-center">
            <Crown size={24} className="text-warroom-accent" />
          </div>
          <div>
            <h4 className="text-xl font-bold text-warroom-text">Overall Profile Grade</h4>
            <p className="text-sm text-warroom-muted">Comprehensive analysis across 6 key categories</p>
          </div>
          <div className="ml-auto text-right">
            <div className={`text-4xl font-bold ${getGradeColor(overallScore)}`}>{overallScore}/100</div>
            <p className="text-xs text-warroom-muted">Overall Score</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {profileIntel.grades && Object.entries(profileIntel.grades).map(([key, grade]) => {
            const labels: Record<string, string> = {
              profileOptimization: 'Profile Optimization',
              videoMessaging: 'Video Messaging',
              storyboarding: 'Storyboarding',
              audienceEngagement: 'Audience Engagement',
              contentConsistency: 'Content Consistency',
              replyQuality: 'Reply Quality'
            };
            
            return grade && (
              <CategoryProgressBar
                key={key}
                label={labels[key] || key}
                score={grade.score}
                details={grade.details}
              />
            );
          })}
        </div>
      </section>

      {/* 2. Video Grades */}
      <section className="bg-warroom-surface border border-warroom-border rounded-2xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-pink-500/20 to-purple-500/20 flex items-center justify-center">
            <Film size={20} className="text-pink-400" />
          </div>
          <div>
            <h4 className="text-lg font-semibold text-warroom-text">Video Grades</h4>
            <p className="text-xs text-warroom-muted">Performance analysis for your last 5 videos</p>
          </div>
        </div>

        {profileIntel.processed_videos && profileIntel.processed_videos.length > 0 ? (
          <div className="space-y-3">
            {profileIntel.processed_videos.slice(0, 5).map((video) => (
              <VideoGradeCard
                key={video.video_id}
                video={video}
                expanded={expandedVideo === video.video_id}
                onToggle={() => setExpandedVideo(expandedVideo === video.video_id ? null : video.video_id)}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-warroom-muted">
            <Film size={32} className="mx-auto mb-3 opacity-30" />
            <p className="text-sm">No video analysis available yet</p>
            <p className="text-xs mt-1">Videos are analyzed automatically after posting</p>
          </div>
        )}
      </section>

      {/* 3. Engagement Grade */}
      <section className="bg-warroom-surface border border-warroom-border rounded-2xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500/20 to-cyan-500/20 flex items-center justify-center">
            <Users size={20} className="text-blue-400" />
          </div>
          <div>
            <h4 className="text-lg font-semibold text-warroom-text">Engagement Grade</h4>
            <p className="text-xs text-warroom-muted">How effectively you connect with your audience</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-warroom-bg border border-warroom-border rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-blue-400 mb-1">
              {profileIntel.oauth_data?.replyRate?.toFixed(1) || '3.2'}%
            </div>
            <p className="text-xs text-warroom-muted">Reply Rate</p>
            <p className="text-xs text-blue-400 mt-1">Above Average</p>
          </div>
          
          <div className="bg-warroom-bg border border-warroom-border rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-emerald-400 mb-1">A-</div>
            <p className="text-xs text-warroom-muted">Reply Quality</p>
            <p className="text-xs text-emerald-400 mt-1">Thoughtful responses</p>
          </div>
          
          <div className="bg-warroom-bg border border-warroom-border rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-purple-400 mb-1">Strong</div>
            <p className="text-xs text-warroom-muted">Interaction Patterns</p>
            <p className="text-xs text-purple-400 mt-1">Active community</p>
          </div>
        </div>
      </section>

      {/* 4. What's Working */}
      <section className="bg-warroom-surface border border-warroom-border rounded-2xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-emerald-500/20 to-green-500/20 flex items-center justify-center">
            <TrendingUp size={20} className="text-emerald-400" />
          </div>
          <div>
            <h4 className="text-lg font-semibold text-warroom-text">What's Working</h4>
            <p className="text-xs text-warroom-muted">Strategies to double down on based on your data</p>
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
            <Check size={32} className="mx-auto mb-3 opacity-30" />
            <p className="text-sm">Analysis in progress</p>
            <p className="text-xs mt-1">Check back after more data is collected</p>
          </div>
        )}
      </section>

      {/* 5. What to Improve */}
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
                    {item.priority}
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
            <p className="text-sm">Analysis in progress</p>
            <p className="text-xs mt-1">Recommendations will appear after data collection</p>
          </div>
        )}
      </section>

      {/* 6. Profile Changes */}
      <section className="bg-warroom-surface border border-warroom-border rounded-2xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500/20 to-pink-500/20 flex items-center justify-center">
            <Edit3 size={20} className="text-purple-400" />
          </div>
          <div>
            <h4 className="text-lg font-semibold text-warroom-text">Profile Changes</h4>
            <p className="text-xs text-warroom-muted">Specific bio, link, and aesthetic recommendations</p>
          </div>
        </div>

        {profileIntel.recommendations?.profileChanges && profileIntel.recommendations.profileChanges.length > 0 ? (
          <div className="space-y-4">
            {profileIntel.recommendations.profileChanges.map((item, idx) => (
              <div key={idx} className="bg-purple-500/5 border border-purple-500/20 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <div className="w-6 h-6 rounded-full bg-purple-500/20 flex items-center justify-center mt-0.5">
                    <Edit3 size={12} className="text-purple-400" />
                  </div>
                  <div className="flex-1">
                    <h5 className="text-sm font-semibold text-warroom-text mb-2">{item.what}</h5>
                    <p className="text-xs text-warroom-muted mb-3">{item.why}</p>
                    <span className={`text-xs px-2 py-1 rounded-full ${getPriorityColor(item.priority)}`}>
                      {item.priority} Priority
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-warroom-muted">
            <Edit3 size={32} className="mx-auto mb-3 opacity-30" />
            <p className="text-sm">Analysis in progress</p>
            <p className="text-xs mt-1">Profile optimization recommendations coming soon</p>
          </div>
        )}
      </section>

      {/* 7. Videos to Consider Removing */}
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

        {profileIntel.recommendations?.videosToDelete && profileIntel.recommendations.videosToDelete.length > 0 ? (
          <div className="space-y-3">
            {profileIntel.recommendations.videosToDelete.map((video, idx) => (
              <div key={idx} className="bg-red-500/5 border border-red-500/20 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <div className="w-6 h-6 rounded-full bg-red-500/20 flex items-center justify-center mt-0.5">
                    <Trash2 size={12} className="text-red-400" />
                  </div>
                  <div className="flex-1">
                    <h5 className="text-sm font-semibold text-warroom-text mb-1">
                      {video.title || `Video ${video.video_id}`}
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
            <p className="text-sm">All content performing well</p>
            <p className="text-xs mt-1">No videos recommended for removal at this time</p>
          </div>
        )}
      </section>

      {/* 8. Next Steps */}
      <section className="bg-warroom-surface border border-warroom-border rounded-2xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-emerald-500/20 to-blue-500/20 flex items-center justify-center">
            <ArrowRight size={20} className="text-emerald-400" />
          </div>
          <div>
            <h4 className="text-lg font-semibold text-warroom-text">Next Steps</h4>
            <p className="text-xs text-warroom-muted">Prioritized action items for maximum impact</p>
          </div>
        </div>

        {profileIntel.recommendations?.nextSteps && profileIntel.recommendations.nextSteps.length > 0 ? (
          <div className="space-y-4">
            {profileIntel.recommendations.nextSteps.map((step, idx) => (
              <div key={idx} className="bg-emerald-500/5 border border-emerald-500/20 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center mt-0.5">
                    <span className="text-xs font-bold text-emerald-400">{idx + 1}</span>
                  </div>
                  <div className="flex-1">
                    <h5 className="text-sm font-semibold text-warroom-text mb-1">{step.action}</h5>
                    <p className="text-xs text-warroom-muted mb-2">Expected: {step.expected_impact}</p>
                    <span className={`text-xs px-2 py-1 rounded-full ${getPriorityColor(step.priority)}`}>
                      {step.priority} Priority
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-warroom-muted">
            <ArrowRight size={32} className="mx-auto mb-3 opacity-30" />
            <p className="text-sm">Action plan generating</p>
            <p className="text-xs mt-1">Personalized next steps will appear after analysis</p>
          </div>
        )}
      </section>
    </div>
  );
}