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

  // New state for auto-scripts
  const [autoScripts, setAutoScripts] = useState<any[]>([]);
  const [loadingAutoScripts, setLoadingAutoScripts] = useState(false);
  const [selectedAutoScriptIdx, setSelectedAutoScriptIdx] = useState<number | null>(null);
  const [totalPostsAnalyzed, setTotalPostsAnalyzed] = useState(0);
  const [createFlowSection, setCreateFlowSection] = useState<"format" | "scripts" | "generate">("format");

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

      // Use new pipeline endpoint
      const pipelinePayload = {
        reference_post_id: selectedReferencePostId,
        digital_copy_id: wizardCopyId,
        editing_dna_id: selectedEditingDna?.id,
        brand_context: {
          brand_name: "Stuff N Things",
          product_name: wizardTitle || "Untitled Video",
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
   *  TAB: CREATE VIDEO (New Flow)
   * ═══════════════════════════════════════════════════════ */
  function renderCreateVideo() {
    return (
      <div className="w-full px-8 py-5 space-y-5">
        {/* API Key Warning Banner */}
        {apiKeyWarning && (
          <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-3 mb-4">
            <div className="flex items-center gap-2">
              <AlertCircle size={16} className="text-yellow-400 flex-shrink-0" />
              <p className="text-sm text-yellow-300">{apiKeyWarning}</p>
            </div>
          </div>
        )}

        {/* Section Content */}
        {createFlowSection === "format" && renderFormatSection()}
        {createFlowSection === "scripts" && renderScriptsSection()}
        {createFlowSection === "generate" && renderGenerateSection()}
      </div>
    );
  }

  // ── Section 1: Format Selection ──────────────────────────────
  function renderFormatSection() {
    return (
      <div className="space-y-4">
        <div>
          <h2 className="text-sm font-semibold text-warroom-text">Choose Your Viral Format</h2>
          <p className="text-xs text-warroom-muted mt-0.5">Select a viral format with competitor intelligence.</p>
        </div>

        {/* Format Picker */}
        <FormatPicker
          onSelect={(format) => {
            setSelectedFormat(format.slug);
            setWizardTitle(format.name);
            fetchAutoScripts(format.slug);
            setCreateFlowSection("scripts");
          }}
          selectedFormat={selectedFormat || undefined}
          onUseHook={(hook) => {
            setScriptParts(prev => ({ ...prev, hook }));
            setScriptTab("hook-lab");
          }}
        />
      </div>
    );
  }

  // ── Section 2: Auto-Generated Scripts ──────────────────────────────
  function renderScriptsSection() {
    return (
      <div className="space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-warroom-text">AI-Generated Scripts</h2>
            <p className="text-xs text-warroom-muted mt-0.5">Scripts generated from competitor analysis for {selectedFormat}.</p>
          </div>
          <button
            onClick={() => selectedFormat && fetchAutoScripts(selectedFormat)}
            disabled={loadingAutoScripts}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-warroom-bg border border-warroom-border text-xs text-warroom-muted rounded-lg hover:border-warroom-accent/30 transition"
          >
            {loadingAutoScripts ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
            Regenerate
          </button>
        </div>

        {/* Auto Scripts */}
        {loadingAutoScripts ? (
          <div className="flex justify-center py-12">
            <Loader2 className="animate-spin text-warroom-accent" size={24} />
          </div>
        ) : autoScripts.length > 0 ? (
          <div className="space-y-4">
            {/* Scripts count info */}
            {totalPostsAnalyzed > 0 && (
              <div className="text-xs text-warroom-muted bg-warroom-surface border border-warroom-border rounded-lg px-3 py-2">
                📊 Generated from {totalPostsAnalyzed} competitor posts analyzed
              </div>
            )}

            {/* Auto-generated scripts */}
            {autoScripts.map((script, i) => (
              <div key={i} className={`bg-warroom-surface border rounded-xl p-5 space-y-3 transition ${
                selectedAutoScriptIdx === i ? "border-warroom-accent" : "border-warroom-border"
              }`}>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-warroom-muted font-medium">Script {i + 1}</span>
                  <button
                    onClick={() => {
                      setWizardScript(`${script.hook}\n\n${script.body}\n\n${script.cta}`);
                      setSelectedAutoScriptIdx(i);
                      setCreateFlowSection("generate");
                    }}
                    className="px-3 py-1.5 bg-warroom-accent text-white text-xs rounded-lg hover:bg-warroom-accent/80 transition"
                  >
                    Use This Script
                  </button>
                </div>
                <p className="text-sm text-orange-400 font-semibold leading-relaxed">{script.hook}</p>
                <p className="text-sm text-warroom-text leading-relaxed whitespace-pre-wrap">{script.body}</p>
                <p className="text-sm text-emerald-400 font-medium">{script.cta}</p>
                {script.why_this_works && (
                  <p className="text-xs text-warroom-muted italic mt-2 pt-2 border-t border-warroom-border">
                    💡 {script.why_this_works}
                  </p>
                )}
              </div>
            ))}

            {/* Manual script option */}
            <div className="border-t border-warroom-border pt-4">
              <h3 className="text-sm font-semibold text-warroom-text mb-3">Or Write Your Own Script</h3>
              <textarea
                value={wizardScript}
                onChange={(e) => setWizardScript(e.target.value)}
                placeholder="[HOOK] Wait, you guys are still doing it the old way?

[BODY] So I just found this product and honestly...

[CTA] Link in bio — trust me on this one."
                rows={8}
                className="w-full bg-warroom-bg border border-warroom-border rounded-xl px-4 py-3 text-sm text-warroom-text resize-none focus:outline-none focus:border-warroom-accent leading-relaxed font-mono"
              />
              <div className="flex justify-between mt-3">
                <button
                  onClick={() => setScriptDrawerOpen(true)}
                  className="flex items-center gap-1 px-3 py-1.5 bg-warroom-bg border border-warroom-border text-xs text-warroom-muted rounded-lg hover:border-warroom-accent/30 hover:text-warroom-accent transition"
                >
                  <TrendingUp size={12} /> Hook Lab
                </button>
                <button
                  onClick={() => {
                    if (wizardScript.trim()) {
                      setSelectedAutoScriptIdx(null);
                      setCreateFlowSection("generate");
                    }
                  }}
                  disabled={!wizardScript.trim()}
                  className="px-4 py-1.5 bg-warroom-accent text-white text-xs rounded-lg disabled:opacity-40 hover:bg-warroom-accent/80 transition"
                >
                  Use Custom Script
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center py-12 text-warroom-muted">
            <Sparkles size={28} className="mx-auto mb-2 text-warroom-accent/30" />
            <p className="text-xs">No auto-generated scripts available.</p>
            <p className="text-xs mt-2">Try selecting a different format or write your own script below.</p>
          </div>
        )}

        <div className="flex justify-between pt-4">
          <button
            onClick={() => setCreateFlowSection("format")}
            className="px-4 py-2 bg-warroom-bg border border-warroom-border text-xs text-warroom-muted rounded-lg"
          >
            Back to Format
          </button>
        </div>
      </div>
    );
  }

  // ── Section 3: Generate ──────────────────────────────
  function renderGenerateSection() {
    return (
      <div className="space-y-5">
        <div>
          <h2 className="text-sm font-semibold text-warroom-text">Generate Video</h2>
          <p className="text-xs text-warroom-muted mt-0.5">Review your script, choose character, and generate your video.</p>
        </div>

        {/* Script Preview */}
        {wizardScript && (
          <div className="bg-warroom-bg border border-warroom-border rounded-xl p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-warroom-muted font-medium">Script Preview</span>
              <button
                onClick={() => setCreateFlowSection("scripts")}
                className="text-xs text-warroom-accent hover:underline"
              >
                Edit Script
              </button>
            </div>
            <pre className="text-xs text-warroom-text whitespace-pre-wrap font-mono leading-relaxed max-h-32 overflow-y-auto">{wizardScript}</pre>
          </div>
        )}

        {/* Character selector (existing carousel from old Settings step) */}
        <div>
          <label className="text-xs text-warroom-muted block mb-3">Choose Character</label>
          <div className="flex gap-3 overflow-x-auto pb-2">
            {/* No Character Option */}
            <div 
              onClick={() => { 
                setSelectedCharacterId(null); 
                setWizardCopyId(null);
                setWizardCharacterDna(null);
                setWizardReferenceSheet(null);
              }}
              className={`flex-shrink-0 cursor-pointer transition ${selectedCharacterId === null ? "ring-2 ring-warroom-accent" : ""}`}
            >
              <div className="w-20 h-20 rounded-xl bg-warroom-surface border border-warroom-border flex flex-col items-center justify-center p-2">
                <Sparkles size={20} className="text-warroom-accent mb-1" />
                <span className="text-xs text-warroom-text text-center leading-tight">AI Only</span>
              </div>
            </div>

            {/* Character Options */}
            {copies.map(copy => (
              <div 
                key={copy.id}
                onClick={() => { 
                  setSelectedCharacterId(Number(copy.id)); 
                  setWizardCopyId(copy.id);
                  setWizardCharacterDna((copy as any).character_dna || null);
                  setWizardReferenceSheet((copy as any).reference_sheet_url || null);
                }}
                className={`flex-shrink-0 cursor-pointer transition ${selectedCharacterId === Number(copy.id) ? "ring-2 ring-warroom-accent" : ""}`}
              >
                <div className="w-20 h-20 rounded-xl overflow-hidden bg-warroom-surface border border-warroom-border">
                  {copy.images && copy.images.length > 0 ? (
                    <img src={copy.images[0].image_url} alt={copy.name} className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-warroom-muted">
                      <User size={24} />
                    </div>
                  )}
                </div>
                <p className="text-xs text-warroom-text text-center mt-1 truncate w-20">{copy.name}</p>
              </div>
            ))}

            {/* Create New Character */}
            <div 
              onClick={() => handleTabChange("digital-copies")}
              className="flex-shrink-0 cursor-pointer"
            >
              <div className="w-20 h-20 rounded-xl border-2 border-dashed border-warroom-border bg-warroom-surface hover:border-warroom-accent hover:bg-warroom-accent/5 transition flex flex-col items-center justify-center">
                <Plus size={20} className="text-warroom-muted mb-1" />
                <span className="text-xs text-warroom-muted text-center leading-tight">Create</span>
              </div>
            </div>
          </div>
        </div>

        {/* Content type toggle */}
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

        {/* Generation Result Display */}
        {generationResult && (
          <div className={`rounded-xl p-4 border ${generationResult.ok ? "bg-emerald-500/10 border-emerald-500/30" : "bg-red-500/10 border-red-500/30"}`}>
            <div className="flex items-center gap-2 mb-1">
              {generationResult.ok ? <CheckCircle size={16} className="text-emerald-400" /> : <AlertCircle size={16} className="text-red-400" />}
              <span className="text-xs font-medium text-warroom-text">{generationResult.ok ? "Pipeline started" : "Pipeline failed"}</span>
            </div>
            
            {generationResult.ok && pipelineStatus && (
              <div className="mt-3 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-warroom-text">
                    {pipelineStatus.current_step ? `Step: ${pipelineStatus.current_step}` : "Initializing..."}
                  </span>
                  <span className="text-warroom-muted">
                    {pipelineStatus.progress ? `${Math.round(pipelineStatus.progress * 100)}%` : "0%"}
                  </span>
                </div>
                
                {/* Progress bar */}
                <div className="w-full bg-warroom-bg rounded-full h-2">
                  <div 
                    className="bg-warroom-accent h-2 rounded-full transition-all duration-300 ease-out"
                    style={{ width: `${(pipelineStatus.progress || 0) * 100}%` }}
                  />
                </div>
                
                {pollStatus === "processing" && <div className="flex items-center gap-2 text-[11px] text-warroom-muted">
                  <Loader2 size={12} className="animate-spin text-warroom-accent" /> 
                  Processing pipeline...
                </div>}
                
                {pollStatus === "completed" && <div className="flex items-center gap-2 text-[11px] text-emerald-400">
                  <CheckCircle size={12} /> 
                  Pipeline complete — video ready!
                </div>}
                
                {pollStatus === "failed" && <div className="flex items-center gap-2 text-[11px] text-red-400">
                  <AlertCircle size={12} /> 
                  Pipeline failed
                </div>}
              </div>
            )}
            
            {generationResult.error && <p className="text-[11px] text-red-400 mt-1">{generationResult.error}</p>}
          </div>
        )}

        {/* Distribution Panel — shown when video is completed */}
        {generationResult?.ok && pollStatus === "completed" && (
          <div className="mt-6">
            <DistributionPanel
              videoProjectId={pollingProjectId ? parseInt(pollingProjectId) : null}
              videoUrl={projects.find(p => p.id === pollingProjectId)?.video_url || null}
              caption={wizardScript || ""}
              onDistribute={(result) => {
                console.log("Distribution launched:", result);
              }}
            />
          </div>
        )}

        <div className="flex justify-between">
          <button
            onClick={() => setCreateFlowSection("scripts")}
            className="px-4 py-2 bg-warroom-bg border border-warroom-border text-xs text-warroom-muted rounded-lg"
          >
            Back to Scripts
          </button>
          <div className="flex gap-2">
            <button onClick={resetWizard} className="px-4 py-2 bg-warroom-bg border border-warroom-border text-xs text-warroom-muted rounded-lg">Start Over</button>
            <button onClick={createAndGenerate} disabled={generating || !wizardScript.trim()}
              className="px-5 py-2 bg-warroom-accent text-white text-xs rounded-lg disabled:opacity-40 hover:bg-warroom-accent/80 transition flex items-center gap-1.5 font-medium">
              {generating ? <Loader2 size={14} className="animate-spin" /> : <Wand2 size={14} />}
              {generating ? "Generating..." : "Generate Video"}
            </button>
          </div>
        </div>
      </div>
    );
  }





  // ── Step 3: Script ─────────────────────────────────────
  function renderStepScript() {
    return (
      <div className="space-y-5">
        <div>
          <h2 className="text-sm font-semibold text-warroom-text">Write Your Script</h2>
          <p className="text-xs text-warroom-muted mt-0.5">The voiceover / dialogue for your video. Use Hook Lab with competitor intel or write manually.</p>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-warroom-border">
          <button
            onClick={() => setScriptTab("hook-lab")}
            className={`px-4 py-2 text-xs font-medium transition-colors border-b-2 ${
              scriptTab === "hook-lab"
                ? "border-warroom-accent text-warroom-accent"
                : "border-transparent text-warroom-muted hover:text-warroom-text"
            }`}
          >
            <span className="flex items-center gap-1.5">
              <Sparkles size={12} />
              Hook Lab
            </span>
          </button>
          <button
            onClick={() => setScriptTab("raw-script")}
            className={`px-4 py-2 text-xs font-medium transition-colors border-b-2 ${
              scriptTab === "raw-script"
                ? "border-warroom-accent text-warroom-accent"
                : "border-transparent text-warroom-muted hover:text-warroom-text"
            }`}
          >
            Raw Script
          </button>
        </div>

        {/* Tab Content */}
        {scriptTab === "hook-lab" ? (
          <HookLab
            formatSlug={selectedFormat || "direct-to-camera"}
            onScriptChange={(parts) => {
              setScriptParts(parts);
              // Combine parts into full script for backward compatibility
              const fullScript = `${parts.hook}\n\n${parts.body}\n\n${parts.cta}`;
              setWizardScript(fullScript);
            }}
            initialScript={scriptParts}
          />
        ) : (
          <div className="space-y-5">
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
                <div className="flex items-center gap-2">
                  <button onClick={() => setScriptDrawerOpen(true)}
                    className="flex items-center gap-1 px-2 py-1 bg-warroom-bg border border-warroom-border text-[10px] text-warroom-muted rounded-lg hover:border-warroom-accent/30 hover:text-warroom-accent transition">
                    <TrendingUp size={10} /> Competitor Intel
                  </button>
                  <button onClick={() => setDnaDrawerOpen(true)}
                    className="flex items-center gap-1 px-2 py-1 bg-warroom-bg border border-warroom-border text-[10px] text-warroom-muted rounded-lg hover:border-warroom-accent/30 hover:text-warroom-accent transition">
                    <Settings size={10} /> Visual Template
                  </button>
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
                </div>
              <textarea ref={scriptTextareaRef} value={wizardScript} onChange={e => setWizardScript(e.target.value)}
                placeholder={"[HOOK] \"Wait, you guys are still doing it the old way?\"\n\n[DEMO] So I just found this product and honestly...\n\n[CTA] Link in bio — trust me on this one."}
                rows={12}
                className="w-full bg-warroom-bg border border-warroom-border rounded-xl px-4 py-3 text-sm text-warroom-text resize-none focus:outline-none focus:border-warroom-accent leading-relaxed font-mono"
              />
              
              {/* Script breakdown display */}
              {wizardScript && (
                <div className="mt-3 p-3 bg-warroom-surface border border-warroom-border rounded-lg">
                  <p className="text-[10px] text-warroom-muted uppercase tracking-wider mb-2">Script Breakdown</p>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                    <div>
                      <span className="text-orange-400 font-semibold">Hook:</span>
                      <p className="text-warroom-text mt-1 leading-relaxed">{wizardScript.split('\n\n')[0] || 'No hook detected'}</p>
                    </div>
                    <div>
                      <span className="text-blue-400 font-semibold">Body:</span>
                      <p className="text-warroom-text mt-1 leading-relaxed">{wizardScript.split('\n\n').slice(1, -1).join(' ') || 'No body content'}</p>
                    </div>
                    <div>
                      <span className="text-emerald-400 font-semibold">CTA:</span>
                      <p className="text-warroom-text mt-1 leading-relaxed">{wizardScript.split('\n\n').slice(-1)[0] || 'No CTA'}</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        <div className="flex justify-between">
          <button onClick={() => setWizardStep("settings")} className="px-4 py-2 bg-warroom-bg border border-warroom-border text-xs text-warroom-muted rounded-lg">Back</button>
          <button onClick={async () => {
            // When going to storyboard, ensure the full script is combined from parts if using Hook Lab
            if (scriptTab === "hook-lab" && scriptParts.hook && scriptParts.body && scriptParts.cta) {
              const fullScript = `${scriptParts.hook}\n\n${scriptParts.body}\n\n${scriptParts.cta}`;
              setWizardScript(fullScript);
            }
            // Auto-populate storyboard from format if it's empty
            if (wizardStoryboard.length === 0) {
              await autoPopulateStoryboard();
            }
            setWizardStep("storyboard");
          }} className="px-4 py-2 bg-warroom-accent text-white text-xs rounded-lg hover:bg-warroom-accent/80 transition flex items-center gap-1">Next <ChevronRight size={14} /></button>
        </div>
      </div>
    );
  }

  // ── Step 4: Storyboard ─────────────────────────────────
  function renderStepStoryboard() {
    const addNewScene = () => {
      const newScene: StoryboardScene = {
        id: `scene_${Date.now()}`,
        title: `Scene ${storyboardScenes.length + 1}`,
        description: "",
        duration_seconds: 5,
        type: "remotion",
        remotion_template: "text_overlay",
        scene: storyboardScenes.length + 1,
        label: `Scene ${storyboardScenes.length + 1}`,
        seconds: "5s",
        direction: "",
      };
      setStoryboardScenes([...storyboardScenes, newScene]);
      // Also update legacy storyboard
      const legacyScene = {
        scene: newScene.scene || 1,
        label: newScene.label || newScene.title,
        seconds: newScene.seconds || `${newScene.duration_seconds}s`,
        direction: newScene.direction || newScene.description,
        camera: newScene.camera || "",
        mood: newScene.mood || ""
      };
      setWizardStoryboard([...wizardStoryboard, legacyScene]);
    };

    const updateScene = (index: number, updates: Partial<StoryboardScene>) => {
      const updated = [...storyboardScenes];
      updated[index] = { ...updated[index], ...updates };
      setStoryboardScenes(updated);
      
      // Also update legacy storyboard
      const legacyUpdated = [...wizardStoryboard];
      if (legacyUpdated[index]) {
        legacyUpdated[index] = {
          ...legacyUpdated[index],
          label: updates.title || updated[index].title,
          seconds: updates.duration_seconds ? `${updates.duration_seconds}s` : legacyUpdated[index].seconds,
          direction: updates.description || updated[index].description,
        };
      }
      setWizardStoryboard(legacyUpdated);
    };

    const deleteScene = (index: number) => {
      setStoryboardScenes(storyboardScenes.filter((_, i) => i !== index));
      setWizardStoryboard(wizardStoryboard.filter((_, i) => i !== index));
    };

    const getSceneTypeIcon = (type: SceneType) => {
      switch (type) {
        case "remotion": return Settings;
        case "ai_generated": return Sparkles;
        case "image": return Image;
        case "stock": return Film;
        default: return Settings;
      }
    };

    const getSceneTypeBadge = (type: SceneType) => {
      switch (type) {
        case "remotion": return { text: "🎬 Remotion (Free, Instant)", color: "bg-emerald-500/10 text-emerald-400" };
        case "ai_generated": return { text: "🤖 AI Generated (~$0.05, 30-60s)", color: "bg-orange-500/10 text-orange-400" };
        case "image": return { text: "🖼️ Image (Free, Instant)", color: "bg-blue-500/10 text-blue-400" };
        case "stock": return { text: "📦 Stock (Free)", color: "bg-gray-500/10 text-gray-400" };
        default: return { text: "Unknown", color: "bg-gray-500/10 text-gray-400" };
      }
    };

    // Calculate summary stats
    const stats = storyboardScenes.reduce((acc, scene) => {
      acc.total++;
      acc.duration += scene.duration_seconds;
      acc.types[scene.type] = (acc.types[scene.type] || 0) + 1;
      if (scene.type === "ai_generated") {
        acc.cost += 0.05; // Approximate cost per AI scene
      }
      return acc;
    }, { total: 0, duration: 0, types: {} as Record<string, number>, cost: 0 });

    return (
      <div className="space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-warroom-text">Storyboard</h2>
            <p className="text-xs text-warroom-muted mt-0.5">Choose scene types: Remotion (free/instant), AI Generated (costs money), Image/Stock. Preview and customize each scene.</p>
          </div>
          <button onClick={addNewScene}
            className="flex items-center gap-1 px-2.5 py-1.5 bg-warroom-bg border border-warroom-border text-xs text-warroom-muted rounded-lg hover:border-warroom-accent/30 transition">
            <Plus size={12} /> Add Scene
          </button>
        </div>

        {storyboardScenes.length === 0 ? (
          <div className="text-center py-12 text-warroom-muted">
            <FileText size={28} className="mx-auto mb-2 text-warroom-accent/30" />
            <p className="text-xs">No scenes yet. Pick a format to get auto-populated scenes, or add scenes manually.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {storyboardScenes.map((scene, i) => {
              const IconComponent = getSceneTypeIcon(scene.type);
              const badge = getSceneTypeBadge(scene.type);
              
              return (
                <div key={scene.id} className="bg-warroom-surface border border-warroom-border rounded-xl p-4">
                  {/* Header */}
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className="w-6 h-6 rounded-full bg-warroom-accent/20 text-warroom-accent flex items-center justify-center text-[10px] font-bold">{i + 1}</span>
                      
                      {/* Friction Indicator */}
                      {simulationFrictionData && simulationFrictionData[scene.title] && (
                        <div className="relative group">
                          <div className={`w-2 h-2 rounded-full ${
                            simulationFrictionData[scene.title] === "low" ? "bg-green-400" :
                            simulationFrictionData[scene.title] === "medium" ? "bg-yellow-400" : "bg-red-400"
                          }`} />
                          <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-warroom-surface border border-warroom-border rounded text-xs text-warroom-text opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto transition-opacity z-10 shadow-xl whitespace-nowrap">
                            {simulationFrictionData[scene.title] === "low" && "🟢 Low friction"}
                            {simulationFrictionData[scene.title] === "medium" && "🟡 Medium friction"}
                            {simulationFrictionData[scene.title] === "high" && "🔴 High friction"}
                          </div>
                        </div>
                      )}
                      
                      <input 
                        value={scene.title} 
                        onChange={e => updateScene(i, { title: e.target.value })}
                        className="bg-transparent text-sm font-semibold text-warroom-text focus:outline-none border-b border-transparent focus:border-warroom-accent" 
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <input 
                        type="number" 
                        value={scene.duration_seconds} 
                        onChange={e => updateScene(i, { duration_seconds: parseInt(e.target.value) || 5 })}
                        className="w-16 bg-warroom-bg border border-warroom-border rounded px-2 py-0.5 text-[11px] text-warroom-text text-center focus:outline-none"
                        min="1" 
                        max="30"
                      />
                      <span className="text-[10px] text-warroom-muted">sec</span>
                      <button onClick={() => deleteScene(i)} className="p-1 text-warroom-muted hover:text-red-400">
                        <X size={12} />
                      </button>
                    </div>
                  </div>

                  {/* Scene Type Selector */}
                  <div className="mb-3">
                    <div className="flex items-center gap-2 mb-2">
                      <label className="text-[10px] uppercase tracking-wider text-warroom-muted">Scene Type</label>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${badge.color}`}>
                        {badge.text}
                      </span>
                    </div>
                    <div className="grid grid-cols-4 gap-2">
                      {(["remotion", "ai_generated", "image", "stock"] as SceneType[]).map(type => {
                        const Icon = getSceneTypeIcon(type);
                        return (
                          <button
                            key={type}
                            onClick={() => updateScene(i, { type })}
                            className={`p-2 rounded-lg border text-xs transition ${
                              scene.type === type
                                ? "border-warroom-accent bg-warroom-accent/10 text-warroom-accent"
                                : "border-warroom-border bg-warroom-bg text-warroom-muted hover:border-warroom-accent/30"
                            }`}
                          >
                            <Icon size={14} className="mx-auto mb-1" />
                            <span className="block capitalize">{type.replace("_", " ")}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Scene Description */}
                  <textarea 
                    value={scene.description} 
                    onChange={e => updateScene(i, { description: e.target.value })}
                    placeholder="Describe what happens in this scene..."
                    rows={2} 
                    className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-xs text-warroom-text resize-none focus:outline-none focus:border-warroom-accent mb-3" 
                  />

                  {/* AI Action Hint */}
                  {scene.ai_action_description && (
                    <div className="mb-3 p-2 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                      <span className="text-[10px] uppercase tracking-wider text-blue-400 block mb-1">For AI:</span>
                      <span className="text-xs text-blue-300">{scene.ai_action_description}</span>
                    </div>
                  )}

                  {/* Type-specific UI */}
                  {scene.type === "remotion" && (
                    <div className="space-y-3">
                      <div>
                        <label className="text-[10px] uppercase tracking-wider text-warroom-muted block mb-1">Template</label>
                        <select
                          value={scene.remotion_template || "text_overlay"}
                          onChange={e => updateScene(i, { remotion_template: e.target.value })}
                          className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent"
                        >
                          {REMOTION_TEMPLATES.map(template => (
                            <option key={template.value} value={template.value}>{template.label}</option>
                          ))}
                        </select>
                      </div>
                      {scene.remotion_template && (
                        <div>
                          <label className="text-[10px] uppercase tracking-wider text-warroom-muted block mb-1">Properties</label>
                          <div className="text-xs text-warroom-muted italic">Props editor coming soon - templates will use default values</div>
                        </div>
                      )}
                    </div>
                  )}

                  {scene.type === "ai_generated" && (
                    <div className="space-y-3">
                      <div>
                        <label className="text-[10px] uppercase tracking-wider text-warroom-muted block mb-1">Provider</label>
                        <select
                          value={scene.ai_provider || "veo"}
                          onChange={e => updateScene(i, { ai_provider: e.target.value as any })}
                          className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent"
                        >
                          {AI_PROVIDERS.map(provider => (
                            <option key={provider.value} value={provider.value}>{provider.label}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="text-[10px] uppercase tracking-wider text-warroom-muted block mb-1">AI Prompt</label>
                        <textarea
                          value={scene.ai_prompt || ""}
                          onChange={e => updateScene(i, { ai_prompt: e.target.value })}
                          placeholder="Describe the video scene for AI generation..."
                          rows={3}
                          className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-xs text-warroom-text resize-none focus:outline-none focus:border-warroom-accent"
                        />
                      </div>
                    </div>
                  )}

                  {scene.type === "image" && (
                    <div className="space-y-3">
                      <div>
                        <label className="text-[10px] uppercase tracking-wider text-warroom-muted block mb-1">Image URL or Upload</label>
                        <input
                          type="text"
                          value={scene.media_url || ""}
                          onChange={e => updateScene(i, { media_url: e.target.value })}
                          placeholder="https://example.com/image.jpg or upload..."
                          className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] uppercase tracking-wider text-warroom-muted block mb-1">Animation</label>
                        <select
                          value={scene.animation || "ken_burns"}
                          onChange={e => updateScene(i, { animation: e.target.value })}
                          className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent"
                        >
                          {ANIMATION_TYPES.map(animation => (
                            <option key={animation.value} value={animation.value}>{animation.label}</option>
                          ))}
                        </select>
                      </div>
                    </div>
                  )}

                  {scene.type === "stock" && (
                    <div className="space-y-3">
                      <div>
                        <label className="text-[10px] uppercase tracking-wider text-warroom-muted block mb-1">Stock Search</label>
                        <input
                          type="text"
                          value={scene.media_url || ""}
                          onChange={e => updateScene(i, { media_url: e.target.value })}
                          placeholder="Search for stock footage..."
                          className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent"
                        />
                        <div className="text-[10px] text-warroom-muted mt-1">Stock footage search coming soon</div>
                      </div>
                      <div>
                        <label className="text-[10px] uppercase tracking-wider text-warroom-muted block mb-1">Animation</label>
                        <select
                          value={scene.animation || "slide"}
                          onChange={e => updateScene(i, { animation: e.target.value })}
                          className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent"
                        >
                          {ANIMATION_TYPES.map(animation => (
                            <option key={animation.value} value={animation.value}>{animation.label}</option>
                          ))}
                        </select>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Summary Bar */}
        {storyboardScenes.length > 0 && (
          <div className="bg-warroom-bg border border-warroom-border rounded-xl p-4">
            <div className="flex items-center gap-4 text-xs text-warroom-muted">
              <span className="flex items-center gap-1">
                <BarChart size={12} />
                Total: <span className="text-warroom-text font-medium">{stats.total} scenes</span>
              </span>
              <span className="text-warroom-border">·</span>
              <span className="text-warroom-text font-medium">{stats.duration}s</span>
              <span className="text-warroom-border">·</span>
              {Object.entries(stats.types).map(([type, count]) => (
                <span key={type}>
                  {type === "remotion" && `Remotion: ${count} (free)`}
                  {type === "ai_generated" && `AI: ${count} ($${(count * 0.05).toFixed(2)})`}
                  {type === "image" && `Image: ${count} (free)`}
                  {type === "stock" && `Stock: ${count} (free)`}
                </span>
              )).filter(Boolean).join(" · ")}
              {stats.cost > 0 && (
                <>
                  <span className="text-warroom-border">·</span>
                  <span className="text-warroom-text font-medium">Est. total: ${stats.cost.toFixed(2)}</span>
                </>
              )}
            </div>
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
      <div className="space-y-5">
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

        {/* Pipeline Progress Display */}
        {generationResult && (
          <div className={`rounded-xl p-4 border ${generationResult.ok ? "bg-emerald-500/10 border-emerald-500/30" : "bg-red-500/10 border-red-500/30"}`}>
            <div className="flex items-center gap-2 mb-1">
              {generationResult.ok ? <CheckCircle size={16} className="text-emerald-400" /> : <AlertCircle size={16} className="text-red-400" />}
              <span className="text-xs font-medium text-warroom-text">{generationResult.ok ? "Pipeline started" : "Pipeline failed"}</span>
            </div>
            
            {generationResult.ok && pipelineStatus && (
              <div className="mt-3 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-warroom-text">
                    {pipelineStatus.current_step ? `Step: ${pipelineStatus.current_step}` : "Initializing..."}
                  </span>
                  <span className="text-warroom-muted">
                    {pipelineStatus.progress ? `${Math.round(pipelineStatus.progress * 100)}%` : "0%"}
                  </span>
                </div>
                
                {/* Progress bar */}
                <div className="w-full bg-warroom-bg rounded-full h-2">
                  <div 
                    className="bg-warroom-accent h-2 rounded-full transition-all duration-300 ease-out"
                    style={{ width: `${(pipelineStatus.progress || 0) * 100}%` }}
                  />
                </div>
                
                {pollStatus === "processing" && <div className="flex items-center gap-2 text-[11px] text-warroom-muted">
                  <Loader2 size={12} className="animate-spin text-warroom-accent" /> 
                  Processing pipeline...
                </div>}
                
                {pollStatus === "completed" && <div className="flex items-center gap-2 text-[11px] text-emerald-400">
                  <CheckCircle size={12} /> 
                  Pipeline complete — video ready!
                </div>}
                
                {pollStatus === "failed" && <div className="flex items-center gap-2 text-[11px] text-red-400">
                  <AlertCircle size={12} /> 
                  Pipeline failed
                </div>}
                
                {/* Generated assets preview */}
                {pipelineStatus.generated_assets && pipelineStatus.generated_assets.length > 0 && (
                  <div className="mt-3">
                    <p className="text-[10px] text-warroom-muted uppercase tracking-wider mb-2">Generated Assets</p>
                    <div className="flex gap-2 flex-wrap">
                      {pipelineStatus.generated_assets.map((asset: any, index: number) => (
                        <div key={index} className="flex items-center gap-1 px-2 py-1 bg-warroom-bg rounded text-[10px] text-warroom-text">
                          {asset.type === "image" && <Image size={10} />}
                          {asset.type === "video" && <Video size={10} />}
                          {asset.name || `Asset ${index + 1}`}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
            
            {generationResult.error && <p className="text-[11px] text-red-400 mt-1">{generationResult.error}</p>}
          </div>
        )}

        {/* Distribution Panel — shown when video is completed */}
        {generationResult?.ok && pollStatus === "completed" && (
          <div className="mt-6">
            <DistributionPanel
              videoProjectId={pollingProjectId ? parseInt(pollingProjectId) : null}
              videoUrl={projects.find(p => p.id === pollingProjectId)?.video_url || null}
              caption={wizardScript || ""}
              onDistribute={(result) => {
                console.log("Distribution launched:", result);
                // Optionally show success notification or redirect
              }}
            />
          </div>
        )}

        <div className="flex justify-between">
          <button onClick={() => setWizardStep("storyboard")} className="px-4 py-2 bg-warroom-bg border border-warroom-border text-xs text-warroom-muted rounded-lg">Back</button>
          <div className="flex gap-2">
            <button onClick={resetWizard} className="px-4 py-2 bg-warroom-bg border border-warroom-border text-xs text-warroom-muted rounded-lg">Start Over</button>
            <button onClick={createAndGenerate} disabled={generating || !wizardScript.trim()}
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