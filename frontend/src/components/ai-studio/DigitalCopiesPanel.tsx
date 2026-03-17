"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import {
  User, Plus, Upload, Camera, Trash2, Image, X, Eye, ChevronRight,
  CheckCircle, AlertCircle, Loader2, Sparkles, Target, Clock
} from "lucide-react";
import { API, authFetch } from "@/lib/api";

/* ── Types ─────────────────────────────────────────────── */
interface DigitalCopy {
  id: number;
  name: string;
  description?: string;
  status: "draft" | "training" | "ready" | "failed";
  created_at: string;
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
  target_images: number;
  quality_ok: boolean;
  angle_coverage: {
    close_up: number;
    full_body: number;
    quarter_body: number;
    profile_left: number;
    profile_right: number;
    other: number;
  };
  missing_angles: string[];
  avg_resolution: {
    width: number;
    height: number;
  };
  ready_for_training: boolean;
  recommendation: string;
}

type CreatorStep = "name" | "upload" | "audit";

/* ── Constants ──────────────────────────────────────────── */
const IMAGE_TYPES = [
  { value: "close_up", label: "Close-Up", description: "Head & shoulders" },
  { value: "full_body", label: "Full Body", description: "Head to toe" },
  { value: "quarter_body", label: "Quarter Body", description: "Waist up" },
  { value: "profile_left", label: "Profile Left", description: "Side view left" },
  { value: "profile_right", label: "Profile Right", description: "Side view right" },
  { value: "other", label: "Other", description: "Different angle" },
];

const DO_DONT_GUIDELINES = {
  do: [
    "20+ photos minimum",
    "Clear face visible",
    "Multiple angles",
    "Good lighting",
    "Various expressions",
    "High resolution",
    "Natural poses"
  ],
  dont: [
    "Sunglasses covering eyes",
    "Blurry or dark photos",
    "Group shots",
    "Heavy filters",
    "Obstructed face",
    "Same angle repeated",
    "Low resolution"
  ]
};

export default function DigitalCopiesPanel() {
  // Digital copies state
  const [copies, setCopies] = useState<DigitalCopy[]>([]);
  const [loading, setLoading] = useState(true);

  // Creator modal state
  const [showCreator, setShowCreator] = useState(false);
  const [creatorStep, setCreatorStep] = useState<CreatorStep>("name");
  const [creatorData, setCreatorData] = useState({
    name: "",
    baseModel: "veo-3.1" as "veo-3.1" | "nano-banana"
  });
  const [currentCopyId, setCurrentCopyId] = useState<number | null>(null);
  const [uploadedImages, setUploadedImages] = useState<DigitalCopyImage[]>([]);
  const [uploading, setUploading] = useState(false);
  const [qualityAudit, setQualityAudit] = useState<QualityAudit | null>(null);
  const [auditLoading, setAuditLoading] = useState(false);

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

  const createDigitalCopy = async () => {
    try {
      const response = await authFetch(`${API}/api/digital-copies`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: creatorData.name,
          base_model: creatorData.baseModel
        })
      });

      if (response.ok) {
        const data = await response.json();
        setCurrentCopyId(data.id);
        setCreatorStep("upload");
        await fetchCopies();
        return data.id;
      } else {
        throw new Error("Failed to create digital copy");
      }
    } catch (error) {
      console.error("Error creating digital copy:", error);
      alert("Failed to create digital copy");
    }
  };

  const uploadImage = async (file: File, imageType: string) => {
    if (!currentCopyId) return;

    try {
      setUploading(true);
      const formData = new FormData();
      formData.append("file", file);
      formData.append("image_type", imageType);

      const response = await authFetch(`${API}/api/digital-copies/${currentCopyId}/images`, {
        method: "POST",
        body: formData
      });

      if (response.ok) {
        const data = await response.json();
        setUploadedImages(prev => [...prev, data]);
        await fetchCopies();
      } else {
        throw new Error("Failed to upload image");
      }
    } catch (error) {
      console.error("Error uploading image:", error);
      alert("Failed to upload image");
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
        await fetchCopies();
      }
    } catch (error) {
      console.error("Error deleting image:", error);
    }
  };

  const performQualityAudit = async () => {
    if (!currentCopyId) return;

    try {
      setAuditLoading(true);
      const response = await authFetch(`${API}/api/digital-copies/${currentCopyId}/quality-audit`);
      if (response.ok) {
        const data = await response.json();
        setQualityAudit(data);
      } else {
        throw new Error("Quality audit failed");
      }
    } catch (error) {
      console.error("Error performing quality audit:", error);
      alert("Quality audit failed");
    } finally {
      setAuditLoading(false);
    }
  };

  const generateCharacter = async () => {
    if (!currentCopyId) return;

    try {
      const response = await authFetch(`${API}/api/digital-copies/${currentCopyId}/generate`, {
        method: "POST"
      });

      if (response.ok) {
        await fetchCopies();
        resetCreator();
        alert("Character generation started!");
      } else {
        throw new Error("Failed to start character generation");
      }
    } catch (error) {
      console.error("Error generating character:", error);
      alert("Failed to start character generation");
    }
  };

  // ── Helper Functions ───────────────────────────────────
  const resetCreator = () => {
    setShowCreator(false);
    setCreatorStep("name");
    setCreatorData({ name: "", baseModel: "veo-3.1" });
    setCurrentCopyId(null);
    setUploadedImages([]);
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

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    files.forEach(file => {
      // Default to "other" image type - user will need to select proper type
      uploadImage(file, "other");
    });
  };

  const renderGauge = (current: number, target: number, label: string) => {
    const percentage = Math.min((current / target) * 100, 100);
    const radius = 45;
    const strokeWidth = 8;
    const normalizedRadius = radius - strokeWidth * 2;
    const circumference = normalizedRadius * 2 * Math.PI;
    const strokeDasharray = `${circumference} ${circumference}`;
    const strokeDashoffset = circumference - (percentage / 100) * circumference;

    return (
      <div className="flex flex-col items-center">
        <div className="relative">
          <svg height={radius * 2} width={radius * 2} className="transform -rotate-90">
            <circle
              stroke="var(--warroom-border)"
              fill="transparent"
              strokeWidth={strokeWidth}
              r={normalizedRadius}
              cx={radius}
              cy={radius}
            />
            <circle
              stroke="var(--warroom-accent)"
              fill="transparent"
              strokeWidth={strokeWidth}
              strokeDasharray={strokeDasharray}
              style={{ strokeDashoffset }}
              r={normalizedRadius}
              cx={radius}
              cy={radius}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <div className="text-lg font-bold text-warroom-text">{current}</div>
            <div className="text-xs text-warroom-muted">/ {target}</div>
          </div>
        </div>
        <div className="text-xs text-warroom-muted mt-2 text-center">{label}</div>
      </div>
    );
  };

  // ── Effects ────────────────────────────────────────────
  useEffect(() => {
    fetchCopies();
  }, [fetchCopies]);

  useEffect(() => {
    if (creatorStep === "audit" && currentCopyId && !qualityAudit) {
      performQualityAudit();
    }
  }, [creatorStep, currentCopyId, qualityAudit]);

  // ── Render ─────────────────────────────────────────────
  return (
    <div className="h-full flex flex-col bg-warroom-bg">
      {/* Header */}
      <div className="flex items-center justify-between p-6 border-b border-warroom-border">
        <div>
          <h1 className="text-xl font-bold text-warroom-text">Character Training Lab</h1>
          <p className="text-sm text-warroom-muted mt-1">Create and manage AI avatars for your videos</p>
        </div>
        <button
          onClick={() => setShowCreator(true)}
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
          // Empty state
          <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
            {/* Hero Section */}
            <div className="max-w-2xl">
              <h2 className="text-3xl font-bold text-warroom-text mb-4">
                MAKE YOUR OWN CHARACTER
              </h2>
              
              {/* Floating Polaroid Images */}
              <div className="relative mb-8 h-48">
                <div className="absolute top-0 left-1/4 transform -rotate-12 bg-white p-2 shadow-lg rounded">
                  <div className="w-24 h-24 bg-gradient-to-br from-purple-400 to-pink-400 rounded flex items-center justify-center">
                    <Camera size={24} className="text-white" />
                  </div>
                  <div className="text-xs text-gray-600 mt-2 text-center">Close-Up</div>
                </div>
                <div className="absolute top-4 right-1/4 transform rotate-12 bg-white p-2 shadow-lg rounded">
                  <div className="w-24 h-24 bg-gradient-to-br from-blue-400 to-cyan-400 rounded flex items-center justify-center">
                    <User size={24} className="text-white" />
                  </div>
                  <div className="text-xs text-gray-600 mt-2 text-center">Full Body</div>
                </div>
                <div className="absolute bottom-0 left-1/3 transform rotate-6 bg-white p-2 shadow-lg rounded">
                  <div className="w-24 h-24 bg-gradient-to-br from-green-400 to-emerald-400 rounded flex items-center justify-center">
                    <Eye size={24} className="text-white" />
                  </div>
                  <div className="text-xs text-gray-600 mt-2 text-center">Profile</div>
                </div>
                <div className="absolute bottom-4 right-1/3 transform -rotate-6 bg-white p-2 shadow-lg rounded">
                  <div className="w-24 h-24 bg-gradient-to-br from-orange-400 to-red-400 rounded flex items-center justify-center">
                    <Target size={24} className="text-white" />
                  </div>
                  <div className="text-xs text-gray-600 mt-2 text-center">Various</div>
                </div>
              </div>

              <p className="text-lg text-warroom-muted mb-8 leading-relaxed">
                Upload photos of yourself from multiple angles to create a digital avatar that can star in unlimited AI-generated videos. 
                Train once, use everywhere.
              </p>

              <button
                onClick={() => setShowCreator(true)}
                className="inline-flex items-center gap-3 px-8 py-4 bg-warroom-accent text-white text-lg font-semibold rounded-xl hover:bg-warroom-accent/80 transition shadow-lg shadow-warroom-accent/25"
              >
                <Sparkles size={20} />
                Create Your Character
              </button>
            </div>
          </div>
        ) : (
          // Character Grid
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {copies.map(copy => (
              <div key={copy.id} className="bg-warroom-surface border border-warroom-border rounded-xl overflow-hidden hover:border-warroom-accent/30 transition">
                {/* Thumbnail */}
                <div className="aspect-square bg-warroom-bg flex items-center justify-center">
                  {copy.thumbnail_url ? (
                    <img src={copy.thumbnail_url} alt={copy.name} className="w-full h-full object-cover" />
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
                  
                  <div className="flex items-center gap-4 text-sm text-warroom-muted">
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
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Creator Modal */}
      {showCreator && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-warroom-surface border border-warroom-border rounded-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-6 border-b border-warroom-border">
              <div>
                <h2 className="text-lg font-bold text-warroom-text">Create Character</h2>
                <div className="flex items-center gap-2 mt-2">
                  {["name", "upload", "audit"].map((step, index) => (
                    <div key={step} className="flex items-center">
                      <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                        creatorStep === step ? "bg-warroom-accent text-white" :
                        ["name", "upload", "audit"].indexOf(creatorStep) > index ? "bg-warroom-accent/20 text-warroom-accent" :
                        "bg-warroom-border text-warroom-muted"
                      }`}>
                        {index + 1}
                      </div>
                      {index < 2 && <ChevronRight size={14} className="text-warroom-border mx-1" />}
                    </div>
                  ))}
                </div>
              </div>
              <button onClick={resetCreator} className="p-2 rounded-lg hover:bg-warroom-bg text-warroom-muted">
                <X size={20} />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6">
              {creatorStep === "name" && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-semibold text-warroom-text mb-4">Name & Base Model</h3>
                    
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-warroom-text mb-2">Character Name</label>
                        <input
                          type="text"
                          value={creatorData.name}
                          onChange={(e) => setCreatorData(prev => ({ ...prev, name: e.target.value }))}
                          placeholder="e.g., My Avatar"
                          className="w-full px-4 py-3 bg-warroom-bg border border-warroom-border rounded-lg text-warroom-text focus:outline-none focus:border-warroom-accent"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-warroom-text mb-2">Base Model</label>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          {[
                            { value: "veo-3.1", label: "Veo 3.1", description: "High quality, realistic videos" },
                            { value: "nano-banana", label: "Nano Banana", description: "Fast generation, good quality" }
                          ].map(model => (
                            <button
                              key={model.value}
                              onClick={() => setCreatorData(prev => ({ ...prev, baseModel: model.value as any }))}
                              className={`p-4 rounded-lg border text-left transition ${
                                creatorData.baseModel === model.value
                                  ? "border-warroom-accent bg-warroom-accent/10 text-warroom-accent"
                                  : "border-warroom-border bg-warroom-bg text-warroom-text hover:border-warroom-accent/30"
                              }`}
                            >
                              <div className="font-medium">{model.label}</div>
                              <div className="text-sm text-warroom-muted mt-1">{model.description}</div>
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="flex justify-end">
                    <button
                      onClick={createDigitalCopy}
                      disabled={!creatorData.name.trim()}
                      className="px-6 py-2 bg-warroom-accent text-white rounded-lg hover:bg-warroom-accent/80 disabled:opacity-50 disabled:cursor-not-allowed transition"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}

              {creatorStep === "upload" && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-semibold text-warroom-text mb-4">Upload Images</h3>
                    
                    {/* Upload Zone */}
                    <div 
                      onClick={() => fileInputRef.current?.click()}
                      className="border-2 border-dashed border-warroom-border rounded-xl p-8 text-center cursor-pointer hover:border-warroom-accent/50 transition"
                    >
                      <div className="flex flex-col items-center">
                        <Upload size={32} className="text-warroom-muted mb-4" />
                        <h4 className="text-lg font-medium text-warroom-text mb-2">
                          Drag and drop images or click to upload
                        </h4>
                        <p className="text-sm text-warroom-muted">
                          Upload multiple photos from different angles for best results
                        </p>
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

                    {/* Image Counter */}
                    <div className="flex items-center justify-center mt-4">
                      <div className="text-center">
                        <div className="text-lg font-bold text-warroom-text">
                          {uploadedImages.length} / 20 photos
                        </div>
                        <div className="text-sm text-warroom-muted">
                          {uploadedImages.length < 8 ? `Need ${8 - uploadedImages.length} more minimum` : "Great! Keep adding for better quality"}
                        </div>
                      </div>
                    </div>

                    {/* Uploaded Images Grid */}
                    {uploadedImages.length > 0 && (
                      <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-3 mt-6">
                        {uploadedImages.map(image => (
                          <div key={image.id} className="relative group">
                            <div className="aspect-square bg-warroom-bg rounded-lg overflow-hidden border border-warroom-border">
                              <div className="w-full h-full flex items-center justify-center">
                                <Image size={24} className="text-warroom-muted" />
                              </div>
                            </div>
                            <div className="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-xs p-1 rounded-b-lg">
                              {IMAGE_TYPES.find(t => t.value === image.image_type)?.label || image.image_type}
                            </div>
                            <button
                              onClick={() => deleteImage(image.id)}
                              className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition"
                            >
                              <X size={12} className="text-white" />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Do/Don't Guidelines */}
                  <div className="bg-warroom-bg rounded-lg p-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <h4 className="text-sm font-semibold text-green-400 mb-3 flex items-center gap-2">
                          <CheckCircle size={16} />
                          Do This ✅
                        </h4>
                        <ul className="space-y-2">
                          {DO_DONT_GUIDELINES.do.map((item, index) => (
                            <li key={index} className="text-sm text-warroom-text flex items-start gap-2">
                              <span className="text-green-400 mt-0.5">•</span>
                              {item}
                            </li>
                          ))}
                        </ul>
                      </div>
                      <div>
                        <h4 className="text-sm font-semibold text-red-400 mb-3 flex items-center gap-2">
                          <X size={16} />
                          Avoid This ❌
                        </h4>
                        <ul className="space-y-2">
                          {DO_DONT_GUIDELINES.dont.map((item, index) => (
                            <li key={index} className="text-sm text-warroom-text flex items-start gap-2">
                              <span className="text-red-400 mt-0.5">•</span>
                              {item}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>

                  <div className="flex justify-between">
                    <button
                      onClick={() => setCreatorStep("name")}
                      className="px-6 py-2 bg-warroom-bg border border-warroom-border text-warroom-muted rounded-lg hover:text-warroom-text transition"
                    >
                      Back
                    </button>
                    <button
                      onClick={() => setCreatorStep("audit")}
                      disabled={uploadedImages.length < 8}
                      className="px-6 py-2 bg-warroom-accent text-white rounded-lg hover:bg-warroom-accent/80 disabled:opacity-50 disabled:cursor-not-allowed transition"
                    >
                      Quality Audit
                    </button>
                  </div>
                </div>
              )}

              {creatorStep === "audit" && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-semibold text-warroom-text mb-4">Quality Audit</h3>
                    
                    {auditLoading ? (
                      <div className="flex flex-col items-center justify-center py-12">
                        <Loader2 className="animate-spin text-warroom-accent mb-4" size={32} />
                        <p className="text-sm text-warroom-muted">Analyzing your images...</p>
                      </div>
                    ) : qualityAudit ? (
                      <div className="space-y-6">
                        {/* Gauges */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                          {renderGauge(qualityAudit.total_images, qualityAudit.target_images, "Image Count")}
                          {renderGauge(qualityAudit.quality_ok ? 100 : 50, 100, "Quality Check")}
                        </div>

                        {/* Angle Coverage */}
                        <div>
                          <h4 className="text-sm font-semibold text-warroom-text mb-3">Angle Coverage</h4>
                          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                            {Object.entries(qualityAudit.angle_coverage).map(([angle, count]) => (
                              <div key={angle} className={`p-3 rounded-lg border ${
                                count > 0 ? "border-green-500/30 bg-green-500/10" : "border-red-500/30 bg-red-500/10"
                              }`}>
                                <div className="flex items-center gap-2">
                                  {count > 0 ? (
                                    <CheckCircle size={16} className="text-green-400" />
                                  ) : (
                                    <X size={16} className="text-red-400" />
                                  )}
                                  <span className="text-sm font-medium text-warroom-text capitalize">
                                    {angle.replace("_", " ")} ({count})
                                  </span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Recommendation */}
                        {qualityAudit.recommendation && (
                          <div>
                            <h4 className="text-sm font-semibold text-warroom-text mb-3">Recommendation</h4>
                            <div className="bg-warroom-bg rounded-lg p-4">
                              <p className="text-sm text-warroom-muted">
                                {qualityAudit.recommendation}
                              </p>
                            </div>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="text-center py-8">
                        <AlertCircle size={32} className="text-red-400 mx-auto mb-4" />
                        <p className="text-sm text-warroom-muted">Failed to load quality audit</p>
                      </div>
                    )}
                  </div>

                  <div className="flex justify-between">
                    <button
                      onClick={() => setCreatorStep("upload")}
                      className="px-6 py-2 bg-warroom-bg border border-warroom-border text-warroom-muted rounded-lg hover:text-warroom-text transition"
                    >
                      Back
                    </button>
                    <button
                      onClick={generateCharacter}
                      disabled={!qualityAudit?.ready_for_training}
                      className="px-6 py-2 bg-warroom-accent text-white rounded-lg hover:bg-warroom-accent/80 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center gap-2"
                    >
                      <Sparkles size={16} />
                      Generate Character
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}