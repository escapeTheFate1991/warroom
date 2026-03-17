import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Img,
} from "remotion";

export interface SplitScreenProps {
  leftLabel: string;
  rightLabel: string;
  leftContent: string; // text or image URL
  rightContent: string;
  splitType: "vertical" | "horizontal" | "wipe";
  leftStyle?: "grayscale" | "normal" | "blur";
  rightStyle?: "color" | "normal" | "glow";
}

export const SplitScreen: React.FC<SplitScreenProps> = ({
  leftLabel,
  rightLabel,
  leftContent,
  rightContent,
  splitType,
  leftStyle = "normal",
  rightStyle = "normal",
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const backgroundColor = "#06060a";
  const textColor = "#e8eaf0";

  const labelOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  const labelY = spring({ frame, fps, from: 30, to: 0, config: { damping: 12 } });

  const getWipeProgress = () => {
    if (splitType !== "wipe") return 1;
    return interpolate(frame, [30, 90], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  };

  const wipeProgress = getWipeProgress();

  const isImage = (content: string) => {
    return /\.(jpg|jpeg|png|gif|webp)$/i.test(content) || content.startsWith("http");
  };

  const getContentStyle = (side: "left" | "right", style: string) => {
    const baseStyle: React.CSSProperties = {
      width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center",
      padding: 40, fontSize: 48, fontWeight: 600, color: textColor, textAlign: "center", lineHeight: 1.3,
    };
    const filters = {
      grayscale: "grayscale(100%) brightness(0.7)",
      blur: "blur(4px) brightness(0.6)",
      color: "saturate(1.3) brightness(1.1)",
      glow: "brightness(1.2)",
    };
    return { 
      ...baseStyle, 
      filter: filters[style as keyof typeof filters] || "none",
      boxShadow: style === "glow" && side === "right" ? "0 0 80px #7c3aed60" : undefined,
    };
  };

  const renderContent = (content: string, side: "left" | "right", style: string) => {
    const contentStyle = getContentStyle(side, style);

    if (isImage(content)) {
      return (
        <div style={contentStyle}>
          <Img
            src={content}
            style={{
              maxWidth: "90%",
              maxHeight: "80%",
              objectFit: "cover",
              borderRadius: 16,
              filter: contentStyle.filter,
            }}
          />
        </div>
      );
    }

    return <div style={contentStyle}>{content}</div>;
  };

  const renderVerticalSplit = () => (
    <AbsoluteFill>
      {/* Left side */}
      <AbsoluteFill style={{ right: "50%" }}>
        <div style={{ backgroundColor: "#0d0d14", height: "100%" }}>
          {renderContent(leftContent, "left", leftStyle)}
        </div>
      </AbsoluteFill>

      {/* Right side */}
      <AbsoluteFill style={{ left: "50%" }}>
        <div style={{ backgroundColor: "#0d0d14", height: "100%" }}>
          {renderContent(rightContent, "right", rightStyle)}
        </div>
      </AbsoluteFill>

      {/* Divider line */}
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: 0,
          bottom: 0,
          width: 4,
          backgroundColor: "#7c3aed",
          transform: "translateX(-50%)",
        }}
      />
    </AbsoluteFill>
  );

  const renderHorizontalSplit = () => (
    <AbsoluteFill>
      {/* Top side */}
      <AbsoluteFill style={{ bottom: "50%" }}>
        <div style={{ backgroundColor: "#0d0d14", height: "100%" }}>
          {renderContent(leftContent, "left", leftStyle)}
        </div>
      </AbsoluteFill>

      {/* Bottom side */}
      <AbsoluteFill style={{ top: "50%" }}>
        <div style={{ backgroundColor: "#0d0d14", height: "100%" }}>
          {renderContent(rightContent, "right", rightStyle)}
        </div>
      </AbsoluteFill>

      {/* Divider line */}
      <div
        style={{
          position: "absolute",
          top: "50%",
          left: 0,
          right: 0,
          height: 4,
          backgroundColor: "#7c3aed",
          transform: "translateY(-50%)",
        }}
      />
    </AbsoluteFill>
  );

  const renderWipe = () => (
    <AbsoluteFill>
      {/* Left content (before) - always visible */}
      <AbsoluteFill>
        <div style={{ backgroundColor: "#0d0d14", height: "100%" }}>
          {renderContent(leftContent, "left", leftStyle)}
        </div>
      </AbsoluteFill>

      {/* Right content (after) - wipes in from left to right */}
      <AbsoluteFill
        style={{
          clipPath: `polygon(0 0, ${wipeProgress * 100}% 0, ${wipeProgress * 100}% 100%, 0 100%)`,
        }}
      >
        <div style={{ backgroundColor: "#0d0d14", height: "100%" }}>
          {renderContent(rightContent, "right", rightStyle)}
        </div>
      </AbsoluteFill>

      {/* Wipe edge effect */}
      {wipeProgress > 0 && wipeProgress < 1 && (
        <div
          style={{
            position: "absolute",
            left: `${wipeProgress * 100}%`,
            top: 0,
            bottom: 0,
            width: 8,
            background: "linear-gradient(90deg, #7c3aed, transparent)",
            transform: "translateX(-50%)",
            boxShadow: "0 0 20px #7c3aed",
          }}
        />
      )}
    </AbsoluteFill>
  );

  const renderSplit = () => {
    switch (splitType) {
      case "vertical":
        return renderVerticalSplit();
      case "horizontal":
        return renderHorizontalSplit();
      case "wipe":
        return renderWipe();
      default:
        return renderVerticalSplit();
    }
  };

  return (
    <AbsoluteFill style={{ backgroundColor }}>
      {renderSplit()}

      {/* Labels */}
      {splitType !== "wipe" && (
        <>
          <div
            style={{
              position: "absolute",
              top: 40,
              left: splitType === "vertical" ? "25%" : 40,
              fontSize: 40,
              fontWeight: 800,
              color: "#ef4444",
              opacity: labelOpacity,
              transform: `${splitType === "vertical" ? "translateX(-50%)" : ""} translateY(${labelY}px)`,
              backgroundColor: "#1a0f0fcc",
              padding: "12px 24px",
              borderRadius: 12,
              border: "2px solid #ef4444",
            }}
          >
            {leftLabel}
          </div>
          <div
            style={{
              position: "absolute",
              top: 40,
              right: splitType === "vertical" ? "25%" : 40,
              fontSize: 40,
              fontWeight: 800,
              color: "#10b981",
              opacity: labelOpacity,
              transform: `${splitType === "vertical" ? "translateX(50%)" : ""} translateY(${labelY}px)`,
              backgroundColor: "#0f1a14cc",
              padding: "12px 24px",
              borderRadius: 12,
              border: "2px solid #10b981",
            }}
          >
            {rightLabel}
          </div>
        </>
      )}

      {/* Wipe labels */}
      {splitType === "wipe" && (
        <>
          <div
            style={{
              position: "absolute",
              top: 40,
              left: 40,
              fontSize: 40,
              fontWeight: 800,
              color: "#ef4444",
              opacity: labelOpacity * (1 - wipeProgress),
              transform: `translateY(${labelY}px)`,
              backgroundColor: "#1a0f0fcc",
              padding: "12px 24px",
              borderRadius: 12,
              border: "2px solid #ef4444",
            }}
          >
            {leftLabel}
          </div>
          <div
            style={{
              position: "absolute",
              top: 40,
              right: 40,
              fontSize: 40,
              fontWeight: 800,
              color: "#10b981",
              opacity: labelOpacity * wipeProgress,
              transform: `translateY(${labelY}px)`,
              backgroundColor: "#0f1a14cc",
              padding: "12px 24px",
              borderRadius: 12,
              border: "2px solid #10b981",
            }}
          >
            {rightLabel}
          </div>
        </>
      )}
    </AbsoluteFill>
  );
};