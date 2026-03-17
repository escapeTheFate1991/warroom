import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
} from "remotion";

export interface CaptionTrackProps {
  segments: Array<{ text: string; startFrame: number; endFrame: number }>;
  style: "centered" | "bottom" | "karaoke";
  fontSize?: number;
  highlightColor?: string;
  backgroundColor?: string;
}

export const CaptionTrack: React.FC<CaptionTrackProps> = ({
  segments,
  style,
  fontSize = 48,
  highlightColor = "#7c3aed",
  backgroundColor = "#06060a",
}) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const textColor = "#e8eaf0";

  const getCurrentSegment = () => {
    return segments.find(
      (segment) => frame >= segment.startFrame && frame <= segment.endFrame
    );
  };

  const getSegmentProgress = (segment: { startFrame: number; endFrame: number }) => {
    const duration = segment.endFrame - segment.startFrame;
    const elapsed = frame - segment.startFrame;
    return Math.max(0, Math.min(1, elapsed / duration));
  };

  const currentSegment = getCurrentSegment();

  if (!currentSegment) {
    return <AbsoluteFill style={{ backgroundColor }} />;
  }

  const progress = getSegmentProgress(currentSegment);
  const opacity = interpolate(
    frame,
    [currentSegment.startFrame, currentSegment.startFrame + 5, currentSegment.endFrame - 5, currentSegment.endFrame],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const getStyleProps = () => {
    switch (style) {
      case "centered":
        return {
          position: {
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
          },
          fontSize: fontSize * 1.2,
          fontWeight: 900,
          textAlign: "center" as const,
          maxWidth: "90%",
          lineHeight: 1.2,
          textShadow: "0 4px 20px rgba(0,0,0,0.8)",
          padding: "0",
          background: "transparent",
          borderRadius: 0,
        };

      case "bottom":
        return {
          position: {
            bottom: 80,
            left: 40,
            right: 40,
          },
          fontSize: fontSize * 0.9,
          fontWeight: 700,
          textAlign: "center" as const,
          maxWidth: "none",
          lineHeight: 1.4,
          textShadow: "none",
          padding: "20px 40px",
          background: "rgba(6,6,10,0.9)",
          borderRadius: 16,
          border: "2px solid rgba(124,58,237,0.3)",
        };

      case "karaoke":
        return {
          position: {
            top: "65%",
            left: "50%",
            transform: "translateX(-50%)",
          },
          fontSize: fontSize,
          fontWeight: 800,
          textAlign: "center" as const,
          maxWidth: "90%",
          lineHeight: 1.3,
          textShadow: "0 2px 10px rgba(0,0,0,0.6)",
          padding: "16px 32px",
          background: "rgba(6,6,10,0.7)",
          borderRadius: 12,
        };

      default:
        return {
          position: {
            bottom: 80,
            left: 40,
            right: 40,
          },
          fontSize: fontSize,
          fontWeight: 700,
          textAlign: "center" as const,
          maxWidth: "none",
          lineHeight: 1.4,
          textShadow: "none",
          padding: "20px 40px",
          background: "rgba(6,6,10,0.9)",
          borderRadius: 16,
        };
    }
  };

  const styleProps = getStyleProps();

  const renderKaraokeText = () => {
    const words = currentSegment.text.split(" ");
    const wordsPerProgress = words.length * progress;

    return (
      <span>
        {words.map((word, index) => {
          const isHighlighted = index < wordsPerProgress;
          const isPartiallyHighlighted = 
            index === Math.floor(wordsPerProgress) && wordsPerProgress % 1 > 0;

          return (
            <span key={index}>
              <span
                style={{
                  color: isHighlighted ? highlightColor : textColor,
                  background: isHighlighted ? `${highlightColor}20` : "transparent",
                  padding: isHighlighted ? "2px 6px" : "0",
                  borderRadius: isHighlighted ? 6 : 0,
                  transition: "all 0.2s ease",
                  transform: isPartiallyHighlighted ? "scale(1.05)" : "scale(1)",
                  display: "inline-block",
                }}
              >
                {word}
              </span>
              {index < words.length - 1 && " "}
            </span>
          );
        })}
      </span>
    );
  };

  const renderRegularText = () => {
    return <span>{currentSegment.text}</span>;
  };

  const getEntranceAnimation = () => {
    const segmentProgress = (frame - currentSegment.startFrame) / 10; // First 10 frames
    
    switch (style) {
      case "centered":
        return {
          transform: `${styleProps.position.transform} scale(${interpolate(segmentProgress, [0, 1], [0.8, 1], { extrapolateRight: "clamp" })})`,
        };
      case "bottom":
        return {
          transform: `translateY(${interpolate(segmentProgress, [0, 1], [50, 0], { extrapolateRight: "clamp" })}px)`,
        };
      case "karaoke":
        return {
          transform: `${styleProps.position.transform} translateY(${interpolate(segmentProgress, [0, 1], [30, 0], { extrapolateRight: "clamp" })}px)`,
        };
      default:
        return {};
    }
  };

  const animationProps = getEntranceAnimation();

  return (
    <AbsoluteFill style={{ backgroundColor }}>
      <div
        style={{
          position: "absolute",
          ...styleProps.position,
          fontSize: styleProps.fontSize,
          fontWeight: styleProps.fontWeight,
          textAlign: styleProps.textAlign,
          color: textColor,
          opacity,
          maxWidth: styleProps.maxWidth,
          lineHeight: styleProps.lineHeight,
          textShadow: styleProps.textShadow,
          padding: styleProps.padding,
          background: styleProps.background,
          borderRadius: styleProps.borderRadius,
          border: styleProps.border,
          ...animationProps,
        }}
      >
        {style === "karaoke" ? renderKaraokeText() : renderRegularText()}
      </div>

      {/* Progress bar for karaoke style */}
      {style === "karaoke" && (
        <div
          style={{
            position: "absolute",
            bottom: 40,
            left: "50%",
            transform: "translateX(-50%)",
            width: "80%",
            height: 4,
            backgroundColor: "rgba(148, 163, 184, 0.3)",
            borderRadius: 2,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              width: `${progress * 100}%`,
              height: "100%",
              backgroundColor: highlightColor,
              borderRadius: 2,
              transition: "width 0.1s linear",
            }}
          />
        </div>
      )}

      {/* Word count indicator for debugging */}
      {style === "karaoke" && process.env.NODE_ENV === "development" && (
        <div
          style={{
            position: "absolute",
            top: 20,
            left: 20,
            fontSize: 16,
            color: "white",
            backgroundColor: "rgba(0,0,0,0.5)",
            padding: "4px 8px",
            borderRadius: 4,
          }}
        >
          Frame: {frame} | Progress: {progress.toFixed(2)} | Words: {Math.floor(currentSegment.text.split(" ").length * progress)}/{currentSegment.text.split(" ").length}
        </div>
      )}
    </AbsoluteFill>
  );
};