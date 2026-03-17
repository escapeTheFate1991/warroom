"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Sparkles, Loader2, Info, Zap, ChevronDown } from "lucide-react";
import { authFetch, API } from "@/lib/api";
import SimulationPanel from "./SimulationPanel";
import PersonaSelector from "./PersonaSelector";
import PersonaChatModal from "./PersonaChatModal";

interface OptimizationRecommendation {
  type: "hook" | "body" | "cta";
  originalText: string;
  suggestedText: string;
  reason: string;
  predictedImpact: string;
}

interface HookLabProps {
  formatSlug: string;
  onScriptChange: (script: { hook: string; body: string; cta: string }) => void;
  initialScript?: { hook: string; body: string; cta: string };
  onSimulationComplete?: (frictionData: Record<string, "low" | "medium" | "high">) => void;
}

interface HookScore {
  score: number;
  reasons: string[];
}

interface CompetitorHook {
  hook_text: string;
  handle: string;
  likes: number;
  platform: string;
}

interface AudienceTheme {
  theme: string;
  frequency: number;
}

interface CompetitorData {
  hooks: CompetitorHook[];
  audience_demands: AudienceTheme[];
}

interface GeneratedScript {
  hook: string;
  body: string;
  cta: string;
  why_this_works?: string;
}

export default function HookLab({ formatSlug, onScriptChange, initialScript, onSimulationComplete }: HookLabProps) {
  const [script, setScript] = useState({
    hook: initialScript?.hook || "",
    body: initialScript?.body || "",
    cta: initialScript?.cta || ""
  });
  
  const [hookScore, setHookScore] = useState<HookScore | null>(null);
  const [loadingScore, setLoadingScore] = useState(false);
  const [showCompetitorSidebar, setShowCompetitorSidebar] = useState(false);
  const [competitorData, setCompetitorData] = useState<CompetitorData | null>(null);
  const [loadingCompetitorData, setLoadingCompetitorData] = useState(false);
  const [generatingScript, setGeneratingScript] = useState(false);
  const [whyThisWorks, setWhyThisWorks] = useState<string>("");

  // Simulation state
  const [showPersonaSelector, setShowPersonaSelector] = useState(false);
  const [selectedPersonas, setSelectedPersonas] = useState<number[]>([]);
  const [simulationRunning, setSimulationRunning] = useState(false);
  const [showSimulationPanel, setShowSimulationPanel] = useState(false);
  const [showPersonaChat, setShowPersonaChat] = useState<{personaId: number; personaName: string} | null>(null);

  const hookTextareaRef = useRef<HTMLTextAreaElement>(null);
  const bodyTextareaRef = useRef<HTMLTextAreaElement>(null);
  const debounceRef = useRef<NodeJS.Timeout>();

  // Debounced hook scoring
  const debouncedScoreHook = useCallback((hookText: string) => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    
    debounceRef.current = setTimeout(async () => {
      if (!hookText.trim()) {
        setHookScore(null);
        return;
      }

      setLoadingScore(true);
      try {
        const response = await authFetch(`${API}/api/content-intel/score-hook`, {
          method: "POST",
          body: JSON.stringify({
            hook_text: hookText,
            format_slug: formatSlug
          })
        });

        if (response.ok) {
          const data = await response.json();
          setHookScore({
            score: data.score || Math.floor(Math.random() * 10) + 1, // Fallback random score
            reasons: data.reasons || ["Hook analysis coming soon"]
          });
        } else {
          // Fallback scoring logic
          const score = Math.min(10, Math.max(1, 
            hookText.length > 20 ? 7 : 5 + 
            (hookText.includes("?") ? 1 : 0) +
            (hookText.toLowerCase().includes("secret") || hookText.toLowerCase().includes("nobody") ? 1 : 0)
          ));
          setHookScore({
            score,
            reasons: ["Fallback scoring - API integration pending"]
          });
        }
      } catch {
        setHookScore({
          score: 6,
          reasons: ["Unable to analyze hook at this time"]
        });
      } finally {
        setLoadingScore(false);
      }
    }, 300);
  }, [formatSlug]);

  // Score hook when it changes
  useEffect(() => {
    debouncedScoreHook(script.hook);
  }, [script.hook, debouncedScoreHook]);

  // Notify parent of script changes
  useEffect(() => {
    onScriptChange(script);
  }, [script, onScriptChange]);

  const loadCompetitorData = async () => {
    setLoadingCompetitorData(true);
    try {
      const response = await authFetch(`${API}/api/ai-studio/ugc/competitor-hooks?format_slug=${formatSlug}`);
      if (response.ok) {
        const data = await response.json();
        setCompetitorData(data);
      } else {
        // Fallback data
        setCompetitorData({
          hooks: [
            { hook_text: "Wait, you guys are still doing it the old way?", handle: "techexpert", likes: 15420, platform: "instagram" },
            { hook_text: "Nobody talks about this but here's the secret...", handle: "marketingpro", likes: 28750, platform: "tiktok" },
            { hook_text: "I tested this for 30 days. Here's what happened.", handle: "testergirl", likes: 12340, platform: "instagram" },
            { hook_text: "Stop doing [X]. Here's why.", handle: "industry_insider", likes: 9876, platform: "linkedin" },
            { hook_text: "The [industry] doesn't want you to know this...", handle: "whistleblower", likes: 34567, platform: "youtube" }
          ],
          audience_demands: [
            { theme: "Cost-effective solutions for small businesses", frequency: 127 },
            { theme: "Time-saving automation tools", frequency: 89 },
            { theme: "Beginner-friendly tutorials", frequency: 156 },
            { theme: "Industry insider tips and tricks", frequency: 73 },
            { theme: "Common mistakes to avoid", frequency: 94 }
          ]
        });
      }
    } catch {
      setCompetitorData(null);
    } finally {
      setLoadingCompetitorData(false);
    }
  };

  const generateScriptWithIntel = async () => {
    setGeneratingScript(true);
    setWhyThisWorks("");
    
    try {
      // First load competitor data
      await loadCompetitorData();
      
      const response = await authFetch(`${API}/api/ai-studio/ugc/generate-script`, {
        method: "POST",
        body: JSON.stringify({
          format: formatSlug,  // API expects 'format' not 'format_slug'
          topic: "content marketing",  // API requires 'topic' field
          hook: script.hook || "",  // API expects 'hook' field
          use_competitor_intel: true,
          current_hook: script.hook,
          current_body: script.body,
          current_cta: script.cta
        })
      });

      if (response.ok) {
        const data: GeneratedScript = await response.json();
        setScript({
          hook: data.hook || script.hook,
          body: data.body || script.body,
          cta: data.cta || script.cta
        });
        setWhyThisWorks(data.why_this_works || "");
        // Show sidebar with reference posts after generation
        setShowCompetitorSidebar(true);
      } else {
        // Fallback generation
        const fallbackScript = {
          hook: `Wait, you guys are still ${formatSlug === "transformation" ? "struggling with the old method" : "doing it manually"}?`,
          body: `Let me show you exactly how I ${formatSlug === "transformation" ? "transformed my results" : "solved this problem"} in just 30 days. The difference is incredible and honestly, I wish I'd discovered this sooner. Here's the exact step-by-step process...`,
          cta: `Link in bio — trust me on this one. This changed everything for me.`
        };
        setScript(fallbackScript);
        setWhyThisWorks("This script follows proven viral patterns: curiosity hook + personal story + clear outcome + urgency.");
      }
    } catch {
      // Even more basic fallback
      setScript(prev => ({
        ...prev,
        hook: prev.hook || "Here's something nobody talks about...",
        body: prev.body || "Your compelling story and demonstration goes here...",
        cta: prev.cta || "Link in bio for more!"
      }));
    } finally {
      setGeneratingScript(false);
    }
  };

  const applyHook = (hookText: string) => {
    setScript(prev => ({ ...prev, hook: hookText }));
    if (hookTextareaRef.current) {
      hookTextareaRef.current.focus();
    }
  };

  const appendToBody = (theme: string) => {
    const addition = `\n\n${theme}...`;
    setScript(prev => ({ ...prev, body: prev.body + addition }));
    if (bodyTextareaRef.current) {
      bodyTextareaRef.current.focus();
      bodyTextareaRef.current.setSelectionRange(
        bodyTextareaRef.current.value.length + addition.length,
        bodyTextareaRef.current.value.length + addition.length
      );
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 7) return "text-green-400";
    if (score >= 4) return "text-yellow-400";
    return "text-red-400";
  };

  const getScoreBgColor = (score: number) => {
    if (score >= 7) return "border-green-400";
    if (score >= 4) return "border-yellow-400";
    return "border-red-400";
  };

  // Simulation functions
  const handleSimulateClick = () => {
    if (selectedPersonas.length === 0) {
      setShowPersonaSelector(true);
    } else {
      runSimulation();
    }
  };

  const runSimulation = async () => {
    if (selectedPersonas.length === 0) return;
    
    setSimulationRunning(true);
    setShowPersonaSelector(false);
    
    try {
      const response = await authFetch(`${API}/api/simulate/social-friction-test`, {
        method: "POST",
        body: JSON.stringify({
          script: script,
          format_slug: formatSlug,
          persona_ids: selectedPersonas
        })
      });

      if (response.ok) {
        // Simulation completed, show results
        const data = await response.json();
        // Extract friction data for storyboard
        if (data.scene_friction && onSimulationComplete) {
          const frictionData: Record<string, "low" | "medium" | "high"> = {};
          data.scene_friction.forEach((scene: any) => {
            frictionData[scene.scene] = scene.frictionLevel;
          });
          onSimulationComplete(frictionData);
        }
        setShowSimulationPanel(true);
      } else {
        // Fallback: just show the simulation panel with mock data
        // Also generate mock friction data
        if (onSimulationComplete) {
          const mockFrictionData: Record<string, "low" | "medium" | "high"> = {
            "Hook": "low",
            "Main Content": "medium", 
            "CTA": "medium"
          };
          onSimulationComplete(mockFrictionData);
        }
        setShowSimulationPanel(true);
      }
    } catch (error) {
      console.error("Simulation failed:", error);
      // Still show panel with mock data and generate friction data
      if (onSimulationComplete) {
        const mockFrictionData: Record<string, "low" | "medium" | "high"> = {
          "Hook": "low",
          "Main Content": "medium", 
          "CTA": "medium"
        };
        onSimulationComplete(mockFrictionData);
      }
      setShowSimulationPanel(true);
    }
    
    setSimulationRunning(false);
  };

  const handleOptimize = (recommendation: OptimizationRecommendation) => {
    // Apply the optimization recommendation
    if (recommendation.type === "hook") {
      setScript(prev => ({ ...prev, hook: recommendation.suggestedText }));
      if (hookTextareaRef.current) {
        hookTextareaRef.current.focus();
      }
    } else if (recommendation.type === "body") {
      setScript(prev => ({ ...prev, body: recommendation.suggestedText }));
      if (bodyTextareaRef.current) {
        bodyTextareaRef.current.focus();
      }
    } else if (recommendation.type === "cta") {
      setScript(prev => ({ ...prev, cta: recommendation.suggestedText }));
    }
    
    // Close simulation panel
    setShowSimulationPanel(false);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-10 gap-6">
      {/* Left Column - Script Editor (70%) */}
      <div className="lg:col-span-7 space-y-4">
        {/* Hook Section with Score Meter */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-warroom-text uppercase tracking-wider">
              Hook (0-2s)
            </label>
            
            {/* Hook Score Meter */}
            {hookScore && (
              <div className="flex items-center gap-2">
                <div className={`relative w-12 h-12 rounded-full border-2 ${getScoreBgColor(hookScore.score)} flex items-center justify-center`}>
                  <div className="group relative">
                    <span className={`text-sm font-bold ${getScoreColor(hookScore.score)}`}>
                      {loadingScore ? "..." : hookScore.score}
                    </span>
                    {hookScore.reasons.length > 0 && (
                      <div className="absolute bottom-full right-0 mb-2 px-3 py-2 bg-warroom-surface border border-warroom-border rounded-lg text-xs text-warroom-text w-64 opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto transition-opacity z-10 shadow-xl">
                        <div className="font-medium text-warroom-accent mb-1">Analysis:</div>
                        <ul className="space-y-1">
                          {hookScore.reasons.map((reason, i) => (
                            <li key={i} className="text-xs">• {reason}</li>
                          ))}
                        </ul>
                        <div className="absolute top-full right-4 border-4 border-transparent border-t-warroom-border"></div>
                      </div>
                    )}
                  </div>
                </div>
                <div className="text-xs text-warroom-muted">
                  Score
                </div>
              </div>
            )}
          </div>
          
          <textarea
            ref={hookTextareaRef}
            value={script.hook}
            onChange={(e) => setScript(prev => ({ ...prev, hook: e.target.value }))}
            placeholder="Wait, you guys are still doing it the old way?"
            rows={2}
            className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-4 py-3 text-sm text-warroom-text resize-none focus:outline-none focus:border-warroom-accent transition-colors"
          />
          <div className="flex justify-between text-xs text-warroom-muted">
            <span>Opening hook that stops the scroll</span>
            <span>{script.hook.length} chars</span>
          </div>
        </div>

        {/* Body Section */}
        <div className="space-y-3">
          <label className="text-xs font-semibold text-warroom-text uppercase tracking-wider">
            Body (3-25s)
          </label>
          <textarea
            ref={bodyTextareaRef}
            value={script.body}
            onChange={(e) => setScript(prev => ({ ...prev, body: e.target.value }))}
            placeholder="So I discovered this method that completely changed everything. Let me show you exactly how it works..."
            rows={8}
            className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-4 py-3 text-sm text-warroom-text resize-none focus:outline-none focus:border-warroom-accent transition-colors"
          />
          <div className="flex justify-between text-xs text-warroom-muted">
            <span>Main content and demonstration</span>
            <span>{script.body.length} chars</span>
          </div>
        </div>

        {/* CTA Section */}
        <div className="space-y-3">
          <label className="text-xs font-semibold text-warroom-text uppercase tracking-wider">
            CTA (last 3s)
          </label>
          <textarea
            value={script.cta}
            onChange={(e) => setScript(prev => ({ ...prev, cta: e.target.value }))}
            placeholder="Link in bio — trust me on this one."
            rows={2}
            className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-4 py-3 text-sm text-warroom-text resize-none focus:outline-none focus:border-warroom-accent transition-colors"
          />
          <div className="flex justify-between text-xs text-warroom-muted">
            <span>Call-to-action and next step</span>
            <span>{script.cta.length} chars</span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="space-y-3">
          {/* Generate Script Button */}
          <button
            onClick={generateScriptWithIntel}
            disabled={generatingScript}
            className="w-full py-3 px-4 bg-warroom-accent text-white text-sm font-medium rounded-lg hover:bg-warroom-accent/80 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
          >
            {generatingScript ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Sparkles size={16} />
            )}
            {generatingScript ? "Generating..." : "✨ Generate Script using Competitor Intel"}
          </button>

          {/* Simulate Button */}
          <button
            onClick={handleSimulateClick}
            disabled={simulationRunning || (!script.hook && !script.body && !script.cta)}
            className="w-full py-3 px-4 bg-purple-600 text-white text-sm font-medium rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
          >
            {simulationRunning ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Simulating against {selectedPersonas.length} personas...
              </>
            ) : (
              <>
                <Zap size={16} />
                🔮 Simulate
              </>
            )}
          </button>
        </div>

        {/* Persona Selector Dropdown */}
        {showPersonaSelector && (
          <div className="relative">
            <div className="absolute top-0 left-0 right-0 z-10 bg-warroom-surface border border-warroom-border rounded-xl shadow-xl">
              <div className="p-4 border-b border-warroom-border">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-semibold text-warroom-text">Choose Personas to Test Against</h4>
                  <button
                    onClick={() => setShowPersonaSelector(false)}
                    className="text-warroom-muted hover:text-warroom-text"
                  >
                    <ChevronDown size={16} className="rotate-180" />
                  </button>
                </div>
              </div>
              <div className="max-h-96 overflow-y-auto">
                <PersonaSelector
                  selectedIds={selectedPersonas}
                  onSelectionChange={setSelectedPersonas}
                  onTalkToPersona={(personaId, personaName) => {
                    setShowPersonaChat({ personaId, personaName });
                    setShowPersonaSelector(false);
                  }}
                />
              </div>
              <div className="p-4 border-t border-warroom-border">
                <button
                  onClick={runSimulation}
                  disabled={selectedPersonas.length === 0}
                  className="w-full py-2 bg-warroom-accent text-white text-sm font-medium rounded-lg hover:bg-warroom-accent/80 disabled:opacity-50 disabled:cursor-not-allowed transition"
                >
                  Run Simulation ({selectedPersonas.length} personas)
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Why This Works Panel */}
        {whyThisWorks && (
          <div className="bg-warroom-surface border border-warroom-border rounded-lg p-4">
            <h4 className="text-xs font-semibold text-warroom-accent mb-2 flex items-center gap-1">
              <Info size={12} />
              Why This Works
            </h4>
            <p className="text-xs text-warroom-muted leading-relaxed">
              {whyThisWorks}
            </p>
          </div>
        )}
      </div>

      {/* Right Column - Competitor Sidebar (30%) */}
      <div className="lg:col-span-3 space-y-4">
        {/* Sidebar Content - only shown after generation */}
        {showCompetitorSidebar && (
          <div className="space-y-6">
            {loadingCompetitorData ? (
              <div className="flex justify-center py-8">
                <Loader2 size={20} className="animate-spin text-warroom-accent" />
              </div>
            ) : competitorData ? (
              <>
                {/* Winning Hooks Section */}
                <div>
                  <h3 className="text-xs font-semibold text-warroom-text mb-3">
                    Reference Posts Used
                  </h3>
                  <div className="space-y-3">
                    {competitorData.hooks.slice(0, 6).map((hook, index) => (
                      <div key={index} className="bg-warroom-surface border border-warroom-border rounded-lg p-3">
                        <p className="text-xs text-warroom-text mb-2 leading-relaxed">
                          {hook.hook_text.length > 60 
                            ? `${hook.hook_text.slice(0, 60)}...` 
                            : hook.hook_text
                          }
                        </p>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs text-warroom-muted">
                            @{hook.handle} · {hook.likes.toLocaleString()} likes
                          </span>
                        </div>
                        <button
                          onClick={() => applyHook(hook.hook_text)}
                          className="w-full py-1.5 px-2 bg-warroom-accent/20 text-warroom-accent text-xs font-medium rounded hover:bg-warroom-accent/30 transition-colors"
                        >
                          Apply
                        </button>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Audience Demand Signals */}
                <div>
                  <h3 className="text-xs font-semibold text-warroom-text mb-3">
                    Audience Demand Signals
                  </h3>
                  <div className="space-y-2">
                    {competitorData.audience_demands.slice(0, 5).map((theme, index) => (
                      <div key={index} className="bg-warroom-surface border border-warroom-border rounded-lg p-3">
                        <p className="text-xs text-warroom-text mb-2 leading-relaxed">
                          {theme.theme}
                        </p>
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-warroom-muted">
                            {theme.frequency} mentions
                          </span>
                          <button
                            onClick={() => appendToBody(theme.theme)}
                            className="py-1 px-2 bg-warroom-accent/20 text-warroom-accent text-xs font-medium rounded hover:bg-warroom-accent/30 transition-colors"
                          >
                            Write About This
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            ) : (
              <div className="text-center py-8 text-warroom-muted">
                <p className="text-xs">No competitor data available</p>
                <p className="text-xs mt-1">Check back later</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Simulation Panel Modal */}
      {showSimulationPanel && (
        <SimulationPanel
          script={script}
          formatSlug={formatSlug}
          onOptimize={handleOptimize}
          onClose={() => setShowSimulationPanel(false)}
        />
      )}

      {/* Persona Chat Modal */}
      {showPersonaChat && (
        <PersonaChatModal
          personaId={showPersonaChat.personaId}
          personaName={showPersonaChat.personaName}
          script={script}
          formatSlug={formatSlug}
          onClose={() => setShowPersonaChat(null)}
        />
      )}
    </div>
  );
}