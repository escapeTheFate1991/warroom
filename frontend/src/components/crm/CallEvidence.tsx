"use client";

import { useState } from "react";
import { ExternalLink, FileText, Play } from "lucide-react";

type ActivityWithCallEvidence = {
  additional?: Record<string, unknown> | null;
};

type CallEvidenceProps = {
  recordingUrl?: string | null;
  transcript?: string | null;
  className?: string;
};

function normalizeText(value?: string | null) {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function readAdditionalString(activity: ActivityWithCallEvidence, ...keys: string[]) {
  const additional = activity.additional;
  if (!additional || typeof additional !== "object") return null;
  for (const key of keys) {
    const value = additional[key];
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return null;
}

export function getCallEvidence(activity: ActivityWithCallEvidence) {
  return {
    recordingUrl: readAdditionalString(activity, "recording_url"),
    transcript: readAdditionalString(activity, "transcript"),
  };
}

export default function CallEvidence({ recordingUrl, transcript, className = "mt-3" }: CallEvidenceProps) {
  const [showPlayer, setShowPlayer] = useState(false);
  const [showTranscript, setShowTranscript] = useState(false);
  const safeRecordingUrl = normalizeText(recordingUrl);
  const safeTranscript = normalizeText(transcript);

  return (
    <div className={className}>
      <div className="flex flex-wrap items-center gap-2 text-xs">
        {safeRecordingUrl ? (
          <>
            <button
              type="button"
              onClick={() => setShowPlayer((current) => !current)}
              className="inline-flex items-center gap-1.5 rounded-md border border-warroom-border bg-warroom-border/30 px-2.5 py-1 text-warroom-text transition hover:bg-warroom-border/50"
            >
              <Play size={12} />
              {showPlayer ? "Hide player" : "Play recording"}
            </button>
            <a
              href={safeRecordingUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 rounded-md border border-warroom-border bg-warroom-border/20 px-2.5 py-1 text-warroom-text transition hover:bg-warroom-border/40"
            >
              <ExternalLink size={12} />
              Open recording
            </a>
          </>
        ) : (
          <span className="text-warroom-muted">Recording unavailable</span>
        )}

        {safeTranscript ? (
          <button
            type="button"
            onClick={() => setShowTranscript((current) => !current)}
            className="inline-flex items-center gap-1.5 rounded-md border border-warroom-border bg-warroom-border/20 px-2.5 py-1 text-warroom-text transition hover:bg-warroom-border/40"
          >
            <FileText size={12} />
            {showTranscript ? "Hide transcript" : "View transcript"}
          </button>
        ) : (
          <span className="text-warroom-muted">Transcript unavailable</span>
        )}
      </div>

      {showPlayer && safeRecordingUrl && (
        <audio controls autoPlay preload="none" className="mt-2 h-10 w-full max-w-md" src={safeRecordingUrl}>
          Your browser does not support audio playback.
        </audio>
      )}

      {showTranscript && safeTranscript && (
        <div className="mt-2 rounded-lg border border-warroom-border bg-warroom-bg/60 p-3">
          <div className="text-[11px] font-medium uppercase tracking-wide text-warroom-muted">Transcript</div>
          <p className="mt-2 whitespace-pre-wrap text-xs leading-5 text-warroom-text/90">{safeTranscript}</p>
        </div>
      )}
    </div>
  );
}