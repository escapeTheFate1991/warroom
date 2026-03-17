import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from "remotion";

export interface CodeWalkthroughProps {
  code: string;
  language?: string;
  highlightLines?: number[];
  animation: "typewriter" | "reveal" | "highlight_cascade";
  theme?: "dark" | "monokai" | "github_dark";
  title?: string;
}

export const CodeWalkthrough: React.FC<CodeWalkthroughProps> = ({
  code,
  language = "javascript",
  highlightLines = [],
  animation,
  theme = "dark",
  title,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const backgroundColor = "#06060a";

  const getThemeColors = () => {
    switch (theme) {
      case "monokai":
        return {
          background: "#272822",
          text: "#f8f8f2",
          keyword: "#f92672",
          string: "#e6db74",
          comment: "#75715e",
          number: "#ae81ff",
          function: "#66d9ef",
        };
      case "github_dark":
        return {
          background: "#0d1117",
          text: "#c9d1d9",
          keyword: "#ff7b72",
          string: "#a5d6ff",
          comment: "#8b949e",
          number: "#79c0ff",
          function: "#d2a8ff",
        };
      case "dark":
      default:
        return {
          background: "#0d0d14",
          text: "#e8eaf0",
          keyword: "#7c3aed",
          string: "#10b981",
          comment: "#94a3b8",
          number: "#f59e0b",
          function: "#06b6d4",
        };
    }
  };

  const colors = getThemeColors();
  const lines = code.split("\n");

  const titleOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  const titleY = spring({ frame, fps, from: 30, to: 0, config: { damping: 12 } });

  const highlightSyntax = (line: string) => {
    // Simple syntax highlighting patterns
    const patterns = [
      { regex: /(\/\/.*|\/\*[\s\S]*?\*\/|#.*)/g, color: colors.comment, weight: 500 },
      { regex: /(function|const|let|var|if|else|for|while|return|import|export|class|extends)/g, color: colors.keyword, weight: 700 },
      { regex: /(['"`])(?:(?!\1)[^\\]|\\.)*(\\.|(?=\1))/g, color: colors.string, weight: 500 },
      { regex: /\b\d+\.?\d*\b/g, color: colors.number, weight: 600 },
      { regex: /\b([a-zA-Z_]\w*)\s*(?=\()/g, color: colors.function, weight: 600 },
    ];

    let highlightedLine = line;
    const spans: Array<{ start: number; end: number; color: string; weight: number }> = [];

    patterns.forEach((pattern) => {
      let match;
      const regex = new RegExp(pattern.regex.source, pattern.regex.flags);
      while ((match = regex.exec(line)) !== null) {
        spans.push({
          start: match.index,
          end: match.index + match[0].length,
          color: pattern.color,
          weight: pattern.weight,
        });
      }
    });

    // Sort spans by start position and merge overlapping
    spans.sort((a, b) => a.start - b.start);
    const mergedSpans = spans.reduce((acc, span) => {
      const lastSpan = acc[acc.length - 1];
      if (lastSpan && span.start <= lastSpan.end) {
        lastSpan.end = Math.max(lastSpan.end, span.end);
        return acc;
      }
      return [...acc, span];
    }, [] as typeof spans);

    if (mergedSpans.length === 0) {
      return <span style={{ color: colors.text }}>{line}</span>;
    }

    const elements: React.ReactNode[] = [];
    let currentPos = 0;

    mergedSpans.forEach((span, index) => {
      // Add text before span
      if (currentPos < span.start) {
        elements.push(
          <span key={`text-${index}`} style={{ color: colors.text }}>
            {line.slice(currentPos, span.start)}
          </span>
        );
      }

      // Add highlighted span
      elements.push(
        <span
          key={`highlight-${index}`}
          style={{ color: span.color, fontWeight: span.weight }}
        >
          {line.slice(span.start, span.end)}
        </span>
      );

      currentPos = span.end;
    });

    // Add remaining text
    if (currentPos < line.length) {
      elements.push(
        <span key="text-end" style={{ color: colors.text }}>
          {line.slice(currentPos)}
        </span>
      );
    }

    return <>{elements}</>;
  };

  const getLineAnimation = (lineIndex: number) => {
    const lineNumber = lineIndex + 1;
    const isHighlighted = highlightLines.includes(lineNumber);

    switch (animation) {
      case "typewriter":
        const totalChars = lines.slice(0, lineIndex + 1).join("").length;
        const typedChars = interpolate(frame, [0, 120], [0, code.length], {
          extrapolateRight: "clamp",
        });
        const lineStartChar = lines.slice(0, lineIndex).join("").length;
        const lineChars = lines[lineIndex].length;
        
        if (typedChars < lineStartChar) {
          return { opacity: 0, content: "", highlight: false };
        }
        
        const charsInLine = Math.max(0, typedChars - lineStartChar);
        const content = lines[lineIndex].slice(0, Math.min(charsInLine, lineChars));
        
        return {
          opacity: 1,
          content,
          highlight: false,
        };

      case "reveal":
        const delay = title ? 30 : 0;
        return {
          opacity: interpolate(frame, [delay + lineIndex * 3, delay + lineIndex * 3 + 15], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
          content: lines[lineIndex],
          highlight: false,
        };

      case "highlight_cascade":
        const revealDelay = title ? 30 : 0;
        const highlightDelay = revealDelay + lines.length * 3 + 20;
        
        const lineOpacity = interpolate(frame, [revealDelay + lineIndex * 2, revealDelay + lineIndex * 2 + 10], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });

        let highlightOpacity = 0;
        if (isHighlighted) {
          const highlightIndex = highlightLines.indexOf(lineNumber);
          highlightOpacity = interpolate(
            frame,
            [highlightDelay + highlightIndex * 8, highlightDelay + highlightIndex * 8 + 15],
            [0, 1],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
          );
        }

        return {
          opacity: lineOpacity,
          content: lines[lineIndex],
          highlight: highlightOpacity > 0,
          highlightOpacity,
        };

      default:
        return {
          opacity: 1,
          content: lines[lineIndex],
          highlight: false,
        };
    }
  };

  return (
    <AbsoluteFill style={{ backgroundColor }}>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          padding: 60,
          height: "100%",
          maxWidth: width,
        }}
      >
        {/* Title */}
        {title && (
          <h1
            style={{
              fontSize: 56,
              fontWeight: 900,
              color: "#e8eaf0",
              marginBottom: 40,
              opacity: titleOpacity,
              transform: `translateY(${titleY}px)`,
              textAlign: "center",
            }}
          >
            {title}
          </h1>
        )}

        {/* Code Container */}
        <div
          style={{
            flex: 1,
            backgroundColor: colors.background,
            borderRadius: 16,
            padding: 40,
            fontFamily: "'Fira Code', 'Monaco', 'Menlo', monospace",
            fontSize: 24,
            lineHeight: 1.6,
            overflow: "hidden",
            border: "2px solid #7c3aed",
            position: "relative",
          }}
        >
          {/* Language indicator */}
          <div
            style={{
              position: "absolute",
              top: 16,
              right: 20,
              fontSize: 18,
              fontWeight: 600,
              color: "#7c3aed",
              backgroundColor: "rgba(124,58,237,0.1)",
              padding: "6px 12px",
              borderRadius: 8,
              opacity: interpolate(frame, [20, 40], [0, 1], { extrapolateRight: "clamp" }),
            }}
          >
            {language}
          </div>

          {/* Line numbers */}
          <div style={{ display: "flex", gap: 24, marginTop: 20 }}>
            <div style={{ color: colors.comment, fontSize: 20, minWidth: 60 }}>
              {lines.map((_, index) => {
                const lineAnim = getLineAnimation(index);
                return (
                  <div
                    key={index}
                    style={{
                      opacity: lineAnim.opacity * 0.7,
                      textAlign: "right",
                      lineHeight: 1.6,
                      fontWeight: 500,
                    }}
                  >
                    {index + 1}
                  </div>
                );
              })}
            </div>

            {/* Code lines */}
            <div style={{ flex: 1 }}>
              {lines.map((line, index) => {
                const { opacity, content, highlight, highlightOpacity } = getLineAnimation(index);

                return (
                  <div
                    key={index}
                    style={{
                      opacity,
                      lineHeight: 1.6,
                      position: "relative",
                      padding: "2px 8px",
                      borderRadius: 6,
                      backgroundColor: highlight
                        ? `rgba(124,58,237,${0.2 * (highlightOpacity || 1)})`
                        : "transparent",
                      border: highlight
                        ? `2px solid rgba(124,58,237,${highlightOpacity || 1})`
                        : "2px solid transparent",
                      transition: "all 0.3s ease",
                      minHeight: "1.6em",
                    }}
                  >
                    {highlightSyntax(content)}
                    {animation === "typewriter" && content && content.length < line.length && (
                      <span
                        style={{
                          color: colors.text,
                          opacity: Math.sin(frame * 0.5) > 0 ? 1 : 0,
                          marginLeft: 2,
                        }}
                      >
                        |
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Highlight indicators */}
          {animation === "highlight_cascade" && highlightLines.length > 0 && (
            <div
              style={{
                position: "absolute",
                bottom: 20,
                left: 20,
                right: 20,
                display: "flex",
                gap: 8,
                justifyContent: "center",
              }}
            >
              {highlightLines.map((lineNum, index) => {
                const delay = (title ? 30 : 0) + lines.length * 3 + 20 + index * 8;
                const opacity = interpolate(frame, [delay, delay + 10], [0, 1], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                });

                return (
                  <div
                    key={lineNum}
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      backgroundColor: "#7c3aed",
                      opacity,
                    }}
                  />
                );
              })}
            </div>
          )}
        </div>
      </div>
    </AbsoluteFill>
  );
};