import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Img,
  Sequence,
} from "remotion";

export interface ProductShowcaseProps {
  images: string[];
  headline: string;
  features: string[];
  ctaText: string;
  brandColor: string;
  backgroundColor: string;
}

export const ProductShowcase: React.FC<ProductShowcaseProps> = ({
  images = [],
  headline = "Introducing Our Product",
  features = ["Feature One", "Feature Two", "Feature Three"],
  ctaText = "Learn More",
  brandColor = "#6366f1",
  backgroundColor = "#0f172a",
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames, width, height } = useVideoConfig();

  const headlineDuration = Math.floor(durationInFrames * 0.3);
  const featuresDuration = Math.floor(durationInFrames * 0.45);
  const ctaDuration = durationInFrames - headlineDuration - featuresDuration;

  return (
    <AbsoluteFill style={{ backgroundColor }}>
      {/* Scene 1: Headline + Product Image */}
      <Sequence from={0} durationInFrames={headlineDuration}>
        <HeadlineScene
          headline={headline}
          image={images[0]}
          brandColor={brandColor}
          fps={fps}
        />
      </Sequence>

      {/* Scene 2: Features */}
      <Sequence from={headlineDuration} durationInFrames={featuresDuration}>
        <FeaturesScene
          features={features}
          images={images.slice(1)}
          brandColor={brandColor}
          fps={fps}
        />
      </Sequence>

      {/* Scene 3: CTA */}
      <Sequence from={headlineDuration + featuresDuration} durationInFrames={ctaDuration}>
        <CTAScene
          ctaText={ctaText}
          brandColor={brandColor}
          fps={fps}
        />
      </Sequence>
    </AbsoluteFill>
  );
};

const HeadlineScene: React.FC<{
  headline: string;
  image?: string;
  brandColor: string;
  fps: number;
}> = ({ headline, image, brandColor, fps }) => {
  const frame = useCurrentFrame();

  const titleOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const titleY = spring({ frame, fps, from: 40, to: 0, config: { damping: 12 } });
  const imageScale = spring({ frame, fps, from: 0.8, to: 1, config: { damping: 15 } });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "column",
        gap: 40,
      }}
    >
      {image && (
        <div
          style={{
            transform: `scale(${imageScale})`,
            borderRadius: 16,
            overflow: "hidden",
            boxShadow: `0 20px 60px ${brandColor}40`,
          }}
        >
          <Img src={image} style={{ maxWidth: 600, maxHeight: 400, objectFit: "cover" }} />
        </div>
      )}
      <h1
        style={{
          fontSize: 72,
          fontWeight: 800,
          color: "white",
          textAlign: "center",
          opacity: titleOpacity,
          transform: `translateY(${titleY}px)`,
          maxWidth: "80%",
          lineHeight: 1.1,
        }}
      >
        {headline}
      </h1>
      <div
        style={{
          width: 80,
          height: 4,
          backgroundColor: brandColor,
          borderRadius: 2,
          opacity: titleOpacity,
        }}
      />
    </AbsoluteFill>
  );
};

const FeaturesScene: React.FC<{
  features: string[];
  images: string[];
  brandColor: string;
  fps: number;
}> = ({ features, images, brandColor, fps }) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        padding: 80,
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 32, maxWidth: 800 }}>
        {features.map((feature, i) => {
          const delay = i * 12;
          const opacity = interpolate(frame, [delay, delay + 15], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          const x = spring({ frame: Math.max(0, frame - delay), fps, from: -60, to: 0, config: { damping: 12 } });

          return (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 20,
                opacity,
                transform: `translateX(${x}px)`,
              }}
            >
              <div
                style={{
                  width: 12,
                  height: 12,
                  borderRadius: "50%",
                  backgroundColor: brandColor,
                  flexShrink: 0,
                }}
              />
              <span
                style={{
                  fontSize: 40,
                  fontWeight: 600,
                  color: "white",
                }}
              >
                {feature}
              </span>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const CTAScene: React.FC<{
  ctaText: string;
  brandColor: string;
  fps: number;
}> = ({ ctaText, brandColor, fps }) => {
  const frame = useCurrentFrame();

  const scale = spring({ frame, fps, from: 0.5, to: 1, config: { damping: 10, mass: 0.5 } });
  const opacity = interpolate(frame, [0, 10], [0, 1], { extrapolateRight: "clamp" });

  const pulseScale = interpolate(
    frame % 30,
    [0, 15, 30],
    [1, 1.05, 1],
    { extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        background: `radial-gradient(circle at center, ${brandColor}20, transparent 70%)`,
      }}
    >
      <div
        style={{
          opacity,
          transform: `scale(${scale * pulseScale})`,
          padding: "24px 64px",
          backgroundColor: brandColor,
          borderRadius: 16,
          boxShadow: `0 10px 40px ${brandColor}60`,
        }}
      >
        <span
          style={{
            fontSize: 48,
            fontWeight: 700,
            color: "white",
          }}
        >
          {ctaText}
        </span>
      </div>
    </AbsoluteFill>
  );
};
