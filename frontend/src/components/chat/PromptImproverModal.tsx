"use client";

import { useState, useRef, useEffect } from "react";
import { X, Sparkles, Send, Loader2, ArrowRight, CheckCircle } from "lucide-react";

interface PromptImproverModalProps {
  originalPrompt: string;
  questions: string[];
  contextSummary?: string;
  onSubmit: (answers: string[]) => void;
  onSkip: () => void;
  onCancel: () => void;
  isImproving: boolean;
}

export default function PromptImproverModal({
  originalPrompt,
  questions,
  contextSummary,
  onSubmit,
  onSkip,
  onCancel,
  isImproving,
}: PromptImproverModalProps) {
  const [answers, setAnswers] = useState<string[]>(questions.map(() => ""));
  const firstInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    firstInputRef.current?.focus();
  }, []);

  const updateAnswer = (idx: number, val: string) => {
    setAnswers(prev => {
      const next = [...prev];
      next[idx] = val;
      return next;
    });
  };

  const handleSubmit = () => {
    onSubmit(answers);
  };

  const handleKeyDown = (e: React.KeyboardEvent, idx: number) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (idx < questions.length - 1) {
        // Focus next input
        const nextInput = document.querySelector(`[data-qi="${idx + 1}"]`) as HTMLInputElement;
        nextInput?.focus();
      } else {
        handleSubmit();
      }
    }
  };

  const filledCount = answers.filter(a => a.trim()).length;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-warroom-surface border border-warroom-border rounded-2xl shadow-2xl w-full max-w-lg mx-4 max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-warroom-border">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-warroom-accent/10 flex items-center justify-center">
              <Sparkles size={16} className="text-warroom-accent" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-warroom-text">Prompt Improver</h3>
              <p className="text-[10px] text-warroom-muted">A few quick questions to improve your prompt</p>
            </div>
          </div>
          <button
            onClick={onCancel}
            className="p-1.5 rounded-lg hover:bg-warroom-border/50 text-warroom-muted hover:text-warroom-text transition"
          >
            <X size={16} />
          </button>
        </div>

        {/* Original prompt preview */}
        <div className="px-5 pt-3">
          <div className="bg-warroom-bg/50 border border-warroom-border/50 rounded-xl px-3 py-2">
            <p className="text-[10px] text-warroom-muted uppercase tracking-wide mb-1">Your prompt</p>
            <p className="text-xs text-warroom-text line-clamp-3">{originalPrompt}</p>
          </div>
          {contextSummary && (
            <p className="text-[10px] text-warroom-muted mt-2 px-1">
              <span className="text-warroom-accent">Understanding:</span> {contextSummary}
            </p>
          )}
        </div>

        {/* Questions */}
        <div className="flex-1 overflow-y-auto px-5 py-3 space-y-3">
          {questions.map((q, idx) => (
            <div key={idx} className="space-y-1.5">
              <label className="text-xs text-warroom-text font-medium flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-warroom-accent/10 text-warroom-accent text-[10px] flex items-center justify-center font-bold flex-shrink-0">
                  {idx + 1}
                </span>
                {q}
              </label>
              <input
                ref={idx === 0 ? firstInputRef : undefined}
                data-qi={idx}
                type="text"
                value={answers[idx]}
                onChange={(e) => updateAnswer(idx, e.target.value)}
                onKeyDown={(e) => handleKeyDown(e, idx)}
                placeholder="Type your answer..."
                className="w-full bg-warroom-bg border border-warroom-border rounded-xl px-3 py-2 text-sm text-warroom-text placeholder-warroom-muted/50 focus:outline-none focus:border-warroom-accent/50 transition"
              />
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-5 py-3 border-t border-warroom-border bg-warroom-surface">
          <button
            onClick={onSkip}
            className="text-xs text-warroom-muted hover:text-warroom-text transition px-3 py-1.5 rounded-lg hover:bg-warroom-border/30"
          >
            Send as-is
          </button>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-warroom-muted">
              {filledCount}/{questions.length} answered
            </span>
            <button
              onClick={handleSubmit}
              disabled={filledCount === 0 || isImproving}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-warroom-accent text-white text-sm font-medium hover:bg-warroom-accent/80 disabled:opacity-40 transition"
            >
              {isImproving ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  Improving...
                </>
              ) : (
                <>
                  <ArrowRight size={14} />
                  Improve & Send
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
