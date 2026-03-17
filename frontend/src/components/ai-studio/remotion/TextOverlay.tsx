import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from "remotion";

export interface TextOverlayProps {
  text: string;
  style: "bold_center" | "lower_third" | "top_banner" | "stamp";
  animation: "typewriter" | "slide_in" | "fade" | "slam";
  color?: string;
  backgroundColor?: string;
  stampText?: string; // e.g. "❌ FALSE" for Myth Buster
  stampColor?: string; // e.g. red for FALSE, green for TRUE
}

export const TextOverlay: React.FC<TextOverlayProps> = ({
  text,
  style,
  animation,
  color = "#e8eaf0",
  backgroundColor = "#06060a",
  stampText,
  stampColor = "#ef4444",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const getAnimationProps = () => {
    switch (animation) {
      case "typewriter":
        const typedLength = interpolate(frame, [0, 60], [0, text.length], {
          extrapolateRight: "clamp",
        });
        return {
          displayText: text.slice(0, Math.floor(typedLength)),
          opacity: 1,
          scale: 1,
          x: 0,
          y: 0,
        };

      case "slide_in":
        return {
          displayText: text,
          opacity: interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" }),
          scale: 1,
          x: spring({ frame, fps, from: -200, to: 0, config: { damping: 12 } }),
          y: 0,
        };

      case "fade":
        return {
          displayText: text,
          opacity: interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" }),
          scale: 1,
          x: 0,
          y: 0,
        };

      case "slam":
        return {
          displayText: text,
          opacity: interpolate(frame, [0, 10], [0, 1], { extrapolateRight: "clamp" }),
          scale: spring({ frame, fps, from: 1.5, to: 1, config: { damping: 8, mass: 0.4 } }),
          x: 0,
          y: 0,
        };

      default:
        return {
          displayText: text,
          opacity: 1,
          scale: 1,
          x: 0,
          y: 0,
        };
    }
  };

  const { displayText, opacity, scale, x, y } = getAnimationProps();

  const getStyleProps = () => {
    switch (style) {
      case "bold_center":
        return {
          position: { top: "50%", left: "50%", transform: "translate(-50%, -50%)" },
          fontSize: 96,
          fontWeight: 900,
          textAlign: "center" as const,
          maxWidth: "90%",
          lineHeight: 1.1,
          textShadow: "0 4px 20px rgba(0,0,0,0.8)",
        };

      case "lower_third":
        return {
          position: { bottom: 80, left: 0, right: 0 },
          fontSize: 48,
          fontWeight: 700,
          textAlign: "left" as const,
          padding: "20px 60px",
          background: `linear-gradient(90deg, ${backgroundColor}f0, ${backgroundColor}80, transparent)`,
          maxWidth: "70%",
          lineHeight: 1.2,
        };

      case "top_banner":
        return {
          position: { top: 60, left: 0, right: 0 },
          fontSize: 52,
          fontWeight: 800,
          textAlign: "center" as const,
          padding: "24px 40px",
          background: `${backgroundColor}e6`,
          borderRadius: 0,
          lineHeight: 1.3,
        };

      case "stamp":
        const rotation = interpolate(frame, [0, 20], [-15, -8], { extrapolateRight: "clamp" });
        return {
          position: { top: "30%", right: "15%" },
          fontSize: 72,
          fontWeight: 900,
          textAlign: "center" as const,
          padding: "32px 48px",
          background: stampColor,
          borderRadius: 16,
          transform: `rotate(${rotation}deg)`,
          border: `8px solid ${stampColor}`,
          boxShadow: `0 8px 32px ${stampColor}60`,
          color: "#ffffff",
          letterSpacing: 2,
          lineHeight: 1,
        };

      default:
        return {
          position: { top: "50%", left: "50%", transform: "translate(-50%, -50%)" },
          fontSize: 64,
          fontWeight: 700,
          textAlign: "center" as const,
          lineHeight: 1.2,
        };
    }
  };

  const styleProps = getStyleProps();

  return (
    <AbsoluteFill style={{ backgroundColor }}>
      <div
        style={{
          position: "absolute",
          ...styleProps.position,
          fontSize: styleProps.fontSize,
          fontWeight: styleProps.fontWeight,
          textAlign: styleProps.textAlign,
          color: style === "stamp" ? styleProps.color : color,
          opacity,
          transform: `${styleProps.transform || ""} scale(${scale}) translate(${x}px, ${y}px)`,
          maxWidth: styleProps.maxWidth,
          lineHeight: styleProps.lineHeight,
          padding: styleProps.padding,
          background: styleProps.background,
          borderRadius: styleProps.borderRadius,
          border: styleProps.border,
          boxShadow: styleProps.boxShadow,
          textShadow: styleProps.textShadow,
          letterSpacing: styleProps.letterSpacing,
        }}
      >
        {style === "stamp" ? stampText || text : displayText}
        {animation === "typewriter" && displayText.length < text.length && (
          <span
            style={{
              opacity: Math.sin(frame * 0.5) > 0 ? 1 : 0,
              marginLeft: 2,
            }}
          >
            |
          </span>
        )}
      </div>
    </AbsoluteFill>
  );
};