import React from 'react';
import { Img, staticFile } from 'remotion';
import { useFadeIn, overlayContainerStyle } from './sceneStyles';

export const LogoGridTemplate: React.FC<{ params: Record<string, unknown> }> = ({ params }) => {
  const logos = (params.logos as string[]) || [];
  const opacity = useFadeIn();

  return (
    <div style={overlayContainerStyle}>
      <div style={{
        opacity,
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: 32,
        width: '100%',
        alignItems: 'center',
      }}>
        {logos.map((logo, i) => (
          <div key={i} style={{
            background: 'rgba(255,255,255,0.9)',
            borderRadius: 16,
            padding: 20,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <Img src={staticFile(`logos/${logo}`)} style={{ width: '100%', height: 'auto', maxHeight: 60 }} />
          </div>
        ))}
      </div>
    </div>
  );
};
