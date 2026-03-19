"use client";

import { useState, useEffect, useRef } from "react";
import {
  ChevronLeft, ChevronRight, Edit2, Instagram, Loader2,
  Eye, Download, Share2, Settings, Play, Pause, RotateCcw
} from "lucide-react";
import { API, authFetch } from "@/lib/api";

/* ── Types ─────────────────────────────────────────────── */
interface CarouselSlide {
  slide_num: number;
  text: string;
  image_url?: string | null;
  is_hook?: boolean;
  is_cta?: boolean;
}

interface CarouselData {
  id: number;
  slides: CarouselSlide[];
  caption: string;
  hashtags: string[];
  format: string;
  status: string;
  total_slides: number;
}

interface CarouselPreviewProps {
  carouselId?: number;
  slides?: CarouselSlide[];
  format?: string;
  onPublish?: (result: any) => void;
  onEdit?: (slideIndex: number, newText: string) => void;
  className?: string;
}

/* ── Main Component ────────────────────────────────────── */
export default function CarouselPreview({
  carouselId,
  slides: propSlides,
  format = "portrait",
  onPublish,
  onEdit,
  className = ""
}: CarouselPreviewProps) {
  // ── State ──────────────────────────────────────────────
  const [slides, setSlides] = useState<CarouselSlide[]>(propSlides || []);
  const [currentSlide, setCurrentSlide] = useState(0);
  const [loading, setLoading] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [editing, setEditing] = useState<number | null>(null);
  const [editText, setEditText] = useState("");
  const [caption, setCaption] = useState("");
  const [hashtags, setHashtags] = useState<string[]>([]);
  const [autoPlay, setAutoPlay] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [carouselData, setCarouselData] = useState<CarouselData | null>(null);

  const autoPlayRef = useRef<NodeJS.Timeout>();

  // ── Effects ────────────────────────────────────────────
  useEffect(() => {
    if (propSlides) {
      setSlides(propSlides);
    }
  }, [propSlides]);

  useEffect(() => {
    if (carouselId && !propSlides) {
      fetchCarouselData();
    }
  }, [carouselId]);

  useEffect(() => {
    if (autoPlay && slides.length > 1) {
      autoPlayRef.current = setInterval(() => {
        setCurrentSlide(prev => (prev + 1) % slides.length);
      }, 3000);
    } else {
      if (autoPlayRef.current) {
        clearInterval(autoPlayRef.current);
      }
    }

    return () => {
      if (autoPlayRef.current) {
        clearInterval(autoPlayRef.current);
      }
    };
  }, [autoPlay, slides.length]);

  // ── API Functions ──────────────────────────────────────
  const fetchCarouselData = async () => {
    if (!carouselId) return;
    
    setLoading(true);
    try {
      const response = await authFetch(`${API}/api/carousel/preview/${carouselId}`);
      if (response.ok) {
        const data = await response.json();
        setCarouselData(data);
        setSlides(data.slides || []);
        setCaption(data.caption || "");
        setHashtags(data.hashtags || []);
      } else {
        console.error("Failed to fetch carousel data");
      }
    } catch (error) {
      console.error("Error fetching carousel:", error);
    } finally {
      setLoading(false);
    }
  };

  const saveEditedSlide = async (slideIndex: number, newText: string) => {
    if (!carouselId) {
      // Local editing for prop-based usage
      const updatedSlides = [...slides];
      updatedSlides[slideIndex] = { ...updatedSlides[slideIndex], text: newText };
      setSlides(updatedSlides);
      onEdit?.(slideIndex, newText);
      setEditing(null);
      return;
    }

    try {
      const updatedSlides = [...slides];
      updatedSlides[slideIndex] = { ...updatedSlides[slideIndex], text: newText };

      const response = await authFetch(`${API}/api/carousel/${carouselId}`, {
        method: "PUT",
        body: JSON.stringify({ slides: updatedSlides })
      });

      if (response.ok) {
        setSlides(updatedSlides);
        setEditing(null);
      } else {
        console.error("Failed to save slide edit");
      }
    } catch (error) {
      console.error("Error saving slide edit:", error);
    }
  };

  const publishCarousel = async () => {
    if (!carouselId) return;

    setPublishing(true);
    try {
      const response = await authFetch(`${API}/api/carousel/publish`, {
        method: "POST",
        body: JSON.stringify({
          carousel_id: carouselId,
          caption,
          hashtags
        })
      });

      if (response.ok) {
        const result = await response.json();
        onPublish?.(result);
        
        // Update local state
        if (carouselData) {
          setCarouselData({
            ...carouselData,
            status: "published"
          });
        }
      } else {
        const error = await response.json();
        alert(error.detail || "Failed to publish carousel");
      }
    } catch (error) {
      console.error("Error publishing carousel:", error);
      alert("Failed to publish carousel");
    } finally {
      setPublishing(false);
    }
  };

  // ── Helper Functions ───────────────────────────────────
  const getAspectRatio = () => {
    switch (format) {
      case "square": return "aspect-square";
      case "story": return "aspect-[9/16]";
      default: return "aspect-[4/5]"; // portrait
    }
  };

  const getFormatLabel = () => {
    switch (format) {
      case "square": return "Square (1:1)";
      case "story": return "Story (9:16)";
      default: return "Portrait (4:5)";
    }
  };

  // ── Render Functions ───────────────────────────────────
  const renderSlide = (slide: CarouselSlide, index: number) => {
    const isActive = index === currentSlide;
    const isEditing = editing === index;

    return (
      <div
        key={`${slide.slide_num}-${index}`}
        className={`relative ${getAspectRatio()} w-full max-w-sm mx-auto bg-warroom-surface border border-warroom-border rounded-2xl overflow-hidden transition-all duration-300 ${
          isActive ? "scale-100 opacity-100" : "scale-95 opacity-60"
        }`}
      >
        {/* Background Image */}
        {slide.image_url ? (
          <img
            src={slide.image_url}
            alt={`Slide ${slide.slide_num}`}
            className="absolute inset-0 w-full h-full object-cover"
          />
        ) : (
          <div className="absolute inset-0 bg-gradient-to-br from-warroom-accent/20 to-warroom-accent/5" />
        )}

        {/* Text Overlay */}
        <div className="absolute inset-0 bg-black/20 flex items-center justify-center p-6">
          {isEditing ? (
            <div className="w-full max-h-full overflow-hidden">
              <textarea
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
                className="w-full h-32 p-3 bg-white/90 text-black text-sm rounded-lg resize-none"
                autoFocus
              />
              <div className="flex gap-2 mt-2">
                <button
                  onClick={() => saveEditedSlide(index, editText)}
                  className="px-3 py-1 bg-green-600 text-white text-xs rounded-md"
                >
                  Save
                </button>
                <button
                  onClick={() => setEditing(null)}
                  className="px-3 py-1 bg-gray-600 text-white text-xs rounded-md"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="relative w-full text-center">
              <p className="text-white text-sm font-medium leading-relaxed drop-shadow-lg">
                {slide.text}
              </p>
              
              {/* Slide indicators */}
              <div className="absolute top-2 right-2 flex items-center gap-1">
                {slide.is_hook && (
                  <span className="text-[10px] bg-yellow-500/80 text-white px-2 py-0.5 rounded-full">
                    Hook
                  </span>
                )}
                {slide.is_cta && (
                  <span className="text-[10px] bg-green-500/80 text-white px-2 py-0.5 rounded-full">
                    CTA
                  </span>
                )}
                <span className="text-[10px] bg-black/60 text-white px-2 py-0.5 rounded-full">
                  {slide.slide_num}
                </span>
              </div>

              {/* Edit button */}
              {isActive && (
                <button
                  onClick={() => {
                    setEditing(index);
                    setEditText(slide.text);
                  }}
                  className="absolute bottom-2 right-2 p-2 bg-black/60 text-white rounded-full hover:bg-black/80 transition"
                >
                  <Edit2 size={14} />
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <Loader2 className="animate-spin text-warroom-accent" size={32} />
      </div>
    );
  }

  if (slides.length === 0) {
    return (
      <div className="text-center py-12 text-warroom-muted">
        <p className="text-sm">No slides to preview</p>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-warroom-text">Carousel Preview</h3>
          <p className="text-sm text-warroom-muted">
            {slides.length} slides • {getFormatLabel()}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setAutoPlay(!autoPlay)}
            className={`p-2 rounded-lg transition ${
              autoPlay ? "bg-warroom-accent text-white" : "bg-warroom-border text-warroom-muted"
            }`}
            title={autoPlay ? "Pause auto-play" : "Start auto-play"}
          >
            {autoPlay ? <Pause size={16} /> : <Play size={16} />}
          </button>

          <button
            onClick={() => setShowSettings(!showSettings)}
            className="p-2 bg-warroom-border text-warroom-muted rounded-lg hover:bg-warroom-accent/20 transition"
          >
            <Settings size={16} />
          </button>
        </div>
      </div>

      {/* Main Preview */}
      <div className="relative">
        {/* Slide Display */}
        <div className="flex items-center justify-center min-h-[400px]">
          {renderSlide(slides[currentSlide], currentSlide)}
        </div>

        {/* Navigation Arrows */}
        {slides.length > 1 && (
          <>
            <button
              onClick={() => setCurrentSlide(prev => (prev - 1 + slides.length) % slides.length)}
              className="absolute left-4 top-1/2 -translate-y-1/2 p-2 bg-black/60 text-white rounded-full hover:bg-black/80 transition"
            >
              <ChevronLeft size={20} />
            </button>
            <button
              onClick={() => setCurrentSlide(prev => (prev + 1) % slides.length)}
              className="absolute right-4 top-1/2 -translate-y-1/2 p-2 bg-black/60 text-white rounded-full hover:bg-black/80 transition"
            >
              <ChevronRight size={20} />
            </button>
          </>
        )}
      </div>

      {/* Progress Dots */}
      {slides.length > 1 && (
        <div className="flex justify-center gap-2">
          {slides.map((_, index) => (
            <button
              key={index}
              onClick={() => setCurrentSlide(index)}
              className={`w-2 h-2 rounded-full transition ${
                index === currentSlide ? "bg-warroom-accent" : "bg-warroom-border"
              }`}
            />
          ))}
        </div>
      )}

      {/* Caption and Hashtags */}
      {showSettings && (
        <div className="space-y-4 p-4 bg-warroom-surface border border-warroom-border rounded-xl">
          <div>
            <label className="text-sm font-medium text-warroom-text block mb-2">
              Instagram Caption
            </label>
            <textarea
              value={caption}
              onChange={(e) => setCaption(e.target.value)}
              placeholder="Write your Instagram caption..."
              className="w-full p-3 bg-warroom-bg border border-warroom-border rounded-lg text-sm resize-none"
              rows={3}
            />
          </div>

          <div>
            <label className="text-sm font-medium text-warroom-text block mb-2">
              Hashtags
            </label>
            <input
              value={hashtags.join(" ")}
              onChange={(e) => setHashtags(e.target.value.split(" ").filter(Boolean))}
              placeholder="#socialmedia #marketing #content"
              className="w-full p-3 bg-warroom-bg border border-warroom-border rounded-lg text-sm"
            />
          </div>
        </div>
      )}

      {/* Action Buttons */}
      {carouselId && (
        <div className="flex gap-3">
          <button
            onClick={publishCarousel}
            disabled={publishing || carouselData?.status === "published"}
            className={`flex-1 flex items-center justify-center gap-2 py-3 px-6 rounded-lg font-medium transition ${
              carouselData?.status === "published"
                ? "bg-green-100 text-green-700 cursor-not-allowed"
                : "bg-gradient-to-r from-purple-500 to-pink-500 text-white hover:from-purple-600 hover:to-pink-600"
            }`}
          >
            {publishing ? (
              <Loader2 size={18} className="animate-spin" />
            ) : carouselData?.status === "published" ? (
              <Instagram size={18} />
            ) : (
              <Instagram size={18} />
            )}
            {publishing
              ? "Publishing..."
              : carouselData?.status === "published"
              ? "Published to Instagram"
              : "Publish to Instagram"
            }
          </button>

          <button
            onClick={() => window.open("#", "_blank")}
            className="px-4 py-3 bg-warroom-border text-warroom-muted rounded-lg hover:bg-warroom-accent/20 transition"
            title="Share preview"
          >
            <Share2 size={18} />
          </button>
        </div>
      )}

      {/* Status */}
      {carouselData && (
        <div className="text-center">
          <span className={`inline-flex items-center gap-1 text-sm px-3 py-1 rounded-full ${
            carouselData.status === "published" 
              ? "bg-green-100 text-green-700"
              : carouselData.status === "failed"
              ? "bg-red-100 text-red-700" 
              : "bg-yellow-100 text-yellow-700"
          }`}>
            Status: {carouselData.status}
          </span>
        </div>
      )}
    </div>
  );
}