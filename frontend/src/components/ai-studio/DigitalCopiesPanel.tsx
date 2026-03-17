"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import {
  User, Plus, Upload, Camera, Trash2, X, ChevronLeft, Loader2, Sparkles,
  Clock, ImageOff, CheckCircle, MoreHorizontal, Play, Settings, 
  ChevronDown, ChevronUp, RotateCcw
} from "lucide-react";
import { API, authFetch } from "@/lib/api";

/* ── Types ─────────────────────────────────────────────── */
interface DigitalCopy {
  id: number;
  name: string;
  description?: string;
  status: "draft" | "training" | "ready" | "failed";
  created_at: string;
  base_model: string;
  images?: DigitalCopyImage[];
  image_count?: number;
  thumbnail_url?: string;
  reference_sheet_url?: string;
  character_dna?: any;
}

interface DigitalCopyImage {
  id: number;
  filename: string;
  content_type: string;
  image_type: string;
  path: string;
  image_url: string;
  uploaded_at: string;
}

interface LocalImage {
  file: File;
  preview: string;
}

interface Toast {
  id: string;
  message: string;
  type: "success" | "error" | "info";
}

/* ── Toast Component ───────────────────────────────────── */
function ToastContainer({ toasts, onRemove }: { toasts: Toast[], onRemove: (id: string) => void }) {
  return (
    <div className="fixed top-4 right-4 z-50 space-y-2">
      {toasts.map(toast => (
        <div 
          key={toast.id}
          className={`px-4 py-3 rounded-lg shadow-lg border max-w-sm animate-in slide-in-from-right duration-300 ${
            toast.type === "success" ? "bg-green-500/20 text-green-400 border-green-400/30" :
            toast.type === "error" ? "bg-red-500/20 text-red-400 border-red-400/30" :
            "bg-blue-500/20 text-blue-400 border-blue-400/30"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-sm">{toast.message}</span>
            <button 
              onClick={() => onRemove(toast.id)}
              className="ml-2 opacity-70 hover:opacity-100"
            >
              <X size={14} />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ── Safe Image Component with Fallback ───────────────── */
function SafeImage({ src, alt, className, fallbackIcon = User, fallbackText }: {
  src: string;
  alt: string;
  className?: string;
  fallbackIcon?: any;
  fallbackText?: string;
}) {
  const [imageError, setImageError] = useState(false);
  const FallbackIcon = fallbackIcon;

  useEffect(() => {
    setImageError(false);
  }, [src]);

  if (imageError) {
    return (
      <div className={`flex flex-col items-center justify-center bg-warroom-bg text-warroom-muted ${className}`}>
        <FallbackIcon size={24} className="mb-1" />
        <span className="text-xs text-center">{fallbackText || "Image unavailable"}</span>
      </div>
    );
  }

  return (
    <img 
      src={src} 
      alt={alt} 
      className={className}
      onError={() => setImageError(true)}
    />
  );
}

/* ── Guidelines Examples ───────────────────────────────── */
const GOOD_EXAMPLES = [
  "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&h=200&fit=crop&crop=face",
  "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=200&h=200&fit=crop&crop=face",
  "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=200&h=200&fit=crop&crop=face",
  "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=200&h=200&fit=crop&crop=face"
];

const BAD_EXAMPLES = [
  "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?w=200&h=200&fit=crop",
  "https://images.unsplash.com/photo-1511895426328-dc8714191300?w=200&h=200&fit=crop",
  "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=200&h=200&fit=crop",
  "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&h=200&fit=crop"
];

export default function DigitalCopiesPanel() {
  // Main state
  const [copies, setCopies] = useState<DigitalCopy[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<"list" | "create" | "generate">("list");
  const [selectedCopy, setSelectedCopy] = useState<DigitalCopy | null>(null);
  
  // Create view state
  const [characterName, setCharacterName] = useState("");
  const [selectedModel, setSelectedModel] = useState("nano-banana-2");
  const [localImages, setLocalImages] = useState<LocalImage[]>([]);
  const [creating, setCreating] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<{ current: number; total: number } | null>(null);
  
  // Generate view state
  const [scenePrompt, setScenePrompt] = useState("");
  const [styleOverride, setStyleOverride] = useState("");
  const [generatedImageUrl, setGeneratedImageUrl] = useState<string>("");
  const [videoGenerating, setVideoGenerating] = useState(false);
  const [videoDuration, setVideoDuration] = useState(4);
  const [videoAspectRatio, setVideoAspectRatio] = useState("16:9");
  const [activeTab, setActiveTab] = useState("Overview");
  const [dnaExpanded, setDnaExpanded] = useState(false);
  
  // Toast state
  const [toasts, setToasts] = useState<Toast[]>([]);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Toast Functions ────────────────────────────────────
  const showToast = (message: string, type: "success" | "error" | "info" = "info") => {
    const id = Math.random().toString(36).substring(2);
    setToasts(prev => [...prev, { id, message, type }]);
    
    setTimeout(() => {
      removeToast(id);
    }, 5000);
  };

  const removeToast = (id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  };

  // ── API Functions ──────────────────────────────────────
  const fetchCopies = useCallback(async () => {
    try {
      setLoading(true);
      const response = await authFetch(`${API}/api/digital-copies`);
      if (response.ok) {
        const data = await response.json();
        setCopies(Array.isArray(data) ? data : data.digital_copies || []);
      }
    } catch (error) {
      console.error("Failed to fetch digital copies:", error);
      showToast("Failed to load characters", "error");
    } finally {
      setLoading(false);
    }
  }, []);

  const createDigitalCopy = async () => {
    if (!characterName.trim() || localImages.length < 20) return;

    try {
      setCreating(true);
      setUploadProgress({ current: 0, total: localImages.length + 2 });

      // Step 1: Create the digital copy
      const createResponse = await authFetch(`${API}/api/digital-copies`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: characterName.trim(),
          base_model: selectedModel
        })
      });

      if (!createResponse.ok) {
        const errData = await createResponse.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to create digital copy");
      }

      const copyData = await createResponse.json();
      setUploadProgress({ current: 1, total: localImages.length + 2 });

      // Step 2: Upload all images sequentially
      for (let i = 0; i < localImages.length; i++) {
        const localImage = localImages[i];
        
        const formData = new FormData();
        formData.append("file", localImage.file);
        formData.append("image_type", "reference");

        const uploadResponse = await authFetch(`${API}/api/digital-copies/${copyData.id}/images`, {
          method: "POST",
          body: formData
        });

        if (!uploadResponse.ok) {
          console.error(`Failed to upload image ${i + 1}`);
        }
        
        setUploadProgress({ current: i + 2, total: localImages.length + 2 });
      }

      // Step 3: Generate reference sheet
      const generateResponse = await authFetch(`${API}/api/digital-copies/${copyData.id}/generate-reference-sheet`, {
        method: "POST"
      });

      if (generateResponse.ok) {
        showToast("Character created and DNA generated successfully!", "success");
      } else {
        showToast("Character created, but DNA generation failed", "error");
      }

      // Cleanup and navigate
      resetCreateState();
      await fetchCopies();
      setView("list");

    } catch (error) {
      console.error("Error creating character:", error);
      showToast(error instanceof Error ? error.message : "Failed to create character", "error");
    } finally {
      setCreating(false);
      setUploadProgress(null);
    }
  };

  const deleteDigitalCopy = async (id: number) => {
    try {
      const response = await authFetch(`${API}/api/digital-copies/${id}`, {
        method: "DELETE"
      });

      if (response.ok) {
        await fetchCopies();
        showToast("Character deleted successfully", "success");
      } else {
        throw new Error("Failed to delete character");
      }
    } catch (error) {
      showToast("Failed to delete character", "error");
    }
  };

  const generateReferenceSheet = async () => {
    if (!selectedCopy) return;

    try {
      const response = await authFetch(`${API}/api/digital-copies/${selectedCopy.id}/generate-reference-sheet`, {
        method: "POST"
      });

      if (response.ok) {
        const result = await response.json();
        setSelectedCopy(prev => prev ? { ...prev, reference_sheet_url: result.reference_sheet_url, character_dna: result.character_dna } : null);
        showToast("Reference sheet regenerated successfully!", "success");
      } else {
        throw new Error("Failed to regenerate reference sheet");
      }
    } catch (error) {
      showToast("Failed to regenerate reference sheet", "error");
    }
  };

  const generateScene = async () => {
    if (!selectedCopy || !scenePrompt.trim()) return;

    try {
      const response = await authFetch(`${API}/api/digital-copies/${selectedCopy.id}/generate-scene`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: scenePrompt.trim(),
          style_override: styleOverride.trim() || undefined
        })
      });

      if (response.ok) {
        const result = await response.json();
        setGeneratedImageUrl(result.image_url);
        showToast("Scene generated successfully!", "success");
      } else {
        throw new Error("Failed to generate scene");
      }
    } catch (error) {
      showToast("Failed to generate scene", "error");
    }
  };

  // ── Helper Functions ───────────────────────────────────
  const resetCreateState = () => {
    setCharacterName("");
    setSelectedModel("nano-banana-2");
    localImages.forEach(img => URL.revokeObjectURL(img.preview));
    setLocalImages([]);
  };

  const getStatusBadge = (status: DigitalCopy["status"]) => {
    switch (status) {
      case "ready":
        return "bg-green-500/20 text-green-400";
      case "training":
        return "bg-yellow-500/20 text-yellow-400 animate-pulse";
      case "failed":
        return "bg-red-500/20 text-red-400";
      default:
        return "bg-gray-500/20 text-gray-400";
    }
  };

  const getImageCountColor = (count: number) => {
    if (count < 20) return "text-red-400";
    if (count < 50) return "text-yellow-400";
    return "text-green-400";
  };

  const getImageCountBg = (count: number) => {
    const percentage = Math.min(count / 80 * 100, 100);
    if (count < 20) return `linear-gradient(to right, #ef4444 ${percentage}%, #374151 ${percentage}%)`;
    if (count < 50) return `linear-gradient(to right, #eab308 ${percentage}%, #374151 ${percentage}%)`;
    return `linear-gradient(to right, #22c55e ${percentage}%, #374151 ${percentage}%)`;
  };

  const addLocalImages = (files: File[]) => {
    files.forEach(file => {
      if (!file.type.startsWith('image/')) {
        showToast(`${file.name} is not a valid image file`, "error");
        return;
      }

      const preview = URL.createObjectURL(file);
      setLocalImages(prev => [...prev, { file, preview }]);
    });
  };

  const removeLocalImage = (index: number) => {
    setLocalImages(prev => {
      URL.revokeObjectURL(prev[index].preview);
      return prev.filter((_, i) => i !== index);
    });
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    addLocalImages(files);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const files = Array.from(e.dataTransfer.files);
    addLocalImages(files);
  };

  const getAverageResolution = () => {
    // This would need to be calculated from actual image dimensions
    // For now, return a placeholder
    return "1080x1080";
  };

  // ── Effects ────────────────────────────────────────────
  useEffect(() => {
    fetchCopies();
  }, [fetchCopies]);

  // ── View 1: Character List ─────────────────────────────
  if (view === "list") {
    return (
      <div className="h-full flex flex-col bg-warroom-bg">
        <ToastContainer toasts={toasts} onRemove={removeToast} />
        
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-warroom-border">
          <h1 className="text-xl font-bold text-warroom-text">Digital Copies</h1>
          <button
            onClick={() => setView("create")}
            className="flex items-center gap-2 px-4 py-2 bg-warroom-accent text-white font-medium rounded-lg hover:bg-warroom-accent/80 transition"
          >
            <Sparkles size={16} />
            Create Character
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex justify-center py-16">
              <Loader2 className="animate-spin text-warroom-accent" size={32} />
            </div>
          ) : copies.length === 0 ? (
            <div className="text-center py-16 text-warroom-muted">
              <User size={64} className="mx-auto mb-4 opacity-50" />
              <h3 className="text-lg font-medium mb-2">No characters yet</h3>
              <p className="text-sm">Create your first digital character to get started</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {copies.map(copy => (
                <div 
                  key={copy.id} 
                  className="bg-warroom-surface border border-warroom-border rounded-xl overflow-hidden group relative cursor-pointer hover:border-warroom-accent/50 transition"
                  onClick={() => {
                    setSelectedCopy(copy);
                    setView("generate");
                  }}
                >
                  {/* Thumbnail */}
                  <div className="aspect-square bg-warroom-bg relative">
                    {copy.images && copy.images.length > 0 ? (
                      <SafeImage 
                        src={copy.images[0].image_url} 
                        alt={copy.name} 
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <User size={48} className="text-warroom-muted" />
                      </div>
                    )}
                    
                    {/* Hover overlay with Generate button */}
                    <div className="absolute inset-0 bg-black/70 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                      <button className="flex items-center gap-2 px-4 py-2 bg-warroom-accent text-white font-medium rounded-lg">
                        <Sparkles size={16} />
                        Generate
                      </button>
                    </div>

                    {/* Three-dot menu */}
                    <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <div className="relative group/menu">
                        <button 
                          className="w-8 h-8 bg-black/50 rounded-full flex items-center justify-center text-white hover:bg-black/70 transition"
                          onClick={(e) => {
                            e.stopPropagation();
                          }}
                        >
                          <MoreHorizontal size={16} />
                        </button>
                        <div className="absolute right-0 top-full mt-1 w-32 bg-warroom-surface border border-warroom-border rounded-lg shadow-lg opacity-0 invisible group-hover/menu:opacity-100 group-hover/menu:visible transition-all z-10">
                          <button 
                            className="w-full px-3 py-2 text-left text-sm text-red-400 hover:bg-warroom-bg rounded-lg"
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteDigitalCopy(copy.id);
                            }}
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Info */}
                  <div className="p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-semibold text-warroom-text truncate">{copy.name}</h3>
                      <span className={`px-2 py-1 text-xs rounded-full font-medium ${getStatusBadge(copy.status)}`}>
                        {copy.status}
                      </span>
                    </div>
                    
                    <div className="text-sm text-warroom-muted">
                      <span>{copy.image_count || copy.images?.length || 0} photos</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  // ── View 2: Create Character ───────────────────────────
  if (view === "create") {
    const canCreate = characterName.trim().length > 0 && localImages.length >= 20;

    return (
      <div className="h-full flex flex-col bg-warroom-bg">
        <ToastContainer toasts={toasts} onRemove={removeToast} />
        
        {/* Upload Progress Overlay */}
        {creating && uploadProgress && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-warroom-surface border border-warroom-border rounded-xl p-6 max-w-md w-full mx-4">
              <div className="text-center">
                <Loader2 className="w-8 h-8 animate-spin text-warroom-accent mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-warroom-text mb-2">Creating Character</h3>
                <div className="text-sm text-warroom-muted mb-3">
                  {uploadProgress.current} / {uploadProgress.total}
                </div>
                <div className="w-full bg-warroom-bg rounded-full h-2">
                  <div 
                    className="bg-warroom-accent h-2 rounded-full transition-all duration-300"
                    style={{ width: `${(uploadProgress.current / uploadProgress.total) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Header */}
        <div className="p-6 border-b border-warroom-border">
          <button 
            onClick={() => {
              setView("list");
              resetCreateState();
            }}
            className="flex items-center gap-2 text-warroom-muted hover:text-warroom-text mb-3"
          >
            <ChevronLeft size={16} />
            Characters
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-6xl mx-auto p-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              {/* Left: Photo Upload Grid */}
              <div className="lg:col-span-2">
                <div 
                  className="min-h-96"
                  onDragOver={handleDragOver}
                  onDrop={handleDrop}
                >
                  <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 gap-3">
                    {/* Upload button as first tile */}
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      className="aspect-square border-2 border-dashed border-warroom-border rounded-lg flex flex-col items-center justify-center hover:border-warroom-accent/50 transition bg-warroom-surface/50"
                    >
                      <Plus size={16} className="text-warroom-muted" />
                    </button>

                    {/* Local images */}
                    {localImages.map((image, index) => (
                      <div key={index} className="relative group">
                        <div className="aspect-square bg-warroom-bg rounded-lg overflow-hidden">
                          <img 
                            src={image.preview}
                            alt="Upload preview"
                            className="w-full h-full object-cover"
                          />
                        </div>
                        <button
                          onClick={() => removeLocalImage(index)}
                          className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition"
                        >
                          <X size={12} className="text-white" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>

                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept="image/*"
                  onChange={handleFileUpload}
                  className="hidden"
                />
              </div>

              {/* Right: Settings Sidebar */}
              <div className="space-y-6">
                {/* Character Name */}
                <div>
                  <label className="block text-sm font-medium text-warroom-text mb-2">
                    Character Name
                  </label>
                  <input
                    type="text"
                    value={characterName}
                    onChange={(e) => setCharacterName(e.target.value)}
                    placeholder="Enter character name"
                    className="w-full px-3 py-2 bg-warroom-surface border border-warroom-border rounded-lg text-warroom-text focus:outline-none focus:border-warroom-accent"
                  />
                </div>

                {/* Model Selection */}
                <div>
                  <label className="block text-sm font-medium text-warroom-text mb-2">
                    Model
                  </label>
                  <select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="w-full px-3 py-2 bg-warroom-surface border border-warroom-border rounded-lg text-warroom-text focus:outline-none focus:border-warroom-accent"
                  >
                    <option value="nano-banana-2">Nano Banana 2</option>
                    <option value="veo-3.1">Veo 3.1</option>
                  </select>
                </div>

                {/* Image Count */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-warroom-text">Images</span>
                    <span className={`text-sm font-medium ${getImageCountColor(localImages.length)}`}>
                      {localImages.length}/80
                    </span>
                  </div>
                  <div className="w-full h-2 bg-warroom-bg rounded-full overflow-hidden">
                    <div 
                      className="h-full transition-all duration-300"
                      style={{ 
                        width: `${Math.min(localImages.length / 80 * 100, 100)}%`,
                        background: getImageCountBg(localImages.length)
                      }}
                    />
                  </div>
                </div>

                {/* Resolution */}
                <div>
                  <span className="text-sm font-medium text-warroom-text">Resolution</span>
                  <p className="text-sm text-warroom-muted mt-1">{getAverageResolution()}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Guidelines */}
          <div className="border-t border-warroom-border bg-warroom-surface/30 p-6">
            <div className="max-w-6xl mx-auto">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Good Examples */}
                <div>
                  <h4 className="text-sm font-semibold text-green-400 mb-4">
                    ✅ Good: clear face, one person, various angles
                  </h4>
                  <div className="grid grid-cols-4 gap-3">
                    {GOOD_EXAMPLES.map((src, index) => (
                      <div key={index} className="aspect-square rounded-lg overflow-hidden">
                        <SafeImage 
                          src={src} 
                          alt={`Good example ${index + 1}`} 
                          className="w-full h-full object-cover"
                        />
                      </div>
                    ))}
                  </div>
                </div>

                {/* Bad Examples */}
                <div>
                  <h4 className="text-sm font-semibold text-red-400 mb-4">
                    ❌ Bad: group shots, filters, face coverings
                  </h4>
                  <div className="grid grid-cols-4 gap-3">
                    {BAD_EXAMPLES.map((src, index) => (
                      <div key={index} className="aspect-square rounded-lg overflow-hidden relative">
                        <SafeImage 
                          src={src} 
                          alt={`Bad example ${index + 1}`} 
                          className="w-full h-full object-cover"
                        />
                        <div className="absolute inset-0 bg-red-500/20" />
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Create Button */}
          <div className="border-t border-warroom-border p-6 bg-warroom-bg">
            <div className="max-w-6xl mx-auto flex justify-end">
              <button
                onClick={createDigitalCopy}
                disabled={!canCreate || creating}
                className="px-8 py-3 bg-warroom-accent text-white font-semibold rounded-lg hover:bg-warroom-accent/80 disabled:opacity-50 disabled:cursor-not-allowed transition"
              >
                {creating ? "Creating..." : "Create"}
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ── View 3: Generate ───────────────────────────────────
  return (
    <div className="h-full flex flex-col bg-warroom-bg">
      <ToastContainer toasts={toasts} onRemove={removeToast} />
      
      {/* Header */}
      <div className="p-6 border-b border-warroom-border">
        <button 
          onClick={() => setView("list")}
          className="flex items-center gap-2 text-warroom-muted hover:text-warroom-text"
        >
          <ChevronLeft size={16} />
          Characters
        </button>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex">
        {/* Left: Canvas/Preview Area (70%) */}
        <div className="flex-1 flex flex-col bg-warroom-surface/30">
          <div className="flex-1 flex items-center justify-center p-6">
            {generatedImageUrl ? (
              <div className="max-w-full max-h-full">
                <img 
                  src={generatedImageUrl} 
                  alt="Generated scene" 
                  className="max-w-full max-h-full object-contain rounded-lg"
                />
              </div>
            ) : selectedCopy?.reference_sheet_url ? (
              <div className="max-w-full max-h-full">
                <img 
                  src={selectedCopy.reference_sheet_url} 
                  alt="Reference sheet" 
                  className="max-w-full max-h-full object-contain rounded-lg"
                />
              </div>
            ) : (
              <div className="grid grid-cols-4 gap-3 max-w-2xl">
                {selectedCopy?.images?.slice(0, 8).map(image => (
                  <div key={image.id} className="aspect-square rounded-lg overflow-hidden">
                    <SafeImage 
                      src={image.image_url} 
                      alt={`${selectedCopy.name} photo`}
                      className="w-full h-full object-cover"
                    />
                  </div>
                )) || (
                  <div className="col-span-4 text-center py-8">
                    <User size={48} className="mx-auto mb-2 text-warroom-muted" />
                    <p className="text-warroom-muted">No images available</p>
                  </div>
                )}
              </div>
            )}
          </div>

          {videoGenerating && (
            <div className="p-4 border-t border-warroom-border">
              <div className="flex items-center gap-3">
                <Loader2 size={16} className="animate-spin" />
                <span className="text-sm text-warroom-muted">Generating video...</span>
                <div className="flex-1 bg-warroom-bg rounded-full h-2">
                  <div className="bg-warroom-accent h-2 rounded-full w-1/3 animate-pulse" />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right: Controls Panel (30%) */}
        <div className="w-80 bg-warroom-surface border-l border-warroom-border flex flex-col">
          <div className="flex-1 overflow-y-auto">
            {/* Character Info */}
            <div className="p-4 border-b border-warroom-border">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-12 h-12 rounded-lg overflow-hidden bg-warroom-bg">
                  {selectedCopy?.images?.[0] ? (
                    <SafeImage 
                      src={selectedCopy.images[0].image_url}
                      alt={selectedCopy.name}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <User size={20} className="text-warroom-muted" />
                    </div>
                  )}
                </div>
                <div>
                  <h3 className="font-semibold text-warroom-text">{selectedCopy?.name}</h3>
                  <p className="text-sm text-warroom-muted">
                    {selectedCopy?.image_count || selectedCopy?.images?.length || 0} photos
                  </p>
                </div>
              </div>

              {/* Character DNA */}
              {selectedCopy?.character_dna && (
                <div className="mb-4">
                  <button
                    onClick={() => setDnaExpanded(!dnaExpanded)}
                    className="flex items-center justify-between w-full text-left text-sm font-medium text-warroom-text"
                  >
                    Character DNA
                    {dnaExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                  </button>
                  {dnaExpanded && (
                    <div className="mt-2 p-3 bg-warroom-bg rounded-lg text-xs text-warroom-muted overflow-x-auto">
                      <pre>{JSON.stringify(selectedCopy.character_dna, null, 2)}</pre>
                    </div>
                  )}
                </div>
              )}

              <button
                onClick={generateReferenceSheet}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 border border-warroom-border rounded-lg text-sm text-warroom-muted hover:text-warroom-text hover:border-warroom-accent/50 transition"
              >
                <RotateCcw size={14} />
                Regenerate Reference Sheet
              </button>
            </div>

            {/* Scene Generation */}
            <div className="p-4 border-b border-warroom-border space-y-4">
              <h4 className="font-medium text-warroom-text">Scene Generation</h4>
              
              <div>
                <textarea
                  value={scenePrompt}
                  onChange={(e) => setScenePrompt(e.target.value)}
                  placeholder="Describe the scene..."
                  className="w-full px-3 py-2 bg-warroom-bg border border-warroom-border rounded-lg text-warroom-text placeholder-warroom-muted focus:outline-none focus:border-warroom-accent resize-none"
                  rows={3}
                />
              </div>

              <div>
                <input
                  type="text"
                  value={styleOverride}
                  onChange={(e) => setStyleOverride(e.target.value)}
                  placeholder="Style override (optional)"
                  className="w-full px-3 py-2 bg-warroom-bg border border-warroom-border rounded-lg text-warroom-text placeholder-warroom-muted focus:outline-none focus:border-warroom-accent"
                />
              </div>

              <button
                onClick={generateScene}
                disabled={!scenePrompt.trim()}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-warroom-accent text-white font-medium rounded-lg hover:bg-warroom-accent/80 disabled:opacity-50 disabled:cursor-not-allowed transition"
              >
                <Sparkles size={16} />
                Generate Image
              </button>
            </div>

            {/* Video Generation */}
            <div className="p-4 space-y-4">
              <h4 className="font-medium text-warroom-text">Video Generation</h4>
              
              <div>
                <label className="block text-sm text-warroom-muted mb-2">Duration</label>
                <select
                  value={videoDuration}
                  onChange={(e) => setVideoDuration(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-warroom-bg border border-warroom-border rounded-lg text-warroom-text focus:outline-none focus:border-warroom-accent"
                >
                  <option value={4}>4s</option>
                  <option value={6}>6s</option>
                  <option value={8}>8s</option>
                </select>
              </div>

              <div>
                <label className="block text-sm text-warroom-muted mb-2">Aspect Ratio</label>
                <select
                  value={videoAspectRatio}
                  onChange={(e) => setVideoAspectRatio(e.target.value)}
                  className="w-full px-3 py-2 bg-warroom-bg border border-warroom-border rounded-lg text-warroom-text focus:outline-none focus:border-warroom-accent"
                >
                  <option value="9:16">9:16 (Portrait)</option>
                  <option value="16:9">16:9 (Landscape)</option>
                  <option value="1:1">1:1 (Square)</option>
                </select>
              </div>

              <button
                disabled={!generatedImageUrl}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-warroom-accent text-white font-medium rounded-lg hover:bg-warroom-accent/80 disabled:opacity-50 disabled:cursor-not-allowed transition"
              >
                <Play size={16} />
                Generate Video
              </button>
            </div>
          </div>

          {/* Bottom Tabs */}
          <div className="border-t border-warroom-border p-4">
            <div className="grid grid-cols-3 gap-1 text-xs">
              {["Overview", "Upscale", "Enhancer", "Relight", "Inpaint", "Angles"].map(tab => (
                <button
                  key={tab}
                  className={`px-2 py-1 rounded text-center transition ${
                    activeTab === tab 
                      ? "bg-warroom-accent text-white" 
                      : "text-warroom-muted hover:text-warroom-text"
                  } ${tab !== "Overview" ? "cursor-not-allowed opacity-50" : ""}`}
                  onClick={() => tab === "Overview" && setActiveTab(tab)}
                  disabled={tab !== "Overview"}
                >
                  {tab}
                </button>
              ))}
            </div>
            {activeTab !== "Overview" && (
              <p className="text-xs text-warroom-muted text-center mt-2">Coming soon</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}