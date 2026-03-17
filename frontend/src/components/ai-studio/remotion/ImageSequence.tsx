import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Img,
  Sequence,
} from "remotion";

export interface ImageSequenceProps {
  images: string[]; // URLs
  captions?: string[];
  effect: "ken_burns" | "slide" | "zoom_pulse";
  durationPerImage?: number; // frames
  overlayText?: string;
}

export const ImageSequence: React.FC<ImageSequenceProps> = ({
  images,
  captions = [],
  effect,
  durationPerImage = 60,
  overlayText,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames, width, height } = useVideoConfig();
  const backgroundColor = "#06060a";
  const textColor = "#e8eaf0";

  const totalImages = images.length;
  const actualDuration = durationPerImage || Math.floor(durationInFrames / totalImages);

  const getCurrentImageIndex = () => {
    return Math.floor(frame / actualDuration) % totalImages;
  };

  const getImageProgress = () => {
    return (frame % actualDuration) / actualDuration;
  };

  const currentIndex = getCurrentImageIndex();
  const progress = getImageProgress();

  const getKenBurnsTransform = (imageIndex: number, progress: number) => {
    const patterns = [
      { zoom: [1, 1.2], pan: [0, -50] }, { zoom: [1.1, 1], pan: [-30, 30] },
      { zoom: [1, 1.15], pan: [40, -20] }, { zoom: [1.08, 1], pan: [0, 0] },
    ];
    const pattern = patterns[imageIndex % patterns.length];
    return {
      scale: interpolate(progress, [0, 1], pattern.zoom, { extrapolateRight: "clamp" }),
      panX: interpolate(progress, [0, 1], [pattern.pan[0], pattern.pan[1]], { extrapolateRight: "clamp" }),
      panY: interpolate(progress, [0, 1], [0, pattern.pan[1] || 0], { extrapolateRight: "clamp" }),
    };
  };

  const getSlideTransform = (imageIndex: number, progress: number) => ({
    currentX: interpolate(progress, [0, 0.1, 1], [100, 0, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
    prevX: interpolate(progress, [0.9, 1], [0, -100], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
  });

  const getZoomPulseTransform = (progress: number) => ({
    scale: interpolate(Math.sin(progress * Math.PI * 4) * 0.5 + 0.5, [0, 1], [1, 1.1], { extrapolateRight: "clamp" }),
  });

  const renderKenBurns = () => (
    <AbsoluteFill>
      {images.map((image, index) => {
        const isActive = index === currentIndex;
        if (!isActive) return null;

        const { scale, panX, panY } = getKenBurnsTransform(index, progress);

        return (
          <AbsoluteFill key={index}>
            <div
              style={{
                width: "100%",
                height: "100%",
                overflow: "hidden",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Img
                src={image}
                style={{
                  width: "100%",
                  height: "100%",
                  objectFit: "cover",
                  transform: `scale(${scale}) translate(${panX}px, ${panY}px)`,
                }}
              />
            </div>
          </AbsoluteFill>
        );
      })}
    </AbsoluteFill>
  );

  const renderSlide = () => {
    const { currentX, prevX } = getSlideTransform(currentIndex, progress);
    const previousIndex = currentIndex > 0 ? currentIndex - 1 : totalImages - 1;

    return (
      <AbsoluteFill>
        {/* Previous image sliding out */}
        {progress > 0.9 && (
          <AbsoluteFill>
            <div
              style={{
                width: "100%",
                height: "100%",
                transform: `translateX(${prevX}%)`,
              }}
            >
              <Img
                src={images[previousIndex]}
                style={{
                  width: "100%",
                  height: "100%",
                  objectFit: "cover",
                }}
              />
            </div>
          </AbsoluteFill>
        )}

        {/* Current image sliding in */}
        <AbsoluteFill>
          <div
            style={{
              width: "100%",
              height: "100%",
              transform: `translateX(${currentX}%)`,
            }}
          >
            <Img
              src={images[currentIndex]}
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
              }}
            />
          </div>
        </AbsoluteFill>
      </AbsoluteFill>
    );
  };

  const renderZoomPulse = () => {
    const { scale } = getZoomPulseTransform(progress);

    return (
      <AbsoluteFill>
        {images.map((image, index) => {
          const isActive = index === currentIndex;
          if (!isActive) return null;

          return (
            <AbsoluteFill key={index}>
              <div
                style={{
                  width: "100%",
                  height: "100%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  overflow: "hidden",
                }}
              >
                <Img
                  src={image}
                  style={{
                    width: "100%",
                    height: "100%",
                    objectFit: "cover",
                    transform: `scale(${scale})`,
                  }}
                />
              </div>
            </AbsoluteFill>
          );
        })}
      </AbsoluteFill>
    );
  };

  const renderEffect = () => {
    switch (effect) {
      case "ken_burns":
        return renderKenBurns();
      case "slide":
        return renderSlide();
      case "zoom_pulse":
        return renderZoomPulse();
      default:
        return renderKenBurns();
    }
  };

  const captionOpacity = interpolate(
    progress,
    [0, 0.1, 0.8, 1],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const overlayOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor }}>
      {/* Image effect */}
      {renderEffect()}

      {/* Vignette overlay */}
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(circle at center, transparent 30%, rgba(6,6,10,0.4) 70%, rgba(6,6,10,0.8) 100%)",
        }}
      />

      {/* Caption for current image */}
      {captions[currentIndex] && (
        <div
          style={{
            position: "absolute",
            bottom: 100,
            left: 60,
            right: 60,
            fontSize: 36,
            fontWeight: 600,
            color: textColor,
            textAlign: "center",
            padding: "20px 40px",
            backgroundColor: "rgba(6,6,10,0.8)",
            borderRadius: 16,
            opacity: captionOpacity,
            lineHeight: 1.4,
          }}
        >
          {captions[currentIndex]}
        </div>
      )}

      {/* Persistent overlay text */}
      {overlayText && (
        <div
          style={{
            position: "absolute",
            top: 60,
            left: 60,
            right: 60,
            fontSize: 48,
            fontWeight: 800,
            color: textColor,
            textAlign: "center",
            opacity: overlayOpacity,
            textShadow: "0 4px 20px rgba(0,0,0,0.8)",
          }}
        >
          {overlayText}
        </div>
      )}

      {/* Progress dots */}
      <div
        style={{
          position: "absolute",
          bottom: 40,
          left: "50%",
          transform: "translateX(-50%)",
          display: "flex",
          gap: 12,
        }}
      >
        {images.map((_, index) => (
          <div
            key={index}
            style={{
              width: 12,
              height: 12,
              borderRadius: "50%",
              backgroundColor: index === currentIndex ? "#7c3aed" : "rgba(148, 163, 184, 0.4)",
              transition: "background-color 0.3s ease",
            }}
          />
        ))}
      </div>
    </AbsoluteFill>
  );
};