"use client";

import { useRef, useEffect, useState } from "react";

interface VoiceOrbProps {
  isActive: boolean;
  isSpeaking: boolean;
  isListening: boolean;
  isProcessing: boolean;
  spokenText?: string;        // Full text being spoken via TTS
  ttsDurationMs?: number;     // Estimated TTS duration in ms
}

export default function VoiceOrb({ isActive, isSpeaking, isListening, isProcessing, spokenText, ttsDurationMs }: VoiceOrbProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const timeRef = useRef(0);
  const targetIntensityRef = useRef(0);
  const currentIntensityRef = useRef(0);

  // Word-by-word caption sync
  const [visibleWords, setVisibleWords] = useState(0);
  const wordsRef = useRef<string[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // When TTS starts (isSpeaking + spokenText), begin word reveal
    if (isSpeaking && spokenText) {
      const words = spokenText.split(/\s+/).filter(Boolean);
      wordsRef.current = words;
      setVisibleWords(0);

      // Estimate: ~150ms per word if no duration given, otherwise spread evenly
      const totalMs = ttsDurationMs || words.length * 150;
      const perWord = Math.max(50, totalMs / words.length);

      let idx = 0;
      timerRef.current = setInterval(() => {
        idx++;
        setVisibleWords(idx);
        if (idx >= words.length) {
          if (timerRef.current) clearInterval(timerRef.current);
        }
      }, perWord);

      return () => { if (timerRef.current) clearInterval(timerRef.current); };
    } else if (!isSpeaking) {
      // TTS stopped — show full text briefly then clear
      if (timerRef.current) clearInterval(timerRef.current);
      const wordCount = wordsRef.current.length;
      if (wordCount > 0) {
        setVisibleWords(wordCount);
        // Clear after 1.5s
        const t = setTimeout(() => { setVisibleWords(0); wordsRef.current = []; }, 1500);
        return () => clearTimeout(t);
      }
    }
  }, [isSpeaking, spokenText, ttsDurationMs]);

  // Canvas animation (unchanged)
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !isActive) return;

    const ctx = canvas.getContext("2d")!;
    const dpr = window.devicePixelRatio || 1;

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);
    };
    resize();
    window.addEventListener("resize", resize);

    let lastTime = performance.now();

    const draw = (now: number) => {
      const dt = (now - lastTime) / 1000;
      lastTime = now;
      timeRef.current += dt;
      const t = timeRef.current;

      const rect = canvas.getBoundingClientRect();
      const w = rect.width;
      const h = rect.height;
      const cx = w / 2;
      const cy = h / 2;
      const baseRadius = Math.min(w, h) * 0.32;

      if (isSpeaking) targetIntensityRef.current = 1.0;
      else if (isListening) targetIntensityRef.current = 0.6;
      else if (isProcessing) targetIntensityRef.current = 0.3;
      else targetIntensityRef.current = 0.1;

      const lerpSpeed = isSpeaking ? 4.0 : 2.0;
      currentIntensityRef.current += (targetIntensityRef.current - currentIntensityRef.current) * dt * lerpSpeed;
      const intensity = currentIntensityRef.current;

      ctx.clearRect(0, 0, w, h);

      // Outer glow
      const glowRadius = baseRadius * (1.3 + intensity * 0.3);
      const glow = ctx.createRadialGradient(cx, cy, baseRadius * 0.5, cx, cy, glowRadius);
      glow.addColorStop(0, `rgba(124, 58, 237, ${0.15 + intensity * 0.15})`);
      glow.addColorStop(0.5, `rgba(99, 102, 241, ${0.08 + intensity * 0.08})`);
      glow.addColorStop(1, "rgba(99, 102, 241, 0)");
      ctx.fillStyle = glow;
      ctx.fillRect(0, 0, w, h);

      // Morphing blob
      const points = 128;
      const speedMult = isSpeaking ? 2.5 : isListening ? 1.5 : 0.6;
      const deformAmount = baseRadius * (0.03 + intensity * 0.12);

      ctx.beginPath();
      for (let i = 0; i <= points; i++) {
        const angle = (i / points) * Math.PI * 2;
        const n1 = Math.sin(angle * 3 + t * speedMult * 1.2) * deformAmount;
        const n2 = Math.sin(angle * 5 - t * speedMult * 0.8) * deformAmount * 0.6;
        const n3 = Math.sin(angle * 7 + t * speedMult * 1.7) * deformAmount * 0.3;
        const n4 = Math.cos(angle * 2 - t * speedMult * 0.5) * deformAmount * 0.4;
        const breathe = Math.sin(t * 0.8) * baseRadius * 0.015;
        const r = baseRadius + n1 + n2 + n3 + n4 + breathe;

        const x = cx + Math.cos(angle) * r;
        const y = cy + Math.sin(angle) * r;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.closePath();

      const grad = ctx.createLinearGradient(
        cx - baseRadius, cy - baseRadius,
        cx + baseRadius, cy + baseRadius
      );
      const hueShift = Math.sin(t * 0.3) * 10;
      grad.addColorStop(0, `hsl(${265 + hueShift}, 80%, 55%)`);
      grad.addColorStop(0.5, `hsl(${250 + hueShift}, 75%, 60%)`);
      grad.addColorStop(1, `hsl(${220 + hueShift}, 70%, 55%)`);
      ctx.fillStyle = grad;
      ctx.fill();

      // Specular highlight
      const specular = ctx.createRadialGradient(
        cx - baseRadius * 0.3, cy - baseRadius * 0.3, 0,
        cx, cy, baseRadius
      );
      specular.addColorStop(0, `rgba(255, 255, 255, ${0.12 + intensity * 0.08})`);
      specular.addColorStop(0.4, "rgba(255, 255, 255, 0.02)");
      specular.addColorStop(1, "rgba(0, 0, 0, 0)");
      ctx.fillStyle = specular;
      ctx.fill();

      animRef.current = requestAnimationFrame(draw);
    };

    animRef.current = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(animRef.current);
      window.removeEventListener("resize", resize);
    };
  }, [isActive, isSpeaking, isListening, isProcessing]);

  if (!isActive) return null;

  // Build visible caption from revealed words
  const words = wordsRef.current;
  const captionText = visibleWords > 0
    ? words.slice(Math.max(0, visibleWords - 15), visibleWords).join(" ")
    : null;

  return (
    <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-warroom-bg">
      <div className="flex-1 flex items-center justify-center w-full">
        <canvas
          ref={canvasRef}
          className="w-full h-full max-w-[400px] max-h-[400px]"
          style={{ aspectRatio: "1/1" }}
        />
      </div>
      {/* Caption area — synced to TTS playback */}
      <div className="w-full px-8 pb-6 min-h-[60px] flex items-center justify-center">
        {captionText ? (
          <p className="text-sm text-warroom-text/70 text-center leading-relaxed max-w-lg transition-opacity duration-200">
            {captionText}
          </p>
        ) : isListening ? (
          <p className="text-xs text-warroom-muted/50 text-center">Listening…</p>
        ) : isProcessing ? (
          <p className="text-xs text-warroom-muted/50 text-center">Thinking…</p>
        ) : null}
      </div>
    </div>
  );
}
