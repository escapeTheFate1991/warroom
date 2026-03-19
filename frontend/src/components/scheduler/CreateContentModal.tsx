"use client";

import { useState, useEffect } from "react";
import {
  X,
  Sparkles,
  Image as ImageIcon,
  Video as VideoIcon,
  Hash,
  Type,
  Wand2,
  CheckCircle2,
  Upload,
  Loader2,
  Instagram,
  Twitter,
  Facebook,
  Youtube,
  Trash2,
  AtSign,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { authFetch, API } from "@/lib/api";

interface CreateContentModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialIdea?: string;
  inspirationId?: string;
  brandId?: string;
}

export function CreateContentModal({
  isOpen,
  onClose,
  initialIdea = "",
  inspirationId,
  brandId,
}: CreateContentModalProps) {
  const [caption, setCaption] = useState(initialIdea);
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([]);
  const [hashtags, setHashtags] = useState<string[]>([]);
  const [hashtagInput, setHashtagInput] = useState("");
  const [uploadedImages, setUploadedImages] = useState<string[]>([]);
  const [uploadedVideos, setUploadedVideos] = useState<string[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<"compose" | "ai-assist">("compose");
  const [error, setError] = useState<string>("");
  const [scheduledFor, setScheduledFor] = useState<string>("");

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setCaption(initialIdea);
      setSelectedPlatforms([]);
      setHashtags([]);
      setHashtagInput("");
      setUploadedImages([]);
      setUploadedVideos([]);
      setError("");
      setScheduledFor("");
    }
  }, [isOpen, initialIdea]);

  const handleSave = async () => {
    setIsSaving(true);
    setError("");
    try {
      // For each selected platform, create a scheduled post
      for (const platform of selectedPlatforms) {
        const fullCaption = hashtags.length > 0 
          ? `${caption}\n\n${hashtags.map((t: string) => `#${t}`).join(" ")}`
          : caption;
        
        const scheduleDate = scheduledFor 
          ? new Date(scheduledFor).toISOString() 
          : new Date(Date.now() + 60000).toISOString(); // Default: 1 min from now
        
        await authFetch(`${API}/api/scheduler/posts`, {
          method: "POST",
          body: JSON.stringify({
            platform: platform,
            content_type: "post",
            caption: fullCaption,
            scheduled_for: scheduleDate,
            media_urls: [...uploadedImages, ...uploadedVideos],
          }),
        });
      }
      
      onClose();
    } catch (error: any) {
      console.error("Save error:", error);
      setError(error.message || "Failed to schedule post");
    } finally {
      setIsSaving(false);
    }
  };

  const handleClose = () => {
    onClose();
  };

  const togglePlatform = (platform: string) => {
    setSelectedPlatforms((prev) =>
      prev.includes(platform)
        ? prev.filter((p) => p !== platform)
        : [...prev, platform]
    );
  };

  const addHashtag = () => {
    if (hashtagInput.trim() && !hashtags.includes(hashtagInput.trim())) {
      setHashtags([...hashtags, hashtagInput.trim()]);
      setHashtagInput("");
    }
  };

  const removeHashtag = (tag: string) => {
    setHashtags(hashtags.filter((t) => t !== tag));
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && hashtagInput.trim()) {
      e.preventDefault();
      addHashtag();
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={handleClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            onClick={(e) => e.target === e.currentTarget && handleClose()}
          >
            <div className="bg-warroom-surface border border-warroom-border rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
              {/* Header */}
              <div className="flex items-center justify-between p-6 border-b border-warroom-border">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-xl bg-warroom-accent/10 flex items-center justify-center">
                    <Sparkles className="h-5 w-5 text-warroom-accent" />
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-warroom-text">Create New Post</h2>
                    <p className="text-sm text-warroom-muted">
                      Compose your content with AI assistance
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleClose}
                  className="h-8 w-8 rounded-lg hover:bg-warroom-bg flex items-center justify-center transition-colors"
                >
                  <X className="h-5 w-5 text-warroom-muted" />
                </button>
              </div>

              {/* Tabs */}
              <div className="flex border-b border-warroom-border px-6">
                <button
                  onClick={() => setActiveTab("compose")}
                  className={cn(
                    "px-4 py-3 text-sm font-medium border-b-2 transition-colors",
                    activeTab === "compose"
                      ? "border-warroom-accent text-warroom-accent"
                      : "border-transparent text-warroom-muted hover:text-warroom-text"
                  )}
                >
                  <Type className="h-4 w-4 inline mr-2" />
                  Compose
                </button>
                <button
                  onClick={() => setActiveTab("ai-assist")}
                  className={cn(
                    "px-4 py-3 text-sm font-medium border-b-2 transition-colors",
                    activeTab === "ai-assist"
                      ? "border-warroom-accent text-warroom-accent"
                      : "border-transparent text-warroom-muted hover:text-warroom-text"
                  )}
                >
                  <Wand2 className="h-4 w-4 inline mr-2" />
                  AI Assist
                </button>
              </div>

              {/* Content */}
              <div className="flex-1 overflow-y-auto p-6">
                {activeTab === "compose" && (
                  <ComposeTab
                    caption={caption}
                    setCaption={setCaption}
                    selectedPlatforms={selectedPlatforms}
                    togglePlatform={togglePlatform}
                    hashtags={hashtags}
                    hashtagInput={hashtagInput}
                    setHashtagInput={setHashtagInput}
                    addHashtag={addHashtag}
                    removeHashtag={removeHashtag}
                    handleKeyPress={handleKeyPress}
                    uploadedImages={uploadedImages}
                    setUploadedImages={setUploadedImages}
                    uploadedVideos={uploadedVideos}
                    setUploadedVideos={setUploadedVideos}
                    isUploading={isUploading}
                    setIsUploading={setIsUploading}
                    scheduledFor={scheduledFor}
                    setScheduledFor={setScheduledFor}
                  />
                )}

                {activeTab === "ai-assist" && (
                  <AIAssistTab
                    caption={caption}
                    setCaption={setCaption}
                    brandId={brandId}
                    selectedPlatforms={selectedPlatforms}
                  />
                )}
              </div>

              {/* Error Display */}
              {error && (
                <div className="px-6 py-3 border-t border-warroom-border bg-red-500/10">
                  <p className="text-sm text-red-400">{error}</p>
                </div>
              )}

              {/* Footer */}
              <div className="flex items-center justify-between p-6 border-t border-warroom-border">
                <div className="text-sm text-warroom-muted">
                  {selectedPlatforms.length > 0 ? (
                    <span>
                      Publishing to {selectedPlatforms.length} platform
                      {selectedPlatforms.length > 1 ? "s" : ""}
                    </span>
                  ) : (
                    <span>Select at least one platform</span>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={handleClose}
                    className="px-4 py-2 rounded-lg text-sm font-medium text-warroom-muted hover:text-warroom-text hover:bg-warroom-bg transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSave}
                    disabled={!caption || selectedPlatforms.length === 0 || isSaving}
                    className="px-6 py-2 rounded-lg text-sm font-bold bg-warroom-accent hover:bg-warroom-accent/90 text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                  >
                    {isSaving ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="h-4 w-4" />
                        Save & Schedule
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

// Compose Tab Component
function ComposeTab({
  caption,
  setCaption,
  selectedPlatforms,
  togglePlatform,
  hashtags,
  hashtagInput,
  setHashtagInput,
  addHashtag,
  removeHashtag,
  handleKeyPress,
  uploadedImages,
  setUploadedImages,
  uploadedVideos,
  setUploadedVideos,
  isUploading,
  setIsUploading,
  scheduledFor,
  setScheduledFor,
}: any) {
  return (
    <div className="space-y-6">
      {/* Caption Input */}
      <div>
        <label className="block text-sm font-medium text-warroom-text mb-2">
          Caption
        </label>
        <textarea
          value={caption}
          onChange={(e) => setCaption(e.target.value)}
          placeholder="Write your caption here..."
          className="w-full h-32 bg-warroom-bg border border-warroom-border rounded-lg px-4 py-3 text-warroom-text placeholder:text-warroom-muted focus:outline-none focus:ring-2 focus:ring-warroom-accent resize-none"
        />
        <div className="flex items-center justify-between mt-2">
          <span className="text-xs text-warroom-muted">
            {caption.length} characters
          </span>
        </div>
      </div>

      {/* Platform Selection */}
      <div>
        <label className="block text-sm font-medium text-warroom-text mb-2">
          Select Platforms
        </label>
        <p className="text-xs text-warroom-muted mb-3">
          Choose which platforms to publish this content to
        </p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {platforms.map((platform) => (
            <button
              key={platform.id}
              onClick={() => togglePlatform(platform.id)}
              className={cn(
                "flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all",
                selectedPlatforms.includes(platform.id)
                  ? "border-warroom-accent bg-warroom-accent/10"
                  : "border-warroom-border hover:border-warroom-accent/50 bg-warroom-bg/30"
              )}
            >
              <platform.icon
                className={cn(
                  "h-6 w-6",
                  selectedPlatforms.includes(platform.id)
                    ? "text-warroom-accent"
                    : "text-warroom-muted"
                )}
              />
              <span
                className={cn(
                  "text-xs font-medium",
                  selectedPlatforms.includes(platform.id)
                    ? "text-warroom-accent"
                    : "text-warroom-muted"
                )}
              >
                {platform.name}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Media Upload */}
      <div>
        <label className="block text-sm font-medium text-warroom-text mb-2">
          Media
        </label>
        <p className="text-xs text-warroom-muted mb-3">
          Upload images or videos for your post
        </p>
        <div className="grid grid-cols-2 gap-3">
          {/* Image Upload */}
          <label className="flex flex-col items-center gap-2 p-6 rounded-xl border-2 border-dashed border-warroom-border hover:border-warroom-accent/50 bg-warroom-bg/30 cursor-pointer transition-all">
            <input
              type="file"
              accept="image/*"
              multiple
              className="hidden"
              onChange={(e) => handleFileUpload(e, "image", setUploadedImages, setIsUploading)}
            />
            <ImageIcon className="h-8 w-8 text-warroom-muted" />
            <span className="text-xs font-medium text-warroom-muted">
              Upload Images
            </span>
          </label>

          {/* Video Upload */}
          <label className="flex flex-col items-center gap-2 p-6 rounded-xl border-2 border-dashed border-warroom-border hover:border-warroom-accent/50 bg-warroom-bg/30 cursor-pointer transition-all">
            <input
              type="file"
              accept="video/*"
              className="hidden"
              onChange={(e) => handleFileUpload(e, "video", setUploadedVideos, setIsUploading)}
            />
            <VideoIcon className="h-8 w-8 text-warroom-muted" />
            <span className="text-xs font-medium text-warroom-muted">
              Upload Video
            </span>
          </label>
        </div>

        {/* Uploaded Media Preview */}
        {(uploadedImages.length > 0 || uploadedVideos.length > 0) && (
          <div className="mt-4 space-y-2">
            {uploadedImages.map((url: string, index: number) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 bg-warroom-bg rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <ImageIcon className="h-4 w-4 text-warroom-accent" />
                  <span className="text-sm text-warroom-text">Image {index + 1}</span>
                </div>
                <button
                  onClick={() =>
                    setUploadedImages(uploadedImages.filter((_: string, i: number) => i !== index))
                  }
                  className="text-warroom-muted hover:text-red-500 transition-colors"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
            {uploadedVideos.map((url: string, index: number) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 bg-warroom-bg rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <VideoIcon className="h-4 w-4 text-warroom-accent" />
                  <span className="text-sm text-warroom-text">Video {index + 1}</span>
                </div>
                <button
                  onClick={() =>
                    setUploadedVideos(uploadedVideos.filter((_: string, i: number) => i !== index))
                  }
                  className="text-warroom-muted hover:text-red-500 transition-colors"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        )}

        {isUploading && (
          <div className="mt-4 flex items-center gap-2 text-sm text-warroom-accent">
            <Loader2 className="h-4 w-4 animate-spin" />
            Uploading...
          </div>
        )}
      </div>

      {/* Hashtags */}
      <div>
        <label className="block text-sm font-medium text-warroom-text mb-2">
          Hashtags
        </label>
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <Hash className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-warroom-muted" />
            <input
              type="text"
              value={hashtagInput}
              onChange={(e) => setHashtagInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Add hashtag"
              className="w-full bg-warroom-bg border border-warroom-border rounded-lg pl-10 pr-4 py-2 text-warroom-text placeholder:text-warroom-muted focus:outline-none focus:ring-2 focus:ring-warroom-accent"
            />
          </div>
          <button
            onClick={addHashtag}
            disabled={!hashtagInput.trim()}
            className="px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/90 text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Add
          </button>
        </div>
        {hashtags.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-3">
            {hashtags.map((tag: string) => (
              <span
                key={tag}
                className="inline-flex items-center gap-1 px-3 py-1 bg-warroom-accent/10 text-warroom-accent rounded-full text-sm"
              >
                #{tag}
                <button
                  onClick={() => removeHashtag(tag)}
                  className="hover:text-warroom-accent/70 transition-colors"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Schedule For */}
      <div>
        <label className="block text-sm font-medium text-warroom-text mb-2">Schedule For</label>
        <input
          type="datetime-local"
          value={scheduledFor}
          onChange={(e) => setScheduledFor(e.target.value)}
          min={new Date().toISOString().slice(0, 16)}
          className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-4 py-2 text-warroom-text focus:outline-none focus:ring-2 focus:ring-warroom-accent"
        />
        <p className="text-xs text-warroom-muted mt-1">Leave empty to publish immediately</p>
      </div>
    </div>
  );
}

// Platform configuration
const platforms = [
  { id: "INSTAGRAM", name: "Instagram", icon: Instagram },
  { id: "TWITTER", name: "Twitter", icon: Twitter },
  { id: "FACEBOOK", name: "Facebook", icon: Facebook },
  { id: "YOUTUBE", name: "YouTube", icon: Youtube },
  { id: "THREADS", name: "Threads", icon: AtSign },
];

// File upload handler
async function handleFileUpload(
  e: React.ChangeEvent<HTMLInputElement>,
  mediaType: "image" | "video",
  setUrls: React.Dispatch<React.SetStateAction<string[]>>,
  setIsUploading: (loading: boolean) => void
) {
  const files = e.target.files;
  if (!files || files.length === 0) return;

  setIsUploading(true);

  try {
    const uploadPromises = Array.from(files).map(async (file) => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("mediaType", mediaType);

      const response = await authFetch(`${API}/api/media/upload`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Upload failed");
      }

      const data = await response.json();
      return data.mediaUrl;
    });

    const urls = await Promise.all(uploadPromises);
    setUrls((prev: string[]) => [...prev, ...urls]);
  } catch (error) {
    console.error("Upload error:", error);
    alert("Failed to upload file(s)");
  } finally {
    setIsUploading(false);
  }
}

// AI Assist Tab Component
function AIAssistTab({ caption, setCaption, brandId, selectedPlatforms }: any) {
  const [isLoading, setIsLoading] = useState(false);
  const [loadingType, setLoadingType] = useState<string>("");
  const [captionIdeas, setCaptionIdeas] = useState<string[]>([]);
  const [hashtagSuggestions, setHashtagSuggestions] = useState<string[]>([]);
  const [optimizationTips, setOptimizationTips] = useState<string[]>([]);

  const handleAIAssist = async (assistType: string, tone?: string) => {
    if (!caption.trim()) {
      alert("Please enter a caption first");
      return;
    }

    setIsLoading(true);
    setLoadingType(assistType);

    try {
      // This would use War Room's AI assist endpoint
      const response = await authFetch(`${API}/api/content/assist`, {
        method: "POST",
        body: JSON.stringify({
          caption,
          assistType,
          aiProvider: "openai",
          brandId,
          platforms: selectedPlatforms,
          tone,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "AI assistance failed");
      }

      const data = await response.json();

      switch (assistType) {
        case "grammar":
          setCaption(data.result);
          break;
        case "ideas":
          setCaptionIdeas(data.captions || []);
          break;
        case "hashtags":
          setHashtagSuggestions(data.hashtags || []);
          break;
        case "tone":
          setCaption(data.result);
          break;
        case "optimize":
          setCaption(data.optimized);
          setOptimizationTips(data.tips || []);
          break;
      }
    } catch (error: any) {
      console.error("AI assist error:", error);
      alert(error.message || "AI assistance failed");
    } finally {
      setIsLoading(false);
      setLoadingType("");
    }
  };

  const tones = [
    { id: "professional", name: "Professional", icon: "💼" },
    { id: "casual", name: "Casual", icon: "😊" },
    { id: "funny", name: "Funny", icon: "😂" },
    { id: "inspirational", name: "Inspirational", icon: "✨" },
    { id: "urgent", name: "Urgent", icon: "⚡" },
  ];

  return (
    <div className="space-y-6">
      {/* Grammar Check */}
      <div>
        <h3 className="text-sm font-bold text-warroom-text mb-3 flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-warroom-accent" />
          Grammar & Spelling
        </h3>
        <button
          onClick={() => handleAIAssist("grammar")}
          disabled={isLoading || !caption.trim()}
          className="w-full px-4 py-3 bg-warroom-bg hover:bg-warroom-surface border border-warroom-border rounded-lg text-warroom-text font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {isLoading && loadingType === "grammar" ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Checking...
            </>
          ) : (
            <>
              <CheckCircle2 className="h-4 w-4" />
              Fix Grammar & Spelling
            </>
          )}
        </button>
      </div>

      {/* Caption Ideas */}
      <div>
        <h3 className="text-sm font-bold text-warroom-text mb-3 flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-warroom-accent" />
          Caption Variations
        </h3>
        <button
          onClick={() => handleAIAssist("ideas")}
          disabled={isLoading || !caption.trim()}
          className="w-full px-4 py-3 bg-warroom-bg hover:bg-warroom-surface border border-warroom-border rounded-lg text-warroom-text font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {isLoading && loadingType === "ideas" ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4" />
              Generate Caption Ideas
            </>
          )}
        </button>
        {captionIdeas.length > 0 && (
          <div className="mt-3 space-y-2">
            {captionIdeas.map((idea, index) => (
              <div
                key={index}
                className="p-3 bg-warroom-bg/50 rounded-lg border border-warroom-border hover:border-warroom-accent/50 transition-colors cursor-pointer group"
                onClick={() => setCaption(idea)}
              >
                <p className="text-sm text-warroom-text group-hover:text-warroom-accent transition-colors">
                  {idea}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Tone Adjustment */}
      <div>
        <h3 className="text-sm font-bold text-warroom-text mb-3 flex items-center gap-2">
          <Type className="h-4 w-4 text-warroom-accent" />
          Adjust Tone
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
          {tones.map((tone) => (
            <button
              key={tone.id}
              onClick={() => handleAIAssist("tone", tone.id)}
              disabled={isLoading || !caption.trim()}
              className="px-3 py-2 bg-warroom-bg hover:bg-warroom-surface border border-warroom-border rounded-lg text-warroom-text text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isLoading && loadingType === "tone" ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <>
                  <span>{tone.icon}</span>
                  <span>{tone.name}</span>
                </>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Hashtag Suggestions */}
      <div>
        <h3 className="text-sm font-bold text-warroom-text mb-3 flex items-center gap-2">
          <Hash className="h-4 w-4 text-warroom-accent" />
          Hashtag Suggestions
        </h3>
        <button
          onClick={() => handleAIAssist("hashtags")}
          disabled={isLoading || !caption.trim()}
          className="w-full px-4 py-3 bg-warroom-bg hover:bg-warroom-surface border border-warroom-border rounded-lg text-warroom-text font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {isLoading && loadingType === "hashtags" ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Hash className="h-4 w-4" />
              Suggest Hashtags
            </>
          )}
        </button>
        {hashtagSuggestions.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {hashtagSuggestions.map((tag, index) => (
              <span
                key={index}
                className="inline-flex items-center gap-1 px-3 py-1 bg-warroom-accent/10 text-warroom-accent rounded-full text-sm cursor-pointer hover:bg-warroom-accent/20 transition-colors"
                onClick={() => {
                  // This would need to be passed from parent to add to hashtags
                  console.log("Add hashtag:", tag);
                }}
              >
                #{tag}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Platform Optimization */}
      <div>
        <h3 className="text-sm font-bold text-warroom-text mb-3 flex items-center gap-2">
          <Wand2 className="h-4 w-4 text-warroom-accent" />
          Platform Optimization
        </h3>
        <button
          onClick={() => handleAIAssist("optimize")}
          disabled={isLoading || !caption.trim() || selectedPlatforms.length === 0}
          className="w-full px-4 py-3 bg-warroom-accent hover:bg-warroom-accent/90 border border-warroom-accent rounded-lg text-white font-bold transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {isLoading && loadingType === "optimize" ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Optimizing...
            </>
          ) : (
            <>
              <Wand2 className="h-4 w-4" />
              Optimize for Selected Platforms
            </>
          )}
        </button>
        {optimizationTips.length > 0 && (
          <div className="mt-3 space-y-2">
            <p className="text-xs font-bold text-warroom-muted uppercase tracking-wider">
              Optimizations Applied:
            </p>
            {optimizationTips.map((tip, index) => (
              <div
                key={index}
                className="flex items-start gap-2 p-2 bg-warroom-accent/5 rounded-lg"
              >
                <CheckCircle2 className="h-4 w-4 text-warroom-accent mt-0.5 flex-shrink-0" />
                <p className="text-sm text-warroom-text">{tip}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}