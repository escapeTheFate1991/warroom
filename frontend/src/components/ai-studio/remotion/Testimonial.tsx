import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Img,
  Sequence,
} from "remotion";

export interface TestimonialProps {
  quote: string;
  authorName: string;
  authorTitle: string;
  avatarUrl: string;
  brandLogo: string;
  brandColor: string;
  backgroundColor: string;
  tagline: string;
}

export const Testimonial: React.FC<TestimonialProps> = ({
  quote = "This product completely transformed our workflow.",
  authorName = "Jane Smith",
  authorTitle = "CEO at TechCo",
  avatarUrl = "",
  brandLogo = "",
  brandColor = "#6366f1",
  backgroundColor = "#0f172a",
  tagline = "Trusted by 1000+ teams",
}) => {
  const { durationInFrames } = useVideoConfig();

  const quoteDuration = Math.floor(durationInFrames * 0.5);
  const authorDuration = Math.floor(durationInFrames * 0.3);
  const brandDuration = durationInFrames - quoteDuration - authorDuration;

  return (
    <AbsoluteFill style={{ backgroundColor }}>
      {/* Decorative gradient */}
      <AbsoluteFill
        style={{
          background: `linear-gradient(135deg, ${brandColor}15, transparent 50%, ${brandColor}10)`,
        }}
      />

      {/* Scene 1: Quote */}
      <Sequence from={0} durationInFrames={quoteDuration}>
        <QuoteScene quote={quote} brandColor={brandColor} />
      </Sequence>

      {/* Scene 2: Author */}
      <Sequence from={quoteDuration} durationInFrames={authorDuration}>
        <AuthorScene
          authorName={authorName}
          authorTitle={authorTitle}
          avatarUrl={avatarUrl}
          brandColor={brandColor}
        />
      </Sequence>

      {/* Scene 3: Brand */}
      <Sequence from={quoteDuration + authorDuration} durationInFrames={brandDuration}>
        <BrandScene
          brandLogo={brandLogo}
          tagline={tagline}
          brandColor={brandColor}
        />
      </Sequence>
    </AbsoluteFill>
  );
};

const QuoteScene: React.FC<{ quote: string; brandColor: string }> = ({
  quote,
  brandColor,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const opacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  const y = spring({ frame, fps, from: 30, to: 0, config: { damping: 14, mass: 0.8 } });

  // Quote mark animation
  const quoteMarkScale = spring({ frame, fps, from: 0, to: 1, config: { damping: 10 } });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        padding: 100,
      }}
    >
      <div style={{ maxWidth: 1200, textAlign: "center", position: "relative" }}>
        {/* Large decorative quote mark */}
        <span
          style={{
            position: "absolute",
            top: -60,
            left: -20,
            fontSize: 200,
            fontWeight: 900,
            color: brandColor,
            opacity: 0.2,
            transform: `scale(${quoteMarkScale})`,
            lineHeight: 1,
          }}
        >
          "
        </span>

        <p
          style={{
            fontSize: 48,
            fontWeight: 500,
            color: "white",
            lineHeight: 1.4,
            opacity,
            transform: `translateY(${y}px)`,
            fontStyle: "italic",
            position: "relative",
            zIndex: 1,
          }}
        >
          &ldquo;{quote}&rdquo;
        </p>
      </div>
    </AbsoluteFill>
  );
};

const AuthorScene: React.FC<{
  authorName: string;
  authorTitle: string;
  avatarUrl: string;
  brandColor: string;
}> = ({ authorName, authorTitle, avatarUrl, brandColor }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const opacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const scale = spring({ frame, fps, from: 0.8, to: 1, config: { damping: 12 } });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        gap: 30,
      }}
    >
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 20,
          opacity,
          transform: `scale(${scale})`,
        }}
      >
        {/* Avatar */}
        <div
          style={{
            width: 120,
            height: 120,
            borderRadius: "50%",
            border: `4px solid ${brandColor}`,
            overflow: "hidden",
            backgroundColor: `${brandColor}30`,
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          {avatarUrl ? (
            <Img
              src={avatarUrl}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          ) : (
            <span style={{ fontSize: 48, color: brandColor, fontWeight: 700 }}>
              {authorName.charAt(0).toUpperCase()}
            </span>
          )}
        </div>

        {/* Name & Title */}
        <div style={{ textAlign: "center" }}>
          <h2
            style={{
              fontSize: 42,
              fontWeight: 700,
              color: "white",
              margin: 0,
            }}
          >
            {authorName}
          </h2>
          <p
            style={{
              fontSize: 24,
              color: `${brandColor}cc`,
              marginTop: 8,
              fontWeight: 500,
            }}
          >
            {authorTitle}
          </p>
        </div>
      </div>
    </AbsoluteFill>
  );
};

const BrandScene: React.FC<{
  brandLogo: string;
  tagline: string;
  brandColor: string;
}> = ({ brandLogo, tagline, brandColor }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const opacity = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: "clamp" });
  const scale = spring({ frame, fps, from: 0.9, to: 1, config: { damping: 12, mass: 0.6 } });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        gap: 30,
        background: `radial-gradient(circle at center, ${brandColor}15, transparent 60%)`,
      }}
    >
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 24,
          opacity,
          transform: `scale(${scale})`,
        }}
      >
        {brandLogo && (
          <Img
            src={brandLogo}
            style={{ maxWidth: 200, maxHeight: 80, objectFit: "contain" }}
          />
        )}
        <p
          style={{
            fontSize: 36,
            fontWeight: 600,
            color: "white",
            textAlign: "center",
          }}
        >
          {tagline}
        </p>
        <div
          style={{
            width: 60,
            height: 3,
            backgroundColor: brandColor,
            borderRadius: 2,
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
