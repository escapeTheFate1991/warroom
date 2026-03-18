"use client";

import { useState, useEffect } from "react";
import { X, Layout, Monitor, Smartphone, Square, Eye } from "lucide-react";
import { API, authFetch } from "@/lib/api";

interface EditingDNA {
  id: string;
  name: string;
  layout_type: string;
  aspect_ratio: string;
  thumbnail_url?: string;
  description?: string;
  layers?: any[];
  settings?: any;
}

interface EditingDNADetail extends EditingDNA {
  layers: any[];
  settings: any;
  preview_config?: any;
}

interface EditingDNADrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectDNA: (dna: EditingDNA) => void;
}

const ASPECT_RATIO_ICONS: Record<string, any> = {
  "9:16": Smartphone,
  "16:9": Monitor, 
  "1:1": Square,
  "4:5": Square,
};

const LAYOUT_COLORS: Record<string, string> = {
  "split_screen": "bg-blue-500/10 border-blue-500/20 text-blue-400",
  "pip": "bg-green-500/10 border-green-500/20 text-green-400", 
  "overlay": "bg-purple-500/10 border-purple-500/20 text-purple-400",
  "grid": "bg-yellow-500/10 border-yellow-500/20 text-yellow-400",
  "full_frame": "bg-gray-500/10 border-gray-500/20 text-gray-400",
};

export default function EditingDNADrawer({
  isOpen,
  onClose,
  onSelectDNA
}: EditingDNADrawerProps) {
  const [dnaTemplates, setDnaTemplates] = useState<EditingDNA[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedDNA, setSelectedDNA] = useState<EditingDNADetail | null>(null);
  const [previewingId, setPreviewingId] = useState<string | null>(null);

  // Fetch DNA templates
  const fetchDNATemplates = async () => {
    setLoading(true);
    try {
      const response = await authFetch(`${API}/api/ai-studio/ugc/editing-dna`);
      if (response.ok) {
        const data = await response.json();
        const templates = Array.isArray(data) ? data : data.templates || [];
        setDnaTemplates(templates);
      } else {
        console.error("Failed to fetch DNA templates");
        // Fallback demo data
        setDnaTemplates([
          {
            id: "demo_1",
            name: "Split Screen Vertical",
            layout_type: "split_screen",
            aspect_ratio: "9:16",
            description: "Character on left, product showcase on right",
            thumbnail_url: "https://via.placeholder.com/200x300"
          },
          {
            id: "demo_2", 
            name: "PIP Bottom Right",
            layout_type: "pip",
            aspect_ratio: "16:9",
            description: "Small character window in bottom right corner",
            thumbnail_url: "https://via.placeholder.com/300x200"
          },
          {
            id: "demo_3",
            name: "Full Frame Portrait",
            layout_type: "full_frame", 
            aspect_ratio: "9:16",
            description: "Character fills entire frame",
            thumbnail_url: "https://via.placeholder.com/200x300"
          },
          {
            id: "demo_4",
            name: "Product Grid Layout",
            layout_type: "grid",
            aspect_ratio: "1:1",
            description: "4-panel grid with character and product shots",
            thumbnail_url: "https://via.placeholder.com/300x300"
          }
        ]);
      }
    } catch (error) {
      console.error("Error fetching DNA templates:", error);
      setDnaTemplates([]);
    }
    setLoading(false);
  };

  // Fetch DNA detail
  const fetchDNADetail = async (dnaId: string) => {
    try {
      const response = await authFetch(`${API}/api/ai-studio/ugc/editing-dna/${dnaId}`);
      if (response.ok) {
        const data = await response.json();
        setSelectedDNA(data);
      } else {
        // Fallback demo detail
        const template = dnaTemplates.find(t => t.id === dnaId);
        if (template) {
          setSelectedDNA({
            ...template,
            layers: [
              { id: 1, type: "video", position: { x: 0, y: 0, width: 50, height: 100 }, name: "Character" },
              { id: 2, type: "image", position: { x: 50, y: 0, width: 50, height: 100 }, name: "Product" }
            ],
            settings: {
              transition_duration: 0.3,
              background_color: "#000000",
              border_radius: 8
            }
          });
        }
      }
    } catch (error) {
      console.error("Error fetching DNA detail:", error);
    }
  };

  // Extract DNA from competitor post
  const extractDNA = async (postId: string) => {
    try {
      const response = await authFetch(`${API}/api/ai-studio/ugc/editing-dna/extract`, {
        method: "POST",
        body: JSON.stringify({ post_id: postId })
      });
      
      if (response.ok) {
        const newDNA = await response.json();
        setDnaTemplates(prev => [newDNA, ...prev]);
        return newDNA;
      }
    } catch (error) {
      console.error("Error extracting DNA:", error);
    }
    return null;
  };

  // Generate layout preview visualization
  const renderLayoutPreview = (dna: EditingDNA) => {
    const IconComponent = ASPECT_RATIO_ICONS[dna.aspect_ratio] || Square;
    const colorClass = LAYOUT_COLORS[dna.layout_type] || LAYOUT_COLORS["full_frame"];
    
    return (
      <div className={`w-full h-32 rounded-lg border-2 border-dashed flex items-center justify-center ${colorClass} relative`}>
        <IconComponent size={24} />
        {/* Visual representation of layout */}
        <div className="absolute inset-2 flex">
          {dna.layout_type === "split_screen" && (
            <>
              <div className="flex-1 bg-white/10 rounded-l border-r border-current/20" />
              <div className="flex-1 bg-white/5 rounded-r" />
            </>
          )}
          {dna.layout_type === "pip" && (
            <>
              <div className="flex-1 bg-white/5 rounded relative">
                <div className="absolute bottom-1 right-1 w-6 h-4 bg-white/20 rounded border border-current/20" />
              </div>
            </>
          )}
          {dna.layout_type === "grid" && (
            <div className="flex-1 grid grid-cols-2 gap-1">
              <div className="bg-white/10 rounded" />
              <div className="bg-white/5 rounded" />
              <div className="bg-white/5 rounded" />
              <div className="bg-white/10 rounded" />
            </div>
          )}
          {dna.layout_type === "overlay" && (
            <div className="flex-1 bg-white/5 rounded relative">
              <div className="absolute inset-2 bg-white/10 rounded border border-current/20" />
            </div>
          )}
        </div>
      </div>
    );
  };

  useEffect(() => {
    if (isOpen) {
      fetchDNATemplates();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/50 z-40"
        onClick={onClose}
      />
      
      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-[400px] bg-warroom-surface border-l border-warroom-border z-50 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-warroom-border">
          <h2 className="text-sm font-semibold text-warroom-text">Visual Templates</h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-warroom-bg rounded transition"
          >
            <X size={16} className="text-warroom-muted" />
          </button>
        </div>

        {/* Templates Grid */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-warroom-accent"></div>
            </div>
          ) : dnaTemplates.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-warroom-muted">
              <Layout size={24} className="mb-2" />
              <p className="text-xs">No visual templates found</p>
              <p className="text-xs mt-1">Create templates by extracting DNA from competitor posts</p>
            </div>
          ) : (
            <div className="space-y-4">
              {dnaTemplates.map((dna) => (
                <div
                  key={dna.id}
                  className="bg-warroom-bg border border-warroom-border rounded-lg p-3 hover:border-warroom-accent/30 transition cursor-pointer"
                  onClick={() => {
                    setPreviewingId(previewingId === dna.id ? null : dna.id);
                    if (previewingId !== dna.id) {
                      fetchDNADetail(dna.id);
                    }
                  }}
                >
                  {/* Template Preview */}
                  <div className="mb-3">
                    {dna.thumbnail_url ? (
                      <img 
                        src={dna.thumbnail_url} 
                        alt={dna.name}
                        className="w-full h-32 object-cover rounded border border-warroom-border"
                      />
                    ) : (
                      renderLayoutPreview(dna)
                    )}
                  </div>

                  {/* Template Info */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <h3 className="text-xs font-semibold text-warroom-text">{dna.name}</h3>
                      <div className="flex items-center gap-1 text-[10px] text-warroom-muted">
                        <span className="px-1.5 py-0.5 bg-warroom-surface rounded font-medium">
                          {dna.aspect_ratio}
                        </span>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${
                        LAYOUT_COLORS[dna.layout_type] || LAYOUT_COLORS["full_frame"]
                      }`}>
                        {dna.layout_type.replace("_", " ")}
                      </span>
                    </div>

                    {dna.description && (
                      <p className="text-[11px] text-warroom-muted">{dna.description}</p>
                    )}
                  </div>

                  {/* Expanded Preview */}
                  {previewingId === dna.id && selectedDNA && (
                    <div className="mt-3 pt-3 border-t border-warroom-border">
                      <div className="bg-warroom-surface border border-warroom-border rounded-lg p-3 mb-3">
                        <p className="text-[10px] uppercase tracking-wider text-warroom-muted mb-2">Phone Frame Preview</p>
                        
                        {/* Phone frame mockup */}
                        <div className="mx-auto w-32 h-56 bg-black rounded-lg border-2 border-gray-600 relative overflow-hidden">
                          <div className="absolute inset-1 bg-warroom-bg rounded-md overflow-hidden">
                            {selectedDNA.layers && selectedDNA.layers.map((layer: any, index: number) => (
                              <div
                                key={layer.id || index}
                                className="absolute border border-warroom-accent/30 bg-warroom-accent/5"
                                style={{
                                  left: `${layer.position?.x || 0}%`,
                                  top: `${layer.position?.y || 0}%`,
                                  width: `${layer.position?.width || 100}%`,
                                  height: `${layer.position?.height || 100}%`,
                                }}
                              >
                                <div className="w-full h-full flex items-center justify-center text-[8px] text-warroom-accent font-medium">
                                  {layer.name || layer.type}
                                </div>
                              </div>
                            ))}
                          </div>
                          
                          {/* Phone UI elements */}
                          <div className="absolute top-1 left-1/2 transform -translate-x-1/2 w-8 h-1 bg-gray-600 rounded-full"></div>
                          <div className="absolute bottom-1 left-1/2 transform -translate-x-1/2 w-12 h-1 bg-gray-600 rounded-full"></div>
                        </div>
                      </div>

                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectDNA(dna);
                          onClose();
                        }}
                        className="w-full py-2 bg-warroom-accent text-white text-xs rounded hover:bg-warroom-accent/80 transition flex items-center justify-center gap-1"
                      >
                        Apply Layout
                      </button>
                    </div>
                  )}

                  {/* Quick apply button when not expanded */}
                  {previewingId !== dna.id && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectDNA(dna);
                        onClose();
                      }}
                      className="w-full mt-2 py-1.5 bg-warroom-accent/10 border border-warroom-accent/30 text-warroom-accent text-xs rounded hover:bg-warroom-accent/20 transition"
                    >
                      Quick Apply
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}