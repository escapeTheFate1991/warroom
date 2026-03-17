import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from "remotion";

export interface CTASlideProps {
  text: string; // "Link in bio", "Follow for Part 2"
  style: "pulse" | "slide_up" | "glow" | "bounce";
  buttonText?: string;
  icon?: "arrow" | "link" | "follow" | "share";
  backgroundColor?: string;
  accentColor?: string;
}

export const CTASlide: React.FC<CTASlideProps> = ({
  text,
  style,
  buttonText,
  icon,
  backgroundColor = "#06060a",
  accentColor = "#7c3aed",
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const textColor = "#e8eaf0";

  const getIconSymbol = () => {
    switch (icon) {
      case "arrow":
        return "→";
      case "link":
        return "🔗";
      case "follow":
        return "👤";
      case "share":
        return "📤";
      default:
        return "";
    }
  };

  const getAnimationProps = () => {
    switch (style) {
      case "pulse":
        const pulseScale = interpolate(
          frame % 60,
          [0, 30, 60],
          [1, 1.1, 1],
          { extrapolateRight: "clamp" }
        );
        const entranceScale = spring({
          frame,
          fps,
          from: 0,
          to: 1,
          config: { damping: 8, mass: 0.5 },
        });
        return {
          scale: entranceScale * pulseScale,
          y: 0,
          opacity: interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" }),
          glow: 0.6,
        };

      case "slide_up":
        return {
          scale: spring({ frame, fps, from: 0.8, to: 1, config: { damping: 10 } }),
          y: spring({ frame, fps, from: 100, to: 0, config: { damping: 12 } }),
          opacity: interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" }),
          glow: 0.4,
        };

      case "glow":
        const glowIntensity = interpolate(
          Math.sin(frame * 0.1) * 0.5 + 0.5,
          [0, 1],
          [0.3, 1],
          { extrapolateRight: "clamp" }
        );
        return {
          scale: spring({ frame, fps, from: 0, to: 1, config: { damping: 6 } }),
          y: 0,
          opacity: interpolate(frame, [0, 25], [0, 1], { extrapolateRight: "clamp" }),
          glow: glowIntensity,
        };

      case "bounce":
        return {
          scale: spring({
            frame,
            fps,
            from: 0,
            to: 1,
            config: { damping: 6, stiffness: 200, mass: 0.8 },
          }),
          y: spring({
            frame: Math.max(0, frame - 10),
            fps,
            from: 50,
            to: 0,
            config: { damping: 8 },
          }),
          opacity: interpolate(frame, [0, 10], [0, 1], { extrapolateRight: "clamp" }),
          glow: 0.5,
        };

      default:
        return {
          scale: 1,
          y: 0,
          opacity: 1,
          glow: 0.4,
        };
    }
  };

  const { scale, y, opacity, glow } = getAnimationProps();

  const buttonOpacity = interpolate(frame, [20, 40], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const backgroundGradientOpacity = interpolate(frame, [0, 30], [0, 0.3], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor }}>
      {/* Background gradient effect */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(circle at center, ${accentColor}${Math.round(backgroundGradientOpacity * 255).toString(16).padStart(2, "0")}, transparent 70%)`,
        }}
      />

      {/* Main CTA container */}
      <div
        style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: `translate(-50%, -50%) scale(${scale}) translateY(${y}px)`,
          opacity,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 40,
          textAlign: "center",
          padding: 60,
        }}
      >
        {/* Main text */}
        <h1
          style={{
            fontSize: 80,
            fontWeight: 900,
            color: textColor,
            margin: 0,
            lineHeight: 1.1,
            textShadow: "0 4px 20px rgba(0,0,0,0.6)",
            maxWidth: width - 120,
          }}
        >
          {text}
        </h1>

        {/* Button */}
        {buttonText && (
          <div
            style={{
              opacity: buttonOpacity,
              transform: `scale(${buttonOpacity})`,
              padding: "24px 64px",
              backgroundColor: accentColor,
              borderRadius: 20,
              boxShadow: `0 0 ${60 * glow}px ${accentColor}, 0 8px 32px rgba(0,0,0,0.3)`,
              cursor: "pointer",
              transition: "all 0.3s ease",
              border: `3px solid ${accentColor}`,
              position: "relative",
              overflow: "hidden",
            }}
          >
            {/* Button glow overlay */}
            <div
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: `linear-gradient(45deg, transparent 30%, ${accentColor}40, transparent 70%)`,
                opacity: glow * 0.3,
                borderRadius: 20,
              }}
            />
            
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 16,
                fontSize: 48,
                fontWeight: 800,
                color: "white",
                position: "relative",
                zIndex: 1,
              }}
            >
              <span>{buttonText}</span>
              {icon && (
                <span
                  style={{
                    fontSize: 42,
                    transform: style === "bounce" && frame % 120 > 60 ? "scale(1.2)" : "scale(1)",
                    transition: "transform 0.2s ease",
                  }}
                >
                  {getIconSymbol()}
                </span>
              )}
            </div>
          </div>
        )}

        {/* Accent elements */}
        <div
          style={{
            display: "flex",
            gap: 12,
            opacity: opacity * 0.8,
          }}
        >
          {[...Array(3)].map((_, i) => (
            <div
              key={i}
              style={{
                width: 12,
                height: 12,
                borderRadius: "50%",
                backgroundColor: accentColor,
                opacity: interpolate(
                  frame % 90,
                  [i * 30, i * 30 + 15, i * 30 + 30],
                  [0.3, 1, 0.3],
                  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                ),
                transform: `scale(${interpolate(
                  frame % 90,
                  [i * 30, i * 30 + 15, i * 30 + 30],
                  [1, 1.5, 1],
                  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                )})`,
              }}
            />
          ))}
        </div>
      </div>

      {/* Floating particles */}
      {[...Array(8)].map((_, i) => {
        const particleDelay = i * 5;
        const particleY = interpolate(
          (frame + particleDelay) % 180,
          [0, 180],
          [height + 50, -50],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
        );
        const particleX = 100 + (i * (width - 200)) / 7;
        const particleOpacity = interpolate(
          (frame + particleDelay) % 180,
          [0, 30, 150, 180],
          [0, 0.6, 0.6, 0],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
        );

        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: particleX,
              top: particleY,
              width: 6,
              height: 6,
              borderRadius: "50%",
              backgroundColor: accentColor,
              opacity: particleOpacity * 0.7,
              transform: `scale(${0.5 + Math.sin((frame + i * 20) * 0.1) * 0.3})`,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};