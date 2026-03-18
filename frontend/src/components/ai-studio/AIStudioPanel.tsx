"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import {
  Sparkles, Loader2, Plus, Trash2, Upload, Image, Video, Film,
  User, Play, Eye, Clock, ChevronRight, FileText, Wand2,
  CheckCircle, AlertCircle, RefreshCw, X, Camera, Link, Mic,
  ExternalLink, Zap, TrendingUp, Save, Settings, BarChart,
} from "lucide-react";
import { API, authFetch } from "@/lib/api";
import ScrollTabs from "@/components/ui/ScrollTabs";
import dynamic from "next/dynamic";
import FormatPicker from "./FormatPicker";
import HookLab from "./HookLab";
import DistributionPanel from "./DistributionPanel";
import PerformanceDashboard from "./PerformanceDashboard";
import DigitalCopiesPanel from "./DigitalCopiesPanel";
import CompetitorScriptDrawer from "./CompetitorScriptDrawer";
import EditingDNADrawer from "./EditingDNADrawer";

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
  images: { id: number; image_url: string; image_type: string }[];
  created_at: string;
  status: string;
  character_dna?: any;
  reference_sheet_url?: string;
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

type SceneType = "remotion" | "ai_generated" | "image" | "stock";

interface StoryboardScene {
  id: string;
  title: string;
  description: string;
  duration_seconds: number;
  type: SceneType;
  // Remotion fields
  remotion_template?: string;
  remotion_props?: Record<string, any>;
  // AI fields
  ai_provider?: "veo" | "nano_banana" | "seeddance";
  ai_prompt?: string;
  // Image/Stock fields
  media_url?: string;
  animation?: string;
  // Legacy Scene fields for backward compatibility
  scene?: number;
  label?: string;
  seconds?: string;
  direction?: string;
  camera?: string;
  mood?: string;
  // Auto-population hints
  ai_action_description?: string;
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

interface ActionTemplate {
  id: string;
  slug: string;
  name: string;
  description: string;
  icon: string;
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

type MainTab = "create-video" | "digital-copies" | "templatizer" | "projects" | "performance" | "motion-control" | "video-editor";
type WizardStep = "template" | "settings" | "script" | "storyboard" | "generate";

export default function AIStudioPanel() {
  const [configured, setConfigured] = useState<boolean | null>(null);
  const [activeTab, setActiveTab] = useState<MainTab>("create-video");

  // Digital copies
  const [copies, setCopies] = useState<DigitalCopy[]>([]);
  const [loadingCopies, setLoadingCopies] = useState(false);



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
  const [storyboardScenes, setStoryboardScenes] = useState<StoryboardScene[]>([]);
  const [generating, setGenerating] = useState(false);
  const [generationResult, setGenerationResult] = useState<{ ok: boolean; generation_id?: string; prompt_used?: string; error?: string } | null>(null);

  // New state for auto-scripts (legacy)
  const [autoScripts, setAutoScripts] = useState<any[]>([]);
  const [loadingAutoScripts, setLoadingAutoScripts] = useState(false);
  const [selectedAutoScriptIdx, setSelectedAutoScriptIdx] = useState<number | null>(null);
  const [totalPostsAnalyzed, setTotalPostsAnalyzed] = useState(0);
  const [createFlowSection, setCreateFlowSection] = useState<"format" | "scripts" | "generate">("format");

  // Blueprint state (video cloning)
  const [blueprints, setBlueprints] = useState<any[]>([]);
  const [loadingBlueprints, setLoadingBlueprints] = useState(false);
  const [selectedBlueprint, setSelectedBlueprint] = useState<any | null>(null);
  const [autoFilledData, setAutoFilledData] = useState<any | null>(null);
  const [loadingAutoFill, setLoadingAutoFill] = useState(false);
  const [brandTopic, setBrandTopic] = useState("");
  const [blueprintFormatFilter, setBlueprintFormatFilter] = useState<string | null>(null);

  // Character DNA and Reference Sheet for selected character
  const [wizardCharacterDna, setWizardCharacterDna] = useState<any>(null);
  const [wizardReferenceSheet, setWizardReferenceSheet] = useState<string | null>(null);

  // Character and action selection
  const [selectedCharacterId, setSelectedCharacterId] = useState<number | null>(null);
  const [selectedActionSlug, setSelectedActionSlug] = useState<string | null>(null);
  const [actionTemplates, setActionTemplates] = useState<ActionTemplate[]>([]);

  // New state for FormatPicker and HookLab
  const [selectedFormat, setSelectedFormat] = useState<string | null>(null);
  const [scriptParts, setScriptParts] = useState<{ hook: string; body: string; cta: string }>({ hook: "", body: "", cta: "" });
  const [creativeMethod, setCreativeMethod] = useState<"ai-avatar" | "product-focused" | "stock-text">("ai-avatar");
  const [scriptTab, setScriptTab] = useState<"hook-lab" | "raw-script">("hook-lab");

  // Simulation state
  const [simulationFrictionData, setSimulationFrictionData] = useState<Record<string, "low" | "medium" | "high"> | null>(null);

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

  // Drawer states
  const [scriptDrawerOpen, setScriptDrawerOpen] = useState(false);
  const [dnaDrawerOpen, setDnaDrawerOpen] = useState(false);
  const [selectedEditingDna, setSelectedEditingDna] = useState<any>(null);

  // Pipeline state
  const [pipelineId, setPipelineId] = useState<number | null>(null);
  const [pipelineStatus, setPipelineStatus] = useState<any>(null);
  const [selectedReferencePostId, setSelectedReferencePostId] = useState<number | null>(null);
  
  // API key notification
  const [apiKeyWarning, setApiKeyWarning] = useState<string | null>(null);

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

  // ── Hash-based tab routing ─────────────────────────────
  const validTabs: MainTab[] = ["create-video", "digital-copies", "templatizer", "projects", "performance", "motion-control", "video-editor"];
  
  const handleTabChange = (tab: MainTab) => {
    setActiveTab(tab);
    window.location.hash = tab;
  };

  // On mount, read hash and set active tab
  useEffect(() => {
    const hash = window.location.hash.replace('#', '') as MainTab;
    if (hash && validTabs.includes(hash)) {
      setActiveTab(hash);
    }
  }, []);

  // Listen for hashchange events for back/forward navigation
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '') as MainTab;
      if (hash && validTabs.includes(hash)) {
        setActiveTab(hash);
      }
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  // ── Init ────────────────────────────────────────────────
  useEffect(() => {
    authFetch(`${API}/api/ai-studio/status`)
      .then(r => r.json()).then(d => setConfigured(d.configured))
      .catch(() => setConfigured(false));
  }, []);

  const fetchCopies = useCallback(async () => {
    setLoadingCopies(true);
    try {
      const r = await authFetch(`${API}/api/digital-copies`);
      if (r.ok) { const d = await r.json(); setCopies(Array.isArray(d) ? d : d.digital_copies || d.data || []); }
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

  const fetchActionTemplates = useCallback(async () => {
    try {
      const r = await authFetch(`${API}/api/action-templates`);
      if (r.ok) { 
        const d = await r.json(); 
        setActionTemplates(d.templates || []);
      }
    } catch { 
      // Fallback action templates
      setActionTemplates([
        { id: "1", slug: "selling", name: "Selling", description: "Direct product pitch", icon: "💰" },
        { id: "2", slug: "car-talking", name: "Car Talking", description: "Speaking while driving", icon: "🚗" },
        { id: "3", slug: "podcast", name: "Podcast", description: "Interview/discussion format", icon: "🎙️" },
        { id: "4", slug: "walking-vlog", name: "Walking Vlog", description: "Talk while walking", icon: "🚶" },
        { id: "5", slug: "presentation", name: "Presentation", description: "Educational content", icon: "📊" }
      ]);
    }
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
      fetchCopies(); fetchTemplates(); fetchProjects(); fetchActionTemplates();
    }
  }, [configured, fetchCopies, fetchTemplates, fetchProjects, fetchActionTemplates]);

  // Initialize script parts from existing script when switching to Hook Lab
  useEffect(() => {
    if (scriptTab === "hook-lab" && wizardScript && !scriptParts.hook && !scriptParts.body && !scriptParts.cta) {
      // Try to parse existing script into parts
      const lines = wizardScript.split('\n').map(line => line.trim()).filter(Boolean);
      if (lines.length >= 3) {
        setScriptParts({
          hook: lines[0] || "",
          body: lines.slice(1, -1).join('\n') || "",
          cta: lines[lines.length - 1] || ""
        });
      }
    }
  }, [scriptTab, wizardScript, scriptParts]);



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
    setApiKeyWarning(null);
    
    try {
      // Check required inputs
      if (!wizardScript) {
        setGenerationResult({ ok: false, error: "Script is required" });
        return;
      }

      // Use new pipeline endpoint — wire blueprint post_id if available
      const pipelinePayload = {
        reference_post_id: selectedBlueprint?.post_id || selectedReferencePostId,
        digital_copy_id: wizardCopyId,
        editing_dna_id: selectedEditingDna?.id,
        brand_context: {
          brand_name: "Stuff N Things",
          product_name: wizardTitle || brandTopic || "Untitled Video",
          script: wizardScript
        }
      };

      const pipelineResp = await authFetch(`${API}/api/ai-studio/ugc/pipeline/start`, {
        method: "POST",
        body: JSON.stringify(pipelinePayload),
      });

      if (pipelineResp.ok) {
        const pipelineData = await pipelineResp.json();
        setPipelineId(pipelineData.pipeline_id);
        setGenerationResult({ 
          ok: true, 
          generation_id: pipelineData.pipeline_id?.toString(),
          prompt_used: "UGC Pipeline started"
        });
        setPollStatus("processing");
        fetchProjects();
      } else if (pipelineResp.status === 500) {
        const errorData = await pipelineResp.json().catch(() => ({}));
        if (errorData.error && errorData.error.toLowerCase().includes("api key")) {
          setApiKeyWarning("Google AI Studio API key needs billing. Go to Settings to update.");
          setTimeout(() => setApiKeyWarning(null), 10000); // Auto-dismiss after 10s
        }
        setGenerationResult({ ok: false, error: errorData.error || "Pipeline failed to start" });
      } else {
        const errorData = await pipelineResp.json().catch(() => ({}));
        setGenerationResult({ ok: false, error: errorData.detail || errorData.error || "Pipeline failed to start" });
      }
    } catch (e: any) {
      if (e.message && e.message.toLowerCase().includes("api key")) {
        setApiKeyWarning("Google AI Studio API key needs billing. Go to Settings to update.");
        setTimeout(() => setApiKeyWarning(null), 10000);
      }
      setGenerationResult({ ok: false, error: e.message });
    } finally { 
      setGenerating(false); 
    }
  };

  // Polling for pipeline status
  useEffect(() => {
    if (!pipelineId || pollStatus !== "processing") return;
    const interval = setInterval(async () => {
      try {
        const r = await authFetch(`${API}/api/ai-studio/ugc/pipeline/${pipelineId}/status`);
        if (r.ok) {
          const d = await r.json();
          setPipelineStatus(d);
          setPollStatus(d.status);
          if (d.status === "completed" || d.status === "failed") {
            clearInterval(interval);
            fetchProjects();
          }
        }
      } catch { }
    }, 3000); // Poll every 3 seconds as required
    return () => clearInterval(interval);
  }, [pipelineId, pollStatus, fetchProjects]);

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

  const REMOTION_TEMPLATES = [
    { value: "text_overlay", label: "Bold Text Overlay" },
    { value: "diagram", label: "Animated Diagram/Chart" },
    { value: "split_screen", label: "Before/After Split Screen" },
    { value: "image_sequence", label: "Image Slideshow (Ken Burns)" },
    { value: "caption_track", label: "Caption Track" },
    { value: "cta", label: "Call to Action Slide" },
    { value: "b_roll", label: "B-Roll with Overlay" },
    { value: "code_walkthrough", label: "Code Walkthrough" },
  ];

  const AI_PROVIDERS = [
    { value: "veo", label: "Veo 3.1" },
    { value: "nano_banana", label: "Nano Banana" },
    { value: "seeddance", label: "Seeddance" },
  ];

  const ANIMATION_TYPES = [
    { value: "ken_burns", label: "Ken Burns" },
    { value: "slide", label: "Slide" },
    { value: "zoom", label: "Zoom" },
  ];

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

  const fetchAutoScripts = async (formatSlug: string) => {
    setLoadingAutoScripts(true);
    try {
      const r = await authFetch(`${API}/api/ai-studio/ugc/auto-scripts`, {
        method: "POST",
        body: JSON.stringify({ format_slug: formatSlug, count: 3 }),
      });
      if (r.ok) {
        const d = await r.json();
        setAutoScripts(d.scripts || []);
        setTotalPostsAnalyzed(d.total_competitor_posts_analyzed || 0);
      }
    } catch {}
    setLoadingAutoScripts(false);
  };

  // ── Blueprint fetchers ────────────────────────────────
  const fetchBlueprints = useCallback(async (formatFilter?: string) => {
    setLoadingBlueprints(true);
    try {
      const params = new URLSearchParams({ limit: "20" });
      if (formatFilter) params.set("format_filter", formatFilter);
      const r = await authFetch(`${API}/api/ai-studio/ugc/blueprints?${params}`);
      if (r.ok) {
        const d = await r.json();
        setBlueprints(d.blueprints || []);
      }
    } catch {}
    setLoadingBlueprints(false);
  }, []);

  useEffect(() => {
    if (configured) fetchBlueprints();
  }, [configured, fetchBlueprints]);

  const autoFillBlueprint = async (postId: number) => {
    setLoadingAutoFill(true);
    try {
      const r = await authFetch(`${API}/api/ai-studio/ugc/blueprints/${postId}/auto-fill`, {
        method: "POST",
        body: JSON.stringify({ digital_copy_id: wizardCopyId, brand_topic: brandTopic }),
      });
      if (r.ok) {
        const d = await r.json();
        setAutoFilledData(d);
        setWizardScript(d.script || "");
        if (d.storyboard) setWizardStoryboard(d.storyboard);
      }
    } catch {}
    setLoadingAutoFill(false);
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

  // Reset wizard - moved before fetchFormatSceneStructure
  const resetWizard = () => {
    setWizardStep("template");
    setWizardTemplate(null);
    setWizardCopyId(null);
    setWizardMode("product");
    setWizardTitle("");
    setWizardScript("");
    setWizardStoryboard([]);
    setStoryboardScenes([]);
    setGenerationResult(null);
    setPollingProjectId(null);
    setPollStatus(null);
    setSelectedFormat(null);
    setScriptParts({ hook: "", body: "", cta: "" });
    setCreativeMethod("ai-avatar");
    setScriptTab("hook-lab");
    setSelectedCharacterId(null);
    setSelectedActionSlug(null);
    setWizardCharacterDna(null);
    setWizardReferenceSheet(null);
    
    // Clear new pipeline state
    setPipelineId(null);
    setPipelineStatus(null);
    setSelectedReferencePostId(null);
    setSelectedEditingDna(null);
    setApiKeyWarning(null);

    // Clear auto-scripts state
    setAutoScripts([]);
    setLoadingAutoScripts(false);
    setSelectedAutoScriptIdx(null);
    setTotalPostsAnalyzed(0);
    setCreateFlowSection("format");

    // Clear blueprint state
    setSelectedBlueprint(null);
    setAutoFilledData(null);
    setBrandTopic("");
  };

  const fetchFormatSceneStructure = async (formatSlug: string) => {
    try {
      const response = await authFetch(`${API}/api/video-formats/${formatSlug}`);
      if (response.ok) {
        const data = await response.json();
        return data.scene_structure || [];
      }
    } catch (e) {
      console.error("Failed to fetch format scene structure:", e);
    }
    return [];
  };

  const autoPopulateStoryboard = async () => {
    if (!selectedFormat) return;
    
    const sceneStructure = await fetchFormatSceneStructure(selectedFormat);
    if (sceneStructure.length > 0) {
      // Map the scene structure to new StoryboardScene format
      const autoScenes: StoryboardScene[] = sceneStructure.map((scene: any, index: number) => ({
        id: `scene_${Date.now()}_${index}`,
        title: scene.title || `Scene ${index + 1}`,
        description: scene.description || "",
        duration_seconds: parseInt(scene.duration_hint?.replace(/[^\d]/g, '') || '5'),
        type: "remotion" as SceneType, // Default to Remotion (free/instant)
        remotion_template: scene.remotion_template || "text_overlay",
        remotion_props: scene.remotion_props || {},
        ai_action_description: scene.ai_action_description,
        // Legacy fields for backward compatibility
        scene: index + 1,
        label: scene.title || `Scene ${index + 1}`,
        seconds: scene.duration_hint || "",
        direction: scene.description || "",
        camera: scene.camera_angle || "",
        mood: scene.mood || ""
      }));
      
      // If script parts exist, enhance scene descriptions
      if (scriptParts.hook || scriptParts.body || scriptParts.cta) {
        if (autoScenes[0] && scriptParts.hook) {
          autoScenes[0].description += ` Hook: ${scriptParts.hook.slice(0, 50)}...`;
          autoScenes[0].direction += ` Hook: ${scriptParts.hook.slice(0, 50)}...`;
        }
        if (autoScenes[autoScenes.length - 1] && scriptParts.cta) {
          autoScenes[autoScenes.length - 1].description += ` CTA: ${scriptParts.cta.slice(0, 50)}...`;
          autoScenes[autoScenes.length - 1].direction += ` CTA: ${scriptParts.cta.slice(0, 50)}...`;
        }
        if (scriptParts.body && autoScenes.length > 2) {
          for (let i = 1; i < autoScenes.length - 1; i++) {
            autoScenes[i].description += ` Body content: ${scriptParts.body.slice(0, 50)}...`;
            autoScenes[i].direction += ` Body content: ${scriptParts.body.slice(0, 50)}...`;
          }
        }
      }
      
      setStoryboardScenes(autoScenes);
      // Also set legacy storyboard for backward compatibility
      const legacyScenes = autoScenes.map(scene => ({
        scene: scene.scene || 1,
        label: scene.label || scene.title,
        seconds: scene.seconds || `${scene.duration_seconds}s`,
        direction: scene.direction || scene.description,
        camera: scene.camera || "",
        mood: scene.mood || ""
      }));
      setWizardStoryboard(legacyScenes);
    }
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
          { id: "performance", label: "Performance", icon: BarChart },
        ]}
        active={activeTab}
        onChange={(id) => { handleTabChange(id as MainTab); if (id === "templatizer" && competitorVideos.length === 0) fetchCompetitorVideos(); }}
        size="sm"
      />

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === "digital-copies" && <DigitalCopiesPanel />}
        {activeTab === "create-video" && renderCreateVideo()}
        {activeTab === "video-editor" && <VideoEditor />}
        {activeTab === "motion-control" && renderMotionControl()}
        {activeTab === "templatizer" && renderTemplatizer()}
        {activeTab === "projects" && renderProjects()}
        {activeTab === "performance" && <PerformanceDashboard />}
      </div>

      {/* Side Drawers */}
      <CompetitorScriptDrawer
        isOpen={scriptDrawerOpen}
        onClose={() => setScriptDrawerOpen(false)}
        onApplyScript={(script, preview) => {
          setWizardScript(script);
          // Show notification
          console.log(`Script generated from ${preview}`);
        }}
        brandName={wizardTitle || ""}
        productName={wizardTitle || ""}
        targetAudience={wizardMode === "product" ? "product users" : "service seekers"}
        keyMessage=""
      />

      <EditingDNADrawer
        isOpen={dnaDrawerOpen}
        onClose={() => setDnaDrawerOpen(false)}
        onSelectDNA={(dna) => {
          setSelectedEditingDna(dna);
          console.log("Selected DNA template:", dna.name);
        }}
      />
    </div>
  );

  /* ═══════════════════════════════════════════════════════
   *  TAB: DIGITAL COPIES
   * ═══════════════════════════════════════════════════════ */


  /* ═══════════════════════════════════════════════════════
   *  TAB: CREATE VIDEO — Blueprint Cloning Machine
   * ═══════════════════════════════════════════════════════ */
  function renderCreateVideo() {
    return (
      <div className="w-full px-8 py-5 space-y-6">
        {/* API Key Warning Banner */}
        {apiKeyWarning && (
          <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-3">
            <div className="flex items-center gap-2">
              <AlertCircle size={16} className="text-yellow-400 flex-shrink-0" />
              <p className="text-sm text-yellow-300">{apiKeyWarning}</p>
            </div>
          </div>
        )}

        {/* ── SECTION A: Production Bar ──────────────────── */}
        <div className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
          <div className="flex items-center gap-4 flex-wrap">
            {/* Avatar / Digital Copy */}
            <div className="flex-shrink-0">
              <label className="text-[10px] uppercase tracking-wider text-warroom-muted block mb-1">Avatar</label>
              <div className="flex gap-2">
                <button onClick={() => { setSelectedCharacterId(null); setWizardCopyId(null); }}
                  className={`w-11 h-11 rounded-lg border flex items-center justify-center transition ${!selectedCharacterId ? "border-warroom-accent bg-warroom-accent/10" : "border-warroom-border bg-warroom-bg"}`}>
                  <Sparkles size={14} className="text-warroom-accent" />
                </button>
                {copies.slice(0, 4).map(copy => (
                  <button key={copy.id}
                    onClick={() => { setSelectedCharacterId(Number(copy.id)); setWizardCopyId(copy.id); }}
                    className={`w-11 h-11 rounded-lg border overflow-hidden transition ${selectedCharacterId === Number(copy.id) ? "border-warroom-accent ring-1 ring-warroom-accent" : "border-warroom-border"}`}>
                    {copy.images?.[0] ? <img src={copy.images[0].image_url} className="w-full h-full object-cover" alt={copy.name} /> : <User size={14} className="text-warroom-muted m-auto" />}
                  </button>
                ))}
                <button onClick={() => handleTabChange("digital-copies")}
                  className="w-11 h-11 rounded-lg border-2 border-dashed border-warroom-border hover:border-warroom-accent transition flex items-center justify-center">
                  <Plus size={14} className="text-warroom-muted" />
                </button>
              </div>
            </div>

            {/* Blueprint indicator */}
            <div className="flex-shrink-0">
              <label className="text-[10px] uppercase tracking-wider text-warroom-muted block mb-1">Blueprint</label>
              {selectedBlueprint ? (
                <div className="flex items-center gap-2 px-3 py-2 bg-warroom-accent/10 border border-warroom-accent/30 rounded-lg">
                  <span className="text-xs text-warroom-accent font-medium truncate max-w-[120px]">@{selectedBlueprint.handle}</span>
                  <button onClick={() => { setSelectedBlueprint(null); setAutoFilledData(null); }} className="text-warroom-muted hover:text-warroom-text"><X size={12} /></button>
                </div>
              ) : (
                <div className="px-3 py-2 bg-warroom-bg border border-warroom-border rounded-lg text-xs text-warroom-muted">Select below ↓</div>
              )}
            </div>

            {/* Topic input */}
            <div className="flex-1 min-w-[200px]">
              <label className="text-[10px] uppercase tracking-wider text-warroom-muted block mb-1">Your Topic</label>
              <div className="flex gap-2">
                <input value={brandTopic} onChange={e => setBrandTopic(e.target.value)}
                  placeholder="What's your video about? (e.g. AI website management)"
                  className="flex-1 bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent" />
                <button onClick={() => selectedBlueprint && autoFillBlueprint(selectedBlueprint.post_id)}
                  disabled={!selectedBlueprint || loadingAutoFill}
                  className="px-4 py-2 bg-warroom-accent text-white text-xs font-medium rounded-lg disabled:opacity-40 hover:bg-warroom-accent/80 transition flex items-center gap-1.5">
                  {loadingAutoFill ? <Loader2 size={14} className="animate-spin" /> : <Wand2 size={14} />}
                  Clone
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* ── SECTION B: Auto-Filled Storyboard ──────────── */}
        {autoFilledData && (
          <div className="bg-warroom-surface border border-warroom-accent/30 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-warroom-text">Production Storyboard</h3>
                <p className="text-xs text-warroom-muted">
                  Cloned from @{autoFilledData.source_handle} · {autoFilledData.total_duration?.toFixed(0)}s · {autoFilledData.source_format?.replace(/_/g, " ")}
                </p>
              </div>
              <div className="flex gap-2">
                <button onClick={() => setAutoFilledData(null)}
                  className="px-3 py-1.5 bg-warroom-bg border border-warroom-border text-xs text-warroom-muted rounded-lg">Clear</button>
                <button onClick={createAndGenerate} disabled={generating || !wizardScript.trim() || (!selectedBlueprint && !selectedReferencePostId)}
                  className="px-4 py-2 bg-warroom-accent text-white text-xs font-medium rounded-lg disabled:opacity-40 flex items-center gap-1.5"
                  title={!wizardCopyId ? "Select an avatar (Digital Copy) to generate video" : ""}>
                  {generating ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
                  Produce Video
                </button>
                {!wizardCopyId && (
                  <span className="text-[10px] text-yellow-400">⚠️ Select an avatar above to produce</span>
                )}
              </div>
            </div>

            {/* Editable script */}
            <div className="bg-warroom-bg rounded-lg p-4">
              <textarea value={wizardScript} onChange={e => setWizardScript(e.target.value)} rows={6}
                className="w-full bg-transparent text-sm text-warroom-text resize-none focus:outline-none leading-relaxed" placeholder="Script will be auto-filled..." />
            </div>

            {/* Storyboard scenes */}
            <div className="space-y-2">
              {(autoFilledData.storyboard || []).map((scene: any, i: number) => (
                <div key={i} className="flex items-start gap-3 p-3 bg-warroom-bg rounded-lg">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-warroom-accent/20 text-warroom-accent flex items-center justify-center text-xs font-bold">{i + 1}</div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-semibold text-warroom-text">{scene.label}</span>
                      <span className="text-[10px] text-warroom-muted">{scene.start?.toFixed?.(1) ?? scene.start}s – {scene.end?.toFixed?.(1) ?? scene.end}s</span>
                    </div>
                    <p className="text-xs text-warroom-muted leading-relaxed">{scene.text || scene.direction}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* Generation result */}
            {generationResult && (
              <div className={`rounded-xl p-4 border ${generationResult.ok ? "bg-emerald-500/10 border-emerald-500/30" : "bg-red-500/10 border-red-500/30"}`}>
                <div className="flex items-center gap-2">
                  {generationResult.ok ? <CheckCircle size={16} className="text-emerald-400" /> : <AlertCircle size={16} className="text-red-400" />}
                  <span className="text-xs text-warroom-text">{generationResult.ok ? "Pipeline started" : generationResult.error}</span>
                </div>
                {generationResult.ok && pipelineStatus && (
                  <div className="mt-2">
                    <div className="w-full bg-warroom-bg rounded-full h-2">
                      <div className="bg-warroom-accent h-2 rounded-full transition-all" style={{ width: `${(pipelineStatus.progress || 0) * 100}%` }} />
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ── SECTION C: Winning Blueprints Grid ──────────── */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-semibold text-warroom-text">Winning Blueprints</h2>
              <p className="text-xs text-warroom-muted">Click a video to clone its structure with your persona</p>
            </div>
            <div className="flex items-center gap-1.5 flex-wrap">
              {["all", "transformation", "direct_to_camera", "myth_buster", "pov", "expose"].map(f => (
                <button key={f}
                  onClick={() => { setBlueprintFormatFilter(f === "all" ? null : f); fetchBlueprints(f === "all" ? undefined : f); }}
                  className={`px-2.5 py-1 rounded-full text-[10px] font-medium transition ${
                    (f === "all" && !blueprintFormatFilter) || blueprintFormatFilter === f
                      ? "bg-warroom-accent/20 text-warroom-accent" : "bg-warroom-bg text-warroom-muted hover:text-warroom-text"
                  }`}>
                  {f === "all" ? "All" : f.replace(/_/g, " ")}
                </button>
              ))}
              <button onClick={() => fetchBlueprints(blueprintFormatFilter || undefined)} className="p-1 text-warroom-muted hover:text-warroom-text"><RefreshCw size={12} /></button>
            </div>
          </div>

          {loadingBlueprints ? (
            <div className="flex justify-center py-12"><Loader2 className="animate-spin text-warroom-accent" size={24} /></div>
          ) : blueprints.length === 0 ? (
            <div className="text-center py-12 text-warroom-muted">
              <Film size={28} className="mx-auto mb-2 text-warroom-accent/30" />
              <p className="text-xs">No competitor videos analyzed yet.</p>
              <p className="text-xs mt-1">Add competitors in the Competitors tab to get blueprints.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
              {blueprints.map(bp => (
                <button key={bp.post_id}
                  onClick={() => {
                    setSelectedBlueprint(bp);
                    if (brandTopic) autoFillBlueprint(bp.post_id);
                  }}
                  className={`text-left bg-warroom-surface border rounded-xl p-4 transition hover:border-warroom-accent/50 ${
                    selectedBlueprint?.post_id === bp.post_id ? "border-warroom-accent ring-1 ring-warroom-accent/30" : "border-warroom-border"
                  }`}>
                  <div className="flex items-start gap-3 mb-3">
                    {bp.thumbnail_url ? (
                      <div className="w-16 h-16 rounded-lg overflow-hidden bg-warroom-bg flex-shrink-0">
                        <img src={bp.thumbnail_url} className="w-full h-full object-cover" alt="" />
                      </div>
                    ) : (
                      <div className="w-16 h-16 rounded-lg bg-warroom-bg flex items-center justify-center flex-shrink-0"><Film size={20} className="text-warroom-muted" /></div>
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5 mb-1">
                        <span className="text-xs font-medium text-warroom-text">@{bp.handle}</span>
                        <span className="text-[10px] text-warroom-muted">{bp.platform}</span>
                      </div>
                      <div className="flex items-center gap-2 text-[10px] text-warroom-muted">
                        <span className="px-1.5 py-0.5 rounded bg-warroom-bg font-medium">{bp.format?.replace(/_/g, " ") || "video"}</span>
                        <span>{bp.total_duration ? `${Math.round(bp.total_duration)}s` : ""}</span>
                        <span className="text-emerald-400 font-medium">{bp.engagement_score?.toLocaleString()} eng</span>
                      </div>
                    </div>
                  </div>
                  <div className="space-y-1.5">
                    {bp.structure?.hook?.text && <p className="text-xs text-orange-400 font-medium line-clamp-2">🎣 {bp.structure.hook.text}</p>}
                    {bp.structure?.value?.key_points?.length > 0 && <p className="text-[10px] text-warroom-muted">📋 {bp.structure.value.key_points.length} key points</p>}
                    {bp.structure?.cta?.text && <p className="text-xs text-emerald-400/70 line-clamp-1">🎯 {bp.structure.cta.text.slice(0, 60)}{bp.structure.cta.text.length > 60 ? "..." : ""}</p>}
                  </div>
                  {bp.has_visual_dna && (
                    <div className="mt-2 flex items-center gap-1 text-[10px] text-purple-400"><Eye size={10} /> Visual DNA available</div>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }



  // ── Step 3: Script ─────────────────────────────────────

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
                <button onClick={() => { handleTabChange("create-video"); resetWizard(); }}
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
            <button onClick={() => { handleTabChange("create-video"); resetWizard(); }} className="text-xs text-warroom-accent underline">Create your first video</button>
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