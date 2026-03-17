"use client";

import { useState, useEffect } from "react";
import { CheckSquare, Square, MessageCircle, Users } from "lucide-react";
import { API, authFetch } from "@/lib/api";

interface PersonaSelectorProps {
  selectedIds: number[];
  onSelectionChange: (ids: number[]) => void;
}

interface Persona {
  id: number;
  name: string;
  archetype: string;
  avatar: string;
  psychographics: string[];
  behavioral_patterns: string[];
  friction_points: string[];
  engagement_style: string;
}

interface PersonaSelectorProps {
  selectedIds: number[];
  onSelectionChange: (ids: number[]) => void;
  onTalkToPersona?: (personaId: number, personaName: string) => void;
}

export default function PersonaSelector({
  selectedIds,
  onSelectionChange,
  onTalkToPersona
}: PersonaSelectorProps) {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPersonas();
  }, []);

  const fetchPersonas = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await authFetch(`${API}/api/simulate/personas`);
      
      if (response.ok) {
        const data = await response.json();
        setPersonas(data.personas || data || []);
      } else {
        // Use mock data if API fails
        setPersonas(getMockPersonas());
      }
    } catch (err) {
      console.error("Failed to fetch personas:", err);
      setError("Failed to load personas");
      setPersonas(getMockPersonas());
    }
    
    setLoading(false);
  };

  const getMockPersonas = (): Persona[] => {
    return [
      {
        id: 1,
        name: "Sarah Miller",
        archetype: "Casual User",
        avatar: "SM",
        psychographics: [
          "Busy working professional",
          "Values efficiency and quick wins", 
          "Skeptical of overhyped products"
        ],
        behavioral_patterns: ["Scrolls quickly", "Saves for later", "Asks practical questions"],
        friction_points: ["Unclear value prop", "Too much commitment", "Generic promises"],
        engagement_style: "cautious_optimizer"
      },
      {
        id: 2,
        name: "Tech Skeptic",
        archetype: "Critical Thinker", 
        avatar: "TS",
        psychographics: [
          "Experienced with tech tools",
          "Burned by false promises before",
          "Values authenticity over hype"
        ],
        behavioral_patterns: ["Questions everything", "Looks for social proof", "Researches extensively"],
        friction_points: ["Buzzword-heavy content", "No proof points", "AI fluff"],
        engagement_style: "analytical_challenger"
      },
      {
        id: 3,
        name: "Emma Rodriguez",
        archetype: "Early Adopter",
        avatar: "ER",
        psychographics: [
          "Always trying new things",
          "Active on social media",
          "Influences friend group decisions"
        ],
        behavioral_patterns: ["Shares immediately", "Comments with questions", "Tags friends"],
        friction_points: ["Outdated methods", "No social proof", "Can't share easily"],
        engagement_style: "enthusiastic_sharer"
      },
      {
        id: 4,
        name: "Budget-Conscious Ben",
        archetype: "Value Seeker",
        avatar: "BC",
        psychographics: [
          "Price-sensitive decision maker",
          "Looks for free alternatives first",
          "Needs clear ROI justification"
        ],
        behavioral_patterns: ["Compares prices", "Seeks discounts", "Reads reviews carefully"],
        friction_points: ["No pricing mentioned", "No free tier", "Expensive without clear value"],
        engagement_style: "cautious_evaluator"
      },
      {
        id: 5,
        name: "Influencer Maya",
        archetype: "Content Creator", 
        avatar: "IM",
        psychographics: [
          "Builds personal brand",
          "Needs shareable content",
          "Audience engagement focused"
        ],
        behavioral_patterns: ["Screenshots for stories", "Reposts to audience", "Creates response content"],
        friction_points: ["Not Instagram-worthy", "Hard to explain to followers", "No viral potential"],
        engagement_style: "amplifier_curator"
      },
      {
        id: 6,
        name: "Business Owner Lisa",
        archetype: "Entrepreneur",
        avatar: "BO",
        psychographics: [
          "Time-constrained decision maker",
          "ROI-focused mindset",
          "Practical implementation needs"
        ],
        behavioral_patterns: ["Saves to review later", "Delegates research", "Wants quick demos"],
        friction_points: ["Too complicated", "No clear business case", "Long learning curve"],
        engagement_style: "efficiency_seeker"
      },
      {
        id: 7,
        name: "Research Rachel",
        archetype: "Information Gatherer",
        avatar: "RR", 
        psychographics: [
          "Thorough research process",
          "Compares all options",
          "Risk-averse decision making"
        ],
        behavioral_patterns: ["Bookmarks everything", "Takes detailed notes", "Asks follow-up questions"],
        friction_points: ["Insufficient detail", "No comparison data", "Missing edge cases"],
        engagement_style: "methodical_researcher"
      },
      {
        id: 8,
        name: "Impulse Ian",
        archetype: "Quick Decider",
        avatar: "II",
        psychographics: [
          "Makes fast decisions", 
          "FOMO-driven behavior",
          "Responds to urgency"
        ],
        behavioral_patterns: ["Acts immediately", "Doesn't read details", "Influenced by scarcity"],
        friction_points: ["Too much information", "No clear next step", "Decision paralysis"],
        engagement_style: "instant_converter"
      }
    ];
  };

  const togglePersona = (personaId: number) => {
    const newSelected = selectedIds.includes(personaId)
      ? selectedIds.filter(id => id !== personaId)
      : [...selectedIds, personaId];
    
    onSelectionChange(newSelected);
  };

  const selectAll = () => {
    onSelectionChange(personas.map(p => p.id));
  };

  const deselectAll = () => {
    onSelectionChange([]);
  };

  const handleTalkToPersona = () => {
    const firstSelected = personas.find(p => selectedIds.includes(p.id));
    if (firstSelected && onTalkToPersona) {
      onTalkToPersona(firstSelected.id, firstSelected.name);
    }
  };

  if (loading) {
    return (
      <div className="bg-warroom-surface border border-warroom-border rounded-xl p-6">
        <div className="animate-spin w-6 h-6 border-2 border-warroom-accent border-t-transparent rounded-full mx-auto mb-3"></div>
        <p className="text-sm text-warroom-muted text-center">Loading personas...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-warroom-surface border border-warroom-border rounded-xl p-6">
        <div className="text-center">
          <div className="text-red-400 mb-2">⚠️</div>
          <p className="text-sm text-warroom-muted">{error}</p>
          <button 
            onClick={fetchPersonas}
            className="mt-2 text-xs text-warroom-accent hover:text-warroom-accent/80"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-warroom-surface border border-warroom-border rounded-xl p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Users size={16} className="text-warroom-accent" />
          <h3 className="text-sm font-semibold text-warroom-text">Select Personas</h3>
        </div>
        <div className="flex gap-2">
          <button
            onClick={selectAll}
            className="text-xs text-warroom-muted hover:text-warroom-accent transition"
          >
            Select All
          </button>
          <span className="text-warroom-border">·</span>
          <button
            onClick={deselectAll}
            className="text-xs text-warroom-muted hover:text-warroom-accent transition"
          >
            Deselect All
          </button>
        </div>
      </div>

      {/* Selected count */}
      <div className="mb-4 text-xs text-warroom-muted">
        {selectedIds.length} of {personas.length} personas selected
      </div>

      {/* Persona cards */}
      <div className="space-y-3 mb-6">
        {personas.map((persona) => {
          const isSelected = selectedIds.includes(persona.id);
          
          return (
            <div
              key={persona.id}
              onClick={() => togglePersona(persona.id)}
              className={`p-4 border rounded-xl cursor-pointer transition ${
                isSelected
                  ? "border-warroom-accent bg-warroom-accent/5"
                  : "border-warroom-border bg-warroom-bg hover:border-warroom-accent/30"
              }`}
            >
              <div className="flex items-start gap-3">
                {/* Checkbox */}
                <div className="pt-0.5">
                  {isSelected ? (
                    <CheckSquare size={16} className="text-warroom-accent" />
                  ) : (
                    <Square size={16} className="text-warroom-muted" />
                  )}
                </div>
                
                {/* Avatar */}
                <div className="w-10 h-10 rounded-full bg-warroom-accent/20 text-warroom-accent flex items-center justify-center text-xs font-bold flex-shrink-0">
                  {persona.avatar}
                </div>
                
                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="text-sm font-medium text-warroom-text">{persona.name}</h4>
                    <span className="px-2 py-0.5 bg-warroom-bg rounded text-[10px] text-warroom-muted font-medium">
                      {persona.archetype}
                    </span>
                  </div>
                  
                  {/* Key traits */}
                  <div className="space-y-1">
                    {persona.psychographics.slice(0, 3).map((trait, index) => (
                      <div key={index} className="text-xs text-warroom-muted flex items-center gap-1">
                        <div className="w-1 h-1 rounded-full bg-warroom-accent/40"></div>
                        {trait}
                      </div>
                    ))}
                  </div>
                  
                  {/* Engagement style */}
                  <div className="mt-2 text-[10px] text-warroom-accent">
                    Style: {persona.engagement_style.replace("_", " ")}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Talk to Persona button */}
      {selectedIds.length > 0 && onTalkToPersona && (
        <button
          onClick={handleTalkToPersona}
          className="w-full py-3 bg-warroom-accent/10 border border-warroom-accent text-warroom-accent text-sm font-medium rounded-lg hover:bg-warroom-accent/20 transition flex items-center justify-center gap-2"
        >
          <MessageCircle size={16} />
          Talk to Persona
          {selectedIds.length > 1 && (
            <span className="text-xs opacity-75">
              (chat with {personas.find(p => selectedIds.includes(p.id))?.name})
            </span>
          )}
        </button>
      )}
      
      {/* Help text */}
      <div className="mt-4 text-xs text-warroom-muted text-center">
        Select personas to test your script against their behavioral patterns and friction points
      </div>
    </div>
  );
}