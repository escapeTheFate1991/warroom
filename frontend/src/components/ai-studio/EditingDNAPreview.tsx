import React, { useState } from 'react';
import { EditingDNA, Layer } from './remotion/EditingDNASchema';

export interface EditingDNAPreviewProps {
  dna: EditingDNA;
  className?: string;
}

interface LayerPreviewProps {
  layer: Layer;
  containerAspectRatio: string;
}

const LayerPreview: React.FC<LayerPreviewProps> = ({ layer, containerAspectRatio }) => {
  const [isHovered, setIsHovered] = useState(false);

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
    border: isHovered ? '2px solid #3b82f6' : '1px solid rgba(255,255,255,0.2)',
    borderRadius: layer.mask === 'rounded_corners_lg' ? '12px' : 
                  layer.mask === 'rounded_corners_sm' ? '4px' : 
                  layer.mask === 'circle' ? '50%' : '0',
    cursor: 'pointer',
    transition: 'border-color 0.2s ease',
  };

  const getBackgroundColor = (sourceType: string) => {
    switch (sourceType) {
      case 'video':
      case 'veo_generated_character':
      case 'veo_generated_environment':
        return '#1a1a1a';
      case 'image':
        return '#2a2a2a';
      case 'text_overlay':
        return '#3b82f6';
      case 'caption':
        return '#059669';
      case 'empty':
        return 'transparent';
      default:
        return '#6b7280';
    }
  };

  const getDisplayText = () => {
    if (layer.source_url) {
      return layer.role;
    }
    return `${layer.role}\n(${layer.source_type})`;
  };

  const tooltipInfo = {
    role: layer.role,
    position: `${layer.position.width} × ${layer.position.height}`,
    sourceType: layer.source_type,
    zIndex: layer.z_index,
    effects: layer.effects?.length ? layer.effects.join(', ') : 'None',
    mask: layer.mask || 'None',
  };

  return (
    <div
      style={{
        ...style,
        backgroundColor: getBackgroundColor(layer.source_type),
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      title={`${tooltipInfo.role} | ${tooltipInfo.sourceType} | z:${tooltipInfo.zIndex}`}
    >
      {layer.source_url ? (
        layer.source_type.includes('image') ? (
          <img 
            src={layer.source_url} 
            alt={layer.role}
            style={{ 
              width: '100%', 
              height: '100%', 
              objectFit: 'cover',
              opacity: isHovered ? 0.8 : 1,
            }}
          />
        ) : (
          <div
            style={{
              width: '100%',
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              fontSize: '10px',
              textAlign: 'center',
              opacity: isHovered ? 0.8 : 1,
              whiteSpace: 'pre-line',
            }}
          >
            {getDisplayText()}
          </div>
        )
      ) : (
        <div
          style={{
            width: '100%',
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontSize: '10px',
            textAlign: 'center',
            opacity: isHovered ? 0.8 : 1,
            whiteSpace: 'pre-line',
          }}
        >
          {getDisplayText()}
        </div>
      )}

      {isHovered && (
        <div
          style={{
            position: 'absolute',
            bottom: '-60px',
            left: '50%',
            transform: 'translateX(-50%)',
            backgroundColor: 'rgba(0,0,0,0.9)',
            color: '#fff',
            padding: '8px',
            borderRadius: '4px',
            fontSize: '11px',
            whiteSpace: 'nowrap',
            zIndex: 1000,
            boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
          }}
        >
          <div><strong>{tooltipInfo.role}</strong></div>
          <div>Size: {tooltipInfo.position}</div>
          <div>Type: {tooltipInfo.sourceType}</div>
          <div>Z-Index: {tooltipInfo.zIndex}</div>
          {tooltipInfo.effects !== 'None' && <div>Effects: {tooltipInfo.effects}</div>}
          {tooltipInfo.mask !== 'None' && <div>Mask: {tooltipInfo.mask}</div>}
        </div>
      )}
    </div>
  );
};

export const EditingDNAPreview: React.FC<EditingDNAPreviewProps> = ({ 
  dna, 
  className = '' 
}) => {
  const aspectRatio = dna.meta.aspect_ratio;
  const isPortrait = aspectRatio === '9:16';
  const isLandscape = aspectRatio === '16:9';
  const isSquare = aspectRatio === '1:1';

  const containerStyle: React.CSSProperties = {
    width: isPortrait ? '200px' : isLandscape ? '300px' : '200px',
    height: isPortrait ? '355px' : isLandscape ? '169px' : '200px',
    position: 'relative',
    backgroundColor: '#000',
    borderRadius: '8px',
    overflow: 'hidden',
    margin: '0 auto',
  };

  // Sort layers by z_index for proper rendering order
  const sortedLayers = [...dna.layers].sort((a, b) => a.z_index - b.z_index);

  return (
    <div className={`editing-dna-preview ${className}`}>
      {/* Phone Frame Preview */}
      <div style={containerStyle}>
        {sortedLayers.map((layer, index) => (
          <LayerPreview
            key={`${layer.role}-${index}`}
            layer={layer}
            containerAspectRatio={aspectRatio}
          />
        ))}
      </div>

      {/* Layout Info */}
      <div 
        style={{
          marginTop: '16px',
          padding: '12px',
          backgroundColor: '#f3f4f6',
          borderRadius: '6px',
          fontSize: '12px',
        }}
      >
        <h4 style={{ margin: '0 0 8px 0', fontWeight: 'bold', color: '#374151' }}>
          Layout Info
        </h4>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px', color: '#6b7280' }}>
          <div><strong>Layout ID:</strong> {dna.layout_id}</div>
          <div><strong>Type:</strong> {dna.meta.composition_type}</div>
          <div><strong>Aspect Ratio:</strong> {dna.meta.aspect_ratio}</div>
          <div><strong>Layers:</strong> {dna.layers.length}</div>
          {dna.meta.source_reference_id && (
            <div style={{ gridColumn: '1 / -1' }}>
              <strong>Source Ref:</strong> {dna.meta.source_reference_id}
            </div>
          )}
          {dna.audio_logic?.primary_track && (
            <div style={{ gridColumn: '1 / -1' }}>
              <strong>Audio:</strong> {dna.audio_logic.primary_track}
            </div>
          )}
          {dna.timing_dna?.transition_style && (
            <div style={{ gridColumn: '1 / -1' }}>
              <strong>Transition:</strong> {dna.timing_dna.transition_style}
            </div>
          )}
        </div>
      </div>

      {/* Layer List */}
      <div 
        style={{
          marginTop: '12px',
          fontSize: '11px',
          color: '#6b7280',
        }}
      >
        <strong>Layers (z-order):</strong>
        {sortedLayers.map((layer, index) => (
          <div 
            key={index}
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              padding: '2px 0',
              borderBottom: index < sortedLayers.length - 1 ? '1px solid #e5e7eb' : 'none',
            }}
          >
            <span>{layer.role}</span>
            <span>z:{layer.z_index}</span>
          </div>
        ))}
      </div>
    </div>
  );
};