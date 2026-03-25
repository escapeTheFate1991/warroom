"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import {
  Film, Loader2, Wand2, Play, ChevronRight, RefreshCw, CheckCircle,
  AlertCircle, Palette, Type, Image as ImageIcon, Sparkles, Download,
  Eye, Settings2,
} from "lucide-react";
import { Player } from "@remotion/player";
import { API, authFetch } from "@/lib/api";
import { ProductShowcase, type ProductShowcaseProps } from "./remotion/ProductShowcase";
import { SocialMediaAd, type SocialMediaAdProps } from "./remotion/SocialMediaAd";
import { Testimonial, type TestimonialProps } from "./remotion/Testimonial";

/* ── Types ─────────────────────────────────────────────── */
interface RemotionTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  compositionId: string;
  durationFrames: number;
  fps: number;
  width: number;
  height: number;
  defaultProps: Record<string, unknown>;
  thumbnailUrl: string | null;
}

interface StoryboardResult {
  templateId: string;
  title: string;
  props: Record<string, unknown>;
  scenes: Array<{
    scene: number;
    label: string;
    seconds: string;
    description: string;
  }>;
}

type EditorStep = "template" | "customize" | "preview";

/* ── Composition Map ───────────────────────────────────── */
const COMPOSITION_MAP: Record<string, React.FC<any>> = {
  ProductShowcase,
  SocialMediaAd,
  Testimonial,
};

/* ── Component ─────────────────────────────────────────── */
export default function VideoEditor() {
  const [templates, setTemplates] = useState<RemotionTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<EditorStep>("template");

  // Selected template & props
  const [selectedTemplate, setSelectedTemplate] = useState<RemotionTemplate | null>(null);
  const [editableProps, setEditableProps] = useState<Record<string, unknown>>({});

  // AI storyboard
  const [aiPrompt, setAiPrompt] = useState("");
  const [generatingStoryboard, setGeneratingStoryboard] = useState(false);

  // Render
  const [rendering, setRendering] = useState(false);
  const [renderResult, setRenderResult] = useState<{ ok: boolean; message?: string; error?: string } | null>(null);

  // ── Fetch templates ──────────────────────────────────
  const fetchTemplates = useCallback(async () => {
    setLoading(true);
    try {
      const r = await authFetch(`${API}/api/video/templates`);
      if (r.ok) {
        const d = await r.json();
        setTemplates(d.templates || []);
      }
    } catch { }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  // ── Select template ──────────────────────────────────
  const selectTemplate = (tpl: RemotionTemplate) => {
    setSelectedTemplate(tpl);
    setEditableProps({ ...tpl.defaultProps });
    setStep("customize");
  };

  // ── AI Storyboard ────────────────────────────────────
  const generateStoryboard = async () => {
    if (!aiPrompt.trim()) return;
    setGeneratingStoryboard(true);
    try {
      const r = await authFetch(`${API}/api/video/storyboard`, {
        method: "POST",
        body: JSON.stringify({ prompt: aiPrompt, duration_seconds: 15 }),
      });
      if (r.ok) {
        const d = await r.json();
        const sb: StoryboardResult = d.storyboard;
        if (sb) {
          // Find matching template
          const matchedTpl = templates.find(t => t.id === sb.templateId);
          if (matchedTpl) {
            setSelectedTemplate(matchedTpl);
            setEditableProps({ ...matchedTpl.defaultProps, ...sb.props });
            setStep("customize");
          } else if (templates.length > 0) {
            // Fallback to first template
            setSelectedTemplate(templates[0]);
            setEditableProps({ ...templates[0].defaultProps, ...sb.props });
            setStep("customize");
          }
        }
      }
    } catch { }
    setGeneratingStoryboard(false);
  };

  // ── Render ───────────────────────────────────────────
  const startRender = async () => {
    if (!selectedTemplate) return;
    setRendering(true);
    setRenderResult(null);
    try {
      const r = await authFetch(`${API}/api/video/render`, {
        method: "POST",
        body: JSON.stringify({
          template_id: selectedTemplate.id,
          props: editableProps,
          title: (editableProps.headline as string) || selectedTemplate.name,
        }),
      });
      const d = await r.json();
      if (r.ok) {
        setRenderResult({ ok: true, message: d.message });
      } else {
        setRenderResult({ ok: false, error: d.detail || "Render failed" });
      }
    } catch (e: any) {
      setRenderResult({ ok: false, error: e.message });
    }
    setRendering(false);
  };

  // ── Update a prop ────────────────────────────────────
  const updateProp = (key: string, value: unknown) => {
    setEditableProps(prev => ({ ...prev, [key]: value }));
  };

  // ── Get composition component ────────────────────────
  const CompositionComponent = selectedTemplate
    ? COMPOSITION_MAP[selectedTemplate.compositionId]
    : null;

  // ── Steps ────────────────────────────────────────────
  const steps = [
    { id: "template" as const, label: "Template" },
    { id: "customize" as const, label: "Customize" },
    { id: "preview" as const, label: "Preview & Export" },
  ];
  const stepIdx = steps.findIndex(s => s.id === step);

  return (
    <div className="p-5 space-y-5">
      {/* Step indicator */}
      <div className="flex items-center gap-1 mb-2">
        {steps.map((s, i) => (
          <div key={s.id} className="flex items-center">
            <button
              onClick={() => { if (i <= stepIdx) setStep(s.id); }}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition ${
                i === stepIdx
                  ? "bg-warroom-accent text-white"
                  : i < stepIdx
                  ? "bg-warroom-accent/20 text-warroom-accent cursor-pointer"
                  : "bg-warroom-bg text-warroom-muted"
              }`}
            >
              <span className="w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold border border-current">
                {i + 1}
              </span>
              <span className="hidden sm:inline">{s.label}</span>
            </button>
            {i < steps.length - 1 && <ChevronRight size={14} className="text-warroom-border mx-0.5" />}
          </div>
        ))}
      </div>

      {step === "template" && renderTemplateStep()}
      {step === "customize" && renderCustomizeStep()}
      {step === "preview" && renderPreviewStep()}
    </div>
  );

  /* ═══════════════════════════════════════════════════════
   *  Step 1: Template Selection
   * ═══════════════════════════════════════════════════════ */
  function renderTemplateStep() {
    return (
      <div className="space-y-5">
        {/* AI Prompt */}
        <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
          <h3 className="text-sm font-semibold text-warroom-text flex items-center gap-1.5 mb-2">
            <Sparkles size={14} className="text-warroom-accent" /> AI Storyboard
          </h3>
          <p className="text-xs text-warroom-muted mb-3">Describe your video and AI will generate a storyboard with the right template and content.</p>
          <div className="flex gap-2">
            <input
              value={aiPrompt}
              onChange={e => setAiPrompt(e.target.value)}
              placeholder="e.g. A product showcase for our new headphones with 3 key features..."
              className="flex-1 bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
              onKeyDown={e => { if (e.key === "Enter") generateStoryboard(); }}
            />
            <button
              onClick={generateStoryboard}
              disabled={generatingStoryboard || !aiPrompt.trim()}
              className="px-4 py-2 bg-warroom-accent text-white text-xs rounded-lg disabled:opacity-40 hover:bg-warroom-accent/80 transition flex items-center gap-1.5"
            >
              {generatingStoryboard ? <Loader2 size={14} className="animate-spin" /> : <Wand2 size={14} />}
              Generate
            </button>
          </div>
        </div>

        {/* Or pick manually */}
        <div className="flex items-center gap-3">
          <div className="flex-1 h-px bg-warroom-border" />
          <span className="text-[10px] text-warroom-muted uppercase tracking-wider">or choose a template</span>
          <div className="flex-1 h-px bg-warroom-border" />
        </div>

        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1,2,3,4,5,6].map(i => (
              <div key={i} className="bg-warroom-surface border border-warroom-border rounded-xl p-4 animate-pulse">
                <div className="h-32 bg-warroom-border rounded-lg mb-3" />
                <div className="h-4 bg-warroom-border rounded w-2/3 mb-2" />
                <div className="h-3 bg-warroom-border rounded w-1/2" />
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {templates.map(tpl => (
              <div
                key={tpl.id}
                onClick={() => selectTemplate(tpl)}
                className={`bg-warroom-surface border rounded-xl p-4 cursor-pointer transition hover:border-warroom-accent/30 ${
                  selectedTemplate?.id === tpl.id ? "border-warroom-accent ring-1 ring-warroom-accent/30" : "border-warroom-border"
                }`}
              >
                {/* Preview thumbnail area */}
                <div className="aspect-video bg-warroom-bg rounded-lg mb-3 flex items-center justify-center overflow-hidden">
                  <div className="text-warroom-muted flex flex-col items-center gap-1">
                    <Film size={24} />
                    <span className="text-[10px]">{tpl.width}×{tpl.height}</span>
                  </div>
                </div>

                <h3 className="text-sm font-semibold text-warroom-text">{tpl.name}</h3>
                <p className="text-[11px] text-warroom-muted mt-1">{tpl.description}</p>

                <div className="flex items-center gap-2 mt-2 text-[10px] text-warroom-muted">
                  <span className="px-1.5 py-0.5 bg-warroom-bg rounded">{tpl.category}</span>
                  <span>{Math.round(tpl.durationFrames / tpl.fps)}s</span>
                  <span>{tpl.fps}fps</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  /* ═══════════════════════════════════════════════════════
   *  Step 2: Customize Props
   * ═══════════════════════════════════════════════════════ */
  function renderCustomizeStep() {
    if (!selectedTemplate) return null;

    return (
      <div className="space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-warroom-text flex items-center gap-2">
              <Settings2 size={14} className="text-warroom-accent" />
              Customize: {selectedTemplate.name}
            </h2>
            <p className="text-xs text-warroom-muted mt-0.5">Edit the text, colors, and content for your video.</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Left: Form */}
          <div className="space-y-4">
            {Object.entries(editableProps).map(([key, value]) => (
              <PropEditor key={key} propKey={key} value={value} onChange={v => updateProp(key, v)} />
            ))}
          </div>

          {/* Right: Live Preview */}
          <div className="sticky top-5">
            <div className="bg-warroom-surface border border-warroom-border rounded-xl p-3">
              <div className="flex items-center gap-2 mb-2">
                <Eye size={12} className="text-warroom-accent" />
                <span className="text-[10px] text-warroom-muted uppercase tracking-wider">Live Preview</span>
              </div>
              {CompositionComponent && (
                <div className="rounded-lg overflow-hidden bg-black">
                  <Player
                    component={CompositionComponent}
                    inputProps={editableProps as any}
                    durationInFrames={selectedTemplate.durationFrames}
                    compositionWidth={selectedTemplate.width}
                    compositionHeight={selectedTemplate.height}
                    fps={selectedTemplate.fps}
                    style={{
                      width: "100%",
                      aspectRatio: `${selectedTemplate.width} / ${selectedTemplate.height}`,
                    }}
                    controls
                    autoPlay
                    loop
                  />
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="flex justify-between">
          <button onClick={() => setStep("template")} className="px-4 py-2 bg-warroom-bg border border-warroom-border text-xs text-warroom-muted rounded-lg">
            Back
          </button>
          <button onClick={() => setStep("preview")} className="px-4 py-2 bg-warroom-accent text-white text-xs rounded-lg hover:bg-warroom-accent/80 transition flex items-center gap-1">
            Preview & Export <ChevronRight size={14} />
          </button>
        </div>
      </div>
    );
  }

  /* ═══════════════════════════════════════════════════════
   *  Step 3: Preview & Export
   * ═══════════════════════════════════════════════════════ */
  function renderPreviewStep() {
    if (!selectedTemplate || !CompositionComponent) return null;

    return (
      <div className="space-y-5 max-w-3xl mx-auto">
        <div>
          <h2 className="text-sm font-semibold text-warroom-text">Preview & Export</h2>
          <p className="text-xs text-warroom-muted mt-0.5">Review your video and export when ready.</p>
        </div>

        {/* Full-size player */}
        <div className="bg-black rounded-xl overflow-hidden">
          <Player
            component={CompositionComponent}
            inputProps={editableProps as any}
            durationInFrames={selectedTemplate.durationFrames}
            compositionWidth={selectedTemplate.width}
            compositionHeight={selectedTemplate.height}
            fps={selectedTemplate.fps}
            style={{
              width: "100%",
              aspectRatio: `${selectedTemplate.width} / ${selectedTemplate.height}`,
            }}
            controls
            autoPlay
            loop
          />
        </div>

        {/* Summary */}
        <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4 space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="text-warroom-muted">Template</span>
            <span className="text-warroom-text font-medium">{selectedTemplate.name}</span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-warroom-muted">Resolution</span>
            <span className="text-warroom-text font-medium">{selectedTemplate.width}×{selectedTemplate.height}</span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-warroom-muted">Duration</span>
            <span className="text-warroom-text font-medium">{Math.round(selectedTemplate.durationFrames / selectedTemplate.fps)}s @ {selectedTemplate.fps}fps</span>
          </div>
        </div>

        {/* Render result */}
        {renderResult && (
          <div className={`rounded-xl p-4 border ${renderResult.ok ? "bg-emerald-500/10 border-emerald-500/30" : "bg-red-500/10 border-red-500/30"}`}>
            <div className="flex items-center gap-2">
              {renderResult.ok ? <CheckCircle size={16} className="text-emerald-400" /> : <AlertCircle size={16} className="text-red-400" />}
              <span className="text-xs font-medium text-warroom-text">
                {renderResult.ok ? "Render job queued" : "Render failed"}
              </span>
            </div>
            <p className="text-[11px] text-warroom-muted mt-1">{renderResult.message || renderResult.error}</p>
          </div>
        )}

        <div className="flex justify-between">
          <button onClick={() => setStep("customize")} className="px-4 py-2 bg-warroom-bg border border-warroom-border text-xs text-warroom-muted rounded-lg">
            Back
          </button>
          <button
            onClick={startRender}
            disabled={rendering}
            className="px-5 py-2 bg-warroom-accent text-white text-xs rounded-lg disabled:opacity-40 hover:bg-warroom-accent/80 transition flex items-center gap-1.5 font-medium"
          >
            {rendering ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
            {rendering ? "Rendering..." : "Export Video"}
          </button>
        </div>
      </div>
    );
  }
}

/* ═══════════════════════════════════════════════════════
 *  Prop Editor — renders appropriate input for each prop type
 * ═══════════════════════════════════════════════════════ */
function PropEditor({
  propKey,
  value,
  onChange,
}: {
  propKey: string;
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  const label = propKey
    .replace(/([A-Z])/g, " $1")
    .replace(/^./, s => s.toUpperCase())
    .trim();

  // Color input
  if (propKey.toLowerCase().includes("color") && typeof value === "string") {
    return (
      <div>
        <label className="text-xs text-warroom-muted block mb-1 flex items-center gap-1.5">
          <Palette size={12} /> {label}
        </label>
        <div className="flex items-center gap-2">
          <input
            type="color"
            value={value}
            onChange={e => onChange(e.target.value)}
            className="w-8 h-8 rounded border border-warroom-border cursor-pointer"
          />
          <input
            value={value}
            onChange={e => onChange(e.target.value)}
            className="flex-1 bg-warroom-bg border border-warroom-border rounded-lg px-3 py-1.5 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent font-mono"
          />
        </div>
      </div>
    );
  }

  // Image/URL input
  if (
    propKey.toLowerCase().includes("image") ||
    propKey.toLowerCase().includes("url") ||
    propKey.toLowerCase().includes("logo") ||
    propKey.toLowerCase().includes("avatar")
  ) {
    return (
      <div>
        <label className="text-xs text-warroom-muted block mb-1 flex items-center gap-1.5">
          <ImageIcon size={12} /> {label}
        </label>
        <input
          value={(value as string) || ""}
          onChange={e => onChange(e.target.value)}
          placeholder="https://example.com/image.jpg"
          className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-1.5 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent"
        />
      </div>
    );
  }

  // Array of strings
  if (Array.isArray(value) && value.every(v => typeof v === "string")) {
    return (
      <div>
        <label className="text-xs text-warroom-muted block mb-1 flex items-center gap-1.5">
          <Type size={12} /> {label}
        </label>
        <div className="space-y-1.5">
          {(value as string[]).map((item, i) => (
            <input
              key={i}
              value={item}
              onChange={e => {
                const updated = [...(value as string[])];
                updated[i] = e.target.value;
                onChange(updated);
              }}
              className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-1.5 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent"
            />
          ))}
        </div>
      </div>
    );
  }

  // String input (default)
  if (typeof value === "string") {
    const isLong = value.length > 80;
    return (
      <div>
        <label className="text-xs text-warroom-muted block mb-1 flex items-center gap-1.5">
          <Type size={12} /> {label}
        </label>
        {isLong ? (
          <textarea
            value={value}
            onChange={e => onChange(e.target.value)}
            rows={3}
            className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-xs text-warroom-text resize-none focus:outline-none focus:border-warroom-accent"
          />
        ) : (
          <input
            value={value}
            onChange={e => onChange(e.target.value)}
            className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-1.5 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent"
          />
        )}
      </div>
    );
  }

  return null;
}
