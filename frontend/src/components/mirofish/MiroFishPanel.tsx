"use client";

import { useState, useEffect } from "react";
import { 
  Brain, Upload, Play, BarChart3, Target, Zap, 
  Sparkles, TrendingUp, MessageCircle, Heart, Share, 
  FileVideo, AlertCircle, CheckCircle, Loader2, Film
} from "lucide-react";
import { authFetch } from "@/lib/api";

interface SimulationResult {
  viral_score: number;
  engagement_rate: number;
  sentiment: {
    positive: number;
    neutral: number;
    negative: number;
  };
  recommendations: Array<{
    suggestion: string;
    reasoning: string;
    priority: 'high' | 'medium' | 'low';
  }>;
  personas_used: number;
  confidence: number;
}

interface VideoProject {
  id: number;
  title: string;
  thumbnail_url?: string;
  status: string;
  created_at: string;
}

interface PublishedContent {
  id: number;
  title: string;
  platform: string;
  engagement_score: number;
  created_at: string;
}

type SubTab = 'pre-publish' | 'post-publish' | 'sandbox';

export default function MiroFishPanel() {
  const [activeSubTab, setActiveSubTab] = useState<SubTab>('pre-publish');
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationResult, setSimulationResult] = useState<SimulationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  // Pre-publish state
  const [selectedProject, setSelectedProject] = useState<number | null>(null);
  const [videoProjects, setVideoProjects] = useState<VideoProject[]>([]);
  
  // Post-publish state
  const [selectedPublishedContent, setSelectedPublishedContent] = useState<number | null>(null);
  const [publishedContent, setPublishedContent] = useState<PublishedContent[]>([]);
  
  // Sandbox state
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [audienceContext, setAudienceContext] = useState('');
  const [selectedPlatform, setSelectedPlatform] = useState('instagram');

  useEffect(() => {
    loadVideoProjects();
    loadPublishedContent();
  }, []);

  const loadVideoProjects = async () => {
    try {
      const response = await authFetch('/api/video-copycat/storyboards');
      if (response.ok) {
        const data = await response.json();
        // Ensure data is an array
        setVideoProjects(Array.isArray(data) ? data : (data.projects || data.storyboards || []));
      } else {
        console.error('Failed to load video projects - API response not OK');
        setVideoProjects([]);
      }
    } catch (error) {
      console.error('Failed to load video projects:', error);
      setVideoProjects([]);
    }
  };

  const loadPublishedContent = async () => {
    try {
      // Load from social content or competitor posts
      const response = await authFetch('/api/social/content');
      if (response.ok) {
        const data = await response.json();
        // Ensure data is an array
        setPublishedContent(Array.isArray(data) ? data : (data.content || data.posts || []));
      } else {
        console.error('Failed to load published content - API response not OK');
        setPublishedContent([]);
      }
    } catch (error) {
      console.error('Failed to load published content:', error);
      setPublishedContent([]);
    }
  };

  const runSimulation = async () => {
    setIsSimulating(true);
    setError(null);
    
    try {
      let endpoint = '/api/mirofish/simulate';
      let body: any = {
        platform: selectedPlatform
      };

      if (activeSubTab === 'pre-publish' && selectedProject) {
        body.video_id = selectedProject;
      } else if (activeSubTab === 'sandbox' && uploadedFile) {
        // Use file upload endpoint
        const formData = new FormData();
        formData.append('file', uploadedFile);
        formData.append('platform', selectedPlatform);
        if (audienceContext) {
          formData.append('audience_context', audienceContext);
        }
        
        const response = await authFetch('/api/mirofish/file-simulate', {
          method: 'POST',
          body: formData
        });
        
        if (response.ok) {
          const result = await response.json();
          setSimulationResult(result);
        } else {
          throw new Error('Simulation failed');
        }
        return;
      }

      if (audienceContext) {
        body.audience_context = audienceContext;
      }

      const response = await authFetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });

      if (response.ok) {
        const result = await response.json();
        setSimulationResult(result);
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Simulation failed');
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Simulation failed');
    } finally {
      setIsSimulating(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-green-400";
    if (score >= 60) return "text-yellow-400";
    if (score >= 40) return "text-orange-400";
    return "text-red-400";
  };

  const getConfidenceText = (confidence: number) => {
    if (confidence >= 0.8) return "High Confidence";
    if (confidence >= 0.6) return "Medium Confidence";
    return "Low Confidence";
  };

  const renderSubTabs = () => (
    <div className="border-b border-warroom-border">
      <div className="flex space-x-8">
        {[
          { id: 'pre-publish', label: 'Pre-Publish Simulator', icon: Target },
          { id: 'post-publish', label: 'Post-Publish Analyzer', icon: BarChart3 },
          { id: 'sandbox', label: 'Content Sandbox', icon: Sparkles }
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveSubTab(id as SubTab)}
            className={`flex items-center space-x-2 px-4 py-3 border-b-2 font-medium ${
              activeSubTab === id
                ? 'border-warroom-accent text-warroom-accent'
                : 'border-transparent text-warroom-muted hover:text-warroom-text'
            }`}
          >
            <Icon className="h-4 w-4" />
            <span>{label}</span>
          </button>
        ))}
      </div>
    </div>
  );

  const renderPrePublishSimulator = () => (
    <div className="space-y-6">
      <div className="bg-warroom-card border border-warroom-border rounded-lg p-6">
        <h3 className="text-lg font-medium mb-4 flex items-center">
          <Film className="h-5 w-5 mr-2 text-warroom-accent" />
          Select Video Project
        </h3>
        
        {videoProjects.length === 0 ? (
          <div className="text-center py-8 text-warroom-muted">
            <FileVideo className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No video projects found. Create a project in the Content Pipeline first.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.isArray(videoProjects) && videoProjects.map((project) => (
              <div
                key={project.id}
                onClick={() => setSelectedProject(project.id)}
                className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                  selectedProject === project.id
                    ? 'border-warroom-accent bg-warroom-accent/10'
                    : 'border-warroom-border hover:border-warroom-accent/50'
                }`}
              >
                {project.thumbnail_url && (
                  <img 
                    src={project.thumbnail_url} 
                    alt={project.title}
                    className="w-full h-32 object-cover rounded mb-3"
                  />
                )}
                <h4 className="font-medium text-sm">{project.title}</h4>
                <p className="text-xs text-warroom-muted mt-1">
                  Status: {project.status}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
      
      <div className="bg-warroom-card border border-warroom-border rounded-lg p-6">
        <h3 className="text-lg font-medium mb-4">Platform & Audience</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-2">Platform</label>
            <select 
              value={selectedPlatform}
              onChange={(e) => setSelectedPlatform(e.target.value)}
              className="w-full px-3 py-2 bg-warroom-bg border border-warroom-border rounded-lg"
            >
              <option value="instagram">Instagram</option>
              <option value="tiktok">TikTok</option>
              <option value="youtube">YouTube</option>
              <option value="facebook">Facebook</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">Audience Context (Optional)</label>
            <input
              type="text"
              value={audienceContext}
              onChange={(e) => setAudienceContext(e.target.value)}
              placeholder="e.g., fitness enthusiasts, entrepreneurs"
              className="w-full px-3 py-2 bg-warroom-bg border border-warroom-border rounded-lg"
            />
          </div>
        </div>
      </div>
    </div>
  );

  const renderPostPublishAnalyzer = () => (
    <div className="space-y-6">
      <div className="bg-warroom-card border border-warroom-border rounded-lg p-6">
        <h3 className="text-lg font-medium mb-4 flex items-center">
          <BarChart3 className="h-5 w-5 mr-2 text-warroom-accent" />
          Select Published Content
        </h3>
        
        {publishedContent.length === 0 ? (
          <div className="text-center py-8 text-warroom-muted">
            <TrendingUp className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No published content found. Content analysis coming soon.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {Array.isArray(publishedContent) && publishedContent.map((content) => (
              <div
                key={content.id}
                onClick={() => setSelectedPublishedContent(content.id)}
                className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                  selectedPublishedContent === content.id
                    ? 'border-warroom-accent bg-warroom-accent/10'
                    : 'border-warroom-border hover:border-warroom-accent/50'
                }`}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <h4 className="font-medium">{content.title}</h4>
                    <p className="text-sm text-warroom-muted">
                      {content.platform} • {new Date(content.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <span className="text-sm font-medium text-warroom-accent">
                    {content.engagement_score}% engagement
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );

  const renderContentSandbox = () => (
    <div className="space-y-6">
      <div className="bg-warroom-card border border-warroom-border rounded-lg p-6">
        <h3 className="text-lg font-medium mb-4 flex items-center">
          <Upload className="h-5 w-5 mr-2 text-warroom-accent" />
          Upload Video File
        </h3>
        
        <div className="border-2 border-dashed border-warroom-border rounded-lg p-8 text-center">
          {uploadedFile ? (
            <div className="space-y-2">
              <CheckCircle className="h-12 w-12 mx-auto text-green-400" />
              <p className="font-medium">{uploadedFile.name}</p>
              <p className="text-sm text-warroom-muted">
                {(uploadedFile.size / (1024 * 1024)).toFixed(1)} MB
              </p>
              <button
                onClick={() => setUploadedFile(null)}
                className="text-sm text-warroom-accent hover:underline"
              >
                Remove file
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <Upload className="h-12 w-12 mx-auto text-warroom-muted" />
              <div>
                <p className="text-lg font-medium">Drop video file here</p>
                <p className="text-warroom-muted">or click to browse</p>
              </div>
              <input
                type="file"
                accept="video/*"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) setUploadedFile(file);
                }}
                className="hidden"
                id="video-upload"
              />
              <label
                htmlFor="video-upload"
                className="inline-flex items-center px-4 py-2 bg-warroom-accent text-white rounded-lg hover:bg-warroom-accent/90 cursor-pointer"
              >
                Select File
              </label>
            </div>
          )}
        </div>
      </div>
      
      <div className="bg-warroom-card border border-warroom-border rounded-lg p-6">
        <h3 className="text-lg font-medium mb-4">Simulation Settings</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-2">Target Platform</label>
            <select 
              value={selectedPlatform}
              onChange={(e) => setSelectedPlatform(e.target.value)}
              className="w-full px-3 py-2 bg-warroom-bg border border-warroom-border rounded-lg"
            >
              <option value="instagram">Instagram</option>
              <option value="tiktok">TikTok</option>
              <option value="youtube">YouTube</option>
              <option value="facebook">Facebook</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">Audience Context</label>
            <input
              type="text"
              value={audienceContext}
              onChange={(e) => setAudienceContext(e.target.value)}
              placeholder="Target audience description"
              className="w-full px-3 py-2 bg-warroom-bg border border-warroom-border rounded-lg"
            />
          </div>
        </div>
      </div>
    </div>
  );

  const renderSimulationButton = () => {
    const canSimulate = 
      (activeSubTab === 'pre-publish' && selectedProject) ||
      (activeSubTab === 'post-publish' && selectedPublishedContent) ||
      (activeSubTab === 'sandbox' && uploadedFile);

    return (
      <div className="flex justify-center">
        <button
          onClick={runSimulation}
          disabled={!canSimulate || isSimulating}
          className={`flex items-center space-x-2 px-8 py-3 rounded-lg font-medium transition-colors ${
            canSimulate && !isSimulating
              ? 'bg-warroom-accent text-white hover:bg-warroom-accent/90'
              : 'bg-warroom-muted text-warroom-text cursor-not-allowed opacity-50'
          }`}
        >
          {isSimulating ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              <span>Running Simulation...</span>
            </>
          ) : (
            <>
              <Play className="h-5 w-5" />
              <span>Run Simulation</span>
            </>
          )}
        </button>
      </div>
    );
  };

  const renderResults = () => {
    if (!simulationResult) return null;

    return (
      <div className="bg-warroom-card border border-warroom-border rounded-lg p-6 space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-xl font-semibold flex items-center">
            <Brain className="h-6 w-6 mr-2 text-warroom-accent" />
            Simulation Results
          </h3>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
            simulationResult.confidence >= 0.8 ? 'bg-green-100 text-green-800' :
            simulationResult.confidence >= 0.6 ? 'bg-yellow-100 text-yellow-800' :
            'bg-red-100 text-red-800'
          }`}>
            {getConfidenceText(simulationResult.confidence)}
          </span>
        </div>

        {/* Viral Score Gauge */}
        <div className="text-center">
          <div className="inline-flex flex-col items-center space-y-2">
            <div className="relative w-32 h-32">
              <svg className="w-32 h-32 transform -rotate-90" viewBox="0 0 36 36">
                <path
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeDasharray={`${simulationResult.viral_score}, 100`}
                  className={getScoreColor(simulationResult.viral_score)}
                />
                <path
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeDasharray="0, 100"
                  className="text-warroom-border"
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className={`text-2xl font-bold ${getScoreColor(simulationResult.viral_score)}`}>
                  {simulationResult.viral_score}
                </span>
              </div>
            </div>
            <div className="text-center">
              <p className="text-lg font-medium">Viral Potential Score</p>
              <p className="text-sm text-warroom-muted">
                Predicted Engagement: {(simulationResult.engagement_rate * 100).toFixed(1)}%
              </p>
            </div>
          </div>
        </div>

        {/* Sentiment Breakdown */}
        <div>
          <h4 className="font-medium mb-3">Audience Sentiment</h4>
          <div className="space-y-2">
            {simulationResult.sentiment && Object.entries(simulationResult.sentiment).map(([sentiment, value]) => (
              <div key={sentiment} className="flex items-center">
                <span className="w-20 text-sm capitalize">{sentiment}</span>
                <div className="flex-1 bg-warroom-border rounded-full h-2 mx-3">
                  <div 
                    className={`h-2 rounded-full ${
                      sentiment === 'positive' ? 'bg-green-400' :
                      sentiment === 'neutral' ? 'bg-yellow-400' :
                      'bg-red-400'
                    }`}
                    style={{ width: `${value * 100}%` }}
                  />
                </div>
                <span className="text-sm font-medium w-12">{(value * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </div>

        {/* Recommendations */}
        <div>
          <h4 className="font-medium mb-3">Recommendations</h4>
          <div className="space-y-3">
            {Array.isArray(simulationResult.recommendations) && simulationResult.recommendations.map((rec, index) => (
              <div key={index} className="bg-warroom-bg border border-warroom-border rounded-lg p-4">
                <div className="flex items-start space-x-3">
                  <div className={`w-2 h-2 rounded-full mt-2 ${
                    rec.priority === 'high' ? 'bg-red-400' :
                    rec.priority === 'medium' ? 'bg-yellow-400' :
                    'bg-blue-400'
                  }`} />
                  <div className="flex-1">
                    <p className="font-medium">{rec.suggestion}</p>
                    <p className="text-sm text-warroom-muted mt-1">{rec.reasoning}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="text-center text-sm text-warroom-muted">
          Based on {simulationResult.personas_used} audience personas
        </div>
      </div>
    );
  };

  return (
    <div className="h-full bg-warroom-bg text-warroom-text overflow-auto">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="bg-warroom-card border-b border-warroom-border p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Brain className="h-8 w-8 text-warroom-accent" />
              <div>
                <h1 className="text-2xl font-semibold">MiroFish Simulation</h1>
                <p className="text-warroom-muted">Predictive content performance analysis</p>
              </div>
            </div>
          </div>
        </div>

        {/* Sub Navigation */}
        {renderSubTabs()}

        {/* Content */}
        <div className="p-6 space-y-6">
          {activeSubTab === 'pre-publish' && renderPrePublishSimulator()}
          {activeSubTab === 'post-publish' && renderPostPublishAnalyzer()}
          {activeSubTab === 'sandbox' && renderContentSandbox()}
          
          {/* Simulation Button */}
          {renderSimulationButton()}

          {/* Error Display */}
          {error && (
            <div className="bg-red-900/20 border border-red-500/50 rounded-lg p-4 flex items-start space-x-3">
              <AlertCircle className="h-5 w-5 text-red-400 mt-0.5 flex-shrink-0" />
              <div>
                <h4 className="font-medium text-red-400">Simulation Error</h4>
                <p className="text-sm text-red-300 mt-1">{error}</p>
              </div>
            </div>
          )}

          {/* Results */}
          {renderResults()}
        </div>
      </div>
    </div>
  );
}