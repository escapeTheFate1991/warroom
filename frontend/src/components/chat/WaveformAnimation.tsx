"use client";

import React, { useEffect, useRef } from "react";

interface WaveformAnimationProps {
  isActive: boolean;
  hasVoiceActivity: boolean;
  isListening?: boolean;
  isSpeaking?: boolean;
}

export default function WaveformAnimation({
  isActive,
  hasVoiceActivity,
  isListening = false,
  isSpeaking = false,
}: WaveformAnimationProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>();
  const audioDataRef = useRef<number[]>(new Array(60).fill(0));
  const phaseRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !isActive) {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      return;
    }

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    const centerX = width / 2;
    const centerY = height / 2;

    const animate = () => {
      ctx.clearRect(0, 0, width, height);
      
      phaseRef.current += 0.1;
      
      // Generate wave data based on state
      const amplitude = hasVoiceActivity ? 80 : 30;
      const frequency = isSpeaking ? 0.3 : 0.15;
      const numberOfWaves = hasVoiceActivity ? 3 : 2;
      
      // Main gradient background
      const gradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, Math.max(width, height) / 2);
      gradient.addColorStop(0, isListening ? 'rgba(34, 197, 94, 0.1)' : 'rgba(99, 102, 241, 0.1)');
      gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, width, height);

      // Draw multiple wave layers
      for (let wave = 0; wave < numberOfWaves; wave++) {
        ctx.beginPath();
        
        const waveAmplitude = amplitude * (1 - wave * 0.3);
        const waveFrequency = frequency * (1 + wave * 0.5);
        const phase = phaseRef.current + wave * Math.PI / 3;
        
        let firstPoint = true;
        
        for (let x = 0; x < width; x += 2) {
          const normalizedX = (x - centerX) / width;
          
          // Complex wave equation for more organic feel
          const baseWave = Math.sin(normalizedX * Math.PI * 4 + phase) * waveAmplitude;
          const modulation = Math.sin(normalizedX * Math.PI * 8 + phase * 1.5) * (waveAmplitude * 0.3);
          const noise = (Math.random() - 0.5) * (hasVoiceActivity ? 10 : 3);
          
          const y = centerY + (baseWave + modulation + noise) * (hasVoiceActivity ? 1 : 0.5);
          
          if (firstPoint) {
            ctx.moveTo(x, y);
            firstPoint = false;
          } else {
            ctx.lineTo(x, y);
          }
        }
        
        // Style the wave
        const alpha = hasVoiceActivity ? 0.8 - wave * 0.2 : 0.6 - wave * 0.2;
        
        if (isListening) {
          ctx.strokeStyle = `rgba(34, 197, 94, ${alpha})`;  // Green for listening
          ctx.shadowColor = '#22c55e';
        } else if (isSpeaking) {
          ctx.strokeStyle = `rgba(99, 102, 241, ${alpha})`;  // Purple for speaking
          ctx.shadowColor = '#6366f1';
        } else {
          ctx.strokeStyle = `rgba(156, 163, 175, ${alpha})`;  // Gray for idle
          ctx.shadowColor = '#9ca3af';
        }
        
        ctx.lineWidth = hasVoiceActivity ? 3 - wave * 0.5 : 2 - wave * 0.3;
        ctx.shadowBlur = hasVoiceActivity ? 20 - wave * 5 : 10 - wave * 2;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        
        ctx.stroke();
        
        // Add glow effect with multiple shadows
        if (hasVoiceActivity) {
          ctx.shadowBlur = 40;
          ctx.stroke();
          ctx.shadowBlur = 60;
          ctx.globalAlpha = 0.3;
          ctx.stroke();
          ctx.globalAlpha = 1;
        }
        
        ctx.shadowBlur = 0;
      }

      // Add central pulsing orb
      if (hasVoiceActivity) {
        const orbRadius = 4 + Math.sin(phaseRef.current * 2) * 2;
        const orbGradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, orbRadius * 3);
        
        if (isListening) {
          orbGradient.addColorStop(0, 'rgba(34, 197, 94, 0.8)');
          orbGradient.addColorStop(0.5, 'rgba(34, 197, 94, 0.3)');
          orbGradient.addColorStop(1, 'rgba(34, 197, 94, 0)');
        } else {
          orbGradient.addColorStop(0, 'rgba(99, 102, 241, 0.8)');
          orbGradient.addColorStop(0.5, 'rgba(99, 102, 241, 0.3)');
          orbGradient.addColorStop(1, 'rgba(99, 102, 241, 0)');
        }
        
        ctx.beginPath();
        ctx.arc(centerX, centerY, orbRadius, 0, Math.PI * 2);
        ctx.fillStyle = orbGradient;
        ctx.fill();
        
        // Orb glow
        ctx.shadowColor = isListening ? '#22c55e' : '#6366f1';
        ctx.shadowBlur = 20;
        ctx.fill();
        ctx.shadowBlur = 0;
      }

      // Add particle effects for high activity
      if (hasVoiceActivity && Math.random() > 0.8) {
        const particleCount = 3;
        for (let i = 0; i < particleCount; i++) {
          const px = centerX + (Math.random() - 0.5) * width * 0.3;
          const py = centerY + (Math.random() - 0.5) * height * 0.3;
          const size = Math.random() * 2 + 1;
          
          ctx.beginPath();
          ctx.arc(px, py, size, 0, Math.PI * 2);
          ctx.fillStyle = isListening ? 'rgba(34, 197, 94, 0.6)' : 'rgba(99, 102, 241, 0.6)';
          ctx.fill();
          
          // Particle glow
          ctx.shadowColor = isListening ? '#22c55e' : '#6366f1';
          ctx.shadowBlur = 10;
          ctx.fill();
          ctx.shadowBlur = 0;
        }
      }
      
      animationRef.current = requestAnimationFrame(animate);
    };

    animate();
    
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isActive, hasVoiceActivity, isListening, isSpeaking]);

  if (!isActive) {
    return null;
  }

  return (
    <div className="relative w-full h-full flex items-center justify-center">
      <canvas
        ref={canvasRef}
        width={400}
        height={200}
        className="w-full h-full object-contain"
        style={{
          filter: hasVoiceActivity ? 'brightness(1.2) saturate(1.3)' : 'brightness(1) saturate(1)',
        }}
      />
      
      {/* Status indicator */}
      <div className="absolute bottom-2 left-1/2 transform -translate-x-1/2">
        <div className="flex items-center gap-2 bg-black/30 backdrop-blur-sm rounded-full px-3 py-1">
          <div 
            className={`w-2 h-2 rounded-full ${
              isListening 
                ? 'bg-green-500 animate-pulse' 
                : isSpeaking 
                ? 'bg-purple-500 animate-pulse'
                : 'bg-gray-400'
            }`}
          />
          <span className="text-xs text-white/80">
            {isListening ? 'Listening...' : isSpeaking ? 'Speaking...' : 'Ready'}
          </span>
        </div>
      </div>
    </div>
  );
}

// Enhanced WaveformIcon for the button
export function EnhancedWaveformIcon({ 
  size = 18, 
  animated = false,
  isActive = false,
  hasActivity = false 
}: { 
  size?: number; 
  animated?: boolean;
  isActive?: boolean;
  hasActivity?: boolean;
}) {
  const bars = [
    { x: 2, baseHeight: 6, maxHeight: 12 },
    { x: 6, baseHeight: 10, maxHeight: 18 },
    { x: 10, baseHeight: 4, maxHeight: 8 },
    { x: 14, baseHeight: 12, maxHeight: 20 },
    { x: 18, baseHeight: 8, maxHeight: 14 },
    { x: 22, baseHeight: 6, maxHeight: 10 },
  ];

  return (
    <svg 
      width={size} 
      height={size} 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="currentColor" 
      strokeWidth="1.5" 
      strokeLinecap="round"
      className={`transition-all duration-300 ${
        isActive 
          ? 'drop-shadow-[0_0_8px_currentColor] text-green-400' 
          : 'text-current'
      }`}
      style={{
        filter: isActive && hasActivity 
          ? 'drop-shadow(0 0 12px currentColor) brightness(1.3)' 
          : isActive 
          ? 'drop-shadow(0 0 8px currentColor)' 
          : 'none'
      }}
    >
      {/* Background glow for active state */}
      {isActive && (
        <defs>
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge> 
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>
      )}
      
      {bars.map((bar, i) => {
        const height = animated && hasActivity
          ? bar.maxHeight
          : animated
          ? bar.baseHeight + (bar.maxHeight - bar.baseHeight) * 0.5
          : bar.baseHeight;
        
        const y1 = (24 - height) / 2;
        const y2 = y1 + height;
        
        return animated ? (
          <line 
            key={i} 
            x1={bar.x} 
            x2={bar.x} 
            y1={12} 
            y2={12}
            filter={isActive ? "url(#glow)" : "none"}
          >
            <animate 
              attributeName="y1" 
              values={hasActivity 
                ? `12;${(24 - bar.maxHeight) / 2};12`
                : `12;${(24 - bar.baseHeight) / 2};12`
              } 
              dur={`${0.6 + i * 0.1}s`} 
              repeatCount="indefinite" 
            />
            <animate 
              attributeName="y2" 
              values={hasActivity
                ? `12;${(24 + bar.maxHeight) / 2};12`
                : `12;${(24 + bar.baseHeight) / 2};12`
              } 
              dur={`${0.6 + i * 0.1}s`} 
              repeatCount="indefinite" 
            />
          </line>
        ) : (
          <line 
            key={i} 
            x1={bar.x} 
            x2={bar.x} 
            y1={y1} 
            y2={y2} 
            filter={isActive ? "url(#glow)" : "none"}
          />
        );
      })}
    </svg>
  );
}