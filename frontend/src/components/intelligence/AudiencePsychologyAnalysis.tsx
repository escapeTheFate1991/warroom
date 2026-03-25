"use client";

import React, { useState, useEffect } from 'react';
import { 
  Brain, 
  Users, 
  TrendingUp, 
  Eye, 
  Heart, 
  Share, 
  MessageCircle, 
  AlertCircle,
  CheckCircle,
  Target,
  Zap,
  BookOpen,
  Lightbulb,
  BarChart3,
  Filter,
  Loader2,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  X,
  Info
} from 'lucide-react';

interface PsychologicalProfile {
  username: string;
  share_motivation: string;
  comment_depth: string;
  engagement_psychology: string;
  pain_points: string[];
  identity_signals: string[];
  emotional_tone: string;
  influence_score: number;
}

interface ContentPsychology {
  hook_psychology: string;
  shareability_score: number;
  friction_points: string[];
  authenticity_score: number;
  algorithm_insights: any;
  viral_triggers: string[];
}

interface BehavioralInsights {
  motivation_distribution: Record<string, number>;
  engagement_depth_distribution: Record<string, number>;
  psychology_distribution: Record<string, number>;
  top_pain_points: Record<string, number>;
  dominant_identities: Record<string, number>;
  average_influence_score: number;
  high_influence_percentage: number;
}

interface SharingPsychology {
  primary_sharing_driver: string;
  utility_share_signals: number;
  identity_share_signals: number;
  relatability_share_signals: number;
  sharing_psychology_breakdown: {
    this_is_how_i_feel: number;
    you_need_this: number;
    this_represents_me: number;
  };
}

interface AlgorithmInsights {
  signals: {
    signal_type: string;
    strength: number;
    evidence: string[];
    optimization_tip: string;
  }[];
  overall_score: {
    score: number;
    grade: string;
    top_signals: any[];
    improvement_areas: any[];
  };
}

interface OptimizationRecommendation {
  category: string;
  recommendation: string;
  reasoning: string;
}

interface PsychologyAnalysisData {
  analysis_metadata: {
    competitor_handle: string;
    competitor_platform: string;
    total_comments_analyzed: number;
    posts_analyzed: number;
    analysis_date: string;
  };
  psychological_profiles: PsychologicalProfile[];
  content_psychology: ContentPsychology;
  behavioral_insights: BehavioralInsights;
  sharing_psychology: SharingPsychology;
  optimization_recommendations: OptimizationRecommendation[];
  audience_uniqueness: {
    uniqueness_ratio: number;
    power_user_ratio: number;
    cross_commenter_ratio: number;
    unique_insights_available: boolean;
  };
  excluded_profiles: {
    power_users: number;
    cross_commenters: number;
    total_excluded: number;
  };
  algorithm_insights?: AlgorithmInsights;
}

interface AudiencePsychologyAnalysisProps {
  competitorId: number;
  competitorHandle: string;
  onClose: () => void;
}

const AudiencePsychologyAnalysis: React.FC<AudiencePsychologyAnalysisProps> = ({
  competitorId,
  competitorHandle,
  onClose
}) => {
  const [analysisData, setAnalysisData] = useState<PsychologyAnalysisData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTab, setSelectedTab] = useState('overview');
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({});

  const tabs = [
    { id: 'overview', label: 'Overview', icon: BarChart3 },
    { id: 'profiles', label: 'Psychology Profiles', icon: Brain },
    { id: 'sharing', label: 'Sharing Psychology', icon: Share },
    { id: 'algorithm', label: 'Algorithm Insights', icon: Zap },
    { id: 'recommendations', label: 'Optimization', icon: Target }
  ];

  const runAnalysis = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const { API, authFetch } = await import('@/lib/api');
      const response = await authFetch(`${API}/api/audience-intel/psychology-analysis`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          competitor_id: competitorId,
          include_related_competitors: true,
          min_comment_length: 10,
          max_profiles: 100
        }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to analyze audience psychology');
      }
      
      const data = await response.json();
      setAnalysisData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runAnalysis();
  }, [competitorId]);

  const toggleSection = (sectionId: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [sectionId]: !prev[sectionId]
    }));
  };

  const formatShareMotivation = (motivation: string) => {
    const motivationMap: Record<string, string> = {
      'utility': 'Utility Value',
      'relatability': 'Emotional Relatability',
      'identity_signal': 'Identity Expression',
      'status': 'Status Signaling',
      'emotion': 'Emotional Response',
      'tribal': 'Community Connection'
    };
    return motivationMap[motivation] || motivation;
  };

  const getMotivationColor = (motivation: string) => {
    const colorMap: Record<string, string> = {
      'utility': 'bg-blue-100 text-blue-800',
      'relatability': 'bg-pink-100 text-pink-800',
      'identity_signal': 'bg-purple-100 text-purple-800',
      'status': 'bg-yellow-100 text-yellow-800',
      'emotion': 'bg-red-100 text-red-800',
      'tribal': 'bg-green-100 text-green-800'
    };
    return colorMap[motivation] || 'bg-gray-100 text-gray-800';
  };

  const getAlgorithmGradeColor = (grade: string) => {
    const gradeColors: Record<string, string> = {
      'A': 'text-green-600',
      'B': 'text-blue-600',
      'C': 'text-yellow-600',
      'D': 'text-orange-600',
      'F': 'text-red-600'
    };
    return gradeColors[grade] || 'text-gray-600';
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-warroom-bg border border-warroom-border rounded-lg p-8 max-w-md w-full mx-4">
          <div className="flex items-center space-x-3">
            <Loader2 className="h-6 w-6 animate-spin text-purple-400" />
            <div>
              <h3 className="text-lg font-medium text-warroom-text">Analyzing Audience Psychology</h3>
              <p className="text-warroom-muted text-sm">This may take a few minutes...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-warroom-bg border border-warroom-border rounded-lg p-8 max-w-md w-full mx-4">
          <div className="flex items-center space-x-3 mb-4">
            <AlertCircle className="h-6 w-6 text-red-400" />
            <h3 className="text-lg font-medium text-red-400">Analysis Failed</h3>
          </div>
          <p className="text-warroom-muted mb-4">{error}</p>
          <div className="flex space-x-3">
            <button
              onClick={runAnalysis}
              className="flex items-center space-x-2 px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600"
            >
              <RefreshCw className="h-4 w-4" />
              <span>Retry</span>
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-warroom-surface border border-warroom-border text-warroom-text rounded-lg hover:bg-warroom-border"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!analysisData) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-warroom-bg border border-warroom-border rounded-lg max-w-7xl w-full h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-warroom-border">
          <div className="flex items-center space-x-3">
            <Brain className="h-6 w-6 text-purple-400" />
            <div>
              <h2 className="text-xl font-bold text-warroom-text">
                Audience Psychology Analysis
              </h2>
              <p className="text-sm text-warroom-muted">
                @{competitorHandle} • {analysisData.analysis_metadata.total_comments_analyzed} comments analyzed
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-warroom-surface border border-warroom-border rounded-lg transition-colors"
          >
            <X className="h-5 w-5 text-warroom-muted" />
          </button>
        </div>

        {/* Tabs */}
        <div className="border-b border-warroom-border">
          <nav className="flex space-x-8 px-6">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setSelectedTab(tab.id)}
                  className={`flex items-center space-x-2 py-4 px-2 border-b-2 font-medium text-sm transition-colors ${
                    selectedTab === tab.id
                      ? 'border-purple-400 text-purple-400'
                      : 'border-transparent text-warroom-muted hover:text-warroom-text hover:border-warroom-accent/30'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 bg-warroom-bg">
          {selectedTab === 'overview' && (
            <div className="space-y-6">
              {/* Key Metrics */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-4 rounded-lg">
                  <div className="flex items-center space-x-2">
                    <Users className="h-5 w-5 text-blue-600" />
                    <h3 className="font-medium text-blue-900">Unique Insights</h3>
                  </div>
                  <p className="text-2xl font-bold text-blue-900 mt-2">
                    {(analysisData.audience_uniqueness.uniqueness_ratio * 100).toFixed(1)}%
                  </p>
                  <p className="text-sm text-blue-700">
                    {analysisData.excluded_profiles.total_excluded} shared users removed
                  </p>
                </div>

                <div className="bg-gradient-to-br from-green-50 to-green-100 p-4 rounded-lg">
                  <div className="flex items-center space-x-2">
                    <Share className="h-5 w-5 text-green-600" />
                    <h3 className="font-medium text-green-900">Primary Driver</h3>
                  </div>
                  <p className="text-lg font-bold text-green-900 mt-2">
                    {formatShareMotivation(analysisData.sharing_psychology.primary_sharing_driver)}
                  </p>
                  <p className="text-sm text-green-700">Main sharing motivation</p>
                </div>

                <div className="bg-gradient-to-br from-purple-50 to-purple-100 p-4 rounded-lg">
                  <div className="flex items-center space-x-2">
                    <TrendingUp className="h-5 w-5 text-purple-600" />
                    <h3 className="font-medium text-purple-900">Shareability</h3>
                  </div>
                  <p className="text-2xl font-bold text-purple-900 mt-2">
                    {(analysisData.content_psychology.shareability_score * 100).toFixed(0)}%
                  </p>
                  <p className="text-sm text-purple-700">Viral potential score</p>
                </div>

                <div className={`bg-gradient-to-br p-4 rounded-lg ${
                  (analysisData.algorithm_insights?.overall_score?.score || 0) > 0.7 
                    ? 'from-green-50 to-green-100' 
                    : 'from-orange-50 to-orange-100'
                }`}>
                  <div className="flex items-center space-x-2">
                    <Zap className={`h-5 w-5 ${
                      (analysisData.algorithm_insights?.overall_score?.score || 0) > 0.7 
                        ? 'text-green-600' 
                        : 'text-orange-600'
                    }`} />
                    <h3 className={`font-medium ${
                      (analysisData.algorithm_insights?.overall_score?.score || 0) > 0.7 
                        ? 'text-green-900' 
                        : 'text-orange-900'
                    }`}>Algorithm Score</h3>
                  </div>
                  <p className={`text-2xl font-bold mt-2 ${
                    (analysisData.algorithm_insights?.overall_score?.score || 0) > 0.7 
                      ? 'text-green-900' 
                      : 'text-orange-900'
                  }`}>
                    {analysisData.algorithm_insights?.overall_score?.grade || 'N/A'}
                  </p>
                  <p className={`text-sm ${
                    (analysisData.algorithm_insights?.overall_score?.score || 0) > 0.7 
                      ? 'text-green-700' 
                      : 'text-orange-700'
                  }`}>
                    {analysisData.algorithm_insights?.overall_score?.score 
                      ? `${(analysisData.algorithm_insights.overall_score.score * 100).toFixed(1)}% optimized`
                      : 'Not analyzed'
                    }
                  </p>
                </div>
              </div>

              {/* Behavioral Distribution */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-white border border-gray-200 rounded-lg p-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Share Motivations</h3>
                  <div className="space-y-3">
                    {Object.entries(analysisData.behavioral_insights.motivation_distribution).map(([motivation, count]) => {
                      const percentage = (count / analysisData.psychological_profiles.length * 100).toFixed(1);
                      return (
                        <div key={motivation} className="flex items-center justify-between">
                          <span className={`px-3 py-1 rounded-full text-xs font-medium ${getMotivationColor(motivation)}`}>
                            {formatShareMotivation(motivation)}
                          </span>
                          <span className="text-sm text-gray-600">{percentage}%</span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div className="bg-white border border-gray-200 rounded-lg p-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Engagement Depth</h3>
                  <div className="space-y-3">
                    {Object.entries(analysisData.behavioral_insights.engagement_depth_distribution).map(([depth, count]) => {
                      const percentage = (count / analysisData.psychological_profiles.length * 100).toFixed(1);
                      const depthColors: Record<string, string> = {
                        'surface': 'bg-gray-100 text-gray-800',
                        'shallow': 'bg-yellow-100 text-yellow-800',
                        'engaged': 'bg-blue-100 text-blue-800',
                        'analytical': 'bg-purple-100 text-purple-800',
                        'expert': 'bg-green-100 text-green-800'
                      };
                      return (
                        <div key={depth} className="flex items-center justify-between">
                          <span className={`px-3 py-1 rounded-full text-xs font-medium ${depthColors[depth] || 'bg-gray-100 text-gray-800'}`}>
                            {depth.charAt(0).toUpperCase() + depth.slice(1)}
                          </span>
                          <span className="text-sm text-gray-600">{percentage}%</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Top Pain Points */}
              <div className="bg-white border border-gray-200 rounded-lg p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Top Pain Points</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {Object.entries(analysisData.behavioral_insights.top_pain_points).slice(0, 8).map(([painPoint, count]) => (
                    <div key={painPoint} className="flex items-center justify-between p-3 bg-red-50 rounded-lg">
                      <span className="text-sm font-medium text-red-800">
                        {painPoint.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
                      </span>
                      <span className="text-sm text-red-600">{count} mentions</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {selectedTab === 'profiles' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium text-gray-900">
                  Psychological Profiles ({analysisData.psychological_profiles.length})
                </h3>
                <div className="text-sm text-gray-500">
                  Unique audience members only (shared users filtered out)
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {analysisData.psychological_profiles.slice(0, 12).map((profile, index) => (
                  <div key={index} className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="font-medium text-gray-900 truncate">@{profile.username}</h4>
                      <div className={`w-3 h-3 rounded-full ${
                        profile.influence_score > 0.7 ? 'bg-green-500' :
                        profile.influence_score > 0.4 ? 'bg-yellow-500' : 'bg-gray-400'
                      }`} title={`Influence: ${(profile.influence_score * 100).toFixed(0)}%`} />
                    </div>
                    
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-gray-500">Share Motivation</span>
                        <span className={`px-2 py-1 rounded text-xs ${getMotivationColor(profile.share_motivation)}`}>
                          {formatShareMotivation(profile.share_motivation)}
                        </span>
                      </div>
                      
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-gray-500">Comment Depth</span>
                        <span className="text-xs text-gray-800 capitalize">{profile.comment_depth}</span>
                      </div>
                      
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-gray-500">Emotional Tone</span>
                        <span className="text-xs text-gray-800 capitalize">{profile.emotional_tone}</span>
                      </div>
                      
                      {profile.identity_signals.length > 0 && (
                        <div>
                          <span className="text-xs text-gray-500">Identity Signals</span>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {profile.identity_signals.slice(0, 3).map((signal, idx) => (
                              <span key={idx} className="px-2 py-1 bg-purple-100 text-purple-800 text-xs rounded">
                                {signal}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              
              {analysisData.psychological_profiles.length > 12 && (
                <div className="text-center">
                  <p className="text-gray-500">
                    Showing 12 of {analysisData.psychological_profiles.length} profiles
                  </p>
                </div>
              )}
            </div>
          )}

          {selectedTab === 'sharing' && (
            <div className="space-y-6">
              {/* Sharing Psychology Breakdown */}
              <div className="bg-white border border-gray-200 rounded-lg p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Why People Share This Content</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="text-center">
                    <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-3">
                      <BookOpen className="h-8 w-8 text-blue-600" />
                    </div>
                    <h4 className="font-medium text-gray-900">You Need This</h4>
                    <p className="text-2xl font-bold text-blue-600 mt-2">
                      {analysisData.sharing_psychology.sharing_psychology_breakdown.you_need_this}
                    </p>
                    <p className="text-sm text-gray-600">Utility-driven sharing</p>
                  </div>
                  
                  <div className="text-center">
                    <div className="w-16 h-16 bg-pink-100 rounded-full flex items-center justify-center mx-auto mb-3">
                      <Heart className="h-8 w-8 text-pink-600" />
                    </div>
                    <h4 className="font-medium text-gray-900">This Is How I Feel</h4>
                    <p className="text-2xl font-bold text-pink-600 mt-2">
                      {analysisData.sharing_psychology.sharing_psychology_breakdown.this_is_how_i_feel}
                    </p>
                    <p className="text-sm text-gray-600">Relatability-driven sharing</p>
                  </div>
                  
                  <div className="text-center">
                    <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-3">
                      <Users className="h-8 w-8 text-purple-600" />
                    </div>
                    <h4 className="font-medium text-gray-900">This Represents Me</h4>
                    <p className="text-2xl font-bold text-purple-600 mt-2">
                      {analysisData.sharing_psychology.sharing_psychology_breakdown.this_represents_me}
                    </p>
                    <p className="text-sm text-gray-600">Identity-driven sharing</p>
                  </div>
                </div>
              </div>
              
              {/* Content Psychology */}
              <div className="bg-white border border-gray-200 rounded-lg p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Content Psychology Analysis</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h4 className="font-medium text-gray-900 mb-3">Hook Psychology</h4>
                    <span className="px-3 py-2 bg-blue-100 text-blue-800 rounded-lg text-sm font-medium">
                      {analysisData.content_psychology.hook_psychology.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
                    </span>
                  </div>
                  
                  <div>
                    <h4 className="font-medium text-gray-900 mb-3">Authenticity Score</h4>
                    <div className="flex items-center space-x-3">
                      <div className={`w-4 h-4 rounded-full ${
                        analysisData.content_psychology.authenticity_score > 0.3 ? 'bg-green-500' :
                        analysisData.content_psychology.authenticity_score > -0.3 ? 'bg-yellow-500' : 'bg-red-500'
                      }`} />
                      <span className="text-sm text-gray-800">
                        {analysisData.content_psychology.authenticity_score > 0.3 ? 'Authentic' :
                         analysisData.content_psychology.authenticity_score > -0.3 ? 'Balanced' : 'Too Polished'}
                      </span>
                      <span className="text-sm text-gray-500">
                        ({analysisData.content_psychology.authenticity_score.toFixed(2)})
                      </span>
                    </div>
                  </div>
                </div>
                
                {analysisData.content_psychology.viral_triggers.length > 0 && (
                  <div className="mt-6">
                    <h4 className="font-medium text-gray-900 mb-3">Viral Triggers Detected</h4>
                    <div className="flex flex-wrap gap-2">
                      {analysisData.content_psychology.viral_triggers.map((trigger, index) => (
                        <span key={index} className="px-3 py-1 bg-green-100 text-green-800 text-sm rounded-full">
                          {trigger.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {selectedTab === 'algorithm' && analysisData.algorithm_insights && (
            <div className="space-y-6">
              {/* Algorithm Score Overview */}
              <div className="bg-white border border-gray-200 rounded-lg p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-medium text-gray-900">Algorithm Optimization Score</h3>
                  <div className={`text-3xl font-bold ${getAlgorithmGradeColor(analysisData.algorithm_insights?.overall_score?.grade)}`}>
                    {analysisData.algorithm_insights?.overall_score?.grade}
                  </div>
                </div>
                <p className="text-gray-600 mb-4">
                  Overall algorithm compatibility: {((analysisData.algorithm_insights?.overall_score?.score || 0) * 100).toFixed(1)}%
                </p>
              </div>

              {/* Top Signals */}
              <div className="bg-white border border-gray-200 rounded-lg p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Top Performing Signals</h3>
                <div className="space-y-4">
                  {analysisData.algorithm_insights?.overall_score?.top_signals?.map((signal, index) => (
                    <div key={index} className="flex items-center justify-between p-4 bg-green-50 rounded-lg">
                      <div>
                        <h4 className="font-medium text-green-900">
                          {signal.signal.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
                        </h4>
                        <p className="text-sm text-green-700">{signal.optimization_tip}</p>
                      </div>
                      <div className="text-right">
                        <span className="text-lg font-bold text-green-600">
                          {(signal.strength * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Improvement Areas */}
              {(analysisData.algorithm_insights?.overall_score?.improvement_areas?.length || 0) > 0 && (
                <div className="bg-white border border-gray-200 rounded-lg p-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Improvement Opportunities</h3>
                  <div className="space-y-4">
                    {analysisData.algorithm_insights?.overall_score?.improvement_areas?.map((signal, index) => (
                      <div key={index} className="flex items-center justify-between p-4 bg-orange-50 rounded-lg">
                        <div>
                          <h4 className="font-medium text-orange-900">
                            {signal.signal.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
                          </h4>
                          <p className="text-sm text-orange-700">{signal.optimization_tip}</p>
                        </div>
                        <div className="text-right">
                          <span className="text-lg font-bold text-orange-600">
                            {(signal.strength * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* All Algorithm Signals */}
              <div className="bg-white border border-gray-200 rounded-lg p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">All Algorithm Signals</h3>
                <div className="space-y-4">
                  {analysisData.algorithm_insights.signals.map((signal, index) => (
                    <div key={index} className="border border-gray-100 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-medium text-gray-900">
                          {signal.signal_type.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
                        </h4>
                        <span className={`px-3 py-1 rounded text-sm font-medium ${
                          signal.strength > 0.7 ? 'bg-green-100 text-green-800' :
                          signal.strength > 0.4 ? 'bg-yellow-100 text-yellow-800' :
                          'bg-red-100 text-red-800'
                        }`}>
                          {(signal.strength * 100).toFixed(0)}%
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 mb-3">{signal.optimization_tip}</p>
                      
                      {signal.evidence.length > 0 && (
                        <div>
                          <button
                            onClick={() => toggleSection(`signal-${index}`)}
                            className="flex items-center space-x-2 text-sm text-blue-600 hover:text-blue-800"
                          >
                            {expandedSections[`signal-${index}`] ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                            <span>View Evidence ({signal.evidence.length})</span>
                          </button>
                          
                          {expandedSections[`signal-${index}`] && (
                            <div className="mt-3 space-y-2">
                              {signal.evidence.slice(0, 3).map((evidence, evIdx) => (
                                <div key={evIdx} className="text-xs text-gray-600 bg-gray-50 p-2 rounded">
                                  {evidence}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {selectedTab === 'recommendations' && (
            <div className="space-y-6">
              <div className="bg-white border border-gray-200 rounded-lg p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  Optimization Recommendations ({analysisData.optimization_recommendations.length})
                </h3>
                <div className="space-y-4">
                  {analysisData.optimization_recommendations.map((rec, index) => (
                    <div key={index} className="border border-gray-100 rounded-lg p-4">
                      <div className="flex items-start space-x-3">
                        <div className={`p-2 rounded-lg ${
                          rec.category === 'Content Strategy' ? 'bg-blue-100' :
                          rec.category === 'Algorithm Optimization' ? 'bg-purple-100' :
                          rec.category === 'Authenticity' ? 'bg-green-100' :
                          rec.category === 'Engagement Strategy' ? 'bg-yellow-100' :
                          'bg-gray-100'
                        }`}>
                          {rec.category === 'Content Strategy' && <BookOpen className="h-5 w-5 text-blue-600" />}
                          {rec.category === 'Algorithm Optimization' && <Zap className="h-5 w-5 text-purple-600" />}
                          {rec.category === 'Authenticity' && <Heart className="h-5 w-5 text-green-600" />}
                          {rec.category === 'Engagement Strategy' && <MessageCircle className="h-5 w-5 text-yellow-600" />}
                          {!['Content Strategy', 'Algorithm Optimization', 'Authenticity', 'Engagement Strategy'].includes(rec.category) && 
                           <Target className="h-5 w-5 text-gray-600" />}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center space-x-2 mb-2">
                            <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                              rec.category === 'Content Strategy' ? 'bg-blue-100 text-blue-800' :
                              rec.category === 'Algorithm Optimization' ? 'bg-purple-100 text-purple-800' :
                              rec.category === 'Authenticity' ? 'bg-green-100 text-green-800' :
                              rec.category === 'Engagement Strategy' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {rec.category}
                            </span>
                          </div>
                          <h4 className="font-medium text-gray-900 mb-1">{rec.recommendation}</h4>
                          <p className="text-sm text-gray-600">{rec.reasoning}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AudiencePsychologyAnalysis;