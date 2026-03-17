import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from "remotion";

export interface DiagramProps {
  type: "flowchart" | "list" | "comparison" | "steps";
  items: Array<{ label: string; description?: string; icon?: string }>;
  animation: "slide_in" | "cascade" | "reveal";
  title?: string;
  accentColor?: string;
}

export const Diagram: React.FC<DiagramProps> = ({
  type,
  items,
  animation,
  title,
  accentColor = "#7c3aed",
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const backgroundColor = "#06060a";
  const textColor = "#e8eaf0";
  const mutedColor = "#94a3b8";

  const titleOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  const titleY = spring({ frame, fps, from: 40, to: 0, config: { damping: 12 } });

  const getItemAnimation = (index: number) => {
    const delay = animation === "cascade" ? index * 8 : 0;
    const startFrame = title ? 20 + delay : delay;

    switch (animation) {
      case "slide_in":
        return {
          opacity: interpolate(frame, [startFrame, startFrame + 15], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
          x: spring({
            frame: Math.max(0, frame - startFrame),
            fps,
            from: -100,
            to: 0,
            config: { damping: 12 },
          }),
          scale: 1,
        };

      case "cascade":
        return {
          opacity: interpolate(frame, [startFrame, startFrame + 12], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
          x: spring({
            frame: Math.max(0, frame - startFrame),
            fps,
            from: -60,
            to: 0,
            config: { damping: 10 },
          }),
          scale: spring({
            frame: Math.max(0, frame - startFrame),
            fps,
            from: 0.8,
            to: 1,
            config: { damping: 8 },
          }),
        };

      case "reveal":
        return {
          opacity: interpolate(frame, [startFrame, startFrame + 20], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
          x: 0,
          scale: spring({
            frame: Math.max(0, frame - startFrame),
            fps,
            from: 0.9,
            to: 1,
            config: { damping: 14 },
          }),
        };

      default:
        return { opacity: 1, x: 0, scale: 1 };
    }
  };

  const renderFlowchart = () => (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 40,
        maxWidth: width - 160,
        alignItems: "center",
      }}
    >
      {items.map((item, index) => {
        const { opacity, x, scale } = getItemAnimation(index);
        return (
          <div key={index} style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
            <div
              style={{
                opacity,
                transform: `translateX(${x}px) scale(${scale})`,
                padding: "24px 48px",
                backgroundColor: "#0d0d14",
                border: `2px solid ${accentColor}`,
                borderRadius: 16,
                textAlign: "center",
                minWidth: 300,
              }}
            >
              <div
                style={{
                  fontSize: 36,
                  fontWeight: 700,
                  color: textColor,
                  marginBottom: item.description ? 8 : 0,
                }}
              >
                {item.icon && <span style={{ marginRight: 12 }}>{item.icon}</span>}
                {item.label}
              </div>
              {item.description && (
                <div style={{ fontSize: 24, color: mutedColor, fontWeight: 500 }}>
                  {item.description}
                </div>
              )}
            </div>
            {index < items.length - 1 && (
              <div
                style={{
                  width: 2,
                  height: 30,
                  backgroundColor: accentColor,
                  margin: "20px 0",
                  opacity: interpolate(
                    frame,
                    [20 + index * 8 + 15, 20 + index * 8 + 25],
                    [0, 1],
                    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                  ),
                }}
              />
            )}
          </div>
        );
      })}
    </div>
  );

  const renderList = () => (
    <div style={{ display: "flex", flexDirection: "column", gap: 32, maxWidth: width - 160 }}>
      {items.map((item, index) => {
        const { opacity, x, scale } = getItemAnimation(index);
        return (
          <div
            key={index}
            style={{
              opacity,
              transform: `translateX(${x}px) scale(${scale})`,
              display: "flex",
              alignItems: "center",
              gap: 24,
            }}
          >
            <div
              style={{
                width: 16,
                height: 16,
                borderRadius: "50%",
                backgroundColor: accentColor,
                flexShrink: 0,
              }}
            />
            <div>
              <div style={{ fontSize: 42, fontWeight: 700, color: textColor }}>
                {item.icon && <span style={{ marginRight: 12 }}>{item.icon}</span>}
                {item.label}
              </div>
              {item.description && (
                <div style={{ fontSize: 28, color: mutedColor, marginTop: 8, fontWeight: 500 }}>
                  {item.description}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );

  const renderComparison = () => (
    <div style={{ display: "flex", gap: 80, maxWidth: width - 160 }}>
      <div style={{ flex: 1 }}>
        <h3
          style={{
            fontSize: 48,
            fontWeight: 800,
            color: "#ef4444",
            textAlign: "center",
            marginBottom: 40,
          }}
        >
          ❌ Before
        </h3>
        {items.slice(0, Math.ceil(items.length / 2)).map((item, index) => {
          const { opacity, x, scale } = getItemAnimation(index);
          return (
            <div
              key={index}
              style={{
                opacity,
                transform: `translateX(${x}px) scale(${scale})`,
                marginBottom: 24,
                padding: "16px 24px",
                backgroundColor: "#1a0f0f",
                border: "2px solid #ef4444",
                borderRadius: 12,
              }}
            >
              <div style={{ fontSize: 32, color: textColor, fontWeight: 600 }}>
                {item.label}
              </div>
            </div>
          );
        })}
      </div>
      <div style={{ flex: 1 }}>
        <h3
          style={{
            fontSize: 48,
            fontWeight: 800,
            color: "#10b981",
            textAlign: "center",
            marginBottom: 40,
          }}
        >
          ✅ After
        </h3>
        {items.slice(Math.ceil(items.length / 2)).map((item, index) => {
          const { opacity, x, scale } = getItemAnimation(index + Math.ceil(items.length / 2));
          return (
            <div
              key={index}
              style={{
                opacity,
                transform: `translateX(${x}px) scale(${scale})`,
                marginBottom: 24,
                padding: "16px 24px",
                backgroundColor: "#0f1a14",
                border: "2px solid #10b981",
                borderRadius: 12,
              }}
            >
              <div style={{ fontSize: 32, color: textColor, fontWeight: 600 }}>
                {item.label}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );

  const renderSteps = () => (
    <div style={{ display: "flex", flexDirection: "column", gap: 48, maxWidth: width - 160 }}>
      {items.map((item, index) => {
        const { opacity, x, scale } = getItemAnimation(index);
        return (
          <div
            key={index}
            style={{
              opacity,
              transform: `translateX(${x}px) scale(${scale})`,
              display: "flex",
              alignItems: "center",
              gap: 32,
            }}
          >
            <div
              style={{
                width: 80,
                height: 80,
                borderRadius: "50%",
                backgroundColor: accentColor,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
                fontSize: 36,
                fontWeight: 900,
                color: "white",
              }}
            >
              {index + 1}
            </div>
            <div>
              <div style={{ fontSize: 44, fontWeight: 700, color: textColor, marginBottom: 8 }}>
                {item.icon && <span style={{ marginRight: 12 }}>{item.icon}</span>}
                {item.label}
              </div>
              {item.description && (
                <div style={{ fontSize: 28, color: mutedColor, fontWeight: 500 }}>
                  {item.description}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );

  const renderDiagram = () => {
    switch (type) {
      case "flowchart":
        return renderFlowchart();
      case "list":
        return renderList();
      case "comparison":
        return renderComparison();
      case "steps":
        return renderSteps();
      default:
        return renderList();
    }
  };

  return (
    <AbsoluteFill style={{ backgroundColor }}>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          minHeight: height,
          padding: 80,
        }}
      >
        {title && (
          <h1
            style={{
              fontSize: 72,
              fontWeight: 900,
              color: textColor,
              textAlign: "center",
              marginBottom: 60,
              opacity: titleOpacity,
              transform: `translateY(${titleY}px)`,
            }}
          >
            {title}
          </h1>
        )}
        {renderDiagram()}
      </div>
    </AbsoluteFill>
  );
};