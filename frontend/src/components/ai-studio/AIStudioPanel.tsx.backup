"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import {
  Sparkles, Loader2, Plus, Trash2, Upload, Image, Video, Film,
  User, Play, Eye, Clock, ChevronRight, FileText, Wand2,
  CheckCircle, AlertCircle, RefreshCw, X, Camera, Link, Mic,
  ExternalLink, Zap, TrendingUp, Save,
} from "lucide-react";
import { API, authFetch } from "@/lib/api";
import ScrollTabs from "@/components/ui/ScrollTabs";
import dynamic from "next/dynamic";

const VideoEditor = dynamic(() => import("./VideoEditor"), {
  loading: () => (
    <div className="flex justify-center py-12">
      <Loader2 className="animate-spin text-warroom-accent" size={24} />
    </div>
  ),
  ssr: false,
});

/* ── Types ─────────────────────────────────────────────── */
interface DigitalCopy {
  id: string;
  name: string;
  description: string;
  assets: Asset[];
  created_at: string;
}
interface Asset {
  id: string;
  filename: string;
  content_type: string;
  angle: string;
  path: string;
  uploaded_at: string;
}
interface VideoTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  duration_seconds: number;
  scene_count: number;
  storyboard: Scene[];
  prompt_template: string;
  thumbnail_url: string | null;
}
interface Scene {
  scene: number;
  label: string;
  seconds: string;
  direction: string;
  camera?: string;
  mood?: string;
}
interface VideoProject {
  id: string;
  title: string;
  template_id: string | null;
  digital_copy_id: string | null;
  content_mode: string;
  status: string;
  video_url: string | null;
  script?: string;
  storyboard?: Scene[];
  created_at: string;
}

interface VoiceSample {
  filename: string;
  label: string;
  size_kb: number;
  content_type: string;
  uploaded_at: string;
}
interface TemplatizeResult {
  analysis: any;
  template_id: string | null;
  source_url: string;
  competitor?: { handle: string; platform: string; engagement_score: number; original_caption: string };
}
interface CompetitorVideo {
  post_id: number;
  handle: string;
  platform: string;
  profile_image: string | null;
  post_url: string;
  thumbnail_url: string | null;
  caption: string;
  likes: number;
  comments: number;
  engagement_score: number;
  posted_at: string | null;
  media_type: string;
}

type MainTab = "create-video" | "digital-copies" | "templatizer" | "projects" | "motion-control" | "video-editor";
type WizardStep = "template" | "settings" | "script" | "storyboard" | "generate";

export default function AIStudioPanel() {
  const [configured, setConfigured] = useState<boolean | null>(null);
  const [activeTab, setActiveTab] = useState<MainTab>("create-video");

  // Digital copies
  const [copies, setCopies] = useState<DigitalCopy[]>([]);
  const [loadingCopies, setLoadingCopies] = useState(false);
  const [showCreateCopy, setShowCreateCopy] = useState(false);
  const [newCopyName, setNewCopyName] = useState("");
  const [newCopyDesc, setNewCopyDesc] = useState("");
  const [creatingCopy, setCreatingCopy] = useState(false);
  const [selectedCopy, setSelectedCopy] = useState<DigitalCopy | null>(null);
  const [uploadingAsset, setUploadingAsset] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Templates
  const [templates, setTemplates] = useState<VideoTemplate[]>([]);
  const [loadingTemplates, setLoadingTemplates] = useState(false);

  // Projects
  const [projects, setProjects] = useState<VideoProject[]>([]);
  const [loadingProjects, setLoadingProjects] = useState(false);

  // Wizard state
  const [wizardStep, setWizardStep] = useState<WizardStep>("template");
  const [wizardTemplate, setWizardTemplate] = useState<VideoTemplate | null>(null);
  const [wizardCopyId, setWizardCopyId] = useState<string | null>(null);
  const [wizardMode, setWizardMode] = useState<"product" | "service">("product");
  const [wizardTitle, setWizardTitle] = useState("");
  const [wizardScript, setWizardScript] = useState("");
  const [wizardStoryboard, setWizardStoryboard] = useState<Scene[]>([]);
  const [generating, setGenerating] = useState(false);
  const [generationResult, setGenerationResult] = useState<{ ok: boolean; generation_id?: string; prompt_used?: string; error?: string } | null>(null);

  // Polling
  const [pollingProjectId, setPollingProjectId] = useState<string | null>(null);
  const [pollStatus, setPollStatus] = useState<string | null>(null);

  // Templatizer
  const [templatizeUrl, setTemplatizeUrl] = useState("");
  const [templatizing, setTemplatizing] = useState(false);
  const [templatizeResult, setTemplatizeResult] = useState<TemplatizeResult | null>(null);
  const [competitorVideos, setCompetitorVideos] = useState<CompetitorVideo[]>([]);
  const [loadingCompetitorVideos, setLoadingCompetitorVideos] = useState(false);
  const [templatizingCompetitor, setTemplatizingCompetitor] = useState<number | null>(null);

  // Voice samples
  const voiceInputRef = useRef<HTMLInputElement>(null);
  const [uploadingVoice, setUploadingVoice] = useState(false);

  // Seeddance 1.5 Settings
  const [wizardModel, setWizardModel] = useState<"veo-3.1" | "seeddance-1.5">("veo-3.1");
  const [fixedLens, setFixedLens] = useState(false);
  const [includeAudio, setIncludeAudio] = useState(true);
  const [durationPreset, setDurationPreset] = useState<"12s" | "7s" | "Auto">("12s");
  const [resolution, setResolution] = useState<"720p" | "1080p">("720p");

  // Script Generator
  const [scriptGenOpen, setScriptGenOpen] = useState(false);
  const [scriptGenFormat, setScriptGenFormat] = useState("transformation");
  const [scriptGenHook, setScriptGenHook] = useState("");
  const [scriptGenTopic, setScriptGenTopic] = useState("");
  const [generatingScript, setGeneratingScript] = useState(false);
  const [showHookLibrary, setShowHookLibrary] = useState(false);
  const scriptTextareaRef = useRef<HTMLTextAreaElement>(null);

  // Schedule Post
  const [showScheduleForm, setShowScheduleForm] = useState(false);
  const [schedulePlatforms, setSchedulePlatforms] = useState<Record<string, boolean>>({ instagram: false, tiktok: false, youtube: false, x: false });
  const [scheduleDate, setScheduleDate] = useState("");
  const [scheduleCaption, setScheduleCaption] = useState("");
  const [scheduling, setScheduling] = useState(false);
  const [scheduleSuccess, setScheduleSuccess] = useState(false);

  // Motion Control
  const [mcModel, setMcModel] = useState("kling-3.0");
  const [mcMotionVideo, setMcMotionVideo] = useState<File | null>(null);
  const [mcCharacterImage, setMcCharacterImage] = useState<File | null>(null);
  const [mcQuality, setMcQuality] = useState("720p");
  const [mcSceneMode, setMcSceneMode] = useState<"video" | "image">("video"); // Scene control mode
  const [mcGenerating, setMcGenerating] = useState(false);
  const [mcGenerationResult, setMcGenerationResult] = useState<{ ok: boolean; error?: string } | null>(null);
  const mcMotionVideoRef = useRef<HTMLInputElement>(null);
  const mcCharacterImageRef = useRef<HTMLInputElement>(null);

  // ── Init ────────────────────────────────────────────────
  useEffect(() => {
    authFetch(`${API}/api/ai-studio/status`)
      .then(r => r.json()).then(d => setConfigured(d.configured))
      .catch(() => setConfigured(false));
  }, []);

  const fetchCopies = useCallback(async () => {
    setLoadingCopies(true);
    try {
      const r = await authFetch(`${API}/api/ai-studio/ugc/digital-copies`);
      if (r.ok) { const d = await r.json(); setCopies(d.copies || []); }
    } catch { }
    setLoadingCopies(false);
  }, []);

  const fetchTemplates = useCallback(async () => {
    setLoadingTemplates(true);
    try {
      const r = await authFetch(`${API}/api/ai-studio/ugc/templates`);
      if (r.ok) { const d = await r.json(); setTemplates(d.templates || []); }
    } catch { }
    setLoadingTemplates(false);
  }, []);

  const fetchProjects = useCallback(async () => {
    setLoadingProjects(true);
    try {
      const r = await authFetch(`${API}/api/ai-studio/ugc/projects`);
      if (r.ok) { const d = await r.json(); setProjects(d.projects || []); }
    } catch { }
    setLoadingProjects(false);
  }, []);

  const fetchCompetitorVideos = useCallback(async () => {
    setLoadingCompetitorVideos(true);
    try {
      const r = await authFetch(`${API}/api/ai-studio/ugc/competitor-videos?limit=20`);
      if (r.ok) { const d = await r.json(); setCompetitorVideos(d.videos || []); }
    } catch { }
    setLoadingCompetitorVideos(false);
  }, []);

  useEffect(() => {
    if (configured) {
      fetchCopies(); fetchTemplates(); fetchProjects();
    }
  }, [configured, fetchCopies, fetchTemplates, fetchProjects]);

  // ── Digital Copy CRUD ────────────────────────────────────
  const createDigitalCopy = async () => {
    if (!newCopyName.trim()) return;
    setCreatingCopy(true);
    try {
      const r = await authFetch(`${API}/api/ai-studio/ugc/digital-copies`, {
        method: "POST", body: JSON.stringify({ name: newCopyName, description: newCopyDesc }),
      });
      if (r.ok) {
        setNewCopyName(""); setNewCopyDesc(""); setShowCreateCopy(false);
        await fetchCopies();
      }
    } catch { } finally { setCreatingCopy(false); }
  };

  const deleteDigitalCopy = async (id: string) => {
    if (!confirm("Delete this digital copy and all its assets?")) return;
    await authFetch(`${API}/api/ai-studio/ugc/digital-copies/${id}`, { method: "DELETE" });
    if (selectedCopy?.id === id) setSelectedCopy(null);
    await fetchCopies();
  };

  const uploadAsset = async (copyId: string, file: File, angle: string) => {
    setUploadingAsset(true);
    const fd = new FormData();
    fd.append("file", file);
    fd.append("angle", angle);
    try {
      await authFetch(`${API}/api/ai-studio/ugc/digital-copies/${copyId}/assets`, { method: "POST", body: fd });
      // Refresh the specific copy
      const r = await authFetch(`${API}/api/ai-studio/ugc/digital-copies/${copyId}`);
      if (r.ok) {
        const updated = await r.json();
        setCopies(prev => prev.map(c => c.id === copyId ? updated : c));
        setSelectedCopy(updated);
      }
    } catch { } finally { setUploadingAsset(false); }
  };

  // ── Voice sample upload ───────────────────────────────────
  const uploadVoiceSample = async (copyId: string, file: File) => {
    setUploadingVoice(true);
    const label = prompt("Label this voice sample (e.g. 'casual', 'energetic', 'professional')") || "default";
    const fd = new FormData();
    fd.append("file", file);
    fd.append("label", label);
    try {
      await authFetch(`${API}/api/ai-studio/ugc/digital-copies/${copyId}/voice-samples`, { method: "POST", body: fd });
      const r = await authFetch(`${API}/api/ai-studio/ugc/digital-copies/${copyId}`);
      if (r.ok) {
        const updated = await r.json();
        setCopies(prev => prev.map(c => c.id === copyId ? updated : c));
        setSelectedCopy(updated);
      }
    } catch { } finally { setUploadingVoice(false); }
  };

  const deleteVoiceSample = async (copyId: string, filename: string) => {
    await authFetch(`${API}/api/ai-studio/ugc/digital-copies/${copyId}/voice-samples/${filename}`, { method: "DELETE" });
    const r = await authFetch(`${API}/api/ai-studio/ugc/digital-copies/${copyId}`);
    if (r.ok) {
      const updated = await r.json();
      setCopies(prev => prev.map(c => c.id === copyId ? updated : c));
      setSelectedCopy(updated);
    }
  };

  // ── Templatizer ─────────────────────────────────────────
  const templatizeFromUrl = async (url: string, save: boolean = false) => {
    setTemplatizing(true);
    setTemplatizeResult(null);
    try {
      const r = await authFetch(`${API}/api/ai-studio/ugc/templatize`, {
        method: "POST",
        body: JSON.stringify({ url, save_as_template: save }),
      });
      const d = await r.json();
      if (r.ok && d.analysis) {
        setTemplatizeResult(d);
        if (save) fetchTemplates();
      } else {
        alert(d.detail || d.error || "Templatization failed");
      }
    } catch (e: any) { alert(e.message); }
    finally { setTemplatizing(false); }
  };

  const templatizeCompetitor = async (postId: number) => {
    setTemplatizingCompetitor(postId);
    setTemplatizeResult(null);
    try {
      const r = await authFetch(`${API}/api/ai-studio/ugc/templatize-competitor`, {
        method: "POST",
        body: JSON.stringify({ competitor_post_id: postId, save_as_template: true }),
      });
      const d = await r.json();
      if (r.ok && d.analysis) {
        setTemplatizeResult(d);
        fetchTemplates();
      } else {
        alert(d.detail || d.error || "Templatization failed");
      }
    } catch (e: any) { alert(e.message); }
    finally { setTemplatizingCompetitor(null); }
  };

  // ── Video Project Create & Generate ───────────────────────
  const createAndGenerate = async () => {
    setGenerating(true);
    setGenerationResult(null);
    try {
      // Create project
      const createResp = await authFetch(`${API}/api/ai-studio/ugc/projects`, {
        method: "POST",
        body: JSON.stringify({
          template_id: wizardTemplate?.id || null,
          digital_copy_id: wizardCopyId,
          title: wizardTitle || wizardTemplate?.name || "Untitled Video",
          script: wizardScript,
          content_mode: wizardMode,
        }),
      });
      if (!createResp.ok) { setGenerationResult({ ok: false, error: "Failed to create project" }); return; }
      const proj = await createResp.json();

      // Update storyboard if modified
      if (wizardStoryboard.length > 0) {
        await authFetch(`${API}/api/ai-studio/ugc/projects/${proj.id}`, {
          method: "PUT",
          body: JSON.stringify({ storyboard: wizardStoryboard }),
        });
      }

      // Generate
      const genResp = await authFetch(`${API}/api/ai-studio/ugc/generate`, {
        method: "POST",
        body: JSON.stringify({
          project_id: proj.id,
          model: wizardModel,
          fixed_lens: fixedLens,
          include_audio: includeAudio,
          duration_preset: durationPreset,
          resolution: resolution
        }),
      });
      const genData = await genResp.json();
      if (genResp.ok) {
        setGenerationResult({ ok: true, generation_id: genData.generation_id, prompt_used: genData.prompt_used });
        setPollingProjectId(proj.id);
        setPollStatus("processing");
        fetchProjects();
      } else {
        setGenerationResult({ ok: false, error: genData.detail || "Generation failed" });
      }
    } catch (e: any) {
      setGenerationResult({ ok: false, error: e.message });
    } finally { setGenerating(false); }
  };

  // Polling for generation status
  useEffect(() => {
    if (!pollingProjectId || pollStatus !== "processing") return;
    const interval = setInterval(async () => {
      try {
        const r = await authFetch(`${API}/api/ai-studio/ugc/generate/${pollingProjectId}/status`);
        if (r.ok) {
          const d = await r.json();
          setPollStatus(d.status);
          if (d.status === "completed" || d.status === "failed") {
            clearInterval(interval);
            fetchProjects();
          }
        }
      } catch { }
    }, 5000);
    return () => clearInterval(interval);
  }, [pollingProjectId, pollStatus, fetchProjects]);

  // ── Script Generator ─────────────────────────────────────
  const VIDEO_FORMATS = [
    { id: "transformation", label: "Transformation (Before/After)", emoji: "🔄" },
    { id: "myth-buster", label: "Myth Buster", emoji: "💥" },
    { id: "pov", label: "POV", emoji: "👁️" },
    { id: "expose", label: "The Exposé", emoji: "🔍" },
    { id: "speed-run", label: "Speed Run", emoji: "⚡" },
    { id: "challenge", label: "Challenge Format", emoji: "🏆" },
    { id: "show-dont-tell", label: "Show Don't Tell", emoji: "🎬" },
    { id: "direct-to-camera", label: "Direct-to-Camera (Gary Vee)", emoji: "📹" },
  ];

  const HOOK_FORMULAS = [
    `[Person] + [conflict] → showed AI → mind changed`,
    `Wait, you guys are still doing it the old way?`,
    `Nobody talks about this but...`,
    `I tested [X] for 30 days. Here's what happened.`,
    `Stop doing [X]. Here's why.`,
    `The [industry] doesn't want you to know this...`,
    `I spent $[X] so you don't have to...`,
    `3 things I wish I knew before [action]`,
  ];

  const TEMPLATE_FORMAT_MAP: Record<string, string> = {
    "product showcase": "Transformation",
    "testimonial": "Show Don't Tell",
    "social media ad": "Direct-to-Camera",
    "product": "Transformation",
    "service": "Direct-to-Camera",
    "tutorial": "Show Don't Tell",
    "unboxing": "Speed Run",
    "review": "The Exposé",
  };

  const getTemplateBadge = (category: string, name: string): string | null => {
    const lower = `${category} ${name}`.toLowerCase();
    for (const [key, badge] of Object.entries(TEMPLATE_FORMAT_MAP)) {
      if (lower.includes(key)) return badge;
    }
    return null;
  };

  const generateScript = async () => {
    setGeneratingScript(true);
    try {
      const r = await authFetch(`${API}/api/ai-studio/ugc/generate-script`, {
        method: "POST",
        body: JSON.stringify({ format: scriptGenFormat, hook: scriptGenHook, topic: scriptGenTopic }),
      });
      if (r.ok) {
        const d = await r.json();
        setWizardScript(d.script || d.content || "");
      } else if (r.status === 404) {
        setWizardScript(`[HOOK] "${scriptGenHook || "Wait, you guys are still doing it the old way?"}"\n\n[BODY] ${scriptGenTopic || "Your topic here"}...\n\n[CTA] Link in bio — trust me on this one.\n\n/* Script generation coming soon — write your script above */`);
      } else {
        const d = await r.json().catch(() => ({}));
        alert(d.detail || d.error || "Script generation failed");
      }
    } catch {
      setWizardScript(`[HOOK] "${scriptGenHook || "Wait, you guys are still doing it the old way?"}"\n\n[BODY] ${scriptGenTopic || "Your topic here"}...\n\n[CTA] Link in bio — trust me on this one.\n\n/* Script generation coming soon — write your script above */`);
    } finally { setGeneratingScript(false); }
  };

  const insertHookAtCursor = (hook: string) => {
    const ta = scriptTextareaRef.current;
    if (ta) {
      const start = ta.selectionStart ?? 0;
      const before = wizardScript.slice(0, start);
      const after = wizardScript.slice(start);
      setWizardScript(`${before}${hook}${after}`);
      setTimeout(() => { ta.focus(); ta.setSelectionRange(start + hook.length, start + hook.length); }, 50);
    } else {
      setWizardScript(`${hook}\n\n${wizardScript}`);
    }
    setShowHookLibrary(false);
  };

  const schedulePost = async (videoUrl: string) => {
    setScheduling(true);
    setScheduleSuccess(false);
    try {
      const platforms = Object.entries(schedulePlatforms).filter(([, v]) => v).map(([k]) => k);
      const r = await authFetch(`${API}/api/scheduler/posts`, {
        method: "POST",
        body: JSON.stringify({ video_url: videoUrl, platforms, scheduled_at: scheduleDate, caption: scheduleCaption }),
      });
      if (r.ok) {
        setScheduleSuccess(true);
        setTimeout(() => { setShowScheduleForm(false); setScheduleSuccess(false); }, 2000);
      } else {
        const d = await r.json().catch(() => ({}));
        alert(d.detail || d.error || "Scheduling failed");
      }
    } catch (e: any) { alert(e.message); }
    finally { setScheduling(false); }
  };

  // Reset wizard
  const resetWizard = () => {
    setWizardStep("template");
    setWizardTemplate(null);
    setWizardCopyId(null);
    setWizardMode("product");
    setWizardTitle("");
    setWizardScript("");
    setWizardStoryboard([]);
    setGenerationResult(null);
    setPollingProjectId(null);
    setPollStatus(null);
  };

  // ── Not configured ─────────────────────────────────────
  if (configured === false) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-warroom-muted gap-3 p-8">
        <Sparkles size={40} className="text-warroom-accent/50" />
        <h2 className="text-lg font-semibold text-warroom-text">UGC Video Studio</h2>
        <p className="text-sm text-center max-w-md">Add your Google AI Studio (Gemini) API key in <strong>Settings → API Keys → Google</strong> to start generating UGC videos.</p>
      </div>
    );
  }

  // ── RENDER ─────────────────────────────────────────────
  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-warroom-border bg-warroom-surface/50">
        <div className="flex items-center gap-2.5">
          <Film size={18} className="text-warroom-accent" />
          <h1 className="text-base font-bold text-warroom-text">UGC Video Studio</h1>
          <span className="text-[10px] bg-warroom-accent/20 text-warroom-accent px-2 py-0.5 rounded-full font-medium">Veo 3.1</span>
        </div>
      </div>

      {/* Tabs */}
      <ScrollTabs
        tabs={[
          { id: "create-video", label: "Create Video", icon: Wand2 },
          { id: "video-editor", label: "Video Editor", icon: Play },
          { id: "motion-control", label: "Motion Control", icon: Video },
          { id: "digital-copies", label: "Digital Copies", icon: User },
          { id: "templatizer", label: "Templatizer", icon: Zap },
          { id: "projects", label: "My Projects", icon: Film },
        ]}
        active={activeTab}
        onChange={(id) => { setActiveTab(id as MainTab); if (id === "templatizer" && competitorVideos.length === 0) fetchCompetitorVideos(); }}
        size="sm"
      />

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === "digital-copies" && renderDigitalCopies()}
        {activeTab === "create-video" && renderCreateVideo()}
        {activeTab === "video-editor" && <VideoEditor />}
        {activeTab === "motion-control" && renderMotionControl()}
        {activeTab === "templatizer" && renderTemplatizer()}
        {activeTab === "projects" && renderProjects()}
      </div>
    </div>
  );

  /* ═══════════════════════════════════════════════════════
   *  TAB: DIGITAL COPIES
   * ═══════════════════════════════════════════════════════ */
  function renderDigitalCopies() {
    return (
      <div className="p-5 space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-warroom-text">Your Digital Copies</h2>
            <p className="text-xs text-warroom-muted mt-0.5">Upload multiple angles of yourself to create a reusable AI avatar for your videos.</p>
          </div>
          <button onClick={() => setShowCreateCopy(true)} className="flex items-center gap-1.5 px-3 py-1.5 bg-warroom-accent text-white text-xs rounded-lg hover:bg-warroom-accent/80 transition">
            <Plus size={14} /> New Digital Copy
          </button>
        </div>

        {/* Create form */}
        {showCreateCopy && (
          <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4 space-y-3">
            <input value={newCopyName} onChange={e => setNewCopyName(e.target.value)} placeholder="Name (e.g. 'My Avatar')" className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent" />
            <input value={newCopyDesc} onChange={e => setNewCopyDesc(e.target.value)} placeholder="Description (optional)" className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent" />
            <div className="flex gap-2">
              <button onClick={createDigitalCopy} disabled={creatingCopy || !newCopyName.trim()} className="px-3 py-1.5 bg-warroom-accent text-white text-xs rounded-lg disabled:opacity-40">
                {creatingCopy ? <Loader2 size={12} className="animate-spin" /> : "Create"}
              </button>
              <button onClick={() => setShowCreateCopy(false)} className="px-3 py-1.5 bg-warroom-bg border border-warroom-border text-xs text-warroom-muted rounded-lg">Cancel</button>
            </div>
          </div>
        )}

        {/* Copy list */}
        {loadingCopies ? (
          <div className="flex justify-center py-12"><Loader2 className="animate-spin text-warroom-accent" size={24} /></div>
        ) : copies.length === 0 ? (
          <div className="flex flex-col items-center py-16 text-warroom-muted gap-3">
            <User size={36} className="text-warroom-accent/30" />
            <p className="text-sm">No digital copies yet</p>
            <p className="text-xs text-center max-w-sm">Create a digital copy of yourself by uploading photos from multiple angles — front, side, 3/4 view, etc.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {copies.map(copy => (
              <div key={copy.id} onClick={() => setSelectedCopy(selectedCopy?.id === copy.id ? null : copy)}
                className={`bg-warroom-surface border rounded-xl p-4 cursor-pointer transition hover:border-warroom-accent/30 ${selectedCopy?.id === copy.id ? "border-warroom-accent" : "border-warroom-border"}`}>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-semibold text-warroom-text">{copy.name}</h3>
                  <button onClick={e => { e.stopPropagation(); deleteDigitalCopy(copy.id); }} className="p-1 rounded hover:bg-red-500/20 text-warroom-muted hover:text-red-400 transition"><Trash2 size={13} /></button>
                </div>
                {copy.description && <p className="text-xs text-warroom-muted mb-2">{copy.description}</p>}
                <div className="flex items-center gap-2 text-[11px] text-warroom-muted">
                  <Camera size={12} /> {copy.assets?.length || 0} assets
                  <span className="text-warroom-border">·</span>
                  {new Date(copy.created_at).toLocaleDateString()}
                </div>

                {/* Asset grid (when selected) */}
                {selectedCopy?.id === copy.id && (
                  <div className="mt-3 pt-3 border-t border-warroom-border space-y-3">
                    <div className="grid grid-cols-3 gap-2">
                      {(copy.assets || []).map(a => (
                        <div key={a.id} className="relative aspect-square bg-warroom-bg rounded-lg overflow-hidden border border-warroom-border group">
                          {a.content_type?.startsWith("image/") ? (
                            <div className="w-full h-full flex items-center justify-center text-warroom-muted"><Image size={20} /></div>
                          ) : (
                            <div className="w-full h-full flex items-center justify-center text-warroom-muted"><Video size={20} /></div>
                          )}
                          <div className="absolute bottom-0 inset-x-0 bg-black/60 text-[9px] text-white px-1.5 py-0.5 truncate">{a.angle}</div>
                        </div>
                      ))}
                      {/* Upload button */}
                      <button onClick={e => { e.stopPropagation(); fileInputRef.current?.click(); }}
                        className="aspect-square bg-warroom-bg border-2 border-dashed border-warroom-border rounded-lg flex flex-col items-center justify-center text-warroom-muted hover:border-warroom-accent hover:text-warroom-accent transition">
                        {uploadingAsset ? <Loader2 size={16} className="animate-spin" /> : <><Upload size={16} /><span className="text-[9px] mt-1">Add</span></>}
                      </button>
                    </div>
                    <input ref={fileInputRef} type="file" accept="image/*,video/*" className="hidden"
                      onChange={async (e) => {
                        const file = e.target.files?.[0];
                        if (!file) return;
                        const angle = prompt("What angle is this? (e.g. front, left-side, 3/4, back)") || "front";
                        await uploadAsset(copy.id, file, angle);
                        e.target.value = "";
                      }}
                    />

                    {/* Voice Samples */}
                    <div className="pt-3 border-t border-warroom-border">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="text-xs font-semibold text-warroom-text flex items-center gap-1.5"><Mic size={12} /> Voice Samples</h4>
                        <button onClick={e => { e.stopPropagation(); voiceInputRef.current?.click(); }}
                          className="flex items-center gap-1 px-2 py-1 bg-warroom-accent/20 text-warroom-accent text-[10px] rounded-lg hover:bg-warroom-accent/30 transition">
                          {uploadingVoice ? <Loader2 size={10} className="animate-spin" /> : <><Upload size={10} /> Upload</>}
                        </button>
                      </div>
                      {((copy as any).voice_samples || []).length === 0 ? (
                        <p className="text-[11px] text-warroom-muted">No voice samples yet. Upload audio recordings to clone your voice for video narration.</p>
                      ) : (
                        <div className="space-y-1.5">
                          {((copy as any).voice_samples || []).map((vs: VoiceSample) => (
                            <div key={vs.filename} className="flex items-center justify-between bg-warroom-bg rounded-lg px-3 py-2 text-xs">
                              <div className="flex items-center gap-2 text-warroom-text">
                                <Mic size={12} className="text-warroom-accent" />
                                <span>{vs.label}</span>
                                <span className="text-warroom-muted text-[10px]">{vs.size_kb} KB</span>
                              </div>
                              <button onClick={e => { e.stopPropagation(); deleteVoiceSample(copy.id, vs.filename); }}
                                className="p-1 rounded hover:bg-red-500/20 text-warroom-muted hover:text-red-400"><Trash2 size={11} /></button>
                            </div>
                          ))}
                        </div>
                      )}
                      <input ref={voiceInputRef} type="file" accept="audio/*" className="hidden"
                        onChange={async (e) => {
                          const file = e.target.files?.[0];
                          if (!file) return;
                          await uploadVoiceSample(copy.id, file);
                          e.target.value = "";
                        }}
                      />
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  /* ═══════════════════════════════════════════════════════
   *  TAB: CREATE VIDEO (Wizard)
   * ═══════════════════════════════════════════════════════ */
  function renderCreateVideo() {
    const steps: { id: WizardStep; label: string }[] = [
      { id: "template", label: "Template" },
      { id: "settings", label: "Settings" },
      { id: "script", label: "Script" },
      { id: "storyboard", label: "Storyboard" },
      { id: "generate", label: "Generate" },
    ];
    const stepIdx = steps.findIndex(s => s.id === wizardStep);

    return (
      <div className="p-5 space-y-5">
        {/* Step indicator */}
        <div className="flex items-center gap-1 mb-2">
          {steps.map((s, i) => (
            <div key={s.id} className="flex items-center">
              <button onClick={() => { if (i <= stepIdx) setWizardStep(s.id); }}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition ${i === stepIdx ? "bg-warroom-accent text-white" : i < stepIdx ? "bg-warroom-accent/20 text-warroom-accent cursor-pointer" : "bg-warroom-bg text-warroom-muted"}`}>
                <span className="w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold border border-current">{i + 1}</span>
                <span className="hidden sm:inline">{s.label}</span>
              </button>
              {i < steps.length - 1 && <ChevronRight size={14} className="text-warroom-border mx-0.5" />}
            </div>
          ))}
        </div>

        {/* Step content */}
        {wizardStep === "template" && renderStepTemplate()}
        {wizardStep === "settings" && renderStepSettings()}
        {wizardStep === "script" && renderStepScript()}
        {wizardStep === "storyboard" && renderStepStoryboard()}
        {wizardStep === "generate" && renderStepGenerate()}
      </div>
    );
  }

  // ── Step 1: Pick Template ──────────────────────────────
  function renderStepTemplate() {
    return (
      <div className="space-y-4">
        <div>
          <h2 className="text-sm font-semibold text-warroom-text">Choose a Video Template</h2>
          <p className="text-xs text-warroom-muted mt-0.5">Each template comes with a prebaked storyboard and scene structure.</p>
        </div>
        {loadingTemplates ? (
          <div className="flex justify-center py-12"><Loader2 className="animate-spin text-warroom-accent" size={24} /></div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {templates.map(tpl => (
              <div key={tpl.id} onClick={() => { setWizardTemplate(tpl); setWizardStoryboard(tpl.storyboard || []); setWizardTitle(tpl.name); }}
                className={`bg-warroom-surface border rounded-xl p-4 cursor-pointer transition hover:border-warroom-accent/30 ${wizardTemplate?.id === tpl.id ? "border-warroom-accent ring-1 ring-warroom-accent/30" : "border-warroom-border"}`}>
                <div className="flex items-center gap-2 mb-2">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${tpl.category === "product" ? "bg-blue-500/20" : "bg-purple-500/20"}`}>
                    <Film size={16} className={tpl.category === "product" ? "text-blue-400" : "text-purple-400"} />
                  </div>
                  <div>
                    <h3 className="text-xs font-semibold text-warroom-text">{tpl.name}</h3>
                    <p className="text-[10px] text-warroom-muted">{tpl.category} · {tpl.duration_seconds}s</p>
                  </div>
                </div>
                <p className="text-[11px] text-warroom-muted mb-2">{tpl.description}</p>
                <div className="flex items-center gap-2 text-[10px] text-warroom-muted flex-wrap">
                  <span className="flex items-center gap-0.5"><Clock size={10} /> {tpl.duration_seconds}s</span>
                  <span className="flex items-center gap-0.5"><FileText size={10} /> {tpl.scene_count} scenes</span>
                  {getTemplateBadge(tpl.category, tpl.name) && (
                    <span className="px-1.5 py-0.5 bg-purple-500/20 text-purple-400 rounded-full text-[9px] font-medium">{getTemplateBadge(tpl.category, tpl.name)}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
        <div className="flex justify-end">
          <button onClick={() => setWizardStep("settings")} disabled={!wizardTemplate}
            className="px-4 py-2 bg-warroom-accent text-white text-xs rounded-lg disabled:opacity-40 hover:bg-warroom-accent/80 transition flex items-center gap-1">
            Next <ChevronRight size={14} />
          </button>
        </div>
      </div>
    );
  }

  // ── Step 2: Settings ───────────────────────────────────
  function renderStepSettings() {
    return (
      <div className="space-y-5 max-w-xl">
        <div>
          <h2 className="text-sm font-semibold text-warroom-text">Video Settings</h2>
          <p className="text-xs text-warroom-muted mt-0.5">Configure the style and assets for this video.</p>
        </div>

        {/* Title */}
        <div>
          <label className="text-xs text-warroom-muted block mb-1">Video Title</label>
          <input value={wizardTitle} onChange={e => setWizardTitle(e.target.value)} placeholder="My UGC Ad"
            className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent" />
        </div>

        {/* Content mode */}
        <div>
          <label className="text-xs text-warroom-muted block mb-1.5">Content Type</label>
          <div className="flex gap-3">
            {(["product", "service"] as const).map(m => (
              <button key={m} onClick={() => setWizardMode(m)}
                className={`flex-1 py-3 rounded-xl border text-xs font-medium transition ${wizardMode === m ? "border-warroom-accent bg-warroom-accent/10 text-warroom-accent" : "border-warroom-border bg-warroom-bg text-warroom-muted hover:border-warroom-accent/30"}`}>
                {m === "product" ? "🛍️ Product Ad" : "💼 Service / Talking Head"}
              </button>
            ))}
          </div>
        </div>

        {/* Digital copy */}
        <div>
          <label className="text-xs text-warroom-muted block mb-1.5">Digital Copy (AI Avatar)</label>
          {copies.length === 0 ? (
            <p className="text-xs text-warroom-muted">No digital copies yet. <button onClick={() => setActiveTab("digital-copies")} className="text-warroom-accent underline">Create one first</button></p>
          ) : (
            <div className="grid grid-cols-2 gap-2">
              <button onClick={() => setWizardCopyId(null)}
                className={`p-3 rounded-xl border text-xs transition ${!wizardCopyId ? "border-warroom-accent bg-warroom-accent/10 text-warroom-accent" : "border-warroom-border bg-warroom-bg text-warroom-muted"}`}>
                ✨ Purely AI-generated (no avatar)
              </button>
              {copies.map(c => (
                <button key={c.id} onClick={() => setWizardCopyId(c.id)}
                  className={`p-3 rounded-xl border text-xs text-left transition ${wizardCopyId === c.id ? "border-warroom-accent bg-warroom-accent/10 text-warroom-accent" : "border-warroom-border bg-warroom-bg text-warroom-muted"}`}>
                  <span className="font-medium text-warroom-text">{c.name}</span>
                  <span className="block text-[10px]">{c.assets?.length || 0} assets</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Model & Advanced Settings */}
        <div className="pt-2 border-t border-warroom-border">
          <label className="text-xs text-warroom-muted block mb-3">Generation Options</label>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-[10px] uppercase tracking-wider text-warroom-muted block mb-1">Model</label>
              <select value={wizardModel} onChange={e => setWizardModel(e.target.value as any)}
                className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-2.5 py-1.5 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent">
                <option value="seeddance-1.5">Seeddance 1.5 Pro ✨</option>
                <option value="veo-3.1">Veo 3.1 HQ</option>
              </select>
            </div>
            <div>
              <label className="text-[10px] uppercase tracking-wider text-warroom-muted block mb-1">Duration</label>
              <div className="flex bg-warroom-bg border border-warroom-border rounded-lg overflow-hidden">
                {(["7s", "12s", "Auto"] as const).map(d => (
                  <button key={d} onClick={() => setDurationPreset(d)} className={`flex-1 text-[11px] py-1.5 transition ${durationPreset === d ? "bg-warroom-accent/20 text-warroom-accent font-medium" : "text-warroom-muted hover:bg-warroom-surface"}`}>{d}</button>
                ))}
              </div>
            </div>
          </div>
          <div className="flex gap-4 mt-3">
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input type="checkbox" checked={fixedLens} onChange={e => setFixedLens(e.target.checked)} className="accent-warroom-accent w-3.5 h-3.5" />
              <span className="text-xs text-warroom-text">Fixed Lens</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input type="checkbox" checked={includeAudio} onChange={e => setIncludeAudio(e.target.checked)} className="accent-warroom-accent w-3.5 h-3.5" />
              <span className="text-xs text-warroom-text">Auto-Audio Generation</span>
            </label>
          </div>
        </div>

        <div className="flex justify-between">
          <button onClick={() => setWizardStep("template")} className="px-4 py-2 bg-warroom-bg border border-warroom-border text-xs text-warroom-muted rounded-lg">Back</button>
          <button onClick={() => setWizardStep("script")} className="px-4 py-2 bg-warroom-accent text-white text-xs rounded-lg hover:bg-warroom-accent/80 transition flex items-center gap-1">Next <ChevronRight size={14} /></button>
        </div>
      </div>
    );
  }

  // ── Step 3: Script ─────────────────────────────────────
  function renderStepScript() {
    return (
      <div className="space-y-5 max-w-2xl">
        <div>
          <h2 className="text-sm font-semibold text-warroom-text">Write Your Script</h2>
          <p className="text-xs text-warroom-muted mt-0.5">The voiceover / dialogue for your video. Use the AI generator or write manually below.</p>
        </div>

        {/* ✨ AI Script Generator (collapsible) */}
        <div className="bg-warroom-surface border border-warroom-border rounded-xl overflow-hidden">
          <button onClick={() => setScriptGenOpen(!scriptGenOpen)}
            className="w-full flex items-center justify-between px-4 py-3 text-xs font-semibold text-warroom-text hover:bg-warroom-bg/50 transition">
            <span className="flex items-center gap-2"><Sparkles size={14} className="text-warroom-accent" /> AI Script Generator</span>
            <ChevronRight size={14} className={`text-warroom-muted transition-transform ${scriptGenOpen ? "rotate-90" : ""}`} />
          </button>
          {scriptGenOpen && (
            <div className="px-4 pb-4 space-y-3 border-t border-warroom-border pt-3">
              {/* Format grid */}
              <div>
                <label className="text-[10px] uppercase tracking-wider text-warroom-muted block mb-1.5">Video Format</label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5">
                  {VIDEO_FORMATS.map(f => (
                    <button key={f.id} onClick={() => setScriptGenFormat(f.id)}
                      className={`px-2 py-2 rounded-lg text-[11px] text-left transition border ${scriptGenFormat === f.id ? "border-warroom-accent bg-warroom-accent/10 text-warroom-accent" : "border-warroom-border bg-warroom-bg text-warroom-muted hover:border-warroom-accent/30"}`}>
                      <span className="mr-1">{f.emoji}</span> {f.label}
                    </button>
                  ))}
                </div>
              </div>
              {/* Hook input */}
              <div>
                <label className="text-[10px] uppercase tracking-wider text-warroom-muted block mb-1">Hook (80% of performance)</label>
                <input value={scriptGenHook} onChange={e => setScriptGenHook(e.target.value)}
                  placeholder={`e.g. "Nobody talks about this but..."`}
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent" />
              </div>
              {/* Topic input */}
              <div>
                <label className="text-[10px] uppercase tracking-wider text-warroom-muted block mb-1">Topic / Product</label>
                <input value={scriptGenTopic} onChange={e => setScriptGenTopic(e.target.value)}
                  placeholder="e.g. AI-powered marketing dashboard for agencies"
                  className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent" />
              </div>
              <button onClick={generateScript} disabled={generatingScript}
                className="w-full py-2.5 bg-warroom-accent text-white text-xs rounded-lg hover:bg-warroom-accent/80 disabled:opacity-40 transition flex items-center justify-center gap-1.5 font-medium">
                {generatingScript ? <Loader2 size={14} className="animate-spin" /> : <Wand2 size={14} />}
                {generatingScript ? "Generating..." : "Generate Script"}
              </button>
            </div>
          )}
        </div>

        {/* Hook Library + Textarea */}
        <div className="relative">
          <div className="flex items-center justify-between mb-1.5">
            <label className="text-[10px] uppercase tracking-wider text-warroom-muted">Script</label>
            <div className="relative">
              <button onClick={() => setShowHookLibrary(!showHookLibrary)}
                className="flex items-center gap-1 px-2 py-1 bg-warroom-bg border border-warroom-border text-[10px] text-warroom-muted rounded-lg hover:border-warroom-accent/30 hover:text-warroom-accent transition">
                <Zap size={10} /> Browse Hooks
              </button>
              {showHookLibrary && (
                <div className="absolute right-0 top-full mt-1 w-80 bg-warroom-surface border border-warroom-border rounded-xl shadow-xl z-20 p-2 space-y-0.5">
                  <p className="text-[10px] text-warroom-muted px-2 py-1 font-medium">Proven Hook Formulas — click to insert</p>
                  {HOOK_FORMULAS.map((h, i) => (
                    <button key={i} onClick={() => insertHookAtCursor(h)}
                      className="w-full text-left px-3 py-2 rounded-lg text-[11px] text-warroom-text hover:bg-warroom-accent/10 hover:text-warroom-accent transition">
                      &ldquo;{h}&rdquo;
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
          <textarea ref={scriptTextareaRef} value={wizardScript} onChange={e => setWizardScript(e.target.value)}
            placeholder={"[HOOK] \"Wait, you guys are still doing it the old way?\"\n\n[DEMO] So I just found this product and honestly...\n\n[CTA] Link in bio — trust me on this one."}
            rows={12}
            className="w-full bg-warroom-bg border border-warroom-border rounded-xl px-4 py-3 text-sm text-warroom-text resize-none focus:outline-none focus:border-warroom-accent leading-relaxed font-mono"
          />
        </div>

        <div className="flex justify-between">
          <button onClick={() => setWizardStep("settings")} className="px-4 py-2 bg-warroom-bg border border-warroom-border text-xs text-warroom-muted rounded-lg">Back</button>
          <button onClick={() => setWizardStep("storyboard")} className="px-4 py-2 bg-warroom-accent text-white text-xs rounded-lg hover:bg-warroom-accent/80 transition flex items-center gap-1">Next <ChevronRight size={14} /></button>
        </div>
      </div>
    );
  }

  // ── Step 4: Storyboard ─────────────────────────────────
  function renderStepStoryboard() {
    return (
      <div className="space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-warroom-text">Storyboard</h2>
            <p className="text-xs text-warroom-muted mt-0.5">Review and edit the scenes for your video. Each scene maps to a segment of the generated video.</p>
          </div>
          <button onClick={() => setWizardStoryboard([...wizardStoryboard, { scene: wizardStoryboard.length + 1, label: "New Scene", seconds: "", direction: "", camera: "", mood: "" }])}
            className="flex items-center gap-1 px-2.5 py-1.5 bg-warroom-bg border border-warroom-border text-xs text-warroom-muted rounded-lg hover:border-warroom-accent/30 transition">
            <Plus size={12} /> Add Scene
          </button>
        </div>

        {wizardStoryboard.length === 0 ? (
          <div className="text-center py-12 text-warroom-muted">
            <FileText size={28} className="mx-auto mb-2 text-warroom-accent/30" />
            <p className="text-xs">No scenes yet. Pick a template to get a prebaked storyboard, or add scenes manually.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {wizardStoryboard.map((scene, i) => (
              <div key={i} className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-warroom-accent/20 text-warroom-accent flex items-center justify-center text-[10px] font-bold">{i + 1}</span>
                    <input value={scene.label} onChange={e => { const s = [...wizardStoryboard]; s[i] = { ...s[i], label: e.target.value }; setWizardStoryboard(s); }}
                      className="bg-transparent text-sm font-semibold text-warroom-text focus:outline-none border-b border-transparent focus:border-warroom-accent" />
                  </div>
                  <div className="flex items-center gap-2">
                    <input value={scene.seconds} onChange={e => { const s = [...wizardStoryboard]; s[i] = { ...s[i], seconds: e.target.value }; setWizardStoryboard(s); }}
                      placeholder="0-5s" className="w-16 bg-warroom-bg border border-warroom-border rounded px-2 py-0.5 text-[11px] text-warroom-text text-center focus:outline-none" />
                    <button onClick={() => setWizardStoryboard(wizardStoryboard.filter((_, j) => j !== i))} className="p-1 text-warroom-muted hover:text-red-400"><X size={12} /></button>
                  </div>
                </div>
                <textarea value={scene.direction} onChange={e => { const s = [...wizardStoryboard]; s[i] = { ...s[i], direction: e.target.value }; setWizardStoryboard(s); }}
                  placeholder="Scene direction..."
                  rows={2} className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-xs text-warroom-text resize-none focus:outline-none focus:border-warroom-accent mb-2" />
                <div className="flex gap-2">
                  <input value={scene.camera || ""} onChange={e => { const s = [...wizardStoryboard]; s[i] = { ...s[i], camera: e.target.value }; setWizardStoryboard(s); }}
                    placeholder="Camera (selfie, b-roll...)" className="flex-1 bg-warroom-bg border border-warroom-border rounded px-2 py-1 text-[11px] text-warroom-text focus:outline-none" />
                  <input value={scene.mood || ""} onChange={e => { const s = [...wizardStoryboard]; s[i] = { ...s[i], mood: e.target.value }; setWizardStoryboard(s); }}
                    placeholder="Mood / Energy" className="flex-1 bg-warroom-bg border border-warroom-border rounded px-2 py-1 text-[11px] text-warroom-text focus:outline-none" />
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="flex justify-between">
          <button onClick={() => setWizardStep("script")} className="px-4 py-2 bg-warroom-bg border border-warroom-border text-xs text-warroom-muted rounded-lg">Back</button>
          <button onClick={() => setWizardStep("generate")} className="px-4 py-2 bg-warroom-accent text-white text-xs rounded-lg hover:bg-warroom-accent/80 transition flex items-center gap-1">Review & Generate <ChevronRight size={14} /></button>
        </div>
      </div>
    );
  }

  // ── Step 5: Generate ───────────────────────────────────
  function renderStepGenerate() {
    return (
      <div className="space-y-5 max-w-2xl">
        <div>
          <h2 className="text-sm font-semibold text-warroom-text">Review & Generate</h2>
          <p className="text-xs text-warroom-muted mt-0.5">Review your video setup and hit generate to start processing via Veo 3.1.</p>
        </div>

        {/* Summary */}
        <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4 space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="text-warroom-muted">Template</span>
            <span className="text-warroom-text font-medium">{wizardTemplate?.name || "None"}</span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-warroom-muted">Title</span>
            <span className="text-warroom-text font-medium">{wizardTitle || "Untitled"}</span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-warroom-muted">Content Type</span>
            <span className="text-warroom-text font-medium">{wizardMode === "product" ? "🛍️ Product" : "💼 Service"}</span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-warroom-muted">Digital Copy</span>
            <span className="text-warroom-text font-medium">{wizardCopyId ? copies.find(c => c.id === wizardCopyId)?.name || wizardCopyId : "AI-generated"}</span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-warroom-muted">Scenes</span>
            <span className="text-warroom-text font-medium">{wizardStoryboard.length}</span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-warroom-muted">Script</span>
            <span className="text-warroom-text font-medium">{wizardScript ? `${wizardScript.length} chars` : "None"}</span>
          </div>
        </div>

        {/* Script preview */}
        {wizardScript && (
          <div className="bg-warroom-bg border border-warroom-border rounded-xl p-4">
            <p className="text-[10px] text-warroom-muted uppercase tracking-wider mb-2">Script Preview</p>
            <pre className="text-xs text-warroom-text whitespace-pre-wrap font-mono leading-relaxed max-h-32 overflow-y-auto">{wizardScript}</pre>
          </div>
        )}

        {/* Generation result */}
        {generationResult && (
          <div className={`rounded-xl p-4 border ${generationResult.ok ? "bg-emerald-500/10 border-emerald-500/30" : "bg-red-500/10 border-red-500/30"}`}>
            <div className="flex items-center gap-2 mb-1">
              {generationResult.ok ? <CheckCircle size={16} className="text-emerald-400" /> : <AlertCircle size={16} className="text-red-400" />}
              <span className="text-xs font-medium text-warroom-text">{generationResult.ok ? "Video generation started" : "Generation failed"}</span>
            </div>
            {generationResult.ok && pollStatus && (
              <div className="flex items-center gap-2 text-[11px] text-warroom-muted mt-1">
                {pollStatus === "processing" && <><Loader2 size={12} className="animate-spin text-warroom-accent" /> Processing video...</>}
                {pollStatus === "completed" && <><CheckCircle size={12} className="text-emerald-400" /> Video ready — check My Projects</>}
                {pollStatus === "failed" && <><AlertCircle size={12} className="text-red-400" /> Generation failed</>}
              </div>
            )}
            {generationResult.error && <p className="text-[11px] text-red-400 mt-1">{generationResult.error}</p>}
          </div>
        )}

        {/* Schedule Post — shown when video is completed */}
        {generationResult?.ok && pollStatus === "completed" && (
          <div className="space-y-3">
            {!showScheduleForm ? (
              <button onClick={() => setShowScheduleForm(true)}
                className="flex items-center gap-1.5 px-4 py-2 bg-purple-500/20 text-purple-400 text-xs rounded-lg hover:bg-purple-500/30 transition font-medium">
                <Clock size={14} /> Schedule Post
              </button>
            ) : (
              <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold text-warroom-text flex items-center gap-1.5"><Clock size={12} /> Schedule Post</h4>
                  <button onClick={() => setShowScheduleForm(false)} className="p-1 text-warroom-muted hover:text-warroom-text"><X size={12} /></button>
                </div>
                {/* Platform checkboxes */}
                <div>
                  <label className="text-[10px] uppercase tracking-wider text-warroom-muted block mb-1.5">Platforms</label>
                  <div className="flex flex-wrap gap-2">
                    {(["instagram", "tiktok", "youtube", "x"] as const).map(p => (
                      <label key={p} className="flex items-center gap-1.5 cursor-pointer select-none">
                        <input type="checkbox" checked={schedulePlatforms[p]} onChange={e => setSchedulePlatforms(prev => ({ ...prev, [p]: e.target.checked }))}
                          className="accent-warroom-accent w-3.5 h-3.5" />
                        <span className="text-xs text-warroom-text capitalize">{p === "x" ? "𝕏" : p}</span>
                      </label>
                    ))}
                  </div>
                </div>
                {/* Datetime */}
                <div>
                  <label className="text-[10px] uppercase tracking-wider text-warroom-muted block mb-1">Schedule Date & Time</label>
                  <input type="datetime-local" value={scheduleDate} onChange={e => setScheduleDate(e.target.value)}
                    className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent" />
                </div>
                {/* Caption */}
                <div>
                  <label className="text-[10px] uppercase tracking-wider text-warroom-muted block mb-1">Caption</label>
                  <textarea value={scheduleCaption} onChange={e => setScheduleCaption(e.target.value)}
                    placeholder="Write your post caption..."
                    rows={3} className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-xs text-warroom-text resize-none focus:outline-none focus:border-warroom-accent" />
                </div>
                {scheduleSuccess ? (
                  <div className="flex items-center gap-1.5 text-xs text-emerald-400"><CheckCircle size={14} /> Post scheduled successfully!</div>
                ) : (
                  <button onClick={() => { const proj = projects.find(p => p.id === pollingProjectId); schedulePost(proj?.video_url || ""); }}
                    disabled={scheduling || !Object.values(schedulePlatforms).some(Boolean) || !scheduleDate}
                    className="w-full py-2 bg-purple-500 text-white text-xs rounded-lg hover:bg-purple-500/80 disabled:opacity-40 transition flex items-center justify-center gap-1.5 font-medium">
                    {scheduling ? <Loader2 size={14} className="animate-spin" /> : <Clock size={14} />}
                    {scheduling ? "Scheduling..." : "Schedule Post"}
                  </button>
                )}
              </div>
            )}
          </div>
        )}

        <div className="flex justify-between">
          <button onClick={() => setWizardStep("storyboard")} className="px-4 py-2 bg-warroom-bg border border-warroom-border text-xs text-warroom-muted rounded-lg">Back</button>
          <div className="flex gap-2">
            <button onClick={resetWizard} className="px-4 py-2 bg-warroom-bg border border-warroom-border text-xs text-warroom-muted rounded-lg">Start Over</button>
            <button onClick={createAndGenerate} disabled={generating || !wizardStoryboard.length}
              className="px-5 py-2 bg-warroom-accent text-white text-xs rounded-lg disabled:opacity-40 hover:bg-warroom-accent/80 transition flex items-center gap-1.5 font-medium">
              {generating ? <Loader2 size={14} className="animate-spin" /> : <Wand2 size={14} />}
              {generating ? "Generating..." : "Generate Video"}
            </button>
          </div>
        </div>
      </div>
    );
  }

  /* ═══════════════════════════════════════════════════════
   *  TAB: TEMPLATIZER
   * ═══════════════════════════════════════════════════════ */
  function renderTemplatizer() {
    return (
      <div className="p-5 space-y-5">
        {/* URL Input */}
        <div>
          <h2 className="text-sm font-semibold text-warroom-text mb-1">Templatize a Video</h2>
          <p className="text-xs text-warroom-muted mb-3">Paste any video URL (Instagram, TikTok, YouTube) — AI will analyze it scene-by-scene and extract a reusable template.</p>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Link size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-warroom-muted" />
              <input value={templatizeUrl} onChange={e => setTemplatizeUrl(e.target.value)}
                placeholder="https://www.instagram.com/reel/... or any video URL"
                className="w-full pl-9 pr-3 py-2.5 bg-warroom-bg border border-warroom-border rounded-lg text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
              />
            </div>
            <button onClick={() => templatizeFromUrl(templatizeUrl, false)} disabled={templatizing || !templatizeUrl.trim()}
              className="px-4 py-2.5 bg-warroom-accent text-white text-xs font-medium rounded-lg hover:bg-warroom-accent/80 disabled:opacity-40 transition flex items-center gap-1.5">
              {templatizing ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />} Analyze
            </button>
          </div>
        </div>

        {/* Analysis result */}
        {templatizeResult?.analysis && (
          <div className="bg-warroom-surface border border-warroom-border rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-warroom-text">{templatizeResult.analysis.title}</h3>
                <p className="text-xs text-warroom-muted mt-0.5">{templatizeResult.analysis.description}</p>
              </div>
              <div className="flex gap-2">
                {!templatizeResult.template_id && (
                  <button onClick={() => templatizeFromUrl(templatizeResult.source_url, true)}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500/20 text-emerald-400 text-xs rounded-lg hover:bg-emerald-500/30 transition">
                    <Save size={12} /> Save as Template
                  </button>
                )}
                {templatizeResult.template_id && (
                  <span className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500/20 text-emerald-400 text-xs rounded-lg">
                    <CheckCircle size={12} /> Saved
                  </span>
                )}
                <button onClick={() => { setActiveTab("create-video"); resetWizard(); }}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-warroom-accent/20 text-warroom-accent text-xs rounded-lg hover:bg-warroom-accent/30 transition">
                  <Wand2 size={12} /> Use Template
                </button>
              </div>
            </div>

            {/* Meta badges */}
            <div className="flex flex-wrap gap-2">
              {[
                { label: `${templatizeResult.analysis.duration_seconds}s`, icon: Clock },
                { label: templatizeResult.analysis.character_type },
                { label: templatizeResult.analysis.editing_style },
                { label: templatizeResult.analysis.music_style },
                { label: templatizeResult.analysis.cta_type },
              ].map((b, i) => b.label && (
                <span key={i} className="px-2 py-1 bg-warroom-bg rounded text-[10px] text-warroom-muted font-medium">{b.label}</span>
              ))}
            </div>

            {/* Script */}
            {templatizeResult.analysis.script && (
              <div>
                <h4 className="text-xs font-semibold text-warroom-text mb-1">Script</h4>
                <p className="text-xs text-warroom-muted bg-warroom-bg rounded-lg p-3 whitespace-pre-wrap">{templatizeResult.analysis.script}</p>
              </div>
            )}

            {/* Scenes */}
            <div>
              <h4 className="text-xs font-semibold text-warroom-text mb-2">Scenes ({templatizeResult.analysis.scenes?.length || 0})</h4>
              <div className="space-y-2">
                {(templatizeResult.analysis.scenes || []).map((s: any, i: number) => (
                  <div key={i} className="bg-warroom-bg rounded-lg p-3 border border-warroom-border">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="w-5 h-5 rounded-full bg-warroom-accent/20 text-warroom-accent flex items-center justify-center text-[10px] font-bold">{s.scene}</span>
                      <span className="text-xs font-semibold text-warroom-text">{s.label}</span>
                      <span className="text-[10px] text-warroom-muted">{s.seconds}</span>
                      <span className="px-1.5 py-0.5 bg-warroom-surface rounded text-[9px] text-warroom-muted">{s.camera}</span>
                    </div>
                    <p className="text-[11px] text-warroom-muted leading-relaxed">{s.direction}</p>
                  </div>
                ))}
              </div>
            </div>

            {templatizeResult.competitor && (
              <div className="text-[11px] text-warroom-muted flex items-center gap-2 pt-2 border-t border-warroom-border">
                <TrendingUp size={12} />
                From @{templatizeResult.competitor.handle} ({templatizeResult.competitor.platform}) · Engagement: {templatizeResult.competitor.engagement_score.toFixed(1)}
              </div>
            )}
          </div>
        )}

        {/* Competitor Videos */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-sm font-semibold text-warroom-text">Top Competitor Videos</h3>
              <p className="text-xs text-warroom-muted mt-0.5">One-click templatize the best-performing competitor videos from your tracked accounts.</p>
            </div>
            <button onClick={fetchCompetitorVideos} className="p-1.5 rounded-lg hover:bg-warroom-border/50 text-warroom-muted"><RefreshCw size={14} /></button>
          </div>
          {loadingCompetitorVideos ? (
            <div className="flex justify-center py-8"><Loader2 className="animate-spin text-warroom-accent" size={24} /></div>
          ) : competitorVideos.length === 0 ? (
            <div className="flex flex-col items-center py-12 text-warroom-muted gap-2">
              <TrendingUp size={28} className="text-warroom-accent/30" />
              <p className="text-xs">No competitor videos found. Track competitors in the Competitors tab first.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
              {competitorVideos.map(v => (
                <div key={v.post_id} className="bg-warroom-surface border border-warroom-border rounded-xl p-3 space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-full bg-warroom-bg flex items-center justify-center text-warroom-muted text-[10px] font-bold">
                      {v.handle?.[0]?.toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-semibold text-warroom-text truncate">@{v.handle}</div>
                      <div className="text-[10px] text-warroom-muted">{v.platform} · {v.media_type}</div>
                    </div>
                    <span className="px-1.5 py-0.5 bg-emerald-500/10 text-emerald-400 rounded text-[10px] font-medium">{v.engagement_score.toFixed(1)}</span>
                  </div>
                  {v.caption && <p className="text-[11px] text-warroom-muted line-clamp-2">{v.caption}</p>}
                  <div className="flex items-center gap-2 text-[10px] text-warroom-muted">
                    <span>❤️ {v.likes?.toLocaleString()}</span>
                    <span>💬 {v.comments?.toLocaleString()}</span>
                    {v.posted_at && <span>· {new Date(v.posted_at).toLocaleDateString()}</span>}
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => templatizeCompetitor(v.post_id)} disabled={templatizingCompetitor === v.post_id}
                      className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 bg-warroom-accent text-white text-xs rounded-lg hover:bg-warroom-accent/80 disabled:opacity-40 transition">
                      {templatizingCompetitor === v.post_id ? <Loader2 size={12} className="animate-spin" /> : <Zap size={12} />} Templatize
                    </button>
                    {v.post_url && (
                      <a href={v.post_url} target="_blank" rel="noopener noreferrer"
                        className="px-3 py-1.5 bg-warroom-bg border border-warroom-border text-warroom-muted text-xs rounded-lg hover:text-warroom-text transition">
                        <ExternalLink size={12} />
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  /* ═══════════════════════════════════════════════════════
   *  TAB: MOTION CONTROL (Kling 3.0)
   * ═══════════════════════════════════════════════════════ */
  function renderMotionControl() {
    const handleMcGenerate = async () => {
      setMcGenerating(true);
      setMcGenerationResult(null);
      // Dummy response for frontend interaction
      setTimeout(() => {
        setMcGenerating(false);
        setMcGenerationResult({ ok: true });
        alert("Motion request successfully queued for Kling 3.0!");
      }, 1500);
    };

    return (
      <div className="p-5 space-y-6 max-w-2xl">
        <div>
          <h2 className="text-sm font-semibold text-warroom-text">Motion Control <span className="text-[10px] bg-warroom-accent/20 text-warroom-accent px-1.5 py-0.5 rounded ml-1">Kling 3.0</span></h2>
          <p className="text-xs text-warroom-muted mt-0.5">Control character motion utilizing standard video references.</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="border border-dashed border-warroom-border bg-warroom-surface rounded-xl p-4 flex flex-col items-center justify-center text-center cursor-pointer hover:border-warroom-accent transition"
            onClick={() => mcMotionVideoRef.current?.click()}>
            <div className="w-10 h-10 rounded-full bg-warroom-bg flex items-center justify-center mb-2">
              <Video size={18} className="text-warroom-muted" />
            </div>
            <h3 className="text-xs font-semibold text-warroom-text">Add motion to copy</h3>
            <p className="text-[10px] text-warroom-muted mt-1">Video duration: 3–30 seconds</p>
            {mcMotionVideo && <span className="mt-2 text-[10px] text-emerald-400 font-medium">{mcMotionVideo.name}</span>}
            <input type="file" ref={mcMotionVideoRef} accept="video/*" className="hidden" onChange={e => setMcMotionVideo(e.target.files?.[0] || null)} />
          </div>

          <div className="border border-dashed border-warroom-border bg-warroom-surface rounded-xl p-4 flex flex-col items-center justify-center text-center cursor-pointer hover:border-warroom-accent transition"
            onClick={() => mcCharacterImageRef.current?.click()}>
            <div className="w-10 h-10 rounded-full bg-warroom-bg flex items-center justify-center mb-2">
              <Plus size={18} className="text-warroom-muted" />
            </div>
            <h3 className="text-xs font-semibold text-warroom-text">Add your character</h3>
            <p className="text-[10px] text-warroom-muted mt-1">Image with visible face and body</p>
            {mcCharacterImage && <span className="mt-2 text-[10px] text-emerald-400 font-medium">{mcCharacterImage.name}</span>}
            <input type="file" ref={mcCharacterImageRef} accept="image/*" className="hidden" onChange={e => setMcCharacterImage(e.target.files?.[0] || null)} />
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-[10px] uppercase tracking-wider text-warroom-muted block mb-1.5">Model</label>
            <div className="bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-xs text-warroom-text flex items-center justify-between">
              <span className="flex items-center gap-1.5"><Sparkles size={12} className="text-warroom-accent" /> {mcModel === "kling-3.0" ? "Kling 3.0 Motion Control" : "Kling 3.0"}</span>
              <ChevronRight size={14} className="text-warroom-muted" />
            </div>
          </div>

          <div>
            <label className="text-[10px] uppercase tracking-wider text-warroom-muted block mb-1.5">Quality</label>
            <div className="bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-xs text-warroom-text flex items-center justify-between">
              <span>{mcQuality}</span>
              <ChevronRight size={14} className="text-warroom-muted" />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs text-warroom-text block font-medium">Scene control mode</label>
              <label className="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" checked={mcSceneMode === "image"} onChange={e => setMcSceneMode(e.target.checked ? "image" : "video")} className="sr-only peer" />
                <div className="w-9 h-5 bg-warroom-bg border border-warroom-border peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-warroom-text after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-warroom-accent"></div>
              </label>
            </div>

            <p className="text-[10px] text-warroom-muted leading-relaxed mb-2">Choose where the background should come from: the character image or the motion video.</p>

            <div className="flex bg-warroom-bg border border-warroom-border rounded-lg p-1">
              <button onClick={() => setMcSceneMode("video")} className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 text-xs rounded-md transition ${mcSceneMode === "video" ? "bg-warroom-surface text-warroom-text font-medium shadow-sm border border-warroom-border" : "text-warroom-muted hover:text-warroom-text"}`}>
                <Video size={12} /> Video
              </button>
              <button onClick={() => setMcSceneMode("image")} className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 text-xs rounded-md transition ${mcSceneMode === "image" ? "bg-warroom-surface text-warroom-text font-medium shadow-sm border border-warroom-border" : "text-warroom-muted hover:text-warroom-text"}`}>
                <Image size={12} /> Image
              </button>
            </div>
          </div>

          <div>
            <span className="text-xs text-warroom-muted flex items-center justify-between cursor-pointer hover:text-warroom-text">
              Advanced settings <ChevronRight size={14} />
            </span>
          </div>

          <button onClick={handleMcGenerate} disabled={mcGenerating || !mcMotionVideo || !mcCharacterImage}
            className="w-full py-3 bg-[#DEFF40] text-black text-xs rounded-lg disabled:opacity-50 transition flex items-center justify-center gap-1.5 font-bold uppercase shadow-[0_0_15px_rgba(222,255,64,0.3)]">
            {mcGenerating ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
            {mcGenerating ? "Generating..." : "Generate ✨ 7"}
          </button>
        </div>
      </div>
    );
  }

  /* ═══════════════════════════════════════════════════════
   *  TAB: PROJECTS
   * ═══════════════════════════════════════════════════════ */
  function renderProjects() {
    return (
      <div className="p-5 space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-warroom-text">My Video Projects</h2>
            <p className="text-xs text-warroom-muted mt-0.5">All your generated and in-progress videos.</p>
          </div>
          <button onClick={fetchProjects} className="p-1.5 rounded-lg hover:bg-warroom-border/50 text-warroom-muted"><RefreshCw size={14} /></button>
        </div>

        {loadingProjects ? (
          <div className="flex justify-center py-12"><Loader2 className="animate-spin text-warroom-accent" size={24} /></div>
        ) : projects.length === 0 ? (
          <div className="flex flex-col items-center py-16 text-warroom-muted gap-3">
            <Film size={36} className="text-warroom-accent/30" />
            <p className="text-sm">No projects yet</p>
            <button onClick={() => { setActiveTab("create-video"); resetWizard(); }} className="text-xs text-warroom-accent underline">Create your first video</button>
          </div>
        ) : (
          <div className="space-y-3">
            {projects.map(p => (
              <div key={p.id} className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${p.status === "completed" ? "bg-emerald-500/20" :
                      p.status === "processing" || p.status === "generating" ? "bg-yellow-500/20" :
                        p.status === "failed" ? "bg-red-500/20" : "bg-warroom-bg"
                      }`}>
                      {p.status === "completed" ? <Play size={18} className="text-emerald-400" /> :
                        p.status === "processing" || p.status === "generating" ? <Loader2 size={18} className="animate-spin text-yellow-400" /> :
                          p.status === "failed" ? <AlertCircle size={18} className="text-red-400" /> :
                            <Film size={18} className="text-warroom-muted" />}
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-warroom-text">{p.title}</h3>
                      <div className="flex items-center gap-2 text-[11px] text-warroom-muted">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${p.status === "completed" ? "bg-emerald-500/20 text-emerald-400" :
                          p.status === "processing" || p.status === "generating" ? "bg-yellow-500/20 text-yellow-400" :
                            p.status === "failed" ? "bg-red-500/20 text-red-400" : "bg-warroom-bg text-warroom-muted"
                          }`}>{p.status}</span>
                        <span>{p.content_mode}</span>
                        <span className="text-warroom-border">·</span>
                        <span>{new Date(p.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>
                  {p.video_url && (
                    <a href={p.video_url} target="_blank" rel="noopener noreferrer"
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-warroom-accent/20 text-warroom-accent text-xs rounded-lg hover:bg-warroom-accent/30 transition">
                      <Eye size={14} /> Watch
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }
}