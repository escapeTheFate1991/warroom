"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import {
  User, Plus, Upload, Camera, Trash2, Image, X, Eye, ChevronRight,
  CheckCircle, AlertCircle, Loader2, Sparkles, Clock, ImageOff
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
}

interface DigitalCopyImage {
  id: number;
  filename: string;
  content_type: string;
  image_type: string;
  path: string;
  uploaded_at: string;
}

interface QualityAudit {
  total_images: number;
  avg_resolution: {
    width: number;
    height: number;
  };
}

/* ── Image Component with 403 Fallback ────────────────── */
function SafeImage({ src, alt, className, fallbackIcon = User, fallbackText }: {
  src: string;
  alt: string;
  className?: string;
  fallbackIcon?: any;
  fallbackText?: string;
}) {
  const [imageError, setImageError] = useState(false);
  const [isInstagramCDN, setIsInstagramCDN] = useState(false);
  const FallbackIcon = fallbackIcon;

  useEffect(() => {
    setIsInstagramCDN(src.includes('cdninstagram.com') || src.includes('scontent-'));
    setImageError(false);
  }, [src]);

  const handleImageError = () => {
    setImageError(true);
  };

  if (imageError || (isInstagramCDN && src)) {
    return (
      <div className={`flex flex-col items-center justify-center bg-warroom-bg text-warroom-muted ${className}`}>
        <ImageOff size={24} className="mb-1" />
        <span className="text-xs text-center">
          {isInstagramCDN ? "Instagram link expired" : (fallbackText || "Image unavailable")}
        </span>
      </div>
    );
  }

  return (
    <img 
      src={src} 
      alt={alt} 
      className={className}
      onError={handleImageError}
    />
  );
}

/* ── Guidelines Examples ───────────────────────────────── */
const GOOD_EXAMPLES = [
  "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&h=200&fit=crop&crop=face",
  "https://images.unsplash.com/photo-1494790108755-2616b612b494?w=200&h=200&fit=crop&crop=face",
  "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=200&h=200&fit=crop&crop=face",
  "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=200&h=200&fit=crop&crop=face"
];

const BAD_EXAMPLES = [
  "https://images.unsplash.com/photo-1511632765486-a01980e01a18?w=200&h=200&fit=crop", // group
  "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=200&h=200&fit=crop&crop=face", // sunglasses
  "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=200&h=200&fit=crop", // heavily filtered
  "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&h=200&fit=crop&crop=face" // duplicate of first good one
];

export default function DigitalCopiesPanel() {
  // Main state
  const [copies, setCopies] = useState<DigitalCopy[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<"list" | "create">("list");
  
  // Creation state
  const [characterName, setCharacterName] = useState("");
  const [selectedModel, setSelectedModel] = useState("veo-3.1");
  const [uploadedImages, setUploadedImages] = useState<DigitalCopyImage[]>([]);
  const [uploading, setUploading] = useState(false);
  const [qualityAudit, setQualityAudit] = useState<QualityAudit | null>(null);
  const [currentCopyId, setCurrentCopyId] = useState<number | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── API Functions ──────────────────────────────────────
  const fetchCopies = useCallback(async () => {
    try {
      setLoading(true);
      const response = await authFetch(`${API}/api/digital-copies`);
      if (response.ok) {
        const data = await response.json();
        setCopies(data.digital_copies || []);
      }
    } catch (error) {
      console.error("Failed to fetch digital copies:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  const createDigitalCopy = async (name: string, baseModel: string) => {
    try {
      const response = await authFetch(`${API}/api/digital-copies`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name,
          base_model: baseModel
        })
      });

      if (response.ok) {
        const data = await response.json();
        setCurrentCopyId(data.id);
        await fetchCopies();
        return data.id;
      } else {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to create digital copy");
      }
    } catch (error) {
      console.error("Error creating digital copy:", error);
      alert(error instanceof Error ? error.message : "Failed to create digital copy");
      return null;
    }
  };

  const uploadImage = async (file: File) => {
    if (!currentCopyId) {
      // Auto-create the digital copy if it doesn't exist
      const copyId = await createDigitalCopy(characterName, selectedModel);
      if (!copyId) return;
      setCurrentCopyId(copyId);
    }

    const copyId = currentCopyId || await createDigitalCopy(characterName, selectedModel);
    if (!copyId) return;

    try {
      setUploading(true);
      const formData = new FormData();
      formData.append("file", file);
      formData.append("image_type", "reference");

      const response = await authFetch(`${API}/api/digital-copies/${copyId}/images`, {
        method: "POST",
        body: formData
      });

      if (response.ok) {
        const data = await response.json();
        setUploadedImages(prev => [...prev, data]);
        
        // Update quality audit
        await fetchQualityAudit(copyId);
        await fetchCopies();
      } else {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to upload image");
      }
    } catch (error) {
      console.error("Error uploading image:", error);
      alert(error instanceof Error ? error.message : "Failed to upload image");
    } finally {
      setUploading(false);
    }
  };

  const deleteImage = async (imageId: number) => {
    if (!currentCopyId) return;

    try {
      const response = await authFetch(`${API}/api/digital-copies/${currentCopyId}/images/${imageId}`, {
        method: "DELETE"
      });

      if (response.ok) {
        setUploadedImages(prev => prev.filter(img => img.id !== imageId));
        await fetchQualityAudit(currentCopyId);
        await fetchCopies();
      }
    } catch (error) {
      console.error("Error deleting image:", error);
      alert("Failed to delete image");
    }
  };

  const deleteCopy = async (copyId: number) => {
    if (!confirm("Are you sure you want to delete this character? This action cannot be undone.")) {
      return;
    }

    try {
      const response = await authFetch(`${API}/api/digital-copies/${copyId}`, {
        method: "DELETE"
      });

      if (response.ok) {
        await fetchCopies();
      } else {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to delete character");
      }
    } catch (error) {
      console.error("Error deleting character:", error);
      alert(error instanceof Error ? error.message : "Failed to delete character");
    }
  };

  const fetchQualityAudit = async (copyId: number) => {
    try {
      const response = await authFetch(`${API}/api/digital-copies/${copyId}/quality-audit`);
      if (response.ok) {
        const data = await response.json();
        setQualityAudit(data);
      }
    } catch (error) {
      console.error("Error fetching quality audit:", error);
    }
  };

  const finalizeCharacter = async () => {
    if (!currentCopyId || !characterName.trim() || uploadedImages.length < 20) return;

    try {
      // Just refresh the copies list - the character is already created
      await fetchCopies();
      
      // Reset to list view
      setView("list");
      resetCreationState();
      
      alert("Character created successfully! It will start training shortly.");
    } catch (error) {
      console.error("Error finalizing character:", error);
      alert("Failed to finalize character");
    }
  };

  // ── Helper Functions ───────────────────────────────────
  const resetCreationState = () => {
    setCharacterName("");
    setSelectedModel("veo-3.1");
    setUploadedImages([]);
    setCurrentCopyId(null);
    setQualityAudit(null);
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

  const getQualityGrade = (resolution: { width: number; height: number } | null) => {
    if (!resolution) return { grade: "Unknown", color: "text-gray-400" };
    
    const avgResolution = (resolution.width + resolution.height) / 2;
    
    if (avgResolution >= 1080) {
      return { grade: `${Math.round(avgResolution)}px Perfect`, color: "text-green-400" };
    } else if (avgResolution >= 720) {
      return { grade: `${Math.round(avgResolution)}px Good`, color: "text-yellow-400" };
    } else {
      return { grade: `${Math.round(avgResolution)}px Poor`, color: "text-red-400" };
    }
  };

  const getImageCountColor = (count: number) => {
    if (count < 20) return "text-red-400";
    if (count < 50) return "text-yellow-400";
    return "text-green-400";
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    files.forEach(file => {
      uploadImage(file);
    });
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const files = Array.from(e.dataTransfer.files);
    files.forEach(file => {
      if (file.type.startsWith('image/')) {
        uploadImage(file);
      }
    });
  };

  // ── Effects ────────────────────────────────────────────
  useEffect(() => {
    fetchCopies();
  }, [fetchCopies]);

  // Fetch quality audit when images change
  useEffect(() => {
    if (currentCopyId && uploadedImages.length > 0) {
      fetchQualityAudit(currentCopyId);
    }
  }, [currentCopyId, uploadedImages.length]);

  // ── Render Components ──────────────────────────────────
  const renderGauge = (current: number, max: number, label: string, color: string) => {
    const percentage = Math.min((current / max) * 100, 100);
    
    return (
      <div className="flex flex-col items-center">
        <div className="relative w-20 h-20">
          <svg className="w-20 h-20 transform -rotate-90" viewBox="0 0 36 36">
            <path
              d="M18 2.0845
                a 15.9155 15.9155 0 0 1 0 31.831
                a 15.9155 15.9155 0 0 1 0 -31.831"
              fill="none"
              stroke="rgb(55, 65, 81)"
              strokeWidth="2"
            />
            <path
              d="M18 2.0845
                a 15.9155 15.9155 0 0 1 0 31.831
                a 15.9155 15.9155 0 0 1 0 -31.831"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeDasharray={`${percentage}, 100`}
              className={color}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <div className="text-lg font-bold text-warroom-text">{current}</div>
            <div className="text-xs text-warroom-muted">/ {max}</div>
          </div>
        </div>
        <div className="text-xs text-warroom-muted mt-2 text-center">{label}</div>
      </div>
    );
  };

  // ── Main Render ────────────────────────────────────────
  if (view === "create") {
    const qualityGrade = getQualityGrade(qualityAudit?.avg_resolution || null);
    const canCreate = characterName.trim().length > 0 && uploadedImages.length >= 20;

    return (
      <div className="h-full flex flex-col bg-warroom-bg">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-warroom-border">
          <div>
            <button 
              onClick={() => { setView("list"); resetCreationState(); }}
              className="flex items-center gap-2 text-warroom-muted hover:text-warroom-text mb-2"
            >
              <ChevronRight size={16} className="rotate-180" />
              Back to Characters
            </button>
            <h1 className="text-xl font-bold text-warroom-text">Create New Character</h1>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-7xl mx-auto p-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              {/* Left: Photo Grid */}
              <div className="lg:col-span-2">
                <h3 className="text-lg font-semibold text-warroom-text mb-4">Upload Photos</h3>
                
                <div 
                  className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-3 mb-6"
                  onDragOver={handleDragOver}
                  onDrop={handleDrop}
                >
                  {/* Upload Button as First Tile */}
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploading}
                    className="aspect-square border-2 border-dashed border-warroom-border rounded-xl flex flex-col items-center justify-center hover:border-warroom-accent/50 transition bg-warroom-surface/50"
                  >
                    {uploading ? (
                      <Loader2 size={20} className="text-warroom-accent animate-spin mb-1" />
                    ) : (
                      <Plus size={20} className="text-warroom-muted mb-1" />
                    )}
                    <span className="text-xs text-warroom-muted text-center">
                      {uploading ? "Uploading..." : "Upload more"}
                    </span>
                  </button>

                  {/* Uploaded Images */}
                  {uploadedImages.map(image => (
                    <div key={image.id} className="relative group">
                      <div className="aspect-square bg-warroom-bg rounded-xl overflow-hidden border border-warroom-border">
                        <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-warroom-accent/10 to-warroom-accent/5">
                          <Image size={16} className="text-warroom-muted" />
                        </div>
                      </div>
                      <button
                        onClick={() => deleteImage(image.id)}
                        className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition shadow-lg"
                      >
                        <X size={12} className="text-white" />
                      </button>
                    </div>
                  ))}
                </div>

                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept="image/*"
                  onChange={handleFileUpload}
                  className="hidden"
                />

                {/* Drop Zone Instructions */}
                {uploadedImages.length === 0 && (
                  <div className="border-2 border-dashed border-warroom-border rounded-xl p-8 text-center bg-warroom-surface/30">
                    <Upload size={32} className="text-warroom-muted mx-auto mb-4" />
                    <h4 className="text-lg font-medium text-warroom-text mb-2">
                      Drag and drop images here
                    </h4>
                    <p className="text-sm text-warroom-muted">
                      or click the + button above to select files
                    </p>
                  </div>
                )}
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
                    className="w-full px-4 py-3 bg-warroom-surface border border-warroom-border rounded-xl text-warroom-text focus:outline-none focus:border-warroom-accent"
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
                    className="w-full px-4 py-3 bg-warroom-surface border border-warroom-border rounded-xl text-warroom-text focus:outline-none focus:border-warroom-accent"
                  >
                    <option value="veo-3.1">Veo 3.1 - High Quality</option>
                    <option value="nano-banana">Nano Banana - Fast</option>
                  </select>
                </div>

                {/* Image Count Gauge */}
                <div>
                  <h4 className="text-sm font-medium text-warroom-text mb-4">Number of Images</h4>
                  {renderGauge(uploadedImages.length, 80, "Photos", getImageCountColor(uploadedImages.length))}
                  <p className="text-xs text-center text-warroom-muted mt-2">
                    Minimum 20, best results with 50+
                  </p>
                </div>

                {/* Quality Gauge */}
                <div>
                  <h4 className="text-sm font-medium text-warroom-text mb-4">Quality</h4>
                  <div className="text-center">
                    <div className={`text-lg font-semibold ${qualityGrade.color}`}>
                      {qualityGrade.grade}
                    </div>
                    <p className="text-xs text-warroom-muted mt-2">
                      Based on average resolution
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Guidelines Section */}
          <div className="border-t border-warroom-border bg-warroom-surface/30 p-6">
            <div className="max-w-7xl mx-auto">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Good Examples */}
                <div>
                  <h4 className="text-sm font-semibold text-green-400 mb-4 flex items-center gap-2">
                    <CheckCircle size={16} />
                    ✅ 20+ photos recommended: one person, clear face, multiple angles.
                  </h4>
                  <div className="grid grid-cols-4 gap-3">
                    {GOOD_EXAMPLES.map((src, index) => (
                      <div key={index} className="aspect-square rounded-lg overflow-hidden border-2 border-green-400/30">
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
                  <h4 className="text-sm font-semibold text-red-400 mb-4 flex items-center gap-2">
                    <X size={16} />
                    ❌ Avoid: duplicates, group shots, filters, face coverings (masks/sunglasses).
                  </h4>
                  <div className="grid grid-cols-4 gap-3">
                    {BAD_EXAMPLES.map((src, index) => (
                      <div key={index} className="aspect-square rounded-lg overflow-hidden border-2 border-red-400/30 relative">
                        <SafeImage 
                          src={src} 
                          alt={`Bad example ${index + 1}`} 
                          className="w-full h-full object-cover"
                        />
                        <div className="absolute inset-0 bg-red-500/20 flex items-center justify-center">
                          <X size={20} className="text-red-400" />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Action Bar */}
        <div className="border-t border-warroom-border p-6 bg-warroom-bg">
          <div className="max-w-7xl mx-auto flex justify-end">
            <button
              onClick={finalizeCharacter}
              disabled={!canCreate}
              className="px-8 py-4 bg-warroom-accent text-white text-lg font-semibold rounded-xl hover:bg-warroom-accent/80 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-lg"
            >
              Create Character
            </button>
          </div>
        </div>
      </div>
    );
  }

  // List View
  return (
    <div className="h-full flex flex-col bg-warroom-bg">
      {/* Header */}
      <div className="flex items-center justify-between p-6 border-b border-warroom-border">
        <div>
          <h1 className="text-xl font-bold text-warroom-text">Digital Copies</h1>
          <p className="text-sm text-warroom-muted mt-1">AI Characters for Video Generation</p>
        </div>
        <button
          onClick={() => setView("create")}
          className="flex items-center gap-2 px-4 py-2 bg-warroom-accent text-white text-sm font-medium rounded-lg hover:bg-warroom-accent/80 transition"
        >
          <Sparkles size={16} />
          Create Character ✨
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {loading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="animate-spin text-warroom-accent" size={32} />
          </div>
        ) : copies.length === 0 ? (
          // Landing Page
          <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
            <div className="max-w-2xl">
              <h2 className="text-4xl font-bold text-warroom-text mb-6">
                MAKE YOUR OWN CHARACTER
              </h2>
              
              {/* Sample Images Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                {GOOD_EXAMPLES.map((src, index) => (
                  <div key={index} className="aspect-square rounded-xl overflow-hidden shadow-lg">
                    <SafeImage 
                      src={src} 
                      alt={`Sample character ${index + 1}`} 
                      className="w-full h-full object-cover"
                    />
                  </div>
                ))}
              </div>

              <p className="text-lg text-warroom-muted mb-8 leading-relaxed">
                Upload photos of yourself from multiple angles to create a digital avatar that can star in unlimited AI-generated videos.
              </p>

              <button
                onClick={() => setView("create")}
                className="inline-flex items-center gap-3 px-8 py-4 bg-warroom-accent text-white text-lg font-semibold rounded-xl hover:bg-warroom-accent/80 transition shadow-lg"
              >
                <Sparkles size={20} />
                Create character
              </button>

              {/* Guidelines Preview */}
              <div className="mt-12 grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Good Examples */}
                <div>
                  <h4 className="text-sm font-semibold text-green-400 mb-4 flex items-center gap-2">
                    <CheckCircle size={16} />
                    Good: one person, clear face, multiple angles
                  </h4>
                  <div className="grid grid-cols-4 gap-2">
                    {GOOD_EXAMPLES.map((src, index) => (
                      <div key={index} className="aspect-square rounded-lg overflow-hidden border-2 border-green-400/30">
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
                  <h4 className="text-sm font-semibold text-red-400 mb-4 flex items-center gap-2">
                    <X size={16} />
                    Bad: duplicates, group shots, filters, face coverings
                  </h4>
                  <div className="grid grid-cols-4 gap-2">
                    {BAD_EXAMPLES.map((src, index) => (
                      <div key={index} className="aspect-square rounded-lg overflow-hidden border-2 border-red-400/30 relative">
                        <SafeImage 
                          src={src} 
                          alt={`Bad example ${index + 1}`} 
                          className="w-full h-full object-cover"
                        />
                        <div className="absolute inset-0 bg-red-500/20 flex items-center justify-center">
                          <X size={16} className="text-red-400" />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          // Character Grid
          <div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {copies.map(copy => (
                <div key={copy.id} className="bg-warroom-surface border border-warroom-border rounded-xl overflow-hidden hover:border-warroom-accent/30 transition group">
                  {/* Thumbnail */}
                  <div className="aspect-square bg-warroom-bg flex items-center justify-center">
                    {copy.thumbnail_url ? (
                      <SafeImage 
                        src={copy.thumbnail_url} 
                        alt={copy.name} 
                        className="w-full h-full object-cover"
                        fallbackText="No thumbnail"
                      />
                    ) : (
                      <div className="flex flex-col items-center text-warroom-muted">
                        <User size={48} />
                        <span className="text-xs mt-2">No thumbnail</span>
                      </div>
                    )}
                  </div>

                  {/* Info */}
                  <div className="p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-semibold text-warroom-text truncate">{copy.name}</h3>
                      <span className={`px-2 py-1 text-xs rounded-full font-medium ${getStatusBadge(copy.status)}`}>
                        {copy.status}
                      </span>
                    </div>
                    
                    <div className="flex items-center justify-between text-sm text-warroom-muted">
                      <span className="flex items-center gap-1">
                        <Camera size={14} />
                        {copy.image_count || 0} images
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock size={14} />
                        {new Date(copy.created_at).toLocaleDateString()}
                      </span>
                    </div>

                    {copy.description && (
                      <p className="text-xs text-warroom-muted mt-2 line-clamp-2">{copy.description}</p>
                    )}

                    {/* Delete Button */}
                    <button
                      onClick={() => deleteCopy(copy.id)}
                      className="w-full mt-3 px-3 py-2 text-xs text-red-400 border border-red-400/30 rounded-lg hover:bg-red-400/10 transition opacity-0 group-hover:opacity-100"
                    >
                      <Trash2 size={12} className="inline mr-1" />
                      Delete Character
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}