import React from 'react';
import { useFadeIn, overlayContainerStyle, headlineStyle, bodyStyle } from './sceneStyles';

export const ClosingTemplate: React.FC<{ params: Record<string, unknown> }> = ({ params }) => {
  const headline = (params.headline as string) || '';
  const subtext = (params.subtext as string) || '';
  const opacity = useFadeIn();

  return (
    <div style={overlayContainerStyle}>
      <div style={{ opacity, display: 'flex', flexDirection: 'column', gap: 16, alignItems: 'center' }}>
        <div style={headlineStyle}>{headline}</div>
        {subtext ? <div style={bodyStyle}>{subtext}</div> : null}
      </div>
    </div>
  );
};
