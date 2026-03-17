import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Img,
} from "remotion";

export interface BRollProps {
  mediaUrl?: string; // background image/video URL
  overlayText?: string;
  overlayPosition: "center" | "bottom" | "top";
  blur?: number; // background blur amount
  vignette?: boolean;
  animation?: "fade_in" | "zoom" | "parallax";
}

export const BRoll: React.FC<BRollProps> = ({
  mediaUrl,
  overlayText,
  overlayPosition,
  blur = 0,
  vignette = true,
  animation = "fade_in",
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const backgroundColor = "#06060a";
  const textColor = "#e8eaf0";

  const getAnimationProps = () => {
    switch (animation) {
      case "fade_in":
        return {
          opacity: interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" }),
          scale: 1,
          translateY: 0,
        };

      case "zoom":
        return {
          opacity: interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" }),
          scale: interpolate(frame, [0, 300], [1, 1.2], { extrapolateRight: "clamp" }),
          translateY: 0,
        };

      case "parallax":
        return {
          opacity: interpolate(frame, [0, 25], [0, 1], { extrapolateRight: "clamp" }),
          scale: 1,
          translateY: interpolate(frame, [0, 300], [0, -50], { extrapolateRight: "clamp" }),
        };

      default:
        return {
          opacity: 1,
          scale: 1,
          translateY: 0,
        };
    }
  };

  const { opacity, scale, translateY } = getAnimationProps();

  const textOpacity = interpolate(frame, [20, 40], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const textY = spring({
    frame: Math.max(0, frame - 20),
    fps,
    from: 30,
    to: 0,
    config: { damping: 12 },
  });

  const getOverlayPositionStyles = () => {
    switch (overlayPosition) {
      case "center":
        return {
          position: "absolute" as const,
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          textAlign: "center" as const,
          maxWidth: "80%",
        };

      case "bottom":
        return {
          position: "absolute" as const,
          bottom: 80,
          left: 60,
          right: 60,
          textAlign: "center" as const,
          padding: "24px 40px",
          backgroundColor: "rgba(6,6,10,0.8)",
          borderRadius: 16,
          border: "2px solid rgba(124,58,237,0.3)",
        };

      case "top":
        return {
          position: "absolute" as const,
          top: 80,
          left: 60,
          right: 60,
          textAlign: "center" as const,
          padding: "24px 40px",
          backgroundColor: "rgba(6,6,10,0.8)",
          borderRadius: 16,
          border: "2px solid rgba(124,58,237,0.3)",
        };

      default:
        return {
          position: "absolute" as const,
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          textAlign: "center" as const,
          maxWidth: "80%",
        };
    }
  };

  const overlayStyles = getOverlayPositionStyles();

  const getTextSize = () => {
    switch (overlayPosition) {
      case "center":
        return 72;
      case "bottom":
      case "top":
        return 48;
      default:
        return 56;
    }
  };

  const vignetteStyles = {
    background: vignette
      ? "radial-gradient(circle at center, transparent 20%, rgba(6,6,10,0.3) 50%, rgba(6,6,10,0.7) 80%, rgba(6,6,10,0.9) 100%)"
      : "none",
  };

  return (
    <AbsoluteFill style={{ backgroundColor }}>
      {/* Background Media */}
      {mediaUrl && (
        <AbsoluteFill
          style={{
            opacity,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              width: "100%",
              height: "100%",
              transform: `scale(${scale}) translateY(${translateY}px)`,
              transformOrigin: "center center",
            }}
          >
            <Img
              src={mediaUrl}
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
                filter: blur > 0 ? `blur(${blur}px)` : "none",
              }}
            />
          </div>
        </AbsoluteFill>
      )}

      {/* Vignette Overlay */}
      {vignette && (
        <AbsoluteFill style={vignetteStyles} />
      )}

      {/* Color Overlay for better text readability */}
      <AbsoluteFill
        style={{
          background: "rgba(6,6,10,0.2)",
        }}
      />

      {/* Text Overlay */}
      {overlayText && (
        <div
          style={{
            ...overlayStyles,
            fontSize: getTextSize(),
            fontWeight: overlayPosition === "center" ? 900 : 700,
            color: textColor,
            opacity: textOpacity,
            transform: `${overlayStyles.transform || ""} translateY(${textY}px)`,
            lineHeight: 1.2,
            textShadow:
              overlayPosition === "center"
                ? "0 4px 20px rgba(0,0,0,0.8)"
                : "0 2px 10px rgba(0,0,0,0.6)",
          }}
        >
          {overlayText}
        </div>
      )}

      {/* Subtle animation elements */}
      {animation === "parallax" && (
        <>
          {/* Floating dots */}
          {[...Array(6)].map((_, i) => {
            const dotY = interpolate(
              (frame + i * 20) % 240,
              [0, 240],
              [height + 20, -20],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            );
            const dotX = 50 + (i * (width - 100)) / 5;
            const dotOpacity = interpolate(
              (frame + i * 20) % 240,
              [0, 60, 180, 240],
              [0, 0.4, 0.4, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            );

            return (
              <div
                key={i}
                style={{
                  position: "absolute",
                  left: dotX,
                  top: dotY,
                  width: 4,
                  height: 4,
                  borderRadius: "50%",
                  backgroundColor: "#7c3aed",
                  opacity: dotOpacity,
                }}
              />
            );
          })}
        </>
      )}

      {/* Subtle zoom indicator for zoom animation */}
      {animation === "zoom" && frame > 60 && (
        <div
          style={{
            position: "absolute",
            bottom: 40,
            right: 40,
            width: 60,
            height: 60,
            borderRadius: "50%",
            border: "3px solid #7c3aed",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            backgroundColor: "rgba(6,6,10,0.8)",
            opacity: interpolate(frame, [60, 80], [0, 0.7], { extrapolateRight: "clamp" }),
          }}
        >
          <div
            style={{
              fontSize: 24,
              color: "#7c3aed",
              fontWeight: 800,
            }}
          >
            🔍
          </div>
        </div>
      )}

      {/* Loading indicator for fade_in */}
      {animation === "fade_in" && frame < 30 && (
        <div
          style={{
            position: "absolute",
            bottom: 40,
            left: "50%",
            transform: "translateX(-50%)",
            display: "flex",
            gap: 8,
          }}
        >
          {[...Array(3)].map((_, i) => (
            <div
              key={i}
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                backgroundColor: "#7c3aed",
                opacity: interpolate(
                  (frame + i * 5) % 20,
                  [0, 10, 20],
                  [0.3, 1, 0.3],
                  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                ),
                transform: `scale(${interpolate(
                  (frame + i * 5) % 20,
                  [0, 10, 20],
                  [1, 1.5, 1],
                  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                )})`,
              }}
            />
          ))}
        </div>
      )}
    </AbsoluteFill>
  );
};