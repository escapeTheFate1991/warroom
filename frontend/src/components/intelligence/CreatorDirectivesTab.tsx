"use client";

import React, { useState, useEffect } from "react";
import { CheckCircle, AlertTriangle, Beaker, Users, MessageSquare, HelpCircle, Share, Lightbulb, Film } from "lucide-react";
import { API, authFetch } from "@/lib/api";

interface CDRResponse {
  success: boolean;
  post_id: number;
  power_score: number;
  dominant_intent: string;
  hook_directive: {
    script_line: string;
    visual_style: string;
    audio_note: string;
  };
  retention_blueprint: {
    pacing_rules: string[];
    interrupts: string[];
    anti_boredom_triggers: string[];
  };
  share_catalyst: {
    identity_moment: string;
    viral_framework: string;
    shareability_score: string;
  };
  conversion_close: {
    cta_type: string;
    script_line: string;
    positioning_note: string;
  };
  technical_specs: {
    video_length: string;
    visual_style: string;
    production_notes: string[];
  };
  generated_at: string;
}

interface AudienceInsight {
  text: string;
  count: number;
  usage_hint: string;
  type: "objection" | "question" | "trigger";
}

interface CreatorDirectivesData {
  cdr: CDRResponse | null;
  audience_intelligence: {
    objections: AudienceInsight[];
    questions: AudienceInsight[];
    sharing_triggers: AudienceInsight[];
    total_comments_analyzed: number;
  };
}

interface CreatorDirectivesTabProps {
  videoId: string;
}

const CategoryIcon = ({ category }: { category: string }) => {
  switch (category) {
    case "replicate":
      return <CheckCircle className="text-green-500" size={16} />;
    case "avoid":
      return <AlertTriangle className="text-red-500" size={16} />;
    case "test":
      return <Beaker className="text-blue-500" size={16} />;
    default:
      return <CheckCircle className="text-gray-500" size={16} />;
  }
};

const InsightIcon = ({ type }: { type: string }) => {
  switch (type) {
    case "objection":
      return <AlertTriangle className="text-orange-500" size={14} />;
    case "question":
      return <HelpCircle className="text-blue-500" size={14} />;
    case "trigger":
      return <Share className="text-purple-500" size={14} />;
    default:
      return <MessageSquare className="text-gray-500" size={14} />;
  }
};

export default function CreatorDirectivesTab({ videoId }: CreatorDirectivesTabProps) {
  const [data, setData] = useState<CreatorDirectivesData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    const fetchCreatorDirectives = async () => {
      try {
        setLoading(true);
        setError("");

        // Fetch creator directives (CDR)
        const directivesResponse = await authFetch(
          `${API}/api/content-intel/creator-directive/${videoId}`,
          { method: "POST" }
        );

        // Fetch audience intelligence  
        const audienceResponse = await authFetch(
          `${API}/api/content-intel/audience-intelligence/${videoId}`
        );

        let cdrData = null;
        let audienceData = null;

        // Handle CDR response (may not exist for all posts)
        if (directivesResponse.ok) {
          cdrData = await directivesResponse.json();
        } else if (directivesResponse.status !== 404 && directivesResponse.status !== 400) {
          console.warn("CDR generation failed:", directivesResponse.status);
        }

        // Handle audience intelligence response
        if (audienceResponse.ok) {
          audienceData = await audienceResponse.json();
        } else if (audienceResponse.status !== 404) {
          setError("Failed to load audience intelligence");
          return;
        }

        setData({
          cdr: cdrData,
          audience_intelligence: {
            objections: audienceData?.objections || [],
            questions: audienceData?.questions || [],
            sharing_triggers: audienceData?.emotional_triggers || [],
            total_comments_analyzed: audienceData?.total_comments_analyzed || 0,
          },
        });
      } catch (err) {
        console.error("Error fetching creator directives:", err);
        setError("Error connecting to API");
      } finally {
        setLoading(false);
      }
    };

    fetchCreatorDirectives();
  }, [videoId]);

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-center py-16">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-warroom-accent"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-6xl mx-auto">
        <div className="text-center py-16">
          <AlertTriangle size={48} className="mx-auto mb-4 text-red-400 opacity-50" />
          <p className="text-lg font-medium text-warroom-text">{error}</p>
          <p className="text-sm mt-2 text-warroom-muted">
            Make sure this video has been analyzed and has comment data available.
          </p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="max-w-6xl mx-auto">
        <div className="text-center py-16">
          <Lightbulb size={48} className="mx-auto mb-4 text-warroom-muted opacity-20" />
          <p className="text-lg font-medium text-warroom-text">No directives available</p>
          <p className="text-sm mt-2 text-warroom-muted">
            Run video analysis to generate creator directives for this content.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Section 1: Structural Directives */}
      <div className="bg-warroom-surface border border-warroom-border rounded-xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 bg-warroom-gradient/20 rounded-lg flex items-center justify-center">
            <CheckCircle size={20} className="text-warroom-accent" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-warroom-text">Structural Directives</h2>
            <p className="text-sm text-warroom-muted">
              Creator directive report with actionable video creation instructions
            </p>
          </div>
        </div>

        {!data.cdr ? (
          <div className="text-center py-8">
            <p className="text-warroom-muted">No creator directives available for this video.</p>
            <p className="text-xs text-warroom-muted mt-2">
              CDR generation requires high-performing content with sufficient engagement data.
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Power Score & Intent */}
            <div className="bg-warroom-bg border border-warroom-border rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-warroom-text">Performance Analysis</h3>
                <span className="text-xs text-warroom-muted">
                  Generated {new Date(data.cdr.generated_at).toLocaleDateString()}
                </span>
              </div>
              <div className="flex gap-4">
                <div>
                  <span className="text-sm text-warroom-muted">Power Score:</span>
                  <span className="ml-2 font-bold text-warroom-accent">{data.cdr.power_score.toFixed(0)}</span>
                </div>
                <div>
                  <span className="text-sm text-warroom-muted">Dominant Intent:</span>
                  <span className="ml-2 font-medium text-warroom-text capitalize">{data.cdr.dominant_intent}</span>
                </div>
              </div>
            </div>

            {/* Hook Directive */}
            <div className="border border-warroom-border rounded-lg p-4 bg-warroom-bg/50">
              <div className="flex items-start gap-3">
                <CheckCircle className="text-green-500" size={16} />
                <div className="flex-1 min-w-0">
                  <h4 className="text-warroom-text font-medium mb-2">✅ Hook Directive</h4>
                  <p className="text-sm text-warroom-text mb-2 font-medium">
                    "{data.cdr.hook_directive.script_line}"
                  </p>
                  <div className="space-y-1 text-xs text-warroom-muted">
                    <p><strong>Visual:</strong> {data.cdr.hook_directive.visual_style}</p>
                    <p><strong>Audio:</strong> {data.cdr.hook_directive.audio_note}</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Retention Blueprint */}
            <div className="border border-warroom-border rounded-lg p-4 bg-warroom-bg/50">
              <div className="flex items-start gap-3">
                <Beaker className="text-blue-500" size={16} />
                <div className="flex-1 min-w-0">
                  <h4 className="text-warroom-text font-medium mb-2">🧪 Retention Blueprint</h4>
                  <div className="space-y-2 text-sm text-warroom-muted">
                    {data.cdr.retention_blueprint.pacing_rules.length > 0 && (
                      <div>
                        <strong className="text-warroom-text">Pacing Rules:</strong>
                        <ul className="ml-4 list-disc">
                          {data.cdr.retention_blueprint.pacing_rules.map((rule, i) => (
                            <li key={i}>{rule}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Share Catalyst */}
            <div className="border border-warroom-border rounded-lg p-4 bg-warroom-bg/50">
              <div className="flex items-start gap-3">
                <Share className="text-purple-500" size={16} />
                <div className="flex-1 min-w-0">
                  <h4 className="text-warroom-text font-medium mb-2">🔥 Share Catalyst</h4>
                  <p className="text-sm text-warroom-text mb-2">
                    <strong>Identity Moment:</strong> {data.cdr.share_catalyst.identity_moment}
                  </p>
                  <p className="text-xs text-warroom-muted">
                    <strong>Viral Framework:</strong> {data.cdr.share_catalyst.viral_framework}
                  </p>
                </div>
              </div>
            </div>

            {/* Conversion Close */}
            <div className="border border-warroom-border rounded-lg p-4 bg-warroom-bg/50">
              <div className="flex items-start gap-3">
                <CheckCircle className="text-green-500" size={16} />
                <div className="flex-1 min-w-0">
                  <h4 className="text-warroom-text font-medium mb-2">💰 Conversion Close</h4>
                  <p className="text-sm text-warroom-text mb-2">
                    <strong>CTA Type:</strong> {data.cdr.conversion_close.cta_type}
                  </p>
                  <p className="text-sm text-warroom-text mb-1">
                    "{data.cdr.conversion_close.script_line}"
                  </p>
                  <p className="text-xs text-warroom-muted">
                    {data.cdr.conversion_close.positioning_note}
                  </p>
                </div>
              </div>
            </div>

            {/* Technical Specs */}
            <div className="border border-warroom-border rounded-lg p-4 bg-warroom-bg/50">
              <div className="flex items-start gap-3">
                <Film className="text-orange-500" size={16} />
                <div className="flex-1 min-w-0">
                  <h4 className="text-warroom-text font-medium mb-2">🎬 Technical Specs</h4>
                  <div className="space-y-1 text-sm text-warroom-muted">
                    <p><strong>Length:</strong> {data.cdr.technical_specs.video_length}</p>
                    <p><strong>Style:</strong> {data.cdr.technical_specs.visual_style}</p>
                    {data.cdr.technical_specs.production_notes && data.cdr.technical_specs.production_notes.length > 0 && (
                      <div>
                        <strong>Production Notes:</strong>
                        <ul className="ml-4 list-disc">
                          {data.cdr.technical_specs.production_notes.map((note, i) => (
                            <li key={i}>{note}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Section 2: Audience Intelligence */}
      <div className="bg-warroom-surface border border-warroom-border rounded-xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 bg-warroom-gradient/20 rounded-lg flex items-center justify-center">
            <Users size={20} className="text-warroom-accent" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-warroom-text">Audience Intelligence</h2>
            <p className="text-sm text-warroom-muted">
              Insights extracted from {data.audience_intelligence.total_comments_analyzed} comments on this video
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Objections */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 mb-4">
              <AlertTriangle size={18} className="text-orange-500" />
              <h3 className="font-medium text-warroom-text">Top Objections</h3>
            </div>
            {data.audience_intelligence.objections.length === 0 ? (
              <p className="text-sm text-warroom-muted italic">No objections identified</p>
            ) : (
              data.audience_intelligence.objections.map((objection, index) => (
                <div
                  key={index}
                  className="bg-warroom-bg border border-warroom-border rounded-lg p-3"
                >
                  <div className="flex items-start gap-2 mb-2">
                    <InsightIcon type="objection" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-warroom-text">
                        {objection.text}
                      </p>
                      <p className="text-xs text-warroom-muted mt-1">
                        Mentioned {objection.count} times
                      </p>
                    </div>
                  </div>
                  <div className="ml-6">
                    <p className="text-xs text-blue-400 font-medium">→ Usage hint:</p>
                    <p className="text-xs text-warroom-muted leading-relaxed">
                      {objection.usage_hint}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Questions */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 mb-4">
              <HelpCircle size={18} className="text-blue-500" />
              <h3 className="font-medium text-warroom-text">Top Questions</h3>
            </div>
            {data.audience_intelligence.questions.length === 0 ? (
              <p className="text-sm text-warroom-muted italic">No questions identified</p>
            ) : (
              data.audience_intelligence.questions.map((question, index) => (
                <div
                  key={index}
                  className="bg-warroom-bg border border-warroom-border rounded-lg p-3"
                >
                  <div className="flex items-start gap-2 mb-2">
                    <InsightIcon type="question" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-warroom-text">
                        {question.text}
                      </p>
                      <p className="text-xs text-warroom-muted mt-1">
                        Asked {question.count} times
                      </p>
                    </div>
                  </div>
                  <div className="ml-6">
                    <p className="text-xs text-green-400 font-medium">→ Content gap opportunity:</p>
                    <p className="text-xs text-warroom-muted leading-relaxed">
                      {question.usage_hint}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Sharing Triggers */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 mb-4">
              <Share size={18} className="text-purple-500" />
              <h3 className="font-medium text-warroom-text">Sharing Triggers</h3>
            </div>
            {data.audience_intelligence.sharing_triggers.length === 0 ? (
              <p className="text-sm text-warroom-muted italic">No sharing triggers identified</p>
            ) : (
              data.audience_intelligence.sharing_triggers.map((trigger, index) => (
                <div
                  key={index}
                  className="bg-warroom-bg border border-warroom-border rounded-lg p-3"
                >
                  <div className="flex items-start gap-2 mb-2">
                    <InsightIcon type="trigger" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-warroom-text">
                        {trigger.text}
                      </p>
                      <p className="text-xs text-warroom-muted mt-1">
                        Triggered {trigger.count} shares
                      </p>
                    </div>
                  </div>
                  <div className="ml-6">
                    <p className="text-xs text-purple-400 font-medium">→ What to do:</p>
                    <p className="text-xs text-warroom-muted leading-relaxed">
                      {trigger.usage_hint}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}