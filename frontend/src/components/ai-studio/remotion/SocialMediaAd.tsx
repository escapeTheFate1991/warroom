import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Img,
  Sequence,
} from "remotion";

export interface SocialMediaAdProps {
  hookText: string;
  bodyText: string;
  ctaText: string;
  backgroundImage: string;
  brandColor: string;
  backgroundColor: string;
}

export const SocialMediaAd: React.FC<SocialMediaAdProps> = ({
  hookText = "Stop scrolling!",
  bodyText = "This changes everything about how you work.",
  ctaText = "Try it free →",
  backgroundImage = "",
  brandColor = "#6366f1",
  backgroundColor = "#0f172a",
}) => {
  const { durationInFrames } = useVideoConfig();

  const hookDuration = Math.floor(durationInFrames * 0.3);
  const bodyDuration = Math.floor(durationInFrames * 0.4);
  const ctaDuration = durationInFrames - hookDuration - bodyDuration;

  return (
    <AbsoluteFill style={{ backgroundColor }}>
      {/* Background image overlay */}
      {backgroundImage && (
        <AbsoluteFill style={{ opacity: 0.15 }}>
          <Img
            src={backgroundImage}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        </AbsoluteFill>
      )}

      {/* Scene 1: Hook */}
      <Sequence from={0} durationInFrames={hookDuration}>
        <HookScene hookText={hookText} brandColor={brandColor} />
      </Sequence>

      {/* Scene 2: Body */}
      <Sequence from={hookDuration} durationInFrames={bodyDuration}>
        <BodyScene bodyText={bodyText} brandColor={brandColor} />
      </Sequence>

      {/* Scene 3: CTA */}
      <Sequence from={hookDuration + bodyDuration} durationInFrames={ctaDuration}>
        <CTAScene ctaText={ctaText} brandColor={brandColor} />
      </Sequence>
    </AbsoluteFill>
  );
};

const HookScene: React.FC<{ hookText: string; brandColor: string }> = ({
  hookText,
  brandColor,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const scale = spring({ frame, fps, from: 1.3, to: 1, config: { damping: 8, mass: 0.6 } });
  const opacity = interpolate(frame, [0, 8], [0, 1], { extrapolateRight: "clamp" });

  // Glitch effect on first few frames
  const glitchX = frame < 6 ? Math.sin(frame * 5) * 8 : 0;
  const glitchY = frame < 6 ? Math.cos(frame * 3) * 4 : 0;

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        padding: 60,
      }}
    >
      <h1
        style={{
          fontSize: 80,
          fontWeight: 900,
          color: "white",
          textAlign: "center",
          opacity,
          transform: `scale(${scale}) translate(${glitchX}px, ${glitchY}px)`,
          lineHeight: 1.1,
          textShadow: `0 0 40px ${brandColor}80`,
        }}
      >
        {hookText}
      </h1>
    </AbsoluteFill>
  );
};

const BodyScene: React.FC<{ bodyText: string; brandColor: string }> = ({
  bodyText,
  brandColor,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const opacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const y = spring({ frame, fps, from: 60, to: 0, config: { damping: 14 } });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        padding: 60,
      }}
    >
      <div
        style={{
          opacity,
          transform: `translateY(${y}px)`,
          maxWidth: "85%",
        }}
      >
        {/* Accent line */}
        <div
          style={{
            width: 60,
            height: 4,
            backgroundColor: brandColor,
            borderRadius: 2,
            marginBottom: 30,
          }}
        />
        <p
          style={{
            fontSize: 52,
            fontWeight: 600,
            color: "white",
            lineHeight: 1.3,
            textAlign: "left",
          }}
        >
          {bodyText}
        </p>
      </div>
    </AbsoluteFill>
  );
};

const CTAScene: React.FC<{ ctaText: string; brandColor: string }> = ({
  ctaText,
  brandColor,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const scale = spring({ frame, fps, from: 0, to: 1, config: { damping: 8, mass: 0.5 } });
  const bgOpacity = interpolate(frame, [0, 10], [0, 0.3], { extrapolateRight: "clamp" });

  // Pulsing glow
  const glowIntensity = interpolate(
    frame % 40,
    [0, 20, 40],
    [0.4, 0.8, 0.4],
    { extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        background: `radial-gradient(circle, ${brandColor}${Math.round(bgOpacity * 255).toString(16).padStart(2, "0")}, transparent 60%)`,
      }}
    >
      <div
        style={{
          transform: `scale(${scale})`,
          padding: "32px 56px",
          backgroundColor: brandColor,
          borderRadius: 20,
          boxShadow: `0 0 ${60 * glowIntensity}px ${brandColor}`,
        }}
      >
        <span
          style={{
            fontSize: 56,
            fontWeight: 800,
            color: "white",
            letterSpacing: -1,
          }}
        >
          {ctaText}
        </span>
      </div>
    </AbsoluteFill>
  );
};
