"use client";

import React from "react";
import { Brain, Clock } from "lucide-react";

interface TranscriptSegment {
  type: string;
  label: string;
  start_time: number;
  end_time: number;
  text: string;
  psych_mechanism?: string;
}

interface VideoRecord {
  transcript?: {
    full?: string;
    segments?: TranscriptSegment[];
  };
  runtime_seconds?: number;
  runtime?: {
    seconds: number;
    display: string;
  };
}

interface TranscriptTabProps {
  videoRecord: VideoRecord;
}

// Psychological mechanism taxonomy
const PSYCHOLOGICAL_MECHANISMS = {
  curiosity_gap: "Curiosity gap + Open loops",
  pain_agitation: "Pain agitation + Problem awareness", 
  social_proof: "Social proof + Validation seeking",
  authority_transfer: "Authority transfer + Expert positioning",
  scarcity_urgency: "Scarcity + Urgency framing",
  identity_play: "Identity play + Tribal belonging",
  actionability: "Actionability — immediate concrete step",
  ease_framing: "Ease framing + Low effort positioning"
} as const;

// Mechanism colors for visual consistency
const MECHANISM_COLORS: Record<string, string> = {
  curiosity_gap: "bg-purple-400/10 text-purple-400 border-purple-400/20",
  pain_agitation: "bg-red-400/10 text-red-400 border-red-400/20",
  social_proof: "bg-blue-400/10 text-blue-400 border-blue-400/20",
  authority_transfer: "bg-yellow-400/10 text-yellow-400 border-yellow-400/20",
  scarcity_urgency: "bg-orange-400/10 text-orange-400 border-orange-400/20",
  identity_play: "bg-green-400/10 text-green-400 border-green-400/20",
  actionability: "bg-cyan-400/10 text-cyan-400 border-cyan-400/20",
  ease_framing: "bg-pink-400/10 text-pink-400 border-pink-400/20",
};

// Default fallback mechanism color
const DEFAULT_MECHANISM_COLOR = "bg-warroom-border/30 text-warroom-muted border-warroom-border/30";

// Format seconds to M:SS format
function formatTimestamp(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Infer psychological mechanism from segment content
function inferPsychMechanism(segment: TranscriptSegment): string {
  const text = segment.text.toLowerCase();
  const type = segment.type.toLowerCase();
  
  // Use existing mechanism if present
  if (segment.psych_mechanism && PSYCHOLOGICAL_MECHANISMS[segment.psych_mechanism as keyof typeof PSYCHOLOGICAL_MECHANISMS]) {
    return PSYCHOLOGICAL_MECHANISMS[segment.psych_mechanism as keyof typeof PSYCHOLOGICAL_MECHANISMS];
  }
  
  // Hook inference patterns
  if (type === "hook") {
    if (text.includes("secret") || text.includes("nobody") || text.includes("what if") || text.includes("imagine")) {
      return PSYCHOLOGICAL_MECHANISMS.curiosity_gap;
    }
    if (text.includes("struggling") || text.includes("problem") || text.includes("tired of") || text.includes("sick of")) {
      return PSYCHOLOGICAL_MECHANISMS.pain_agitation;
    }
    if (text.includes("everyone") || text.includes("most people") || text.includes("studies show") || text.includes("experts")) {
      return PSYCHOLOGICAL_MECHANISMS.social_proof;
    }
    if (text.includes("proven") || text.includes("research") || text.includes("discovered") || text.includes("method")) {
      return PSYCHOLOGICAL_MECHANISMS.authority_transfer;
    }
    if (text.includes("limited") || text.includes("only") || text.includes("now") || text.includes("quick")) {
      return PSYCHOLOGICAL_MECHANISMS.scarcity_urgency;
    }
  }
  
  // Value beat inference patterns
  if (type === "value_beat" || type.startsWith("value")) {
    if (text.includes("step") || text.includes("how to") || text.includes("here's what") || text.includes("you need to")) {
      return PSYCHOLOGICAL_MECHANISMS.actionability;
    }
    if (text.includes("simple") || text.includes("easy") || text.includes("just") || text.includes("only takes")) {
      return PSYCHOLOGICAL_MECHANISMS.ease_framing;
    }
    if (text.includes("people like you") || text.includes("your type") || text.includes("if you're")) {
      return PSYCHOLOGICAL_MECHANISMS.identity_play;
    }
    if (text.includes("studies") || text.includes("research") || text.includes("data") || text.includes("proven")) {
      return PSYCHOLOGICAL_MECHANISMS.authority_transfer;
    }
  }
  
  // CTA inference patterns
  if (type === "cta") {
    if (text.includes("now") || text.includes("today") || text.includes("before") || text.includes("limited")) {
      return PSYCHOLOGICAL_MECHANISMS.scarcity_urgency;
    }
    if (text.includes("easy") || text.includes("simple") || text.includes("quick") || text.includes("just")) {
      return PSYCHOLOGICAL_MECHANISMS.ease_framing;
    }
  }
  
  // Default mechanisms by segment type
  switch (type) {
    case "hook":
      return PSYCHOLOGICAL_MECHANISMS.curiosity_gap;
    case "value_beat":
    case "value":
      return PSYCHOLOGICAL_MECHANISMS.actionability;
    case "cta":
      return PSYCHOLOGICAL_MECHANISMS.scarcity_urgency;
    default:
      return PSYCHOLOGICAL_MECHANISMS.actionability;
  }
}

// Get effectiveness rating based on content analysis
function getEffectivenessRating(segment: TranscriptSegment): "Strong" | "Moderate" | "Weak" {
  const text = segment.text;
  const type = segment.type;
  
  // Strong indicators
  if (text.length > 50 && (
    text.includes("secret") || 
    text.includes("nobody tells you") ||
    text.includes("step-by-step") ||
    text.includes("exactly how") ||
    text.includes("proven method")
  )) {
    return "Strong";
  }
  
  // Weak indicators  
  if (text.length < 20 || text.includes("umm") || text.includes("like, you know")) {
    return "Weak";
  }
  
  // Hook effectiveness
  if (type === "hook") {
    if (text.includes("?") || text.includes("what if") || text.includes("imagine")) {
      return "Strong";
    }
    if (text.length < 30) {
      return "Weak";
    }
  }
  
  return "Moderate";
}

// Get effectiveness color
function getEffectivenessColor(rating: "Strong" | "Moderate" | "Weak"): string {
  switch (rating) {
    case "Strong":
      return "text-green-400";
    case "Moderate":
      return "text-yellow-400";
    case "Weak":
      return "text-red-400";
    default:
      return "text-warroom-muted";
  }
}

export default function TranscriptTab({ videoRecord }: TranscriptTabProps) {
  const transcript = videoRecord.transcript;
  
  if (!transcript || !transcript.segments || transcript.segments.length === 0) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="text-center py-16 text-warroom-muted">
          <Brain size={48} className="mx-auto mb-4 opacity-20" />
          <p className="text-lg font-medium text-warroom-text">No transcript available</p>
          <p className="text-sm mt-2">Transcript processing may still be in progress</p>
        </div>
      </div>
    );
  }

  const segments = transcript.segments;

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="flex items-center gap-2">
          <Brain size={20} className="text-warroom-accent" />
          <h2 className="text-lg font-semibold">Core Beats Analysis</h2>
        </div>
        <div className="text-sm text-warroom-muted">
          {segments.length} segments • {transcript.full ? `${transcript.full.split(' ').length} words` : 'Processing...'}
        </div>
      </div>

      {/* Transcript Segments */}
      <div className="space-y-4">
        {segments.map((segment, index) => {
          const mechanism = inferPsychMechanism(segment);
          const effectiveness = getEffectivenessRating(segment);
          const mechanismKey = Object.keys(PSYCHOLOGICAL_MECHANISMS).find(
            key => PSYCHOLOGICAL_MECHANISMS[key as keyof typeof PSYCHOLOGICAL_MECHANISMS] === mechanism
          );
          const mechanismColor = mechanismKey ? MECHANISM_COLORS[mechanismKey] : DEFAULT_MECHANISM_COLOR;

          return (
            <div
              key={index}
              className="bg-warroom-surface border border-warroom-border rounded-lg p-6 space-y-4"
            >
              {/* Header Row */}
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-3">
                  {/* Section Type */}
                  <span className="px-3 py-1 bg-warroom-accent/20 text-warroom-accent rounded-full text-sm font-medium">
                    {segment.label}
                  </span>
                  
                  {/* Time Range */}
                  <div className="flex items-center gap-1 text-sm text-warroom-muted">
                    <Clock size={14} />
                    <span>
                      {formatTimestamp(segment.start_time)}–{formatTimestamp(segment.end_time)}
                    </span>
                  </div>
                </div>

                {/* Effectiveness Rating */}
                <span className={`text-sm font-medium ${getEffectivenessColor(effectiveness)}`}>
                  {effectiveness}
                </span>
              </div>

              {/* Transcript Text */}
              <div className="bg-warroom-bg rounded-lg p-4 border border-warroom-border/50">
                <p className="text-warroom-text leading-relaxed">
                  {segment.text || "No transcript text available"}
                </p>
              </div>

              {/* Psychological Mechanism */}
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2">
                  <Brain size={16} className="text-warroom-muted" />
                  <span className="text-sm text-warroom-muted">Psychology:</span>
                </div>
                <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm font-medium ${mechanismColor}`}>
                  🧠
                  <span>{mechanism}</span>
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Full Transcript (if available and different from segments) */}
      {transcript.full && transcript.full.trim() !== segments.map(s => s.text).join(' ').trim() && (
        <div className="mt-8 pt-6 border-t border-warroom-border">
          <h3 className="text-sm font-medium text-warroom-muted mb-3">Full Transcript</h3>
          <div className="bg-warroom-surface border border-warroom-border rounded-lg p-4">
            <p className="text-sm text-warroom-muted leading-relaxed">
              {transcript.full}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}