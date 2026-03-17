import React from 'react';
import { AbsoluteFill, Sequence, OffthreadVideo, Img, useCurrentFrame } from 'remotion';
import { EditingDNA, Layer } from './EditingDNASchema';

export interface UniversalTemplateProps {
  dna: EditingDNA;
}

interface LayerRendererProps {
  layer: Layer;
  frame: number;
}

const LayerRenderer: React.FC<LayerRendererProps> = ({ layer, frame }) => {
  const style: React.CSSProperties = {
    position: 'absolute',
    top: layer.position.top,
    bottom: layer.position.bottom,
    left: layer.position.left ?? 0,
    right: layer.position.right,
    height: layer.position.height,
    width: layer.position.width,
    zIndex: layer.z_index,
    overflow: 'hidden',
  };

  // Apply effects
  const effects = layer.effects || [];
  if (effects.includes('subtle_zoom_in')) {
    const scale = 1 + (frame / 1000) * 0.1; // Gradual zoom in
    style.transform = `scale(${scale})`;
  }
  
  if (effects.includes('fade_in')) {
    const opacity = Math.min(1, frame / 30); // Fade in over 30 frames
    style.opacity = opacity;
  }

  // Apply masks
  if (layer.mask === 'rounded_corners_lg') {
    style.borderRadius = '12px';
  } else if (layer.mask === 'rounded_corners_sm') {
    style.borderRadius = '4px';
  } else if (layer.mask === 'circle') {
    style.borderRadius = '50%';
  }

  // Render content based on source_type
  const renderContent = () => {
    switch (layer.source_type) {
      case 'video':
      case 'veo_generated_character':
      case 'veo_generated_environment':
        if (layer.source_url) {
          return (
            <OffthreadVideo
              src={layer.source_url}
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
          );
        }
        return (
          <div
            style={{
              width: '100%',
              height: '100%',
              backgroundColor: '#1a1a1a',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              fontSize: '14px',
              textAlign: 'center',
            }}
          >
            {layer.role} (Video)
          </div>
        );

      case 'image':
        if (layer.source_url) {
          return (
            <Img
              src={layer.source_url}
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
          );
        }
        return (
          <div
            style={{
              width: '100%',
              height: '100%',
              backgroundColor: '#2a2a2a',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              fontSize: '14px',
              textAlign: 'center',
            }}
          >
            {layer.role} (Image)
          </div>
        );

      case 'text_overlay':
        return (
          <div
            style={{
              width: '100%',
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              fontSize: '24px',
              fontWeight: 'bold',
              textAlign: 'center',
              textShadow: '2px 2px 4px rgba(0,0,0,0.8)',
              padding: '16px',
            }}
          >
            {layer.role}
          </div>
        );

      case 'caption':
        return (
          <div
            style={{
              width: '100%',
              height: '100%',
              display: 'flex',
              alignItems: 'flex-end',
              justifyContent: 'center',
              color: '#fff',
              fontSize: '18px',
              fontWeight: 'bold',
              textAlign: 'center',
              backgroundColor: 'rgba(0,0,0,0.6)',
              padding: '12px',
            }}
          >
            {layer.role}
          </div>
        );

      case 'empty':
        return null;

      default:
        return (
          <div
            style={{
              width: '100%',
              height: '100%',
              backgroundColor: '#3a3a3a',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              fontSize: '12px',
              textAlign: 'center',
            }}
          >
            {layer.role}
          </div>
        );
    }
  };

  return (
    <div style={style}>
      {renderContent()}
    </div>
  );
};

export const UniversalTemplate: React.FC<UniversalTemplateProps> = ({ dna }) => {
  const frame = useCurrentFrame();

  // Sort layers by z_index to ensure proper rendering order
  const sortedLayers = [...dna.layers].sort((a, b) => a.z_index - b.z_index);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#000',
        aspectRatio: dna.meta.aspect_ratio === '9:16' ? '9/16' : 
                     dna.meta.aspect_ratio === '16:9' ? '16/9' : '1/1',
      }}
    >
      {sortedLayers.map((layer, index) => (
        <LayerRenderer
          key={`${layer.role}-${index}`}
          layer={layer}
          frame={frame}
        />
      ))}
    </AbsoluteFill>
  );
};