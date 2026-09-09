import React from 'react';
import { COLORS } from '../../lib/constants';
import { useFadeIn, overlayContainerStyle, headlineStyle } from './sceneStyles';

export const StrikethroughTemplate: React.FC<{ params: Record<string, unknown> }> = ({ params }) => {
  const oldText = (params.oldText as string) || '';
  const newText = (params.newText as string) || '';
  const opacity = useFadeIn();

  return (
    <div style={overlayContainerStyle}>
      <div style={{ opacity, display: 'flex', flexDirection: 'column', gap: 16, alignItems: 'center' }}>
        <div style={{ ...headlineStyle, color: COLORS.red, textDecoration: 'line-through', opacity: 0.7, fontSize: 44 }}>
          {oldText}
        </div>
        <div style={headlineStyle}>{newText}</div>
      </div>
    </div>
  );
};
