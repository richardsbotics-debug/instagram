import React from 'react';
import { useFadeIn, overlayContainerStyle, headlineStyle } from './sceneStyles';

export const HookTemplate: React.FC<{ params: Record<string, unknown> }> = ({ params }) => {
  const text = (params.text as string) || '';
  const opacity = useFadeIn();

  return (
    <div style={overlayContainerStyle}>
      <div style={{ ...headlineStyle, opacity, fontSize: 68 }}>{text}</div>
    </div>
  );
};
